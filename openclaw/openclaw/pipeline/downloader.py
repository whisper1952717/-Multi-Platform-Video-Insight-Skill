"""VideoDownloader — 视频下载模块，实现降级策略链。"""
from __future__ import annotations

import logging
import os
import tempfile
from typing import Optional

from openclaw.models.types import DownloadResult, VideoInfo

logger = logging.getLogger(__name__)


class VideoDownloader:
    """视频下载模块，降级策略链：字幕 → 音频 → 跳过。"""

    def __init__(self, download_dir: str = "./data/downloads", access_manager=None):
        self._download_dir = download_dir
        self._access_manager = access_manager
        os.makedirs(download_dir, exist_ok=True)

    async def download(self, video: VideoInfo) -> DownloadResult:
        """执行降级策略链，返回 DownloadResult。"""
        video_id = _url_to_id(video.url)

        # 1. 尝试获取字幕
        subtitle_text = await self._fetch_subtitle(video)
        if subtitle_text:
            logger.info(f"[downloader] 字幕获取成功: {video.url}")
            return DownloadResult(
                video_id=video_id,
                method="subtitle",
                subtitle_text=subtitle_text,
            )

        # 2. 降级：下载音频
        audio_path = await self._download_audio(video)
        if audio_path:
            logger.info(f"[downloader] 音频下载成功: {video.url}")
            return DownloadResult(
                video_id=video_id,
                method="audio",
                file_path=audio_path,
            )

        # 3. 跳过
        reason = f"字幕和音频均获取失败: {video.url}"
        logger.warning(f"[downloader] 跳过视频: {reason}")
        return DownloadResult(
            video_id=video_id,
            method="skipped",
            skipped_reason=reason,
        )

    async def _fetch_subtitle(self, video: VideoInfo) -> Optional[str]:
        """通过 yt-dlp 获取字幕文件内容。B站优先 CC 字幕。"""
        try:
            import yt_dlp

            subtitle_langs = ["zh-Hans", "zh", "en"]
            if video.platform == "bilibili":
                subtitle_langs = ["zh", "zh-Hans", "en"]

            with tempfile.TemporaryDirectory() as tmpdir:
                ydl_opts = {
                    "quiet": True,
                    "skip_download": True,
                    "writesubtitles": True,
                    "writeautomaticsub": True,
                    "subtitleslangs": subtitle_langs,
                    "subtitlesformat": "vtt",
                    "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
                }
                # 添加 Cookie（如果有）
                if self._access_manager:
                    cookie_path = self._access_manager.get_cookie_path(video.platform)
                    if cookie_path:
                        ydl_opts["cookiefile"] = cookie_path

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video.url])

                # 查找生成的字幕文件
                for fname in os.listdir(tmpdir):
                    if fname.endswith(".vtt") or fname.endswith(".srt"):
                        fpath = os.path.join(tmpdir, fname)
                        content = open(fpath, encoding="utf-8").read()
                        return _parse_subtitle(content)
        except Exception as e:
            logger.debug(f"[downloader] 字幕获取失败: {e}")
        return None

    async def _download_audio(self, video: VideoInfo) -> Optional[str]:
        """通过 yt-dlp 下载音频文件，返回文件路径。"""
        try:
            import yt_dlp

            out_path = os.path.join(self._download_dir, f"{_url_to_id(video.url)}.%(ext)s")
            ydl_opts = {
                "quiet": True,
                "format": "bestaudio/best",
                "outtmpl": out_path,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "128",
                }],
            }
            if self._access_manager:
                cookie_path = self._access_manager.get_cookie_path(video.platform)
                if cookie_path:
                    ydl_opts["cookiefile"] = cookie_path

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video.url, download=True)
                if info:
                    final_path = os.path.join(
                        self._download_dir, f"{_url_to_id(video.url)}.mp3"
                    )
                    if os.path.exists(final_path):
                        return final_path
        except Exception as e:
            logger.debug(f"[downloader] 音频下载失败: {e}")
        return None


def _url_to_id(url: str) -> str:
    """从 URL 生成简短 ID。"""
    import hashlib
    return hashlib.md5(url.encode()).hexdigest()[:16]


def _parse_subtitle(content: str) -> str:
    """解析 VTT/SRT 字幕文件，提取纯文本。"""
    import re
    # 去除 VTT 头部
    lines = content.split("\n")
    text_lines = []
    for line in lines:
        line = line.strip()
        # 跳过时间戳行、WEBVTT 头、空行、序号
        if not line:
            continue
        if line.startswith("WEBVTT") or line.startswith("NOTE"):
            continue
        if re.match(r"^\d+$", line):
            continue
        if re.match(r"[\d:,\. ]+ --> [\d:,\. ]+", line):
            continue
        # 去除 HTML 标签
        line = re.sub(r"<[^>]+>", "", line)
        if line:
            text_lines.append(line)
    return " ".join(text_lines)
