"""DataStore 抽象基类。"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
from openclaw.models.types import VideoInfo, VideoStatus, TranscriptResult, VideoAnalysis


class BaseDataStore(ABC):
    @abstractmethod
    async def initialize(self) -> None:
        """初始化数据库（建表等）"""

    @abstractmethod
    async def save_video(self, video: VideoInfo, run_id: str) -> str:
        """保存视频信息，返回 video_id"""

    @abstractmethod
    async def get_video_status(self, url: str) -> Optional[VideoStatus]:
        """获取视频处理状态"""

    @abstractmethod
    async def update_video_status(self, url: str, status: VideoStatus, skipped_reason: Optional[str] = None) -> None:
        """更新视频处理状态"""

    @abstractmethod
    async def save_transcript(self, video_id: str, transcript: TranscriptResult) -> None:
        """保存转录结果"""

    @abstractmethod
    async def save_analysis(self, video_id: str, analysis: VideoAnalysis) -> None:
        """保存分析结果"""

    @abstractmethod
    async def save_insights(self, run_id: str, mode: str, target: str, result: dict) -> None:
        """保存聚合洞察"""

    @abstractmethod
    async def save_checkpoint(self, run_id: str, state: dict) -> None:
        """保存断点续传检查点"""

    @abstractmethod
    async def load_checkpoint(self, run_id: str) -> Optional[dict]:
        """加载断点续传检查点"""

    @abstractmethod
    async def is_cached(self, url: str, cache_ttl_hours: int) -> bool:
        """检查视频是否在缓存有效期内已分析"""

    @abstractmethod
    async def has_content_changed(self, url: str, publish_date: str, view_count: int) -> bool:
        """检测视频内容是否有变化"""
