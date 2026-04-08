"""
config.py — Configuration loader for OTP Bot
Loads settings from environment variables (.env file) or falls back to defaults.
"""

import os
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

# ─────────────────────────────────────────────
# 🔑 Required tokens — set these in your .env
# ─────────────────────────────────────────────

# Telegram Bot Token from @BotFather
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "your-telegram-bot-token")

# 5sim.net API Key from profile page
FIVESIM_API_KEY: str = os.getenv("FIVESIM_API_KEY", "your-5sim-api-key")

# ─────────────────────────────────────────────
# 💰 Price / behaviour settings
# ─────────────────────────────────────────────

# Maximum price in cents (default $0.15 = 15 cents)
MAX_PRICE: int = int(os.getenv("MAX_PRICE", "15"))

# Minimum stock required to consider a country/operator (avoids empty providers)
MIN_STOCK: int = int(os.getenv("MIN_STOCK", "10"))

# OTP polling interval in seconds
POLL_INTERVAL: int = int(os.getenv("POLL_INTERVAL", "5"))

# OTP wait timeout in seconds (120 = 2 minutes)
OTP_TIMEOUT: int = int(os.getenv("OTP_TIMEOUT", "120"))

# Maximum number of countries to try when buying (retries)
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))

# ─────────────────────────────────────────────
# 👤 Access control (optional)
# ─────────────────────────────────────────────

# Comma-separated Telegram user IDs allowed to use the bot.
# Leave empty (or unset) to allow everyone.
_admin_ids_raw: str = os.getenv("ADMIN_USER_IDS", "")
ADMIN_USER_IDS: list[int] = (
    [int(uid.strip()) for uid in _admin_ids_raw.split(",") if uid.strip()]
    if _admin_ids_raw.strip()
    else []
)

# Price escalation steps in cents (auto-increase if nothing found at MAX_PRICE)
PRICE_ESCALATION_STEPS: list[int] = [15, 25, 50, 100, 200]

# ─────────────────────────────────────────────
# 🌐 5sim.net base URL
# ─────────────────────────────────────────────
FIVESIM_BASE_URL: str = "https://5sim.net"
