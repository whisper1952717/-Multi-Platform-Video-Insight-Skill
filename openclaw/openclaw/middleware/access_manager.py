"""SourceAccessManager — 网络访问管理中间件。"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import random
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# User-Agent 池
UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
]

PLATFORM_REFERERS = {
    "bilibili": "https://www.bilibili.com/",
    "douyin": "https://www.douyin.com/",
    "youtube": "https://www.youtube.com/",
    "xiaohongshu": "https://www.xiaohongshu.com/",
}


class CookieManager:
    """Cookie 生命周期管理：导入、加密存储、过期检测。"""

    def __init__(self, cookie_dir: str = "./cookies"):
        self._cookie_dir = Path(cookie_dir)
        self._cookies: Dict[str, dict] = {}

    def load_cookie(self, platform: str, cookie_path: Optional[str] = None) -> Optional[str]:
        """加载平台 Cookie 文件内容（Netscape 格式）。"""
        path = Path(cookie_path) if cookie_path else self._cookie_dir / f"{platform}.txt"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def is_cookie_valid(self, platform: str, cookie_path: Optional[str] = None) -> bool:
        """检查 Cookie 文件是否存在且非空。"""
        content = self.load_cookie(platform, cookie_path)
        return bool(content and content.strip())


class ProxyPoolInterface:
    """代理池接口（预留扩展）。"""

    def __init__(self, proxies: Optional[List[str]] = None):
        self._proxies = proxies or []
        self._current_idx = 0
        self._failure_counts: Dict[str, int] = {}

    def get_proxy(self) -> Optional[str]:
        if not self._proxies:
            return None
        proxy = self._proxies[self._current_idx % len(self._proxies)]
        return proxy

    def rotate(self) -> None:
        if self._proxies:
            self._current_idx = (self._current_idx + 1) % len(self._proxies)

    def mark_failed(self, proxy: str) -> None:
        self._failure_counts[proxy] = self._failure_counts.get(proxy, 0) + 1

    def get_available_proxies(self) -> List[str]:
        return [p for p in self._proxies if self._failure_counts.get(p, 0) < 3]


class SourceAccessManager:
    """统一网络访问管理中间件。"""

    PAUSE_DURATION = 600  # 连续失败后暂停 10 分钟（秒）
    MAX_FAILURES_BEFORE_PAUSE = 5
    MAX_RETRIES = 3
    MIN_PLATFORM_INTERVAL = 3.0  # 单平台最低间隔（秒）

    def __init__(
        self,
        platform_delays: Optional[Dict[str, Tuple[float, float]]] = None,
        proxy_enabled: bool = False,
        proxies: Optional[List[str]] = None,
    ):
        self._global_semaphore = asyncio.Semaphore(2)
        self._platform_locks: Dict[str, asyncio.Lock] = {}
        self._platform_last_request: Dict[str, float] = {}
        self._failure_counts: Dict[str, int] = {}
        self._paused_until: Dict[str, float] = {}
        self._platform_delays = platform_delays or {}
        self._ua_idx = 0
        self._cookie_manager = CookieManager()
        self._proxy_pool = ProxyPoolInterface(proxies) if proxy_enabled else None

    def _get_platform_lock(self, platform: str) -> asyncio.Lock:
        if platform not in self._platform_locks:
            self._platform_locks[platform] = asyncio.Lock()
        return self._platform_locks[platform]

    def _get_headers(self, platform: str) -> Dict[str, str]:
        ua = UA_POOL[self._ua_idx % len(UA_POOL)]
        self._ua_idx += 1
        return {
            "User-Agent": ua,
            "Referer": PLATFORM_REFERERS.get(platform, "https://www.google.com/"),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def _is_paused(self, platform: str) -> bool:
        until = self._paused_until.get(platform, 0)
        return time.monotonic() < until

    def _pause_platform(self, platform: str) -> None:
        self._paused_until[platform] = time.monotonic() + self.PAUSE_DURATION
        logger.warning(f"平台 {platform} 连续失败 {self.MAX_FAILURES_BEFORE_PAUSE} 次，暂停 10 分钟")

    async def _wait_platform_interval(self, platform: str) -> None:
        last = self._platform_last_request.get(platform, 0)
        elapsed = time.monotonic() - last
        if elapsed < self.MIN_PLATFORM_INTERVAL:
            await asyncio.sleep(self.MIN_PLATFORM_INTERVAL - elapsed)

    async def _random_delay(self, platform: str) -> None:
        lo, hi = self._platform_delays.get(platform, (1.0, 8.0))
        await asyncio.sleep(random.uniform(lo, hi))

    async def _retry_with_backoff(self, fn: Callable, platform: str, *args, **kwargs) -> Any:
        last_exc: Optional[Exception] = None
        for attempt in range(self.MAX_RETRIES):
            try:
                result = await fn(*args, **kwargs)
                self._failure_counts[platform] = 0
                return result
            except Exception as exc:
                last_exc = exc
                status_code = getattr(exc, "status", None) or getattr(exc, "code", None)
                if status_code in (403, 429) or "403" in str(exc) or "429" in str(exc):
                    wait = 2 ** attempt
                    logger.warning(f"[{platform}] HTTP {status_code}，{wait}s 后重试（第 {attempt+1} 次）")
                    await asyncio.sleep(wait)
                else:
                    break
        raise last_exc  # type: ignore

    async def request(
        self,
        platform: str,
        request_fn: Callable[..., Any],
        *args,
        **kwargs,
    ) -> Any:
        """统一请求入口，含限流、延时、重试、失败统计。"""
        if self._is_paused(platform):
            remaining = self._paused_until[platform] - time.monotonic()
            raise RuntimeError(f"平台 {platform} 已暂停，剩余 {remaining:.0f}s")

        async with self._global_semaphore:
            lock = self._get_platform_lock(platform)
            async with lock:
                await self._wait_platform_interval(platform)
                await self._random_delay(platform)
                headers = self._get_headers(platform)
                kwargs.setdefault("headers", headers)

                try:
                    result = await self._retry_with_backoff(request_fn, platform, *args, **kwargs)
                    self._platform_last_request[platform] = time.monotonic()
                    return result
                except Exception as exc:
                    self._failure_counts[platform] = self._failure_counts.get(platform, 0) + 1
                    if self._failure_counts[platform] >= self.MAX_FAILURES_BEFORE_PAUSE:
                        self._pause_platform(platform)
                    logger.error(f"[{platform}] 请求失败（连续 {self._failure_counts[platform]} 次）: {exc}")
                    raise

    def get_cookie_path(self, platform: str, cookie_path: Optional[str] = None) -> Optional[str]:
        """获取平台 Cookie 文件路径（如果有效）。"""
        if self._cookie_manager.is_cookie_valid(platform, cookie_path):
            return cookie_path or str(self._cookie_manager._cookie_dir / f"{platform}.txt")
        return None
