"""LLM 预设方案定义

四种预设方案，每种方案配置 TopicClassifier、VideoAnalyzer、InsightsAggregator 三个环节的 LLM 模型。
"""

from typing import Dict
from openclaw.config.settings import LLMModelConfig


# 预设方案 A：极致性价比
# TopicClassifier=Doubao-1.5-Pro, VideoAnalyzer=DeepSeek-V3, InsightsAggregator=DeepSeek-V3
COST_EFFECTIVE_PRESET: Dict[str, LLMModelConfig] = {
    "TopicClassifier": LLMModelConfig(
        provider="doubao",
        model="doubao-1.5-pro-32k",
        max_tokens=1024,
        temperature=0.1,
    ),
    "VideoAnalyzer": LLMModelConfig(
        provider="deepseek",
        model="deepseek-chat",
        max_tokens=4096,
        temperature=0.3,
    ),
    "InsightsAggregator": LLMModelConfig(
        provider="deepseek",
        model="deepseek-chat",
        max_tokens=4096,
        temperature=0.3,
    ),
}

# 预设方案 B：质量优先
# TopicClassifier=Qwen-Turbo, VideoAnalyzer=GPT-4o, InsightsAggregator=GPT-4o
QUALITY_PRESET: Dict[str, LLMModelConfig] = {
    "TopicClassifier": LLMModelConfig(
        provider="qwen",
        model="qwen-turbo",
        max_tokens=1024,
        temperature=0.1,
    ),
    "VideoAnalyzer": LLMModelConfig(
        provider="openai",
        model="gpt-4o",
        max_tokens=4096,
        temperature=0.3,
    ),
    "InsightsAggregator": LLMModelConfig(
        provider="openai",
        model="gpt-4o",
        max_tokens=4096,
        temperature=0.3,
    ),
}

# 预设方案 B+：旗舰全开
# TopicClassifier=Qwen-Turbo, VideoAnalyzer=GPT-5.4, InsightsAggregator=GPT-5.4
FLAGSHIP_PRESET: Dict[str, LLMModelConfig] = {
    "TopicClassifier": LLMModelConfig(
        provider="qwen",
        model="qwen-turbo",
        max_tokens=1024,
        temperature=0.1,
    ),
    "VideoAnalyzer": LLMModelConfig(
        provider="openai",
        model="gpt-4.5-preview",
        max_tokens=8192,
        temperature=0.3,
    ),
    "InsightsAggregator": LLMModelConfig(
        provider="openai",
        model="gpt-4.5-preview",
        max_tokens=8192,
        temperature=0.3,
    ),
}

# 预设方案 C：国内生态优先
# TopicClassifier=Qwen-Turbo, VideoAnalyzer=Qwen-Max, InsightsAggregator=Qwen-Max
CHINA_ECO_PRESET: Dict[str, LLMModelConfig] = {
    "TopicClassifier": LLMModelConfig(
        provider="qwen",
        model="qwen-turbo",
        max_tokens=1024,
        temperature=0.1,
    ),
    "VideoAnalyzer": LLMModelConfig(
        provider="qwen",
        model="qwen-max",
        max_tokens=4096,
        temperature=0.3,
    ),
    "InsightsAggregator": LLMModelConfig(
        provider="qwen",
        model="qwen-max",
        max_tokens=4096,
        temperature=0.3,
    ),
}

# 预设方案映射表
PRESETS: Dict[str, Dict[str, LLMModelConfig]] = {
    "cost_effective": COST_EFFECTIVE_PRESET,
    "quality": QUALITY_PRESET,
    "flagship": FLAGSHIP_PRESET,
    "china_eco": CHINA_ECO_PRESET,
}


def get_preset(preset_name: str) -> Dict[str, LLMModelConfig]:
    """根据预设名称获取对应的模型配置字典。

    Args:
        preset_name: 预设方案名称（cost_effective / quality / flagship / china_eco）

    Returns:
        包含三个环节模型配置的字典

    Raises:
        ValueError: 当预设名称不存在时
    """
    if preset_name not in PRESETS:
        valid = ", ".join(PRESETS.keys())
        raise ValueError(f"未知预设方案 '{preset_name}'，有效选项：{valid}")
    return PRESETS[preset_name]
