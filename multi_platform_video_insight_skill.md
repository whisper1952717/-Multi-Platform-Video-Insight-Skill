# Multi-Platform Video Insight Skill System — OpenClaw

## 1. Overview
**系统名称**：Multi-Platform Video Insight Skill System  
**功能**：抓取多平台视频（B站、抖音、YouTube、小红书等），提取行业信号、认知框架、方法论、商业机会线索，并生成可直接使用的洞察报告。  
**模式**：
- **Mode1（单博主分析）**：深度提取单个博主的视频认知与商业洞察。  
- **Mode2（赛道/主题分析）**：横向分析多博主视频，提炼趋势、共识与商业机会。

---

## 2. Architecture

```
                    ┌─────────────────┐
                    │  ConfigManager   │  ← 统一配置管理（API keys, Cookie, 代理, LLM模型）
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ PlatformAdapter  │  ← 自动识别平台，路由到对应抓取方法
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ VideoListFetcher │  ← 获取视频列表（支持 max_videos 限制）
                    └────────┬────────┘
                             │
              ┌──────────────▼──────────────┐
              │    AsyncPipelineManager      │  ← 异步并发调度（Mode2 多博主并行）
              │  ┌────────────────────────┐  │
              │  │   VideoDownloader      │  │  ← 下载视频/音频，字幕优先
              │  └───────────┬────────────┘  │
              │  ┌───────────▼────────────┐  │
              │  │  TranscriptGenerator   │  │  ← 视频/音频转录为文本
              │  └───────────┬────────────┘  │
              │  ┌───────────▼────────────┐  │
              │  │   TranscriptCleaner    │  │  ← 清理口头禅、广告、重复段落
              │  └───────────┬────────────┘  │
              │  ┌───────────▼────────────┐  │
              │  │    VideoSegmenter      │  │  ← 语义分段，提高信息密度
              │  └───────────┬────────────┘  │
              │  ┌───────────▼────────────┐  │
              │  │    TopicClassifier     │  │  ← 主题粗分类（前置，指导分析）
              │  └───────────┬────────────┘  │
              │  ┌───────────▼────────────┐  │
              │  │    VideoAnalyzer       │  │  ← 单视频深度分析（含置信度评分）
              │  └────────────────────────┘  │
              └──────────────┬──────────────┘
                             │
                    ┌────────▼────────┐
                    │ InsightsAggregator│  ← 聚合分析结果，生成洞察报告
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  InsightMemory   │  ← 历史存储，长期跟踪（Optional）
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ ReportGenerator  │  ← 输出最终报告
                    └─────────────────┘

横切关注点（贯穿所有网络请求模块）：
┌─────────────────────────────────────────┐
│         SourceAccessManager             │
│  - 请求频率控制（随机延时 1~8s）          │
│  - 反爬策略（请求头伪装、Cookie管理）      │
│  - 代理IP池管理                          │
│  - 异常重试（HTTP 403/429）              │
│  - 降级策略（跳过失败视频，记录日志）      │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│         LoggingMonitor                  │
│  - 结构化日志（每步骤耗时、成功/失败）     │
│  - 抓取成功率监控                        │
│  - 异常告警                              │
│  - 运行报告生成                          │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│         DataStore                       │
│  - 中间数据持久化（视频列表、转录文本）    │
│  - 分析结果缓存（避免重复分析）           │
│  - 断点续传支持                          │
└─────────────────────────────────────────┘
```

### Module Descriptions

#### 核心流水线模块
- **ConfigManager**：统一管理所有配置项，包括 API keys、Cookie、代理池配置、LLM 模型选择、平台参数等。支持环境变量和配置文件两种方式。
- **PlatformAdapter**：自动识别视频来源平台，调用对应抓取方法，统一输出格式。
- **VideoListFetcher**：获取视频列表，包括 URL、标题、作者、发布时间、播放量。支持 `max_videos` 限制。
- **AsyncPipelineManager**：异步并发调度器。Mode1 串行处理单博主视频；Mode2 并行处理多博主，控制并发数（默认 max_concurrency=3）。
- **VideoDownloader**：下载视频或音频文件，字幕优先策略。失败时降级为音频下载。
- **TranscriptGenerator**：将视频/音频转录为文本。优先使用平台字幕，无字幕时调用 Whisper 转录。
- **TranscriptCleaner**：清理转录文本。使用规则匹配（口头禅词库、广告关键词）+ LLM 辅助清洗，轻量高效。
- **VideoSegmenter**：语义分段。使用 LLM 或 semantic-text-splitter 进行语义切分，而非简单的固定长度分割。
- **TopicClassifier**：主题粗分类（前置于 VideoAnalyzer）。先对视频内容做主题标签，让后续分析可以根据主题类型调整分析策略。
- **VideoAnalyzer**：单视频深度分析，提取核心信号、认知框架、方法论片段和高价值表达。输出包含 `confidence_score` 质量评分。
- **InsightsAggregator**：聚合多视频分析结果，生成洞察报告（Mode1: 单博主，Mode2: 赛道趋势）。
- **InsightMemory (Optional)**：存储历史分析结果，支持长期跟踪和变化对比。
- **ReportGenerator**：输出最终报告（Markdown/PDF/JSON），结构化展示分析结果。

#### 横切关注点模块
- **SourceAccessManager**：作为中间件贯穿所有网络请求模块（VideoListFetcher、VideoDownloader 等），统一控制请求频率、反爬策略、代理IP轮换、异常重试和降级处理。
- **LoggingMonitor**：结构化日志记录，监控每个步骤的耗时、成功率、异常情况。支持运行报告生成。
- **DataStore**：中间数据持久化层，存储视频列表、转录文本、分析结果。支持缓存（避免重复分析同一视频）和断点续传。

---

## 3. 用户交互界面 — 模型选择与任务配置

### 3.1 交互流程

用户启动 Skill 时，系统通过对话式交互收集配置，流程如下：

```
用户触发 Skill
  → Step 1: 选择分析模式（Mode1 / Mode2）
  → Step 2: 输入分析目标（博主URL / 关键词）
  → Step 3: 配置分析参数（时间范围、视频数量等）
  → Step 4: 选择模型方案（预设方案 或 自定义模型）
  → Step 5: 确认配置 & 预估成本
  → 开始执行
```

### 3.2 模型选择界面设计

#### 方式一：预设方案快速选择

用户可以从预设方案中一键选择，系统自动配置各环节模型：

```
┌─────────────────────────────────────────────────────────┐
│  🤖 选择分析质量方案                                      │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 💰 方案A：极致性价比（推荐日常使用）               │    │
│  │    TopicClassifier: Doubao-1.5-Pro               │    │
│  │    VideoAnalyzer:   DeepSeek-V3                  │    │
│  │    Aggregator:      DeepSeek-V3                  │    │
│  │    预估成本：Mode1 ~¥0.35 / Mode2 ~¥2.5          │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ ⚖️ 方案B：质量优先                                │    │
│  │    TopicClassifier: GPT-4o-mini                  │    │
│  │    VideoAnalyzer:   GPT-4o                       │    │
│  │    Aggregator:      GPT-5.4                      │    │
│  │    预估成本：Mode1 ~¥3.0 / Mode2 ~¥20            │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 🚀 方案B+：旗舰全开（重要分析推荐）               │    │
│  │    TopicClassifier: GPT-4o-mini                  │    │
│  │    VideoAnalyzer:   GPT-5.4                      │    │
│  │    Aggregator:      GPT-5.4                      │    │
│  │    预估成本：Mode1 ~¥4.4 / Mode2 ~¥31            │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 🇨🇳 方案C：国内生态优先                           │    │
│  │    TopicClassifier: Qwen-Turbo                   │    │
│  │    VideoAnalyzer:   Qwen-Plus                    │    │
│  │    Aggregator:      Qwen-Max                     │    │
│  │    预估成本：Mode1 ~¥0.20 / Mode2 ~¥1.1          │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ ⚙️ 自定义：手动选择每个环节的模型                  │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### 方式二：自定义模型选择

用户选择"自定义"后，可以逐个环节选择模型：

```
┌─────────────────────────────────────────────────────────┐
│  ⚙️ 自定义模型配置                                       │
│                                                         │
│  TopicClassifier（主题分类，每视频调用1次）：              │
│  ┌─────────────────────────────────────────────────┐    │
│  │ ○ Doubao-1.5-Pro    ¥0.8/百万输入  [推荐]       │    │
│  │ ○ Qwen-Turbo        ¥0.3/百万输入               │    │
│  │ ○ GPT-4o-mini       $0.15/百万输入              │    │
│  │ ○ DeepSeek-V3       $0.27/百万输入              │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  VideoAnalyzer（核心分析，每视频调用1次）：                │
│  ┌─────────────────────────────────────────────────┐    │
│  │ ○ DeepSeek-V3       $0.27/$1.10    [性价比推荐]  │    │
│  │ ○ Qwen-Plus         ¥2/¥8                       │    │
│  │ ○ GPT-4o            $2.50/$10.00                │    │
│  │ ○ GPT-5.4           $2.50/$15.00   [质量推荐]    │    │
│  │ ○ DeepSeek-R1       $0.55/$2.19                 │    │
│  │ ○ Qwen-Max          ¥8/¥24                      │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  InsightsAggregator（聚合报告，每次运行调用1次）：         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ ○ GPT-5.4           $2.50/$15.00   [质量推荐]    │    │
│  │ ○ DeepSeek-V3       $0.27/$1.10    [性价比推荐]  │    │
│  │ ○ GPT-4o            $2.50/$10.00                │    │
│  │ ○ Qwen-Max          ¥8/¥24                      │    │
│  │ ○ DeepSeek-R1       $0.55/$2.19                 │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ────────────────────────────────────────────────────   │
│  📊 预估成本：根据您的选择实时计算...                     │
│     TopicClassifier: 20次 × ~500 token = ~¥0.01        │
│     VideoAnalyzer:   20次 × ~3k token = ~$0.04         │
│     Aggregator:      1次  × ~5k token = ~$0.06         │
│     总计预估：~$0.11 (~¥0.80)                           │
│  ────────────────────────────────────────────────────   │
│                                                         │
│  [确认配置并开始分析]                                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 3.3 实时成本预估

在用户选择模型后、确认执行前，系统根据以下因素实时计算预估成本：

```
预估成本 = Σ (每个LLM环节的预估调用次数 × 单次预估token × 模型单价)

其中：
- TopicClassifier 调用次数 = max_videos × (Mode2 ? max_creators : 1)
- VideoAnalyzer 调用次数 = TopicClassifier 调用次数 × (1 - 预估过滤率20%)
- InsightsAggregator 调用次数 = 1
- 单次预估 token 基于历史平均值（首次运行使用默认估算值）
```

展示格式：
```
📊 本次运行预估成本：
   ├─ TopicClassifier (Doubao-1.5-Pro × 20次):  ~¥0.02
   ├─ VideoAnalyzer   (DeepSeek-V3 × 16次):     ~$0.03
   ├─ Aggregator      (DeepSeek-V3 × 1次):      ~$0.005
   ├─ OpenClaw 平台层:                           ~视平台计费
   └─ 总计预估: ~¥0.30 (不含平台层)
   
   ⚠️ 实际成本可能因视频长度和内容复杂度波动 ±30%
```

### 3.4 模型配置持久化

- 用户的模型选择保存在 ConfigManager 中，下次运行自动加载上次配置
- 支持保存多套自定义方案（如"日常方案"、"深度分析方案"）
- 用户可以在运行前选择"使用上次配置"快速启动

### 3.5 OpenClaw Skill 参数扩展

为支持用户模型选择，Skill 输入参数新增：

```json
{
  "mode": "single",
  "target": "https://space.bilibili.com/123456",
  "time_window": "last_30_days",
  "max_videos": 20,
  "output_format": "Markdown",
  
  "llm_preset": "cost_effective",
  
  "llm_custom": {
    "topic_classifier": {
      "provider": "volcengine",
      "model": "doubao-1.5-pro-32k"
    },
    "video_analyzer": {
      "provider": "deepseek",
      "model": "deepseek-v3"
    },
    "insights_aggregator": {
      "provider": "openai",
      "model": "gpt-5.4"
    }
  }
}
```

参数说明：
- `llm_preset`：预设方案快捷键，可选值：
  - `"cost_effective"` — 方案A（极致性价比）
  - `"quality"` — 方案B（质量优先）
  - `"flagship"` — 方案B+（旗舰全开）
  - `"china_eco"` — 方案C（国内生态）
  - `"custom"` — 使用 llm_custom 自定义配置
- `llm_custom`：自定义模型配置，仅当 `llm_preset = "custom"` 时生效
- 如果同时提供 `llm_preset` 和 `llm_custom`，以 `llm_preset` 为准（除非值为 `"custom"`）

---

## 4. Input/Output Specification

### Skill Inputs
- `mode`: "single" (Mode1) 或 "multi" (Mode2)
- `target`: Mode1：博主 URL；Mode2：主题关键词
- `platforms`: 指定搜索平台列表，例如 ["bilibili", "douyin", "youtube"]（Mode2 必填，Mode1 自动识别）
- `time_window`: 分析时间范围，支持两种格式：
  - 相对时间：`"last_30_days"`, `"last_7_days"`, `"last_90_days"`
  - 绝对时间：`"2025-01-01 ~ 2025-03-01"`
- `max_videos`: 每个博主最大分析视频数量（默认 20，防止成本和时间失控）
- `max_creators`: Mode2 最大博主数量（默认 10）
- `output_format`: Markdown / PDF / JSON

### Skill Outputs
统一输出 JSON 结构，所有分析结果包含 `confidence_score`（0.0~1.0）质量评分。

#### Mode1 — 单博主分析
```json
{
  "metadata": {
    "creator": "博主名称",
    "platform": "bilibili",
    "videos_analyzed": 15,
    "videos_skipped": 2,
    "time_range": "2025-01-01 ~ 2025-03-01",
    "analysis_duration_seconds": 320
  },
  "core_signals": [
    {"signal": "多次提到GEO优化", "confidence_score": 0.92, "source_videos": [1, 3, 7]},
    {"signal": "企业AI落地服务需求显性化", "confidence_score": 0.85, "source_videos": [2, 5]}
  ],
  "cognition_framework": [
    {"framework": "趋势判断 → 内容教育 → 建立信任 → 企业服务", "confidence_score": 0.88}
  ],
  "methodology_fragments": [
    {"method": "问题→案例→方法→机会", "confidence_score": 0.90}
  ],
  "business_opportunities": {
    "direction_judgment": [
      {"judgment": "AI可见度正在成为新的流量入口", "confidence_score": 0.87}
    ],
    "verifiable_hypotheses": [
      {"hypothesis": "中小企业缺少AI整体流程设计能力", "confidence_score": 0.82}
    ]
  },
  "high_value_quotes": [
    {"quote": "未来的SEO不是搜索优化，而是AI回答优化。", "source_video": 3, "timestamp": "05:32"}
  ],
  "insights_for_me": ["内容表达应围绕问题解决而非工具介绍"],
  "quality_summary": {
    "overall_confidence": 0.87,
    "low_quality_signals_count": 1,
    "notes": "2个视频因转录质量差被跳过"
  }
}
```

#### Mode2 — 赛道分析
```json
{
  "metadata": {
    "topic": "AI咨询",
    "platforms": ["bilibili", "douyin"],
    "creators_analyzed": 8,
    "total_videos_analyzed": 45,
    "total_videos_skipped": 5,
    "time_range": "last_30_days",
    "analysis_duration_seconds": 1200
  },
  "trend_signals": [
    {"signal": "AI咨询相关概念升温", "confidence_score": 0.91, "mentioned_by_creators": 6},
    {"signal": "企业AI落地服务需求增加", "confidence_score": 0.88, "mentioned_by_creators": 5}
  ],
  "consensus_and_divergence": {
    "consensus": [
      {"point": "AI营销替代传统SEO", "confidence_score": 0.90, "supporters": 7}
    ],
    "divergence": [
      {"point": "工具教学 vs 落地服务", "side_a": "工具教学", "side_b": "落地服务", "ratio": "3:5"}
    ]
  },
  "common_methodology": [
    {"method": "趋势判断 → 内容教育 → 企业服务", "confidence_score": 0.85}
  ],
  "business_opportunities": {
    "direction_judgment": [
      {"judgment": "中小企业AI落地服务是赛道重点", "confidence_score": 0.89}
    ],
    "verifiable_hypotheses": [
      {"hypothesis": "企业关注AI自动化流程，但缺整体设计能力", "confidence_score": 0.83}
    ]
  },
  "high_value_quotes": [
    {"quote": "企业不会买AI课程，他们只会买AI结果。", "creator": "博主A", "platform": "bilibili"}
  ],
  "insights_for_me": ["AI服务可能比工具教学更有长期价值"],
  "quality_summary": {
    "overall_confidence": 0.87,
    "low_quality_signals_count": 3,
    "notes": "5个视频因转录质量差或内容无关被跳过"
  }
}
```

---

## 5. Prompt Framework

### TopicClassifier Prompt（前置分类）
```
你是一个内容分类专家。

## 输入
单条视频转录文本（已清洗）

## 任务
对视频内容进行主题分类，输出主题标签和内容类型。

## 输出格式（严格JSON）
{
  "primary_topic": "主题标签（如：AI营销、企业服务、技术教程）",
  "secondary_topics": ["次要主题1", "次要主题2"],
  "content_type": "观点输出 | 教程讲解 | 案例分析 | 行业分析 | 产品推荐 | 其他",
  "business_relevance": 0.0~1.0,
  "skip_reason": null 或 "内容与商业分析无关的原因"
}

## 规则
- business_relevance < 0.3 时，设置 skip_reason，后续分析将跳过该视频
- 主题标签应简洁，不超过6个字
- content_type 必须从给定选项中选择
```

### VideoAnalyzer Prompt
```
你是一个资深商业研究分析师，擅长从视频内容中提取商业洞察。

## 输入
- 视频转录文本（已清洗和分段）
- 主题分类结果：{topic_classification}

## 任务
从视频内容中提取以下维度的信息：

## 输出格式（严格JSON Schema）
{
  "core_signals": [
    {
      "signal": "信号描述（一句话）",
      "evidence": "支撑该信号的原文片段",
      "confidence_score": 0.0~1.0
    }
  ],
  "cognition_framework": [
    {
      "framework": "认知框架描述",
      "reasoning_chain": "推理链条说明",
      "confidence_score": 0.0~1.0
    }
  ],
  "methodology_fragments": [
    {
      "method": "方法论描述",
      "applicable_scenario": "适用场景",
      "confidence_score": 0.0~1.0
    }
  ],
  "high_value_quotes": [
    {
      "quote": "原话",
      "context": "上下文说明"
    }
  ],
  "overall_quality": 0.0~1.0
}

## 分析规则
1. 核心信号：只提取有明确证据支撑的信号，不做过度推断
2. confidence_score 评分标准：
   - 0.9+：多次明确提及，有具体数据或案例支撑
   - 0.7~0.9：明确提及，有一定论据
   - 0.5~0.7：隐含提及，需要推断
   - <0.5：弱信号，证据不足
3. 如果视频内容质量差或与商业分析无关，overall_quality 设为低分并说明原因
4. 高价值表达只保留真正有洞察力的原话，不要凑数

## Few-shot 示例
输入："...现在做SEO已经没用了，未来的流量入口是AI搜索。我们公司已经帮30多家企业做了GEO优化，效果比传统SEO好3倍..."
输出：
{
  "core_signals": [
    {
      "signal": "GEO优化正在替代传统SEO",
      "evidence": "帮30多家企业做了GEO优化，效果比传统SEO好3倍",
      "confidence_score": 0.88
    }
  ],
  "cognition_framework": [
    {
      "framework": "流量入口迁移判断：传统搜索 → AI搜索",
      "reasoning_chain": "SEO失效 → AI搜索崛起 → GEO成为新优化方向",
      "confidence_score": 0.85
    }
  ],
  "methodology_fragments": [],
  "high_value_quotes": [
    {
      "quote": "未来的流量入口是AI搜索",
      "context": "讨论SEO失效趋势时的判断"
    }
  ],
  "overall_quality": 0.85
}
```

### InsightsAggregator Prompt
```
你是内容洞察聚合系统，擅长从多条分析结果中提炼高层洞察。

## 输入
多条 VideoAnalyzer 输出结果（JSON数组）

## 模式
- Mode1（单博主）：聚合同一博主的多视频分析，提炼其核心认知体系
- Mode2（赛道分析）：聚合多博主分析，提炼行业趋势和共识/分歧

## 输出格式（严格JSON Schema）
### Mode1 输出
{
  "core_signals": [{"signal": "", "confidence_score": 0.0, "frequency": 0}],
  "cognition_framework": [{"framework": "", "confidence_score": 0.0}],
  "methodology_fragments": [{"method": "", "confidence_score": 0.0}],
  "business_opportunities": {
    "direction_judgment": [{"judgment": "", "confidence_score": 0.0}],
    "verifiable_hypotheses": [{"hypothesis": "", "confidence_score": 0.0}]
  },
  "high_value_quotes": [{"quote": "", "source_video": 0}],
  "insights_for_me": [""]
}

### Mode2 输出
{
  "trend_signals": [{"signal": "", "confidence_score": 0.0, "mentioned_by_creators": 0}],
  "consensus_and_divergence": {
    "consensus": [{"point": "", "confidence_score": 0.0, "supporters": 0}],
    "divergence": [{"point": "", "side_a": "", "side_b": "", "ratio": ""}]
  },
  "common_methodology": [{"method": "", "confidence_score": 0.0}],
  "business_opportunities": {
    "direction_judgment": [{"judgment": "", "confidence_score": 0.0}],
    "verifiable_hypotheses": [{"hypothesis": "", "confidence_score": 0.0}]
  },
  "high_value_quotes": [{"quote": "", "creator": "", "platform": ""}],
  "insights_for_me": [""]
}

## 聚合规则
1. 信号去重：相似信号合并，confidence_score 取加权平均
2. 频率加权：多次出现的信号权重更高
3. 过滤低质量：overall_quality < 0.5 的分析结果降权处理
4. 商业机会：只保留有多个信号支撑的机会判断
5. insights_for_me：基于所有分析结果，给出对用户最有价值的3~5条启发
```

---

## 6. Anti-Crawler Access Strategy

### SourceAccessManager（中间件模式）

SourceAccessManager 作为横切关注点，贯穿所有涉及网络请求的模块（VideoListFetcher、VideoDownloader、TranscriptGenerator）。

#### 请求控制
- 随机延时 1~8 秒（可按平台配置不同延时范围）
- 最大并发请求数 2（全局）
- 单平台请求间隔不低于 3 秒

#### 身份伪装
- 请求头伪装：User-Agent 池轮换、Referer、Accept-Language
- Cookie 生命周期管理：
  - 获取：支持手动导入（浏览器导出）和自动刷新
  - 存储：加密存储在本地配置文件中
  - 刷新：Cookie 过期前自动提醒，支持配置刷新策略
  - 过期处理：Cookie 失效时自动降级为无登录模式，记录日志并告警

#### 代理IP管理
- 预留代理池接口（ProxyPoolInterface）
- 支持 HTTP/SOCKS5 代理
- 代理轮换策略：每 N 个请求或遇到封禁时切换
- 代理健康检查：定期验证代理可用性
- 无代理时降级为直连模式

#### 异常处理与降级
- HTTP 403/429 自动重试（最多 3 次，指数退避）
- 连续失败 5 次后暂停该平台请求 10 分钟
- 单视频抓取失败时跳过并记录，不中断整个流水线
- 降级策略链：字幕获取 → 音频下载 → 跳过并记录

#### 平台特殊策略
- B站：Cookie 登录，优先获取 CC 字幕
- 抖音：Cookie 登录，需要特殊签名处理
- YouTube：yt-dlp 原生支持，优先自动字幕
- 小红书：Cookie 登录，反爬较严，建议配合代理

---

## 7. Open Source Components

| 层级 | 项目 | 用途 | 备注 |
|------|------|------|------|
| 视频抓取 | **yt-dlp** | 视频下载 + 平台解析 | 核心依赖，支持多平台 |
| 视频转录 | **OpenAI Whisper** / **faster-whisper** | 音频转文本 | 无字幕时的降级方案 |
| B站专用 | **bilibili-api-python** | B站 API 调用 | 替代 Bili2Text，更活跃 |
| 文本清洗 | **规则引擎（本地）** | 口头禅/广告清理 | 正则 + 词库，不消耗 LLM token |
| 语义分段 | **semantic-text-splitter（本地）** | 转录文本语义分段 | 本地方案，不消耗 LLM token |
| 主题分类 | **Doubao-1.5-Pro / Qwen-Turbo** | TopicClassifier | 轻量模型，成本极低 |
| 异步调度 | **asyncio + aiohttp** | 并发请求管理 | Python 原生异步 |
| 数据存储 | **SQLite / PostgreSQL** | 中间数据持久化 | 视频列表、转录文本、分析结果 |
| 向量存储 | **ChromaDB / FAISS** | InsightMemory 向量检索 | 长期洞察存储 |
| 日志监控 | **structlog + Rich** | 结构化日志 + 终端美化 | 轻量级监控方案 |
| 配置管理 | **pydantic-settings** | 类型安全的配置管理 | 支持环境变量和配置文件 |
| 核心分析 LLM | **DeepSeek-V3 / Qwen-Plus / GPT-4o** | VideoAnalyzer / InsightsAggregator | 按需选择，支持多 provider |

---

## 8. Parameter Design

| 参数 | 描述 | 默认值 | 适用模式 |
|------|------|--------|----------|
| mode | "single" 或 "multi" | 必填 | 全部 |
| target | Mode1: 博主 URL；Mode2: 主题关键词 | 必填 | 全部 |
| platforms | 搜索平台列表 | ["bilibili"] | Mode2 必填，Mode1 自动识别 |
| time_window | 分析时间范围（相对或绝对） | "last_30_days" | 全部 |
| max_videos | 每个博主最大分析视频数 | 20 | 全部 |
| max_creators | Mode2 最大博主数量 | 10 | Mode2 |
| max_concurrency | 异步并发数 | 3 | Mode2 |
| output_format | Markdown / PDF / JSON | "Markdown" | ReportGenerator |
| llm_model | LLM 模型配置（支持按环节分别配置） | 见 config.yaml | VideoAnalyzer / InsightsAggregator / TopicClassifier |
| proxy_enabled | 是否启用代理 | false | SourceAccessManager |
| cache_enabled | 是否启用缓存（避免重复分析） | true | DataStore |

---

## 9. Running Logic

### Mode1 — 单博主分析
```
输入：
  mode = "single"
  target = "https://space.bilibili.com/123456"
  time_window = "last_30_days"
  max_videos = 20
  output_format = "Markdown"

流程：
  ConfigManager.load()
  → PlatformAdapter.detect(target) → platform="bilibili"
  → VideoListFetcher.fetch(target, time_window, max_videos)
      ← SourceAccessManager 控制请求
      ← DataStore 缓存视频列表
  → AsyncPipelineManager.process_videos(video_list):
      对每个视频（串行或低并发）：
        → VideoDownloader.download(video)
            ← 降级链：字幕 → 音频 → 跳过
        → TranscriptGenerator.transcribe(media)
        → TranscriptCleaner.clean(transcript)
        → VideoSegmenter.segment(cleaned_text)
        → TopicClassifier.classify(segments)
            ← business_relevance < 0.3 → 跳过
        → VideoAnalyzer.analyze(segments, topic_classification)
        → DataStore.save(analysis_result)
      ← LoggingMonitor 记录每步状态
  → InsightsAggregator.aggregate(all_results, mode="single")
  → InsightMemory.store(aggregated_insights)  [Optional]
  → ReportGenerator.generate(insights, format="Markdown")
  → 输出报告 + 运行摘要
```

### Mode2 — 赛道/主题分析
```
输入：
  mode = "multi"
  target = "AI咨询"
  platforms = ["bilibili", "douyin"]
  time_window = "last_30_days"
  max_videos = 15
  max_creators = 10
  max_concurrency = 3
  output_format = "Markdown"

流程：
  ConfigManager.load()
  → PlatformAdapter.resolve_platforms(platforms)
  → VideoListFetcher.search(target, platforms, max_creators)
      ← SourceAccessManager 控制请求
      ← 返回多博主视频列表
  → AsyncPipelineManager.process_creators(creator_list, max_concurrency=3):
      对每个博主（并行，最多3个同时）：
        → VideoListFetcher.fetch(creator, time_window, max_videos)
        → 对每个视频（串行）：
            → VideoDownloader → TranscriptGenerator → TranscriptCleaner
            → VideoSegmenter → TopicClassifier → VideoAnalyzer
            → DataStore.save(analysis_result)
        ← LoggingMonitor 记录进度
  → InsightsAggregator.aggregate(all_results, mode="multi")
  → InsightMemory.store(aggregated_insights)  [Optional]
  → ReportGenerator.generate(insights, format="Markdown")
  → 输出赛道趋势报告 + 运行摘要
```

### 错误处理流程
```
任意步骤失败时：
  → LoggingMonitor.log_error(step, error, video_info)
  → 判断错误类型：
      网络错误 → SourceAccessManager.retry(max=3, backoff=exponential)
      转录失败 → 跳过该视频，记录 skipped_reason
      分析失败 → 降级为简单摘要模式
      连续失败 → 暂停该平台，切换下一个
  → DataStore.save_checkpoint()  ← 支持断点续传
  → 继续处理剩余视频
```

---

## 10. ConfigManager 设计

### 配置文件结构（config.yaml）
```yaml
# LLM 配置（分环节配置不同模型）
llm:
  providers:
    openai:
      api_key: "${OPENAI_API_KEY}"
      base_url: "https://api.openai.com/v1"
    deepseek:
      api_key: "${DEEPSEEK_API_KEY}"
      base_url: "https://api.deepseek.com/v1"
    volcengine:  # 豆包
      api_key: "${VOLCENGINE_API_KEY}"
      base_url: "https://ark.cn-beijing.volces.com/api/v3"
    aliyun:  # 通义千问
      api_key: "${DASHSCOPE_API_KEY}"
      base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"

  # 各环节模型配置
  transcript_cleaner: "local"  # 本地规则引擎，不消耗 token
  video_segmenter: "local"     # semantic-text-splitter，不消耗 token
  topic_classifier:
    provider: "volcengine"
    model: "doubao-1.5-pro-32k"
    max_tokens: 512
    temperature: 0.2
  video_analyzer:
    provider: "deepseek"
    model: "deepseek-v3"
    max_tokens: 4096
    temperature: 0.3
  insights_aggregator:
    provider: "deepseek"
    model: "deepseek-v3"
    max_tokens: 4096
    temperature: 0.3

# 平台配置
platforms:
  bilibili:
    cookie_path: "./cookies/bilibili.txt"
    cookie_refresh_days: 7
    request_delay: [2, 6]  # 随机延时范围（秒）
  douyin:
    cookie_path: "./cookies/douyin.txt"
    cookie_refresh_days: 3
    request_delay: [3, 8]
  youtube:
    request_delay: [1, 4]
  xiaohongshu:
    cookie_path: "./cookies/xiaohongshu.txt"
    cookie_refresh_days: 5
    request_delay: [3, 8]

# 代理配置
proxy:
  enabled: false
  pool_url: ""  # 代理池API地址
  protocol: "http"  # http / socks5
  rotate_every: 10  # 每N个请求轮换
  health_check_interval: 300  # 健康检查间隔（秒）

# 存储配置
storage:
  db_type: "sqlite"  # sqlite / postgresql
  db_path: "./data/openclaw.db"
  cache_enabled: true
  cache_ttl_hours: 72  # 缓存有效期

# 日志配置
logging:
  level: "INFO"
  output: "console+file"
  log_dir: "./logs"
  structured: true
```

---

## 11. DataStore 设计

### 数据模型
```
videos 表：
  - id, platform, url, title, creator, publish_date, view_count
  - fetched_at, status (pending/downloaded/transcribed/analyzed/skipped)

transcripts 表：
  - id, video_id, raw_text, cleaned_text, segments (JSON)
  - quality_score, created_at

analyses 表：
  - id, video_id, topic_classification (JSON), analysis_result (JSON)
  - confidence_score, created_at

insights 表：
  - id, run_id, mode, target, aggregated_result (JSON)
  - created_at

run_logs 表：
  - id, run_id, step, status, duration_ms, error_message
  - created_at
```

### 缓存策略
- 同一视频 URL 在 cache_ttl 内不重复下载和分析
- 视频内容更新检测：对比 publish_date 和 view_count 变化
- 断点续传：记录每个视频的处理状态，重启时从上次中断处继续

---

## 12. LoggingMonitor 设计

### 日志格式（结构化）
```json
{
  "timestamp": "2025-03-11T10:30:00Z",
  "level": "INFO",
  "module": "VideoDownloader",
  "event": "download_complete",
  "video_url": "https://...",
  "duration_ms": 3200,
  "method": "subtitle",
  "run_id": "run_20250311_001"
}
```

### 监控指标
- 每次运行的总视频数、成功数、跳过数、失败数
- 各模块平均耗时
- 各平台抓取成功率
- LLM API 调用次数和 token 消耗
- 运行结束后自动生成运行摘要

---

## 13. LLM 成本分析与模型选型

### 13.1 LLM 调用点全景图

系统中共有以下 LLM token 消耗点：

| # | 调用点 | 调用频率 | 任务复杂度 | 是否可替代为本地方案 |
|---|--------|---------|-----------|-------------------|
| 1 | TranscriptCleaner | 每个视频 1 次 | 低 | ✅ 推荐本地规则引擎 |
| 2 | VideoSegmenter | 每个视频 1 次 | 低 | ✅ 推荐本地 semantic-text-splitter |
| 3 | TopicClassifier | 每个视频 1 次 | 中低 | ⚠️ 可用轻量模型 |
| 4 | VideoAnalyzer | 每个视频 1 次 | 高（核心环节） | ❌ 必须用强模型 |
| 5 | InsightsAggregator | 每次运行 1 次 | 高 | ❌ 必须用强模型 |
| 6 | OpenClaw 平台层 | 每次运行若干次 | 中 | ❌ 平台自身消耗 |

### 13.2 各环节推荐模型

#### 可用模型价格参考（每百万 token，2025年参考价）

| 模型 | 输入价格 | 输出价格 | 特点 | 定位 |
|------|---------|---------|------|------|
| **GPT-5.4** | $2.50 | $15.00 | 当前最强旗舰，1M上下文，128K输出 | 🔴 旗舰 |
| **GPT-5** | $1.25 | $10.00 | 前代旗舰，200K上下文 | 🔴 旗舰 |
| GPT-4o | $2.50 | $10.00 | 综合能力强，中文理解好 | 🟡 高端 |
| GPT-4o-mini | $0.15 | $0.60 | 性价比极高，轻量任务首选 | 🟢 轻量 |
| Qwen-Max | ¥8/百万 (~$1.10) | ¥24/百万 (~$3.30) | 阿里旗舰，复杂推理强 | 🟡 高端 |
| Qwen-Plus | ¥2/百万 (~$0.28) | ¥8/百万 (~$1.10) | 中等价位，能力均衡 | 🟢 中端 |
| Qwen-Turbo | ¥0.3/百万 (~$0.04) | ¥0.6/百万 (~$0.08) | 极便宜，速度快 | 🟢 轻量 |
| Doubao-1.5-Pro-32k | ¥0.8/百万 (~$0.11) | ¥2/百万 (~$0.28) | 极便宜，中文能力强 | 🟢 中端 |
| Doubao-Lite | ¥0.3/百万 (~$0.04) | ¥0.6/百万 (~$0.08) | 最便宜之一 | 🟢 轻量 |
| DeepSeek-V3 | $0.27 | $1.10 | 性价比高，缓存命中 $0.027 | 🟢 中端 |
| DeepSeek-R1 | $0.55 | $2.19 | 推理能力强，适合复杂分析 | 🟡 高端 |

#### 各环节推荐方案

**① TranscriptCleaner — 推荐：本地规则引擎（不消耗 token）**
- 首选方案：正则规则 + 口头禅词库 + 广告关键词库，能处理 80%+ 的清洗需求
- 降级方案（规则处理不了时）：Doubao-Lite 或 Qwen-Turbo（最便宜）
- 理由：清洗任务简单，不值得用 LLM

**② VideoSegmenter — 推荐：本地 semantic-text-splitter（不消耗 token）**
- 首选方案：semantic-text-splitter 库，基于语义相似度做本地分段
- 降级方案：Doubao-Lite 或 Qwen-Turbo
- 理由：分段是结构化任务，本地方案完全够用

**③ TopicClassifier — 推荐：Doubao-1.5-Pro 或 Qwen-Turbo**
- 首选：Doubao-1.5-Pro-32k（¥0.8/百万输入，中文分类能力强）
- 备选：Qwen-Turbo（¥0.3/百万输入，更便宜但分类精度略低）
- 备选：GPT-4o-mini（$0.15/百万输入，如果需要多语言支持）
- 理由：分类任务不需要强推理，轻量模型足够，但需要准确的中文理解

**④ VideoAnalyzer — 推荐：DeepSeek-V3（性价比首选）/ GPT-5.4（旗舰首选）**
- 性价比首选：DeepSeek-V3（$0.27/$1.10，支持缓存命中 90% 折扣）
- 旗舰首选：GPT-5.4（$2.50/$15.00，当前最强模型，1M 上下文窗口，对复杂口语化内容的信号提取和推理能力最强）
- 均衡选择：Qwen-Plus（¥2/¥8，能力均衡，阿里生态内调用稳定）
- 前代旗舰：GPT-4o（$2.50/$10.00，成熟稳定，输出价格比 GPT-5.4 低 33%）
- 理由：这是核心分析环节。大多数场景下 DeepSeek-V3 已经够用；但如果你追求最高分析质量（比如分析头部博主的深度内容、涉及复杂商业逻辑推理），GPT-5.4 的推理深度和上下文理解确实有可感知的提升

**⑤ InsightsAggregator — 推荐：GPT-5.4（旗舰首选）/ DeepSeek-V3（性价比首选）**
- 旗舰首选：GPT-5.4（聚合环节只调用 1 次，用最强模型的边际成本很低，但对最终报告质量影响最大）
- 性价比首选：DeepSeek-V3（输入是多条分析结果的 JSON，token 量大，缓存机制能大幅降低成本）
- 备选：Qwen-Max（阿里旗舰，复杂推理能力强）
- 理由：聚合是整个流水线的"最后一公里"，直接决定报告质量。这里多花几毛钱用旗舰模型是值得的

**⑥ 额外推荐：Claude 3.5 Sonnet / Claude 3 Haiku**
- 虽然你没列出 Claude，但值得考虑：
  - Claude 3.5 Sonnet（$3/$15）：在长文本分析和结构化输出方面表现优秀，适合 VideoAnalyzer
  - Claude 3 Haiku（$0.25/$1.25）：轻量任务性价比好，适合 TopicClassifier
- 如果你的分析内容涉及较多英文视频（YouTube），Claude 的英文分析能力有优势

### 13.3 推荐配置方案

#### 方案 A：极致性价比（推荐）
```yaml
llm:
  transcript_cleaner: "local"          # 本地规则引擎，0 成本
  video_segmenter: "local"             # semantic-text-splitter，0 成本
  topic_classifier:
    model: "doubao-1.5-pro-32k"        # ¥0.8/百万输入
    provider: "volcengine"
  video_analyzer:
    model: "deepseek-v3"               # $0.27/百万输入
    provider: "deepseek"
  insights_aggregator:
    model: "deepseek-v3"               # $0.27/百万输入（缓存命中更便宜）
    provider: "deepseek"
```

#### 方案 B：质量优先
```yaml
llm:
  transcript_cleaner: "local"
  video_segmenter: "local"
  topic_classifier:
    model: "gpt-4o-mini"               # $0.15/百万输入
    provider: "openai"
  video_analyzer:
    model: "gpt-4o"                    # $2.50/百万输入
    provider: "openai"
  insights_aggregator:
    model: "gpt-5.4"                   # $2.50/百万输入，输出质量最高
    provider: "openai"
```

#### 方案 B+：旗舰全开（追求极致分析质量）
```yaml
llm:
  transcript_cleaner: "local"
  video_segmenter: "local"
  topic_classifier:
    model: "gpt-4o-mini"               # $0.15/百万输入（分类不需要旗舰）
    provider: "openai"
  video_analyzer:
    model: "gpt-5.4"                   # $2.50/百万输入，最强分析能力
    provider: "openai"
  insights_aggregator:
    model: "gpt-5.4"                   # $2.50/百万输入，最强聚合推理
    provider: "openai"
```
> 适用场景：分析头部博主深度内容、涉及复杂商业逻辑推理、对报告质量有极高要求时使用。
> GPT-5.4 的 1M 上下文窗口在 InsightsAggregator 聚合大量分析结果时特别有优势。

#### 方案 C：国内生态优先（全中国模型）
```yaml
llm:
  transcript_cleaner: "local"
  video_segmenter: "local"
  topic_classifier:
    model: "qwen-turbo"                # ¥0.3/百万输入
    provider: "aliyun"
  video_analyzer:
    model: "qwen-plus"                 # ¥2/百万输入
    provider: "aliyun"
  insights_aggregator:
    model: "qwen-max"                  # ¥8/百万输入
    provider: "aliyun"
```

### 13.4 成本估算对比

#### Mode1（单博主 20 个视频）

| 环节 | 方案A（极致性价比） | 方案B（质量优先） | 方案B+（旗舰全开） | 方案C（国内生态） |
|------|-------------------|------------------|-------------------|-----------------|
| TranscriptCleaner | ¥0（本地） | ¥0（本地） | ¥0（本地） | ¥0（本地） |
| VideoSegmenter | ¥0（本地） | ¥0（本地） | ¥0（本地） | ¥0（本地） |
| TopicClassifier（20次） | ~¥0.02 | ~$0.003 | ~$0.003 | ~¥0.006 |
| VideoAnalyzer（20次） | ~$0.04 | ~$0.35 | ~$0.55 | ~¥0.12 |
| InsightsAggregator（1次） | ~$0.005 | ~$0.06 | ~$0.06 | ~¥0.05 |
| **单次运行总计** | **~¥0.35 (~$0.05)** | **~$0.41 (~¥3.0)** | **~$0.61 (~¥4.4)** | **~¥0.20** |

#### Mode2（10 个博主 × 15 个视频 = 150 个视频）

| 环节 | 方案A（极致性价比） | 方案B（质量优先） | 方案B+（旗舰全开） | 方案C（国内生态） |
|------|-------------------|------------------|-------------------|-----------------|
| TranscriptCleaner | ¥0（本地） | ¥0（本地） | ¥0（本地） | ¥0（本地） |
| VideoSegmenter | ¥0（本地） | ¥0（本地） | ¥0（本地） | ¥0（本地） |
| TopicClassifier（150次） | ~¥0.15 | ~$0.02 | ~$0.02 | ~¥0.05 |
| VideoAnalyzer（150次） | ~$0.30 | ~$2.60 | ~$4.10 | ~¥0.90 |
| InsightsAggregator（1次） | ~$0.02 | ~$0.18 | ~$0.18 | ~¥0.15 |
| **单次运行总计** | **~¥2.5 (~$0.35)** | **~$2.80 (~¥20)** | **~$4.30 (~¥31)** | **~¥1.10** |

> **方案选择建议**：
> - 日常批量分析、定期跟踪 → 方案 A 或 C（成本可控）
> - 重要博主深度分析、关键赛道研究 → 方案 B（质量与成本平衡）
> - 高价值决策场景、需要最深度洞察 → 方案 B+（旗舰全开，单次多花几块钱换最高质量）
> - 可以混合使用：日常用方案 A，重要分析切换到方案 B+，通过 ConfigManager 动态切换即可

> 注：以上为 LLM API 消耗估算，不含 OpenClaw 平台层自身的 token 消耗。
> 实际成本还会因视频长度、转录文本量、TopicClassifier 过滤率等因素波动。

### 13.5 成本优化策略

#### 架构层优化（已在设计中体现）
1. **TranscriptCleaner 和 VideoSegmenter 使用本地方案**：直接省掉 2 个 LLM 调用点，每个视频少 2 次 API 调用
2. **TopicClassifier 前置过滤**：business_relevance < 0.3 的视频跳过 VideoAnalyzer，按 20% 过滤率计算，Mode2 可省掉 ~30 次 VideoAnalyzer 调用
3. **DataStore 缓存**：同一视频不重复分析，对于定期跟踪同一博主的场景，缓存命中率可达 60%+

#### 模型层优化
4. **分层模型策略**：轻量任务用便宜模型，核心分析用强模型，不要一刀切
5. **DeepSeek 缓存机制**：DeepSeek-V3 支持输入缓存，缓存命中时输入价格降至 $0.027/百万（90% 折扣）。对于 InsightsAggregator 这种 system prompt 固定的场景，缓存效果显著
6. **Prompt 精简**：严格约束输出 JSON Schema，避免 LLM 输出废话，减少输出 token（输出 token 单价是输入的 3~4 倍）

#### 运营层优化
7. **批量处理**：积累一定量的视频后批量分析，利用 DeepSeek 的缓存机制
8. **监控 token 消耗**：LoggingMonitor 记录每次 LLM 调用的 token 数和费用，定期审查是否有浪费
9. **动态模型切换**：ConfigManager 支持按环节配置不同模型，可以随时根据成本和质量反馈调整

---

## 14. Optimization Notes

- **TopicClassifier 前置**：先分类再分析，让 VideoAnalyzer 根据主题类型调整分析策略，提高分析质量
- **TranscriptCleaner 本地化**：规则引擎 + 口头禅词库，不消耗 LLM token，处理 80%+ 清洗需求
- **VideoSegmenter 本地化**：使用 semantic-text-splitter 做语义分段，不消耗 LLM token
- **分层模型策略**：轻量任务（分类）用 Doubao-Lite/Qwen-Turbo，核心分析用 DeepSeek-V3/GPT-4o，成本降低 80%+
- **SourceAccessManager 中间件化**：作为横切关注点贯穿所有网络请求，统一管理反爬策略
- **AsyncPipelineManager**：Mode2 多博主并行处理，显著提升效率
- **DataStore 缓存**：避免重复分析同一视频，支持断点续传，定期跟踪场景缓存命中率 60%+
- **DeepSeek 缓存机制**：利用 DeepSeek-V3 的输入缓存，system prompt 固定场景可享 90% 输入折扣
- **Prompt 精简**：严格 JSON Schema 约束输出，减少输出 token（输出单价是输入的 3~4 倍）
- **confidence_score**：所有分析结果带质量评分，用户可快速识别高价值洞察
- **降级策略链**：每个步骤都有降级方案，保证流水线不会因单点失败而中断
- **token 消耗监控**：LoggingMonitor 记录每次 LLM 调用的 token 数和费用，支持成本审查

---

## 15. Future Extensions

- 支持更多视频平台（快手、微博视频等）
- 提供长周期趋势监控和预警（基于 InsightMemory 的时序对比）
- 可训练的 InsightsAggregator 模块，提高分析准确性
- 输出可定制化报告格式（HTML, Excel, PPT）
- LLM 模型动态切换：根据成本和质量反馈自动调整各环节模型选择
- Web UI 管理界面：配置管理、运行监控、报告浏览（模型选择界面已在第3章设计）
- Webhook 通知：运行完成后推送到飞书/钉钉/Slack
- 多语言支持：英文、日文视频内容分析

---

此文档为 OpenClaw 开发团队的完整开发蓝图，涵盖架构设计、模块职责、数据流、配置管理、错误处理和监控方案。
