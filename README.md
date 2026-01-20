Enterprise-Grade GenAI RAG System with RBAC & Audit Logs

A full-stack, enterprise-oriented Generative AI application built using FastAPI, FAISS, Streamlit, and LLMs, designed to demonstrate secure, role-aware knowledge retrieval, governance, and production-style architecture.

This project goes beyond a basic chatbot and focuses on real-world GenAI concerns such as:

Role-based access control

Data leakage prevention

Auditability

Retrieval tuning

Clean frontend interaction

🚀 Key Features
🔐 Authentication & Authorization

JWT-based authentication

Role-Based Access Control (RBAC):

Intern

Manager

Admin

Stateless authorization using tokens

📚 Retrieval-Augmented Generation (RAG)

Semantic search using FAISS

Text & PDF document ingestion

Role-aware document filtering

Top-K retrieval with configurable behavior

🛡️ Security & Guardrails

Keyword-based sensitive information blocking

Role-based access enforcement

Defense-in-depth approach:

Document-level filtering

Query-level guardrails

📝 Audit Logging (Governance)

Every query is logged with:

Username

Role

Question

Decision (allowed / blocked / no results)

Timestamp

Stored in SQLite

Enables traceability & compliance

🖥️ Frontend (Streamlit)

Clean, interactive chat UI

Login-based session handling

Role-aware responses

Supports iterative questioning

Designed for demos & interviews
