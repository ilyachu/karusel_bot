import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FAL_KEY = os.getenv("FAL_KEY")
DATA_DIR = os.getenv("DATA_DIR", "data")
EXPORTS_DIR = os.getenv("EXPORTS_DIR", os.path.join(DATA_DIR, "exports"))
EXPORT_PUBLIC_BASE_URL = os.getenv("EXPORT_PUBLIC_BASE_URL", "")

admin_id = os.getenv("ADMIN_ID")
try:
    ADMIN_ID = int(admin_id) if admin_id else 252202
except ValueError:
    ADMIN_ID = 252202
    print("Warning: ADMIN_ID must be an integer. Falling back to default admin.")

if not all([TELEGRAM_BOT_TOKEN, GEMINI_API_KEY, OPENAI_API_KEY, FAL_KEY]):
    print("Warning: Some API keys are missing in .env file")
