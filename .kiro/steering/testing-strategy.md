---
inclusion: fileMatch
fileMatchPattern: '**/tests/**,**/test_*'
---

# 测试策略

## 测试框架

- 使用 pytest 作为测试框架
- 异步测试使用 pytest-asyncio
- Mock 外部依赖（LLM API、视频平台 API、yt-dlp）

## 测试分层

- 单元测试：每个模块独立测试，Mock 所有外部依赖
- 集成测试：测试模块间的数据流转（如 TranscriptCleaner → VideoSegmenter → TopicClassifier）
- 端到端测试：使用预录制的测试数据跑完整流水线

## 必须测试的场景

- 各平台 URL 识别（PlatformAdapter）
- 降级策略链触发（字幕失败 → 音频 → 跳过）
- TopicClassifier 过滤逻辑（business_relevance < 0.3 跳过）
- LLM 返回非法 JSON 的重试逻辑
- 缓存命中和断点续传
- Mode1 和 Mode2 的完整输出结构校验
- 并发调度的正确性（AsyncPipelineManager）

## 测试数据

- 在 `tests/fixtures/` 目录存放测试用的转录文本、LLM 响应 mock 数据
- 不使用真实的视频 URL 或博主数据作为测试输入
- 测试数据中的个人信息使用占位符替代
