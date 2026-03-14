"""AsyncPipelineManager 单元测试。"""
import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from openclaw.models.types import (
    ContentType, DownloadResult, TopicClassification,
    TranscriptResult, TimestampedSegment, VideoAnalysis, VideoInfo, VideoStatus,
)


def _make_video(url: str = "https://bilibili.com/video/test") -> VideoInfo:
    return VideoInfo(
        url=url, title="测试", creator="creator",
        platform="bilibili",
        publish_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        view_count=100,
    )


def _make_analysis(video_id: str = "v1") -> VideoAnalysis:
    return VideoAnalysis(
        video_id=video_id, core_signals=[], cognition_framework=[],
        methodology_fragments=[], high_value_quotes=[], overall_quality=0.8,
    )


def _make_transcript(video_id: str = "v1") -> TranscriptResult:
    return TranscriptResult(
        video_id=video_id,
        segments=[TimestampedSegment(start=0, end=5, text="测试内容")],
        full_text="测试内容",
    )


def _make_topic(relevance: float = 0.8) -> TopicClassification:
    return TopicClassification(
        primary_topic="AI", content_type=ContentType.INDUSTRY,
        business_relevance=relevance,
    )


def _make_manager(max_concurrency=3, cache_enabled=False):
    from openclaw.pipeline.manager import AsyncPipelineManager
    from openclaw.pipeline.downloader import VideoDownloader
    from openclaw.pipeline.transcriber import TranscriptGenerator
    from openclaw.pipeline.cleaner import TranscriptCleaner
    from openclaw.pipeline.segmenter import VideoSegmenter
    from openclaw.pipeline.classifier import TopicClassifier
    from openclaw.pipeline.analyzer import VideoAnalyzer

    downloader = MagicMock(spec=VideoDownloader)
    transcriber = MagicMock(spec=TranscriptGenerator)
    cleaner = MagicMock(spec=TranscriptCleaner)
    segmenter = MagicMock(spec=VideoSegmenter)
    classifier = MagicMock(spec=TopicClassifier)
    analyzer = MagicMock(spec=VideoAnalyzer)

    # 默认行为
    downloader.download = AsyncMock(return_value=DownloadResult(video_id="v1", method="subtitle", subtitle_text="内容"))
    transcriber.transcribe = AsyncMock(return_value=_make_transcript())
    cleaner.clean = MagicMock(return_value="清洗后内容")
    segmenter.segment = MagicMock(return_value=["段落1", "段落2"])
    classifier.classify = AsyncMock(return_value=_make_topic())
    classifier.should_skip = MagicMock(return_value=False)
    analyzer.analyze = AsyncMock(return_value=_make_analysis())

    return AsyncPipelineManager(
        downloader=downloader, transcriber=transcriber, cleaner=cleaner,
        segmenter=segmenter, classifier=classifier, analyzer=analyzer,
        max_concurrency=max_concurrency, cache_enabled=cache_enabled,
    ), downloader, transcriber, cleaner, segmenter, classifier, analyzer


# ── Mode1 串行处理 ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mode1_processes_all_videos():
    """Mode1 应处理列表中的所有视频。"""
    mgr, downloader, *_ = _make_manager()
    videos = [_make_video(f"https://bilibili.com/video/{i}") for i in range(3)]
    results = await mgr.process_single_creator(videos)
    assert downloader.download.call_count == 3
    assert len(results) == 3


@pytest.mark.asyncio
async def test_mode1_serial_order():
    """Mode1 应按顺序串行处理视频（不并发）。"""
    mgr, downloader, *_ = _make_manager()
    call_order = []

    async def track_download(video):
        call_order.append(video.url)
        return DownloadResult(video_id="v1", method="subtitle", subtitle_text="内容")

    downloader.download = track_download
    videos = [_make_video(f"https://bilibili.com/video/{i}") for i in range(3)]
    await mgr.process_single_creator(videos)

    expected = [f"https://bilibili.com/video/{i}" for i in range(3)]
    assert call_order == expected


# ── Mode2 并发控制 ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mode2_respects_concurrency_limit():
    """Mode2 并发数不应超过 max_concurrency。"""
    max_concurrency = 2
    mgr, downloader, *_ = _make_manager(max_concurrency=max_concurrency)

    concurrent_count = 0
    max_concurrent_seen = 0

    async def slow_download(video):
        nonlocal concurrent_count, max_concurrent_seen
        concurrent_count += 1
        max_concurrent_seen = max(max_concurrent_seen, concurrent_count)
        await asyncio.sleep(0.01)
        concurrent_count -= 1
        return DownloadResult(video_id="v1", method="subtitle", subtitle_text="内容")

    downloader.download = slow_download

    creator_videos = {
        f"creator_{i}": [_make_video(f"https://bilibili.com/video/c{i}")] for i in range(5)
    }
    await mgr.process_multi_creators(creator_videos)
    assert max_concurrent_seen <= max_concurrency


@pytest.mark.asyncio
async def test_mode2_processes_all_creators():
    """Mode2 应处理所有博主的视频。"""
    mgr, downloader, *_ = _make_manager(max_concurrency=3)
    creator_videos = {
        "creator_a": [_make_video("https://bilibili.com/video/a1"), _make_video("https://bilibili.com/video/a2")],
        "creator_b": [_make_video("https://bilibili.com/video/b1")],
    }
    results = await mgr.process_multi_creators(creator_videos)
    assert downloader.download.call_count == 3
    assert len(results) == 3


# ── 缓存命中跳过 ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_hit_skips_processing():
    """缓存命中时应跳过处理，不调用下载器。"""
    mgr, downloader, *_ = _make_manager(cache_enabled=True)

    mock_datastore = MagicMock()
    mock_datastore.is_cached = AsyncMock(return_value=True)
    mgr._datastore = mock_datastore

    video = _make_video()
    results = await mgr.process_single_creator([video])

    downloader.download.assert_not_called()
    assert results == []


@pytest.mark.asyncio
async def test_cache_miss_processes_video():
    """缓存未命中时应正常处理视频。"""
    mgr, downloader, *_ = _make_manager(cache_enabled=True)

    mock_datastore = MagicMock()
    mock_datastore.is_cached = AsyncMock(return_value=False)
    mock_datastore.save_video = AsyncMock(return_value="video_id_1")
    mock_datastore.update_video_status = AsyncMock()
    mock_datastore.save_checkpoint = AsyncMock()
    mock_datastore.save_transcript = AsyncMock()
    mock_datastore.save_analysis = AsyncMock()
    mgr._datastore = mock_datastore

    results = await mgr.process_single_creator([_make_video()])
    downloader.download.assert_called_once()
    assert len(results) == 1


# ── 下载跳过时不进入后续步骤 ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_skipped_download_stops_pipeline():
    """下载结果为 skipped 时，后续步骤不应执行。"""
    mgr, downloader, transcriber, *_ = _make_manager()
    downloader.download = AsyncMock(return_value=DownloadResult(
        video_id="v1", method="skipped", skipped_reason="无法获取"
    ))
    results = await mgr.process_single_creator([_make_video()])
    transcriber.transcribe.assert_not_called()
    assert results == []


# ── 低商业相关度跳过 ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_low_relevance_skips_analysis():
    """business_relevance < 0.3 时，分析步骤不应执行。"""
    mgr, _, _, _, _, classifier, analyzer = _make_manager()
    classifier.classify = AsyncMock(return_value=_make_topic(relevance=0.1))
    classifier.should_skip = MagicMock(return_value=True)

    results = await mgr.process_single_creator([_make_video()])
    analyzer.analyze.assert_not_called()
    assert results == []
