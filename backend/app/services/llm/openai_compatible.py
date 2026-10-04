from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import NoReturn

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)

from app.core.config import Settings
from app.core.errors import LLMServiceError, LLMTimeoutError
from app.services.llm.base import (
    AgentMessage,
    AgentToolCall,
    AgentToolResponse,
    LLMMessage,
    LLMProvider,
)

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, settings: Settings) -> None:
        self._model = settings.llm_model
        self._temperature = settings.llm_temperature
        self._max_tokens = settings.llm_max_tokens
        self._client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=settings.llm_timeout_seconds,
            max_retries=0,
        )

    @property
    def name(self) -> str:
        return "openai-compatible"

    @property
    def supports_tools(self) -> bool:
        return True

    @staticmethod
    def _raise_provider_error(exc: Exception) -> NoReturn:
        if isinstance(exc, APITimeoutError):
            logger.warning("LLM request timed out")
            raise LLMTimeoutError() from exc
        if isinstance(exc, AuthenticationError):
            logger.error("LLM authentication failed")
            raise LLMServiceError("模型服务认证失败，请检查后端 API Key 配置") from exc
        if isinstance(exc, RateLimitError):
            logger.warning("LLM rate limit reached")
            raise LLMServiceError("模型服务请求过于频繁，请稍后重试") from exc
        if isinstance(exc, (APIConnectionError, APIError)):
            logger.warning("LLM provider request failed: %s", type(exc).__name__)
            raise LLMServiceError() from exc
        logger.exception("Unexpected LLM provider error")
        raise LLMServiceError() from exc

    async def complete(self, messages: list[LLMMessage]) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )
        except Exception as exc:
            self._raise_provider_error(exc)

        content = response.choices[0].message.content if response.choices else None
        if not content or not content.strip():
            raise LLMServiceError("模型服务返回了空内容，请重新发送")
        return content.strip()

    async def stream(self, messages: list[LLMMessage]) -> AsyncIterator[str]:
        has_content = False
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                stream=True,
            )
            async for event in response:
                content = event.choices[0].delta.content if event.choices else None
                if content:
                    has_content = True
                    yield content
        except Exception as exc:
            self._raise_provider_error(exc)

        if not has_content:
            raise LLMServiceError("模型服务返回了空内容，请重新发送")

    async def complete_with_tools(
        self, messages: list[AgentMessage], tools: list[dict]
    ) -> AgentToolResponse:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                tools=tools,
            )
        except Exception as exc:
            self._raise_provider_error(exc)

        if not response.choices:
            raise LLMServiceError("模型服务返回了空内容，请重新发送")
        message = response.choices[0].message
        raw_calls = getattr(message, "tool_calls", None) or []
        tool_calls = [
            AgentToolCall(
                id=call.id or "",
                name=call.function.name,
                arguments=call.function.arguments or "{}",
            )
            for call in raw_calls
            if call.function and call.function.name
        ]
        content = (message.content or "").strip() if message.content else ""
        if not tool_calls and not content:
            raise LLMServiceError("模型服务返回了空内容，请重新发送")
        return AgentToolResponse(content=content or None, tool_calls=tool_calls)
