from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.agent.workflow import WorkflowAgent
from app.agent.nodes.realtime_policy_search import RealtimePolicySearchNode
from app.realtime_policy.provider import RealtimeSearchProvider, DisabledRealtimeSearchProvider
from app.realtime_policy.tavily import TavilyRealtimeSearchProvider
from app.realtime_policy.tool import OfficialRealtimePolicySearchTool
from app.agent.tools.local_policy import LocalPolicySearchTool
from app.agent.tools.rag_policy import RagPolicySearchTool
from app.agent.tools.dify_policy import DifyPolicySearchTool
from app.agent.tools.dify_policy_sources import DifyPolicySourceCatalog
from app.agent.tools.plan import DeterministicPlanTool
from app.agent.tools.policy_compare import DeterministicPolicyCompareTool
from app.api.chat import router as chat_router
from app.core.config import Settings
from app.core.errors import AppError
from app.models.chat import ApiResponse
from app.policy.repository import PolicyRepository
from app.policy.relations import PolicyRelationRepository
from app.rag.chunker import MarkdownPolicyChunker
from app.rag.loader import RagDocumentLoader
from app.rag.retriever import InMemoryRagRetriever
from app.services.chat_service import ChatService
from app.services.llm_profile_extractor import LLMProfileExtractor
from app.services.llm.base import LLMProvider, UnavailableLLMProvider
from app.services.llm.openai_compatible import OpenAICompatibleProvider
from app.stores.session_store import InMemorySessionStore

logger = logging.getLogger(__name__)


def _build_realtime_provider(settings: Settings) -> RealtimeSearchProvider:
    if not settings.realtime_policy_search_enabled:
        return DisabledRealtimeSearchProvider()
    provider_name = settings.realtime_policy_search_provider.strip().lower()
    if provider_name != "tavily":
        raise ValueError(
            f"Unsupported realtime policy search provider: {provider_name or '<empty>'}"
        )
    if not settings.realtime_policy_search_api_key.strip():
        logger.warning("realtime search enabled but API key missing provider=tavily")
        return DisabledRealtimeSearchProvider()
    return TavilyRealtimeSearchProvider(
        api_key=settings.realtime_policy_search_api_key,
        timeout_seconds=settings.realtime_policy_search_timeout_seconds,
    )


def _trace_id(request: Request) -> str:
    return getattr(request.state, "trace_id", None) or request.headers.get(
        "X-Trace-Id"
    ) or uuid.uuid4().hex


def create_app(
    settings: Settings | None = None,
    provider: LLMProvider | None = None,
    realtime_provider: RealtimeSearchProvider | None = None,
) -> FastAPI:
    active_settings = settings or Settings.from_env()
    active_provider = provider
    if active_provider is None:
        active_provider = (
            OpenAICompatibleProvider(active_settings)
            if active_settings.llm_configured
            else UnavailableLLMProvider()
        )

    store = InMemorySessionStore(
        history_limit=active_settings.session_history_limit,
        session_limit=active_settings.session_limit,
    )
    backend_root = Path(__file__).resolve().parents[1]
    policy_repository = PolicyRepository(backend_root / "data" / "policies" / "policies.json")
    local_policy_search = LocalPolicySearchTool(policy_repository)
    try:
        documents = RagDocumentLoader(
            policy_repository, backend_root / "data" / "policies" / "raw"
        ).load()
        rag_retriever: InMemoryRagRetriever | None = InMemoryRagRetriever(
            MarkdownPolicyChunker().chunk_documents(documents)
        )
    except Exception:
        logger.exception("Local policy knowledge base is unavailable; using structured search fallback")
        rag_retriever = None
    rag_policy_search = RagPolicySearchTool(
        rag_retriever, policy_repository, local_policy_search
    )
    policy_search_tool = DifyPolicySearchTool(
        enabled=active_settings.dify_knowledge_enabled,
        base_url=active_settings.dify_base_url,
        dataset_id=active_settings.dify_dataset_id,
        api_key=active_settings.dify_dataset_api_key,
        timeout_seconds=active_settings.dify_knowledge_timeout_seconds,
        top_k=active_settings.dify_knowledge_top_k,
        repository=policy_repository,
        fallback=rag_policy_search,
        source_catalog=DifyPolicySourceCatalog.from_path(
            backend_root / "data" / "dify_policy_sources.json"
        ),
    )
    policy_relation_repository = PolicyRelationRepository(
        backend_root / "data" / "policies" / "policy_relations.json"
    )
    active_realtime_provider = (
        realtime_provider
        if realtime_provider is not None
        else _build_realtime_provider(active_settings)
    )
    workflow_agent = WorkflowAgent.production(
        policy_repository,
        policy_search_tool,
        DeterministicPolicyCompareTool(policy_repository, policy_relation_repository),
        DeterministicPlanTool(policy_repository),
        RealtimePolicySearchNode(OfficialRealtimePolicySearchTool(
            active_realtime_provider,
            policy_repository, list(active_settings.realtime_policy_allowed_domains),
            timeout_seconds=active_settings.realtime_policy_search_timeout_seconds,
            max_results=active_settings.realtime_policy_search_max_results,
        ), enabled=active_settings.realtime_policy_search_enabled),
    )
    application = FastAPI(
        title="应届毕业生就业创业政策 Agent - Chat 模块",
        version="1.0.0",
    )
    application.state.settings = active_settings
    application.state.llm_provider = active_provider
    application.state.policy_repository = policy_repository
    application.state.policy_relation_repository = policy_relation_repository
    application.state.rag_retriever = rag_retriever
    application.state.policy_search_tool = policy_search_tool
    application.state.realtime_search_provider = active_realtime_provider
    application.state.workflow_agent = workflow_agent
    profile_extractor = (
        LLMProfileExtractor(active_provider, active_settings.profile_extraction_timeout_seconds)
        if active_settings.profile_extraction_enabled and active_settings.llm_configured
        else None
    )
    application.state.chat_service = ChatService(
        active_provider,
        store,
        workflow_agent,
        profile_extractor,
        policy_repository=policy_repository,
        final_explanation_timeout_seconds=active_settings.final_explanation_timeout_seconds,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(active_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Trace-Id"],
    )

    @application.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        response = ApiResponse[dict](
            code=exc.code,
            message=exc.message,
            traceId=_trace_id(request),
            data=None,
        )
        return JSONResponse(status_code=exc.http_status, content=response.model_dump())

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        fields = [".".join(str(part) for part in error["loc"][1:]) for error in exc.errors()]
        field_text = "、".join(dict.fromkeys(field for field in fields if field))
        message = f"请求参数缺失或格式错误：{field_text}" if field_text else "请求参数缺失或格式错误"
        response = ApiResponse[dict](
            code=1001,
            message=message,
            traceId=_trace_id(request),
            data=None,
        )
        return JSONResponse(status_code=400, content=response.model_dump())

    @application.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        trace_id = _trace_id(request)
        logger.exception("Unhandled request error traceId=%s", trace_id)
        response = ApiResponse[dict](
            code=5001,
            message="服务暂时不可用，请稍后重试",
            traceId=trace_id,
            data=None,
        )
        return JSONResponse(status_code=500, content=response.model_dump())

    application.include_router(chat_router)

    phase_root = Path(__file__).resolve().parents[2]
    dist_dir = phase_root / "frontend" / "dist"
    if dist_dir.is_dir():
        assets_dir = dist_dir / "assets"
        application.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @application.get("/", include_in_schema=False)
        async def frontend_index() -> FileResponse:
            return FileResponse(dist_dir / "index.html")

    return application


app = create_app()
