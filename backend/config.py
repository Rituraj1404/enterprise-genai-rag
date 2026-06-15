import os
from dotenv import load_dotenv
from pathlib import Path

# Force absolute path to .env
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)

SECRET_KEY = os.getenv("SECRET_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

print("ENV PATH:", ENV_PATH)
print("DEBUG SECRET_KEY:", SECRET_KEY)
print("DEBUG OPENAI_API_KEY:", OPENAI_API_KEY)
print("DEBUG GROQ_API_KEY:", GROQ_API_KEY)
