"""Prompt 模板定义。"""

# ── TopicClassifier Prompt ────────────────────────────────────────────────────

TOPIC_CLASSIFIER_SYSTEM = """你是一个专业的视频内容分类助手。
请分析给定的视频转录文本，输出 JSON 格式的分类结果。
content_type 必须是以下之一：观点输出、教程讲解、案例分析、行业分析、产品推荐、其他
business_relevance 是 0.0~1.0 的浮点数，表示内容与商业分析的相关程度。
输出严格遵循 JSON Schema，不要输出任何额外文字。"""

TOPIC_CLASSIFIER_USER = """请对以下视频转录文本进行主题分类：

{transcript}

输出 JSON 格式，包含字段：primary_topic, secondary_topics, content_type, business_relevance, skip_reason（可为 null）"""

# ── VideoAnalyzer Prompt ──────────────────────────────────────────────────────

VIDEO_ANALYZER_SYSTEM = """你是一个专业的商业洞察分析师。
请从视频转录文本中提取核心商业信号、认知框架、方法论片段和高价值表达。
每个信号必须附带 confidence_score（0.0~1.0）和支撑证据。
评分标准：
- 0.9+：多次明确提及且有具体数据或案例支撑
- 0.7~0.9：明确提及且有一定论据
- 0.5~0.7：隐含提及需要推断
- <0.5：弱信号证据不足
输出严格遵循 JSON Schema，不要输出任何额外文字。"""

VIDEO_ANALYZER_USER = """主题分类结果：{topic_classification}

视频转录文本（分段）：
{segments}

请提取商业洞察，输出 JSON 格式，包含字段：core_signals, cognition_framework, methodology_fragments, high_value_quotes, overall_quality"""

VIDEO_ANALYZER_FEW_SHOT = [
    {
        "role": "user",
        "content": "主题：AI创业\n内容：我们用三个月把产品从0做到月收入100万，核心是找到了一个被大公司忽视的细分市场。"
    },
    {
        "role": "assistant",
        "content": '{"core_signals": [{"signal": "细分市场切入策略", "evidence": "找到了一个被大公司忽视的细分市场", "confidence_score": 0.85}], "cognition_framework": [{"framework": "大公司盲区理论", "reasoning_chain": "大公司因规模效应忽视小市场→小市场对创业公司足够大→快速验证并占领", "confidence_score": 0.8}], "methodology_fragments": [{"method": "3个月MVP验证", "applicable_scenario": "早期创业产品验证", "confidence_score": 0.9}], "high_value_quotes": [{"quote": "找到了一个被大公司忽视的细分市场", "context": "描述创业成功的核心策略"}], "overall_quality": 0.85}'
    }
]

# ── InsightsAggregator Prompt ─────────────────────────────────────────────────

AGGREGATOR_MODE1_SYSTEM = """你是一个专业的商业洞察聚合分析师。
请将多个视频的分析结果聚合为结构化的洞察报告。
对相似信号进行去重合并，confidence_score 取加权平均。
仅保留有多个信号支撑的商业机会。
生成 3~5 条对用户最有价值的启发（insights_for_me）。
输出严格遵循 JSON Schema。"""

AGGREGATOR_MODE1_USER = """以下是同一博主的多个视频分析结果：

{analyses}

请聚合输出 Mode1 洞察报告，包含字段：core_signals, cognition_framework, methodology_fragments, business_opportunities, high_value_quotes, insights_for_me, quality_summary"""

AGGREGATOR_MODE2_SYSTEM = """你是一个专业的行业趋势分析师。
请将多个博主的视频分析结果聚合为赛道洞察报告。
识别趋势信号、博主间的共识与分歧、通用方法论和商业机会。
共识点需标注支持比例，分歧点需标注双方立场。
生成 3~5 条对用户最有价值的启发（insights_for_me）。
输出严格遵循 JSON Schema。"""

AGGREGATOR_MODE2_USER = """以下是多个博主的视频分析结果：

{analyses}

请聚合输出 Mode2 赛道洞察报告，包含字段：trend_signals, consensus_and_divergence, common_methodology, business_opportunities, high_value_quotes, insights_for_me, quality_summary"""
