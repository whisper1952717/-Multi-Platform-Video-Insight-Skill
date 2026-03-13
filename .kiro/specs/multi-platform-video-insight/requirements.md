# 需求文档

## 简介

Multi-Platform Video Insight Skill System（OpenClaw）是一个多平台视频洞察分析系统。系统抓取多平台视频（B站、抖音、YouTube、小红书等），提取行业信号、认知框架、方法论、商业机会线索，并生成可直接使用的洞察报告。系统支持两种分析模式：Mode1（单博主分析）深度提取单个博主的视频认知与商业洞察；Mode2（赛道/主题分析）横向分析多博主视频，提炼趋势、共识与商业机会。

## 术语表

- **System**：Multi-Platform Video Insight Skill System（OpenClaw），本系统的总称
- **ConfigManager**：统一配置管理模块，管理 API keys、Cookie、代理池配置、LLM 模型选择、平台参数等
- **PlatformAdapter**：平台适配器，自动识别视频来源平台并路由到对应抓取方法
- **VideoListFetcher**：视频列表获取模块，获取视频 URL、标题、作者、发布时间、播放量
- **AsyncPipelineManager**：异步并发调度器，管理视频处理流水线的并发执行
- **VideoDownloader**：视频下载模块，下载视频或音频文件
- **TranscriptGenerator**：转录生成模块，将视频/音频转录为文本
- **TranscriptCleaner**：转录清洗模块，清理口头禅、广告、重复段落
- **VideoSegmenter**：视频分段模块，对转录文本进行语义分段
- **TopicClassifier**：主题分类模块，对视频内容进行主题标签分类
- **VideoAnalyzer**：视频分析模块，对单视频进行深度商业洞察分析
- **InsightsAggregator**：洞察聚合模块，聚合多视频分析结果生成洞察报告
- **InsightMemory**：洞察记忆模块（可选），存储历史分析结果支持长期跟踪
- **ReportGenerator**：报告生成模块，输出最终结构化报告
- **SourceAccessManager**：网络访问管理中间件，统一控制请求频率、反爬策略、代理轮换、异常重试和降级处理
- **LoggingMonitor**：日志监控模块，记录结构化日志并监控运行状态
- **DataStore**：数据存储模块，负责中间数据持久化、缓存和断点续传
- **Mode1**：单博主分析模式，深度分析单个博主的视频内容
- **Mode2**：赛道/主题分析模式，横向分析多博主视频内容
- **confidence_score**：置信度评分，取值范围 0.0~1.0，衡量分析结果的质量
- **business_relevance**：商业相关度评分，取值范围 0.0~1.0，衡量视频内容与商业分析的相关程度
- **降级策略链**：当某步骤失败时按优先级依次尝试替代方案的策略

## 需求

### 需求 1：分析模式选择与任务配置

**用户故事：** 作为一名商业分析师，我希望能够选择单博主分析或赛道分析模式并配置分析参数，以便针对不同分析目标获取相应的洞察报告。

#### 验收标准

1. THE System SHALL 提供 Mode1（单博主分析）和 Mode2（赛道/主题分析）两种分析模式供用户选择
2. WHEN 用户选择 Mode1 时，THE System SHALL 接受一个博主 URL 作为分析目标
3. WHEN 用户选择 Mode2 时，THE System SHALL 接受一个主题关键词和一个平台列表作为分析目标
4. THE System SHALL 接受以下分析参数：时间范围（相对时间如 "last_30_days" 或绝对时间如 "2025-01-01 ~ 2025-03-01"）、每个博主最大分析视频数量（默认 20）、输出格式（Markdown / PDF / JSON）
5. WHEN 用户选择 Mode2 时，THE System SHALL 额外接受最大博主数量参数（默认 10）和异步并发数参数（默认 3）
6. WHEN 用户未提供可选参数时，THE System SHALL 使用预定义的默认值

### 需求 2：LLM 模型选择与成本预估

**用户故事：** 作为一名用户，我希望能够选择预设的 LLM 模型方案或自定义每个环节的模型，并在执行前看到预估成本，以便在分析质量和成本之间做出平衡。

#### 验收标准

1. THE System SHALL 提供至少四种预设模型方案：极致性价比（方案A）、质量优先（方案B）、旗舰全开（方案B+）、国内生态优先（方案C）
2. WHEN 用户选择预设方案时，THE System SHALL 自动配置 TopicClassifier、VideoAnalyzer、InsightsAggregator 三个环节的 LLM 模型
3. WHEN 用户选择自定义模式时，THE System SHALL 允许用户逐个环节选择 LLM 模型（TopicClassifier、VideoAnalyzer、InsightsAggregator）
4. WHEN 用户完成模型选择后，THE System SHALL 根据预估调用次数、单次预估 token 数和模型单价实时计算并展示预估成本
5. THE System SHALL 在成本预估中展示每个 LLM 环节的分项成本和总计预估成本
6. THE System SHALL 在成本预估中标注实际成本可能因视频长度和内容复杂度波动的幅度范围
7. WHEN 同时提供 llm_preset 和 llm_custom 参数时，THE System SHALL 以 llm_preset 为准（除非 llm_preset 值为 "custom"）

### 需求 3：模型配置持久化

**用户故事：** 作为一名频繁使用系统的用户，我希望系统能记住我的模型选择，以便下次运行时快速启动。

#### 验收标准

1. WHEN 用户完成模型配置后，THE ConfigManager SHALL 将模型选择持久化存储
2. WHEN 用户下次启动系统时，THE ConfigManager SHALL 自动加载上次使用的模型配置
3. THE ConfigManager SHALL 支持用户保存多套自定义模型方案并为每套方案命名
4. WHEN 用户选择"使用上次配置"时，THE System SHALL 跳过模型选择步骤直接进入执行

### 需求 4：统一配置管理

**用户故事：** 作为一名开发者，我希望通过统一的配置文件管理所有系统参数，以便方便地部署和维护系统。

#### 验收标准

1. THE ConfigManager SHALL 支持通过 YAML 配置文件管理所有配置项，包括 LLM provider 配置、平台配置、代理配置、存储配置和日志配置
2. THE ConfigManager SHALL 支持通过环境变量覆盖配置文件中的敏感信息（如 API keys）
3. THE ConfigManager SHALL 使用 pydantic-settings 实现类型安全的配置校验
4. WHEN 配置文件中存在无效配置项时，THE ConfigManager SHALL 返回明确的校验错误信息

### 需求 5：平台自动识别与适配

**用户故事：** 作为一名用户，我希望系统能自动识别视频来源平台并使用对应的抓取方法，以便我无需关心平台差异。

#### 验收标准

1. WHEN 用户提供博主 URL 时，THE PlatformAdapter SHALL 自动识别视频来源平台（B站、抖音、YouTube、小红书）
2. WHEN 平台被识别后，THE PlatformAdapter SHALL 路由到对应平台的抓取方法
3. THE PlatformAdapter SHALL 将不同平台的抓取结果统一为标准输出格式
4. IF 提供的 URL 无法匹配任何已支持的平台，THEN THE PlatformAdapter SHALL 返回明确的错误信息，指明不支持该平台

### 需求 6：视频列表获取

**用户故事：** 作为一名用户，我希望系统能根据我的配置获取目标博主的视频列表，以便后续进行批量分析。

#### 验收标准

1. WHEN 在 Mode1 下运行时，THE VideoListFetcher SHALL 根据博主 URL 获取该博主的视频列表，包含 URL、标题、作者、发布时间和播放量
2. WHEN 在 Mode2 下运行时，THE VideoListFetcher SHALL 根据主题关键词在指定平台列表中搜索相关博主和视频列表
3. THE VideoListFetcher SHALL 根据 time_window 参数过滤视频列表，仅保留指定时间范围内的视频
4. THE VideoListFetcher SHALL 根据 max_videos 参数限制每个博主返回的视频数量
5. WHEN 在 Mode2 下运行时，THE VideoListFetcher SHALL 根据 max_creators 参数限制返回的博主数量

### 需求 7：视频下载与降级策略

**用户故事：** 作为一名用户，我希望系统能可靠地下载视频内容，即使某些下载方式失败也能通过降级方案获取内容。

#### 验收标准

1. THE VideoDownloader SHALL 优先尝试获取视频的字幕文件
2. IF 字幕文件获取失败，THEN THE VideoDownloader SHALL 降级为下载音频文件
3. IF 音频文件下载也失败，THEN THE VideoDownloader SHALL 跳过该视频并记录跳过原因
4. THE VideoDownloader SHALL 使用 yt-dlp 作为核心下载引擎
5. WHEN 下载 B站视频时，THE VideoDownloader SHALL 优先获取 CC 字幕

### 需求 8：视频转录

**用户故事：** 作为一名用户，我希望系统能将视频内容转录为文本，以便后续进行文本分析。

#### 验收标准

1. WHEN 平台提供字幕文件时，THE TranscriptGenerator SHALL 优先使用平台字幕作为转录结果
2. WHEN 平台未提供字幕时，THE TranscriptGenerator SHALL 调用 Whisper 或 faster-whisper 将音频转录为文本
3. THE TranscriptGenerator SHALL 输出包含时间戳信息的转录文本

### 需求 9：转录文本清洗

**用户故事：** 作为一名用户，我希望系统能清理转录文本中的噪音内容，以便提高后续分析的准确性。

#### 验收标准

1. THE TranscriptCleaner SHALL 使用本地规则引擎（正则匹配 + 口头禅词库 + 广告关键词库）清理转录文本，不消耗 LLM token
2. THE TranscriptCleaner SHALL 清除口头禅、广告内容和重复段落
3. WHEN 本地规则引擎无法处理的清洗场景出现时，THE TranscriptCleaner SHALL 降级使用轻量 LLM 模型辅助清洗

### 需求 10：转录文本语义分段

**用户故事：** 作为一名用户，我希望系统能对转录文本进行语义分段，以便提高信息密度和分析精度。

#### 验收标准

1. THE VideoSegmenter SHALL 使用本地 semantic-text-splitter 库进行语义分段，不消耗 LLM token
2. THE VideoSegmenter SHALL 基于语义相似度进行分段，而非简单的固定长度分割
3. THE VideoSegmenter SHALL 输出分段后的文本片段列表

### 需求 11：主题分类（前置分类）

**用户故事：** 作为一名用户，我希望系统在深度分析前先对视频内容进行主题分类，以便后续分析可以根据主题类型调整策略并过滤无关内容。

#### 验收标准

1. THE TopicClassifier SHALL 在 VideoAnalyzer 之前执行，对每个视频的转录文本进行主题分类
2. THE TopicClassifier SHALL 输出主题标签（primary_topic）、次要主题列表（secondary_topics）、内容类型（content_type）和商业相关度评分（business_relevance）
3. THE TopicClassifier SHALL 将 content_type 限定为以下选项之一：观点输出、教程讲解、案例分析、行业分析、产品推荐、其他
4. WHEN business_relevance 评分低于 0.3 时，THE TopicClassifier SHALL 标记该视频为跳过状态并记录跳过原因，后续 VideoAnalyzer 不再处理该视频
5. THE TopicClassifier SHALL 使用轻量 LLM 模型（如 Doubao-1.5-Pro 或 Qwen-Turbo）执行分类任务

### 需求 12：单视频深度分析

**用户故事：** 作为一名商业分析师，我希望系统能从每个视频中提取核心信号、认知框架、方法论片段和高价值表达，以便获取深度商业洞察。

#### 验收标准

1. THE VideoAnalyzer SHALL 接收清洗和分段后的转录文本以及 TopicClassifier 的分类结果作为输入
2. THE VideoAnalyzer SHALL 提取以下维度的信息：核心信号（core_signals）、认知框架（cognition_framework）、方法论片段（methodology_fragments）和高价值表达（high_value_quotes）
3. THE VideoAnalyzer SHALL 为每个提取的信号、框架和方法论片段附带 confidence_score（0.0~1.0）质量评分
4. THE VideoAnalyzer SHALL 遵循以下 confidence_score 评分标准：0.9+ 表示多次明确提及且有具体数据或案例支撑；0.7~0.9 表示明确提及且有一定论据；0.5~0.7 表示隐含提及需要推断；低于 0.5 表示弱信号证据不足
5. THE VideoAnalyzer SHALL 为每个核心信号提供支撑该信号的原文片段作为证据
6. THE VideoAnalyzer SHALL 输出整体质量评分（overall_quality），当视频内容质量差或与商业分析无关时设为低分并说明原因
7. THE VideoAnalyzer SHALL 使用强 LLM 模型（如 DeepSeek-V3 或 GPT-4o 或 GPT-5.4）执行分析任务

### 需求 13：洞察聚合

**用户故事：** 作为一名商业分析师，我希望系统能将多个视频的分析结果聚合为结构化的洞察报告，以便快速获取高层商业洞察。

#### 验收标准

1. WHEN 在 Mode1 下运行时，THE InsightsAggregator SHALL 聚合同一博主的多视频分析结果，提炼核心信号、认知框架、方法论片段、商业机会和高价值表达
2. WHEN 在 Mode2 下运行时，THE InsightsAggregator SHALL 聚合多博主分析结果，提炼趋势信号、共识与分歧、通用方法论、商业机会和高价值表达
3. THE InsightsAggregator SHALL 对相似信号进行去重合并，confidence_score 取加权平均
4. THE InsightsAggregator SHALL 对多次出现的信号赋予更高权重
5. WHEN 某条分析结果的 overall_quality 低于 0.5 时，THE InsightsAggregator SHALL 对该结果进行降权处理
6. THE InsightsAggregator SHALL 仅保留有多个信号支撑的商业机会判断
7. THE InsightsAggregator SHALL 生成 3~5 条对用户最有价值的启发（insights_for_me）
8. WHEN 在 Mode2 下运行时，THE InsightsAggregator SHALL 识别并输出博主之间的共识点和分歧点，包括分歧双方的立场和比例


### 需求 14：洞察记忆与历史跟踪（可选）

**用户故事：** 作为一名长期跟踪行业趋势的分析师，我希望系统能存储历史分析结果，以便进行长期变化对比和趋势追踪。

#### 验收标准

1. WHERE InsightMemory 功能启用时，THE InsightMemory SHALL 存储每次运行的聚合洞察结果
2. WHERE InsightMemory 功能启用时，THE InsightMemory SHALL 支持基于向量检索的历史洞察查询
3. WHERE InsightMemory 功能启用时，THE InsightMemory SHALL 使用 ChromaDB 或 FAISS 作为向量存储引擎

### 需求 15：报告生成

**用户故事：** 作为一名用户，我希望系统能将分析结果输出为结构化的报告，以便直接使用或分享。

#### 验收标准

1. THE ReportGenerator SHALL 支持 Markdown、PDF 和 JSON 三种输出格式
2. THE ReportGenerator SHALL 根据用户指定的 output_format 参数生成对应格式的报告
3. WHEN 生成 Mode1 报告时，THE ReportGenerator SHALL 包含以下结构：元数据（博主信息、分析视频数、跳过视频数、时间范围、分析耗时）、核心信号、认知框架、方法论片段、商业机会（方向判断和可验证假设）、高价值表达、用户启发和质量摘要
4. WHEN 生成 Mode2 报告时，THE ReportGenerator SHALL 包含以下结构：元数据（主题、平台列表、分析博主数、分析视频总数、跳过视频数、时间范围、分析耗时）、趋势信号、共识与分歧、通用方法论、商业机会、高价值表达、用户启发和质量摘要
5. THE ReportGenerator SHALL 在报告的质量摘要中包含整体置信度评分、低质量信号数量和备注说明

### 需求 16：反爬与网络访问管理

**用户故事：** 作为一名用户，我希望系统能安全稳定地抓取各平台视频数据，避免被平台封禁。

#### 验收标准

1. THE SourceAccessManager SHALL 作为中间件贯穿所有涉及网络请求的模块（VideoListFetcher、VideoDownloader、TranscriptGenerator）
2. THE SourceAccessManager SHALL 在每次请求之间插入 1~8 秒的随机延时，延时范围可按平台单独配置
3. THE SourceAccessManager SHALL 将全局最大并发请求数限制为 2
4. THE SourceAccessManager SHALL 将单平台请求间隔限制为不低于 3 秒
5. THE SourceAccessManager SHALL 实现请求头伪装，包括 User-Agent 池轮换、Referer 和 Accept-Language 设置
6. THE SourceAccessManager SHALL 支持 Cookie 生命周期管理，包括手动导入、加密存储、过期前自动提醒和过期后降级为无登录模式
7. IF Cookie 失效，THEN THE SourceAccessManager SHALL 自动降级为无登录模式并记录日志和告警
8. THE SourceAccessManager SHALL 预留代理池接口（ProxyPoolInterface），支持 HTTP 和 SOCKS5 代理协议
9. WHEN 代理功能启用时，THE SourceAccessManager SHALL 按配置的请求数或遇到封禁时轮换代理 IP
10. WHEN 代理功能启用时，THE SourceAccessManager SHALL 定期验证代理可用性
11. WHEN 代理功能未启用或所有代理不可用时，THE SourceAccessManager SHALL 降级为直连模式
12. WHEN 收到 HTTP 403 或 429 响应时，THE SourceAccessManager SHALL 自动重试，最多 3 次，使用指数退避策略
13. WHEN 对某平台连续失败 5 次时，THE SourceAccessManager SHALL 暂停该平台请求 10 分钟
14. WHEN 单视频抓取失败时，THE SourceAccessManager SHALL 跳过该视频并记录失败信息，不中断整个流水线

### 需求 17：异步并发调度

**用户故事：** 作为一名用户，我希望系统能高效地并行处理多个博主的视频分析任务，以便缩短 Mode2 赛道分析的总耗时。

#### 验收标准

1. WHEN 在 Mode1 下运行时，THE AsyncPipelineManager SHALL 串行或低并发处理单博主的视频列表
2. WHEN 在 Mode2 下运行时，THE AsyncPipelineManager SHALL 并行处理多个博主的视频分析任务，并发数由 max_concurrency 参数控制（默认 3）
3. THE AsyncPipelineManager SHALL 使用 Python asyncio + aiohttp 实现异步并发调度
4. THE AsyncPipelineManager SHALL 确保每个博主内部的视频按串行顺序处理

### 需求 18：数据存储与缓存

**用户故事：** 作为一名用户，我希望系统能缓存已分析的视频数据并支持断点续传，以便避免重复分析和应对中断。

#### 验收标准

1. THE DataStore SHALL 持久化存储视频列表、转录文本、分析结果和聚合洞察
2. THE DataStore SHALL 支持 SQLite 和 PostgreSQL 两种数据库后端
3. WHEN cache_enabled 为 true 时，THE DataStore SHALL 在 cache_ttl 有效期内对同一视频 URL 不重复下载和分析
4. THE DataStore SHALL 通过对比 publish_date 和 view_count 变化检测视频内容是否更新
5. THE DataStore SHALL 记录每个视频的处理状态（pending / downloaded / transcribed / analyzed / skipped）
6. WHEN 系统中断后重新启动时，THE DataStore SHALL 从上次中断处继续处理未完成的视频（断点续传）

### 需求 19：结构化日志与运行监控

**用户故事：** 作为一名运维人员，我希望系统能记录详细的结构化日志并监控运行状态，以便排查问题和优化性能。

#### 验收标准

1. THE LoggingMonitor SHALL 使用 structlog + Rich 记录结构化日志，包含时间戳、日志级别、模块名、事件名、相关 URL、耗时和 run_id
2. THE LoggingMonitor SHALL 记录每个步骤的耗时和成功/失败状态
3. THE LoggingMonitor SHALL 监控各平台的抓取成功率
4. THE LoggingMonitor SHALL 记录每次 LLM API 调用的 token 消耗数量和费用
5. WHEN 运行结束时，THE LoggingMonitor SHALL 自动生成运行摘要，包含总视频数、成功数、跳过数、失败数和各模块平均耗时
6. THE LoggingMonitor SHALL 支持同时输出到控制台和日志文件

### 需求 20：错误处理与降级策略

**用户故事：** 作为一名用户，我希望系统在遇到错误时能自动降级处理而非中断整个流水线，以便最大化获取可用的分析结果。

#### 验收标准

1. WHEN 网络请求失败时，THE System SHALL 通过 SourceAccessManager 进行最多 3 次指数退避重试
2. WHEN 视频转录失败时，THE System SHALL 跳过该视频并记录 skipped_reason
3. WHEN VideoAnalyzer 分析失败时，THE System SHALL 降级为简单摘要模式
4. WHEN 对某平台连续失败时，THE System SHALL 暂停该平台并切换到下一个平台继续处理
5. WHEN 任意步骤失败时，THE DataStore SHALL 保存当前检查点以支持断点续传
6. THE System SHALL 在降级策略链中按以下优先级尝试：字幕获取 → 音频下载 → 跳过并记录

### 需求 21：输出数据结构与质量评分

**用户故事：** 作为一名用户，我希望所有分析结果都包含质量评分，以便快速识别高价值洞察并过滤低质量内容。

#### 验收标准

1. THE System SHALL 以统一的 JSON 结构输出所有分析结果
2. THE System SHALL 为所有核心信号、认知框架、方法论片段和商业机会附带 confidence_score（0.0~1.0）
3. WHEN 生成 Mode1 输出时，THE System SHALL 包含 metadata、core_signals、cognition_framework、methodology_fragments、business_opportunities、high_value_quotes、insights_for_me 和 quality_summary 字段
4. WHEN 生成 Mode2 输出时，THE System SHALL 包含 metadata、trend_signals、consensus_and_divergence、common_methodology、business_opportunities、high_value_quotes、insights_for_me 和 quality_summary 字段
5. THE System SHALL 在 quality_summary 中包含 overall_confidence 整体置信度、low_quality_signals_count 低质量信号数量和 notes 备注说明
6. THE System SHALL 在 Mode1 的 metadata 中包含 creator、platform、videos_analyzed、videos_skipped、time_range 和 analysis_duration_seconds
7. THE System SHALL 在 Mode2 的 metadata 中包含 topic、platforms、creators_analyzed、total_videos_analyzed、total_videos_skipped、time_range 和 analysis_duration_seconds

### 需求 22：Prompt 框架与 LLM 交互规范

**用户故事：** 作为一名开发者，我希望系统的 LLM 交互使用严格的 Prompt 框架和 JSON Schema 约束输出，以便确保分析结果的结构化和一致性。

#### 验收标准

1. THE TopicClassifier SHALL 使用严格 JSON Schema 约束 LLM 输出格式，包含 primary_topic、secondary_topics、content_type、business_relevance 和 skip_reason 字段
2. THE VideoAnalyzer SHALL 使用严格 JSON Schema 约束 LLM 输出格式，包含 core_signals、cognition_framework、methodology_fragments、high_value_quotes 和 overall_quality 字段
3. THE InsightsAggregator SHALL 根据运行模式（Mode1 或 Mode2）使用对应的严格 JSON Schema 约束 LLM 输出格式
4. THE VideoAnalyzer SHALL 在 Prompt 中包含 Few-shot 示例以提高输出质量和一致性
5. THE System SHALL 通过严格约束输出 JSON Schema 减少 LLM 输出冗余 token

### 需求 23：平台特殊策略

**用户故事：** 作为一名用户，我希望系统能针对不同平台的特性采用对应的抓取策略，以便最大化抓取成功率。

#### 验收标准

1. WHEN 抓取 B站视频时，THE System SHALL 使用 Cookie 登录并优先获取 CC 字幕
2. WHEN 抓取抖音视频时，THE System SHALL 使用 Cookie 登录并处理特殊签名机制
3. WHEN 抓取 YouTube 视频时，THE System SHALL 使用 yt-dlp 原生支持并优先获取自动字幕
4. WHEN 抓取小红书视频时，THE System SHALL 使用 Cookie 登录并建议配合代理使用
5. THE System SHALL 为每个平台单独配置 Cookie 路径、Cookie 刷新周期和请求延时范围

### 需求 24：分层模型策略与成本优化

**用户故事：** 作为一名用户，我希望系统能通过分层模型策略和多种优化手段控制 LLM 使用成本，以便在可接受的成本范围内获取高质量分析。

#### 验收标准

1. THE System SHALL 对 TranscriptCleaner 和 VideoSegmenter 使用本地方案处理，不消耗 LLM token
2. THE System SHALL 对 TopicClassifier 使用轻量 LLM 模型，对 VideoAnalyzer 和 InsightsAggregator 使用强 LLM 模型
3. THE System SHALL 通过 TopicClassifier 前置过滤（business_relevance < 0.3）减少 VideoAnalyzer 的调用次数
4. THE System SHALL 通过 DataStore 缓存避免对同一视频的重复分析
5. WHEN 使用 DeepSeek-V3 模型时，THE System SHALL 利用其输入缓存机制降低重复 system prompt 的输入成本
6. THE System SHALL 通过严格 JSON Schema 约束 LLM 输出格式以减少输出 token 消耗
