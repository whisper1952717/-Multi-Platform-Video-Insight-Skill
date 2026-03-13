"""统一 LLM 客户端，支持多 provider 的异步调用。"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Type

import aiohttp
from pydantic import BaseModel

from openclaw.config.settings import LLMModelConfig, LLMProviderConfig

logger = logging.getLogger(__name__)


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

        async with session.post(url, json=payload, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json()

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
