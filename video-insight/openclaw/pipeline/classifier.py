"""TopicClassifier — 主题分类模块，使用轻量 LLM。"""
from __future__ import annotations

import json
import logging
from typing import List, Optional

from openclaw.models.types import ContentType, TopicClassification

logger = logging.getLogger(__name__)

CLASSIFIER_SYSTEM = """你是一个专业的视频内容分类助手。
请分析给定的视频转录文本，输出 JSON 格式的分类结果。
content_type 必须是以下之一：观点输出、教程讲解、案例分析、行业分析、产品推荐、其他
business_relevance 是 0.0~1.0 的浮点数，表示内容与商业分析的相关程度。
输出严格遵循 JSON 格式，不要输出任何额外文字。"""

CLASSIFIER_USER_TEMPLATE = """请对以下视频转录文本进行主题分类：

{transcript}

输出 JSON 格式，包含字段：
- primary_topic: 主要主题（字符串）
- secondary_topics: 次要主题列表（字符串数组）
- content_type: 内容类型（观点输出/教程讲解/案例分析/行业分析/产品推荐/其他）
- business_relevance: 商业相关度（0.0~1.0）
- skip_reason: 跳过原因（如果 business_relevance < 0.3，说明原因；否则为 null）"""


class TopicClassifier:
    """主题分类模块，使用轻量 LLM 进行前置过滤。"""

    SKIP_THRESHOLD = 0.3

    def __init__(self, llm_client=None, model_config=None):
        self._llm_client = llm_client
        self._model_config = model_config

    async def classify(self, segments: List[str]) -> TopicClassification:
        """对视频分段文本进行主题分类。"""
        # 合并分段，截取前 3000 字符用于分类
        transcript = " ".join(segments)[:3000]

        if not self._llm_client or not self._model_config:
            # 无 LLM 时返回默认分类
            return TopicClassification(
                primary_topic="未知",
                secondary_topics=[],
                content_type=ContentType.OTHER,
                business_relevance=0.5,
            )

        try:
            user_prompt = CLASSIFIER_USER_TEMPLATE.format(transcript=transcript)
            response = await self._llm_client.call(
                model_config=self._model_config,
                system_prompt=CLASSIFIER_SYSTEM,
                user_prompt=user_prompt,
            )

            # 解析 JSON 响应
            if isinstance(response, str):
                data = json.loads(response)
            else:
                data = response

            # 映射 content_type
            content_type_map = {
                "观点输出": ContentType.OPINION,
                "教程讲解": ContentType.TUTORIAL,
                "案例分析": ContentType.CASE_STUDY,
                "行业分析": ContentType.INDUSTRY,
                "产品推荐": ContentType.PRODUCT,
                "其他": ContentType.OTHER,
            }
            ct_str = data.get("content_type", "其他")
            content_type = content_type_map.get(ct_str, ContentType.OTHER)

            business_relevance = float(data.get("business_relevance", 0.5))
            business_relevance = max(0.0, min(1.0, business_relevance))

            skip_reason = None
            if business_relevance < self.SKIP_THRESHOLD:
                skip_reason = data.get("skip_reason") or f"商业相关度过低（{business_relevance:.2f}）"

            return TopicClassification(
                primary_topic=data.get("primary_topic", "未知"),
                secondary_topics=data.get("secondary_topics", []),
                content_type=content_type,
                business_relevance=business_relevance,
                skip_reason=skip_reason,
            )

        except Exception as e:
            logger.error(f"[classifier] 分类失败: {e}")
            return TopicClassification(
                primary_topic="未知",
                secondary_topics=[],
                content_type=ContentType.OTHER,
                business_relevance=0.5,
            )

    def should_skip(self, classification: TopicClassification) -> bool:
        """business_relevance < 0.3 时返回 True，跳过后续分析。"""
        return classification.business_relevance < self.SKIP_THRESHOLD
