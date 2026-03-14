"""TranscriptGenerator — 转录生成模块。"""
from __future__ import annotations

import logging
import re
from typing import List, Optional

from openclaw.models.types import DownloadResult, TimestampedSegment, TranscriptResult

logger = logging.getLogger(__name__)


class TranscriptGenerator:
    """将下载结果转录为带时间戳的文本。"""

    def __init__(self, whisper_model: str = "base", device: str = "cpu"):
        self._whisper_model_name = whisper_model
        self._device = device
        self._whisper = None  # 延迟加载

    async def transcribe(self, download_result: DownloadResult) -> TranscriptResult:
        """根据下载结果生成转录文本。"""
        if download_result.method == "subtitle" and download_result.subtitle_text:
            return self._from_subtitle_text(download_result)

        if download_result.method == "audio" and download_result.file_path:
            return await self._from_audio(download_result)

        # skipped 或无内容
        return TranscriptResult(
            video_id=download_result.video_id,
            segments=[],
            full_text="",
        )

    def _from_subtitle_text(self, result: DownloadResult) -> TranscriptResult:
        """从字幕文本构建 TranscriptResult（无精确时间戳）。"""
        text = result.subtitle_text or ""
        segment = TimestampedSegment(start=0.0, end=0.0, text=text)
        return TranscriptResult(
            video_id=result.video_id,
            segments=[segment],
            full_text=text,
        )

    async def _from_audio(self, result: DownloadResult) -> TranscriptResult:
        """使用 faster-whisper 转录音频文件。"""
        try:
            from faster_whisper import WhisperModel

            if self._whisper is None:
                self._whisper = WhisperModel(
                    self._whisper_model_name, device=self._device, compute_type="int8"
                )

            segments_raw, _ = self._whisper.transcribe(
                result.file_path, beam_size=5, language="zh"
            )
            segments: List[TimestampedSegment] = []
            full_parts: List[str] = []
            for seg in segments_raw:
                segments.append(TimestampedSegment(
                    start=seg.start, end=seg.end, text=seg.text.strip()
                ))
                full_parts.append(seg.text.strip())

            return TranscriptResult(
                video_id=result.video_id,
                segments=segments,
                full_text=" ".join(full_parts),
            )
        except Exception as e:
            logger.error(f"[transcriber] Whisper 转录失败: {e}")
            return TranscriptResult(
                video_id=result.video_id,
                segments=[],
                full_text="",
            )
