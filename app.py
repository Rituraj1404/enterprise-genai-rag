import streamlit as st
import requests

API_BASE = "http://127.0.0.1:8000"

with st.sidebar:
    st.title("🔐 Session")
    if st.session_state.get("token"):
        st.success("Authenticated")
    else:
        st.warning("Not logged in")


st.set_page_config(
    page_title="Enterprise GenAI Assistant",
    page_icon="🤖",
    layout="centered"
)

# ------------------ SESSION STATE ------------------
if "token" not in st.session_state:
    st.session_state.token = None

if "chat" not in st.session_state:
    st.session_state.chat = []

# ------------------ API CALLS ------------------
def login_api(username, password):
    res = requests.post(
        f"{API_BASE}/login",
        data={"username": username, "password": password},
        timeout=10
    )
    if res.status_code != 200:
        return None
    return res.json()

def query_api(token, question):
    print(">>> SENDING QUESTION:", question)

    res = requests.post(
        f"{API_BASE}/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": question},
        timeout=20
    )

    print(">>> STATUS CODE:", res.status_code)
    print(">>> RESPONSE:", res.text)

    return res.json()


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


    # Chat input (IMPORTANT: use form)
    with st.form("chat_form"):
        question = st.text_input("Ask a question")
        ask_btn = st.form_submit_button("Ask")

    if ask_btn and question.strip():
        response = query_api(st.session_state.token, question)

        st.session_state.chat.append({
            "sender": "user",
            "text": question
        })

        st.session_state.chat.append({
            "sender": "ai",
            "text": response.get("answer", ""),
            "role": response.get("role", "")
        })

        st.rerun()
        
    if st.session_state.token:
        st.divider()
        st.subheader("📋 Audit Logs (Admin Only)")

        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        res = requests.get(f"{API_BASE}/audit-logs", headers=headers)
        if res.status_code == 200:
             logs = res.json()["logs"]
             st.table(logs)
             
             st.divider()
st.subheader("📄 Upload PDF")

uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

if uploaded_file:
    files = {"file": uploaded_file}
    res = requests.post(f"{API_BASE}/upload-pdf", files=files)

    if res.status_code == 200:
        st.success("PDF indexed successfully")



    # Logout
    if st.button("Logout"):
        st.session_state.token = None
        st.session_state.chat = []
        st.rerun()
