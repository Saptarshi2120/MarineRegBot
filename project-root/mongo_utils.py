# # mongo_utils.py
# from pymongo import MongoClient

# def get_qa_pairs_by_pdf(pdf_name):
#     client = MongoClient("mongodb+srv://saptarshidey2120:Saptarshi123@chatpdfcluster.mongodb.net/")
#     db = client['pdf_chat_db']
#     collection = db['chat_history']

#     # Fetch Q&A pairs for the given PDF name
#     docs = collection.find({"pdf_name": pdf_name})

#     qa_pairs = []
#     for doc in docs:
#         qa_pairs.append({
#             "q": doc.get("question", ""),
#             "a": doc.get("answer", "")
#         })

#     return qa_pairs


# project-root/mongo_utils.py

from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

# Securely load MongoDB URI from .env file
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://saptarshidey2120:Saptarshi123@chatpdfcluster.mongodb.net/")
DB_NAME = "pdf_chat_db"
COLLECTION_NAME = "chat_history"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

def get_qa_pairs_by_pdf_name(pdf_name):
    """
    Fetch Q&A pairs from MongoDB filtered by pdf_name.

    Returns a list of dictionaries with:
    - question (q)
    - answer (a)
    - sources (list)
    - timestamp (string)
    """
    query = {"pdf_name": pdf_name}
    projection = {
        "_id": 0,
        "question": 1,
        "answer": 1,
        "sources": 1,
        "timestamp": 1
    }

    docs = collection.find(query, projection).sort("timestamp", 1)

    qa_pairs = []
    for doc in docs:
        qa_pairs.append({
            "q": doc.get("question", ""),
            "a": doc.get("answer", ""),
            "sources": doc.get("sources", []),
            "timestamp": doc.get("timestamp", "")
        })

    return qa_pairs
