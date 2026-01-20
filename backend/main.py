from fastapi import FastAPI, Depends
from auth.jwt import create_access_token, verify_token
from auth.roles import require_role
from langchain_openai import ChatOpenAI
from fastapi import Depends
from rag.retriever import retrieve_documents
from auth.jwt import verify_token
from database.read_audit import fetch_audit_logs
from database.audit import init_db, log_event



app = FastAPI()



init_db()

# Dummy users (replace with DB later)
fake_users = {
    "intern": {"password": "intern123", "role": "intern"},
    "manager": {"password": "manager123", "role": "manager"},
    "admin": {"password": "admin123", "role": "admin"},
}

from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends, HTTPException

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    username = form_data.username
    password = form_data.password

    user = fake_users.get(username)
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({
        "sub": username,
        "role": user["role"]
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@app.get("/protected")
def protected(user=Depends(verify_token)):
    return {"message": "Access granted", "user": user}

@app.get("/admin-only")
def admin_only(user=Depends(require_role("admin"))):
    return {"message": "Welcome Admin"}

from rag.retriever import retrieve_documents, build_vectorstore

build_vectorstore()

from llm.generator import generate_answer
from fastapi import Depends
from auth.jwt import verify_token
from rag.retriever import retrieve_documents

FORBIDDEN_KEYWORDS = ["revenue", "financial", "salary", "profit"]

from pydantic import BaseModel

class QueryRequest(BaseModel):
    question: str
    
    

@app.post("/query")
def query_ai(req: QueryRequest, user=Depends(verify_token)):
    question = req.question

    username = user["sub"]
    role = user["role"]
    q_lower = question.lower()

    # 🔐 Guardrail
    if any(word in q_lower for word in FORBIDDEN_KEYWORDS) and role != "admin":
        log_event(
            username=username,
            role=role,
            question=question,
            decision="blocked",
            sources=[]
        )

        return {
            "answer": "You are not authorized to access financial information.",
            "role": role,
            "sources": []
        }

    docs = retrieve_documents(question, role)

    if not docs:
        log_event(
            username=username,
            role=role,
            question=question,
            decision="no_results",
            sources=[]
        )

        return {
            "answer": "No relevant documents found for your role.",
            "role": role,
            "sources": []
        }

    context = "\n\n".join([doc.page_content for doc in docs])
    answer = generate_answer(context, question)
  

    sources = [doc.metadata["source"] for doc in docs]

    log_event(
        username=username,
        role=role,
        question=question,
        decision="allowed",
        sources=sources
    )

    return {
        "answer": answer,
        "role": role,
        "sources": [doc.metadata for doc in docs]
    }


@app.get("/audit-logs")
def get_audit_logs(user=Depends(verify_token)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    logs = fetch_audit_logs()
    return {"logs": logs}

from fastapi import UploadFile, File

@app.post("/upload-pdf")
def upload_pdf(file: UploadFile = File(...), user=Depends(verify_token)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    content = file.file.read()
    save_and_index_pdf(content, file.filename)

    return {"status": "indexed"}


    
    