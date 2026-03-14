"""InsightsAggregator — 洞察聚合模块。"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from openclaw.models.types import (
    BusinessOpportunity, ConsensusAndDivergence, CoreSignal,
    Mode1Insights, Mode2Insights, QualitySummary, VideoAnalysis,
)

logger = logging.getLogger(__name__)

AGGREGATOR_MODE1_SYSTEM = """你是一个专业的商业洞察聚合分析师。
请将多个视频的分析结果聚合为结构化的洞察报告。
对相似信号进行去重合并，confidence_score 取加权平均。
仅保留有多个信号支撑的商业机会。
生成 3~5 条对用户最有价值的启发（insights_for_me）。
输出严格遵循 JSON 格式。"""

AGGREGATOR_MODE2_SYSTEM = """你是一个专业的行业趋势分析师。
请将多个博主的视频分析结果聚合为赛道洞察报告。
识别趋势信号、博主间的共识与分歧、通用方法论和商业机会。
共识点需标注支持比例，分歧点需标注双方立场。
生成 3~5 条对用户最有价值的启发（insights_for_me）。
输出严格遵循 JSON 格式。"""


def _weighted_avg_confidence(scores: List[Tuple[float, float]]) -> float:
    """加权平均 confidence_score，权重为出现次数。"""
    if not scores:
        return 0.0
    total_weight = sum(w for _, w in scores)
    if total_weight == 0:
        return 0.0
    return sum(s * w for s, w in scores) / total_weight


def _merge_signals(analyses: List[VideoAnalysis], quality_threshold: float = 0.5) -> List[dict]:
    """合并多视频的核心信号，去重并加权。"""
    signal_map: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
    for analysis in analyses:
        weight = analysis.overall_quality if analysis.overall_quality >= quality_threshold else analysis.overall_quality * 0.5
        for sig in analysis.core_signals:
            signal_map[sig.signal].append((sig.confidence_score, weight))

    merged = []
    for signal_text, score_weights in signal_map.items():
        avg_score = _weighted_avg_confidence(score_weights)
        merged.append({
            "signal": signal_text,
            "confidence_score": round(avg_score, 3),
            "occurrence_count": len(score_weights),
        })
    # 按出现次数和置信度排序
    merged.sort(key=lambda x: (x["occurrence_count"], x["confidence_score"]), reverse=True)
    return merged


class InsightsAggregator:
    """洞察聚合模块，支持 Mode1 和 Mode2。"""

    def __init__(self, llm_client=None, mode1_config=None, mode2_config=None):
        self._llm_client = llm_client
        self._mode1_config = mode1_config
        self._mode2_config = mode2_config

    async def aggregate_mode1(
        self, analyses: List[VideoAnalysis], metadata: dict
    ) -> Mode1Insights:
        """Mode1 聚合：单博主多视频洞察。"""
        if not analyses:
            return self._empty_mode1(metadata)

        merged_signals = _merge_signals(analyses)
        low_quality_count = sum(1 for a in analyses if a.overall_quality < 0.5)
        avg_confidence = sum(a.overall_quality for a in analyses) / len(analyses)

        # 收集所有方法论和高价值表达
        all_methods = []
        for a in analyses:
            for m in a.methodology_fragments:
                all_methods.append({"method": m.method, "applicable_scenario": m.applicable_scenario, "confidence_score": m.confidence_score})

        all_quotes = []
        for a in analyses:
            for q in a.high_value_quotes:
                all_quotes.append({"quote": q.quote, "context": q.context})

        all_frameworks = []
        for a in analyses:
            for f in a.cognition_framework:
                all_frameworks.append({"framework": f.framework, "reasoning_chain": f.reasoning_chain, "confidence_score": f.confidence_score})

        # 使用 LLM 生成聚合洞察（如果可用）
        insights_for_me = await self._generate_insights_for_me(merged_signals, "mode1")
        business_opportunities = await self._generate_business_opportunities(merged_signals)

        quality_summary = QualitySummary(
            overall_confidence=round(avg_confidence, 3),
            low_quality_signals_count=low_quality_count,
            notes=f"共分析 {len(analyses)} 个视频，{low_quality_count} 个低质量结果已降权",
        )

        return Mode1Insights(
            metadata=metadata,
            core_signals=merged_signals[:10],
            cognition_framework=all_frameworks[:5],
            methodology_fragments=all_methods[:5],
            business_opportunities=business_opportunities,
            high_value_quotes=all_quotes[:5],
            insights_for_me=insights_for_me,
            quality_summary=quality_summary,
        )

    async def aggregate_mode2(
        self, creator_analyses: Dict[str, List[VideoAnalysis]], metadata: dict
    ) -> Mode2Insights:
        """Mode2 聚合：多博主赛道洞察。"""
        all_analyses = [a for analyses in creator_analyses.values() for a in analyses]
        if not all_analyses:
            return self._empty_mode2(metadata)

        merged_signals = _merge_signals(all_analyses)
        low_quality_count = sum(1 for a in all_analyses if a.overall_quality < 0.5)
        avg_confidence = sum(a.overall_quality for a in all_analyses) / len(all_analyses)

        # 趋势信号：出现在多个博主中的信号
        trend_signals = [s for s in merged_signals if s["occurrence_count"] >= 2]

        all_methods = []
        for a in all_analyses:
            for m in a.methodology_fragments:
                all_methods.append({"method": m.method, "applicable_scenario": m.applicable_scenario, "confidence_score": m.confidence_score})

        all_quotes = []
        for a in all_analyses:
            for q in a.high_value_quotes:
                all_quotes.append({"quote": q.quote, "context": q.context})

        insights_for_me = await self._generate_insights_for_me(trend_signals, "mode2")
        business_opportunities = await self._generate_business_opportunities(trend_signals)
        consensus_divergence = self._analyze_consensus_divergence(creator_analyses)

        quality_summary = QualitySummary(
            overall_confidence=round(avg_confidence, 3),
            low_quality_signals_count=low_quality_count,
            notes=f"共分析 {len(creator_analyses)} 个博主，{len(all_analyses)} 个视频",
        )

        return Mode2Insights(
            metadata=metadata,
            trend_signals=trend_signals[:10],
            consensus_and_divergence=consensus_divergence,
            common_methodology=all_methods[:5],
            business_opportunities=business_opportunities,
            high_value_quotes=all_quotes[:5],
            insights_for_me=insights_for_me,
            quality_summary=quality_summary,
        )

    def _analyze_consensus_divergence(
        self, creator_analyses: Dict[str, List[VideoAnalysis]]
    ) -> ConsensusAndDivergence:
        """分析博主间的共识与分歧。"""
        # 统计每个信号在各博主中的出现情况
        signal_creators: Dict[str, List[str]] = defaultdict(list)
        for creator, analyses in creator_analyses.items():
            for analysis in analyses:
                for sig in analysis.core_signals:
                    signal_creators[sig.signal].append(creator)

        total_creators = len(creator_analyses)
        consensus = []
        divergence = []

        for signal, creators in signal_creators.items():
            unique_creators = list(set(creators))
            ratio = len(unique_creators) / total_creators if total_creators > 0 else 0
            if ratio >= 0.6:
                consensus.append({"signal": signal, "support_ratio": round(ratio, 2), "creators": unique_creators})
            elif ratio <= 0.3 and len(unique_creators) >= 1:
                divergence.append({"signal": signal, "support_ratio": round(ratio, 2), "creators": unique_creators})

        return ConsensusAndDivergence(consensus=consensus[:5], divergence=divergence[:5])

    async def _generate_insights_for_me(self, signals: List[dict], mode: str) -> List[str]:
        """使用 LLM 生成用户启发，无 LLM 时返回基于信号的简单启发。"""
        if not signals:
            return ["暂无足够数据生成洞察"]

        if self._llm_client:
            config = self._mode1_config if mode == "mode1" else self._mode2_config
            if config:
                try:
                    signals_text = json.dumps(signals[:5], ensure_ascii=False)
                    response = await self._llm_client.call(
                        model_config=config,
                        system_prompt="请基于以下信号，生成 3~5 条对商业分析师最有价值的启发，每条启发简洁有力，直接输出 JSON 数组格式。",
                        user_prompt=signals_text,
                    )
                    data = json.loads(response) if isinstance(response, str) else response
                    if isinstance(data, list):
                        return data[:5]
                except Exception as e:
                    logger.warning(f"[aggregator] LLM 生成启发失败: {e}")

        # 降级：基于信号生成简单启发
        return [f"关注信号：{s['signal']}" for s in signals[:4]] + ["建议深入研究高置信度信号"]

    async def _generate_business_opportunities(self, signals: List[dict]) -> BusinessOpportunity:
        """基于信号生成商业机会（仅保留多信号支撑的判断）。"""
        # 仅保留出现次数 >= 2 的信号作为商业机会依据
        strong_signals = [s for s in signals if s.get("occurrence_count", 1) >= 2]

        direction_judgment = [
            {"judgment": f"基于{s['signal']}的商业方向", "confidence_score": s["confidence_score"]}
            for s in strong_signals[:3]
        ]
        verifiable_hypotheses = [
            {"hypothesis": f"假设：{s['signal']}可以转化为产品/服务机会", "confidence_score": s["confidence_score"] * 0.8}
            for s in strong_signals[:3]
        ]

        return BusinessOpportunity(
            direction_judgment=direction_judgment,
            verifiable_hypotheses=verifiable_hypotheses,
        )

    def _empty_mode1(self, metadata: dict) -> Mode1Insights:
        return Mode1Insights(
            metadata=metadata, core_signals=[], cognition_framework=[],
            methodology_fragments=[], business_opportunities=BusinessOpportunity(direction_judgment=[], verifiable_hypotheses=[]),
            high_value_quotes=[], insights_for_me=["暂无数据"], quality_summary=QualitySummary(overall_confidence=0.0, low_quality_signals_count=0, notes="无分析结果")
        )

    def _empty_mode2(self, metadata: dict) -> Mode2Insights:
        return Mode2Insights(
            metadata=metadata, trend_signals=[], consensus_and_divergence=ConsensusAndDivergence(consensus=[], divergence=[]),
            common_methodology=[], business_opportunities=BusinessOpportunity(direction_judgment=[], verifiable_hypotheses=[]),
            high_value_quotes=[], insights_for_me=["暂无数据"], quality_summary=QualitySummary(overall_confidence=0.0, low_quality_signals_count=0, notes="无分析结果")
        )
