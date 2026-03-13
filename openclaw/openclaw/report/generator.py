"""ReportGenerator — 报告生成模块，支持 Markdown、PDF、JSON 三种格式。"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional, Union

from openclaw.models.types import Mode1Insights, Mode2Insights

logger = logging.getLogger(__name__)


class ReportGenerator:
    """生成结构化洞察报告。"""

    def generate(
        self,
        insights: Union[Mode1Insights, Mode2Insights],
        output_format: str = "Markdown",
        output_path: Optional[str] = None,
    ) -> str:
        """
        生成报告。

        Args:
            insights: Mode1Insights 或 Mode2Insights
            output_format: "Markdown" | "PDF" | "JSON"
            output_path: 输出文件路径（可选）

        Returns:
            报告内容字符串
        """
        output_format = output_format.upper()

        if output_format == "JSON":
            content = self._to_json(insights)
        elif output_format in ("MARKDOWN", "MD"):
            content = self._to_markdown(insights)
        elif output_format == "PDF":
            content = self._to_pdf(insights, output_path)
        else:
            logger.warning(f"未知输出格式 {output_format}，使用 Markdown")
            content = self._to_markdown(insights)

        if output_path and output_format != "PDF":
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info(f"[report] 报告已保存到: {output_path}")
            except Exception as e:
                logger.error(f"[report] 保存失败: {e}")

        return content

    def _to_json(self, insights: Union[Mode1Insights, Mode2Insights]) -> str:
        return insights.model_dump_json(indent=2)

    def _to_markdown(self, insights: Union[Mode1Insights, Mode2Insights]) -> str:
        if isinstance(insights, Mode1Insights):
            return self._mode1_markdown(insights)
        return self._mode2_markdown(insights)

    def _mode1_markdown(self, ins: Mode1Insights) -> str:
        meta = ins.metadata
        lines = [
            f"# OpenClaw 洞察报告 — 单博主分析",
            f"",
            f"## 元数据",
            f"- 博主：{meta.get('creator', 'N/A')}",
            f"- 平台：{meta.get('platform', 'N/A')}",
            f"- 分析视频数：{meta.get('videos_analyzed', 0)}",
            f"- 跳过视频数：{meta.get('videos_skipped', 0)}",
            f"- 时间范围：{meta.get('time_range', 'N/A')}",
            f"",
            f"## 核心信号",
        ]
        for sig in ins.core_signals:
            lines.append(f"- **{sig.get('signal', '')}** (置信度: {sig.get('confidence_score', 0):.2f})")

        lines += ["", "## 认知框架"]
        for fw in ins.cognition_framework:
            lines.append(f"- **{fw.get('framework', '')}**: {fw.get('reasoning_chain', '')}")

        lines += ["", "## 方法论片段"]
        for m in ins.methodology_fragments:
            lines.append(f"- **{m.get('method', '')}** — 适用场景：{m.get('applicable_scenario', '')}")

        lines += ["", "## 商业机会"]
        for d in ins.business_opportunities.direction_judgment:
            lines.append(f"- {d.get('judgment', '')} (置信度: {d.get('confidence_score', 0):.2f})")

        lines += ["", "## 高价值表达"]
        for q in ins.high_value_quotes:
            lines.append(f"> {q.get('quote', '')}")
            lines.append(f"> *{q.get('context', '')}*")
            lines.append("")

        lines += ["## 用户启发"]
        for i, insight in enumerate(ins.insights_for_me, 1):
            lines.append(f"{i}. {insight}")

        qs = ins.quality_summary
        lines += [
            "", "## 质量摘要",
            f"- 整体置信度：{qs.overall_confidence:.2f}",
            f"- 低质量信号数：{qs.low_quality_signals_count}",
            f"- 备注：{qs.notes}",
        ]
        return "\n".join(lines)

    def _mode2_markdown(self, ins: Mode2Insights) -> str:
        meta = ins.metadata
        lines = [
            f"# OpenClaw 洞察报告 — 赛道分析",
            f"",
            f"## 元数据",
            f"- 主题：{meta.get('topic', 'N/A')}",
            f"- 平台：{', '.join(meta.get('platforms', []))}",
            f"- 分析博主数：{meta.get('creators_analyzed', 0)}",
            f"- 分析视频总数：{meta.get('total_videos_analyzed', 0)}",
            f"",
            f"## 趋势信号",
        ]
        for sig in ins.trend_signals:
            lines.append(f"- **{sig.get('signal', '')}** (出现次数: {sig.get('occurrence_count', 1)}, 置信度: {sig.get('confidence_score', 0):.2f})")

        lines += ["", "## 共识与分歧", "### 共识点"]
        for c in ins.consensus_and_divergence.consensus:
            lines.append(f"- {c.get('signal', '')} (支持比例: {c.get('support_ratio', 0):.0%})")

        lines += ["", "### 分歧点"]
        for d in ins.consensus_and_divergence.divergence:
            lines.append(f"- {d.get('signal', '')} (支持比例: {d.get('support_ratio', 0):.0%})")

        lines += ["", "## 通用方法论"]
        for m in ins.common_methodology:
            lines.append(f"- **{m.get('method', '')}** — {m.get('applicable_scenario', '')}")

        lines += ["", "## 商业机会"]
        for d in ins.business_opportunities.direction_judgment:
            lines.append(f"- {d.get('judgment', '')} (置信度: {d.get('confidence_score', 0):.2f})")

        lines += ["", "## 高价值表达"]
        for q in ins.high_value_quotes:
            lines.append(f"> {q.get('quote', '')}")
            lines.append("")

        lines += ["## 用户启发"]
        for i, insight in enumerate(ins.insights_for_me, 1):
            lines.append(f"{i}. {insight}")

        qs = ins.quality_summary
        lines += [
            "", "## 质量摘要",
            f"- 整体置信度：{qs.overall_confidence:.2f}",
            f"- 低质量信号数：{qs.low_quality_signals_count}",
            f"- 备注：{qs.notes}",
        ]
        return "\n".join(lines)

    def _to_pdf(self, insights: Union[Mode1Insights, Mode2Insights], output_path: Optional[str] = None) -> str:
        """Markdown 转 PDF（需要 weasyprint）。"""
        md_content = self._to_markdown(insights)
        if not output_path:
            output_path = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        try:
            from weasyprint import HTML
            HTML(string=f"<pre>{md_content}</pre>").write_pdf(output_path)
            logger.info(f"[report] PDF 已生成: {output_path}")
        except ImportError:
            logger.warning("weasyprint 未安装，PDF 生成失败，返回 Markdown 内容")
        except Exception as e:
            logger.error(f"[report] PDF 生成失败: {e}")
        return md_content
