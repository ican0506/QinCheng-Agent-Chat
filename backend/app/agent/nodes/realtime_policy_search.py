import logging
from time import perf_counter
from app.agent.models import GovernmentAgentState
from app.realtime_policy.intent import FreshnessIntentDetector
from app.realtime_policy.models import RealtimeSearchStatus
from app.realtime_policy.tool import OfficialRealtimePolicySearchTool

logger = logging.getLogger("uvicorn.error")


class RealtimePolicySearchNode:
    def __init__(self, tool: OfficialRealtimePolicySearchTool, *, enabled: bool = False):
        self.tool = tool
        self.enabled = enabled

    async def execute(self, state: GovernmentAgentState, *, force: bool = False, query: str | None = None) -> GovernmentAgentState:
        started = perf_counter()
        intent = FreshnessIntentDetector.detect(state.userMessage)
        state.realtimePolicyHits = []
        state.realtimeSearchStatus = RealtimeSearchStatus.NOT_TRIGGERED
        should_search = force or intent.requiresRealtimeSearch
        if should_search:
            state.realtimeSearchStatus = RealtimeSearchStatus.DISABLED
            if self.enabled:
                try:
                    state.realtimeSearchStatus, state.realtimePolicyHits = await self.tool.search(
                        state.userProfile,
                        state.userMessage,
                        intent.reason or '官方政策信息查询',
                        search_query=query,
                    )
                except Exception:
                    state.realtimeSearchStatus = RealtimeSearchStatus.ERROR
        state.realtimeSearchMs = (perf_counter() - started) * 1000
        logger.info('realtime_policy_search triggered=%s provider=%s status=%s result_count=%d realtime_search_ms=%d', should_search, type(self.tool.provider).__name__, state.realtimeSearchStatus.value, len(state.realtimePolicyHits), state.realtimeSearchMs)
        return state
