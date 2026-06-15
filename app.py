import streamlit as st
import requests

API_BASE = "http://127.0.0.1:8000"

# set_page_config MUST be the first Streamlit call
st.set_page_config(
    page_title="Enterprise GenAI Assistant",
    page_icon="🤖",
    layout="centered"
)

# ------------------ SESSION STATE ------------------
if "token" not in st.session_state:
    st.session_state.token = None

if "role" not in st.session_state:
    st.session_state.role = None

if "chat" not in st.session_state:
    st.session_state.chat = []

# ------------------ SIDEBAR ------------------
with st.sidebar:
    st.title("🔐 Session")
    if st.session_state.token:
        st.success("Authenticated")
        if st.session_state.role:
            st.caption(f"Role: {st.session_state.role}")
    else:
        st.warning("Not logged in")

# ------------------ API CALLS ------------------
def login_api(username, password):
    try:
        res = requests.post(
            f"{API_BASE}/login",
            data={"username": username, "password": password},
            timeout=10
        )
    except requests.exceptions.RequestException as e:
        st.error(f"Could not reach backend: {e}")
        return None

    if res.status_code != 200:
        return None
    return res.json()


def query_api(token, question):
    try:
        res = requests.post(
            f"{API_BASE}/query",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": question},
            timeout=20
        )
    except requests.exceptions.RequestException as e:
        st.error(f"Could not reach backend: {e}")
        return {"answer": "", "role": "", "sources": []}

    if res.status_code != 200:
        st.error(f"Query failed ({res.status_code}): {res.text}")
        return {"answer": "", "role": "", "sources": []}

    return res.json()


def get_audit_logs(token):
    try:
        res = requests.get(
            f"{API_BASE}/audit-logs",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
    except requests.exceptions.RequestException as e:
        st.error(f"Could not reach backend: {e}")
        return None

    if res.status_code != 200:
        return None
    return res.json().get("logs", [])


def upload_pdf_api(token, uploaded_file):
    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
    try:
        res = requests.post(
            f"{API_BASE}/upload-pdf",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            timeout=60
        )
    except requests.exceptions.RequestException as e:
        st.error(f"Could not reach backend: {e}")
        return False

    if res.status_code != 200:
        st.error(f"Upload failed ({res.status_code}): {res.text}")
        return False
    return True


# ------------------ UI ------------------
st.title("🤖 Enterprise GenAI Assistant")

# ========== LOGIN ==========
if st.session_state.token is None:
    st.subheader("🔐 Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_btn = st.form_submit_button("Login")

    if login_btn:
        data = login_api(username, password)
        if not data:
            st.error("Invalid credentials")
        else:
            st.session_state.token = data["access_token"]
            st.success("Login successful")
            st.rerun()

# ========== CHAT ==========
else:
    st.subheader("💬 Chat")

    # Show chat history
    for msg in st.session_state.chat:
        if msg["sender"] == "user":
            st.markdown(f"**You:** {msg['text']}")
        else:
            st.markdown(f"**AI:** {msg['text']}")
            st.caption(f"🔑 Role used: {msg['role']}")

    # Chat input
    with st.form("chat_form"):
        question = st.text_input("Ask a question")
        ask_btn = st.form_submit_button("Ask")

    if ask_btn and question.strip():
        response = query_api(st.session_state.token, question)

        if response.get("role"):
            st.session_state.role = response["role"]

        st.session_state.chat.append({"sender": "user", "text": question})
        st.session_state.chat.append({
            "sender": "ai",
            "text": response.get("answer", ""),
            "role": response.get("role", "")
        })

        st.rerun()

    # ---- Audit logs (admin only - backend enforces) ----
    st.divider()
    st.subheader("📋 Audit Logs (Admin Only)")
    logs = get_audit_logs(st.session_state.token)
    if logs is not None:
        if logs:
            st.table(logs)
        else:
            st.info("No audit logs yet.")
    else:
        st.caption("Not available for your role.")

    # ---- Upload PDF (admin only - backend enforces) ----
    st.divider()
    st.subheader("📄 Upload PDF")
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

    if uploaded_file:
        if upload_pdf_api(st.session_state.token, uploaded_file):
            st.success("PDF indexed successfully")

    # ---- Logout ----
    st.divider()
    if st.button("Logout"):
        st.session_state.token = None
        st.session_state.role = None
        st.session_state.chat = []
        st.rerun()