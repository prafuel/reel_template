"""
watermark.py
Adds a text watermark to a video using ffmpeg subprocess.
"""
import os
import tempfile
import subprocess


def add_watermark(
    input_path: str,
    output_path: str,
    watermark_text: str = "@goat.garp",
    font_size: int = 48,
    position: str = "bottom_right",
) -> str:
    """
    Burn a text watermark onto every frame of the video.

    Args:
        input_path:     Path to the source MP4.
        output_path:    Destination MP4 path.
        watermark_text: The text to render.
        font_size:      Font size in pixels.
        position:       One of 'bottom_right', 'bottom_left', 'top_right', 'top_left', 'center'.

    Returns:
        output_path
    """
    margin = 30

    position_map = {
        "bottom_right": f"x=(w-text_w-{margin}):y=(h-text_h-{margin})",
        "bottom_left":  f"x={margin}:y=(h-text_h-{margin})",
        "top_right":    f"x=(w-text_w-{margin}):y={margin}",
        "top_left":     f"x={margin}:y={margin}",
        "center":       f"x=(w-text_w)/2:y=(h-text_h)/2",
    }

    xy = position_map.get(position, position_map["bottom_right"])

    # Build the drawtext filter
    # - semi-transparent white text with a faint border for a watermark look
    drawtext = (
        f"drawtext="
        f"text='{watermark_text}':"
        f"fontsize={font_size}:"
        f"fontcolor=white@0.3:"
        f"borderw=2:"
        f"bordercolor=black@0.15:"
        f"{xy}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", drawtext,
        "-codec:a", "copy",
        "-preset", "fast",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg watermark failed:\n{result.stderr}")

    return output_path