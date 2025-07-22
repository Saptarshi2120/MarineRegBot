# ⚓ MarineRegBot – MARPOL & SOLAS Compliance Chatbot

[![Streamlit](https://img.shields.io/badge/Framework-Streamlit-red?style=flat-square&logo=streamlit)](https://streamlit.io/)
[![LangChain](https://img.shields.io/badge/Powered%20By-LangChain-green?style=flat-square)](https://www.langchain.com/)
[![Google Gemini](https://img.shields.io/badge/LLM-Google%20Gemini-blue?style=flat-square)](https://ai.google.dev/gemini-api)
[![MongoDB](https://img.shields.io/badge/Database-MongoDB-green?style=flat-square&logo=mongodb)](https://www.mongodb.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 **Overview**

**MarineRegBot** is an AI-powered regulatory compliance assistant for the **marine industry**.  
It uses **Google Gemini** and **LangChain** to answer **compliance-related questions** from **MARPOL** and **SOLAS** regulations.

### ✅ **Key Highlights**
- Preloaded **MARPOL** & **SOLAS 2020** regulations.
- **Custom PDF Q&A** – Upload your own documents.
- **Two Separate Pipelines**:
  1. **Marine Compliance Database** (Central regulatory database).
  2. **Custom PDF Q&A** (On-demand document queries).
- Multiple Q&A Modes:
  - **✅ Compliance Checker (Yes/No)**  
  - **⚠️ Violation Penalty Explanation**  
  - **📘 Scenario Training for Crew**  
  - **🌐 Multilingual (English, Simple English, Hindi)**

---

## Getting Started

### Prerequisites

- Python 3.8+
- Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

- Set up a `.env` file with your Google API key:

    ```makefile
    GOOGLE_API_KEY=your_api_key_here
    ```

### Running the App

1. Clone the repository:

    ```bash
    git clone https://github.com/Saptarshi2120/MarineRegBot.git
    ```

2. Navigate to the project directory:

    ```bash
    cd PDF-ChatBot
    ```

3. Install the required Python libraries:

    ```bash
    pip install -r requirements.txt
    ```

4. Run the Streamlit application:

    ```bash
    streamlit run main.py
    ```

5. Upload PDFs through the sidebar and start asking questions!


## 🚀 **Features**

### ✅ **1. Marine Compliance Q&A (Preloaded MARPOL & SOLAS PDFs)**
- Ask compliance-related questions directly.
- Get answers with **rule references** (e.g., "MARPOL Annex I Reg 14").
- Automatic **Yes/No compliance checker**.

### ✅ **2. Custom PDF Q&A**
- Upload multiple PDFs (e.g., Port Operations, Company Manuals).
- Generate FAISS vector indexes for semantic search.
- Optionally **merge into the Marine Compliance Database**.

### ✅ **3. Crew Training Assistant**
- Scenario-based Q&A for emergency drills.
- Step-by-step answers for onboard training.

### ✅ **4. Multilingual Support**
- English, **Simple English** (for non-technical crew), **Hindi**.

### ✅ **5. Logging & Monitoring**
- All Q&A logged in **MongoDB**.
- View real-time logs in the Streamlit sidebar.

---

## 🏗 **Tech Stack**

| Component           | Technology Used |
|----------------------|-----------------|
| **Frontend**        | Streamlit |
| **Backend (RAG)**   | LangChain + Google Gemini (Gemini 1.5 Flash) |
| **Vector DB**       | FAISS |
| **Database**        | MongoDB |
| **PDF Parsing**     | PyPDF2 |
| **Deployment Ready**| Streamlit Cloud / Hugging Face Spaces |

---
