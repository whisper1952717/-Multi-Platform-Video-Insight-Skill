"""Video Insight CLI 入口 — Multi-Platform Video Insight Skill System."""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from typing import Dict, Optional


# ── 模型选择确认界面 ──────────────────────────────────────────────────────────

async def _maybe_use_gateway(settings) -> Optional[Dict]:
    """无任何外部 API key 时，询问用户是否使用 openclaw gateway。

    Returns:
        model_configs（使用 gateway）或 None（用户拒绝）
    """
    from openclaw.llm.gateway import probe_gateway, load_gateway_pref, save_gateway_pref
    from openclaw.config.presets import OPENCLAW_GATEWAY_PRESET

    # 检查用户偏好
    pref = load_gateway_pref()
    if pref == "never":
        print("\n⚠️  未配置任何 API key，且已设置不使用 openclaw gateway。")
        print("   请在 ~/.openclaw/openclaw.json 中配置至少一个 API key。")
        return None

    # 探测 gateway
    print("\n🔍 未检测到任何 API key，正在探测 openclaw gateway...")
    gateway_info = await probe_gateway()

    if gateway_info is None:
        print("   ⚠️  openclaw gateway 不可达，请确认 openclaw 正在运行。")
        print("   或在 ~/.openclaw/openclaw.json 中配置 API key。")
        return None

    current_model = gateway_info.get("model", "unknown")
    all_models = gateway_info.get("all_models", [])

    if pref == "always":
        print(f"   ✅ 已自动使用 openclaw gateway（当前模型：{current_model}）")
        return _build_gateway_configs(current_model, all_models)

    # 询问用户
    print(f"\n   检测到 openclaw gateway 在线，当前模型：{current_model}")
    if len(all_models) > 1:
        print(f"   可用模型：{', '.join(all_models[:5])}" + ("..." if len(all_models) > 5 else ""))
    print()
    print("   是否通过 openclaw 的大模型来执行分析？")
    print("   [1] 是，仅本次")
    print("   [2] 是，以后都用（记住选择）")
    print("   [3] 否，我去配置 API key")

    try:
        choice = input("\n   请选择 [1/2/3] > ").strip()
    except (EOFError, KeyboardInterrupt):
        return None

    if choice == "2":
        save_gateway_pref("always")
        print("   ✅ 已记住，以后自动使用 openclaw gateway")
        return _build_gateway_configs(current_model, all_models)
    elif choice == "1":
        return _build_gateway_configs(current_model, all_models)
    else:
        print("   请在 ~/.openclaw/openclaw.json 中配置 API key 后重试。")
        return None


def _build_gateway_configs(primary_model: str, all_models: list) -> Dict:
    """根据 gateway 当前模型构建 model_configs。

    策略：分类用最轻量的模型（或 primary），分析/聚合用 primary。
    """
    from openclaw.config.settings import LLMModelConfig

    # 找轻量模型用于分类（优先选 mini/turbo/flash/lite 类）
    classifier_model = primary_model
    for m in all_models:
        ml = m.lower()
        if any(k in ml for k in ("mini", "turbo", "flash", "lite", "8b", "small")):
            classifier_model = m
            break

    return {
        "TopicClassifier":    LLMModelConfig(provider="openclaw", model=classifier_model, max_tokens=1024, temperature=0.1),
        "VideoAnalyzer":      LLMModelConfig(provider="openclaw", model=primary_model,    max_tokens=4096, temperature=0.3),
        "InsightsAggregator": LLMModelConfig(provider="openclaw", model=primary_model,    max_tokens=4096, temperature=0.3),
    }

async def _confirm_model_config(settings) -> Optional[Dict]:
    """展示推荐的模型方案，让用户确认或调整。

    返回最终确认的 model_configs dict，用户取消则返回 None。
    """
    from openclaw.config.presets import (
        PRESETS, PRESET_DESCRIPTIONS, recommend_preset, get_available_providers
    )
    from openclaw.config.settings import LLMPreset, LLMModelConfig
    from openclaw.llm.gateway import probe_gateway

    available = get_available_providers(settings.llm_providers)
    # 排除 openclaw 本身，只看外部 API key
    external = [p for p in available if p != "openclaw"]

    # 无任何外部 key → 走 gateway 询问流程
    if not external:
        return await _maybe_use_gateway(settings)

    # 探测 gateway（后台，不阻塞）
    gateway_info = None
    try:
        gateway_info = await probe_gateway()
    except Exception:
        pass

    # 自动推荐预设
    recommended = recommend_preset(settings.llm_providers)
    if settings.llm_preset != LLMPreset.COST_EFFECTIVE:
        recommended = settings.llm_preset.value

    model_configs = dict(PRESETS[recommended])

    print("\n🤖 模型配置确认")
    print("─" * 56)
    display_providers = external[:]
    if gateway_info:
        display_providers.append(f"openclaw({gateway_info['model']})")
    print(f"  已检测到的 key：{', '.join(display_providers)}")
    print(f"  推荐方案：{recommended}  ({PRESET_DESCRIPTIONS.get(recommended, '')})")
    if gateway_info:
        print(f"  💡 openclaw gateway 在线（{gateway_info['model']}），可在逐模块调整时选用")
    print()
    _print_model_table(model_configs)

    print("\n  选项：")
    print("  [Enter]   确认使用当前方案")
    print("  [p]       切换预设方案")
    print("  [e]       逐模块调整模型")
    print("  [q]       取消退出")

    while True:
        try:
            choice = input("\n请选择 > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n已取消。")
            return None

        if choice in ("", "y"):
            return model_configs

        elif choice == "q":
            print("已取消。")
            return None

        elif choice == "p":
            model_configs = _select_preset(available)
            if model_configs is None:
                return None
            _print_model_table(model_configs)
            print("\n  [Enter] 确认  [e] 逐模块调整  [p] 重新选预设  [q] 取消")

        elif choice == "e":
            model_configs = _edit_modules(model_configs, available)
            _print_model_table(model_configs)
            print("\n  [Enter] 确认  [p] 切换预设  [q] 取消")

        else:
            print("  无效输入，请重新选择。")


def _print_model_table(model_configs: Dict) -> None:
    """打印模块→模型对应表。"""
    print(f"  {'模块':<22} {'Provider':<12} {'模型'}")
    print("  " + "-" * 52)
    for component, cfg in model_configs.items():
        print(f"  {component:<22} {cfg.provider:<12} {cfg.model}")


def _select_preset(available: list) -> Optional[Dict]:
    """让用户从预设列表中选择。"""
    from openclaw.config.presets import PRESETS, PRESET_DESCRIPTIONS, PROVIDER_ENV_MAP

    print("\n  可用预设方案：")
    preset_list = list(PRESETS.keys())
    for i, name in enumerate(preset_list, 1):
        desc = PRESET_DESCRIPTIONS.get(name, "")
        # 检查该预设所需的 provider 是否都已配置
        needed = {cfg.provider for cfg in PRESETS[name].values()}
        missing = needed - set(available)
        status = "⚠️  缺少key" if missing else "✅"
        print(f"  [{i}] {name:<18} {status}  {desc}")

    try:
        sel = input("\n  输入编号 > ").strip()
        idx = int(sel) - 1
        if 0 <= idx < len(preset_list):
            return dict(PRESETS[preset_list[idx]])
    except (ValueError, KeyboardInterrupt):
        pass
    print("  无效选择，保持原方案。")
    return None


def _edit_modules(model_configs: Dict, available: list) -> Dict:
    """逐模块让用户调整 provider 和 model，提供推荐列表 + 支持自由输入。"""
    from openclaw.config.presets import PROVIDER_RECOMMENDED_MODELS
    from openclaw.config.settings import LLMModelConfig

    configs = dict(model_configs)

    print(f"\n  逐模块调整（直接回车保持不变）：")
    for component in list(configs.keys()):
        cfg = configs[component]
        print(f"\n  ┌─ [{component}]")
        print(f"  │  当前：{cfg.provider} / {cfg.model}")

        # provider 选择
        try:
            new_provider = input(f"  │  Provider ({'/'.join(available)}) [{cfg.provider}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        new_provider = new_provider or cfg.provider

        # 展示该 provider 的推荐模型列表
        recommended = PROVIDER_RECOMMENDED_MODELS.get(new_provider, [])
        if recommended:
            print(f"  │  推荐模型：")
            for i, m in enumerate(recommended, 1):
                print(f"  │    [{i}] {m['model']:<42} {m['price']:<18} {m['desc']}")
            print(f"  │    [0] 自定义输入...")

        # model 选择：编号或直接输入
        try:
            model_input = input(f"  │  选择编号或输入模型名 [{cfg.model}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        new_model = cfg.model
        if model_input == "":
            new_model = cfg.model
        elif model_input.isdigit():
            idx = int(model_input)
            if idx == 0:
                try:
                    custom = input(f"  │  输入模型名: ").strip()
                    new_model = custom or cfg.model
                except (EOFError, KeyboardInterrupt):
                    pass
            elif 1 <= idx <= len(recommended):
                new_model = recommended[idx - 1]["model"]
        else:
            new_model = model_input

        print(f"  └─ 已设置：{new_provider} / {new_model}")
        configs[component] = LLMModelConfig(
            provider=new_provider,
            model=new_model,
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
        )

    return configs


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

def _build_pipeline(settings, datastore, monitor, model_configs=None):
    """构建流水线所有组件。model_configs 为 None 时从 settings 自动获取。"""
    from openclaw.middleware.access_manager import SourceAccessManager
    from openclaw.pipeline.downloader import VideoDownloader
    from openclaw.pipeline.transcriber import TranscriptGenerator
    from openclaw.pipeline.cleaner import TranscriptCleaner
    from openclaw.pipeline.segmenter import VideoSegmenter
    from openclaw.pipeline.classifier import TopicClassifier
    from openclaw.pipeline.analyzer import VideoAnalyzer
    from openclaw.pipeline.manager import AsyncPipelineManager
    from openclaw.llm.client import LLMClient

    if model_configs is None:
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

    # 模型选择确认
    model_configs = await _confirm_model_config(settings)
    if model_configs is None:
        return 0

    datastore = await _init_datastore(settings)
    pipeline, llm_client, model_configs = _build_pipeline(settings, datastore, monitor, model_configs)

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

    # 模型选择确认
    model_configs = await _confirm_model_config(settings)
    if model_configs is None:
        return 0

    datastore = await _init_datastore(settings)
    pipeline, llm_client, model_configs = _build_pipeline(settings, datastore, monitor, model_configs)

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
    return f"video_insight_report_{mode}_{ts}.{ext}"


# ── 参数解析 ──────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="video-insight",
        description="Video Insight — Multi-Platform Video Insight Skill System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  video-insight mode1 https://space.bilibili.com/12345 --max-videos 30
  video-insight mode2 "AI创业" --platforms bilibili youtube --max-creators 5
  video-insight mode1 https://www.youtube.com/@channel --use-last-config
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
