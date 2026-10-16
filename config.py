import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Telegram Bot Config
BOT_TOKEN = os.getenv("BOT_TOKEN", "8916949352:AAFdxDRR6704E_Q87kREKMYE1KULHnBmJMk")
admin_env = os.getenv("ADMINS") or os.getenv("ADMIN_ID")
if admin_env:
    ADMINS = [int(x.strip()) for x in admin_env.split(",") if x.strip().isdigit()]
else:
    ADMINS = [8422157752]

DEFAULT_SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "ismoiluzb022")

# SeenSMS API Config
SEEN_API_URL = "https://seensms.uz/api/v1"
DEFAULT_SEEN_API_KEY = os.getenv("SEEN_API_KEY", "1ybZkQeX3znP4a2poz7ZW3VYr6Men8iT")

# Web Server & Web App Config
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("PORT", os.getenv("WEB_PORT", 8080)))

# Render auto-injects RENDER_EXTERNAL_URL
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
DEFAULT_WEBAPP_URL = os.getenv("WEBAPP_URL") or RENDER_EXTERNAL_URL or "https://pixorasmmuzbot.onrender.com"
WEBAPP_URL = DEFAULT_WEBAPP_URL

# Business defaults
DEFAULT_MARGIN_PERCENT = 20.0  # 20% margin for admin
DEFAULT_CARD_NUMBER = "6262 7201 2331 5395"
DEFAULT_CARD_HOLDER = "Pixora SMM"
DEFAULT_MIN_DEPOSIT = 5000  # UZS
DEFAULT_REF_BONUS = 500  # 500 UZS per active referral

# Database
DB_PATH = BASE_DIR / "pixora_smm.db"
ASSETS_DIR = BASE_DIR / "assets"
