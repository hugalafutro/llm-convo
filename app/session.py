from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import Request, Response

from .models import SessionState

if TYPE_CHECKING:
    pass

SESSION_COOKIE = "llm_convo_session"

_store: dict[str, SessionState] = {}


def get_or_create_session(request: Request, response: Response) -> tuple[str, SessionState]:
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id and session_id in _store:
        return session_id, _store[session_id]

    session_id = uuid.uuid4().hex
    state = SessionState()
    _store[session_id] = state
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24,
    )
    return session_id, state


def get_session(request: Request) -> SessionState | None:
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id:
        return _store.get(session_id)
    return None


def session_count() -> int:
    return len(_store)
