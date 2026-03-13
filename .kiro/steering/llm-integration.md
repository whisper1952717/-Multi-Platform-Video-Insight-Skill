---
inclusion: fileMatch
fileMatchPattern: '**/topic_classifier.py,**/video_analyzer.py,**/insights_aggregator.py,**/prompts/**'
---

# LLM 集成规范

## 多 Provider 统一接口

所有 LLM 调用必须通过统一的 LLM 客户端接口，不直接调用各 provider 的 SDK。
使用 OpenAI SDK 的兼容模式，通过 base_url 切换不同 provider（OpenAI、DeepSeek、千问、豆包）。

## Prompt 管理

- Prompt 模板统一存放在 `src/prompts/` 目录
- 使用 Jinja2 或 Python f-string 模板，不在代码中硬编码长 prompt
- 每个 prompt 必须包含严格的 JSON Schema 输出约束
- VideoAnalyzer prompt 必须包含 few-shot 示例

## Token 成本控制

- 每次 LLM 调用必须记录 input_tokens、output_tokens 和费用
- 通过 LoggingMonitor 汇总每次运行的总 token 消耗
- 输出格式严格约束为 JSON，避免 LLM 输出冗余文本
- temperature 设置：分类任务 0.1~0.2，分析任务 0.3，聚合任务 0.3

## 错误处理

- LLM 返回非法 JSON 时，最多重试 2 次
- 重试时在 prompt 中追加格式纠正提示
- 连续失败后降级为简单摘要模式
- 所有 LLM 调用设置超时（默认 60 秒）
