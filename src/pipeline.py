"""
pipeline.py
Reusable entry-point for the YouTube → Instagram Reel pipeline.
Called by both main.py (CLI) and bot.py (Telegram).
"""
import os
import tempfile
import shutil

from src.utils.downloader import download_video
from src.utils.watermark import add_watermark
from src.utils.compositor import composite_video

DEFAULT_TEMPLATE = os.path.join(
    os.path.dirname(__file__), "templates", "dark.png"
)
DEFAULT_WATERMARK = "@goat.garp"
OUTPUT_DIR = "output"


def run_pipeline(
    url: str,
    caption_override: str | None = None,
    watermark: str = DEFAULT_WATERMARK,
    template: str = DEFAULT_TEMPLATE,
    output_dir: str = OUTPUT_DIR,
) -> tuple[str, str]:
    """
    Run the full pipeline for a YouTube URL.

    Returns:
        (output_path, title)
    """
    # ── 1. Download (cached if already present) ───────────────────────────────
    print(f"[1/3] Downloading: {url}")
    raw_path, title = download_video(url)
    caption = caption_override or title
    print(f"      Title : {title}")
    print(f"      Saved : {raw_path}")

    # ── 2. Paths ──────────────────────────────────────────────────────────────
    video_id = os.path.splitext(os.path.basename(raw_path))[0]
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{video_id}_reel.mp4")

    tmp_dir = tempfile.mkdtemp(prefix="clipping_")
    watermarked_path = os.path.join(tmp_dir, f"{video_id}_wm.mp4")

    try:
        # ── 3. Watermark ──────────────────────────────────────────────────────
        print(f"[2/3] Adding watermark: {watermark}")
        add_watermark(raw_path, watermarked_path, watermark_text=watermark)

        # ── 4. Composite ──────────────────────────────────────────────────────
        print(f"[3/3] Compositing …  Caption: {caption}")
        composite_video(
            watermarked_video=watermarked_path,
            template_path=template,
            caption=caption,
            output_path=output_path,
        )
        print(f"✅ Done: {output_path}")
        return output_path, title

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
