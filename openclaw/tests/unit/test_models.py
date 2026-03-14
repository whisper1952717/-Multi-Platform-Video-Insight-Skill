"""核心数据模型单元测试。"""
import pytest
from pydantic import ValidationError


def test_confidence_score_bounds():
    """confidence_score 超出 [0, 1] 范围应抛出 ValidationError。"""
    from openclaw.models.types import CoreSignal
    with pytest.raises(ValidationError):
        CoreSignal(signal="test", confidence_score=1.5, evidence="e")
    with pytest.raises(ValidationError):
        CoreSignal(signal="test", confidence_score=-0.1, evidence="e")


def test_confidence_score_valid():
    """confidence_score 在 [0, 1] 范围内应正常创建。"""
    from openclaw.models.types import CoreSignal
    sig = CoreSignal(signal="AI 趋势", confidence_score=0.85, evidence="多个视频提及")
    assert sig.confidence_score == 0.85


def test_video_info_creation():
    """VideoInfo 正常创建。"""
    from openclaw.models.types import VideoInfo
    from datetime import datetime, timezone
    v = VideoInfo(
        url="https://www.bilibili.com/video/BV1xx",
        title="测试视频",
        platform="bilibili",
        creator="test_creator",
        publish_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        view_count=1000,
    )
    assert v.platform == "bilibili"


def test_mode1_insights_serialization_roundtrip():
    """Mode1Insights 序列化后反序列化应得到等价对象。"""
    from openclaw.models.types import Mode1Insights, BusinessOpportunity, QualitySummary
    ins = Mode1Insights(
        metadata={"creator": "test", "platform": "bilibili"},
        core_signals=[{"signal": "AI", "confidence_score": 0.9}],
        cognition_framework=[],
        methodology_fragments=[],
        business_opportunities=BusinessOpportunity(direction_judgment=[], verifiable_hypotheses=[]),
        high_value_quotes=[],
        insights_for_me=["关注 AI 趋势"],
        quality_summary=QualitySummary(overall_confidence=0.8, low_quality_signals_count=0, notes="ok"),
    )
    json_str = ins.model_dump_json()
    restored = Mode1Insights.model_validate_json(json_str)
    assert restored.insights_for_me == ins.insights_for_me
    assert restored.quality_summary.overall_confidence == ins.quality_summary.overall_confidence


def test_mode2_insights_serialization_roundtrip():
    """Mode2Insights 序列化后反序列化应得到等价对象。"""
    from openclaw.models.types import Mode2Insights, BusinessOpportunity, QualitySummary, ConsensusAndDivergence
    ins = Mode2Insights(
        metadata={"topic": "AI创业", "platforms": ["bilibili"]},
        trend_signals=[{"signal": "AI", "confidence_score": 0.8, "occurrence_count": 3}],
        consensus_and_divergence=ConsensusAndDivergence(consensus=[], divergence=[]),
        common_methodology=[],
        business_opportunities=BusinessOpportunity(direction_judgment=[], verifiable_hypotheses=[]),
        high_value_quotes=[],
        insights_for_me=["关注赛道趋势"],
        quality_summary=QualitySummary(overall_confidence=0.75, low_quality_signals_count=1, notes="ok"),
    )
    json_str = ins.model_dump_json()
    restored = Mode2Insights.model_validate_json(json_str)
    assert restored.trend_signals == ins.trend_signals
    assert restored.quality_summary.low_quality_signals_count == 1
