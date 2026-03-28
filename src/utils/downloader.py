"""
downloader.py
Downloads a YouTube video using yt-dlp and returns the local path + title.
If the video has already been downloaded (identified by its video ID), the
existing file is reused and no network download is performed.
"""
import os
import yt_dlp


def download_video(url: str, output_dir: str = "downloads") -> tuple[str, str]:
    """
    Download a YouTube video at the best available MP4 quality.

    If a file for the same video ID already exists in *output_dir* it will be
    reused without re-downloading.

    Returns:
        (local_filepath, video_title)
    """
    os.makedirs(output_dir, exist_ok=True)

    # ── Fetch metadata (no download) ──────────────────────────────────────────
    info_opts = {"quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(info_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        video_id = info.get("id", "video")
        title = info.get("title", "video")

    local_path = os.path.join(output_dir, f"{video_id}.mp4")

    # ── Return cached file if it already exists ───────────────────────────────
    if os.path.isfile(local_path):
        print(f"      [cache] Using already-downloaded file: {local_path}")
        return local_path, title

    # ── Download ──────────────────────────────────────────────────────────────
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(url, download=True)

    return local_path, title