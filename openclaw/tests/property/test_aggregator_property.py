"""InsightsAggregator 属性测试（Property-Based Testing）。"""
import pytest
from hypothesis import given, settings, strategies as st
from openclaw.models.types import VideoAnalysis, CoreSignal


def _make_analysis(signals: list, quality: float = 0.8) -> VideoAnalysis:
    return VideoAnalysis(
        video_id="test",
        core_signals=[CoreSignal(signal=s, confidence_score=0.8, evidence="e") for s in signals],
        cognition_framework=[],
        methodology_fragments=[],
        high_value_quotes=[],
        overall_quality=quality,
    )


# ── 属性 9: 去重合并后信号数不超过输入信号总数 ────────────────────────────────

@given(
    signal_lists=st.lists(
        st.lists(
            st.text(min_size=1, max_size=30, alphabet="abcdefghijklmnopqrstuvwxyz_"),
            min_size=0, max_size=5,
        ),
        min_size=1, max_size=6,
    )
)
@settings(max_examples=50)
@pytest.mark.asyncio
async def test_merged_signals_not_exceed_input(signal_lists):
    """属性 9: 聚合后信号数 ≤ 输入信号总数之和。"""
    from openclaw.aggregation.aggregator import InsightsAggregator
    agg = InsightsAggregator()
    analyses = [_make_analysis(signals) for signals in signal_lists]
    total_input = sum(len(a.core_signals) for a in analyses)

    result = await agg.aggregate_mode1(analyses, {"creator": "test"})
    assert len(result.core_signals) <= total_input


@given(
    signal_lists=st.lists(
        st.lists(
            st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"),
            min_size=1, max_size=4,
        ),
        min_size=2, max_size=5,
    )
)
@settings(max_examples=30)
@pytest.mark.asyncio
async def test_mode2_merged_signals_not_exceed_input(signal_lists):
    """属性 9b: Mode2 聚合后信号数 ≤ 输入信号总数。"""
    from openclaw.aggregation.aggregator import InsightsAggregator
    agg = InsightsAggregator()
    creator_analyses = {
        f"creator_{i}": [_make_analysis(signals)] for i, signals in enumerate(signal_lists)
    }
    all_analyses = [a for analyses in creator_analyses.values() for a in analyses]
    total_input = sum(len(a.core_signals) for a in all_analyses)

    result = await agg.aggregate_mode2(creator_analyses, {"topic": "test"})
    # trend_signals 是 merged_signals 的子集，必然 ≤ total_input
    assert len(result.trend_signals) <= total_input


# ── 属性 10: 降权一致性 ───────────────────────────────────────────────────────

@given(
    signal_name=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"),
    high_quality=st.floats(min_value=0.5, max_value=1.0, allow_nan=False),
    low_quality=st.floats(min_value=0.01, max_value=0.49, allow_nan=False),
    confidence=st.floats(min_value=0.1, max_value=1.0, allow_nan=False),
)
@settings(max_examples=50)
def test_low_quality_downweighted(signal_name, high_quality, low_quality, confidence):
    """属性 10: overall_quality < 0.5 的分析在聚合中权重应低于高质量分析。"""
    from openclaw.aggregation.aggregator import _merge_signals

    high_analysis = VideoAnalysis(
        video_id="high",
        core_signals=[CoreSignal(signal=signal_name, confidence_score=confidence, evidence="e")],
        cognition_framework=[], methodology_fragments=[], high_value_quotes=[],
        overall_quality=high_quality,
    )
    low_analysis = VideoAnalysis(
        video_id="low",
        core_signals=[CoreSignal(signal=signal_name, confidence_score=confidence, evidence="e")],
        cognition_framework=[], methodology_fragments=[], high_value_quotes=[],
        overall_quality=low_quality,
    )

    merged_high = _merge_signals([high_analysis])
    merged_low = _merge_signals([low_analysis])

    # 相同信号相同置信度，高质量的加权结果应 >= 低质量的
    assert merged_high[0]["confidence_score"] >= merged_low[0]["confidence_score"]


# ── 空输入边界 ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_aggregate_mode1_empty_returns_valid():
    """空输入应返回有效的 Mode1Insights，不崩溃。"""
    from openclaw.aggregation.aggregator import InsightsAggregator
    agg = InsightsAggregator()
    result = await agg.aggregate_mode1([], {"creator": "test"})
    assert result.core_signals == []
    assert 0.0 <= result.quality_summary.overall_confidence <= 1.0


@pytest.mark.asyncio
async def test_aggregate_mode2_empty_returns_valid():
    """空输入应返回有效的 Mode2Insights，不崩溃。"""
    from openclaw.aggregation.aggregator import InsightsAggregator
    agg = InsightsAggregator()
    result = await agg.aggregate_mode2({}, {"topic": "test"})
    assert result.trend_signals == []
    assert 0.0 <= result.quality_summary.overall_confidence <= 1.0
