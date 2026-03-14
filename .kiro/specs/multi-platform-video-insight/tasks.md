# 实现计划：Multi-Platform Video Insight Skill System（OpenClaw）

## 概述

基于需求文档和技术设计，将系统实现拆分为增量式编码任务。每个任务构建在前一个任务之上，从基础设施层开始，逐步构建核心流水线，最终完成聚合与报告输出。技术栈：Python 3.11+, asyncio, pydantic-settings, structlog, SQLite/PostgreSQL, yt-dlp, faster-whisper, semantic-text-splitter, ChromaDB/FAISS。

## 任务列表

- [x] 1. 项目结构初始化与核心数据模型
  - [x] 1.1 创建项目目录结构和 pyproject.toml
    - 按照设计文档的项目结构创建所有目录和 `__init__.py` 文件
    - 配置 pyproject.toml，声明所有依赖：pydantic, pydantic-settings, structlog, rich, yt-dlp, faster-whisper, semantic-text-splitter, chromadb, aiohttp, aiosqlite 等
    - 创建 `openclaw/__init__.py` 和 `openclaw/main.py` 入口骨架
    - _需求: 4.1, 4.3_

  - [x] 1.2 实现核心 Pydantic 数据模型（`openclaw/models/types.py`）
    - 实现所有数据模型：VideoInfo, VideoStatus, DownloadResult, TimestampedSegment, TranscriptResult, ContentType, TopicClassification, CoreSignal, CognitionFramework, MethodologyFragment, HighValueQuote, VideoAnalysis, BusinessOpportunity, QualitySummary, Mode1Insights, Mode2Insights, ConsensusAndDivergence
    - 所有 confidence_score 字段使用 `Field(ge=0.0, le=1.0)` 约束
    - _需求: 21.1, 21.2, 21.3, 21.4, 21.5, 21.6, 21.7, 12.3_

  - [x]* 1.3 为核心数据模型编写属性测试
    - **属性 1: confidence_score 范围约束** — 所有包含 confidence_score 的模型，值必须在 [0.0, 1.0] 范围内
    - **验证需求: 21.2, 12.3**
    - **属性 2: Mode1Insights/Mode2Insights 序列化往返一致性** — 模型实例序列化为 JSON 后反序列化应得到等价对象
    - **验证需求: 21.1, 21.3, 21.4**

- [x] 2. 配置管理与 LLM 客户端
  - [x] 2.1 实现 ConfigManager（`openclaw/config/settings.py` 和 `openclaw/config/presets.py`）
    - 实现 AppSettings, LLMPreset, LLMProviderConfig, LLMModelConfig, PlatformConfig, StorageConfig 等配置模型
    - 支持 YAML 配置文件加载和环境变量覆盖（`env_file=".env"`, `env_nested_delimiter="__"`）
    - 实现四种预设方案定义（cost_effective, quality, flagship, china_eco）
    - 实现配置校验，无效配置返回明确错误信息
    - 创建示例 `config.yaml` 配置文件
    - _需求: 4.1, 4.2, 4.3, 4.4, 2.1, 2.2, 2.7_

  - [x] 2.2 实现模型配置持久化（`openclaw/config/settings.py` 扩展）
    - 实现 saved_configs 表的读写逻辑：保存/加载/列出/删除自定义方案
    - 实现 `is_last_used` 标记，支持自动加载上次配置
    - 支持多套命名方案的保存和切换
    - _需求: 3.1, 3.2, 3.3, 3.4_

  - [x] 2.3 实现成本预估功能（`openclaw/config/settings.py` 扩展）
    - 根据预估调用次数、单次预估 token 数和模型单价计算预估成本
    - 展示每个 LLM 环节（TopicClassifier、VideoAnalyzer、InsightsAggregator）的分项成本和总计
    - 标注实际成本波动幅度范围
    - _需求: 2.4, 2.5, 2.6_

  - [x] 2.4 实现统一 LLM 客户端（`openclaw/llm/client.py`）
    - 实现 LLMClient 类，支持多 provider 的 aiohttp session 管理
    - 实现 `call` 方法：构建请求、发送、解析响应、校验 response_schema
    - 支持 few-shot 示例注入和 JSON Schema 约束输出
    - 记录 token 消耗到 LoggingMonitor
    - _需求: 22.4, 22.5, 24.5_

  - [x] 2.5 实现 Prompt 模板和 JSON Schema 定义（`openclaw/llm/prompts.py` 和 `openclaw/llm/schemas.py`）
    - 定义 TopicClassifier 的 Prompt 模板和 JSON Schema
    - 定义 VideoAnalyzer 的 Prompt 模板（含 Few-shot 示例）和 JSON Schema
    - 定义 InsightsAggregator 的 Mode1/Mode2 Prompt 模板和 JSON Schema
    - _需求: 22.1, 22.2, 22.3, 22.4, 22.5_

  - [x]* 2.6 为 ConfigManager 编写单元测试
    - 测试 YAML 加载、环境变量覆盖、无效配置校验错误
    - 测试预设方案自动配置三个 LLM 环节
    - 测试 llm_preset 与 llm_custom 同时提供时的优先级逻辑
    - _需求: 4.1, 4.2, 4.3, 4.4, 2.7_

- [x] 3. 检查点 — 确保所有测试通过
  - 确保所有测试通过，如有疑问请询问用户。

- [x] 4. 数据存储层
  - [x] 4.1 实现 DataStore 抽象层和 SQLite 后端（`openclaw/storage/datastore.py` 和 `openclaw/storage/sqlite_backend.py`）
    - 实现 BaseDataStore 抽象基类，定义所有接口方法
    - 实现 SQLiteDataStore：建表（videos, transcripts, analyses, insights, run_logs, checkpoints, saved_configs）、CRUD 操作
    - 实现缓存逻辑：`is_cached` 方法根据 cache_ttl 判断是否需要重新处理
    - 实现内容变更检测：`has_content_changed` 方法对比 publish_date 和 view_count
    - 实现视频状态管理：pending → downloaded → transcribed → analyzed / skipped
    - _需求: 18.1, 18.2, 18.3, 18.4, 18.5_

  - [x] 4.2 实现断点续传功能（`openclaw/storage/datastore.py` 扩展）
    - 实现 `save_checkpoint` 和 `load_checkpoint` 方法
    - 检查点记录 run_id、当前处理进度、已完成视频列表
    - 系统重启时从检查点恢复未完成的视频处理
    - _需求: 18.6, 20.5_

  - [x] 4.3 实现 PostgreSQL 后端（`openclaw/storage/postgres_backend.py`）
    - 实现 PostgresDataStore，复用 BaseDataStore 接口
    - 使用 asyncpg 或 aiopg 实现异步数据库操作
    - 建表 SQL 适配 PostgreSQL 语法
    - _需求: 18.2_

  - [x]* 4.4 为 DataStore 编写属性测试
    - **属性 3: 缓存一致性** — 在 cache_ttl 内保存的视频，`is_cached` 应返回 True；超过 ttl 应返回 False
    - **验证需求: 18.3**
    - **属性 4: 断点续传完整性** — save_checkpoint 后 load_checkpoint 应返回等价状态
    - **验证需求: 18.6, 20.5**

- [x] 5. 日志监控与网络访问管理
  - [x] 5.1 实现 LoggingMonitor（`openclaw/monitoring/logger.py`）
    - 使用 structlog + Rich 配置结构化日志，包含时间戳、日志级别、模块名、事件名、URL、耗时、run_id
    - 实现步骤耗时和成功/失败状态记录
    - 实现平台抓取成功率统计
    - 实现 LLM token 消耗和费用记录
    - 实现运行结束摘要生成（总视频数、成功数、跳过数、失败数、各模块平均耗时）
    - 支持同时输出到控制台和日志文件
    - _需求: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6_

  - [x] 5.2 实现 SourceAccessManager（`openclaw/middleware/access_manager.py`）
    - 实现全局信号量（最大并发 2）和平台级锁
    - 实现请求间随机延时（1~8 秒，按平台可配置）和单平台最低 3 秒间隔
    - 实现请求头伪装：UA 池轮换、Referer、Accept-Language
    - 实现指数退避重试（最多 3 次：1s, 2s, 4s），针对 HTTP 403/429
    - 实现连续失败 5 次暂停平台 10 分钟
    - 实现单视频失败跳过不中断流水线
    - _需求: 16.1, 16.2, 16.3, 16.4, 16.5, 16.12, 16.13, 16.14, 20.1, 20.4_

  - [x] 5.3 实现 Cookie 管理和代理池接口（`openclaw/middleware/access_manager.py` 扩展）
    - 实现 Cookie 生命周期管理：手动导入、加密存储、过期提醒、过期后降级为无登录模式
    - 预留 ProxyPoolInterface，支持 HTTP/SOCKS5 代理
    - 实现代理轮换（按请求数或遇封禁时）和代理可用性验证
    - 代理不可用时降级为直连模式
    - _需求: 16.6, 16.7, 16.8, 16.9, 16.10, 16.11_

  - [ ]* 5.4 为 SourceAccessManager 编写单元测试
    - 测试随机延时范围、全局并发限制、平台间隔限制
    - 测试指数退避重试逻辑（模拟 403/429 响应）
    - 测试连续失败暂停平台逻辑
    - _需求: 16.2, 16.3, 16.4, 16.12, 16.13_

- [x] 6. 检查点 — 确保所有测试通过
  - 确保所有测试通过，如有疑问请询问用户。

- [x] 7. 平台适配器与视频列表获取
  - [x] 7.1 实现 PlatformAdapter 基类和路由器（`openclaw/adapters/base.py`）
    - 实现 BasePlatformAdapter 抽象基类：`fetch_video_list` 和 `search_creators` 方法
    - 实现 PlatformRouter：URL 正则匹配识别平台、路由到对应适配器
    - 不支持的 URL 返回明确错误信息
    - _需求: 5.1, 5.2, 5.3, 5.4_

  - [x] 7.2 实现 B站适配器（`openclaw/adapters/bilibili.py`）
    - 实现 BilibiliAdapter，通过 SourceAccessManager 发起请求
    - 支持 Cookie 登录、CC 字幕优先获取
    - 获取视频列表并统一为 VideoInfo 格式
    - _需求: 6.1, 6.3, 6.4, 23.1, 23.5_

  - [x] 7.3 实现抖音适配器（`openclaw/adapters/douyin.py`）
    - 实现 DouyinAdapter，处理特殊签名机制
    - 支持 Cookie 登录
    - _需求: 6.1, 6.3, 6.4, 23.2, 23.5_

  - [x] 7.4 实现 YouTube 适配器（`openclaw/adapters/youtube.py`）
    - 实现 YouTubeAdapter，使用 yt-dlp 原生支持
    - 优先获取自动字幕
    - _需求: 6.1, 6.3, 6.4, 23.3, 23.5_

  - [x] 7.5 实现小红书适配器（`openclaw/adapters/xiaohongshu.py`）
    - 实现 XiaohongshuAdapter，支持 Cookie 登录
    - 建议配合代理使用
    - _需求: 6.1, 6.3, 6.4, 23.4, 23.5_

  - [x] 7.6 实现 VideoListFetcher 逻辑（集成到适配器和 PipelineManager）
    - Mode1：根据博主 URL 获取视频列表
    - Mode2：根据关键词在指定平台搜索博主和视频，受 max_creators 限制
    - 实现 time_window 过滤和 max_videos 限制
    - _需求: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x]* 7.7 为 PlatformRouter 编写属性测试
    - **属性 5: 平台识别确定性** — 同一 URL 多次调用 detect_platform 应返回相同平台
    - **验证需求: 5.1**
    - **属性 6: 不支持 URL 错误处理** — 非法或不支持的 URL 应返回明确错误而非崩溃
    - **验证需求: 5.4**

- [x] 8. 视频处理流水线（下载→转录→清洗→分段）
  - [x] 8.1 实现 VideoDownloader（`openclaw/pipeline/downloader.py`）
    - 使用 yt-dlp 作为核心下载引擎
    - 实现降级策略链：字幕获取 → 音频下载 → 跳过并记录
    - B站优先 CC 字幕
    - 通过 SourceAccessManager 管理网络请求
    - 下载结果持久化到 DataStore
    - _需求: 7.1, 7.2, 7.3, 7.4, 7.5, 20.6_

  - [x] 8.2 实现 TranscriptGenerator（`openclaw/pipeline/transcriber.py`）
    - 有字幕文件时解析为带时间戳文本
    - 无字幕时调用 faster-whisper 转录音频
    - 输出 TranscriptResult（含时间戳信息）
    - 转录结果持久化到 DataStore
    - _需求: 8.1, 8.2, 8.3, 20.2_

  - [x] 8.3 实现 TranscriptCleaner（`openclaw/pipeline/cleaner.py`）
    - 实现本地规则引擎：正则匹配去广告、口头禅词库过滤、重复段落去重
    - 不消耗 LLM token
    - 实现 `clean_with_fallback`：规则引擎处理不了时降级使用轻量 LLM
    - _需求: 9.1, 9.2, 9.3, 24.1_

  - [x] 8.4 实现 VideoSegmenter（`openclaw/pipeline/segmenter.py`）
    - 使用 semantic-text-splitter 进行语义分段
    - 基于语义相似度分段，非固定长度
    - 不消耗 LLM token
    - 输出分段文本片段列表
    - _需求: 10.1, 10.2, 10.3, 24.1_

  - [x]* 8.5 为下载降级策略编写单元测试
    - 测试字幕获取成功路径
    - 测试字幕失败→音频下载降级路径
    - 测试全部失败→跳过并记录路径
    - _需求: 7.1, 7.2, 7.3, 20.6_

  - [x]* 8.6 为 TranscriptCleaner 编写属性测试
    - **属性 7: 清洗幂等性** — 对已清洗文本再次清洗应得到相同结果
    - **验证需求: 9.1, 9.2**

- [x] 9. 检查点 — 确保所有测试通过
  - 确保所有测试通过，如有疑问请询问用户。

- [x] 10. 分类与分析模块
  - [x] 10.1 实现 TopicClassifier（`openclaw/pipeline/classifier.py`）
    - 调用轻量 LLM 进行主题分类
    - 输出 primary_topic, secondary_topics, content_type, business_relevance
    - content_type 限定为：观点输出、教程讲解、案例分析、行业分析、产品推荐、其他
    - business_relevance < 0.3 时标记跳过
    - 使用严格 JSON Schema 约束输出
    - _需求: 11.1, 11.2, 11.3, 11.4, 11.5, 22.1, 24.2, 24.3_

  - [x] 10.2 实现 VideoAnalyzer（`openclaw/pipeline/analyzer.py`）
    - 接收清洗分段后的文本和分类结果作为输入
    - 提取 core_signals, cognition_framework, methodology_fragments, high_value_quotes
    - 每个信号附带 confidence_score 和 evidence
    - 输出 overall_quality 评分
    - 使用强 LLM + Few-shot 示例 + 严格 JSON Schema
    - 分析失败时降级为简单摘要模式
    - _需求: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 22.2, 22.4, 20.3_

  - [x]* 10.3 为 TopicClassifier 编写单元测试
    - 测试 business_relevance < 0.3 时标记跳过逻辑
    - 测试 content_type 枚举约束
    - 模拟 LLM 响应验证 JSON Schema 解析
    - _需求: 11.3, 11.4_

  - [x]* 10.4 为 VideoAnalyzer 编写属性测试
    - **属性 8: confidence_score 评分标准一致性** — 所有输出的 confidence_score 必须在 [0.0, 1.0] 范围内
    - **验证需求: 12.3, 12.4**

- [x] 11. 异步流水线调度
  - [x] 11.1 实现 AsyncPipelineManager（`openclaw/pipeline/manager.py`）
    - 实现 `process_single_creator`：Mode1 串行处理单博主视频列表
    - 实现 `process_multi_creators`：Mode2 并行处理多博主（信号量控制并发数），每博主内部串行
    - 使用 asyncio + aiohttp 实现异步调度
    - 集成 DataStore 的缓存检查（cache_enabled 时跳过已缓存视频）
    - 集成断点续传：处理前检查检查点，每步完成后保存检查点
    - 串联完整流水线：下载 → 转录 → 清洗 → 分段 → 分类 → 分析
    - _需求: 17.1, 17.2, 17.3, 17.4, 18.3, 18.6, 24.4_

  - [x]* 11.2 为 AsyncPipelineManager 编写单元测试
    - 测试 Mode1 串行处理顺序
    - 测试 Mode2 并发数限制（信号量）
    - 测试缓存命中时跳过处理
    - _需求: 17.1, 17.2, 17.4_

- [x] 12. 检查点 — 确保所有测试通过
  - 确保所有测试通过，如有疑问请询问用户。

- [x] 13. 洞察聚合与报告生成
  - [x] 13.1 实现 InsightsAggregator（`openclaw/aggregation/aggregator.py`）
    - Mode1 聚合：提炼核心信号、认知框架、方法论、商业机会、高价值表达
    - Mode2 聚合：提炼趋势信号、共识与分歧、通用方法论、商业机会
    - 相似信号去重合并，confidence_score 加权平均
    - 多次出现的信号赋予更高权重
    - overall_quality < 0.5 的结果降权
    - 仅保留多信号支撑的商业机会
    - 生成 3~5 条 insights_for_me
    - Mode2 额外输出共识点和分歧点（含立场和比例）
    - 使用严格 JSON Schema 约束输出
    - _需求: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 13.8, 22.3_

  - [x] 13.2 实现 InsightMemory（可选）（`openclaw/aggregation/memory.py`）
    - 存储每次运行的聚合洞察结果
    - 支持基于向量检索的历史洞察查询
    - 使用 ChromaDB 或 FAISS 作为向量存储引擎
    - _需求: 14.1, 14.2, 14.3_

  - [x] 13.3 实现 ReportGenerator（`openclaw/report/generator.py`）
    - 支持 Markdown、PDF、JSON 三种输出格式
    - Mode1 报告结构：元数据、核心信号、认知框架、方法论、商业机会、高价值表达、用户启发、质量摘要
    - Mode2 报告结构：元数据、趋势信号、共识与分歧、通用方法论、商业机会、高价值表达、用户启发、质量摘要
    - 质量摘要包含 overall_confidence、low_quality_signals_count、notes
    - PDF 生成使用 weasyprint 或 md2pdf
    - _需求: 15.1, 15.2, 15.3, 15.4, 15.5_

  - [x]* 13.4 为 InsightsAggregator 编写属性测试
    - **属性 9: 去重合并后信号数不超过输入信号总数** — 聚合后的信号数量应 ≤ 输入的所有视频信号数量之和
    - **验证需求: 13.3**
    - **属性 10: 降权一致性** — overall_quality < 0.5 的分析结果在聚合中的权重应低于高质量结果
    - **验证需求: 13.5**

  - [x]* 13.5 为 ReportGenerator 编写单元测试
    - 测试三种输出格式生成
    - 测试 Mode1 和 Mode2 报告结构完整性
    - _需求: 15.1, 15.2, 15.3, 15.4_

- [x] 14. 检查点 — 确保所有测试通过
  - 确保所有测试通过，如有疑问请询问用户。

- [x] 15. CLI 入口与端到端集成
  - [x] 15.1 实现 CLI 入口（`openclaw/main.py`）
    - 实现命令行参数解析：模式选择（Mode1/Mode2）、目标 URL/关键词、时间范围、最大视频数、输出格式、LLM 预设方案
    - Mode1 接受博主 URL；Mode2 接受关键词 + 平台列表 + max_creators + max_concurrency
    - 未提供可选参数时使用默认值
    - 支持"使用上次配置"快速启动
    - 执行前展示成本预估，用户确认后开始
    - _需求: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.3, 2.4, 3.4_

  - [x] 15.2 端到端流水线集成
    - 串联所有模块：配置加载 → 平台识别 → 视频列表获取 → 流水线调度 → 聚合 → 报告生成
    - 集成 LoggingMonitor 全链路日志
    - 集成 DataStore 全链路持久化
    - 集成 SourceAccessManager 全链路网络管理
    - 运行结束自动生成运行摘要
    - _需求: 1.1, 17.3, 19.5, 20.1, 20.2, 20.3, 20.4, 20.5, 20.6_

  - [x]* 15.3 编写端到端集成测试
    - 使用 mock 数据模拟完整 Mode1 流程（从配置到报告输出）
    - 使用 mock 数据模拟完整 Mode2 流程
    - 验证断点续传：模拟中断后恢复
    - _需求: 1.1, 1.2, 1.3, 17.1, 17.2, 18.6_

- [x] 16. 最终检查点 — 确保所有测试通过
  - 确保所有测试通过，如有疑问请询问用户。

## 备注

- 标记 `*` 的子任务为可选测试任务，可跳过以加速 MVP 开发
- 每个任务引用了具体的需求编号以确保可追溯性
- 检查点任务确保增量验证
- 属性测试验证通用正确性属性，单元测试验证具体示例和边界情况
- 需求 14（InsightMemory）为可选功能，已包含在任务 13.2 中
