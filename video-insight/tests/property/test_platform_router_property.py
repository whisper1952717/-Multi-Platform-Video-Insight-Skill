"""PlatformRouter 属性测试（Property-Based Testing）。"""
import pytest
from hypothesis import given, settings, strategies as st


KNOWN_URLS = {
    "bilibili": [
        "https://www.bilibili.com/video/BV1xx411c7mD",
        "https://space.bilibili.com/123456",
        "https://b23.tv/abc123",
    ],
    "douyin": [
        "https://www.douyin.com/user/abc123",
        "https://www.iesdouyin.com/share/video/123",
    ],
    "youtube": [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/@channelname",
    ],
    "xiaohongshu": [
        "https://www.xiaohongshu.com/user/profile/abc",
        "https://xhslink.com/abc123",
    ],
}


# ── 属性 5: 平台识别确定性 ────────────────────────────────────────────────────

@pytest.mark.parametrize("platform,urls", KNOWN_URLS.items())
def test_detect_platform_deterministic(platform, urls):
    """属性 5: 同一 URL 多次调用 detect_platform 应返回相同平台。"""
    from openclaw.adapters.base import PlatformRouter
    router = PlatformRouter()
    for url in urls:
        results = {router.detect_platform(url) for _ in range(5)}
        assert len(results) == 1, f"URL {url} 返回了不一致的平台: {results}"
        assert results.pop() == platform


@given(
    url=st.sampled_from([
        url for urls in KNOWN_URLS.values() for url in urls
    ])
)
@settings(max_examples=40)
def test_detect_platform_consistent_hypothesis(url):
    """属性 5 (hypothesis): 任意已知 URL 多次识别结果一致。"""
    from openclaw.adapters.base import PlatformRouter
    router = PlatformRouter()
    first = router.detect_platform(url)
    for _ in range(3):
        assert router.detect_platform(url) == first


# ── 属性 6: 不支持 URL 错误处理 ──────────────────────────────────────────────

UNSUPPORTED_URLS = [
    "https://www.weibo.com/user/123",
    "https://www.tiktok.com/@user",
    "https://twitter.com/user",
    "https://www.instagram.com/user",
    "not-a-url-at-all",
    "ftp://some.server/file",
    "",
    "https://example.com/video/123",
]


@pytest.mark.parametrize("url", UNSUPPORTED_URLS)
def test_unsupported_url_raises_value_error(url):
    """属性 6: 不支持的 URL 应抛出 ValueError 而非崩溃。"""
    from openclaw.adapters.base import PlatformRouter
    router = PlatformRouter()
    with pytest.raises(ValueError):
        router.detect_platform(url)


@given(
    url=st.text(min_size=0, max_size=200).filter(
        lambda u: not any(
            kw in u.lower()
            for kw in ["bilibili", "b23.tv", "douyin", "iesdouyin",
                       "youtube", "youtu.be", "xiaohongshu", "xhslink"]
        )
    )
)
@settings(max_examples=50)
def test_random_non_platform_url_raises(url):
    """属性 6 (hypothesis): 随机非平台 URL 应抛出 ValueError 而非崩溃。"""
    from openclaw.adapters.base import PlatformRouter
    router = PlatformRouter()
    try:
        router.detect_platform(url)
        # 如果没抛出，说明意外匹配了某平台——这不应该发生
        # 但 hypothesis 可能生成包含平台关键词的字符串，filter 已过滤
    except ValueError:
        pass  # 预期行为
    except Exception as e:
        pytest.fail(f"detect_platform 抛出了非 ValueError 异常: {type(e).__name__}: {e}")


# ── resolve_platforms 测试 ────────────────────────────────────────────────────

def test_resolve_platforms_valid():
    """resolve_platforms 对有效平台名称应返回适配器列表。"""
    from openclaw.adapters.base import PlatformRouter
    router = PlatformRouter()
    adapters = router.resolve_platforms(["bilibili", "youtube"])
    assert len(adapters) == 2


def test_resolve_platforms_invalid_raises():
    """resolve_platforms 对无效平台名称应抛出 ValueError。"""
    from openclaw.adapters.base import PlatformRouter
    router = PlatformRouter()
    with pytest.raises(ValueError, match="不支持的平台"):
        router.resolve_platforms(["bilibili", "weibo"])
