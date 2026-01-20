from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_answer(context: str, question: str) -> str:
    prompt = f"""
You are an enterprise knowledge assistant.

Rules:
- Answer ONLY using the provided context
- If context is insufficient, say "Information not available"
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
