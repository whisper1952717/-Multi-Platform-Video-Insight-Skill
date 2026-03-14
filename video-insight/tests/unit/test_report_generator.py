"""ReportGenerator 单元测试。"""
import json
import pytest
from openclaw.models.types import (
    BusinessOpportunity, ConsensusAndDivergence,
    Mode1Insights, Mode2Insights, QualitySummary,
)


def _make_mode1(creator="test_creator") -> Mode1Insights:
    return Mode1Insights(
        metadata={"creator": creator, "platform": "bilibili", "videos_analyzed": 5, "videos_skipped": 1, "time_range": "last_30_days"},
        core_signals=[{"signal": "AI趋势", "confidence_score": 0.9, "occurrence_count": 3}],
        cognition_framework=[{"framework": "第一性原理", "reasoning_chain": "从基础出发推导", "confidence_score": 0.8}],
        methodology_fragments=[{"method": "MVP验证", "applicable_scenario": "早期创业", "confidence_score": 0.85}],
        business_opportunities=BusinessOpportunity(
            direction_judgment=[{"judgment": "AI工具方向", "confidence_score": 0.8}],
            verifiable_hypotheses=[{"hypothesis": "AI可降低成本", "confidence_score": 0.7}],
        ),
        high_value_quotes=[{"quote": "找到细分市场", "context": "创业策略"}],
        insights_for_me=["关注AI工具赛道", "重视细分市场"],
        quality_summary=QualitySummary(overall_confidence=0.82, low_quality_signals_count=1, notes="整体质量良好"),
    )


def _make_mode2(topic="AI创业") -> Mode2Insights:
    return Mode2Insights(
        metadata={"topic": topic, "platforms": ["bilibili", "youtube"], "creators_analyzed": 3, "total_videos_analyzed": 10},
        trend_signals=[{"signal": "AI降本增效", "confidence_score": 0.88, "occurrence_count": 5}],
        consensus_and_divergence=ConsensusAndDivergence(
            consensus=[{"signal": "AI是趋势", "support_ratio": 0.8, "creators": ["a", "b", "c"]}],
            divergence=[{"signal": "是否需要大模型", "support_ratio": 0.33, "creators": ["a"]}],
        ),
        common_methodology=[{"method": "快速迭代", "applicable_scenario": "产品开发", "confidence_score": 0.75}],
        business_opportunities=BusinessOpportunity(direction_judgment=[], verifiable_hypotheses=[]),
        high_value_quotes=[{"quote": "速度即护城河", "context": "竞争策略"}],
        insights_for_me=["关注AI降本趋势"],
        quality_summary=QualitySummary(overall_confidence=0.78, low_quality_signals_count=2, notes="多博主验证"),
    )


# ── JSON 格式 ─────────────────────────────────────────────────────────────────

def test_generate_json_mode1():
    """Mode1 JSON 格式应可解析且包含核心字段。"""
    from openclaw.report.generator import ReportGenerator
    gen = ReportGenerator()
    content = gen.generate(_make_mode1(), output_format="JSON")
    data = json.loads(content)
    assert "core_signals" in data
    assert "quality_summary" in data
    assert "insights_for_me" in data
    assert data["quality_summary"]["overall_confidence"] == 0.82


def test_generate_json_mode2():
    """Mode2 JSON 格式应包含趋势信号和共识分歧。"""
    from openclaw.report.generator import ReportGenerator
    gen = ReportGenerator()
    content = gen.generate(_make_mode2(), output_format="JSON")
    data = json.loads(content)
    assert "trend_signals" in data
    assert "consensus_and_divergence" in data
    assert "insights_for_me" in data


# ── Markdown 格式 ─────────────────────────────────────────────────────────────

def test_generate_markdown_mode1_structure():
    """Mode1 Markdown 应包含所有必要章节。"""
    from openclaw.report.generator import ReportGenerator
    gen = ReportGenerator()
    content = gen.generate(_make_mode1(), output_format="Markdown")
    assert "# OpenClaw 洞察报告" in content
    assert "## 元数据" in content
    assert "## 核心信号" in content
    assert "## 认知框架" in content
    assert "## 方法论片段" in content
    assert "## 商业机会" in content
    assert "## 高价值表达" in content
    assert "## 用户启发" in content
    assert "## 质量摘要" in content


def test_generate_markdown_mode2_structure():
    """Mode2 Markdown 应包含趋势信号和共识分歧章节。"""
    from openclaw.report.generator import ReportGenerator
    gen = ReportGenerator()
    content = gen.generate(_make_mode2(), output_format="Markdown")
    assert "## 趋势信号" in content
    assert "## 共识与分歧" in content
    assert "### 共识点" in content
    assert "### 分歧点" in content
    assert "## 通用方法论" in content
    assert "## 质量摘要" in content


def test_generate_markdown_contains_data():
    """Markdown 报告应包含实际数据内容。"""
    from openclaw.report.generator import ReportGenerator
    gen = ReportGenerator()
    content = gen.generate(_make_mode1(), output_format="Markdown")
    assert "test_creator" in content
    assert "AI趋势" in content
    assert "关注AI工具赛道" in content
    assert "0.82" in content


# ── MD 别名 ───────────────────────────────────────────────────────────────────

def test_generate_md_alias():
    """'MD' 格式应与 'Markdown' 等价。"""
    from openclaw.report.generator import ReportGenerator
    gen = ReportGenerator()
    md = gen.generate(_make_mode1(), output_format="MD")
    markdown = gen.generate(_make_mode1(), output_format="Markdown")
    assert md == markdown


# ── 未知格式降级 ──────────────────────────────────────────────────────────────

def test_generate_unknown_format_falls_back_to_markdown():
    """未知格式应降级为 Markdown。"""
    from openclaw.report.generator import ReportGenerator
    gen = ReportGenerator()
    content = gen.generate(_make_mode1(), output_format="XML")
    assert "# OpenClaw 洞察报告" in content


# ── 文件输出 ──────────────────────────────────────────────────────────────────

def test_generate_saves_to_file(tmp_path):
    """指定 output_path 时应将报告写入文件。"""
    from openclaw.report.generator import ReportGenerator
    gen = ReportGenerator()
    out_file = str(tmp_path / "report.md")
    gen.generate(_make_mode1(), output_format="Markdown", output_path=out_file)
    with open(out_file, encoding="utf-8") as f:
        content = f.read()
    assert "# OpenClaw 洞察报告" in content


def test_generate_json_saves_to_file(tmp_path):
    """JSON 格式也应正确写入文件。"""
    from openclaw.report.generator import ReportGenerator
    gen = ReportGenerator()
    out_file = str(tmp_path / "report.json")
    gen.generate(_make_mode2(), output_format="JSON", output_path=out_file)
    with open(out_file, encoding="utf-8") as f:
        data = json.load(f)
    assert "trend_signals" in data
