from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def classify_query(question: str) -> str:
    """
    Classify a user question as either:
      - company
      - general
    """

    prompt = f"""Classify the following user message into exactly one category.

Categories:
- "company": company/internal information
- "general": casual/general questions

Respond ONLY:
company
or
general

Message:
"{question}"

Category:"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=5,
    )

    label = response.choices[0].message.content.strip().lower()

    return "company" if "company" in label else "general"


def _build_history_messages(history: list[dict] | None) -> list[dict]:
    """
    Convert chat history into OpenAI format.
    """

    if not history:
        return []

    MAX_TURNS = 6
    trimmed = history[-MAX_TURNS:]

    messages = []

    for msg in trimmed:
        role = "user" if msg.get("sender") == "user" else "assistant"

        messages.append({
            "role": role,
            "content": msg.get("text", "")
        })

    return messages


def _build_user_context(user_name=None, user_role=None):

    if not user_name and not user_role:
        return ""

    parts = []

    if user_name:
        parts.append(f"Authenticated user name: {user_name}")

    if user_role:
        parts.append(f"Authenticated user role: {user_role}")

    return "\n".join(parts)


def generate_general_answer_stream(
    question,
    history=None,
    user_name=None,
    user_role=None,
):
    """
    General assistant with user awareness.
    """

    user_context = _build_user_context(
        user_name=user_name,
        user_role=user_role
    )

    system_text = """
You are a friendly enterprise assistant.

Rules:
- Use conversation history naturally.
- If user asks:
  - what is my name
  - who am i
  - what is my role
  answer ONLY using authenticated user context.
- Never invent identity.
- If identity not available say:
  "I don't know who is logged in."
- Keep answers concise.
"""

    if user_context:
        system_text += f"\n\nLogged in user:\n{user_context}"

    system_msg = {
        "role": "system",
        "content": system_text
    }

    messages = (
        [system_msg]
        + _build_history_messages(history)
        + [{"role": "user", "content": question}]
    )

    stream = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.5,
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta.content

        if delta:
            yield delta


def generate_answer_stream(
    context: str,
    question: str,
    history=None,
    user_name=None,
    user_role=None,
):
    """
    Company / RAG assistant with user awareness.
    """

    user_context = _build_user_context(
        user_name=user_name,
        user_role=user_role
    )

    system_text = """
You are an enterprise knowledge assistant.

Rules:

- Answer using ONLY the provided context.

- Multiple retrieved chunks may contain unrelated information.
Ignore unrelated chunks.

- If at least ONE chunk contains information needed to answer,
answer using that information.

- Use conversation history only to understand follow-up questions.

- Only say:
'Information not available'
when absolutely NONE of the provided context contains useful information.

- Do not hallucinate.

- Be concise and factual.

- User identity questions must be answered ONLY using authenticated user context.
""" 

    if user_context:
        system_text += f"\n\nLogged in user:\n{user_context}"

    system_msg = {
        "role": "system",
        "content": system_text
    }

    history_messages = _build_history_messages(history)

    user_msg = {
        "role": "user",
        "content": (
            f"Context:\n{context}\n\n"
            f"Question:\n{question}\n\n"
            f"Answer:"
        )
    }

    messages = (
        [system_msg]
        + history_messages
        + [user_msg]
    )

    stream = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.2,
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta.content

        if delta:
            yield delta


# Non-stream wrappers


def generate_general_answer(
    question,
    history=None,
    user_name=None,
    user_role=None,
):
    return "".join(
        generate_general_answer_stream(
            question,
            history,
            user_name,
            user_role,
        )
    )


def generate_answer(
    context,
    question,
    history=None,
    user_name=None,
    user_role=None,
):
    return "".join(
        generate_answer_stream(
            context,
            question,
            history,
            user_name,
            user_role,
        )
    )