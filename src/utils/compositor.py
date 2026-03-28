"""
compositor.py
Composites a watermarked video into the 9:16 Instagram template.

Template layout (1080x1920):
  Rows   0 – 435  : Header (logo + @goat.garp)
  Row  ~436        : Divider line
  Rows 437 – 546  : Caption zone  (height 109px)
  Row  ~547        : Divider line
  Rows 760 – 1336 : Video zone    (576px tall × 1080px wide, matches 16:9)
  Row ~1337        : Divider line
  Rows 1342 – 1920: Bottom zone
"""
import os
import textwrap
import subprocess


# ── Template zone constants (pixels) ──────────────────────────────────────────
# TEMPLATE_W = 1080
# TEMPLATE_H = 1920


# CAPTION_X = 40
# CAPTION_Y = 437
# CAPTION_W = TEMPLATE_W - 80  # leave 40 px margin each side
# CAPTION_H = 109

# FONT_SIZE_CAPTION = 42

TEMPLATE_W = 1080
TEMPLATE_H = 1920

VIDEO_X = 0
VIDEO_Y = 760
VIDEO_W = 1080
VIDEO_H = 576

CAPTION_X = 40
CAPTION_Y = 600
CAPTION_W = TEMPLATE_W - 80
CAPTION_H = 60       # tighter zone, single line caption

FONT_SIZE_CAPTION = 38
# ──────────────────────────────────────────────────────────────────────────────

def _wrap_text(text: str, max_chars: int = 38) -> list[str]:
    """Wrap text into lines that fit within the caption zone."""
    wrapped = textwrap.wrap(text, width=max_chars)
    return wrapped[:3]  # max 3 lines


def _build_caption_filter(
    lines: list[str],
    caption_x: int,
    caption_y: int,
    caption_w: int,
    caption_h: int,
    fontsize: int,
) -> str:
    """Build stacked drawtext filters, one per line."""
    line_height = fontsize + 8  # a bit of leading
    total_h = len(lines) * line_height
    y_start = caption_y + (caption_h - total_h) // 2  # vertically centred block

    filters = []
    for i, line in enumerate(lines):
        escaped = (
            line
            .replace("\\", "\\\\")
            .replace("'",  "\\'")
            .replace(":",  "\\:")
        )
        y = y_start + i * line_height
        filters.append(
            f"drawtext=text='{escaped}'"
            f":fontsize={fontsize}"
            f":fontcolor=white"
            f":borderw=2"
            f":bordercolor=black@0.5"
            f":x=({caption_x}+(({caption_w}-text_w)/2))"
            f":y={y}"
        )
    return ",".join(filters)


def composite_video(
    watermarked_video: str,
    template_path: str,
    caption: str,
    output_path: str,
) -> str:
    lines = _wrap_text(caption)

    caption_filter = _build_caption_filter(
        lines,
        caption_x=CAPTION_X,
        caption_y=CAPTION_Y,
        caption_w=CAPTION_W,
        caption_h=CAPTION_H,
        fontsize=FONT_SIZE_CAPTION,
    )

    filter_complex = (
        f"[1:v]scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=decrease,"
        f"pad={VIDEO_W}:{VIDEO_H}:(ow-iw)/2:(oh-ih)/2:black[scaled];"
        f"[0:v][scaled]overlay={VIDEO_X}:{VIDEO_Y},"
        f"{caption_filter}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", template_path,
        "-i", watermarked_video,
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "1:a?",
        "-shortest",
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264",
        "-preset", "fast",
        "-movflags", "+faststart",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg composite failed:\n{result.stderr}")

    return output_path