"""PlatformRouter 单元测试。"""
import pytest


def test_detect_bilibili():
    from openclaw.adapters.base import PlatformRouter
    r = PlatformRouter()
    assert r.detect_platform("https://space.bilibili.com/12345") == "bilibili"
    assert r.detect_platform("https://www.bilibili.com/video/BV1xx") == "bilibili"


def test_detect_youtube():
    from openclaw.adapters.base import PlatformRouter
    r = PlatformRouter()
    assert r.detect_platform("https://www.youtube.com/@channel") == "youtube"
    assert r.detect_platform("https://youtu.be/abc123") == "youtube"


def test_detect_douyin():
    from openclaw.adapters.base import PlatformRouter
    r = PlatformRouter()
    assert r.detect_platform("https://www.douyin.com/user/xxx") == "douyin"


def test_detect_xiaohongshu():
    from openclaw.adapters.base import PlatformRouter
    r = PlatformRouter()
    assert r.detect_platform("https://www.xiaohongshu.com/user/xxx") == "xiaohongshu"


def test_unsupported_url_raises():
    """不支持的 URL 应抛出 ValueError 而非崩溃。"""
    from openclaw.adapters.base import PlatformRouter
    r = PlatformRouter()
    with pytest.raises(ValueError, match="不支持的平台"):
        r.detect_platform("https://www.twitter.com/user")


def test_detect_platform_deterministic():
    """同一 URL 多次调用应返回相同结果。"""
    from openclaw.adapters.base import PlatformRouter
    r = PlatformRouter()
    url = "https://space.bilibili.com/99999"
    results = [r.detect_platform(url) for _ in range(10)]
    assert len(set(results)) == 1


def test_resolve_platforms():
    from openclaw.adapters.base import PlatformRouter
    r = PlatformRouter()
    adapters = r.resolve_platforms(["bilibili", "youtube"])
    assert len(adapters) == 2


def test_resolve_unsupported_platform_raises():
    from openclaw.adapters.base import PlatformRouter
    r = PlatformRouter()
    with pytest.raises(ValueError):
        r.resolve_platforms(["tiktok"])
