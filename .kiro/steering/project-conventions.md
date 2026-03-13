---
inclusion: auto
---

# 项目开发规范

## 技术栈

- 语言：Python 3.11+
- 异步框架：asyncio + aiohttp
- 配置管理：pydantic-settings
- 日志：structlog + Rich
- 数据库：SQLite（开发）/ PostgreSQL（生产）
- 向量存储：ChromaDB / FAISS
- 视频下载：yt-dlp
- 音频转录：faster-whisper
- 文本分段：semantic-text-splitter
- LLM 调用：OpenAI SDK（兼容 DeepSeek、千问、豆包等 OpenAI 兼容接口）

## 项目结构

```
openclaw/
├── config/              # 配置文件（config.yaml, cookies/）
├── src/
│   ├── core/            # 核心流水线模块
│   │   ├── platform_adapter.py
│   │   ├── video_list_fetcher.py
│   │   ├── video_downloader.py
│   │   ├── transcript_generator.py
│   │   ├── transcript_cleaner.py
│   │   ├── video_segmenter.py
│   │   ├── topic_classifier.py
│   │   ├── video_analyzer.py
│   │   ├── insights_aggregator.py
│   │   ├── insight_memory.py
│   │   └── report_generator.py
│   ├── infra/           # 基础设施模块
│   │   ├── config_manager.py
│   │   ├── async_pipeline_manager.py
│   │   ├── source_access_manager.py
│   │   ├── logging_monitor.py
│   │   └── data_store.py
│   ├── models/          # 数据模型（pydantic schemas）
│   ├── prompts/         # LLM Prompt 模板
│   └── utils/           # 工具函数
├── tests/               # 测试
├── data/                # 运行时数据（SQLite、缓存）
├── logs/                # 日志文件
└── reports/             # 生成的报告
```

## 编码规范

- 遵循 PEP 8，行宽 120 字符
- 使用 type hints 标注所有函数签名
- 所有公开函数和类必须有中文 docstring
- 异步函数使用 async/await，不使用回调
- 错误处理使用自定义异常类，不裸抛 Exception
- 配置项通过 pydantic-settings 管理，不硬编码

## Git 规范

- 提交信息使用中文，格式：`<类型>: <描述>`
- 类型包括：功能、修复、重构、文档、测试、配置
- 示例：`功能: 实现 PlatformAdapter B站适配器`
- 每个模块独立提交，不混合多个模块的改动
