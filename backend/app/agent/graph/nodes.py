"""将既有业务节点适配为 LangGraph 节点。"""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.agent.models import AgentStage, GovernmentAgentState, SuggestedAction
from app.agent.nodes.eligibility import EligibilityNode
from app.agent.nodes.material_check import MaterialCheckNode
from app.agent.nodes.plan import PlanNode
from app.agent.nodes.policy_compare import PolicyCompareNode
from app.agent.nodes.policy_search import PolicySearchNode
from app.agent.nodes.profile import ProfileNode
from app.agent.nodes.realtime_policy_search import RealtimePolicySearchNode
from app.agent.presentation import PresentationAdapter
from app.policy.models import ApplicationStatus, ValidityStatus
from app.policy.repository import PolicyRepository
from app.services.policy_query_context import GoalResolver, RouteDecider, UserGoal

GraphNode = Callable[[GovernmentAgentState], Awaitable[GovernmentAgentState]]


class GraphNodeAdapter:
    """请求作用域适配器；所有节点均以 state 入、state 出。"""

    def __init__(
        self,
        *,
        profile: ProfileNode,
        policy_search: PolicySearchNode,
        eligibility: EligibilityNode,
        policy_compare: PolicyCompareNode,
        material: MaterialCheckNode | None,
        plan: PlanNode,
        realtime: RealtimePolicySearchNode | None,
        repository: PolicyRepository | None,
    ) -> None:
        self._profile = profile
        self._policy_search = policy_search
        self._eligibility = eligibility
        self._policy_compare = policy_compare
        self._material = material
        self._plan = plan
        self._realtime = realtime
        self._repository = repository

    async def resolve_goal(self, state: GovernmentAgentState) -> GovernmentAgentState:
        detected = state.requestedGoal or GoalResolver.resolve(state.userMessage, state.activeGoal)
        effective = (
            state.activeGoal
            if detected in {UserGoal.FOLLOW_UP_REPLY, UserGoal.PROFILE_UPDATE}
            and state.activeGoal is not None
            else detected
        )
        state.userGoal = effective
        state.activeGoal = effective
        state.routeDecision = RouteDecider.decide(detected, previous_goal=state.activeGoal)
        state.applicationGuide = effective is UserGoal.APPLICATION_GUIDE
        return state

    async def merge_profile(self, state: GovernmentAgentState) -> GovernmentAgentState:
        # ChatService 在进入图前完成请求/会话画像的确定性合并；该节点只消费
        # 合并后的 canonical profile，统一初始化本轮画像相关状态。
        return await self._profile.execute(state)

    async def official_search(self, state: GovernmentAgentState) -> GovernmentAgentState:
        if self._realtime is not None:
            return await self._realtime.execute(state, force=True)
        return state

    async def policy_search(self, state: GovernmentAgentState) -> GovernmentAgentState:
        return await self._policy_search.execute(state)

    async def required_fields(self, state: GovernmentAgentState) -> GovernmentAgentState:
        # 具体缺失字段只能由结构化资格规则产生；这里是显式图阶段，避免
        # 在路由器或 Presentation 中提前猜测字段。
        state.requiredFieldsForCurrentGoal = []
        return state

    async def eligibility(self, state: GovernmentAgentState) -> GovernmentAgentState:
        return await self._eligibility.execute(state)

    async def policy_compare(self, state: GovernmentAgentState) -> GovernmentAgentState:
        return await self._policy_compare.execute(state)

    async def material(self, state: GovernmentAgentState) -> GovernmentAgentState:
        if self._material is not None:
            return await self._material.execute(state)
        return state

    async def plan(self, state: GovernmentAgentState) -> GovernmentAgentState:
        return await self._plan.execute(state)

    async def presentation(self, state: GovernmentAgentState) -> GovernmentAgentState:
        self._add_policy_reference_notices(state)
        state.suggestedActions = self._suggested_actions(state)
        state.finalReply = PresentationAdapter.fallback_reply(state)
        state.stage = AgentStage.COMPLETED
        return state

    def _add_policy_reference_notices(self, state: GovernmentAgentState) -> None:
        if self._repository is None:
            return
        for candidate in state.candidatePolicies:
            record = self._repository.get_by_id(candidate.policyId)
            if record is None:
                continue
            historical = record.validityStatus in {ValidityStatus.HISTORICAL, ValidityStatus.EXPIRED}
            closed = record.applicationStatus is ApplicationStatus.CLOSED
            if historical and closed:
                notice = "该记录为历史申报通知，申报窗口已结束。请关注苏州市人社部门后续发布的最新年度申报安排。"
            elif historical:
                notice = "该记录为历史政策依据，不能直接作为当前申请依据。请关注苏州市人社部门后续发布的最新年度申报安排。"
            elif closed:
                notice = "该政策当前申报窗口已结束。请关注苏州市人社部门后续发布的最新年度申报安排。"
            else:
                continue
            state.policyReferenceNotices[candidate.policyId] = notice

    @staticmethod
    def _suggested_actions(state: GovernmentAgentState) -> list[SuggestedAction]:
        if state.userGoal is UserGoal.JOB_SEARCH:
            return [
                SuggestedAction(label="看看就业见习", prompt="就业见习适合哪些毕业生？"),
                SuggestedAction(label="看看毕业生就业支持", prompt="毕业生现在有什么就业支持？"),
                SuggestedAction(label="了解可能符合的补贴", prompt="我可能符合哪些就业补贴？"),
            ]
        if state.userGoal is UserGoal.POLICY_DISCOVERY:
            return [
                SuggestedAction(label="了解就业见习", prompt="就业见习适合哪些毕业生？"),
                SuggestedAction(label="判断我是否符合", prompt="我符合这项政策吗？"),
            ]
        if state.userGoal is UserGoal.POLICY_FACT:
            return [
                SuggestedAction(label="看看办理流程", prompt="这个政策怎么办理？"),
                SuggestedAction(label="判断我是否符合", prompt="我符合这项政策吗？"),
            ]
        if state.userGoal is UserGoal.ELIGIBILITY_CHECK:
            return [SuggestedAction(label="在右侧完善画像", prompt="我想补充个人情况")]
        if state.userGoal is UserGoal.APPLICATION_GUIDE:
            return [SuggestedAction(label="判断我是否符合", prompt="我符合这项政策吗？")]
        return []
