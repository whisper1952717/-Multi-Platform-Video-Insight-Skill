"""核心数据模型属性测试（Property-Based Testing）。"""
import json
import pytest
from hypothesis import given, settings, strategies as st
from pydantic import ValidationError


# ── 属性 1: confidence_score 范围约束 ─────────────────────────────────────────

CONFIDENCE_MODELS = [
    ("CoreSignal", {"signal": "test", "evidence": "e"}),
    ("CognitionFramework", {"framework": "f", "reasoning_chain": "r"}),
    ("MethodologyFragment", {"method": "m", "applicable_scenario": "s"}),
]


@pytest.mark.parametrize("model_name,extra_fields", CONFIDENCE_MODELS)
@given(score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
@settings(max_examples=50)
def test_confidence_score_valid_range(model_name, extra_fields, score):
    """属性 1a: [0.0, 1.0] 范围内的 confidence_score 应始终有效。"""
    import openclaw.models.types as types
    cls = getattr(types, model_name)
    obj = cls(**extra_fields, confidence_score=score)
    assert 0.0 <= obj.confidence_score <= 1.0


@pytest.mark.parametrize("model_name,extra_fields", CONFIDENCE_MODELS)
@given(score=st.one_of(
    st.floats(max_value=-0.001, allow_nan=False, allow_infinity=False),
    st.floats(min_value=1.001, allow_nan=False, allow_infinity=False),
))
@settings(max_examples=50)
def test_confidence_score_out_of_range_rejected(model_name, extra_fields, score):
    """属性 1b: 超出 [0.0, 1.0] 范围的 confidence_score 应被拒绝。"""
    import openclaw.models.types as types
    cls = getattr(types, model_name)
    with pytest.raises(ValidationError):
        cls(**extra_fields, confidence_score=score)


@given(score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
@settings(max_examples=50)
def test_topic_classification_business_relevance_valid(score):
    """属性 1c: TopicClassification.business_relevance 在 [0,1] 内应有效。"""
    from openclaw.models.types import TopicClassification, ContentType
    obj = TopicClassification(
        primary_topic="test",
        content_type=ContentType.OTHER,
        business_relevance=score,
    )
    assert 0.0 <= obj.business_relevance <= 1.0


@given(score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
@settings(max_examples=50)
def test_video_analysis_overall_quality_valid(score):
    """属性 1d: VideoAnalysis.overall_quality 在 [0,1] 内应有效。"""
    from openclaw.models.types import VideoAnalysis
    obj = VideoAnalysis(
        video_id="v1",
        core_signals=[],
        cognition_framework=[],
        methodology_fragments=[],
        high_value_quotes=[],
        overall_quality=score,
    )
    assert 0.0 <= obj.overall_quality <= 1.0


# ── 属性 2: Mode1Insights/Mode2Insights 序列化往返一致性 ──────────────────────

@given(
    creator=st.text(min_size=1, max_size=50),
    confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    low_count=st.integers(min_value=0, max_value=100),
    insights=st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=5),
)
@settings(max_examples=50)
def test_mode1_insights_serialization_roundtrip(creator, confidence, low_count, insights):
    """属性 2a: Mode1Insights 序列化→反序列化应得到等价对象。"""
    from openclaw.models.types import Mode1Insights, BusinessOpportunity, QualitySummary
    ins = Mode1Insights(
        metadata={"creator": creator},
        core_signals=[],
        cognition_framework=[],
        methodology_fragments=[],
        business_opportunities=BusinessOpportunity(direction_judgment=[], verifiable_hypotheses=[]),
        high_value_quotes=[],
        insights_for_me=insights,
        quality_summary=QualitySummary(
            overall_confidence=confidence,
            low_quality_signals_count=low_count,
            notes="test",
        ),
    )
    restored = Mode1Insights.model_validate_json(ins.model_dump_json())
    assert restored.insights_for_me == ins.insights_for_me
    assert abs(restored.quality_summary.overall_confidence - ins.quality_summary.overall_confidence) < 1e-9
    assert restored.quality_summary.low_quality_signals_count == ins.quality_summary.low_quality_signals_count


@given(
    topic=st.text(min_size=1, max_size=50),
    confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    insights=st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=5),
)
@settings(max_examples=50)
def test_mode2_insights_serialization_roundtrip(topic, confidence, insights):
    """属性 2b: Mode2Insights 序列化→反序列化应得到等价对象。"""
    from openclaw.models.types import Mode2Insights, BusinessOpportunity, QualitySummary, ConsensusAndDivergence
    ins = Mode2Insights(
        metadata={"topic": topic},
        trend_signals=[],
        consensus_and_divergence=ConsensusAndDivergence(consensus=[], divergence=[]),
        common_methodology=[],
        business_opportunities=BusinessOpportunity(direction_judgment=[], verifiable_hypotheses=[]),
        high_value_quotes=[],
        insights_for_me=insights,
        quality_summary=QualitySummary(
            overall_confidence=confidence,
            low_quality_signals_count=0,
            notes="test",
        ),
    )
    restored = Mode2Insights.model_validate_json(ins.model_dump_json())
    assert restored.insights_for_me == ins.insights_for_me
    assert abs(restored.quality_summary.overall_confidence - ins.quality_summary.overall_confidence) < 1e-9
