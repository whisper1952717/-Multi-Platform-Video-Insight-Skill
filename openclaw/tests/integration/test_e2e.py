"""端到端集成测试 — 使用 mock 数据模拟完整流程。"""
import os
import tempfile
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from openclaw.models.types import (
    ContentType, DownloadResult, TimestampedSegment,
    TopicClassification, TranscriptResult, VideoAnalysis, VideoInfo, VideoStatus,
)


# ── 共享 fixtures ─────────────────────────────────────────────────────────────

def _make_video(url: str, platform: str = "bilibili") -> VideoInfo:
    return VideoInfo(
        url=url, title=f"视频-{url[-4:]}", creator="test_creator",
        platform=platform,
        publish_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        view_count=5000,
    )


def _make_transcript(video_id: str) -> TranscriptResult:
    return TranscriptResult(
        video_id=video_id,
        segments=[TimestampedSegment(start=0, end=10, text="AI正在改变商业格局，创业公司需要找到差异化策略。")],
        full_text="AI正在改变商业格局，创业公司需要找到差异化策略。",
    )


def _make_analysis(video_id: str, quality: float = 0.85) -> VideoAnalysis:
    from openclaw.models.types import CoreSignal
    return VideoAnalysis(
        video_id=video_id,
        core_signals=[CoreSignal(signal="AI差异化策略", evidence="创业公司需要找到差异化策略", confidence_score=0.85)],
        cognition_framework=[],
        methodology_fragments=[],
        high_value_quotes=[],
        overall_quality=quality,
    )


def _build_pipeline(tmp_path: str, cache_enabled: bool = False):
    """构建完整流水线，所有外部依赖均 mock。"""
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

    downloader.download = AsyncMock(side_effect=lambda v: DownloadResult(
        video_id=v.url[-8:], method="subtitle", subtitle_text="AI正在改变商业格局"
    ))
    transcriber.transcribe = AsyncMock(side_effect=lambda r: _make_transcript(r.video_id))
    cleaner.clean = MagicMock(return_value="AI正在改变商业格局，创业公司需要找到差异化策略。")
    segmenter.segment = MagicMock(return_value=["AI正在改变商业格局", "创业公司需要找到差异化策略"])
    classifier.classify = AsyncMock(return_value=TopicClassification(
        primary_topic="AI创业", content_type=ContentType.INDUSTRY, business_relevance=0.85
    ))
    classifier.should_skip = MagicMock(return_value=False)
    analyzer.analyze = AsyncMock(side_effect=lambda segs, topic, vid: _make_analysis(vid))

    mgr = AsyncPipelineManager(
        downloader=downloader, transcriber=transcriber, cleaner=cleaner,
        segmenter=segmenter, classifier=classifier, analyzer=analyzer,
        cache_enabled=cache_enabled,
    )
    return mgr, downloader, transcriber, analyzer


# ── Mode1 端到端 ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mode1_full_pipeline(tmp_path):
    """Mode1 完整流程：视频列表 → 流水线 → 聚合 → 报告。"""
    from openclaw.aggregation.aggregator import InsightsAggregator
    from openclaw.report.generator import ReportGenerator

    mgr, downloader, transcriber, analyzer = _build_pipeline(str(tmp_path))
    videos = [_make_video(f"https://bilibili.com/video/v{i}") for i in range(3)]

    # 1. 流水线处理
    analyses = await mgr.process_single_creator(videos)
    assert len(analyses) == 3
    assert downloader.download.call_count == 3
    assert transcriber.transcribe.call_count == 3
    assert analyzer.analyze.call_count == 3

    # 2. 聚合
    agg = InsightsAggregator()
    insights = await agg.aggregate_mode1(analyses, {
        "creator": "test_creator", "platform": "bilibili",
        "videos_analyzed": 3, "videos_skipped": 0, "time_range": "last_30_days",
    })
    assert len(insights.core_signals) > 0
    assert len(insights.insights_for_me) > 0
    assert 0.0 <= insights.quality_summary.overall_confidence <= 1.0

    # 3. 报告生成
    gen = ReportGenerator()
    md_report = gen.generate(insights, output_format="Markdown")
    json_report = gen.generate(insights, output_format="JSON")

    assert "# OpenClaw 洞察报告" in md_report
    assert "test_creator" in md_report
    assert "core_signals" in json_report


# ── Mode2 端到端 ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mode2_full_pipeline(tmp_path):
    """Mode2 完整流程：多博主 → 并发流水线 → 聚合 → 报告。"""
    from openclaw.aggregation.aggregator import InsightsAggregator
    from openclaw.report.generator import ReportGenerator

    mgr, downloader, _, analyzer = _build_pipeline(str(tmp_path))

    creator_videos = {
        "creator_a": [_make_video(f"https://bilibili.com/video/a{i}") for i in range(2)],
        "creator_b": [_make_video(f"https://youtube.com/watch?v=b{i}", "youtube") for i in range(2)],
    }

    # 1. 并发流水线
    analyses = await mgr.process_multi_creators(creator_videos)
    assert len(analyses) == 4
    assert downloader.download.call_count == 4

    # 2. 聚合
    agg = InsightsAggregator()
    creator_analyses = {
        "creator_a": analyses[:2],
        "creator_b": analyses[2:],
    }
    insights = await agg.aggregate_mode2(creator_analyses, {
        "topic": "AI创业", "platforms": ["bilibili", "youtube"],
        "creators_analyzed": 2, "total_videos_analyzed": 4,
    })
    assert 0.0 <= insights.quality_summary.overall_confidence <= 1.0

    # 3. 报告
    gen = ReportGenerator()
    report = gen.generate(insights, output_format="Markdown")
    assert "## 趋势信号" in report
    assert "## 共识与分歧" in report


# ── 断点续传 ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_checkpoint_resume(tmp_path):
    """模拟中断后恢复：检查点应保存并可加载。"""
    from openclaw.storage.sqlite_backend import SQLiteDataStore

    db_path = os.path.join(str(tmp_path), "test.db")
    async with SQLiteDataStore(db_path) as store:
        run_id = "run-resume-test"

        # 模拟第一次运行，处理到一半
        await store.save_checkpoint(run_id, {
            "last_url": "https://bilibili.com/video/v1",
            "step": "analyzed",
            "completed_urls": ["https://bilibili.com/video/v0", "https://bilibili.com/video/v1"],
        })

        # 模拟重启后加载检查点
        checkpoint = await store.load_checkpoint(run_id)
        assert checkpoint is not None
        assert checkpoint["step"] == "analyzed"
        assert len(checkpoint["completed_urls"]) == 2

        # 继续处理剩余视频（v2）
        await store.save_checkpoint(run_id, {
            "last_url": "https://bilibili.com/video/v2",
            "step": "analyzed",
            "completed_urls": ["https://bilibili.com/video/v0", "https://bilibili.com/video/v1", "https://bilibili.com/video/v2"],
        })

        final = await store.load_checkpoint(run_id)
        assert len(final["completed_urls"]) == 3


# ── 报告文件输出 ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mode1_report_saved_to_file(tmp_path):
    """Mode1 报告应能正确保存到文件。"""
    from openclaw.aggregation.aggregator import InsightsAggregator
    from openclaw.report.generator import ReportGenerator

    mgr, *_ = _build_pipeline(str(tmp_path))
    videos = [_make_video("https://bilibili.com/video/file_test")]
    analyses = await mgr.process_single_creator(videos)

    agg = InsightsAggregator()
    insights = await agg.aggregate_mode1(analyses, {"creator": "test", "platform": "bilibili", "videos_analyzed": 1, "videos_skipped": 0, "time_range": "last_30_days"})

    out_path = os.path.join(str(tmp_path), "report.md")
    gen = ReportGenerator()
    gen.generate(insights, output_format="Markdown", output_path=out_path)

    assert os.path.exists(out_path)
    with open(out_path, encoding="utf-8") as f:
        content = f.read()
    assert "# OpenClaw 洞察报告" in content
