from __future__ import annotations

from typing import Protocol

from app.agent.models import GovernmentAgentState


class AgentNode(Protocol):
    async def execute(self, state: GovernmentAgentState) -> GovernmentAgentState: ...
