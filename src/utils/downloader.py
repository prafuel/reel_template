"""
downloader.py
Robust YouTube downloader using yt-dlp.
Handles:
- Bot detection (cookies.txt or browser fallback)
- Anti-bot headers + android player client
- Format retry strategy
- File caching by video ID
"""
import os
import yt_dlp

COOKIES_FILE = "cookies.txt"

# Browsers to try in order when cookies.txt is not available
_BROWSERS = ["chrome", "firefox", "chromium", "brave"]

# Common desktop user-agent to reduce bot-detection false positives
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


def _cookies_config() -> dict:
    """Return the best available cookie authentication config."""
    if os.path.isfile(COOKIES_FILE):
        print(f"      [auth] Using cookies file: {COOKIES_FILE}")
        return {"cookiefile": COOKIES_FILE}
    for browser in _BROWSERS:
        try:
            # Quick probe — raises if browser profile not found
            with yt_dlp.YoutubeDL({"quiet": True, "cookiesfrombrowser": (browser,)}) as ydl:
                pass
            print(f"      [auth] Using cookies from browser: {browser}")
            return {"cookiesfrombrowser": (browser,)}
        except Exception:
            continue
    print("      [auth] No cookies available — proceeding unauthenticated")
    return {}


def download_video(url: str, output_dir: str = "downloads") -> tuple[str, str]:
    """
    Download a YouTube video at the best available quality.

    If a file for the same video ID already exists in *output_dir* it will be
    reused without re-downloading.

    Returns:
        (local_filepath, video_title)
    """
    os.makedirs(output_dir, exist_ok=True)

    auth = _cookies_config()

    common_opts = {
        "quiet": True,
        "no_warnings": True,
        "http_headers": {"User-Agent": _UA},
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
            }
        },
        **auth,
    }

    # ── Fetch metadata (no download) ──────────────────────────────────────────
    with yt_dlp.YoutubeDL(common_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            raise RuntimeError("Failed to extract video info")
        video_id = info.get("id", "video")
        title = info.get("title", "video")
        # Strip accidental "NA" prefix left by some extractors
        if title.startswith("NA "):
            title = title[3:]

    local_path = os.path.join(output_dir, f"{video_id}.mp4")

    # ── Return cached file if it already exists ───────────────────────────────
    if os.path.isfile(local_path):
        print(f"      [cache] Using already-downloaded file: {local_path}")
        return local_path, title

    # ── Download with format fallback ─────────────────────────────────────────
    format_strategies = [
        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",  # best quality
        "bv*+ba/b",                                               # best streams
        "best",                                                   # combined
        "b",                                                      # last resort
    ]

    last_error: Exception | None = None
    for fmt in format_strategies:
        try:
            ydl_opts = {
                **common_opts,
                "format": fmt,
                "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
                "merge_output_format": "mp4",
                "retries": 3,
                "fragment_retries": 3,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)
            return local_path, title
        except Exception as exc:
            last_error = exc
            print(f"      [retry] Format '{fmt}' failed: {exc}")

    raise RuntimeError(f"All download strategies failed: {last_error}")
