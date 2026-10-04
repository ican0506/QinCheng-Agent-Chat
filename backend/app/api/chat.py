from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import StreamingResponse

from app.core.errors import AppError
from app.models.chat import ApiResponse, ChatData, ChatRequest, SessionProfileUpdateRequest

router = APIRouter(prefix="/api", tags=["Chat"])
logger = logging.getLogger(__name__)


def resolve_trace_id(value: str | None) -> str:
    if value:
        cleaned = value.strip()[:128]
        if cleaned:
            return cleaned
    return uuid.uuid4().hex


def sse_event(event: str, payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {data}\n\n"


@router.post("/agent/chat", response_model=ApiResponse[ChatData])
async def chat(
    payload: ChatRequest,
    request: Request,
    x_trace_id: str | None = Header(default=None, alias="X-Trace-Id"),
) -> ApiResponse[ChatData]:
    trace_id = resolve_trace_id(x_trace_id)
    request.state.trace_id = trace_id
    data = await request.app.state.chat_service.chat(payload, trace_id=trace_id)
    return ApiResponse(code=0, message="success", traceId=trace_id, data=data)


@router.post("/agent/chat/stream")
async def stream_chat(
    payload: ChatRequest,
    request: Request,
    x_trace_id: str | None = Header(default=None, alias="X-Trace-Id"),
) -> StreamingResponse:
    trace_id = resolve_trace_id(x_trace_id)
    request.state.trace_id = trace_id

    async def events() -> AsyncIterator[str]:
        try:
            async for item in request.app.state.chat_service.stream_chat(payload, trace_id=trace_id):
                if item.kind == "delta":
                    yield sse_event("delta", {"text": item.text})
                elif item.data is not None:
                    response = ApiResponse[ChatData](
                        code=0,
                        message="success",
                        traceId=trace_id,
                        data=item.data,
                    )
                    yield sse_event("done", response.model_dump(mode="json"))
        except AppError as exc:
            response = ApiResponse[dict](
                code=exc.code,
                message=exc.message,
                traceId=trace_id,
                data=None,
            )
            yield sse_event("error", response.model_dump(mode="json"))
        except Exception:
            logger.exception("Unhandled streaming error traceId=%s", trace_id)
            response = ApiResponse[dict](
                code=5001,
                message="服务暂时不可用，请稍后重试",
                traceId=trace_id,
                data=None,
            )
            yield sse_event("error", response.model_dump(mode="json"))

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.put("/agent/sessions/{session_id}/profile", response_model=ApiResponse[ChatData])
async def update_session_profile(
    session_id: str,
    payload: SessionProfileUpdateRequest,
    request: Request,
    x_trace_id: str | None = Header(default=None, alias="X-Trace-Id"),
) -> ApiResponse[ChatData]:
    trace_id = resolve_trace_id(x_trace_id)
    request.state.trace_id = trace_id
    data = await request.app.state.chat_service.update_session_profile(
        session_id, payload.userId, payload.profile
    )
    return ApiResponse(code=0, message="success", traceId=trace_id, data=data)


@router.delete("/agent/sessions/{session_id}", response_model=ApiResponse[dict[str, bool]])
async def delete_session(
    session_id: str,
    request: Request,
    user_id: str = Query(alias="userId", min_length=1, max_length=128),
    x_trace_id: str | None = Header(default=None, alias="X-Trace-Id"),
) -> ApiResponse[dict[str, bool]]:
    trace_id = resolve_trace_id(x_trace_id)
    request.state.trace_id = trace_id
    deleted = await request.app.state.chat_service.delete_session(session_id, user_id)
    return ApiResponse(code=0, message="success", traceId=trace_id, data={"deleted": deleted})


@router.get("/health")
async def health(request: Request) -> dict:
    settings = request.app.state.settings
    provider = request.app.state.llm_provider
    return {
        "status": "ok",
        "module": "chat",
        "llmConfigured": settings.llm_configured,
        "provider": provider.name,
        "model": settings.llm_model,
    }
