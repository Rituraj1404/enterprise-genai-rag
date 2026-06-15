from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_answer(context: str, question: str) -> str:
    prompt = f"""
You are an enterprise knowledge assistant.

Rules:
- Answer using the provided context. Multiple unrelated chunks may be included; use only the relevant ones.
- If NONE of the context relates to the question, say "Information not available"
- Be concise and factual
- Do NOT hallucinate

Context:
{context}

Question:
{question}

Answer:
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    return response.choices[0].message.content.strip()
