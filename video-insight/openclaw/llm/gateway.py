"""openclaw gateway 工具函数

负责探测本地 openclaw gateway 状态、查询当前配置的模型。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import aiohttp


# gateway 默认端口
_DEFAULT_GATEWAY_URL = "http://localhost:9099"

# 用户偏好持久化路径（记录"一直用 gateway"的选择）
_PREFS_PATH = Path.home() / ".openclaw" / "video_insight_prefs.json"


def get_gateway_url() -> str:
    url = os.environ.get("OPENCLAW_GATEWAY_URL", "").strip()
    return url.rstrip("/") if url else _DEFAULT_GATEWAY_URL


async def probe_gateway() -> Optional[dict]:
    """探测 gateway 是否在线，并返回当前主模型信息。

    Returns:
        {"model": "openai-codex/gpt-5.4", "provider": "openai-codex"} 或 None（不可达）
    """
    base = get_gateway_url()
    token = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "").strip()
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    try:
        async with aiohttp.ClientSession() as session:
            # 先尝试 /v1/models（标准 OpenAI 兼容端点）
            async with session.get(
                f"{base}/v1/models", headers=headers, timeout=aiohttp.ClientTimeout(total=3)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = data.get("data", [])
                    if models:
                        # 取第一个作为当前主模型
                        primary = models[0].get("id", "unknown")
                        provider = primary.split("/")[0] if "/" in primary else "openclaw"
                        return {"model": primary, "provider": provider, "all_models": [m["id"] for m in models]}
                    return {"model": "unknown", "provider": "openclaw", "all_models": []}
    except Exception:
        pass
    return None


def load_gateway_pref() -> Optional[str]:
    """读取用户对 gateway 的使用偏好。

    Returns:
        "always" | "never" | None（未设置）
    """
    if _PREFS_PATH.exists():
        try:
            data = json.loads(_PREFS_PATH.read_text())
            return data.get("use_gateway")
        except Exception:
            pass
    return None


def save_gateway_pref(pref: str) -> None:
    """保存用户偏好：always / never。"""
    _PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if _PREFS_PATH.exists():
        try:
            existing = json.loads(_PREFS_PATH.read_text())
        except Exception:
            pass
    existing["use_gateway"] = pref
    _PREFS_PATH.write_text(json.dumps(existing, ensure_ascii=False, indent=2))
