"""小红书平台适配器。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from openclaw.adapters.base import BasePlatformAdapter, _parse_time_window
from openclaw.models.types import VideoInfo


class XiaohongshuAdapter(BasePlatformAdapter):
    """小红书视频适配器，支持 Cookie 登录，建议配合代理使用。"""

    platform_name = "xiaohongshu"

    async def fetch_video_list(
        self, target: str, time_window: str = "last_30_days", max_videos: int = 20
    ) -> List[VideoInfo]:
        """获取小红书博主视频列表。"""
        cutoff = _parse_time_window(time_window)

        try:
            import yt_dlp
            ydl_opts = {"quiet": True, "extract_flat": True, "playlistend": max_videos * 2}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(target, download=False)
                entries = info.get("entries", []) if info else []
        except Exception:
            entries = []

        videos = []
        for entry in entries:
            if len(videos) >= max_videos:
                break
            try:
                pub_date = datetime.fromtimestamp(entry.get("timestamp", 0), tz=timezone.utc)
                if cutoff and pub_date < cutoff:
                    continue
                videos.append(VideoInfo(
                    url=entry.get("url", ""),
                    title=entry.get("title", ""),
                    creator=entry.get("uploader", ""),
                    platform="xiaohongshu",
                    publish_date=pub_date,
                    view_count=entry.get("view_count", 0) or 0,
                ))
            except Exception:
                continue
        return videos

    async def search_creators(self, keyword: str, max_creators: int = 10) -> List[str]:
        return []
