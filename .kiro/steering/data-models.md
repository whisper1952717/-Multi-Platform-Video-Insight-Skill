---
inclusion: fileMatch
fileMatchPattern: '**/models/**,**/data_store.py'
---

# 数据模型规范

## Pydantic 模型

- 所有数据结构使用 pydantic BaseModel 定义
- 模型定义统一放在 `src/models/` 目录
- 字段必须有类型标注和中文描述（Field(description="...")）
- 枚举值使用 Python Enum 类型

## 数据库模型

- 数据库表结构与 Pydantic 模型保持一致
- 使用 SQLAlchemy 或 SQLModel 作为 ORM
- 所有表必须有 id、created_at 字段
- videos 表必须有 status 字段追踪处理状态

## JSON 输出

- 所有 LLM 输出必须经过 Pydantic 模型校验
- 校验失败时记录原始输出并触发重试
- 最终报告输出必须符合需求文档中定义的 JSON Schema
