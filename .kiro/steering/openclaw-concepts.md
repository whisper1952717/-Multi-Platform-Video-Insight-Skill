# OpenClaw 概念定义与 Skill 格式规范

## 术语定义

### openclaw（机器人）
指部署在用户电脑上的 **OpenClaw 个人 AI 助手平台**（https://openclaw.ai）。
- 是一个运行在本地电脑上的 AI agent，可通过 WhatsApp、Telegram、Discord 等聊天软件交互
- 支持持久记忆、浏览器控制、文件系统访问、执行 shell 命令等能力
- 可通过 Skills 扩展功能

### video-insight 目录
指工作区中的 `video-insight/` 文件夹，包含我们自己开发的 Python 代码（Multi-Platform Video Insight 功能的实现）。
- 这是一个独立的 Python CLI 工具，需要单独安装（`pip install -e .`）
- 安装后提供 `video-insight` 命令行工具供 openclaw 机器人调用

### Skills
openclaw 机器人的扩展功能模块。每个 skill 是一个文件夹，包含 `SKILL.md` 文件，用于告诉 AI agent 有哪些工具可用以及如何使用。

**Skills 存放位置（优先级从高到低）：**
1. `<workspace>/skills/` — 仅当前 agent 可用
2. `~/.openclaw/skills/` — 所有 agent 共享
3. 内置 skills — openclaw 自带

## SKILL.md 格式规范

每个 skill 文件夹必须包含一个 `SKILL.md`，格式如下：

```markdown
---
name: skill-name
description: 一句话描述这个 skill 的功能
metadata: {"openclaw": {"emoji": "🎯", "requires": {"bins": ["some-cli"], "env": ["API_KEY"]}, "primaryEnv": "API_KEY"}}
---

# Skill 使用说明

（正文：告诉 AI agent 这个工具是什么、怎么用、参数是什么）
```

### frontmatter 必填字段
- `name` — skill 唯一标识符（kebab-case）
- `description` — 简短描述，会注入到 agent 的 system prompt

### frontmatter 可选字段
- `metadata` — 单行 JSON，包含 openclaw 专属配置：
  - `requires.bins` — 需要在 PATH 中存在的命令行工具
  - `requires.env` — 需要设置的环境变量
  - `requires.config` — 需要在 openclaw.json 中为 truthy 的配置项
  - `primaryEnv` — 关联的主要 API key 环境变量名
  - `emoji` — 在 macOS Skills UI 中显示的 emoji
  - `always: true` — 跳过所有 gate 检查，始终加载
- `user-invocable` — `true/false`，是否暴露为斜杠命令（默认 true）

## 安装 Skill 的完整流程

我们的 Multi-Platform Video Insight skill 依赖 openclaw 目录中的 Python 代码，因此安装分两步：

**第一步：在 openclaw 电脑上安装 Python 工具**
```bash
cd video-insight
pip install -e .
```

**第二步：安装 skill 文件**
```bash
mkdir -p ~/.openclaw/skills/multi-platform-video-insight
cp multi_platform_video_insight_skill.md ~/.openclaw/skills/multi-platform-video-insight/SKILL.md
```

**第三步：在 `~/.openclaw/openclaw.json` 中配置 API keys**

至少配置一个即可，系统自动推荐最优方案：

```json
{
  "skills": {
    "entries": {
      "multi-platform-video-insight": {
        "enabled": true,
        "env": {
          "OPENROUTER_API_KEY": "sk-or-xxx",
          "DEEPSEEK_API_KEY": "sk-xxx",
          "VOLCENGINE_API_KEY": "xxx",
          "MINIMAX_API_KEY": "xxx",
          "ZHIPU_API_KEY": "xxx",
          "MOONSHOT_API_KEY": "sk-xxx",
          "DASHSCOPE_API_KEY": "sk-xxx",
          "OPENAI_API_KEY": "sk-xxx"
        }
      }
    }
  }
}
```

新手推荐只填 `OPENROUTER_API_KEY`（一个key访问多模型）。

## 关系示意

```
用户（WhatsApp/Telegram）
    ↓ 发消息
openclaw 机器人
    ↓ 读取 skill 说明，知道有视频分析能力
    ↓ 从 openclaw.json 注入 API keys 为环境变量
video-insight CLI 工具（`video-insight mode1 ...`）
    ↓ 执行
视频下载 → 转录 → 分析 → 生成报告
```
