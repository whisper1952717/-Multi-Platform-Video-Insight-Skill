"""SourceAccessManager 单元测试。"""
import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock


def _make_manager(**kwargs):
    from openclaw.middleware.access_manager import SourceAccessManager
    return SourceAccessManager(**kwargs)


# ── 随机延时范围 ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_random_delay_within_range(monkeypatch):
    """随机延时应在配置的 [lo, hi] 范围内。"""
    delays = []
    import openclaw.middleware.access_manager as mod

    original_sleep = asyncio.sleep

    async def mock_sleep(t):
        delays.append(t)

    monkeypatch.setattr(asyncio, "sleep", mock_sleep)

    mgr = _make_manager(platform_delays={"bilibili": (2.0, 4.0)})
    await mgr._random_delay("bilibili")

    assert len(delays) == 1
    assert 2.0 <= delays[0] <= 4.0


@pytest.mark.asyncio
async def test_random_delay_default_range(monkeypatch):
    """未配置平台延时时，应使用默认范围 [1.0, 8.0]。"""
    delays = []

    async def mock_sleep(t):
        delays.append(t)

    monkeypatch.setattr(asyncio, "sleep", mock_sleep)

    mgr = _make_manager()
    await mgr._random_delay("youtube")

    assert len(delays) == 1
    assert 1.0 <= delays[0] <= 8.0


# ── 平台间隔限制 ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_platform_interval_enforced(monkeypatch):
    """连续请求同一平台时，应等待最低间隔。"""
    slept = []

    async def mock_sleep(t):
        slept.append(t)

    monkeypatch.setattr(asyncio, "sleep", mock_sleep)

    mgr = _make_manager()
    # 模拟刚刚请求过（0.5秒前）
    mgr._platform_last_request["bilibili"] = time.monotonic() - 0.5
    await mgr._wait_platform_interval("bilibili")

    # 应该 sleep 约 2.5 秒（3.0 - 0.5）
    assert len(slept) == 1
    assert slept[0] > 2.0


@pytest.mark.asyncio
async def test_platform_interval_no_wait_if_enough_time(monkeypatch):
    """距上次请求超过最低间隔时，不应额外等待。"""
    slept = []

    async def mock_sleep(t):
        slept.append(t)

    monkeypatch.setattr(asyncio, "sleep", mock_sleep)

    mgr = _make_manager()
    # 模拟 10 秒前请求过
    mgr._platform_last_request["bilibili"] = time.monotonic() - 10.0
    await mgr._wait_platform_interval("bilibili")

    assert len(slept) == 0


# ── 指数退避重试 ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_retry_on_403(monkeypatch):
    """遇到 403 错误时应进行指数退避重试。"""
    slept = []

    async def mock_sleep(t):
        slept.append(t)

    monkeypatch.setattr(asyncio, "sleep", mock_sleep)

    call_count = 0

    async def failing_fn():
        nonlocal call_count
        call_count += 1
        exc = Exception("HTTP 403 Forbidden")
        raise exc

    mgr = _make_manager()
    with pytest.raises(Exception, match="403"):
        await mgr._retry_with_backoff(failing_fn, "bilibili")

    # 应重试 MAX_RETRIES 次
    assert call_count == mgr.MAX_RETRIES
    # 每次 403 都会 sleep：1s, 2s, 4s
    assert len(slept) == mgr.MAX_RETRIES
    assert slept[0] == 1  # 2^0
    assert slept[1] == 2  # 2^1
    assert slept[2] == 4  # 2^2


@pytest.mark.asyncio
async def test_retry_on_429(monkeypatch):
    """遇到 429 错误时应进行指数退避重试。"""
    slept = []

    async def mock_sleep(t):
        slept.append(t)

    monkeypatch.setattr(asyncio, "sleep", mock_sleep)

    call_count = 0

    async def failing_fn():
        nonlocal call_count
        call_count += 1
        raise Exception("rate limit 429 exceeded")

    mgr = _make_manager()
    with pytest.raises(Exception):
        await mgr._retry_with_backoff(failing_fn, "douyin")

    assert call_count == mgr.MAX_RETRIES


@pytest.mark.asyncio
async def test_no_retry_on_other_errors(monkeypatch):
    """非 403/429 错误不应重试。"""
    slept = []

    async def mock_sleep(t):
        slept.append(t)

    monkeypatch.setattr(asyncio, "sleep", mock_sleep)

    call_count = 0

    async def failing_fn():
        nonlocal call_count
        call_count += 1
        raise ValueError("some other error")

    mgr = _make_manager()
    with pytest.raises(ValueError):
        await mgr._retry_with_backoff(failing_fn, "youtube")

    # 只调用一次，不重试
    assert call_count == 1
    assert len(slept) == 0


@pytest.mark.asyncio
async def test_retry_success_on_second_attempt(monkeypatch):
    """第二次尝试成功时应返回结果并重置失败计数。"""
    slept = []

    async def mock_sleep(t):
        slept.append(t)

    monkeypatch.setattr(asyncio, "sleep", mock_sleep)

    call_count = 0

    async def flaky_fn():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("HTTP 429")
        return "success"

    mgr = _make_manager()
    result = await mgr._retry_with_backoff(flaky_fn, "bilibili")
    assert result == "success"
    assert call_count == 2
    assert mgr._failure_counts.get("bilibili", 0) == 0


# ── 连续失败暂停平台 ──────────────────────────────────────────────────────────

def test_pause_platform_after_max_failures():
    """连续失败 MAX_FAILURES_BEFORE_PAUSE 次后，平台应被暂停。"""
    mgr = _make_manager()
    mgr._failure_counts["bilibili"] = mgr.MAX_FAILURES_BEFORE_PAUSE - 1
    mgr._pause_platform("bilibili")
    assert mgr._is_paused("bilibili") is True


def test_paused_platform_raises_on_request():
    """已暂停的平台发起请求时应立即抛出 RuntimeError。"""
    mgr = _make_manager()
    mgr._paused_until["bilibili"] = time.monotonic() + 600

    async def dummy_fn():
        return "ok"

    with pytest.raises(RuntimeError, match="已暂停"):
        asyncio.get_event_loop().run_until_complete(
            mgr.request("bilibili", dummy_fn)
        )


def test_platform_not_paused_initially():
    """初始状态下平台不应被暂停。"""
    mgr = _make_manager()
    assert mgr._is_paused("bilibili") is False
    assert mgr._is_paused("youtube") is False


# ── UA 轮换 ───────────────────────────────────────────────────────────────────

def test_ua_rotation():
    """连续获取请求头时，UA 应轮换。"""
    from openclaw.middleware.access_manager import UA_POOL
    mgr = _make_manager()
    headers1 = mgr._get_headers("bilibili")
    headers2 = mgr._get_headers("bilibili")
    # 两次 UA 应不同（除非池只有1个）
    if len(UA_POOL) > 1:
        assert headers1["User-Agent"] != headers2["User-Agent"]


def test_headers_contain_referer():
    """请求头应包含正确的 Referer。"""
    mgr = _make_manager()
    headers = mgr._get_headers("bilibili")
    assert "bilibili.com" in headers["Referer"]
    headers_yt = mgr._get_headers("youtube")
    assert "youtube.com" in headers_yt["Referer"]
