"""VideoAnalyzer 属性测试（Property-Based Testing）。"""
import json
import pytest
from hypothesis import given, settings, strategies as st
from unittest.mock import AsyncMock
from openclaw.models.types import ContentType, TopicClassification
from openclaw.config.settings import LLMModelConfig


def _make_topic(relevance=0.8):
    return TopicClassification(
        primary_topic="AI创业",
        content_type=ContentType.INDUSTRY,
        business_relevance=relevance,
    )


def _make_model_config():
    return LLMModelConfig(provider="test", model="test-model")


# ── 属性 8: confidence_score 评分标准一致性 ───────────────────────────────────

@given(
    signals=st.lists(
        st.fixed_dictionaries({
            "signal": st.text(min_size=1, max_size=50),
            "evidence": st.text(min_size=1, max_size=100),
            "confidence_score": st.floats(min_value=-2.0, max_value=3.0, allow_nan=False),
        }),
        min_size=0, max_size=5,
    ),
    frameworks=st.lists(
        st.fixed_dictionaries({
            "framework": st.text(min_size=1, max_size=50),
            "reasoning_chain": st.text(min_size=1, max_size=100),
            "confidence_score": st.floats(min_value=-2.0, max_value=3.0, allow_nan=False),
        }),
        min_size=0, max_size=3,
    ),
    methods=st.lists(
        st.fixed_dictionaries({
            "method": st.text(min_size=1, max_size=50),
            "applicable_scenario": st.text(min_size=1, max_size=100),
            "confidence_score": st.floats(min_value=-2.0, max_value=3.0, allow_nan=False),
        }),
        min_size=0, max_size=3,
    ),
    overall_quality=st.floats(min_value=-1.0, max_value=2.0, allow_nan=False),
)
@settings(max_examples=50)
@pytest.mark.asyncio
async def test_analyzer_clamps_all_confidence_scores(signals, frameworks, methods, overall_quality):
    """属性 8: VideoAnalyzer 输出的所有 confidence_score 必须在 [0.0, 1.0] 范围内。"""
    from openclaw.pipeline.analyzer import VideoAnalyzer

    llm_response = json.dumps({
        "core_signals": signals,
        "cognition_framework": frameworks,
        "methodology_fragments": methods,
        "high_value_quotes": [],
        "overall_quality": overall_quality,
    }, ensure_ascii=False)

    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(return_value=llm_response)

    analyzer = VideoAnalyzer(llm_client=mock_llm, model_config=_make_model_config())
    result = await analyzer.analyze(["测试文本"], _make_topic(), "video_test")

    # 所有 confidence_score 必须在 [0, 1]
    for sig in result.core_signals:
        assert 0.0 <= sig.confidence_score <= 1.0, f"core_signal score out of range: {sig.confidence_score}"
    for fw in result.cognition_framework:
        assert 0.0 <= fw.confidence_score <= 1.0, f"framework score out of range: {fw.confidence_score}"
    for m in result.methodology_fragments:
        assert 0.0 <= m.confidence_score <= 1.0, f"method score out of range: {m.confidence_score}"
    assert 0.0 <= result.overall_quality <= 1.0, f"overall_quality out of range: {result.overall_quality}"


# ── 无 LLM 时返回空分析 ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyzer_no_llm_returns_empty():
    """无 LLM 时应返回空分析，overall_quality=0.0。"""
    from openclaw.pipeline.analyzer import VideoAnalyzer
    analyzer = VideoAnalyzer()
    result = await analyzer.analyze(["文本"], _make_topic(), "v1")
    assert result.core_signals == []
    assert result.overall_quality == 0.0


# ── LLM 失败时降级 ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyzer_llm_failure_returns_fallback():
    """LLM 调用失败时应降级，不抛出异常。"""
    from openclaw.pipeline.analyzer import VideoAnalyzer
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(side_effect=Exception("timeout"))
    analyzer = VideoAnalyzer(llm_client=mock_llm, model_config=_make_model_config())
    result = await analyzer.analyze(["文本"], _make_topic(), "v1")
    # 不应抛出，返回有效的 VideoAnalysis
    assert result.video_id == "v1"
    assert 0.0 <= result.overall_quality <= 1.0


# ── 无效 JSON 响应时降级 ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyzer_invalid_json_falls_back():
    """LLM 返回无效 JSON 时应降级，不崩溃。"""
    from openclaw.pipeline.analyzer import VideoAnalyzer
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(return_value="这不是JSON格式的响应")
    analyzer = VideoAnalyzer(llm_client=mock_llm, model_config=_make_model_config())
    result = await analyzer.analyze(["文本"], _make_topic(), "v1")
    assert result is not None
    assert 0.0 <= result.overall_quality <= 1.0
