"""DataStore 属性测试（Property-Based Testing）。"""
import asyncio
import os
import tempfile
import pytest
from datetime import datetime, timezone
from hypothesis import given, settings, strategies as st


def _make_video(url: str = "https://www.bilibili.com/video/test") -> "VideoInfo":
    from openclaw.models.types import VideoInfo
    return VideoInfo(
        url=url,
        title="测试视频",
        creator="test_creator",
        platform="bilibili",
        publish_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        view_count=100,
    )


async def _make_store(db_path: str) -> "SQLiteDataStore":
    from openclaw.storage.sqlite_backend import SQLiteDataStore
    store = SQLiteDataStore(db_path)
    await store.initialize()
    return store


# ── 属性 3: 缓存一致性 ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_hit_within_ttl():
    """在 cache_ttl 内已分析的视频，is_cached 应返回 True。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        store = await _make_store(db_path)
        try:
            video = _make_video("https://bilibili.com/video/cache_test")
            video_id = await store.save_video(video, "run1")

            # 保存分析结果
            from openclaw.models.types import VideoAnalysis, VideoStatus
            analysis = VideoAnalysis(
                video_id=video_id,
                core_signals=[],
                cognition_framework=[],
                methodology_fragments=[],
                high_value_quotes=[],
                overall_quality=0.8,
            )
            await store.save_analysis(video_id, analysis)
            await store.update_video_status(video.url, VideoStatus.ANALYZED)

            # TTL=72h，刚分析完应命中缓存
            assert await store.is_cached(video.url, cache_ttl_hours=72) is True
        finally:
            await store.close()


@pytest.mark.asyncio
async def test_cache_miss_without_analysis():
    """未分析的视频，is_cached 应返回 False。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        store = await _make_store(db_path)
        try:
            video = _make_video("https://bilibili.com/video/no_analysis")
            await store.save_video(video, "run1")
            # 只保存视频，不保存分析
            assert await store.is_cached(video.url, cache_ttl_hours=72) is False
        finally:
            await store.close()


@pytest.mark.asyncio
async def test_cache_miss_ttl_zero():
    """TTL=0 时，即使已分析也应视为过期（缓存未命中）。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        store = await _make_store(db_path)
        try:
            video = _make_video("https://bilibili.com/video/ttl_zero")
            video_id = await store.save_video(video, "run1")

            from openclaw.models.types import VideoAnalysis, VideoStatus
            analysis = VideoAnalysis(
                video_id=video_id,
                core_signals=[],
                cognition_framework=[],
                methodology_fragments=[],
                high_value_quotes=[],
                overall_quality=0.8,
            )
            await store.save_analysis(video_id, analysis)
            await store.update_video_status(video.url, VideoStatus.ANALYZED)

            # TTL=0 意味着立即过期
            assert await store.is_cached(video.url, cache_ttl_hours=0) is False
        finally:
            await store.close()


# ── 属性 4: 断点续传完整性 ────────────────────────────────────────────────────

@pytest.mark.asyncio
@given(
    run_id=st.text(min_size=1, max_size=36, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-")),
    step=st.sampled_from(["downloaded", "transcribed", "analyzed", "failed"]),
    last_url=st.text(min_size=5, max_size=100),
)
@settings(max_examples=30)
async def test_checkpoint_roundtrip(run_id, step, last_url):
    """属性 4: save_checkpoint 后 load_checkpoint 应返回等价状态。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, f"test_{run_id[:8]}.db")
        store = await _make_store(db_path)
        try:
            state = {"last_url": last_url, "step": step, "run_id": run_id}
            await store.save_checkpoint(run_id, state)
            loaded = await store.load_checkpoint(run_id)
            assert loaded is not None
            assert loaded["last_url"] == last_url
            assert loaded["step"] == step
        finally:
            await store.close()


@pytest.mark.asyncio
async def test_checkpoint_overwrite():
    """多次 save_checkpoint 应覆盖，load 返回最新状态。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        store = await _make_store(db_path)
        try:
            run_id = "run-overwrite-test"
            await store.save_checkpoint(run_id, {"step": "downloaded", "last_url": "url1"})
            await store.save_checkpoint(run_id, {"step": "analyzed", "last_url": "url2"})
            loaded = await store.load_checkpoint(run_id)
            assert loaded["step"] == "analyzed"
            assert loaded["last_url"] == "url2"
        finally:
            await store.close()


@pytest.mark.asyncio
async def test_checkpoint_missing_returns_none():
    """不存在的 run_id 应返回 None。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        store = await _make_store(db_path)
        try:
            result = await store.load_checkpoint("nonexistent-run-id")
            assert result is None
        finally:
            await store.close()


# ── 视频状态流转 ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_video_status_transitions():
    """视频状态应能正确流转：pending → downloaded → analyzed。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        store = await _make_store(db_path)
        try:
            from openclaw.models.types import VideoStatus
            video = _make_video("https://bilibili.com/video/status_test")
            await store.save_video(video, "run1")

            # 初始状态
            status = await store.get_video_status(video.url)
            assert status == VideoStatus.PENDING

            await store.update_video_status(video.url, VideoStatus.DOWNLOADED)
            assert await store.get_video_status(video.url) == VideoStatus.DOWNLOADED

            await store.update_video_status(video.url, VideoStatus.ANALYZED)
            assert await store.get_video_status(video.url) == VideoStatus.ANALYZED
        finally:
            await store.close()
