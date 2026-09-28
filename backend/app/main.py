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
from app.agent.tools.local_policy import LocalPolicySearchTool
from app.agent.tools.rag_policy import RagPolicySearchTool
from app.api.chat import router as chat_router
from app.core.config import Settings
from app.core.errors import AppError
from app.models.chat import ApiResponse
from app.policy.repository import PolicyRepository
from app.rag.chunker import MarkdownPolicyChunker
from app.rag.loader import RagDocumentLoader
from app.rag.retriever import InMemoryRagRetriever
from app.services.chat_service import ChatService
from app.services.llm.base import LLMProvider, UnavailableLLMProvider
from app.services.llm.openai_compatible import OpenAICompatibleProvider
from app.stores.session_store import InMemorySessionStore

logger = logging.getLogger(__name__)


def _trace_id(request: Request) -> str:
    return getattr(request.state, "trace_id", None) or request.headers.get(
        "X-Trace-Id"
    ) or uuid.uuid4().hex


def create_app(
    settings: Settings | None = None,
    provider: LLMProvider | None = None,
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
    policy_search_tool = RagPolicySearchTool(
        rag_retriever, policy_repository, local_policy_search
    )
    workflow_agent = WorkflowAgent.production(policy_repository, policy_search_tool)
    application = FastAPI(
        title="应届毕业生就业创业政策 Agent - Chat 模块",
        version="1.0.0",
    )
    application.state.settings = active_settings
    application.state.llm_provider = active_provider
    application.state.policy_repository = policy_repository
    application.state.rag_retriever = rag_retriever
    application.state.workflow_agent = workflow_agent
    application.state.chat_service = ChatService(active_provider, store, workflow_agent)

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
