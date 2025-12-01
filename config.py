import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FAL_KEY = os.getenv("FAL_KEY")
ADMIN_ID = 252202

if not all([TELEGRAM_BOT_TOKEN, GEMINI_API_KEY, OPENAI_API_KEY, FAL_KEY]):
    print("Warning: Some API keys are missing in .env file")
