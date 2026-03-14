"""InsightsAggregator 单元测试。"""
import pytest


def _make_analysis(signals, quality=0.8):
    """构造测试用 VideoAnalysis。"""
    from openclaw.models.types import VideoAnalysis, CoreSignal
    return VideoAnalysis(
        video_id="test",
        core_signals=[CoreSignal(signal=s, confidence_score=0.8, evidence="test") for s in signals],
        cognition_framework=[],
        methodology_fragments=[],
        high_value_quotes=[],
        overall_quality=quality,
    )


@pytest.mark.asyncio
async def test_aggregate_mode1_empty():
    """空分析列表应返回空洞察。"""
    from openclaw.aggregation.aggregator import InsightsAggregator
    agg = InsightsAggregator()
    result = await agg.aggregate_mode1([], {"creator": "test"})
    assert result.insights_for_me == ["暂无数据"]
    assert result.core_signals == []


@pytest.mark.asyncio
async def test_aggregate_mode1_dedup():
    """相同信号应被合并，聚合后信号数 <= 输入信号总数。"""
    from openclaw.aggregation.aggregator import InsightsAggregator
    agg = InsightsAggregator()
    analyses = [
        _make_analysis(["AI趋势", "商业机会"]),
        _make_analysis(["AI趋势", "技术创新"]),
        _make_analysis(["AI趋势"]),
    ]
    total_input_signals = sum(len(a.core_signals) for a in analyses)
    result = await agg.aggregate_mode1(analyses, {"creator": "test"})
    assert len(result.core_signals) <= total_input_signals


@pytest.mark.asyncio
async def test_aggregate_mode1_low_quality_downweight():
    """低质量分析（overall_quality < 0.5）应降权。"""
    from openclaw.aggregation.aggregator import InsightsAggregator, _merge_signals
    high_quality = _make_analysis(["信号A"], quality=0.9)
    low_quality = _make_analysis(["信号A"], quality=0.2)

    # 高质量权重应高于低质量
    merged_high = _merge_signals([high_quality])
    merged_low = _merge_signals([low_quality])

    # 同一信号，高质量的置信度应 >= 低质量的
    assert merged_high[0]["confidence_score"] >= merged_low[0]["confidence_score"]


@pytest.mark.asyncio
async def test_aggregate_mode2_trend_signals():
    """Mode2 趋势信号应只包含出现在多个博主中的信号。"""
    from openclaw.aggregation.aggregator import InsightsAggregator
    agg = InsightsAggregator()
    creator_analyses = {
        "creator_a": [_make_analysis(["AI趋势", "独家信号A"])],
        "creator_b": [_make_analysis(["AI趋势", "独家信号B"])],
    }
    result = await agg.aggregate_mode2(creator_analyses, {"topic": "AI"})
    # AI趋势出现在两个博主中，应在趋势信号里
    trend_signal_names = [s.get("signal") for s in result.trend_signals]
    assert "AI趋势" in trend_signal_names


@pytest.mark.asyncio
async def test_aggregate_mode2_consensus():
    """共识分析：多博主共同提及的信号应被识别为共识。"""
    from openclaw.aggregation.aggregator import InsightsAggregator
    agg = InsightsAggregator()
    creator_analyses = {
        "a": [_make_analysis(["共识信号"])],
        "b": [_make_analysis(["共识信号"])],
        "c": [_make_analysis(["共识信号"])],
    }
    result = await agg.aggregate_mode2(creator_analyses, {"topic": "test"})
    consensus_signals = [c.get("signal") for c in result.consensus_and_divergence.consensus]
    assert "共识信号" in consensus_signals
