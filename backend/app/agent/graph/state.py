"""LangGraph 使用的强类型、请求作用域状态。"""
from __future__ import annotations

from typing import TypedDict

from app.agent.models import GovernmentAgentState


class GovernmentAgentGraphState(TypedDict):
    """图中每条边传递的完整 Agent State。

    业务节点仍以 GovernmentAgentState 作为强类型模型，图适配层只负责在
    LangGraph 的字典状态与该模型之间转换；不会把任何结果存入实例属性。
    """

    agent: GovernmentAgentState
