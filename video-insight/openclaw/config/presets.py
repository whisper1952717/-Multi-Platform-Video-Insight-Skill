"""LLM 预设方案定义

预设方案配置 TopicClassifier、VideoAnalyzer、InsightsAggregator 三个环节的 LLM 模型。
系统会根据用户已配置的 API key 自动推荐最优预设，用户也可手动选择或逐模块调整。
"""

from typing import Dict, List, Optional
from openclaw.config.settings import LLMModelConfig


# ── 预设方案 ──────────────────────────────────────────────────────────────────

COST_EFFECTIVE_PRESET: Dict[str, LLMModelConfig] = {
    "TopicClassifier": LLMModelConfig(provider="doubao",   model="doubao-1.5-pro-32k", max_tokens=1024, temperature=0.1),
    "VideoAnalyzer":   LLMModelConfig(provider="deepseek", model="deepseek-chat",       max_tokens=4096, temperature=0.3),
    "InsightsAggregator": LLMModelConfig(provider="deepseek", model="deepseek-chat",    max_tokens=4096, temperature=0.3),
}

QUALITY_PRESET: Dict[str, LLMModelConfig] = {
    "TopicClassifier": LLMModelConfig(provider="qwen",   model="qwen-turbo", max_tokens=1024, temperature=0.1),
    "VideoAnalyzer":   LLMModelConfig(provider="openai", model="gpt-4o",     max_tokens=4096, temperature=0.3),
    "InsightsAggregator": LLMModelConfig(provider="openai", model="gpt-4o",  max_tokens=4096, temperature=0.3),
}

FLAGSHIP_PRESET: Dict[str, LLMModelConfig] = {
    "TopicClassifier": LLMModelConfig(provider="qwen",   model="qwen-turbo",     max_tokens=1024, temperature=0.1),
    "VideoAnalyzer":   LLMModelConfig(provider="openai", model="gpt-4.5-preview", max_tokens=8192, temperature=0.3),
    "InsightsAggregator": LLMModelConfig(provider="openai", model="gpt-4.5-preview", max_tokens=8192, temperature=0.3),
}

CHINA_ECO_PRESET: Dict[str, LLMModelConfig] = {
    "TopicClassifier": LLMModelConfig(provider="qwen", model="qwen-turbo", max_tokens=1024, temperature=0.1),
    "VideoAnalyzer":   LLMModelConfig(provider="qwen", model="qwen-max",   max_tokens=4096, temperature=0.3),
    "InsightsAggregator": LLMModelConfig(provider="qwen", model="qwen-max", max_tokens=4096, temperature=0.3),
}

DEEPSEEK_ONLY_PRESET: Dict[str, LLMModelConfig] = {
    "TopicClassifier": LLMModelConfig(provider="deepseek", model="deepseek-chat", max_tokens=1024, temperature=0.1),
    "VideoAnalyzer":   LLMModelConfig(provider="deepseek", model="deepseek-chat", max_tokens=4096, temperature=0.3),
    "InsightsAggregator": LLMModelConfig(provider="deepseek", model="deepseek-chat", max_tokens=4096, temperature=0.3),
}

OPENAI_ONLY_PRESET: Dict[str, LLMModelConfig] = {
    "TopicClassifier": LLMModelConfig(provider="openai", model="gpt-4o-mini", max_tokens=1024, temperature=0.1),
    "VideoAnalyzer":   LLMModelConfig(provider="openai", model="gpt-4o",      max_tokens=4096, temperature=0.3),
    "InsightsAggregator": LLMModelConfig(provider="openai", model="gpt-4o",   max_tokens=4096, temperature=0.3),
}

QWEN_ONLY_PRESET: Dict[str, LLMModelConfig] = {
    "TopicClassifier": LLMModelConfig(provider="qwen", model="qwen-turbo", max_tokens=1024, temperature=0.1),
    "VideoAnalyzer":   LLMModelConfig(provider="qwen", model="qwen-plus",  max_tokens=4096, temperature=0.3),
    "InsightsAggregator": LLMModelConfig(provider="qwen", model="qwen-max", max_tokens=4096, temperature=0.3),
}

MINIMAX_ONLY_PRESET: Dict[str, LLMModelConfig] = {
    "TopicClassifier": LLMModelConfig(provider="minimax", model="MiniMax-Text-01",  max_tokens=1024, temperature=0.1),
    "VideoAnalyzer":   LLMModelConfig(provider="minimax", model="MiniMax-M2.5",     max_tokens=4096, temperature=0.3),
    "InsightsAggregator": LLMModelConfig(provider="minimax", model="MiniMax-M2.5",  max_tokens=4096, temperature=0.3),
}

GLM_ONLY_PRESET: Dict[str, LLMModelConfig] = {
    "TopicClassifier": LLMModelConfig(provider="zhipu", model="glm-4-flash", max_tokens=1024, temperature=0.1),
    "VideoAnalyzer":   LLMModelConfig(provider="zhipu", model="glm-4-plus",  max_tokens=4096, temperature=0.3),
    "InsightsAggregator": LLMModelConfig(provider="zhipu", model="glm-4-plus", max_tokens=4096, temperature=0.3),
}

KIMI_ONLY_PRESET: Dict[str, LLMModelConfig] = {
    "TopicClassifier": LLMModelConfig(provider="moonshot", model="moonshot-v1-8k",   max_tokens=1024, temperature=0.1),
    "VideoAnalyzer":   LLMModelConfig(provider="moonshot", model="moonshot-v1-128k", max_tokens=4096, temperature=0.3),
    "InsightsAggregator": LLMModelConfig(provider="moonshot", model="moonshot-v1-128k", max_tokens=4096, temperature=0.3),
}

OPENROUTER_PRESET: Dict[str, LLMModelConfig] = {
    "TopicClassifier": LLMModelConfig(provider="openrouter", model="meta-llama/llama-3.1-8b-instruct:free", max_tokens=1024, temperature=0.1),
    "VideoAnalyzer":   LLMModelConfig(provider="openrouter", model="deepseek/deepseek-chat",                max_tokens=4096, temperature=0.3),
    "InsightsAggregator": LLMModelConfig(provider="openrouter", model="deepseek/deepseek-chat",             max_tokens=4096, temperature=0.3),
}

# openclaw gateway 预设：复用用户已配置的 ChatGPT/Codex 订阅
# 分类用轻量模型，分析和聚合用用户订阅的旗舰模型
OPENCLAW_GATEWAY_PRESET: Dict[str, LLMModelConfig] = {
    "TopicClassifier":    LLMModelConfig(provider="openclaw", model="openai-codex/gpt-5.4", max_tokens=1024, temperature=0.1),
    "VideoAnalyzer":      LLMModelConfig(provider="openclaw", model="openai-codex/gpt-5.4", max_tokens=4096, temperature=0.3),
    "InsightsAggregator": LLMModelConfig(provider="openclaw", model="openai-codex/gpt-5.4", max_tokens=4096, temperature=0.3),
}

# ── 预设映射表 ────────────────────────────────────────────────────────────────

PRESETS: Dict[str, Dict[str, LLMModelConfig]] = {
    "cost_effective":  COST_EFFECTIVE_PRESET,
    "quality":         QUALITY_PRESET,
    "flagship":        FLAGSHIP_PRESET,
    "china_eco":       CHINA_ECO_PRESET,
    "deepseek_only":   DEEPSEEK_ONLY_PRESET,
    "openai_only":     OPENAI_ONLY_PRESET,
    "qwen_only":       QWEN_ONLY_PRESET,
    "minimax_only":    MINIMAX_ONLY_PRESET,
    "glm_only":        GLM_ONLY_PRESET,
    "kimi_only":       KIMI_ONLY_PRESET,
    "openrouter":         OPENROUTER_PRESET,
    "openclaw_gateway":   OPENCLAW_GATEWAY_PRESET,
}

PRESET_DESCRIPTIONS: Dict[str, str] = {
    "cost_effective": "极致性价比（Doubao分类 + DeepSeek分析，需2个key）",
    "quality":        "质量优先（Qwen分类 + GPT-4o分析，需2个key）",
    "flagship":       "旗舰全开（Qwen分类 + GPT-4.5分析，需2个key）",
    "china_eco":      "国内生态（全程通义千问，需1个key）",
    "deepseek_only":  "仅 DeepSeek（全程 DeepSeek-V3，需1个key）",
    "openai_only":    "仅 OpenAI（GPT-4o-mini分类 + GPT-4o分析，需1个key）",
    "qwen_only":      "仅通义千问（Turbo分类 + Max分析，需1个key）",
    "minimax_only":   "仅 MiniMax（M2.5，超大上下文，需1个key）",
    "glm_only":       "仅智谱GLM（Flash免费分类 + Plus分析，需1个key）",
    "kimi_only":      "仅 Kimi（长文本强，128K上下文，需1个key）",
    "openrouter":        "OpenRouter（一个key访问多模型，推荐新手）",
    "openclaw_gateway":  "openclaw Gateway（复用你的ChatGPT/Codex订阅，无需额外key）",
}

# ── provider 元数据 ───────────────────────────────────────────────────────────

# provider → 对应的环境变量名
PROVIDER_ENV_MAP: Dict[str, str] = {
    "openai":      "OPENAI_API_KEY",
    "deepseek":    "DEEPSEEK_API_KEY",
    "doubao":      "VOLCENGINE_API_KEY",
    "qwen":        "DASHSCOPE_API_KEY",
    "minimax":     "MINIMAX_API_KEY",
    "zhipu":       "ZHIPU_API_KEY",
    "moonshot":    "MOONSHOT_API_KEY",
    "openrouter":  "OPENROUTER_API_KEY",
    "openclaw":    "",   # 使用本地 openclaw gateway，无需 API key
}

# provider → 推荐模型列表（含价格和特点说明，价格单位：$/百万token，数据截至2026年3月）
PROVIDER_RECOMMENDED_MODELS: Dict[str, List[Dict]] = {
    "openai": [
        {"model": "gpt-4o-mini",     "desc": "快速轻量，适合分类",          "price": "$0.15/$0.60"},
        {"model": "gpt-4o",          "desc": "综合能力强，均衡之选",         "price": "$2.50/$10.00"},
        {"model": "gpt-4.5-preview", "desc": "旗舰质量，成本较高",           "price": "$75/$150"},
    ],
    "deepseek": [
        {"model": "deepseek-chat",      "desc": "DeepSeek-V3，性价比标杆",   "price": "$0.27/$1.10"},
        {"model": "deepseek-reasoner",  "desc": "R1推理模型，复杂分析更强",  "price": "$0.55/$2.19"},
    ],
    "doubao": [
        {"model": "doubao-1.5-pro-32k",  "desc": "字节旗舰，国内最便宜之一", "price": "¥0.8/¥2.0（人民币）"},
        {"model": "doubao-1.5-lite-32k", "desc": "轻量版，适合分类任务",     "price": "¥0.3/¥0.6（人民币）"},
    ],
    "qwen": [
        {"model": "qwen-turbo",   "desc": "极速轻量，适合分类",              "price": "$0.05/$0.20"},
        {"model": "qwen-plus",    "desc": "均衡性能，推荐分析环节",          "price": "$0.40/$1.20"},
        {"model": "qwen-max",     "desc": "旗舰质量",                        "price": "$1.60/$6.40"},
    ],
    "minimax": [
        {"model": "MiniMax-Text-01",      "desc": "轻量快速，适合分类",      "price": "$0.10/$0.55"},
        {"model": "MiniMax-M2.5",         "desc": "旗舰，1M上下文，benchmark顶级", "price": "$0.30/$1.20"},
        {"model": "MiniMax-M2.5-Lightning","desc": "高速版，实时场景",        "price": "$0.30/$2.40"},
    ],
    "zhipu": [
        {"model": "glm-4-flash",  "desc": "完全免费，适合分类/测试",         "price": "免费"},
        {"model": "glm-4-plus",   "desc": "均衡性能，200K上下文",            "price": "$0.60/$2.20"},
        {"model": "glm-4-long",   "desc": "超长上下文专用（1M token）",      "price": "$0.07/$0.07"},
    ],
    "moonshot": [
        {"model": "moonshot-v1-8k",   "desc": "快速，适合短文本分类",        "price": "$0.15/$0.60"},
        {"model": "moonshot-v1-32k",  "desc": "中等上下文，均衡",            "price": "$0.40/$1.60"},
        {"model": "moonshot-v1-128k", "desc": "长文本强，128K上下文",        "price": "$0.60/$2.50"},
    ],
    "openrouter": [
        {"model": "meta-llama/llama-3.1-8b-instruct:free", "desc": "免费，适合分类",    "price": "免费"},
        {"model": "deepseek/deepseek-chat",                 "desc": "DeepSeek-V3，推荐", "price": "$0.27/$1.10"},
        {"model": "minimax/minimax-m2.5",                   "desc": "MiniMax旗舰",       "price": "$0.30/$1.20"},
        {"model": "google/gemini-flash-1.5",                "desc": "谷歌，速度快",      "price": "$0.075/$0.30"},
        {"model": "anthropic/claude-3-5-sonnet",            "desc": "Claude，长文本强",  "price": "$3.00/$15.00"},
    ],
    "openclaw": [
        {"model": "openai-codex/gpt-5.4",          "desc": "ChatGPT订阅 OAuth，旗舰质量", "price": "订阅包含"},
        {"model": "openai-codex/gpt-5.3-codex-spark", "desc": "Codex Spark，需Pro订阅",  "price": "订阅包含"},
        {"model": "openai/gpt-5.4",                "desc": "OpenAI API key直连",          "price": "按token计费"},
    ],
}


# ── 核心函数 ──────────────────────────────────────────────────────────────────

def get_preset(preset_name: str) -> Dict[str, LLMModelConfig]:
    """根据预设名称获取对应的模型配置字典。"""
    if preset_name not in PRESETS:
        valid = ", ".join(PRESETS.keys())
        raise ValueError(f"未知预设方案 '{preset_name}'，有效选项：{valid}")
    return PRESETS[preset_name]


def get_available_providers(llm_providers: dict) -> list:
    """返回已配置了有效 api_key 的 provider 列表。
    
    openclaw provider 始终视为可用（使用本地 gateway，无需真实 API key）。
    """
    result = []
    for k, v in llm_providers.items():
        if k == "openclaw":
            result.append(k)  # gateway 始终可用
            continue
        key = getattr(v, "api_key", "") or (isinstance(v, dict) and v.get("api_key", ""))
        if key:
            result.append(k)
    return result


def recommend_preset(llm_providers: dict) -> Optional[str]:
    """根据已配置的 provider 自动推荐最优预设。

    推荐优先级：
    1. openrouter → openrouter（一个key最省事）
    2. deepseek + doubao → cost_effective（性价比最优）
    3. qwen + openai → quality
    4. deepseek only → deepseek_only
    5. openai only → openai_only
    6. qwen only → china_eco
    7. minimax only → minimax_only
    8. zhipu only → glm_only
    9. moonshot only → kimi_only
    """
    available = set(get_available_providers(llm_providers))
    if not available:
        return None
    if "openrouter" in available:
        return "openrouter"
    if "deepseek" in available and "doubao" in available:
        return "cost_effective"
    if "qwen" in available and "openai" in available:
        return "quality"
    if "deepseek" in available:
        return "deepseek_only"
    if "openai" in available:
        return "openai_only"
    if "qwen" in available:
        return "china_eco"
    if "minimax" in available:
        return "minimax_only"
    if "zhipu" in available:
        return "glm_only"
    if "moonshot" in available:
        return "kimi_only"
    # openclaw gateway 兜底：用户有订阅但没配其他 key
    if "openclaw" in available:
        return "openclaw_gateway"
    return None
