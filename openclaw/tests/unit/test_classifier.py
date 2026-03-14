"""TopicClassifier 单元测试。"""
import json
import pytest
from unittest.mock import AsyncMock
from openclaw.models.types import ContentType


def _make_llm_response(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False)


# ── 无 LLM 时的默认行为 ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_classify_no_llm_returns_default():
    """无 LLM 时应返回默认分类，business_relevance=0.5。"""
    from openclaw.pipeline.classifier import TopicClassifier
    clf = TopicClassifier()
    result = await clf.classify(["任意文本"])
    assert result.primary_topic == "未知"
    assert result.content_type == ContentType.OTHER
    assert result.business_relevance == 0.5
    assert result.skip_reason is None


# ── business_relevance < 0.3 时标记跳过 ──────────────────────────────────────

@pytest.mark.asyncio
async def test_classify_low_relevance_sets_skip_reason():
    """business_relevance < 0.3 时应设置 skip_reason。"""
    from openclaw.pipeline.classifier import TopicClassifier
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(return_value=_make_llm_response({
        "primary_topic": "宠物护理",
        "secondary_topics": [],
        "content_type": "其他",
        "business_relevance": 0.1,
        "skip_reason": "内容与商业分析无关",
    }))
    from openclaw.config.settings import LLMModelConfig
    clf = TopicClassifier(llm_client=mock_llm, model_config=LLMModelConfig(provider="test", model="test"))
    result = await clf.classify(["今天给猫咪洗澡了"])
    assert result.business_relevance == 0.1
    assert result.skip_reason is not None
    assert len(result.skip_reason) > 0


@pytest.mark.asyncio
async def test_classify_boundary_relevance_no_skip():
    """business_relevance == 0.3 时不应跳过（阈值为严格小于）。"""
    from openclaw.pipeline.classifier import TopicClassifier
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(return_value=_make_llm_response({
        "primary_topic": "创业",
        "secondary_topics": [],
        "content_type": "观点输出",
        "business_relevance": 0.3,
        "skip_reason": None,
    }))
    from openclaw.config.settings import LLMModelConfig
    clf = TopicClassifier(llm_client=mock_llm, model_config=LLMModelConfig(provider="test", model="test"))
    result = await clf.classify(["创业内容"])
    assert result.skip_reason is None


# ── should_skip 逻辑 ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("relevance,expected_skip", [
    (0.0, True),
    (0.1, True),
    (0.29, True),
    (0.3, False),
    (0.5, False),
    (1.0, False),
])
def test_should_skip_threshold(relevance, expected_skip):
    """should_skip 应在 business_relevance < 0.3 时返回 True。"""
    from openclaw.pipeline.classifier import TopicClassifier
    from openclaw.models.types import TopicClassification
    clf = TopicClassifier()
    classification = TopicClassification(
        primary_topic="test",
        content_type=ContentType.OTHER,
        business_relevance=relevance,
    )
    assert clf.should_skip(classification) == expected_skip


# ── content_type 枚举约束 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("ct_str,expected_enum", [
    ("观点输出", ContentType.OPINION),
    ("教程讲解", ContentType.TUTORIAL),
    ("案例分析", ContentType.CASE_STUDY),
    ("行业分析", ContentType.INDUSTRY),
    ("产品推荐", ContentType.PRODUCT),
    ("其他", ContentType.OTHER),
    ("未知类型", ContentType.OTHER),  # 未知类型应降级为 OTHER
])
async def test_content_type_mapping(ct_str, expected_enum):
    """LLM 返回的 content_type 字符串应正确映射到枚举。"""
    from openclaw.pipeline.classifier import TopicClassifier
    from openclaw.config.settings import LLMModelConfig
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(return_value=_make_llm_response({
        "primary_topic": "测试",
        "secondary_topics": [],
        "content_type": ct_str,
        "business_relevance": 0.5,
        "skip_reason": None,
    }))
    clf = TopicClassifier(llm_client=mock_llm, model_config=LLMModelConfig(provider="test", model="test"))
    result = await clf.classify(["文本"])
    assert result.content_type == expected_enum


# ── LLM 失败降级 ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_classify_llm_failure_returns_default():
    """LLM 调用失败时应降级返回默认分类，不抛出异常。"""
    from openclaw.pipeline.classifier import TopicClassifier
    from openclaw.config.settings import LLMModelConfig
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(side_effect=Exception("LLM 连接超时"))
    clf = TopicClassifier(llm_client=mock_llm, model_config=LLMModelConfig(provider="test", model="test"))
    result = await clf.classify(["文本内容"])
    # 不应抛出异常，返回默认值
    assert result.primary_topic == "未知"
    assert result.business_relevance == 0.5


# ── business_relevance 范围钳制 ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_classify_clamps_relevance_out_of_range():
    """LLM 返回超出范围的 business_relevance 应被钳制到 [0, 1]。"""
    from openclaw.pipeline.classifier import TopicClassifier
    from openclaw.config.settings import LLMModelConfig
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(return_value=_make_llm_response({
        "primary_topic": "AI",
        "secondary_topics": [],
        "content_type": "行业分析",
        "business_relevance": 1.5,  # 超出范围
        "skip_reason": None,
    }))
    clf = TopicClassifier(llm_client=mock_llm, model_config=LLMModelConfig(provider="test", model="test"))
    result = await clf.classify(["AI内容"])
    assert 0.0 <= result.business_relevance <= 1.0
