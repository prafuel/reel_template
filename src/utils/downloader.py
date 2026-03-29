# """
# downloader.py
# Downloads a YouTube video using yt-dlp and returns the local path + title.
# If the video has already been downloaded (identified by its video ID), the
# existing file is reused and no network download is performed.
# """
# import os
# import yt_dlp


# def download_video(url: str, output_dir: str = "downloads") -> tuple[str, str]:
#     """
#     Download a YouTube video at the best available MP4 quality.

#     If a file for the same video ID already exists in *output_dir* it will be
#     reused without re-downloading.

#     Returns:
#         (local_filepath, video_title)
#     """
#     os.makedirs(output_dir, exist_ok=True)

#     # ── Fetch metadata (no download) ──────────────────────────────────────────
#     info_opts = {"quiet": True, "no_warnings": True}
#     with yt_dlp.YoutubeDL(info_opts) as ydl:
#         info = ydl.extract_info(url, download=False)
#         video_id = info.get("id", "video")
#         title = info.get("title", "video")

#     local_path = os.path.join(output_dir, f"{video_id}.mp4")

#     # ── Return cached file if it already exists ───────────────────────────────
#     if os.path.isfile(local_path):
#         print(f"      [cache] Using already-downloaded file: {local_path}")
#         return local_path, title

#     # ── Download ──────────────────────────────────────────────────────────────
#     ydl_opts = {
#         "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
#         "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
#         "merge_output_format": "mp4",
#         "quiet": True,
#         "no_warnings": True,
#     }

#     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#         ydl.extract_info(url, download=True)

#     return local_path, title

# ==========================================================


# import os
# import yt_dlp


# def download_video(url: str, output_dir: str = "downloads") -> tuple[str, str]:
#     """
#     Download a YouTube video at the best available quality.

#     Returns:
#         (local_filepath, video_title)
#     """
#     os.makedirs(output_dir, exist_ok=True)

#     # ── AUTH CONFIG (REQUIRED FOR YOUTUBE NOW) ────────────────────────────────
#     # Use ONE of the below:

#     # ✅ Local dev (works only if browser is available)
#     # cookies_config = {
#     #     "cookiesfrombrowser": ("firefox",),  # or ("firefox",)
#     # }

#     # ❗ For server / docker, use this instead:
#     cookies_config = {
#         "cookiefile": "cookies.txt",
#     }

#     # ── Fetch metadata (no download) ──────────────────────────────────────────
#     info_opts = {
#         "quiet": True,
#         "no_warnings": True,
#         "ignoreerrors": False,
#         **cookies_config,
#     }

#     with yt_dlp.YoutubeDL(info_opts) as ydl:
#         info = ydl.extract_info(url, download=False)

#         if info is None:
#             raise RuntimeError("Failed to extract video info")

#         video_id = info.get("id", "video")
#         title = info.get("title", "video")

#     local_path = os.path.join(output_dir, f"{video_id}.mp4")

#     # ── Return cached file if it already exists ───────────────────────────────
#     if os.path.isfile(local_path):
#         print(f"[cache] Using already-downloaded file: {local_path}")
#         return local_path, title

#     # ── Download ──────────────────────────────────────────────────────────────
#     ydl_opts = {
#         # ✅ Modern resilient format selection (DON'T over-filter)
#         "format": "bestvideo+bestaudio/best",

#         # Output
#         "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
#         "merge_output_format": "mp4",

#         # Stability improvements
#         "format_sort": ["res", "fps", "codec:avc:m4a"],
#         "retries": 3,
#         "fragment_retries": 3,

#         # Logging
#         "quiet": True,
#         "no_warnings": True,

#         # 🔑 Required for YouTube auth
#         **cookies_config,
#     }

#     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#         ydl.extract_info(url, download=True)

#     return local_path, title

# =====================================================================

"""
downloader.py

Robust YouTube downloader using yt-dlp.
Handles:
- Bot detection (cookies + headers)
- Format inconsistencies
- Retry/fallback strategy
"""

import os
import yt_dlp


def download_video(url: str, output_dir: str = "downloads") -> tuple[str, str]:
    os.makedirs(output_dir, exist_ok=True)

    # ── AUTH CONFIG ───────────────────────────────────────────────────────────
    # Use ONE (switch for server)
    cookies_config = {
        "cookiefile": "cookies.txt",  # ✅ USE THIS for reliability
        # "cookiesfrombrowser": ("chrome",),
    }

    # ── COMMON HEADERS (CRITICAL) ─────────────────────────────────────────────
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }

    # ── STEP 1: METADATA ──────────────────────────────────────────────────────
    info_opts = {
        "quiet": True,
        "no_warnings": True,
        "http_headers": headers,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"]  # 🔥 bypass restrictions
            }
        },
        **cookies_config,
    }

    with yt_dlp.YoutubeDL(info_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        if not info:
            raise RuntimeError("Failed to extract video info")

        video_id = info.get("id", "video")
        title = info.get("title", "video")

    local_path = os.path.join(output_dir, f"{video_id}.mp4")

    # ── CACHE ────────────────────────────────────────────────────────────────
    if os.path.isfile(local_path):
        print(f"[cache] Using existing file: {local_path}")
        return local_path, title

    # ── DOWNLOAD STRATEGIES (IMPORTANT) ───────────────────────────────────────
    format_strategies = [
        "bv*+ba/b",          # best separate streams
        "best",              # fallback combined
        "b",                 # ultra fallback (almost always works)
    ]

    last_error = None

    for fmt in format_strategies:
        try:
            ydl_opts = {
                "format": fmt,
                "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
                "merge_output_format": "mp4",

                # Stability
                "retries": 3,
                "fragment_retries": 3,

                # Headers + anti-bot
                "http_headers": headers,
                "extractor_args": {
                    "youtube": {
                        "player_client": ["android", "web"]
                    }
                },

                "quiet": True,
                "no_warnings": True,

                **cookies_config,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)

            return local_path, title

        except Exception as e:
            last_error = e
            print(f"[retry] Format '{fmt}' failed, trying next...")

    # ── FAIL HARD ────────────────────────────────────────────────────────────
    raise RuntimeError(f"All download strategies failed: {last_error}")