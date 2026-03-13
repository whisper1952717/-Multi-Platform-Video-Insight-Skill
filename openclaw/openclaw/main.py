"""OpenClaw CLI 入口 — Multi-Platform Video Insight Skill System."""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from typing import Optional


# ── 成本预估展示 ──────────────────────────────────────────────────────────────

def _show_cost_estimate(settings, num_videos: int) -> bool:
    """展示成本预估，返回用户是否确认继续。"""
    from openclaw.config.settings import CostEstimator

    model_configs = settings.get_active_model_config()
    estimate = CostEstimator.estimate(model_configs, num_videos=num_videos)

    print("\n📊 成本预估")
    print("─" * 40)
    for item in estimate["breakdown"]:
        print(f"  {item['component']:<22} {item['model']:<25} ${item['estimated_cost_usd']:.4f}")
    print("─" * 40)
    print(f"  {'预估总计':<22} {'':25} ${estimate['total_usd']:.4f}")
    print(f"\n  ⚠️  {estimate['variance_note']}")
    print()

    try:
        answer = input("是否继续？[Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n已取消。")
        return False

    return answer in ("", "y", "yes", "是")


# ── 配置加载辅助 ──────────────────────────────────────────────────────────────

def _load_settings(args):
    """根据 CLI 参数加载配置，支持 use-last-config 快速启动。"""
    from openclaw.config.settings import ConfigPersistence, load_settings

    # 优先使用上次配置
    if getattr(args, "use_last_config", False):
        last = ConfigPersistence.load_last_used()
        if last:
            print("✅ 已加载上次使用的配置")
            from openclaw.config.settings import AppSettings
            return AppSettings(**last)
        else:
            print("⚠️  未找到上次配置，使用默认配置")

    settings = load_settings("config.yaml")

    # CLI 参数覆盖 llm_preset
    if hasattr(args, "llm_preset") and args.llm_preset:
        from openclaw.config.settings import LLMPreset
        try:
            settings = settings.model_copy(update={"llm_preset": LLMPreset(args.llm_preset)})
        except ValueError:
            print(f"⚠️  未知 LLM 预设 '{args.llm_preset}'，使用默认值 cost_effective")

    return settings


# ── 数据存储初始化 ────────────────────────────────────────────────────────────

async def _init_datastore(settings):
    """根据配置初始化数据存储后端。"""
    if settings.storage.db_type == "postgresql":
        from openclaw.storage.postgres_backend import PostgresDataStore
        ds = PostgresDataStore(settings.storage.db_path)
    else:
        from openclaw.storage.sqlite_backend import SQLiteDataStore
        ds = SQLiteDataStore(settings.storage.db_path)
    await ds.initialize()
    return ds


# ── 流水线组件初始化 ──────────────────────────────────────────────────────────

def _build_pipeline(settings, datastore, monitor):
    """构建流水线所有组件。"""
    from openclaw.middleware.access_manager import SourceAccessManager
    from openclaw.pipeline.downloader import VideoDownloader
    from openclaw.pipeline.transcriber import TranscriptGenerator
    from openclaw.pipeline.cleaner import TranscriptCleaner
    from openclaw.pipeline.segmenter import VideoSegmenter
    from openclaw.pipeline.classifier import TopicClassifier
    from openclaw.pipeline.analyzer import VideoAnalyzer
    from openclaw.pipeline.manager import AsyncPipelineManager
    from openclaw.llm.client import LLMClient

    model_configs = settings.get_active_model_config()
    access_mgr = SourceAccessManager(settings.platforms)
    llm_client = LLMClient(settings.llm_providers)

    downloader = VideoDownloader(access_manager=access_mgr, datastore=datastore)
    transcriber = TranscriptGenerator(datastore=datastore)
    cleaner = TranscriptCleaner()
    segmenter = VideoSegmenter()
    classifier = TopicClassifier(
        llm_client=llm_client,
        model_config=model_configs.get("TopicClassifier"),
    )
    analyzer = VideoAnalyzer(
        llm_client=llm_client,
        model_config=model_configs.get("VideoAnalyzer"),
    )

    pipeline = AsyncPipelineManager(
        downloader=downloader,
        transcriber=transcriber,
        cleaner=cleaner,
        segmenter=segmenter,
        classifier=classifier,
        analyzer=analyzer,
        datastore=datastore,
        monitor=monitor,
        max_concurrency=getattr(settings, "_max_concurrency", 3),
        cache_enabled=settings.storage.cache_enabled,
        cache_ttl_hours=settings.storage.cache_ttl_hours,
    )
    return pipeline, llm_client, model_configs


# ── Mode1 执行 ────────────────────────────────────────────────────────────────

async def _run_mode1(args) -> int:
    """Mode1：单博主分析流水线。"""
    from openclaw.monitoring.logger import LoggingMonitor
    from openclaw.adapters.base import PlatformRouter
    from openclaw.aggregation.aggregator import InsightsAggregator
    from openclaw.report.generator import ReportGenerator

    settings = _load_settings(args)
    monitor = LoggingMonitor(
        log_level=settings.log_level,
        log_file=settings.log_file,
    )
    monitor.run_start(mode="mode1", target=args.url)

    # 成本预估
    if not _show_cost_estimate(settings, args.max_videos):
        return 0

    datastore = await _init_datastore(settings)
    pipeline, llm_client, model_configs = _build_pipeline(settings, datastore, monitor)

    # 平台路由 + 视频列表获取
    router = PlatformRouter(settings.platforms)
    adapter = router.get_adapter(args.url)
    if adapter is None:
        print(f"❌ 不支持的 URL：{args.url}")
        return 1

    print(f"\n🔍 正在获取博主视频列表...")
    videos = await adapter.fetch_video_list(
        url=args.url,
        time_window=args.time_window,
        max_videos=args.max_videos,
    )
    print(f"   找到 {len(videos)} 个视频")

    if not videos:
        print("⚠️  未找到符合条件的视频，退出。")
        return 0

    # 流水线处理
    print(f"\n⚙️  开始处理流水线...")
    analyses = await pipeline.process_single_creator(videos)
    print(f"   完成分析：{len(analyses)} 个视频")

    # 聚合
    aggregator = InsightsAggregator(
        llm_client=llm_client,
        mode1_config=model_configs.get("InsightsAggregator"),
    )
    metadata = {
        "creator": args.url,
        "platform": adapter.platform_name,
        "videos_analyzed": len(analyses),
        "videos_skipped": len(videos) - len(analyses),
        "time_range": args.time_window,
        "generated_at": datetime.now().isoformat(),
    }
    insights = await aggregator.aggregate_mode1(analyses, metadata)

    # 报告生成
    output_path = _make_output_path(args.output_format, "mode1")
    report = ReportGenerator()
    content = report.generate(insights, output_format=args.output_format, output_path=output_path)

    print(f"\n✅ 报告已生成：{output_path}")
    monitor.run_end()

    # 保存本次配置为"上次使用"
    from openclaw.config.settings import ConfigPersistence
    ConfigPersistence.save_config("_last", settings.model_dump(), mark_last_used=True)

    return 0


# ── Mode2 执行 ────────────────────────────────────────────────────────────────

async def _run_mode2(args) -> int:
    """Mode2：赛道/话题多博主分析流水线。"""
    from openclaw.monitoring.logger import LoggingMonitor
    from openclaw.adapters.base import PlatformRouter
    from openclaw.aggregation.aggregator import InsightsAggregator
    from openclaw.report.generator import ReportGenerator

    settings = _load_settings(args)
    # 注入 max_concurrency 到 settings（临时属性）
    object.__setattr__(settings, "_max_concurrency", args.max_concurrency)

    monitor = LoggingMonitor(
        log_level=settings.log_level,
        log_file=settings.log_file,
    )
    monitor.run_start(mode="mode2", target=args.keyword)

    # 成本预估（按 max_creators * max_videos 估算）
    estimated_videos = args.max_creators * args.max_videos
    if not _show_cost_estimate(settings, estimated_videos):
        return 0

    datastore = await _init_datastore(settings)
    pipeline, llm_client, model_configs = _build_pipeline(settings, datastore, monitor)

    router = PlatformRouter(settings.platforms)
    creator_videos: dict = {}

    for platform in args.platforms:
        adapter = router.get_adapter_by_platform(platform)
        if adapter is None:
            print(f"⚠️  不支持的平台：{platform}，跳过")
            continue

        print(f"\n🔍 [{platform}] 搜索关键词：{args.keyword}")
        creators = await adapter.search_creators(
            keyword=args.keyword,
            max_creators=args.max_creators,
        )
        print(f"   找到 {len(creators)} 个博主")

        for creator_url in creators:
            videos = await adapter.fetch_video_list(
                url=creator_url,
                time_window=args.time_window,
                max_videos=args.max_videos,
            )
            if videos:
                creator_videos[creator_url] = videos

    if not creator_videos:
        print("⚠️  未找到符合条件的博主/视频，退出。")
        return 0

    total_videos = sum(len(v) for v in creator_videos.values())
    print(f"\n⚙️  共 {len(creator_videos)} 个博主，{total_videos} 个视频，开始并行处理...")

    analyses_map = {}
    for creator, videos in creator_videos.items():
        analyses = await pipeline._process_creator_with_semaphore(creator, videos)
        analyses_map[creator] = analyses

    # 聚合
    aggregator = InsightsAggregator(
        llm_client=llm_client,
        mode2_config=model_configs.get("InsightsAggregator"),
    )
    metadata = {
        "topic": args.keyword,
        "platforms": args.platforms,
        "creators_analyzed": len(analyses_map),
        "total_videos_analyzed": sum(len(v) for v in analyses_map.values()),
        "time_range": args.time_window,
        "generated_at": datetime.now().isoformat(),
    }
    insights = await aggregator.aggregate_mode2(analyses_map, metadata)

    # 报告生成
    output_path = _make_output_path(args.output_format, "mode2")
    report = ReportGenerator()
    report.generate(insights, output_format=args.output_format, output_path=output_path)

    print(f"\n✅ 报告已生成：{output_path}")
    monitor.run_end()

    from openclaw.config.settings import ConfigPersistence
    ConfigPersistence.save_config("_last", settings.model_dump(), mark_last_used=True)

    return 0


# ── 辅助函数 ──────────────────────────────────────────────────────────────────

def _make_output_path(output_format: str, mode: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = {"Markdown": "md", "PDF": "pdf", "JSON": "json"}.get(output_format, "md")
    return f"openclaw_report_{mode}_{ts}.{ext}"


# ── 参数解析 ──────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openclaw",
        description="OpenClaw — Multi-Platform Video Insight Skill System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  openclaw mode1 https://space.bilibili.com/12345 --max-videos 30
  openclaw mode2 "AI创业" --platforms bilibili youtube --max-creators 5
  openclaw mode1 https://www.youtube.com/@channel --use-last-config
        """,
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    # ── Mode1 ──
    mode1 = subparsers.add_parser("mode1", help="单博主深度分析")
    mode1.add_argument("url", help="博主主页 URL（支持 B站/抖音/YouTube/小红书）")
    mode1.add_argument(
        "--time-window",
        default="last_30_days",
        choices=["last_7_days", "last_30_days", "last_90_days", "last_180_days", "last_365_days"],
        help="时间范围（默认：last_30_days）",
    )
    mode1.add_argument("--max-videos", type=int, default=20, metavar="N", help="最大视频数（默认：20）")
    mode1.add_argument(
        "--output-format",
        choices=["Markdown", "PDF", "JSON"],
        default="Markdown",
        help="输出格式（默认：Markdown）",
    )
    mode1.add_argument(
        "--llm-preset",
        choices=["cost_effective", "quality", "flagship", "china_eco"],
        default="cost_effective",
        help="LLM 预设方案（默认：cost_effective）",
    )
    mode1.add_argument("--use-last-config", action="store_true", help="使用上次保存的配置快速启动")
    mode1.add_argument("--config", default="config.yaml", metavar="PATH", help="配置文件路径（默认：config.yaml）")

    # ── Mode2 ──
    mode2 = subparsers.add_parser("mode2", help="赛道/话题多博主分析")
    mode2.add_argument("keyword", help="搜索关键词（如：AI创业、量化交易）")
    mode2.add_argument(
        "--platforms",
        nargs="+",
        default=["bilibili", "youtube"],
        choices=["bilibili", "douyin", "youtube", "xiaohongshu"],
        help="目标平台列表（默认：bilibili youtube）",
    )
    mode2.add_argument(
        "--time-window",
        default="last_30_days",
        choices=["last_7_days", "last_30_days", "last_90_days", "last_180_days", "last_365_days"],
        help="时间范围（默认：last_30_days）",
    )
    mode2.add_argument("--max-videos", type=int, default=20, metavar="N", help="每博主最大视频数（默认：20）")
    mode2.add_argument("--max-creators", type=int, default=10, metavar="N", help="最大博主数（默认：10）")
    mode2.add_argument("--max-concurrency", type=int, default=3, metavar="N", help="最大并发博主数（默认：3）")
    mode2.add_argument(
        "--output-format",
        choices=["Markdown", "PDF", "JSON"],
        default="Markdown",
        help="输出格式（默认：Markdown）",
    )
    mode2.add_argument(
        "--llm-preset",
        choices=["cost_effective", "quality", "flagship", "china_eco"],
        default="cost_effective",
        help="LLM 预设方案（默认：cost_effective）",
    )
    mode2.add_argument("--use-last-config", action="store_true", help="使用上次保存的配置快速启动")
    mode2.add_argument("--config", default="config.yaml", metavar="PATH", help="配置文件路径（默认：config.yaml）")

    return parser


# ── 主入口 ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    try:
        exit_code = asyncio.run(_run_mode1(args) if args.mode == "mode1" else _run_mode2(args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  用户中断，已退出。")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 运行出错：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
