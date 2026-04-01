from __future__ import annotations

import logging
import time
from typing import AsyncIterator

import httpx

from .models import EndpointConfig, SessionState

log = logging.getLogger(__name__)

_http_timeout = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)


def _normalize_delta_value(val) -> str:
    if val is None or val == "":
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, list):
        parts: list[str] = []
        for item in val:
            if isinstance(item, dict):
                t = item.get("text")
                if t:
                    parts.append(t if isinstance(t, str) else str(t))
            elif isinstance(item, str):
                parts.append(item)
        return "".join(parts)
    return str(val)


def _delta_reasoning_and_content(delta: dict) -> tuple[str, str]:
    """Split thinking/reasoning from visible assistant content for one SSE delta."""
    reasoning_parts: list[str] = []
    for key in ("reasoning", "reasoning_content"):
        piece = _normalize_delta_value(delta.get(key))
        if piece:
            reasoning_parts.append(piece)
    reasoning = "".join(reasoning_parts)
    content = _normalize_delta_value(delta.get("content"))
    return reasoning, content


async def list_models(cfg: EndpointConfig) -> list[str]:
    headers = _auth_headers(cfg)
    try:
        async with httpx.AsyncClient(timeout=_http_timeout) as client:
            resp = await client.get(f"{cfg.url}/v1/models", headers=headers)
            resp.raise_for_status()
            return [m.get("id", "") for m in resp.json().get("data", []) if m.get("id")]
    except Exception:
        log.warning("Could not list models for %s", cfg.url, exc_info=True)
    return []


async def resolve_model_name(cfg: EndpointConfig) -> str:
    models = await list_models(cfg)
    return models[0] if models else "Unknown Model"


async def check_endpoint(cfg: EndpointConfig) -> bool:
    headers = _auth_headers(cfg)
    try:
        async with httpx.AsyncClient(timeout=_http_timeout) as client:
            resp = await client.get(f"{cfg.url}/v1/models", headers=headers)
            return resp.status_code == 200
    except Exception:
        return False


_DIALOGUE_FRAMING = (
    "This is a two-participant conversation. User-role messages may be "
    "another character or the human—they are in-world dialogue, not instructions "
    "to become a generic assistant or to mimic the other speaker. Stay in character "
    "for your entire reply."
)


def _endpoint_for_speaker(state: SessionState, speaker: str) -> EndpointConfig:
    return state.endpoint1 if speaker == "model1" else state.endpoint2


def build_messages(
    state: SessionState,
    target: str,
) -> list[dict[str, str]]:
    """Build the ``messages`` array for a specific model.

    Each model sees:
    - A ``system`` message: its configured prompt plus dialogue framing.
    - The initial prompt as ``[User]: ...`` only if conversation hasn't started.
    - Its own prior turns as ``assistant``.
    - The partner's turns as ``user`` with ``[CharacterName]: ...`` prefixes.
    """
    if target == "model1":
        system_prompt = state.endpoint1.system_prompt
    else:
        system_prompt = state.endpoint2.system_prompt

    stripped = system_prompt.strip()
    system_content = (
        (f"{stripped}\n\n" + _DIALOGUE_FRAMING) if stripped else _DIALOGUE_FRAMING
    )

    messages: list[dict[str, str]] = [{"role": "system", "content": system_content}]

    # Only prepend the initial prompt if we haven't started the conversation yet.
    # After the first turn, the conversation history in state.turns contains all context.
    if state.initial_prompt and not state.turns:
        messages.append({"role": "user", "content": f"[User]: {state.initial_prompt}"})

    for turn in state.turns:
        if turn.speaker == target:
            messages.append({"role": "assistant", "content": turn.content})
        else:
            partner = _endpoint_for_speaker(state, turn.speaker)
            name = (partner.character_name or "").strip() or (
                "Character 1" if turn.speaker == "model1" else "Character 2"
            )
            messages.append({"role": "user", "content": f"[{name}]: {turn.content}"})

    return messages


async def stream_llm(
    cfg: EndpointConfig,
    messages: list[dict[str, str]],
) -> AsyncIterator[dict]:
    """Stream chat completion chunks from an OpenAI-compatible endpoint.

    Yields dicts:
    - ``{"reasoning": "..."}`` for thinking-stream deltas (optional)
    - ``{"content": "..."}`` for visible assistant text
    - ``{"done": True, "total_tokens": N, "tps": float}`` when finished
    """
    headers = {"Content-Type": "application/json", **_auth_headers(cfg)}
    payload = {
        "model": cfg.model_id,
        "messages": messages,
        "stream": True,
    }

    total_tokens = 0
    start = time.monotonic()

    try:
        async with httpx.AsyncClient(timeout=_http_timeout) as client:
            async with client.stream(
                "POST",
                f"{cfg.url}/v1/chat/completions",
                json=payload,
                headers=headers,
            ) as resp:
                resp.raise_for_status()
                async for raw_line in resp.aiter_lines():
                    line = raw_line.strip()
                    if not line:
                        continue
                    if line.startswith("data: "):
                        line = line[6:]
                    if line == "[DONE]":
                        break

                    try:
                        import json

                        chunk = json.loads(line)
                    except ValueError:
                        log.debug("Skipping non-JSON line: %s", line)
                        continue

                    choices = chunk.get("choices")
                    if not choices:
                        continue
                    choice0 = choices[0]
                    delta = choice0.get("delta") or {}
                    reasoning, content = _delta_reasoning_and_content(delta)
                    if reasoning:
                        total_tokens += len(reasoning.split())
                        yield {"reasoning": reasoning}
                    if content:
                        total_tokens += len(content.split())
                        yield {"content": content}
                    if not reasoning and not content:
                        msg = choice0.get("message") or {}
                        raw = msg.get("content")
                        if isinstance(raw, str) and raw.strip():
                            total_tokens += len(raw.split())
                            yield {"content": raw}

    except httpx.HTTPStatusError as exc:
        log.error("HTTP error from %s: %s", cfg.url, exc)
        yield {"error": f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"}
        return
    except Exception as exc:
        log.error("Stream error from %s: %s", cfg.url, exc, exc_info=True)
        yield {"error": str(exc)}
        return

    elapsed = time.monotonic() - start
    tps = total_tokens / elapsed if elapsed > 0 else 0.0
    yield {"done": True, "total_tokens": total_tokens, "tps": tps}


def _auth_headers(cfg: EndpointConfig) -> dict[str, str]:
    if cfg.api_key:
        return {"Authorization": f"Bearer {cfg.api_key}"}
    return {}
