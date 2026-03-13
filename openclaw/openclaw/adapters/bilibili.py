"""B站平台适配器。"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List

from openclaw.adapters.base import BasePlatformAdapter, _parse_time_window
from openclaw.models.types import VideoInfo


class BilibiliAdapter(BasePlatformAdapter):
    """B站视频适配器，支持 Cookie 登录和 CC 字幕优先获取。"""

    platform_name = "bilibili"

    async def fetch_video_list(
        self, target: str, time_window: str = "last_30_days", max_videos: int = 20
    ) -> List[VideoInfo]:
        """获取 B站博主视频列表。target 为博主主页 URL 或 UID。"""
        # 提取 UID
        uid_match = re.search(r"space\.bilibili\.com/(\d+)", target)
        uid = uid_match.group(1) if uid_match else target

        cutoff = _parse_time_window(time_window)

        # 使用 yt-dlp 获取视频列表（实际运行时需要 yt-dlp 安装）
        try:
            import yt_dlp
            ydl_opts = {
                "quiet": True,
                "extract_flat": True,
                "playlistend": max_videos * 2,  # 多取一些用于时间过滤
            }
            url = f"https://space.bilibili.com/{uid}/video"
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                entries = info.get("entries", []) if info else []
        except Exception:
            entries = []

        videos = []
        for entry in entries:
            if len(videos) >= max_videos:
                break
            try:
                pub_date = datetime.fromtimestamp(
                    entry.get("timestamp", 0), tz=timezone.utc
                )
                if cutoff and pub_date < cutoff:
                    continue
                videos.append(VideoInfo(
                    url=entry.get("url") or f"https://www.bilibili.com/video/{entry.get('id', '')}",
                    title=entry.get("title", ""),
                    creator=entry.get("uploader", uid),
                    platform="bilibili",
                    publish_date=pub_date,
                    view_count=entry.get("view_count", 0) or 0,
                ))
            except Exception:
                continue

        return videos

    async def search_creators(self, keyword: str, max_creators: int = 10) -> List[str]:
        """搜索 B站相关博主，返回主页 URL 列表。"""
        # 实际实现需要调用 B站搜索 API，此处返回空列表作为骨架
        return []
