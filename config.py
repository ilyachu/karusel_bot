import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-3.1-flash-lite-preview")
FAL_KEY = os.getenv("FAL_KEY")
DATA_DIR = os.getenv("DATA_DIR", "data")
EXPORTS_DIR = os.getenv("EXPORTS_DIR", os.path.join(DATA_DIR, "exports"))
EXPORT_PUBLIC_BASE_URL = os.getenv("EXPORT_PUBLIC_BASE_URL", "")
THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
THREADS_USER_ID = os.getenv("THREADS_USER_ID", "me")
THREADS_API_BASE = os.getenv("THREADS_API_BASE", "https://graph.threads.net/v1.0")
THREADS_MEDIA_PROXY_BASE_URL = os.getenv("THREADS_MEDIA_PROXY_BASE_URL")
THREADS_MEDIA_PROXY_SECRET = os.getenv("THREADS_MEDIA_PROXY_SECRET")
THREADS_MEDIA_PROXY_TTL_SECONDS = int(os.getenv("THREADS_MEDIA_PROXY_TTL_SECONDS", "300"))
THREADS_MEDIA_PROXY_BOT_ALIAS = os.getenv("THREADS_MEDIA_PROXY_BOT_ALIAS", "")

admin_id = os.getenv("ADMIN_ID")
try:
    ADMIN_ID = int(admin_id) if admin_id else 252202
except ValueError:
    ADMIN_ID = 252202
    print("Warning: ADMIN_ID must be an integer. Falling back to default admin.")

if not all([TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, FAL_KEY]):
    print("Warning: Some API keys are missing in .env file")
