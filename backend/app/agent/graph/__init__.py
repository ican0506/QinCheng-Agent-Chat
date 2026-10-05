"""LangGraph 编排层：仅协调既有业务节点，不承载业务规则。"""

from app.agent.graph.graph import GovernmentAgentGraph

__all__ = ["GovernmentAgentGraph"]
