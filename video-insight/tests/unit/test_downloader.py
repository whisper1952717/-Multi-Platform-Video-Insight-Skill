"""VideoDownloader 降级策略单元测试。"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
from openclaw.models.types import VideoInfo


def _make_video(platform="bilibili"):
    return VideoInfo(
        url=f"https://www.{platform}.com/video/test123",
        title="测试视频",
        creator="test_creator",
        platform=platform,
        publish_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        view_count=1000,
    )


# ── 路径 1: 字幕获取成功 ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_download_subtitle_success(tmp_path):
    """字幕获取成功时，method 应为 'subtitle'，subtitle_text 非空。"""
    from openclaw.pipeline.downloader import VideoDownloader
    downloader = VideoDownloader(download_dir=str(tmp_path))

    with patch.object(downloader, "_fetch_subtitle", new=AsyncMock(return_value="这是字幕内容")):
        result = await downloader.download(_make_video())

    assert result.method == "subtitle"
    assert result.subtitle_text == "这是字幕内容"
    assert result.skipped_reason is None


# ── 路径 2: 字幕失败 → 音频下载 ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_download_fallback_to_audio(tmp_path):
    """字幕失败时应降级到音频下载，method 应为 'audio'。"""
    from openclaw.pipeline.downloader import VideoDownloader
    downloader = VideoDownloader(download_dir=str(tmp_path))

    audio_path = str(tmp_path / "audio.mp3")
    with patch.object(downloader, "_fetch_subtitle", new=AsyncMock(return_value=None)), \
         patch.object(downloader, "_download_audio", new=AsyncMock(return_value=audio_path)):
        result = await downloader.download(_make_video())

    assert result.method == "audio"
    assert result.file_path == audio_path
    assert result.skipped_reason is None


# ── 路径 3: 全部失败 → 跳过 ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_download_skip_when_all_fail(tmp_path):
    """字幕和音频均失败时，method 应为 'skipped'，skipped_reason 非空。"""
    from openclaw.pipeline.downloader import VideoDownloader
    downloader = VideoDownloader(download_dir=str(tmp_path))

    with patch.object(downloader, "_fetch_subtitle", new=AsyncMock(return_value=None)), \
         patch.object(downloader, "_download_audio", new=AsyncMock(return_value=None)):
        result = await downloader.download(_make_video())

    assert result.method == "skipped"
    assert result.skipped_reason is not None
    assert len(result.skipped_reason) > 0


# ── 降级顺序验证 ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audio_not_called_when_subtitle_succeeds(tmp_path):
    """字幕成功时，不应调用音频下载。"""
    from openclaw.pipeline.downloader import VideoDownloader
    downloader = VideoDownloader(download_dir=str(tmp_path))

    audio_mock = AsyncMock(return_value="/some/path.mp3")
    with patch.object(downloader, "_fetch_subtitle", new=AsyncMock(return_value="字幕")), \
         patch.object(downloader, "_download_audio", new=audio_mock):
        await downloader.download(_make_video())

    audio_mock.assert_not_called()


@pytest.mark.asyncio
async def test_subtitle_called_before_audio(tmp_path):
    """字幕获取应先于音频下载被调用。"""
    from openclaw.pipeline.downloader import VideoDownloader
    downloader = VideoDownloader(download_dir=str(tmp_path))

    call_order = []

    async def mock_subtitle(video):
        call_order.append("subtitle")
        return None

    async def mock_audio(video):
        call_order.append("audio")
        return None

    with patch.object(downloader, "_fetch_subtitle", new=mock_subtitle), \
         patch.object(downloader, "_download_audio", new=mock_audio):
        await downloader.download(_make_video())

    assert call_order == ["subtitle", "audio"]


# ── video_id 生成 ─────────────────────────────────────────────────────────────

def test_url_to_id_deterministic():
    """同一 URL 应始终生成相同的 video_id。"""
    from openclaw.pipeline.downloader import _url_to_id
    url = "https://www.bilibili.com/video/BV1xx"
    assert _url_to_id(url) == _url_to_id(url)
    assert len(_url_to_id(url)) == 16


def test_url_to_id_different_urls():
    """不同 URL 应生成不同的 video_id。"""
    from openclaw.pipeline.downloader import _url_to_id
    assert _url_to_id("https://url1.com") != _url_to_id("https://url2.com")


# ── 字幕解析 ─────────────────────────────────────────────────────────────────

def test_parse_subtitle_vtt():
    """VTT 字幕应正确解析为纯文本。"""
    from openclaw.pipeline.downloader import _parse_subtitle
    vtt = """WEBVTT

1
00:00:01.000 --> 00:00:03.000
这是第一句话

2
00:00:04.000 --> 00:00:06.000
这是第二句话
"""
    result = _parse_subtitle(vtt)
    assert "这是第一句话" in result
    assert "这是第二句话" in result
    assert "WEBVTT" not in result
    assert "-->" not in result
