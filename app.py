import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import shutil
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
from io import BytesIO
from logger import get_logger
from exception import CustomException, log_to_mongo
from pymongo import MongoClient
import sys
import time

# ========== Load .env and Logger ==========
logger = get_logger(__name__)
load_dotenv()

# Config
api_key = os.getenv("GOOGLE_API_KEY")
mongo_uri = os.getenv("MONGO_URI")
app_password = os.getenv("APP_PASSWORD", "admin")

if not api_key:
    logger.critical("GOOGLE_API_KEY missing.")
    st.error("API key not found in .env file.")
    st.stop()

if not mongo_uri:
    logger.critical("MONGO_URI missing.")
    st.error("MongoDB URI not found in .env file.")
    st.stop()

# Mongo Setup
mongo_client = MongoClient(mongo_uri)
db = mongo_client["pdf_chat_db"]
collection = db["chat_history"]
pdf_metadata_collection = db["pdf_metadata"]
app_logs_collection = db["app_logs"]

# Gemini Config
genai.configure(api_key=api_key)

# Constants
INDEX_DIR = "faiss_indexes"
LOG_DIR = "logs"
MARINE_INDEX_DIR = "marine_faiss_index"
os.makedirs(INDEX_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(MARINE_INDEX_DIR, exist_ok=True)

PRELOAD_PDFS = [
    "data/MARPOL.pdf",
    "data/SOLAS 2020.pdf"
]

# ========== Log Cleanup ==========
def clean_old_logs(max_files=10):
    logs = [f for f in os.listdir(LOG_DIR) if f.endswith(".log")]
    if len(logs) > max_files:
        logs.sort(key=lambda f: os.path.getctime(os.path.join(LOG_DIR, f)))
        for f in logs[:-max_files]:
            os.remove(os.path.join(LOG_DIR, f))
            logger.info(f"Deleted old log: {f}")
            log_to_mongo("INFO", f"Deleted old log: {f}", "clean_old_logs")

clean_old_logs()

# ========== Password Protection ==========
app_password = "1234"

if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False

def try_login():
    if st.session_state.entered_pw == app_password:
        st.session_state.auth_ok = True
    else:
        st.session_state.auth_ok = False
        st.error("Incorrect password")

if not st.session_state.auth_ok:
    st.sidebar.title("🔒 Login")
    
    st.sidebar.text_input(
        "Enter Password:",
        key="entered_pw",
        value=app_password,        # show 1234 by default
        on_change=try_login        # called on Enter
    )
    
    st.sidebar.button("Unlock", on_click=try_login)  # also allows manual click
    
    st.stop()

# ========== Marine PDFs Preloading ==========
def preload_marine_pdfs():
    try:
        if os.listdir(MARINE_INDEX_DIR):
            logger.info("Marine regulatory indexes already exist.")
            return

        all_text = ""
        for pdf_path in PRELOAD_PDFS:
            pdf_reader = PdfReader(pdf_path)
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text:
                    all_text += f"[Source: {os.path.basename(pdf_path)}, Page {page_num+1}]\n{page_text}\n"

        splitter = RecursiveCharacterTextSplitter(chunk_size=3000, chunk_overlap=300)
        chunks = splitter.split_text(all_text)

        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        metadatas = [{"source": "MARPOL_SOLAS"} for _ in chunks]
        vector_store = FAISS.from_texts(chunks, embedding=embeddings, metadatas=metadatas)
        vector_store.save_local(MARINE_INDEX_DIR)

        msg = f"Preloaded MARPOL & SOLAS 2020 into FAISS index with {len(chunks)} chunks."
        logger.info(msg)
        log_to_mongo("INFO", msg, "preload_marine_pdfs")

    except Exception as e:
        raise CustomException(e, sys)

preload_marine_pdfs()

# ========== PDF Processing (Custom + Upgrade Option) ==========
def process_and_store(pdf_file, replace=True):
    try:
        file_name = pdf_file.name
        index_path = os.path.join(INDEX_DIR, file_name + "_index")

        if replace and os.path.exists(index_path):
            shutil.rmtree(index_path)
            msg = f"Replaced vector store for {file_name}"
            logger.info(msg)
            log_to_mongo("INFO", msg, "process_and_store", {"pdf_name": file_name})

        pdf_reader = PdfReader(BytesIO(pdf_file.read()))
        all_text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                all_text += page_text + "\n"

        page_count = len(pdf_reader.pages)
        word_count = len(all_text.split())
        preview = all_text[:300] + "..." if len(all_text) > 300 else all_text

        splitter = RecursiveCharacterTextSplitter(chunk_size=3000, chunk_overlap=300)
        chunks = splitter.split_text(all_text)
        chunk_count = len(chunks)

        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        metadatas = [{"source": file_name} for _ in chunks]
        vector_store = FAISS.from_texts(chunks, embedding=embeddings, metadatas=metadatas)
        vector_store.save_local(index_path)

        msg = f"Vector store created for {file_name} with {chunk_count} chunks."
        logger.info(msg)
        log_to_mongo("INFO", msg, "process_and_store", {"pdf_name": file_name, "chunk_count": chunk_count})

        metadata_doc = {
            "pdf_name": file_name,
            "upload_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "page_count": page_count,
            "word_count": word_count,
            "summary_preview": preview,
            "chunk_count": chunk_count,
            "index_path": index_path,
            "uploaded_by": "admin"
        }
        pdf_metadata_collection.insert_one(metadata_doc)

        return file_name, word_count, chunk_count, preview

    except Exception as e:
        raise CustomException(e, sys)

def upgrade_to_marine_database(pdf_name):
    try:
        index_path = os.path.join(INDEX_DIR, pdf_name + "_index")
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        custom_db = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
        marine_db = FAISS.load_local(MARINE_INDEX_DIR, embeddings, allow_dangerous_deserialization=True)
        marine_db.merge_from(custom_db)
        marine_db.save_local(MARINE_INDEX_DIR)

        msg = f"✅ {pdf_name} upgraded to Marine Compliance Database."
        logger.info(msg)
        log_to_mongo("INFO", msg, "upgrade_to_marine_database", {"pdf_name": pdf_name})
        st.success(msg)
    except Exception as e:
        st.error("⚠️ Upgrade failed.")
        raise CustomException(e, sys)

# ========== Prompt Optimization ==========
def get_conversational_chain(mode="professional", language="English"):
    try:
        if mode == "compliance":
            prompt_template = """
Answer YES or NO first. Then explain briefly with regulation reference (e.g., MARPOL Annex I Reg 14).
If the answer is not available, say "Answer not available in the context".

Context:
{context}

Question:
{question}

Answer:
"""
        elif mode == "penalty":
            prompt_template = """
Explain the possible penalties or consequences for non-compliance as per MARPOL or SOLAS.
Mention fines, detention, or other enforcement actions if available.

Context:
{context}

Question:
{question}

Answer:
"""
        elif mode == "scenario":
            prompt_template = """
Answer as step-by-step guidance suitable for crew training. Use numbered points for clarity.

Context:
{context}

Question:
{question}

Answer:
"""
        else:
            if language == "Hindi":
                prompt_template = """
उत्तर हिंदी में दें। नियम संख्या (Annex / Chapter / Regulation) भी बताएँ यदि संभव हो।
यदि उत्तर उपलब्ध नहीं है तो कहें: "उत्तर संदर्भ में उपलब्ध नहीं है।"

संदर्भ:
{context}

प्रश्न:
{question}

उत्तर:
"""
            elif language == "Simple English":
                prompt_template = """
Explain in simple English for a general audience, but also mention regulation numbers if possible.

Context:
{context}

Question:
{question}

Answer:
"""
            else:
                prompt_template = """
Provide a precise professional compliance answer with regulation reference.

Context:
{context}

Question:
{question}

Answer:
"""

        model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)
        prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
        chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
        return chain
    except Exception as e:
        raise CustomException(e, sys)

# ========== Q&A Function ==========
def question_answer(user_question, index_path, mode="professional", language="English"):
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        db_local = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)

        docs = db_local.similarity_search(user_question)
        chain = get_conversational_chain(mode, language)
        response = chain({"input_documents": docs, "question": user_question}, return_only_outputs=True)
        answer = response["output_text"]

        st.write("🧠 **Answer:**", answer)
        st.download_button("📥 Download Answer", answer, file_name="answer.txt")

        sources = set(doc.metadata.get("source", "Unknown") for doc in docs)
        st.markdown("**📄 Source(s):**")
        for src in sources:
            st.markdown(f"- `{src}`")

        log_data = {
            "question": user_question,
            "answer": answer,
            "mode": mode,
            "language": language,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        collection.insert_one(log_data)
        log_to_mongo("INFO", f"Q&A Logged: {log_data}", "question_answer", log_data)

    except Exception as e:
        st.error("⚠️ Something went wrong while answering your question.")
        raise CustomException(e, sys)

# ========== View Logs ==========
def view_logs():
    try:
        log_file = sorted(os.listdir(LOG_DIR))[-1]
        with open(os.path.join(LOG_DIR, log_file), "r") as f:
            lines = f.readlines()
            st.text("".join(lines[-50:]))
    except:
        st.warning("Log file not found or empty.")

# ========== Main App ==========
def main():
    try:
        st.set_page_config("📚 MarineRegBot")
        st.title("⚓ Marine Regulatory Bot")

        tab1, tab2 = st.tabs(["💬 Marine Compliance Q&A", "🗂️ Custom PDF Q&A & Management"])

        # ====== Tab 1: Marine Compliance ======
        with tab1:
            st.subheader("💬 Ask Marine Compliance Questions (MARPOL & SOLAS Database)")
            marine_pdfs = ", ".join(PRELOAD_PDFS + [f for f in os.listdir(MARINE_INDEX_DIR)])
            st.info(f"**Currently Loaded Marine PDFs:** {marine_pdfs}")

            with st.form("marine_qa_form", clear_on_submit=False):
                user_question = st.text_input("Ask your compliance question:")
                language = st.selectbox("🌐 Language", ["English", "Simple English", "Hindi"])
                compliance_mode = st.checkbox("✅ Compliance Checker (Yes/No)")
                scenario_mode = st.checkbox("📘 Scenario Training Mode")
                penalty_mode = st.checkbox("⚠️ Penalty Explanation Mode")
                submitted = st.form_submit_button("Get Answer", use_container_width=True)

            mode = "professional"
            if compliance_mode:
                mode = "compliance"
            elif penalty_mode:
                mode = "penalty"
            elif scenario_mode:
                mode = "scenario"
            elif language != "English":
                mode = "simple"

            if submitted:
                if user_question:
                    question_answer(user_question, MARINE_INDEX_DIR, mode, language)
                else:
                    st.warning("Please enter a question.")

        # ====== Tab 2: Custom PDFs ======
        with tab2:
            st.subheader("📤 Upload & Ask Questions on Custom PDFs")
            pdf_docs = st.file_uploader("Upload PDFs", accept_multiple_files=True)
            replace = st.checkbox("🔄 Replace existing vector store for each file?", value=True)

            if st.button("Submit & Process PDFs"):
                with st.spinner("Processing..."):
                    for pdf in pdf_docs:
                        name, wc, cc, preview = process_and_store(pdf, replace=replace)
                        st.success(f"✅ {name}: {wc} words, {cc} chunks")
                        st.code(preview, language='markdown')

                        if st.button(f"✅ Add {name} to Marine Database"):
                            upgrade_to_marine_database(name)

            available_indexes = [
                f.replace("_index", "") for f in os.listdir(INDEX_DIR) if f.endswith("_index")
            ]

            if available_indexes:
                selected_pdf = st.selectbox("Choose Custom PDF to ask from:", available_indexes)

                with st.form("custom_qa_form", clear_on_submit=False):
                    user_question_custom = st.text_input("Ask your question:")
                    language_custom = st.selectbox("🌐 Language (Custom PDFs)", ["English", "Simple English", "Hindi"])
                    compliance_mode_custom = st.checkbox("✅ Compliance Checker (Yes/No) - Custom")
                    scenario_mode_custom = st.checkbox("📘 Scenario Training - Custom")
                    penalty_mode_custom = st.checkbox("⚠️ Penalty Mode - Custom")
                    submitted_custom = st.form_submit_button("Get Answer", use_container_width=True)

                mode_custom = "professional"
                if compliance_mode_custom:
                    mode_custom = "compliance"
                elif penalty_mode_custom:
                    mode_custom = "penalty"
                elif scenario_mode_custom:
                    mode_custom = "scenario"
                elif language_custom != "English":
                    mode_custom = "simple"

                if submitted_custom:
                    if selected_pdf and user_question_custom:
                        index_path = os.path.join(INDEX_DIR, selected_pdf + "_index")
                        question_answer(user_question_custom, index_path, mode_custom, language_custom)
                    else:
                        st.warning("Please enter a question and select a PDF.")

            if st.button("🧹 Delete All Custom FAISS Indexes"):
                shutil.rmtree(INDEX_DIR)
                os.makedirs(INDEX_DIR)
                st.success("🧹 All Custom FAISS indexes deleted")
                log_to_mongo("INFO", "Deleted all FAISS indexes", "main")

        # ====== Sidebar Logs ======
        with st.sidebar:
            st.title("🔍 View Logs")
            if "refresh_logs" not in st.session_state:
                st.session_state.refresh_logs = False

            if st.button("🔄 Refresh Logs"):
                st.session_state.refresh_logs = True
                time.sleep(0.2)

            if st.session_state.refresh_logs:
                view_logs()
                st.session_state.refresh_logs = False

    except Exception as e:
        st.error("🚨 Critical error occurred. Check logs.")
        raise CustomException(e, sys)

# Run app
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical("App crashed.")
        log_to_mongo("CRITICAL", "App crashed", "__main__")
        raise CustomException(e, sys)
