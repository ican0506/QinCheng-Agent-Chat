from __future__ import annotations

import asyncio
from collections import OrderedDict
from dataclasses import dataclass, field

from app.core.errors import InvalidRequestError
from app.services.llm.base import LLMMessage


@dataclass
class SessionRecord:
    user_id: str
    messages: list[LLMMessage] = field(default_factory=list)
    material_declarations: dict[str, bool] = field(default_factory=dict)


class InMemorySessionStore:
    """Phase 1 conversation store. Replace behind this interface when persistence is needed."""

    def __init__(self, history_limit: int = 40, session_limit: int = 1000) -> None:
        self._history_limit = history_limit
        self._session_limit = session_limit
        self._sessions: OrderedDict[str, SessionRecord] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get_messages(self, session_id: str, user_id: str) -> list[LLMMessage]:
        async with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                return []
            if record.user_id != user_id:
                raise InvalidRequestError("sessionId 与 userId 不匹配")
            self._sessions.move_to_end(session_id)
            return [message.copy() for message in record.messages]

    async def append_exchange(
        self, session_id: str, user_id: str, user_message: str, assistant_message: str
    ) -> None:
        async with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                record = SessionRecord(user_id=user_id)
                self._sessions[session_id] = record
            elif record.user_id != user_id:
                raise InvalidRequestError("sessionId 与 userId 不匹配")

            record.messages.extend(
                [
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": assistant_message},
                ]
            )
            record.messages = record.messages[-self._history_limit :]
            self._sessions.move_to_end(session_id)

            while len(self._sessions) > self._session_limit:
                self._sessions.popitem(last=False)

    async def get_material_declarations(self, session_id: str, user_id: str) -> dict[str, bool]:
        async with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                return {}
            if record.user_id != user_id:
                raise InvalidRequestError("sessionId 与 userId 不匹配")
            return dict(record.material_declarations)

    async def set_material_declarations(self, session_id: str, user_id: str, declarations: dict[str, bool]) -> None:
        async with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                record = SessionRecord(user_id=user_id)
                self._sessions[session_id] = record
            elif record.user_id != user_id:
                raise InvalidRequestError("sessionId 与 userId 不匹配")
            record.material_declarations = dict(declarations)
