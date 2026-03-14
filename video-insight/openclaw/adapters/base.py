"""平台适配器基类和路由器。"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Type

from openclaw.models.types import VideoInfo


class BasePlatformAdapter(ABC):
    """平台适配器抽象基类。"""

    platform_name: str = ""

    def __init__(self, access_manager=None):
        self._access_manager = access_manager

    @abstractmethod
    async def fetch_video_list(
        self, target: str, time_window: str = "last_30_days", max_videos: int = 20
    ) -> List[VideoInfo]:
        """获取博主视频列表。"""

    @abstractmethod
    async def search_creators(
        self, keyword: str, max_creators: int = 10
    ) -> List[str]:
        """搜索相关博主，返回博主 URL 列表（Mode2）。"""


def _parse_time_window(time_window: str) -> Optional[object]:
    """解析时间窗口，返回起始时间（datetime）。"""
    from datetime import datetime, timezone, timedelta

    if time_window.startswith("last_"):
        match = re.match(r"last_(\d+)_days", time_window)
        if match:
            days = int(match.group(1))
            return datetime.now(timezone.utc) - timedelta(days=days)
    elif "~" in time_window:
        start_str = time_window.split("~")[0].strip()
        try:
            return datetime.fromisoformat(start_str).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


class PlatformRouter:
    """根据 URL 自动识别平台并路由到对应适配器。"""

    PLATFORM_PATTERNS: Dict[str, str] = {
        "bilibili": r"bilibili\.com|b23\.tv",
        "douyin": r"douyin\.com|iesdouyin\.com",
        "youtube": r"youtube\.com|youtu\.be",
        "xiaohongshu": r"xiaohongshu\.com|xhslink\.com",
    }

    def __init__(self, access_manager=None):
        self._access_manager = access_manager
        self._adapters: Dict[str, BasePlatformAdapter] = {}

    def _get_adapter(self, platform: str) -> BasePlatformAdapter:
        if platform not in self._adapters:
            from openclaw.adapters.bilibili import BilibiliAdapter
            from openclaw.adapters.douyin import DouyinAdapter
            from openclaw.adapters.youtube import YouTubeAdapter
            from openclaw.adapters.xiaohongshu import XiaohongshuAdapter

            adapter_map: Dict[str, Type[BasePlatformAdapter]] = {
                "bilibili": BilibiliAdapter,
                "douyin": DouyinAdapter,
                "youtube": YouTubeAdapter,
                "xiaohongshu": XiaohongshuAdapter,
            }
            cls = adapter_map[platform]
            self._adapters[platform] = cls(self._access_manager)
        return self._adapters[platform]

    def detect_platform(self, url: str) -> str:
        """根据 URL 识别平台名称。"""
        for platform, pattern in self.PLATFORM_PATTERNS.items():
            if re.search(pattern, url, re.IGNORECASE):
                return platform
        raise ValueError(
            f"不支持的平台 URL：{url}。支持的平台：{list(self.PLATFORM_PATTERNS.keys())}"
        )

    def get_adapter(self, url: str) -> BasePlatformAdapter:
        """根据 URL 返回对应平台适配器实例。"""
        platform = self.detect_platform(url)
        return self._get_adapter(platform)

    def resolve_platforms(self, platform_names: List[str]) -> List[BasePlatformAdapter]:
        """根据平台名称列表返回适配器实例列表（Mode2）。"""
        adapters = []
        for name in platform_names:
            name_lower = name.lower()
            if name_lower not in self.PLATFORM_PATTERNS:
                raise ValueError(
                    f"不支持的平台：{name}。支持的平台：{list(self.PLATFORM_PATTERNS.keys())}"
                )
            adapters.append(self._get_adapter(name_lower))
        return adapters
