---
inclusion: fileMatch
fileMatchPattern: '**/source_access_manager.py,**/video_downloader.py,**/video_list_fetcher.py,**/platform_adapter.py'
---

# 反爬与网络安全规范

## 请求频率

- 所有网络请求必须经过 SourceAccessManager 中间件
- 禁止绕过 SourceAccessManager 直接发起 HTTP 请求
- 每次请求之间必须有随机延时，最小 1 秒
- 单平台请求间隔不低于 3 秒

## Cookie 安全

- Cookie 文件不得提交到 Git 仓库（已在 .gitignore 中排除）
- Cookie 存储必须加密，不以明文形式保存
- API Key 通过环境变量注入，不写入配置文件

## 降级策略

- 每个网络请求步骤都必须有降级方案
- 降级链：字幕获取 → 音频下载 → 跳过并记录
- 单视频失败不得中断整个流水线
- 连续失败 5 次必须暂停该平台

## 代理使用

- 代理配置通过 ConfigManager 管理
- 代理池接口必须支持健康检查
- 无可用代理时自动降级为直连
