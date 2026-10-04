from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict


class LLMMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


# Agent 工具循环允许 assistant(tool_calls) 与 role="tool" 消息，直接使用宽松 dict。
AgentMessage = dict[str, Any]


@dataclass(frozen=True)
class AgentToolCall:
    """LLM 发起的一次工具调用请求。"""

    id: str
    name: str
    arguments: str


@dataclass(frozen=True)
class AgentToolResponse:
    """complete_with_tools 的返回：要么给出文本，要么给出工具调用。"""

    content: str | None = None
    tool_calls: list[AgentToolCall] = field(default_factory=list)


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, messages: list[LLMMessage]) -> str:
        """Return one assistant reply for the supplied conversation."""

    async def stream(self, messages: list[LLMMessage]) -> AsyncIterator[str]:
        """Yield reply chunks. Providers without streaming support use one chunk."""
        yield await self.complete(messages)

    @property
    def supports_tools(self) -> bool:
        """Whether the provider supports OpenAI-style function calling."""
        return False

    async def complete_with_tools(
        self, messages: list[AgentMessage], tools: list[dict[str, Any]]
    ) -> AgentToolResponse:
        """Run one tool-aware completion. Only valid when supports_tools is True."""
        raise NotImplementedError("当前 LLM Provider 不支持 function calling")

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name for health checks."""


class UnavailableLLMProvider(LLMProvider):
    @property
    def name(self) -> str:
        return "not-configured"

    async def complete(self, messages: list[LLMMessage]) -> str:
        from app.core.errors import LLMServiceError

        raise LLMServiceError("模型服务尚未配置，请在后端 .env 中设置 LLM_API_KEY")
