from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from auth.jwt import create_access_token, verify_token
from auth.roles import require_role
from database.users_db import init_users_db, get_user, create_default_users, verify_password

from rag.retriever import retrieve_documents, build_vectorstore, save_and_index_pdf
from llm.generator import generate_answer, classify_query, generate_general_answer
from database.audit import init_db, log_event
from database.read_audit import fetch_audit_logs

app = FastAPI()

# -----------------------------
# Startup: init DBs once
# -----------------------------
init_db()
init_users_db()
create_default_users()  # seeds intern/manager/admin if table empty

# Build vectorstore once at startup (not on every import in hot-reload loops)
build_vectorstore()

FORBIDDEN_KEYWORDS = ["revenue", "financial", "salary", "profit"]


class QueryRequest(BaseModel):
    question: str


# -----------------------------
# Auth
# -----------------------------
@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/protected")
def protected(user=Depends(verify_token)):
    return {"message": "Access granted", "user": user}


@app.get("/admin-only")
def admin_only(user=Depends(require_role("admin"))):
    return {"message": "Welcome Admin"}


# -----------------------------
# RAG Query
# -----------------------------
@app.post("/query")
def query_ai(req: QueryRequest, user=Depends(verify_token)):
    question = req.question
    username = user["sub"]
    role = user["role"]
    q_lower = question.lower().strip()

    # Handle greetings/small talk without hitting the RAG pipeline —
    # FAISS always returns top-k chunks even for "hello", which then
    # makes the LLM say "Information not available" for a non-question.
    GREETINGS = {"hi", "hello", "hey", "hii", "good morning", "good afternoon",
                  "good evening", "thanks", "thank you", "bye", "goodbye"}
    if q_lower in GREETINGS or q_lower.rstrip("!.?") in GREETINGS:
        log_event(username=username, role=role, question=question, decision="greeting", sources=[])
        return {
            "answer": "Hello! How can I help you with company policies, projects, or other information today?",
            "role": role,
            "sources": [],
        }

    # Guardrail: block sensitive keywords for non-admins
    if any(word in q_lower for word in FORBIDDEN_KEYWORDS) and role != "admin":
        log_event(username=username, role=role, question=question, decision="blocked", sources=[])
        return {
            "answer": "You are not authorized to access financial information.",
            "role": role,
            "sources": [],
        }

    # Classify: is this a company/docs question, or general chat?
    # Company questions go through strict RAG (context-only).
    # General questions get a normal LLM answer, no "Information not available".
    intent = classify_query(question)

    if intent == "general":
        answer = generate_general_answer(
        question=question,
        history=None,
        user_name=username,
        user_role=role,
     )

        log_event(
        username=username,
        role=role,
        question=question,
        decision="general",
        sources=[]
    )

        return {
        "answer": answer,
        "role": role,
        "sources": [],
     }

    docs = retrieve_documents(question, role)

    if not docs:
        log_event(username=username, role=role, question=question, decision="no_results", sources=[])
        return {
            "answer": "No relevant documents found for your role.",
            "role": role,
            "sources": [],
        }

    context = "\n\n".join(doc.page_content for doc in docs)
    answer = generate_answer(
    context=context,
    question=question,
    history=None,
    user_name=username,
    user_role=role,
    )

    sources = [doc.metadata.get("source", "unknown") for doc in docs]

    log_event(username=username, role=role, question=question, decision="allowed", sources=sources)

    return {
        "answer": answer,
        "role": role,
        "sources": [doc.metadata for doc in docs],
    }


# -----------------------------
# Audit logs (admin only)
# -----------------------------
@app.get("/audit-logs")
def get_audit_logs(user=Depends(require_role("admin"))):
    logs = fetch_audit_logs()
    return {"logs": logs}


# -----------------------------
# Upload + index PDF (admin only)
# -----------------------------
@app.post("/upload-pdf")
def upload_pdf(
    file: UploadFile = File(...),
    role: str = "admin",  # which doc category to file this under: intern/manager/admin
    user=Depends(require_role("admin")),
):
    content = file.file.read()
    save_and_index_pdf(content, file.filename, role=role)
    return {"status": "indexed", "filename": file.filename, "role": role}