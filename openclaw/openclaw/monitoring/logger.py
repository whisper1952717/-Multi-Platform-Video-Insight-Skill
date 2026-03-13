"""LoggingMonitor — 结构化日志与运行监控。"""
from __future__ import annotations

import logging
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

try:
    import structlog
    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False

try:
    from rich.console import Console
    from rich.logging import RichHandler
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


@dataclass
class StepStats:
    step: str
    status: str  # success | failed | skipped
    duration_ms: int
    error: Optional[str] = None


@dataclass
class RunSummary:
    run_id: str
    total_videos: int = 0
    success_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    step_durations: Dict[str, List[int]] = field(default_factory=lambda: defaultdict(list))
    platform_stats: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: {"success": 0, "failed": 0}))
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0


class LoggingMonitor:
    """结构化日志监控，支持 structlog + Rich 输出到控制台和文件。"""

    def __init__(self, run_id: str, log_level: str = "INFO", log_file: Optional[str] = None):
        self.run_id = run_id
        self._summary = RunSummary(run_id=run_id)
        self._start_times: Dict[str, float] = {}
        self._setup_logging(log_level, log_file)

    def _setup_logging(self, log_level: str, log_file: Optional[str]) -> None:
        level = getattr(logging, log_level.upper(), logging.INFO)
        handlers: List[logging.Handler] = []

        if HAS_RICH:
            handlers.append(RichHandler(rich_tracebacks=True, show_path=False))
        else:
            handlers.append(logging.StreamHandler(sys.stdout))

        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

        logging.basicConfig(level=level, handlers=handlers, format="%(message)s", datefmt="[%X]")
        self._logger = logging.getLogger(f"openclaw.{self.run_id[:8]}")

    def _log(self, level: str, event: str, **kwargs) -> None:
        extra = {"run_id": self.run_id, **kwargs}
        msg = f"[{event}] " + " ".join(f"{k}={v}" for k, v in extra.items())
        getattr(self._logger, level.lower(), self._logger.info)(msg)

    def step_start(self, step: str, url: Optional[str] = None) -> None:
        self._start_times[step] = time.monotonic()
        self._log("info", "step_start", step=step, url=url or "")

    def step_end(self, step: str, status: str = "success", error: Optional[str] = None, platform: Optional[str] = None) -> int:
        start = self._start_times.pop(step, time.monotonic())
        duration_ms = int((time.monotonic() - start) * 1000)
        self._summary.step_durations[step].append(duration_ms)

        if platform:
            if status == "success":
                self._summary.platform_stats[platform]["success"] += 1
            else:
                self._summary.platform_stats[platform]["failed"] += 1

        self._log(
            "info" if status == "success" else "warning",
            "step_end",
            step=step, status=status, duration_ms=duration_ms,
            error=error or ""
        )
        return duration_ms

    def video_success(self) -> None:
        self._summary.total_videos += 1
        self._summary.success_count += 1

    def video_skipped(self, reason: str = "") -> None:
        self._summary.total_videos += 1
        self._summary.skipped_count += 1
        self._log("info", "video_skipped", reason=reason)

    def video_failed(self, error: str = "") -> None:
        self._summary.total_videos += 1
        self._summary.failed_count += 1
        self._log("warning", "video_failed", error=error)

    def record_llm_usage(self, model: str, input_tokens: int, output_tokens: int, cost_usd: float = 0.0) -> None:
        self._summary.total_input_tokens += input_tokens
        self._summary.total_output_tokens += output_tokens
        self._summary.total_cost_usd += cost_usd
        self._log("debug", "llm_usage", model=model, input_tokens=input_tokens,
                  output_tokens=output_tokens, cost_usd=round(cost_usd, 6))

    def print_summary(self) -> None:
        s = self._summary
        avg_durations = {
            step: int(sum(times) / len(times))
            for step, times in s.step_durations.items()
            if times
        }
        self._log("info", "run_summary",
                  total=s.total_videos, success=s.success_count,
                  skipped=s.skipped_count, failed=s.failed_count,
                  avg_step_ms=avg_durations,
                  total_tokens=s.total_input_tokens + s.total_output_tokens,
                  total_cost_usd=round(s.total_cost_usd, 4))

    @property
    def summary(self) -> RunSummary:
        return self._summary
