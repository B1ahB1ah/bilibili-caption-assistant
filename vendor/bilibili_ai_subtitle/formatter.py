"""Output formatting for Bilibili subtitle segments."""

import json
import re
from pathlib import Path


def safe_filename(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|]", "-", value).strip(" .")
    return value or "bilibili-ai-subtitle"


def _timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    remaining = seconds % 60
    return f"{hours:02}:{minutes:02}:{remaining:06.3f}".replace(".", ",")


def render_srt(segments: list[dict]) -> str:
    blocks = []
    for index, segment in enumerate(segments, start=1):
        blocks.append(
            "\n".join(
                [
                    str(index),
                    f"{_timestamp(segment['from'])} --> {_timestamp(segment['to'])}",
                    segment["content"],
                ]
            )
        )
    return "\n\n".join(blocks) + "\n"


def render_text(segments: list[dict]) -> str:
    return "\n".join(segment["content"] for segment in segments) + "\n"


def render_json(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2) + "\n"


def render(result: dict, output_format: str) -> str:
    if output_format == "srt":
        return render_srt(result["subtitles"])
    if output_format == "txt":
        return render_text(result["subtitles"])
    if output_format == "json":
        return render_json(result)
    raise ValueError(f"unsupported output format: {output_format}")


def default_output_path(result: dict, output_format: str) -> Path:
    title = safe_filename(result["video_title"])
    return Path.cwd() / f"{title}.ai-zh.{output_format}"
