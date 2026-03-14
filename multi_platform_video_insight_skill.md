---
name: multi-platform-video-insight
description: 抓取多平台视频（B站、抖音、YouTube、小红书），提取行业信号、认知框架、方法论，生成洞察报告。支持单博主深度分析（Mode1）和赛道多博主横向分析（Mode2）。
metadata: {"openclaw": {"emoji": "🎬", "requires": {"bins": ["video-insight"], "env": ["OPENROUTER_API_KEY"]}, "primaryEnv": "OPENROUTER_API_KEY"}}
---

# Multi-Platform Video Insight

## 功能概述

从多平台视频中提取商业洞察，支持两种分析模式：

- **Mode1（单博主分析）**：深度分析单个博主的视频，提取核心信号、认知框架、方法论、高价值表达
- **Mode2（赛道分析）**：横向分析多博主视频，提炼行业趋势、共识与分歧、商业机会

支持平台：B站、抖音、YouTube、小红书

## 使用方法

### Mode1 — 单博主分析

```
video-insight mode1 <博主主页URL> [选项]
```

示例：
```
video-insight mode1 https://space.bilibili.com/12345 --max-videos 20 --llm-preset cost_effective
video-insight mode1 https://www.youtube.com/@channel --output-format JSON
video-insight mode1 https://space.bilibili.com/12345 --use-last-config
```

### Mode2 — 赛道分析

```
video-insight mode2 <关键词> [选项]
```

示例：
```
video-insight mode2 "AI创业" --platforms bilibili youtube --max-creators 5
video-insight mode2 "量化交易" --platforms bilibili douyin --max-videos 15 --max-creators 8
```

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--time-window` | 时间范围：last_7_days / last_30_days / last_90_days / last_180_days / last_365_days | last_30_days |
| `--max-videos` | 每博主最大分析视频数 | 20 |
| `--max-creators` | Mode2 最大博主数（仅 Mode2） | 10 |
| `--max-concurrency` | 并发博主数（仅 Mode2） | 3 |
| `--output-format` | 输出格式：Markdown / PDF / JSON | Markdown |
| `--llm-preset` | LLM 方案：cost_effective / quality / flagship / china_eco | cost_effective |
| `--use-last-config` | 使用上次保存的配置快速启动 | false |

## LLM 方案说明

| 方案 | TopicClassifier | VideoAnalyzer | Aggregator | 预估成本(Mode1/Mode2) |
|------|----------------|---------------|------------|----------------------|
| `cost_effective` | Doubao-1.5-Pro | DeepSeek-V3 | DeepSeek-V3 | ~¥0.35 / ~¥2.5 |
| `quality` | GPT-4o-mini | GPT-4o | GPT-5.4 | ~¥3.0 / ~¥20 |
| `flagship` | GPT-4o-mini | GPT-5.4 | GPT-5.4 | ~¥4.4 / ~¥31 |
| `china_eco` | Qwen-Turbo | Qwen-Plus | Qwen-Max | ~¥0.20 / ~¥1.1 |

## API Key 配置

**推荐新手：只需一个 OpenRouter key**，即可访问 DeepSeek、GPT-4o、MiniMax 等几十个模型。

注册地址：https://openrouter.ai（支持支付宝/信用卡充值）

在 `~/.openclaw/openclaw.json` 中配置：

```json
{
  "skills": {
    "entries": {
      "multi-platform-video-insight": {
        "enabled": true,
        "env": {
          "OPENROUTER_API_KEY": "sk-or-xxx"
        }
      }
    }
  }
}
```

**进阶用户：直接配置各家 key**，系统启动时自动推荐最优方案，支持切换预设或逐模块调整：

| 环境变量 | 服务商 | 特点 |
|----------|--------|------|
| `DEEPSEEK_API_KEY` | DeepSeek | 性价比标杆，$0.27/$1.10 每百万token |
| `VOLCENGINE_API_KEY` | 豆包（字节） | 国内最便宜之一，¥0.8/¥2.0 |
| `DASHSCOPE_API_KEY` | 通义千问（阿里） | 均衡，Turbo版极速 |
| `MINIMAX_API_KEY` | MiniMax | M2.5旗舰，1M超大上下文，$0.30/$1.20 |
| `ZHIPU_API_KEY` | 智谱GLM | Flash版完全免费，Plus版$0.60/$2.20 |
| `MOONSHOT_API_KEY` | Kimi（月之暗面） | 长文本强，128K上下文，$0.15/$2.50 |
| `OPENAI_API_KEY` | OpenAI | GPT-4o，生态成熟 |

只需填写你已有的 key，系统会自动匹配最优预设。启动时可进一步调整每个模块使用的具体模型。

## Cookie 配置

B站、抖音、小红书需要 Cookie 才能抓取数据。将浏览器导出的 Cookie 文件放到 skill 安装目录下的 `cookies/` 文件夹：

```
~/.openclaw/skills/multi-platform-video-insight/
├── SKILL.md
└── cookies/
    ├── bilibili.txt
    ├── douyin.txt
    └── xiaohongshu.txt
```

## 输出说明

分析完成后在当前目录生成报告文件，例如：
- `video_insight_report_mode1_20260314_103000.md`
- `video_insight_report_mode2_20260314_103000.json`

报告包含：核心信号（含置信度评分）、认知框架、方法论片段、高价值引用、商业机会判断、对用户的启发。

## 安装前提

使用此 skill 前，需在本机安装 video-insight CLI 工具：

```bash
cd /path/to/video-insight
pip install -e .
```

安装后 `video-insight` 命令即可在终端使用。
