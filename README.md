# 🔐 Enterprise GenAI RAG System (FastAPI + Streamlit)

An **enterprise-grade Generative AI application** demonstrating **secure Retrieval-Augmented Generation (RAG)** with **role-based access control (RBAC)**, **audit logging**, and a clean **Streamlit frontend**.

This project is designed to showcase **real-world GenAI engineering practices** rather than a basic chatbot.

---

## 🚀 Features

### 🔑 Authentication & Authorization
- JWT-based authentication
- Role-Based Access Control (RBAC)
  - **Intern**
  - **Manager**
  - **Admin**
- Stateless authorization using JWT tokens

---

### 📚 Retrieval-Augmented Generation (RAG)
- Vector search using **FAISS**
- Semantic retrieval over internal documents
- Role-aware document filtering
- Top-K retrieval strategy

---

### 🛡️ Security & Guardrails
- Sensitive keyword blocking for non-admin roles
- Role-based access enforcement at retrieval level
- Prevents data leakage across roles

---

### 📝 Audit Logging
- Every query is logged with:
  - Username
  - Role
  - Question
  - Decision (allowed / blocked / no results)
  - Timestamp
- Stored in **SQLite**
- Enables traceability and governance

---

### 🖥️ Frontend (Streamlit)
- Interactive chat-style UI
- Login-based session handling
- Role-aware responses
- Ideal for demos and interviews

---

## 🏗️ Architecture

Streamlit UI
│
▼
FastAPI Backend
├─ JWT Auth
├─ RBAC
├─ Guardrails
├─ Audit Logs
└─ RAG Engine
│
▼
FAISS Index
│
▼
LLM


---

## 🧰 Tech Stack

| Layer | Technology |
|-----|-----------|
| Backend | FastAPI |
| Frontend | Streamlit |
| Vector Store | FAISS |
| Embeddings | Sentence Transformers |
| LLM | OpenAI-compatible API |
| Auth | JWT |
| Database | SQLite |
| Language | Python 3.10 |

---

## 📂 Project Structure

GenAI/
├── backend/
│ ├── auth/ # JWT authentication
│ ├── rag/ # Embeddings, retriever, loaders
│ ├── llm/ # LLM interaction logic
│ ├── database/ # Audit logging (SQLite)
│ ├── main.py # FastAPI entry point
│ └── requirements.txt
│
├── streamlit_app/
│ └── app.py # Streamlit frontend
│
└── README.md

---

## ▶️ Run Locally

### 1️⃣ Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt


## ▶️ Run Backend (FastAPI)

```bash
cd backend
python -m venv venv
venv\Scripts\activate    # Windows
pip install -r requirements.txt
python -m uvicorn main:app --reload


