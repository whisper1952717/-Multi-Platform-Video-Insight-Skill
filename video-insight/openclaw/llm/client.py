"""统一 LLM 客户端，支持多 provider 的异步调用。"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Type

import aiohttp
from pydantic import BaseModel

from openclaw.config.settings import LLMModelConfig, LLMProviderConfig

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """LLM 调用错误基类。"""
    def __init__(self, message: str, status_code: int = 0, provider: str = "", model: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.provider = provider
        self.model = model


class LLMAuthError(LLMError):
    """API key 无效或未授权（401）。"""


class LLMQuotaError(LLMError):
    """余额不足或超出配额（402/429）。"""


class LLMConnectionError(LLMError):
    """无法连接到 provider（网络问题或 gateway 未启动）。"""


def _classify_error(status: int, body: str, provider: str, model: str) -> LLMError:
    """根据 HTTP 状态码和响应体分类错误。"""
    msg_lower = body.lower()

    if status == 401 or "invalid api key" in msg_lower or "unauthorized" in msg_lower or "authentication" in msg_lower:
        hint = _auth_hint(provider)
        return LLMAuthError(
            f"❌ [{provider}/{model}] API key 无效或未授权\n   {hint}",
            status_code=status, provider=provider, model=model,
        )

    if status in (402, 429) or "insufficient" in msg_lower or "quota" in msg_lower or "balance" in msg_lower or "rate limit" in msg_lower:
        hint = _quota_hint(provider, status)
        return LLMQuotaError(
            f"❌ [{provider}/{model}] {'余额不足' if status == 402 or 'balance' in msg_lower or 'insufficient' in msg_lower else '请求频率超限'}\n   {hint}",
            status_code=status, provider=provider, model=model,
        )

    return LLMError(
        f"❌ [{provider}/{model}] 请求失败（HTTP {status}）：{body[:200]}",
        status_code=status, provider=provider, model=model,
    )


def _auth_hint(provider: str) -> str:
    hints = {
        "openai":     "请检查 OPENAI_API_KEY 是否正确，或前往 https://platform.openai.com/api-keys 重新生成",
        "deepseek":   "请检查 DEEPSEEK_API_KEY，或前往 https://platform.deepseek.com 确认",
        "doubao":     "请检查 VOLCENGINE_API_KEY，或前往火山引擎控制台确认",
        "qwen":       "请检查 DASHSCOPE_API_KEY，或前往阿里云灵积控制台确认",
        "minimax":    "请检查 MINIMAX_API_KEY，或前往 https://platform.minimaxi.com 确认",
        "zhipu":      "请检查 ZHIPU_API_KEY，或前往 https://open.bigmodel.cn 确认",
        "moonshot":   "请检查 MOONSHOT_API_KEY，或前往 https://platform.moonshot.cn 确认",
        "openrouter": "请检查 OPENROUTER_API_KEY，或前往 https://openrouter.ai/keys 确认",
        "openclaw":   "openclaw gateway 认证失败，请检查 OPENCLAW_GATEWAY_TOKEN 或运行 openclaw doctor",
    }
    return hints.get(provider, "请检查对应的 API key 配置")


def _quota_hint(provider: str, status: int) -> str:
    if provider == "openclaw":
        return "ChatGPT 订阅可能已达用量上限，请稍后重试或切换其他 provider"
    if provider == "openrouter":
        return "OpenRouter 余额不足，请前往 https://openrouter.ai/credits 充值"
    hints = {
        "openai":   "OpenAI 余额不足，请前往 https://platform.openai.com/billing 充值",
        "deepseek": "DeepSeek 余额不足，请前往 https://platform.deepseek.com/usage 充值",
        "doubao":   "豆包余额不足，请前往火山引擎控制台充值",
        "qwen":     "通义千问余额不足，请前往阿里云控制台充值",
        "minimax":  "MiniMax 余额不足，请前往 https://platform.minimaxi.com 充值",
        "zhipu":    "智谱余额不足，请前往 https://open.bigmodel.cn 充值",
        "moonshot": "Kimi 余额不足，请前往 https://platform.moonshot.cn 充值",
    }
    suffix = "（429 频率限制，请稍后重试）" if status == 429 else ""
    return hints.get(provider, "请检查账户余额") + suffix


class LLMClient:
    """统一 LLM 调用客户端，支持 OpenAI 兼容接口。"""

    def __init__(self, providers: Dict[str, LLMProviderConfig]):
        self._providers = providers
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def call(
        self,
        model_config: LLMModelConfig,
        system_prompt: str,
        user_prompt: str,
        response_schema: Optional[Type[BaseModel]] = None,
        few_shot_examples: Optional[List[dict]] = None,
    ) -> Any:
        """
        统一 LLM 调用接口（OpenAI 兼容格式）。

        Args:
            model_config: 模型配置（provider + model + params）
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            response_schema: 期望的响应 Pydantic 模型（用于解析和校验）
            few_shot_examples: Few-shot 示例列表，格式 [{"role": "user"/"assistant", "content": str}]

        Returns:
            若提供 response_schema，返回对应 Pydantic 模型实例；否则返回原始字符串。
        """
        provider_cfg = self._providers.get(model_config.provider)
        if not provider_cfg:
            raise ValueError(f"未找到 provider 配置：{model_config.provider}")

        messages = [{"role": "system", "content": system_prompt}]
        if few_shot_examples:
            messages.extend(few_shot_examples)
        messages.append({"role": "user", "content": user_prompt})

        payload: dict = {
            "model": model_config.model,
            "messages": messages,
            "max_tokens": model_config.max_tokens,
            "temperature": model_config.temperature,
        }

        # 若有 schema，要求 JSON 输出
        if response_schema:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {provider_cfg.api_key}",
            "Content-Type": "application/json",
        }

        session = await self._get_session()
        url = f"{provider_cfg.base_url.rstrip('/')}/chat/completions"

        try:
            async with session.post(url, json=payload, headers=headers) as resp:
                body = await resp.text()
                if resp.status >= 400:
                    raise _classify_error(resp.status, body, model_config.provider, model_config.model)
                data = json.loads(body)
        except aiohttp.ClientConnectorError as e:
            provider = model_config.provider
            if provider == "openclaw":
                raise LLMConnectionError(
                    f"❌ 无法连接到 openclaw gateway（{provider_cfg.base_url}）\n"
                    "   请确认 openclaw 正在运行，或检查 OPENCLAW_GATEWAY_URL 配置",
                    provider=provider, model=model_config.model,
                ) from e
            raise LLMConnectionError(
                f"❌ [{provider}/{model_config.model}] 连接失败：{e}\n   请检查网络或 base_url 配置",
                provider=provider, model=model_config.model,
            ) from e
        except (LLMAuthError, LLMQuotaError, LLMConnectionError, LLMError):
            raise
        except Exception as e:
            raise LLMError(
                f"❌ [{model_config.provider}/{model_config.model}] 未知错误：{e}",
                provider=model_config.provider, model=model_config.model,
            ) from e

        content = data["choices"][0]["message"]["content"]

        # 记录 token 消耗
        usage = data.get("usage", {})
        logger.info(
            "llm_call_completed",
            extra={
                "model": model_config.model,
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
            },
        )

        if response_schema:
            parsed = json.loads(content)
            return response_schema.model_validate(parsed)

        return content

    async def __aenter__(self) -> "LLMClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
