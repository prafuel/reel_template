"""
bot.py
Telegram bot that accepts a YouTube URL and returns the processed reel video.
Uses python-telegram-bot v20+ (async Application).
"""
import os
import re
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.request import HTTPXRequest

from src.pipeline import run_pipeline

logger = logging.getLogger(__name__)

# YouTube URL pattern (supports youtu.be, youtube.com/watch, /shorts, /live)
YT_PATTERN = re.compile(
    r"(https?://)?(www\.)?"
    r"(youtube\.com/(watch\?.*v=|shorts/|live/)|youtu\.be/)"
    r"[\w\-]+"
)

# Thread pool so the blocking pipeline doesn't stall the event loop
_executor = ThreadPoolExecutor(max_workers=3)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_url(text: str) -> str | None:
    """Return the first YouTube URL found in *text*, or None."""
    m = YT_PATTERN.search(text)
    if not m:
        return None
    url = m.group(0)
    if not url.startswith("http"):
        url = "https://" + url
    return url


async def _run_in_thread(url: str, caption: str | None = None):
    """Run the blocking pipeline in a thread-pool executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, run_pipeline, url, caption)


# ── Handlers ──────────────────────────────────────────────────────────────────

WELCOME_TEXT = (
    "👋 *Welcome to the Reel Bot!*\n\n"
    "Send me any *YouTube link* and I'll turn it into an "
    "Instagram-ready 9:16 reel with watermark and caption.\n\n"
    "*Formats supported:*\n"
    "`https://youtu.be/xxxxx` — uses video title as caption\n"
    "`https://youtu.be/xxxxx My custom caption` — uses your text\n"
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME_TEXT, parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME_TEXT, parse_mode="Markdown")


def _extract_caption(text: str, url: str) -> str | None:
    """Return text that follows the URL in *text*, stripped; None if empty."""
    remainder = text.replace(url, "", 1).strip()
    return remainder if remainder else None


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    url = _extract_url(text)

    if not url:
        await update.message.reply_text(
            "🤔 That doesn't look like a YouTube URL.\n"
            "Try something like `https://youtu.be/xxxxx`",
            parse_mode="Markdown",
        )
        return

    caption_override = _extract_caption(text, url)

    status_msg = await update.message.reply_text(
        "⏳ *Processing your video…*\n"
        "This may take a few minutes depending on video length.",
        parse_mode="Markdown",
    )

    try:
        output_path, raw_path, title = await _run_in_thread(url, caption_override)

        await status_msg.delete()

        with open(output_path, "rb") as video_file:
            await update.message.reply_video(
                video=video_file,
                caption=f"🎬 *{caption_override or title}*",
                parse_mode="Markdown",
                supports_streaming=True,
            )

        # ── Cleanup ──────────────────────────────────────────────────────────
        # 1. Remove specific files
        for path in [output_path, raw_path]:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    logger.info("Removed temporary file: %s", path)
            except Exception as e:
                logger.warning("Failed to remove temporary file %s: %s", path, e)

        # 2. Sweep directories (as requested: "remove all files from downloads and output")
        for folder in ["downloads", "output"]:
            try:
                if os.path.isdir(folder):
                    for filename in os.listdir(folder):
                        file_path = os.path.join(folder, filename)
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                    logger.info("Swept directory: %s", folder)
            except Exception as e:
                logger.warning("Failed to sweep directory %s: %s", folder, e)

    except Exception as exc:
        logger.exception("Pipeline failed for %s", url)
        error_msg = str(exc)
        
        # Friendly suggestion for common auth errors
        if "sign in" in error_msg.lower() or "bot" in error_msg.lower():
            hint = (
                "\n\n💡 *Hint:* YouTube is blocking the bot. Depending on your setup:\n"
                "1. Ensure you are logged into YouTube in Chrome or Firefox.\n"
                "2. If that fails, export your YouTube cookies to a `cookies.txt` "
                "file in the project folder."
            )
            error_msg += hint

        await status_msg.edit_text(
            f"❌ *Something went wrong!*\n\n`{error_msg}`",
            parse_mode="Markdown",
        )


# ── Application factory ───────────────────────────────────────────────────────

def build_app(token: str) -> Application:
    request = HTTPXRequest(
        read_timeout=60,
        write_timeout=60,
        connect_timeout=30,
        pool_timeout=60,
    )
    app = Application.builder().token(token).request(request).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app
