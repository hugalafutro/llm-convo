from __future__ import annotations

import logging
import time
from typing import AsyncIterator

import httpx

from .models import EndpointConfig, SessionState, Turn

log = logging.getLogger(__name__)

_http_timeout = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)


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


def build_messages(
    state: SessionState,
    target: str,
) -> list[dict[str, str]]:
    """Build the ``messages`` array for a specific model.

    Each model sees:
    - Its own system prompt as the ``system`` message.
    - The initial user prompt as the first ``user`` message.
    - Its own prior turns as ``assistant``.
    - The partner's turns as ``user``.
    """
    if target == "model1":
        system_prompt = state.endpoint1.system_prompt
    else:
        system_prompt = state.endpoint2.system_prompt

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": state.initial_prompt})

    for turn in state.turns:
        role = "assistant" if turn.speaker == target else "user"
        messages.append({"role": role, "content": turn.content})

    return messages


async def stream_llm(
    cfg: EndpointConfig,
    messages: list[dict[str, str]],
) -> AsyncIterator[dict]:
    """Stream chat completion chunks from an OpenAI-compatible endpoint.

    Yields dicts of two kinds:
    - ``{"content": "..."}`` for each text delta
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
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content") or ""
                    if content:
                        total_tokens += len(content.split())
                        yield {"content": content}

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
