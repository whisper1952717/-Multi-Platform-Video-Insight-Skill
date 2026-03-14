"""ConfigManager 单元测试。"""
import os
import tempfile
import textwrap
import pytest
from pydantic import ValidationError


# ── YAML 加载 ─────────────────────────────────────────────────────────────────

def test_load_settings_defaults():
    """无配置文件时应使用默认值。"""
    import warnings
    from openclaw.config.settings import load_settings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        settings = load_settings("/nonexistent/path.yaml")
    assert settings.llm_preset.value == "cost_effective"
    assert settings.log_level == "INFO"
    assert settings.proxy_enabled is False


def test_load_settings_from_yaml():
    """从 YAML 文件加载配置。"""
    from openclaw.config.settings import load_settings
    yaml_content = textwrap.dedent("""\
        llm_preset: quality
        log_level: DEBUG
        proxy_enabled: false
        storage:
          db_type: sqlite
          cache_ttl_hours: 48
    """)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write(yaml_content)
        path = f.name
    try:
        settings = load_settings(path)
        assert settings.llm_preset.value == "quality"
        assert settings.log_level == "DEBUG"
        assert settings.storage.cache_ttl_hours == 48
    finally:
        os.unlink(path)


def test_load_settings_invalid_db_type():
    """无效的 db_type 应抛出 ValidationError。"""
    from openclaw.config.settings import load_settings
    yaml_content = "storage:\n  db_type: mysql\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write(yaml_content)
        path = f.name
    try:
        with pytest.raises(ValidationError):
            load_settings(path)
    finally:
        os.unlink(path)


def test_load_settings_invalid_log_level():
    """无效的 log_level 应抛出 ValidationError。"""
    from openclaw.config.settings import AppSettings
    with pytest.raises(ValidationError):
        AppSettings(log_level="VERBOSE")


# ── 环境变量覆盖 ──────────────────────────────────────────────────────────────

def test_env_override_log_level(monkeypatch):
    """环境变量应覆盖 YAML 配置。"""
    monkeypatch.setenv("OPENCLAW__LOG_LEVEL", "WARNING")
    from openclaw.config.settings import AppSettings
    settings = AppSettings()
    assert settings.log_level == "WARNING"


def test_env_override_proxy_enabled(monkeypatch):
    """环境变量覆盖 proxy_enabled。"""
    monkeypatch.setenv("OPENCLAW__PROXY_ENABLED", "true")
    from openclaw.config.settings import AppSettings
    settings = AppSettings()
    assert settings.proxy_enabled is True


# ── 预设方案 ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("preset_name", ["cost_effective", "quality", "flagship", "china_eco"])
def test_preset_has_three_components(preset_name):
    """每个预设方案应包含三个 LLM 环节配置。"""
    from openclaw.config.presets import get_preset
    preset = get_preset(preset_name)
    assert "TopicClassifier" in preset
    assert "VideoAnalyzer" in preset
    assert "InsightsAggregator" in preset


def test_preset_invalid_name():
    """无效预设名称应抛出 ValueError。"""
    from openclaw.config.presets import get_preset
    with pytest.raises(ValueError, match="未知预设方案"):
        get_preset("nonexistent_preset")


def test_get_active_model_config_uses_preset():
    """非 CUSTOM 模式下，get_active_model_config 应返回预设配置。"""
    from openclaw.config.settings import AppSettings, LLMPreset
    settings = AppSettings(llm_preset=LLMPreset.QUALITY)
    config = settings.get_active_model_config()
    assert config["VideoAnalyzer"].model == "gpt-4o"


# ── llm_preset vs llm_custom 优先级 ──────────────────────────────────────────

def test_preset_takes_priority_over_custom():
    """非 CUSTOM 模式下，即使提供了 llm_custom，也应使用预设方案。"""
    from openclaw.config.settings import AppSettings, LLMPreset, LLMModelConfig
    custom = {
        "TopicClassifier": LLMModelConfig(provider="custom", model="custom-model"),
        "VideoAnalyzer": LLMModelConfig(provider="custom", model="custom-model"),
        "InsightsAggregator": LLMModelConfig(provider="custom", model="custom-model"),
    }
    settings = AppSettings(llm_preset=LLMPreset.COST_EFFECTIVE, llm_custom=custom)
    config = settings.get_active_model_config()
    # 应使用预设，而非 custom-model
    assert config["VideoAnalyzer"].model != "custom-model"


def test_custom_preset_requires_llm_custom():
    """llm_preset=CUSTOM 但未提供 llm_custom 时应抛出 ValidationError。"""
    from openclaw.config.settings import AppSettings, LLMPreset
    with pytest.raises(ValidationError, match="llm_custom"):
        AppSettings(llm_preset=LLMPreset.CUSTOM, llm_custom=None)


def test_custom_preset_uses_llm_custom():
    """llm_preset=CUSTOM 时应使用 llm_custom 配置。"""
    from openclaw.config.settings import AppSettings, LLMPreset, LLMModelConfig
    custom = {
        "TopicClassifier": LLMModelConfig(provider="my_provider", model="my-model-small"),
        "VideoAnalyzer": LLMModelConfig(provider="my_provider", model="my-model-large"),
        "InsightsAggregator": LLMModelConfig(provider="my_provider", model="my-model-large"),
    }
    settings = AppSettings(llm_preset=LLMPreset.CUSTOM, llm_custom=custom)
    config = settings.get_active_model_config()
    assert config["VideoAnalyzer"].model == "my-model-large"


# ── 成本预估 ──────────────────────────────────────────────────────────────────

def test_cost_estimator_returns_three_components():
    """成本预估应包含三个环节的分项。"""
    from openclaw.config.settings import CostEstimator
    from openclaw.config.presets import get_preset
    preset = get_preset("cost_effective")
    result = CostEstimator.estimate(preset, num_videos=10)
    assert len(result["breakdown"]) == 3
    assert result["total_usd"] > 0
    assert "variance_note" in result


def test_cost_estimator_total_equals_sum():
    """总成本应等于各分项之和。"""
    from openclaw.config.settings import CostEstimator
    from openclaw.config.presets import get_preset
    preset = get_preset("quality")
    result = CostEstimator.estimate(preset, num_videos=5)
    total_from_breakdown = sum(item["estimated_cost_usd"] for item in result["breakdown"])
    assert abs(result["total_usd"] - round(total_from_breakdown, 4)) < 0.001
