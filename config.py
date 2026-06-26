import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GEMINI_API_KEYS_RAW = os.getenv("GEMINI_API_KEY", "")
GEMINI_API_KEYS = [k.strip() for k in GEMINI_API_KEYS_RAW.split(",") if k.strip()]
GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else ""

# تحليل قائمة معرفات المدراء (Admin IDs) من نص مفصول بفواصل إلى قائمة أرقام
admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = []
if admin_ids_raw:
    try:
        ADMIN_IDS = [int(x.strip()) for x in admin_ids_raw.split(",") if x.strip()]
    except ValueError:
        print("WARNING: Failed to parse ADMIN_IDS as numbers. Make sure they are comma-separated integers.")
