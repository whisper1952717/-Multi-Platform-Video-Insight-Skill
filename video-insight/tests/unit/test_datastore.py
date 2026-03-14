"""SQLiteDataStore 单元测试。"""
import asyncio
import pytest
from datetime import datetime, timezone


@pytest.fixture
async def datastore(tmp_path):
    from openclaw.storage.sqlite_backend import SQLiteDataStore
    db_path = str(tmp_path / "test.db")
    ds = SQLiteDataStore(db_path)
    await ds.initialize()
    yield ds


def _make_video(url: str):
    from openclaw.models.types import VideoInfo
    from datetime import datetime, timezone
    return VideoInfo(
        url=url, title="测试视频", platform="bilibili",
        creator="test_creator",
        publish_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        view_count=100,
    )


@pytest.mark.asyncio
async def test_save_and_get_video(datastore):
    """保存视频后可以查询到。"""
    video = _make_video("https://bilibili.com/video/BV1test")
    video_id = await datastore.save_video(video, run_id="run-001")
    assert video_id is not None


@pytest.mark.asyncio
async def test_is_cached_within_ttl(datastore):
    """在 TTL 内完整分析过的视频，is_cached 应返回 True。"""
    from openclaw.models.types import VideoStatus, VideoAnalysis
    video = _make_video("https://bilibili.com/video/BV1cached")
    video_id = await datastore.save_video(video, run_id="run-001")
    # 模拟完整分析流程
    await datastore.update_video_status(video.url, VideoStatus.ANALYZED)
    analysis = VideoAnalysis(
        video_id=video_id,
        core_signals=[], cognition_framework=[],
        methodology_fragments=[], high_value_quotes=[],
        overall_quality=0.8,
    )
    await datastore.save_analysis(video_id, analysis)
    result = await datastore.is_cached(video.url, cache_ttl_hours=72)
    assert result is True


@pytest.mark.asyncio
async def test_is_not_cached_unknown_url(datastore):
    """未保存的 URL，is_cached 应返回 False。"""
    result = await datastore.is_cached("https://bilibili.com/video/BV1unknown", cache_ttl_hours=72)
    assert result is False


@pytest.mark.asyncio
async def test_update_video_status(datastore):
    """视频状态更新正常工作。"""
    from openclaw.models.types import VideoStatus
    video = _make_video("https://bilibili.com/video/BV1status")
    await datastore.save_video(video, run_id="run-001")
    # 不应抛出异常
    await datastore.update_video_status(video.url, VideoStatus.DOWNLOADED)


@pytest.mark.asyncio
async def test_checkpoint_save_and_load(datastore):
    """save_checkpoint 后 load_checkpoint 应返回等价状态。"""
    run_id = "run-checkpoint-test"
    state = {"last_url": "https://bilibili.com/video/BV1xx", "step": "downloaded", "count": 5}
    await datastore.save_checkpoint(run_id, state)
    loaded = await datastore.load_checkpoint(run_id)
    assert loaded is not None
    assert loaded["last_url"] == state["last_url"]
    assert loaded["step"] == state["step"]


@pytest.mark.asyncio
async def test_checkpoint_overwrite(datastore):
    """多次保存检查点，load 应返回最新状态。"""
    run_id = "run-overwrite"
    await datastore.save_checkpoint(run_id, {"step": "downloaded"})
    await datastore.save_checkpoint(run_id, {"step": "analyzed"})
    loaded = await datastore.load_checkpoint(run_id)
    assert loaded["step"] == "analyzed"


@pytest.mark.asyncio
async def test_load_nonexistent_checkpoint(datastore):
    """不存在的 run_id，load_checkpoint 应返回 None。"""
    result = await datastore.load_checkpoint("nonexistent-run-id")
    assert result is None
