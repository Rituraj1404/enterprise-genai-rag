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
from collections import defaultdict

app = FastAPI()


chat_history = defaultdict(list)
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

def build_contextual_question(
    username,
    question,
):

    history = chat_history[username]

    if not history:
        return question

    recent = history[-4:]

    context = "\n".join([
        f'{x["sender"]}: {x["text"]}'
        for x in recent
    ])

    return f"""
Conversation:
{context}

Current question:
{question}
"""


@app.post("/query")
def query_ai(req: QueryRequest, user=Depends(verify_token)):

    question = req.question

    username = user["sub"]
    role = user["role"]

    original_question = question

    # conversational retrieval context
    question = build_contextual_question(
        username=username,
        question=question,
    )

    q_lower = original_question.lower().strip()

    GREETINGS = {
        "hi",
        "hello",
        "hey",
        "hii",
        "good morning",
        "good afternoon",
        "good evening",
        "thanks",
        "thank you",
        "bye",
        "goodbye",
    }

    if q_lower in GREETINGS or q_lower.rstrip("!.?") in GREETINGS:
        log_event(
            username=username,
            role=role,
            question=original_question,
            decision="greeting",
            sources=[],
        )

        return {
            "answer": "Hello! How can I help you with company policies, projects, or other information today?",
            "role": role,
            "sources": [],
        }

    if any(word in q_lower for word in FORBIDDEN_KEYWORDS) and role != "admin":

        log_event(
            username=username,
            role=role,
            question=original_question,
            decision="blocked",
            sources=[],
        )

        return {
            "answer": "You are not authorized to access financial information.",
            "role": role,
            "sources": [],
        }

    intent = classify_query(original_question)

    # ---------- GENERAL ----------
    if intent == "general":

        answer = generate_general_answer(
            question=question,
            history=chat_history[username],
            user_name=username,
            user_role=role,
        )

        # save memory
        chat_history[username].append({
            "sender": "user",
            "text": original_question,
        })

        chat_history[username].append({
            "sender": "ai",
            "text": answer,
        })

        log_event(
            username=username,
            role=role,
            question=original_question,
            decision="general",
            sources=[],
        )

        return {
            "answer": answer,
            "role": role,
            "sources": [],
        }

    # ---------- RAG ----------
    docs = retrieve_documents(
        question,
        role,
    )

    if not docs:

        log_event(
            username=username,
            role=role,
            question=original_question,
            decision="no_results",
            sources=[],
        )

        return {
            "answer": "No relevant documents found for your role.",
            "role": role,
            "sources": [],
        }

    context = "\n\n".join(
        doc.page_content
        for doc in docs
    )
    print("\n========== CONTEXT ==========")
    print(context)
    print("=============================\n")

    answer = generate_answer(
        context=context,
        question=original_question,
        history=chat_history[username],
        user_name=username,
        user_role=role,
    )

    sources = []

    for doc in docs:  
        src = doc.metadata.get(
        "source",
        "unknown"
        )
        if src not in sources:
            sources.append(src)
    # append citations
    answer += "\n\nSources:\n"

    for s in sources:
         answer += f"• {s}\n"

                

    # save memory
    chat_history[username].append({
        "sender": "user",
        "text": original_question,
    })

    chat_history[username].append({
        "sender": "ai",
        "text": answer,
    })

    sources = [
        doc.metadata.get(
            "source",
            "unknown",
        )
        for doc in docs
    ]

    log_event(
        username=username,
        role=role,
        question=original_question,
        decision="allowed",
        sources=sources,
    )

    return {
        "answer": answer,
        "role": role,
        "sources": [
            doc.metadata
            for doc in docs
        ],
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