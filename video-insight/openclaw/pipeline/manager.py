"""AsyncPipelineManager — 异步并发流水线调度器。"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Dict, List, Optional

from openclaw.models.types import VideoAnalysis, VideoInfo, VideoStatus
from openclaw.pipeline.downloader import VideoDownloader
from openclaw.pipeline.transcriber import TranscriptGenerator
from openclaw.pipeline.cleaner import TranscriptCleaner
from openclaw.pipeline.segmenter import VideoSegmenter
from openclaw.pipeline.classifier import TopicClassifier
from openclaw.pipeline.analyzer import VideoAnalyzer

logger = logging.getLogger(__name__)


class AsyncPipelineManager:
    """异步并发调度器，管理视频处理流水线。"""

    def __init__(
        self,
        downloader: VideoDownloader,
        transcriber: TranscriptGenerator,
        cleaner: TranscriptCleaner,
        segmenter: VideoSegmenter,
        classifier: TopicClassifier,
        analyzer: VideoAnalyzer,
        datastore=None,
        monitor=None,
        max_concurrency: int = 3,
        cache_enabled: bool = True,
        cache_ttl_hours: int = 72,
    ):
        self._downloader = downloader
        self._transcriber = transcriber
        self._cleaner = cleaner
        self._segmenter = segmenter
        self._classifier = classifier
        self._analyzer = analyzer
        self._datastore = datastore
        self._monitor = monitor
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._cache_enabled = cache_enabled
        self._cache_ttl_hours = cache_ttl_hours
        self._run_id = str(uuid.uuid4())

    async def process_single_creator(
        self, videos: List[VideoInfo]
    ) -> List[VideoAnalysis]:
        """Mode1：串行处理单博主视频列表。"""
        results = []
        for video in videos:
            result = await self._process_video(video)
            if result:
                results.append(result)
        return results

    async def process_multi_creators(
        self, creator_videos: Dict[str, List[VideoInfo]]
    ) -> List[VideoAnalysis]:
        """Mode2：并行处理多博主，每博主内部串行。"""
        tasks = [
            self._process_creator_with_semaphore(creator, videos)
            for creator, videos in creator_videos.items()
        ]
        results_nested = await asyncio.gather(*tasks, return_exceptions=True)
        results = []
        for r in results_nested:
            if isinstance(r, Exception):
                logger.error(f"[manager] 博主处理失败: {r}")
            elif isinstance(r, list):
                results.extend(r)
        return results

    async def _process_creator_with_semaphore(
        self, creator: str, videos: List[VideoInfo]
    ) -> List[VideoAnalysis]:
        """带信号量的博主处理（Mode2 并发控制）。"""
        async with self._semaphore:
            logger.info(f"[manager] 开始处理博主: {creator}，共 {len(videos)} 个视频")
            return await self.process_single_creator(videos)

    async def _process_video(self, video: VideoInfo) -> Optional[VideoAnalysis]:
        """单视频完整处理流水线：下载→转录→清洗→分段→分类→分析。"""
        # 检查缓存
        if self._cache_enabled and self._datastore:
            if await self._datastore.is_cached(video.url, self._cache_ttl_hours):
                logger.info(f"[manager] 缓存命中，跳过: {video.url}")
                if self._monitor:
                    self._monitor.video_skipped("缓存命中")
                return None

        # 保存视频信息
        video_id = video.url
        if self._datastore:
            video_id = await self._datastore.save_video(video, self._run_id)

        try:
            # 1. 下载
            if self._monitor:
                self._monitor.step_start("download", video.url)
            download_result = await self._downloader.download(video)
            if self._monitor:
                self._monitor.step_end("download", platform=video.platform)

            if download_result.method == "skipped":
                if self._datastore:
                    await self._datastore.update_video_status(
                        video.url, VideoStatus.SKIPPED, download_result.skipped_reason
                    )
                if self._monitor:
                    self._monitor.video_skipped(download_result.skipped_reason or "")
                return None

            # 保存检查点
            if self._datastore:
                await self._datastore.update_video_status(video.url, VideoStatus.DOWNLOADED)
                await self._datastore.save_checkpoint(self._run_id, {"last_url": video.url, "step": "downloaded"})

            # 2. 转录
            if self._monitor:
                self._monitor.step_start("transcribe", video.url)
            transcript = await self._transcriber.transcribe(download_result)
            if self._monitor:
                self._monitor.step_end("transcribe")

            if not transcript.full_text:
                if self._datastore:
                    await self._datastore.update_video_status(video.url, VideoStatus.SKIPPED, "转录结果为空")
                if self._monitor:
                    self._monitor.video_skipped("转录结果为空")
                return None

            if self._datastore:
                await self._datastore.save_transcript(video_id, transcript)
                await self._datastore.update_video_status(video.url, VideoStatus.TRANSCRIBED)

            # 3. 清洗
            cleaned_text = self._cleaner.clean(transcript.full_text)

            # 4. 分段
            segments = self._segmenter.segment(cleaned_text)
            if not segments:
                segments = [cleaned_text]

            # 5. 分类
            if self._monitor:
                self._monitor.step_start("classify", video.url)
            topic = await self._classifier.classify(segments)
            if self._monitor:
                self._monitor.step_end("classify")

            if self._classifier.should_skip(topic):
                if self._datastore:
                    await self._datastore.update_video_status(
                        video.url, VideoStatus.SKIPPED, topic.skip_reason
                    )
                if self._monitor:
                    self._monitor.video_skipped(topic.skip_reason or "商业相关度过低")
                return None

            # 6. 分析
            if self._monitor:
                self._monitor.step_start("analyze", video.url)
            analysis = await self._analyzer.analyze(segments, topic, video_id)
            if self._monitor:
                self._monitor.step_end("analyze")

            if self._datastore:
                await self._datastore.save_analysis(video_id, analysis)
                await self._datastore.update_video_status(video.url, VideoStatus.ANALYZED)
                await self._datastore.save_checkpoint(self._run_id, {"last_url": video.url, "step": "analyzed"})

            if self._monitor:
                self._monitor.video_success()

            return analysis

        except Exception as e:
            logger.error(f"[manager] 视频处理失败 {video.url}: {e}")
            if self._datastore:
                await self._datastore.update_video_status(video.url, VideoStatus.SKIPPED, str(e))
                await self._datastore.save_checkpoint(self._run_id, {"last_url": video.url, "step": "failed", "error": str(e)})
            if self._monitor:
                self._monitor.video_failed(str(e))
            return None
