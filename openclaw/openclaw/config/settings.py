"""ConfigManager — 统一配置管理

使用 pydantic-settings 实现类型安全的配置校验，支持 YAML 文件加载和环境变量覆盖。
环境变量格式：OPENCLAW__LLM_PROVIDERS__OPENAI__API_KEY=xxx
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ── LLM 预设枚举 ──────────────────────────────────────────────────────────────

class LLMPreset(str, Enum):
    COST_EFFECTIVE = "cost_effective"  # 方案A：极致性价比
    QUALITY = "quality"                # 方案B：质量优先
    FLAGSHIP = "flagship"              # 方案B+：旗舰全开
    CHINA_ECO = "china_eco"            # 方案C：国内生态优先
    CUSTOM = "custom"                  # 自定义


# ── 嵌套配置模型（继承 BaseModel，避免嵌套 BaseSettings 问题）────────────────

class LLMProviderConfig(BaseModel):
    """LLM 服务商配置（API key + base URL）"""
    api_key: str = ""
    base_url: str


class LLMModelConfig(BaseModel):
    """单个 LLM 模型配置"""
    provider: str
    model: str
    max_tokens: int = 4096
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)


class PlatformConfig(BaseModel):
    """平台抓取配置"""
    cookie_path: Optional[str] = None
    cookie_refresh_days: int = 7
    request_delay: Tuple[float, float] = (2.0, 6.0)

    @field_validator("request_delay", mode="before")
    @classmethod
    def coerce_request_delay(cls, v: object) -> Tuple[float, float]:
        """支持从 YAML list 转换为 tuple"""
        if isinstance(v, (list, tuple)) and len(v) == 2:
            return (float(v[0]), float(v[1]))
        raise ValueError("request_delay 必须是包含两个浮点数的列表，例如 [2.0, 6.0]")


class StorageConfig(BaseModel):
    """数据存储配置"""
    db_type: str = "sqlite"   # sqlite | postgresql
    db_path: str = "./data/openclaw.db"
    cache_enabled: bool = True
    cache_ttl_hours: int = 72

    @field_validator("db_type")
    @classmethod
    def validate_db_type(cls, v: str) -> str:
        allowed = {"sqlite", "postgresql"}
        if v not in allowed:
            raise ValueError(f"db_type 必须是 {allowed} 之一，当前值：{v!r}")
        return v


# ── 主配置模型 ────────────────────────────────────────────────────────────────

class AppSettings(BaseSettings):
    """应用主配置，支持 YAML 文件加载和环境变量覆盖。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        env_prefix="OPENCLAW__",
        extra="ignore",
    )

    llm_providers: Dict[str, LLMProviderConfig] = Field(default_factory=dict)
    llm_preset: LLMPreset = LLMPreset.COST_EFFECTIVE
    llm_custom: Optional[Dict[str, LLMModelConfig]] = None
    platforms: Dict[str, PlatformConfig] = Field(default_factory=dict)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    proxy_enabled: bool = False
    log_level: str = "INFO"
    log_file: Optional[str] = None

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level 必须是 {allowed} 之一，当前值：{v!r}")
        return upper

    @model_validator(mode="after")
    def validate_custom_preset(self) -> "AppSettings":
        """当 llm_preset 为 CUSTOM 时，llm_custom 不能为空。"""
        if self.llm_preset == LLMPreset.CUSTOM and not self.llm_custom:
            raise ValueError(
                "llm_preset 为 'custom' 时，必须提供 llm_custom 配置（TopicClassifier、"
                "VideoAnalyzer、InsightsAggregator 三个环节）"
            )
        return self

    def get_active_model_config(self) -> Dict[str, LLMModelConfig]:
        """获取当前生效的模型配置字典。

        - 若 llm_preset != CUSTOM，始终使用预设方案（忽略 llm_custom）
        - 若 llm_preset == CUSTOM，使用 llm_custom
        """
        # 延迟导入避免循环依赖
        from openclaw.config.presets import get_preset

        if self.llm_preset != LLMPreset.CUSTOM:
            return get_preset(self.llm_preset.value)
        # CUSTOM 模式，model_validator 已保证 llm_custom 不为 None
        return self.llm_custom  # type: ignore[return-value]


# ── YAML 加载函数 ─────────────────────────────────────────────────────────────

def load_settings(config_path: str = "config.yaml") -> AppSettings:
    """从 YAML 文件加载配置，并支持通过环境变量覆盖。

    加载顺序（优先级从低到高）：
    1. 模型字段默认值
    2. YAML 配置文件
    3. .env 文件中的环境变量
    4. 系统环境变量

    Args:
        config_path: YAML 配置文件路径，默认为 "config.yaml"

    Returns:
        AppSettings 实例

    Raises:
        FileNotFoundError: 配置文件不存在时
        pydantic.ValidationError: 配置校验失败时，包含明确的错误信息
    """
    path = Path(config_path)
    yaml_data: dict = {}

    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}
    else:
        # 配置文件不存在时给出友好提示，但不强制要求（可全用环境变量）
        import warnings
        warnings.warn(
            f"配置文件 '{config_path}' 不存在，将仅使用环境变量和默认值。",
            stacklevel=2,
        )

    # pydantic-settings 支持通过构造函数传入初始值，环境变量会自动覆盖
    return AppSettings(**yaml_data)


# ── 模型配置持久化 ─────────────────────────────────────────────────────────────


class ConfigPersistence:
    """模型配置持久化管理，支持多套命名方案的保存和切换。"""

    _store_path: Path = Path.home() / ".openclaw" / "saved_configs.json"

    @classmethod
    def _load_store(cls) -> dict:
        if cls._store_path.exists():
            with cls._store_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    @classmethod
    def _save_store(cls, store: dict) -> None:
        cls._store_path.parent.mkdir(parents=True, exist_ok=True)
        with cls._store_path.open("w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, indent=2)

    @classmethod
    def save_config(cls, name: str, config: dict, mark_last_used: bool = True) -> None:
        """保存一套命名配置方案。"""
        store = cls._load_store()
        # 清除其他方案的 is_last_used 标记
        if mark_last_used:
            for k in store:
                store[k]["is_last_used"] = False
        store[name] = {"config": config, "is_last_used": mark_last_used}
        cls._save_store(store)

    @classmethod
    def load_config(cls, name: str) -> Optional[dict]:
        """加载指定名称的配置方案。"""
        store = cls._load_store()
        entry = store.get(name)
        return entry["config"] if entry else None

    @classmethod
    def load_last_used(cls) -> Optional[dict]:
        """加载上次使用的配置方案。"""
        store = cls._load_store()
        for entry in store.values():
            if entry.get("is_last_used"):
                return entry["config"]
        return None

    @classmethod
    def list_configs(cls) -> list[dict]:
        """列出所有已保存的配置方案。"""
        store = cls._load_store()
        return [
            {"name": k, "is_last_used": v.get("is_last_used", False)}
            for k, v in store.items()
        ]

    @classmethod
    def delete_config(cls, name: str) -> bool:
        """删除指定名称的配置方案，返回是否成功。"""
        store = cls._load_store()
        if name in store:
            del store[name]
            cls._save_store(store)
            return True
        return False


# ── 成本预估 ──────────────────────────────────────────────────────────────────

class CostEstimator:
    """LLM 调用成本预估器。"""

    # 每千 token 价格（美元），仅供预估参考
    PRICE_PER_1K_TOKENS: dict = {
        "doubao-1.5-pro-32k": {"input": 0.0008, "output": 0.002},
        "deepseek-chat": {"input": 0.00027, "output": 0.0011},
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4.5-preview": {"input": 0.075, "output": 0.15},
        "qwen-turbo": {"input": 0.0003, "output": 0.0006},
        "qwen-max": {"input": 0.004, "output": 0.012},
    }

    @classmethod
    def estimate(
        cls,
        model_configs: Dict[str, "LLMModelConfig"],
        num_videos: int = 20,
        avg_tokens_per_video: int = 3000,
    ) -> dict:
        """
        估算总成本。

        Returns:
            {
                "breakdown": [{"component": str, "model": str, "estimated_cost_usd": float}],
                "total_usd": float,
                "variance_note": str
            }
        """
        breakdown = []
        total = 0.0

        for component, model_cfg in model_configs.items():
            model = model_cfg.model
            prices = cls.PRICE_PER_1K_TOKENS.get(model, {"input": 0.001, "output": 0.003})

            # 估算每个环节的 token 消耗
            if component == "TopicClassifier":
                input_tokens = avg_tokens_per_video * num_videos
                output_tokens = 200 * num_videos
            elif component == "VideoAnalyzer":
                input_tokens = avg_tokens_per_video * num_videos
                output_tokens = 1000 * num_videos
            else:  # InsightsAggregator
                input_tokens = avg_tokens_per_video * num_videos // 2
                output_tokens = 2000

            cost = (input_tokens / 1000 * prices["input"] +
                    output_tokens / 1000 * prices["output"])
            breakdown.append({
                "component": component,
                "model": model,
                "estimated_cost_usd": round(cost, 4),
            })
            total += cost

        return {
            "breakdown": breakdown,
            "total_usd": round(total, 4),
            "variance_note": "实际成本可能因视频长度和内容复杂度波动 ±50%",
        }
