from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import AsyncIterator

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse

from . import BASE_DIR
from .models import ConnectRequest, SetModelRequest, Turn
from .services import build_messages, check_endpoint, list_models, stream_llm
from .session import get_or_create_session, get_session, session_count

log = logging.getLogger(__name__)
templates = Jinja2Templates(directory=BASE_DIR / "templates")

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@router.post("/connect")
async def connect(body: ConnectRequest, request: Request, response: Response):
    _sid, state = get_or_create_session(request, response)

    cfg = state.endpoint1 if body.endpoint_num == 1 else state.endpoint2
    cfg.url = body.endpoint_url.rstrip("/")
    cfg.system_prompt = body.system_prompt
    cfg.api_key = body.api_key
    cfg.character_name = body.character_name or f"Character {body.endpoint_num}"

    reachable = await check_endpoint(cfg)
    if not reachable:
        return {
            "status": "error",
            "message": f"Failed to connect to Endpoint {body.endpoint_num}",
        }

    models = await list_models(cfg)

    # Check for previously saved model preference for this API URL
    saved_model = cfg.last_model_per_api.get(body.endpoint_url.rstrip("/"))
    if saved_model and saved_model in models:
        cfg.model_id = saved_model
    else:
        cfg.model_id = models[0] if models else "Unknown Model"
    log.info(
        "Endpoint %d connected: %s (model: %s)",
        body.endpoint_num,
        cfg.url,
        cfg.model_id,
    )
    return {
        "status": "success",
        "message": f"Connected to Endpoint {body.endpoint_num}",
        "model": cfg.model_id,
        "models": models,
        "saved_model": cfg.last_model_per_api.get(body.endpoint_url.rstrip("/"), ""),
    }


@router.get("/chat")
async def chat(request: Request):
    """SSE endpoint for the conversation stream.

    Query params: prompt, num_exchanges
    Uses GET so the browser can use EventSource natively.
    """
    state = get_session(request)
    if state is None:
        return Response("Session not found", status_code=400)

    prompt = request.query_params.get("prompt", "")
    try:
        num_exchanges = int(request.query_params.get("num_exchanges", "3"))
    except (TypeError, ValueError):
        return Response("Invalid num_exchanges value", status_code=400)
    if not 1 <= num_exchanges <= 30:
        return Response("num_exchanges must be between 1 and 30", status_code=400)
    starting_speaker = request.query_params.get("starting_speaker", "")

    if not state.endpoint1.url or not state.endpoint2.url:
        return Response("Connect both endpoints first", status_code=400)

    state.turns.clear()
    state.initial_prompt = ""
    state.initial_speaker = (
        starting_speaker if starting_speaker in {"model1", "model2"} else ""
    )
    if prompt:
        if state.initial_speaker:
            state.turns.append(Turn(speaker=state.initial_speaker, content=prompt))
        else:
            state.initial_prompt = prompt

    async def event_stream() -> AsyncIterator[dict]:
        turn_order = (
            [("model2", state.endpoint2), ("model1", state.endpoint1)]
            if state.initial_speaker in {"", "model1"}
            else [("model1", state.endpoint1), ("model2", state.endpoint2)]
        )
        for _ in range(num_exchanges):
            if await request.is_disconnected():
                break

            for target, cfg in turn_order:
                sender = cfg.character_name or f"Model {target[-1]}"
                ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

                yield {
                    "event": "sender",
                    "data": json.dumps(
                        {
                            "sender": sender,
                            "speaker": target,
                            "timestamp": ts,
                            "model": cfg.model_id,
                        }
                    ),
                }

                messages = build_messages(state, target)

                full_response = ""
                error_occurred = False

                async for chunk in stream_llm(cfg, messages):
                    if await request.is_disconnected():
                        return

                    if "reasoning" in chunk:
                        yield {
                            "event": "reasoning",
                            "data": json.dumps({"reasoning": chunk["reasoning"]}),
                        }
                    elif "content" in chunk:
                        full_response += chunk["content"]
                        yield {
                            "event": "content",
                            "data": json.dumps({"content": chunk["content"]}),
                        }
                    elif "error" in chunk:
                        yield {
                            "event": "error",
                            "data": json.dumps({"error": chunk["error"]}),
                        }
                        error_occurred = True
                    elif "done" in chunk:
                        yield {
                            "event": "end",
                            "data": json.dumps(
                                {
                                    "end": True,
                                    "timestamp": datetime.now(timezone.utc).strftime(
                                        "%Y-%m-%d %H:%M:%S"
                                    ),
                                    "model": cfg.model_id,
                                    "total_tokens": chunk["total_tokens"],
                                    "tps": chunk["tps"],
                                }
                            ),
                        }

                if full_response and not error_occurred:
                    state.turns.append(Turn(speaker=target, content=full_response))

        yield {"event": "done", "data": json.dumps({"conversation_done": True})}

    return EventSourceResponse(event_stream())


@router.post("/set-model")
async def set_model(body: SetModelRequest, request: Request):
    state = get_session(request)
    if state is None:
        return Response("Session not found", status_code=400)
    cfg = state.endpoint1 if body.endpoint_num == 1 else state.endpoint2
    cfg.model_id = body.model_id
    # Remember the model preference for this API URL
    if cfg.url:
        cfg.last_model_per_api[cfg.url.rstrip("/")] = body.model_id
    return {"status": "ok", "model": cfg.model_id}


@router.post("/clear")
async def clear(request: Request):
    state = get_session(request)
    if state:
        state.turns.clear()
        state.initial_prompt = ""
        state.initial_speaker = ""
    return {"status": "ok"}


@router.post("/generate-starter")
async def generate_starter(request: Request, response: Response):
    """Generate a conversation starter based on the endpoint's character and prompt."""
    state = get_session(request)
    if state is None:
        return Response("Session not found", status_code=400)

    try:
        body = await request.json()
        endpoint_num = body.get("endpoint_num")
        previous_starter = str(body.get("previous_starter") or "").strip()
    except Exception:
        return Response("Invalid request body", status_code=400)

    if endpoint_num not in (1, 2):
        return Response("Invalid endpoint number", status_code=400)

    cfg = state.endpoint1 if endpoint_num == 1 else state.endpoint2

    if not cfg.url:
        return Response("Endpoint not connected", status_code=400)

    character_name = cfg.character_name or f"Character {endpoint_num}"

    starter_system = f"""{cfg.system_prompt}

You are tasked with generating a short 1-2 sentence conversation starter for the character "{character_name}".
Generate an engaging, in-character opening line that would naturally start a conversation.
Respond with ONLY the conversation starter text, nothing else."""

    if previous_starter:
        starter_system += f"""

The user already has this conversation starter:
{previous_starter}

Generate a distinctly different alternative, not a rewording of the same idea."""

    async def request_starter(user_content: str) -> str | Response:
        messages = [
            {"role": "system", "content": starter_system},
            {"role": "user", "content": user_content},
        ]

        full_response = ""
        async for chunk in stream_llm(cfg, messages):
            if "content" in chunk:
                full_response += chunk["content"]
            elif "error" in chunk:
                return Response(chunk["error"], status_code=500)
        return full_response.strip()

    starter = await request_starter(
        (
            f"Generate a new conversation starter for character: {character_name}"
            if previous_starter
            else f"Generate a conversation starter for character: {character_name}"
        )
    )
    if isinstance(starter, Response):
        return starter

    if previous_starter and starter == previous_starter:
        retry_prompt = (
            f'Generate a clearly different conversation starter for character: {character_name}. '
            "Do not reuse the same opening idea, wording, or setup as the previous starter."
        )
        retry_starter = await request_starter(retry_prompt)
        if isinstance(retry_starter, Response):
            return retry_starter
        starter = retry_starter

    return {"starter": starter}


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "sessions": session_count(),
        "uptime_s": time.monotonic(),
    }
