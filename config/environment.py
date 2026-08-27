import os
from dotenv import load_dotenv

# This tells Python to look for a .env file and load its contents
load_dotenv()

class Config:
    # Fetch the secret key from the environment
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
    GROQ_API_URL = os.getenv(
        "GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions"
    )
    ACCOUNTING_API_URL = os.getenv("ACCOUNTING_API_URL", "http://localhost:8080")
    ACCOUNTING_API_KEY = os.getenv("ACCOUNTING_API_KEY", "demo-key-1234")