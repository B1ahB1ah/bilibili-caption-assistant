"""Authenticated, metadata-only Bilibili AI subtitle extraction."""

import json
import os
import re
import urllib.parse
from collections.abc import Callable

import httpx

from .protobuf import parse_web_subtitle_response

API_BASE_URL = "https://api.bilibili.com"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
)


class SubtitleError(RuntimeError):
    """Base error for extraction failures."""


class NoAISubtitleError(SubtitleError):
    """The logged-in subtitle APIs contain no AI subtitle track."""


def extract_bvid(source: str) -> str:
    value = source.strip()
    if re.fullmatch(r"BV[a-zA-Z0-9]+", value, re.IGNORECASE):
        return value

    parsed = urllib.parse.urlparse(value)
    match = re.search(r"/video/(BV[a-zA-Z0-9]+)", parsed.path, re.IGNORECASE)
    if match:
        return match.group(1)
    raise SubtitleError(f"无法识别 B站 BV 号 / Cannot find a Bilibili BV id: {source}")


def _browser_readers() -> dict[str, Callable]:
    import browser_cookie3

    return {
        "chrome": browser_cookie3.chrome,
        "edge": browser_cookie3.edge,
        "firefox": browser_cookie3.firefox,
        "brave": browser_cookie3.brave,
    }


def get_sessdata(browser: str = "chrome") -> str:
    """Read only the Bilibili SESSDATA value and keep it in memory."""
    from_environment = os.environ.get("BILIBILI_SESSDATA")
    if from_environment:
        return from_environment

    readers = _browser_readers()
    names = list(readers) if browser == "auto" else [browser]
    if any(name not in readers for name in names):
        raise SubtitleError(f"不支持的浏览器 / Unsupported browser: {browser}")

    errors = []
    for name in names:
        try:
            jar = readers[name](domain_name=".bilibili.com")
            for cookie in jar:
                if cookie.name == "SESSDATA" and cookie.value:
                    return cookie.value
        except Exception as error:  # noqa: BLE001 - browser/keychain errors vary by platform
            errors.append(f"{name}: {type(error).__name__}")

    detail = f" ({', '.join(errors)})" if errors else ""
    raise SubtitleError(
        "未找到 B站 SESSDATA。请确认浏览器已登录；macOS 如弹出钥匙串提示请点允许。"
        "也可以临时设置 BILIBILI_SESSDATA 环境变量。"
        " / Bilibili SESSDATA was not found. Sign in with the selected browser, "
        f"approve the macOS Keychain prompt, or set BILIBILI_SESSDATA.{detail}"
    )


class BilibiliAIExtractor:
    """Extract AI subtitle tracks without downloading media."""

    def __init__(self, sessdata: str, client: httpx.Client | None = None):
        self.sessdata = sessdata
        self.client = client or httpx.Client(timeout=30.0, follow_redirects=True)
        self.client.cookies.set("SESSDATA", sessdata, domain=".bilibili.com")
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _headers(self, referer: str = "https://www.bilibili.com/") -> dict[str, str]:
        return {"User-Agent": USER_AGENT, "Referer": referer}

    def get_video_info(self, source: str, page: int = 1) -> dict:
        bvid = extract_bvid(source)
        response = self.client.get(
            f"{API_BASE_URL}/x/web-interface/view",
            params={"bvid": bvid},
            headers=self._headers(),
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            raise SubtitleError(f"B站视频信息接口失败: {payload.get('message', 'unknown')}")

        data = payload["data"]
        pages = data.get("pages") or []
        if page < 1 or (pages and page > len(pages)):
            raise SubtitleError(f"分P编号超出范围 / Page is out of range: {page}")

        selected = pages[page - 1] if pages else {}
        cid = selected.get("cid") or data.get("cid")
        if not cid:
            raise SubtitleError("视频信息中缺少 cid / Video metadata has no cid")

        title = data.get("title") or bvid
        if len(pages) > 1 and selected.get("part"):
            title = f"{title} - P{page} {selected['part']}"

        return {
            "bvid": data.get("bvid") or bvid,
            "aid": data.get("aid"),
            "cid": cid,
            "title": title,
            "duration": selected.get("duration") or data.get("duration"),
            "page": page,
        }

    def _legacy_tracks(self, info: dict) -> list[dict]:
        response = self.client.get(
            f"{API_BASE_URL}/x/player/wbi/v2",
            params={"bvid": info["bvid"], "cid": info["cid"]},
            headers=self._headers(f"https://www.bilibili.com/video/{info['bvid']}"),
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            return []
        return payload.get("data", {}).get("subtitle", {}).get("subtitles", [])

    def _protobuf_tracks(self, info: dict) -> list[dict]:
        response = self.client.get(
            f"{API_BASE_URL}/x/v2/subtitle/web/view",
            params={
                "oid": info["cid"],
                "pid": info["aid"],
                "context_ext": json.dumps({"video_type": 1}, separators=(",", ":")),
                "type": 1,
                "cur_production_type": 0,
                "preferred_language": "ai-zh",
                "playlist_switch": 0,
            },
            headers={
                **self._headers(f"https://www.bilibili.com/video/{info['bvid']}"),
                "Accept": "application/octet-stream",
            },
        )
        response.raise_for_status()
        try:
            return parse_web_subtitle_response(response.content)
        except (UnicodeDecodeError, ValueError) as error:
            raise SubtitleError(f"B站 Protobuf 字幕元数据解析失败: {error}") from error

    def list_ai_tracks(self, source: str, page: int = 1) -> tuple[dict, list[dict]]:
        info = self.get_video_info(source, page)
        tracks = self._legacy_tracks(info)
        if not tracks:
            tracks = self._protobuf_tracks(info)
        ai_tracks = [track for track in tracks if str(track.get("lan", "")).startswith("ai-")]
        return info, ai_tracks

    def extract(self, source: str, page: int = 1, language: str = "ai-zh") -> dict:
        info, tracks = self.list_ai_tracks(source, page)
        if not tracks:
            raise NoAISubtitleError(
                "登录态接口中没有 AI 字幕。请先确认播放器字幕菜单确实出现“中文 AI”。"
                "本工具不会下载视频或启动 ASR。"
                " / No AI subtitle track was returned. Confirm the player shows an AI caption option. "
                "This tool will not download media or start ASR."
            )

        track = next((item for item in tracks if item.get("lan") == language), tracks[0])
        subtitle_url = track.get("subtitle_url")
        if not subtitle_url:
            raise SubtitleError("AI 字幕轨道缺少下载地址 / AI track has no subtitle URL")
        if subtitle_url.startswith("//"):
            subtitle_url = "https:" + subtitle_url

        response = self.client.get(
            subtitle_url,
            headers=self._headers(f"https://www.bilibili.com/video/{info['bvid']}"),
        )
        response.raise_for_status()
        payload = response.json()
        body = payload.get("body") or []
        if not body:
            raise SubtitleError("字幕文件为空 / Subtitle body is empty")

        subtitles = [
            {
                "from": float(item.get("from", 0)),
                "to": float(item.get("to", 0)),
                "content": str(item.get("content", "")),
            }
            for item in body
        ]
        return {
            "source": "bilibili_ai_subtitle_api",
            "format": "json",
            "language": track.get("lan"),
            "language_name": track.get("lan_doc"),
            "subtitle_count": len(subtitles),
            "video_title": info["title"],
            "bvid": info["bvid"],
            "aid": info["aid"],
            "cid": info["cid"],
            "page": info["page"],
            "subtitles": subtitles,
        }
