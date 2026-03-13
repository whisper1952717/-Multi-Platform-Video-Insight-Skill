"""VideoAnalyzer — 单视频深度分析模块，使用强 LLM。"""
from __future__ import annotations

import json
import logging
from typing import List, Optional

from openclaw.models.types import (
    CognitionFramework, CoreSignal, HighValueQuote,
    MethodologyFragment, TopicClassification, VideoAnalysis,
)

logger = logging.getLogger(__name__)

ANALYZER_SYSTEM = """你是一个专业的商业洞察分析师。
请从视频转录文本中提取核心商业信号、认知框架、方法论片段和高价值表达。
每个信号必须附带 confidence_score（0.0~1.0）和支撑证据。
评分标准：
- 0.9+：多次明确提及且有具体数据或案例支撑
- 0.7~0.9：明确提及且有一定论据
- 0.5~0.7：隐含提及需要推断
- <0.5：弱信号证据不足
输出严格遵循 JSON 格式，不要输出任何额外文字。"""

ANALYZER_USER_TEMPLATE = """主题分类结果：{topic_classification}

视频转录文本（分段）：
{segments}

请提取商业洞察，输出 JSON 格式，包含字段：
- core_signals: 核心信号列表，每项含 signal（信号描述）、evidence（原文证据）、confidence_score
- cognition_framework: 认知框架列表，每项含 framework（框架名称）、reasoning_chain（推理链）、confidence_score
- methodology_fragments: 方法论片段列表，每项含 method（方法名称）、applicable_scenario（适用场景）、confidence_score
- high_value_quotes: 高价值表达列表，每项含 quote（原文引用）、context（上下文说明）
- overall_quality: 整体质量评分（0.0~1.0）"""

FEW_SHOT_EXAMPLES = [
    {
        "role": "user",
        "content": "主题：AI创业\n内容：我们用三个月把产品从0做到月收入100万，核心是找到了一个被大公司忽视的细分市场。"
    },
    {
        "role": "assistant",
        "content": json.dumps({
            "core_signals": [{"signal": "细分市场切入策略", "evidence": "找到了一个被大公司忽视的细分市场", "confidence_score": 0.85}],
            "cognition_framework": [{"framework": "大公司盲区理论", "reasoning_chain": "大公司因规模效应忽视小市场→小市场对创业公司足够大→快速验证并占领", "confidence_score": 0.8}],
            "methodology_fragments": [{"method": "3个月MVP验证", "applicable_scenario": "早期创业产品验证", "confidence_score": 0.9}],
            "high_value_quotes": [{"quote": "找到了一个被大公司忽视的细分市场", "context": "描述创业成功的核心策略"}],
            "overall_quality": 0.85
        }, ensure_ascii=False)
    }
]

FALLBACK_ANALYSIS_SYSTEM = "请对以下视频内容做简短摘要，输出 JSON 格式：{\"summary\": \"摘要内容\", \"overall_quality\": 0.3}"


class VideoAnalyzer:
    """单视频深度分析，使用强 LLM + Few-shot 示例。"""

    def __init__(self, llm_client=None, model_config=None):
        self._llm_client = llm_client
        self._model_config = model_config

    async def analyze(
        self,
        segments: List[str],
        topic: TopicClassification,
        video_id: str = "unknown",
    ) -> VideoAnalysis:
        """深度分析视频内容，提取商业洞察。"""
        if not self._llm_client or not self._model_config:
            return self._empty_analysis(video_id)

        transcript_text = "\n".join(f"[段落{i+1}] {s}" for i, s in enumerate(segments[:10]))
        topic_str = f"主题：{topic.primary_topic}，类型：{topic.content_type.value}，商业相关度：{topic.business_relevance:.2f}"

        user_prompt = ANALYZER_USER_TEMPLATE.format(
            topic_classification=topic_str,
            segments=transcript_text[:6000],
        )

        try:
            response = await self._llm_client.call(
                model_config=self._model_config,
                system_prompt=ANALYZER_SYSTEM,
                user_prompt=user_prompt,
                few_shot_examples=FEW_SHOT_EXAMPLES,
            )

            data = json.loads(response) if isinstance(response, str) else response

            core_signals = [
                CoreSignal(
                    signal=s.get("signal", ""),
                    evidence=s.get("evidence", ""),
                    confidence_score=max(0.0, min(1.0, float(s.get("confidence_score", 0.5)))),
                )
                for s in data.get("core_signals", [])
            ]
            cognition_framework = [
                CognitionFramework(
                    framework=f.get("framework", ""),
                    reasoning_chain=f.get("reasoning_chain", ""),
                    confidence_score=max(0.0, min(1.0, float(f.get("confidence_score", 0.5)))),
                )
                for f in data.get("cognition_framework", [])
            ]
            methodology_fragments = [
                MethodologyFragment(
                    method=m.get("method", ""),
                    applicable_scenario=m.get("applicable_scenario", ""),
                    confidence_score=max(0.0, min(1.0, float(m.get("confidence_score", 0.5)))),
                )
                for m in data.get("methodology_fragments", [])
            ]
            high_value_quotes = [
                HighValueQuote(
                    quote=q.get("quote", ""),
                    context=q.get("context", ""),
                )
                for q in data.get("high_value_quotes", [])
            ]
            overall_quality = max(0.0, min(1.0, float(data.get("overall_quality", 0.5))))

            return VideoAnalysis(
                video_id=video_id,
                core_signals=core_signals,
                cognition_framework=cognition_framework,
                methodology_fragments=methodology_fragments,
                high_value_quotes=high_value_quotes,
                overall_quality=overall_quality,
            )

        except Exception as e:
            logger.error(f"[analyzer] 分析失败，降级为简单摘要: {e}")
            return await self._fallback_analysis(video_id, segments)

    async def _fallback_analysis(self, video_id: str, segments: List[str]) -> VideoAnalysis:
        """分析失败时降级为简单摘要模式。"""
        try:
            if self._llm_client and self._model_config:
                text = " ".join(segments)[:2000]
                response = await self._llm_client.call(
                    model_config=self._model_config,
                    system_prompt=FALLBACK_ANALYSIS_SYSTEM,
                    user_prompt=text,
                )
                data = json.loads(response) if isinstance(response, str) else {}
                summary = data.get("summary", "")
                quality = float(data.get("overall_quality", 0.3))
                return VideoAnalysis(
                    video_id=video_id,
                    core_signals=[CoreSignal(signal=summary, evidence="摘要", confidence_score=0.3)] if summary else [],
                    cognition_framework=[],
                    methodology_fragments=[],
                    high_value_quotes=[],
                    overall_quality=max(0.0, min(1.0, quality)),
                )
        except Exception:
            pass
        return self._empty_analysis(video_id)

    def _empty_analysis(self, video_id: str) -> VideoAnalysis:
        return VideoAnalysis(
            video_id=video_id,
            core_signals=[],
            cognition_framework=[],
            methodology_fragments=[],
            high_value_quotes=[],
            overall_quality=0.0,
        )
