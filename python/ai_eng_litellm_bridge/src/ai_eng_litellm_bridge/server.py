"""HTTP server — FastAPI bridge to the multi-LLM router.

Exposes three endpoints under `127.0.0.1:<port>` (NEVER 0.0.0.0; ADR-0008):

* `POST /llm/invoke`  — main inference endpoint.
* `GET  /llm/capabilities` — capability matrix for the TS client.
* `GET  /health` — liveness probe (no auth) for the heartbeat client.

Bearer-token auth against `AI_ENGINEERING_BRIDGE_TOKEN`. Per-skill rate
limit (sliding 60s window).

Constitution alignment:

* Article III (Dual-Plane): every request is gated by deterministic auth +
  rate-limit BEFORE any LLM I/O.
* Article IV: this server is Layer 3 (BYOK) only — Layer 2 default flows
  never reach it.
* Article IX: each request emits a structured event to stdout (NDJSON) for
  the local NDJSON sink to ingest.
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import time
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .router import (
    _CAPABILITY_MATRIX,
    CapabilityMismatchError,
    PrivacyTierViolation,
    Router,
    RouterError,
    RoutingConfig,
    RoutingConfigError,
    TPMExceededError,
)

# ---------------------------------------------------------------------------
# Wire DTOs
# ---------------------------------------------------------------------------


class LLMRequest(BaseModel):
    """Mirrors `LLMRequest` from `packages/runtime/src/shared/ports/llm.ts`."""

    model_config = ConfigDict(extra="forbid")

    skill: str = Field(min_length=1, max_length=128)
    prompt: str = Field(min_length=1)
    capabilities: list[str] = Field(default_factory=list)
    privacy_tier: str = Field(default="standard")


class LLMResponseDTO(BaseModel):
    text: str
    tokens_used: int
    cost_usd: float
    provider_id: str
    model_id: str
    latency_ms: int


class HealthResponse(BaseModel):
    status: str
    version: str


# ---------------------------------------------------------------------------
# Per-skill rate limiter — independent of the global TPM cap
# ---------------------------------------------------------------------------


@dataclass
class _SkillLimiter:
    """Sliding-window counter, one bucket per skill name. Defaults to 60
    requests/minute per skill; overridable via env var
    `AI_ENGINEERING_BRIDGE_SKILL_RPM`.
    """

    rpm: int
    buckets: dict[str, deque[float]] = field(default_factory=dict)

    def admit(self, skill: str, *, now: float | None = None) -> bool:
        if self.rpm <= 0:
            return True
        ts = time.monotonic() if now is None else now
        cutoff = ts - 60.0
        bucket = self.buckets.setdefault(skill, deque())
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.rpm:
            return False
        bucket.append(ts)
        return True


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------


def _expected_token() -> str:
    token = os.environ.get("AI_ENGINEERING_BRIDGE_TOKEN", "")
    return token


async def require_bearer(authorization: str | None = Header(default=None)) -> None:
    expected = _expected_token()
    if not expected:
        # Fail-closed: if the operator hasn't set a token, refuse all auth'd
        # endpoints. The /health endpoint is exempt from this dependency.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="bridge token not configured",
        )
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
        )
    presented = authorization.removeprefix("Bearer ").strip()
    # Constant-time comparison to avoid timing attacks against the token.
    if not secrets.compare_digest(presented, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid bearer token",
        )


# ---------------------------------------------------------------------------
# Telemetry — minimal NDJSON-to-stdout
# ---------------------------------------------------------------------------


def _emit_event(event_type: str, **fields: Any) -> None:
    """Write a single NDJSON event line to stdout. The container's collector
    forwards stdout to the framework's NDJSON sink. Privacy: the prompt body
    is NEVER emitted — only sizes."""
    if os.environ.get("AI_ENGINEERING_TELEMETRY_DISABLED") == "1":
        return
    payload: dict[str, Any] = {
        "ts": time.time(),
        "type": event_type,
        **fields,
    }
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# App factory — kept as a function so tests can construct fresh apps
# ---------------------------------------------------------------------------


@dataclass
class ServerDeps:
    """Application dependencies. Tests build with a fake `Router`; production
    builds with the real one from `RoutingConfig.from_path`."""

    router: Router
    limiter: _SkillLimiter
    version: str = "3.0.0a0"


def _capabilities_payload() -> dict[str, list[str]]:
    return {model: sorted(caps) for model, caps in _CAPABILITY_MATRIX.items()}


def _error_response(exc: RouterError) -> JSONResponse:
    # Use raw codes — `status.HTTP_422_UNPROCESSABLE_ENTITY` is deprecated in
    # newer Starlette versions, but the integer is stable.
    code = 502  # bad gateway / unknown router error
    if isinstance(exc, PrivacyTierViolation | RoutingConfigError):
        code = 400
    elif isinstance(exc, CapabilityMismatchError):
        code = 422
    elif isinstance(exc, TPMExceededError):
        code = 429
    return JSONResponse(
        status_code=code,
        content={
            "error": exc.__class__.__name__,
            "message": str(exc),
            "retryable": exc.retryable,
        },
    )


def create_app(deps: ServerDeps) -> FastAPI:
    """Construct a FastAPI app bound to the given deps. Each call returns a
    fresh app — tests can build many in parallel without state leakage."""

    app = FastAPI(
        title="ai-engineering LiteLLM bridge",
        version=deps.version,
        # No public docs URL — this server is loopback-only.
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.get("/health")
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", version=deps.version)

    @app.get(
        "/llm/capabilities",
        dependencies=[Depends(require_bearer)],
    )
    async def capabilities() -> dict[str, list[str]]:
        return _capabilities_payload()

    @app.post(
        "/llm/invoke",
        response_model=LLMResponseDTO,
        dependencies=[Depends(require_bearer)],
    )
    async def invoke(req: LLMRequest) -> LLMResponseDTO:
        if not deps.limiter.admit(req.skill):
            _emit_event(
                "bridge.rate_limited",
                skill=req.skill,
                privacy_tier=req.privacy_tier,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"per-skill rate limit hit for skill={req.skill!r}",
            )
        try:
            result = deps.router.invoke(
                skill=req.skill,
                prompt=req.prompt,
                privacy_tier=req.privacy_tier,
                capabilities=tuple(req.capabilities),
            )
        except RouterError as exc:
            _emit_event(
                "bridge.invoke_failed",
                skill=req.skill,
                error=exc.__class__.__name__,
                retryable=exc.retryable,
            )
            return _error_response(exc)
        _emit_event(
            "bridge.invoke_ok",
            skill=req.skill,
            model_id=result.model_id,
            provider_id=result.provider_id,
            tokens=result.tokens_used,
            latency_ms=result.latency_ms,
            prompt_len=len(req.prompt),
        )
        return LLMResponseDTO(
            text=result.text,
            tokens_used=result.tokens_used,
            cost_usd=result.cost_usd,
            provider_id=result.provider_id,
            model_id=result.model_id,
            latency_ms=result.latency_ms,
        )

    return app


# ---------------------------------------------------------------------------
# Production entry point
# ---------------------------------------------------------------------------


def build_default_app() -> FastAPI:
    """Construct the production app from environment configuration.

    Required env:
      * `AI_ENGINEERING_ROUTING_PATH` — path to routing TOML.
      * `AI_ENGINEERING_BRIDGE_TOKEN` — bearer token (read at request time).

    Optional env:
      * `AI_ENGINEERING_LLM_TPM_LIMIT` — global TPM cap.
      * `AI_ENGINEERING_BRIDGE_SKILL_RPM` — per-skill RPM (default 60).
    """
    routing_path = os.environ.get("AI_ENGINEERING_ROUTING_PATH")
    if not routing_path:
        raise RoutingConfigError(
            "AI_ENGINEERING_ROUTING_PATH must be set to the routing TOML path",
            retryable=False,
        )
    config = RoutingConfig.from_path(routing_path)
    router = Router(config)
    rpm_raw = os.environ.get("AI_ENGINEERING_BRIDGE_SKILL_RPM", "60")
    rpm = int(rpm_raw) if rpm_raw.isdigit() else 60
    limiter = _SkillLimiter(rpm=rpm)
    return create_app(ServerDeps(router=router, limiter=limiter))


def serve(
    *,
    port: int,
    host: str = "127.0.0.1",
    routing_config_path: str | None = None,
) -> None:
    """Blocking serve. Binds 127.0.0.1 by default; refuses 0.0.0.0."""
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise RoutingConfigError(
            f"refusing to bind {host!r}; only loopback is permitted (ADR-0008)",
            retryable=False,
        )
    if routing_config_path:
        os.environ["AI_ENGINEERING_ROUTING_PATH"] = routing_config_path
    import uvicorn

    app = build_default_app()
    uvicorn.run(app, host=host, port=port, log_level="info")


__all__: Sequence[str] = (
    "LLMRequest",
    "LLMResponseDTO",
    "ServerDeps",
    "build_default_app",
    "create_app",
    "serve",
)
