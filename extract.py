# /// script
# requires-python = ">=3.10"
# dependencies = ["browser-cookie3>=0.20.1,<1", "httpx>=0.28,<1"]
# ///
import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent / "vendor"))
import browser_cookie3
import httpx
from bilibili_ai_subtitle.extractor import BilibiliAIExtractor, SubtitleError
from bilibili_ai_subtitle.formatter import render_srt


def stamp(n):
    n = int(n)
    return f"{n//3600:02d}:{n//60%60:02d}:{n%60:02d}"


def extract(source, browser, page):
    match = re.search(r"BV[A-Za-z0-9]{10}", source)
    if not match:
        url = re.search(r"https?://b23\.tv/[A-Za-z0-9]+", source)
        if not url:
            raise SubtitleError("请输入 BV 号、B站视频链接或 b23.tv 短链接。")
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            response = client.get(url.group(0))
            response.raise_for_status()
            if not (response.url.host == "bilibili.com" or response.url.host.endswith(".bilibili.com")):
                raise SubtitleError("短链接没有指向 B站视频。")
            source = str(response.url)
            match = re.search(r"BV[A-Za-z0-9]{10}", source)
        if not match:
            raise SubtitleError("短链接中未找到 BV 号。")
    bvid = match.group(0)
    urlmatch = re.search(r"https?://[^\s]+", source)
    if urlmatch and page == 1:
        try:
            page = int(parse_qs(urlparse(urlmatch.group(0)).query).get("p", ["1"])[0])
        except ValueError:
            pass
    if page < 1:
        raise SubtitleError("分P序号必须大于零。")
    session = os.environ.get("BILIBILI_SESSDATA") if browser == "app" else None
    if browser != "app":
        try:
            jar = getattr(browser_cookie3, browser)(domain_name=".bilibili.com")
            session = next((c.value for c in jar if c.name == "SESSDATA" and c.value), None)
        except Exception:
            raise SubtitleError(f"无法读取 {browser} 登录态。可切换到“应用内登录”，不需要访问浏览器文件或钥匙串。") from None
    if not session:
        raise SubtitleError("未找到登录态。请先在应用内登录 B站，或选择已登录的浏览器。")
    with BilibiliAIExtractor(session) as ex:
        nav = ex.client.get("https://api.bilibili.com/x/web-interface/nav", headers=ex._headers()).json()
        if not nav.get("data", {}).get("isLogin"):
            raise SubtitleError("B站登录已失效，请在所选浏览器重新登录后重试。")
        info = ex.get_video_info(bvid, page)
        tracks = ex._legacy_tracks(info)
        if not tracks:
            tracks = ex._protobuf_tracks(info)
        if not tracks:
            raise SubtitleError("本次接口未返回可用字幕。请检查播放器字幕菜单；本应用不会自动下载音视频或转写。")
        track = next((t for lang in ["ai-zh", "zh-CN", "zh-Hans", "zh"] for t in tracks if t.get("lan") == lang), tracks[0])
        url = track.get("subtitle_url", "")
        if url.startswith("//"):
            url = "https:" + url
        host = urlparse(url).hostname or ""
        if not url.startswith("https://") or not any(host == d or host.endswith("."+d) for d in ["bilibili.com", "hdslb.com", "biliimg.com"]):
            raise SubtitleError("字幕地址异常，已停止请求。")
        response = ex.client.get(url, headers=ex._headers())
        response.raise_for_status()
        segments = response.json().get("body") or []
        if not segments:
            raise SubtitleError("字幕文件为空，请稍后重试。")
        segments = [{"from": float(s["from"]), "to": float(s["to"]), "content": str(s["content"])} for s in segments]
    warnings = []
    duration = info["duration"] or 0
    if abs(duration - segments[-1]["to"]) > max(15, duration * .01):
        warnings.append("末条字幕与视频时长差距较大，可能有静音、片尾或缺失。")
    if segments[0]["from"] > 15:
        warnings.append("开头超过15秒没有字幕。")
    gaps = sum(b["from"] - a["to"] > 60 for a, b in zip(segments, segments[1:]))
    if gaps:
        warnings.append(f"存在 {gaps} 处超过60秒的字幕空档。")
    return {"ok": True, "title": info["title"], "bvid": bvid, "page": page,
            "source_url": f"https://www.bilibili.com/video/{bvid}/?p={page}",
            "count": len(segments), "duration": stamp(duration), "last": stamp(segments[-1]["to"]),
            "language": track.get("lan", ""),
            "notice": "B站 AI 自动生成字幕，未经人工逐字校对" if track.get("lan", "").startswith("ai-") else "B站现成字幕，未经本应用逐字校对",
            "warnings": warnings, "subtitles": segments,
            "text": "\n".join(f"[{stamp(s['from'])}] {s['content']}" for s in segments),
            "srt": render_srt(segments)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--browser", default="safari", choices=["app", "safari", "chrome", "edge", "firefox", "brave"])
    parser.add_argument("--page", default=1, type=int)
    args = parser.parse_args()
    try:
        result = extract(args.source, args.browser, args.page)
    except SubtitleError as error:
        result = {"ok": False, "error": str(error)}
    except httpx.HTTPError as error:
        status = getattr(getattr(error, "response", None), "status_code", None)
        result = {"ok": False, "error": f"B站请求失败（{type(error).__name__}，HTTP {status}），请检查网络后重试。"}
    except Exception as error:
        result = {"ok": False, "error": f"提取未完成（{type(error).__name__}），可能是接口变化或返回格式异常。"}
    print(json.dumps(result, ensure_ascii=False))
