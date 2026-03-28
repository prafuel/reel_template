"""
bot_runner.py — Entry point for the Telegram Reel Bot
======================================================
Usage:
    python bot_runner.py

Reads TELEGRAM_BOT_API from .env (or the shell environment).
"""
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ── Token ─────────────────────────────────────────────────────────────────────
TOKEN = os.getenv("TELEGRAM_BOT_API")
if not TOKEN:
    logger.error("TELEGRAM_BOT_API is not set. Add it to your .env file.")
    sys.exit(1)

# ── Import bot (after env is loaded) ─────────────────────────────────────────
from src.bot import build_app  # noqa: E402


def main() -> None:
    logger.info("🤖 Starting Reel Bot …")
    app = build_app(TOKEN)
    logger.info("✅ Bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
