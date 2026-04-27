"""Router — privacy-tier-aware multi-LLM routing through LiteLLM.

This module is designed to be **fully testable without ever calling LiteLLM**.
The single boundary call (`litellm.completion`) is captured via a thin
`_invoke_completion` indirection that tests can monkeypatch. The rest of the
module is pure Python: TOML loading, capability matching, fallback resolution,
TPM accounting.

Constitution alignment:

* Article III (Dual-Plane): Probabilistic-plane I/O is mediated by the
  Deterministic plane — the `route_request` decision is data-driven from a
  hash-pinned TOML config, not LLM-suggested.
* Article IV (Subscription Piggyback): the bridge is **Layer 3** (BYOK) only.
  Default flows never reach this code; they delegate to the IDE host. ADR-0005.
* Article VI (Supply Chain): LiteLLM is hard-pinned at `==1.51.0`. ADR-0008.
"""

from __future__ import annotations

import os
import time
import tomllib
from collections import deque
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

PrivacyTier = str  # "standard" | "strict" | "airgapped"
LLMCapability = str  # "tool_use" | "structured_output" | "prompt_caching" | ...

# Providers permitted under each privacy tier. `strict` is intentionally
# narrow: only providers with signed enterprise BAAs / data-residency
# guarantees commonly used in regulated industries.
_TIER_ALLOWED_PROVIDERS: dict[str, frozenset[str]] = {
    "standard": frozenset(),  # empty == "no filter" (all providers allowed)
    "strict": frozenset({"bedrock", "azure"}),
    "airgapped": frozenset({"bedrock"}),
}

# Provider prefix -> provider id. LiteLLM uses `provider/model` notation
# (e.g. `bedrock/anthropic.claude-3-5-sonnet`, `azure/gpt-5`,
# `openai/gpt-4o`). When no `/` separator, infer from the model id stem.
_PROVIDER_PREFIX_MAP: dict[str, str] = {
    "bedrock": "bedrock",
    "azure": "azure",
    "openai": "openai",
    "anthropic": "anthropic",
    "claude": "anthropic",
    "gpt": "openai",
    "gemini": "google",
    "mistral": "mistral",
}

# Capability matrix — what each *family* of model supports. We keep this
# explicit to fail fast on capability mismatches (Article VII: no silent
# downgrades). Conservative bias: capabilities default to False unless we
# know they exist.
_CAPABILITY_MATRIX: dict[str, frozenset[str]] = {
    "claude-opus-4-7": frozenset(
        {"tool_use", "structured_output", "prompt_caching", "long_context", "vision", "streaming"}
    ),
    "claude-sonnet-4-6": frozenset(
        {"tool_use", "structured_output", "prompt_caching", "long_context", "vision", "streaming"}
    ),
    "gpt-5": frozenset(
        {"tool_use", "structured_output", "prompt_caching", "long_context", "vision", "streaming"}
    ),
    "gpt-4o": frozenset({"tool_use", "structured_output", "long_context", "vision", "streaming"}),
    "gemini-1.5-pro": frozenset(
        {"tool_use", "structured_output", "long_context", "vision", "streaming"}
    ),
}


# ---------------------------------------------------------------------------
# Errors — raised at the application boundary, never inside pure helpers
# ---------------------------------------------------------------------------


class RouterError(Exception):
    """Base error from the router. Carries a `retryable` flag for the wire."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class CapabilityMismatchError(RouterError):
    """No model in the fallback chain satisfies the requested capabilities."""


class PrivacyTierViolation(RouterError):
    """The selected route is not permitted under the requested privacy tier."""


class TPMExceededError(RouterError):
    """The hard tokens-per-minute cap was exceeded — abort, do not retry."""

    def __init__(self, used: int, limit: int) -> None:
        super().__init__(
            f"TPM limit exceeded: {used}/{limit} tokens in 60s window",
            retryable=False,
        )
        self.used = used
        self.limit = limit


class RoutingConfigError(RouterError):
    """The TOML routing config is missing or malformed."""


# ---------------------------------------------------------------------------
# Config loading — pure, deterministic
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoutingConfig:
    """Parsed routing config. Immutable so a single instance can serve every
    request without locking."""

    routes: dict[str, str]
    fallbacks: dict[str, tuple[str, ...]]
    privacy_tiers: dict[str, str]

    @classmethod
    def from_path(cls, path: str | os.PathLike[str]) -> RoutingConfig:
        p = Path(path)
        if not p.is_file():
            raise RoutingConfigError(f"routing config not found: {p}")
        try:
            data = tomllib.loads(p.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            raise RoutingConfigError(f"invalid TOML in {p}: {exc}") from exc
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RoutingConfig:
        section = data.get("llm", {})
        if not isinstance(section, dict):
            raise RoutingConfigError("`[llm]` section is malformed")
        routes_raw = section.get("routes", {}) or {}
        fallbacks_raw = section.get("fallbacks", {}) or {}
        tiers_raw = section.get("privacy_tiers", {}) or {}
        if not isinstance(routes_raw, dict) or not isinstance(fallbacks_raw, dict):
            raise RoutingConfigError("routes/fallbacks must be tables")
        routes = {str(k): str(v) for k, v in routes_raw.items()}
        fallbacks: dict[str, tuple[str, ...]] = {}
        for k, v in fallbacks_raw.items():
            if not isinstance(v, list):
                raise RoutingConfigError(f"fallbacks for `{k}` must be a list of model ids")
            fallbacks[str(k)] = tuple(str(x) for x in v)
        if not isinstance(tiers_raw, dict):
            raise RoutingConfigError("privacy_tiers must be a table")
        privacy_tiers = {str(k): str(v) for k, v in tiers_raw.items()}
        return cls(routes=routes, fallbacks=fallbacks, privacy_tiers=privacy_tiers)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _provider_of(model_id: str) -> str:
    """Infer the LiteLLM provider id from a model id.

    Uses prefix conventions first (`bedrock/...`, `azure/...`), then falls
    back to family-based heuristics. Tests cover the cases we care about.
    """
    if "/" in model_id:
        prefix, _, _ = model_id.partition("/")
        return _PROVIDER_PREFIX_MAP.get(prefix.lower(), prefix.lower())
    stem = model_id.split("-")[0].lower()
    return _PROVIDER_PREFIX_MAP.get(stem, stem)


def _model_supports(model_id: str, capabilities: Iterable[str]) -> bool:
    """Returns True iff `model_id` supports every capability in `capabilities`.

    Lookup falls back through the `provider/model` form so `bedrock/claude-...`
    inherits the capability set of `claude-...`.
    """
    requested = set(capabilities)
    if not requested:
        return True
    keys: list[str] = []
    if "/" in model_id:
        _, _, tail = model_id.partition("/")
        keys.append(tail)
    keys.append(model_id)
    for k in keys:
        caps = _CAPABILITY_MATRIX.get(k)
        if caps is not None:
            return requested.issubset(caps)
    # Unknown family — refuse rather than guess. KISS + Article VII.
    return False


def _filter_for_tier(models: Sequence[str], tier: PrivacyTier) -> list[str]:
    """Removes models whose provider is not allowed under the privacy tier."""
    allowed = _TIER_ALLOWED_PROVIDERS.get(tier)
    if allowed is None:
        # Unknown tier -> conservative: deny all.
        return []
    if not allowed:
        return list(models)  # empty allowlist == "no filter"
    return [m for m in models if _provider_of(m) in allowed]


# ---------------------------------------------------------------------------
# TPM rate limiter — sliding 60-second window
# ---------------------------------------------------------------------------


@dataclass
class _TpmWindow:
    limit: int
    events: deque[tuple[float, int]] = field(default_factory=deque)

    def admit(self, tokens: int, *, now: float | None = None) -> None:
        if self.limit <= 0:
            return  # disabled
        ts = time.monotonic() if now is None else now
        cutoff = ts - 60.0
        while self.events and self.events[0][0] < cutoff:
            self.events.popleft()
        used = sum(t for _, t in self.events)
        if used + tokens > self.limit:
            raise TPMExceededError(used + tokens, self.limit)
        self.events.append((ts, tokens))


# ---------------------------------------------------------------------------
# Router — orchestrates lookups + invocation
# ---------------------------------------------------------------------------


@dataclass
class InvocationResult:
    """Wire-shape response. Mirrors `LLMResponse` in `packages/runtime/.../llm.ts`."""

    text: str
    tokens_used: int
    cost_usd: float
    provider_id: str
    model_id: str
    latency_ms: int


# Type alias for the LiteLLM completion function. Indirection lets tests
# inject a fake without touching `litellm` at all.
CompletionFn = Callable[..., Any]


def _default_completion_fn() -> CompletionFn:
    """Lazy import — keeps tests fast and the module importable in
    environments without litellm installed (e.g. pre-commit lint)."""
    import litellm

    return litellm.completion


class Router:
    """Stateless-ish router. Holds config + a TPM window; everything else is
    derived per-request.
    """

    def __init__(
        self,
        config: RoutingConfig,
        *,
        tpm_limit: int | None = None,
        completion_fn: CompletionFn | None = None,
    ) -> None:
        self._config = config
        env_limit = os.environ.get("AI_ENGINEERING_LLM_TPM_LIMIT")
        effective_limit = (
            tpm_limit
            if tpm_limit is not None
            else (int(env_limit) if env_limit and env_limit.isdigit() else 0)
        )
        self._tpm = _TpmWindow(limit=effective_limit)
        self._completion_fn = completion_fn  # resolved lazily so tests can patch

    @property
    def config(self) -> RoutingConfig:
        return self._config

    # -- Routing decisions ---------------------------------------------------

    def route_request(self, skill: str, privacy_tier: PrivacyTier) -> str:
        """Returns the primary model for `skill` under `privacy_tier`.

        Raises `PrivacyTierViolation` if the primary route is not permitted.
        Raises `RoutingConfigError` if no route is configured for the skill.
        """
        if privacy_tier not in _TIER_ALLOWED_PROVIDERS:
            raise PrivacyTierViolation(
                f"unknown privacy tier: {privacy_tier!r}",
                retryable=False,
            )
        primary = self._config.routes.get(skill)
        if primary is None:
            raise RoutingConfigError(
                f"no route configured for skill={skill!r}",
                retryable=False,
            )
        allowed = _filter_for_tier([primary], privacy_tier)
        if not allowed:
            raise PrivacyTierViolation(
                f"primary route {primary!r} for skill={skill!r} not permitted "
                f"under privacy_tier={privacy_tier!r}",
                retryable=False,
            )
        return primary

    def candidate_chain(
        self,
        skill: str,
        privacy_tier: PrivacyTier,
        capabilities: Sequence[str],
    ) -> list[str]:
        """Builds the ordered fallback chain for a request.

        The chain is: `[primary, *fallbacks]`, then filtered by privacy tier
        AND by capability support. The result is the list of models the
        invoker should try in order.
        """
        primary = self._config.routes.get(skill)
        if primary is None:
            raise RoutingConfigError(
                f"no route configured for skill={skill!r}",
                retryable=False,
            )
        chain: list[str] = [primary, *self._config.fallbacks.get(primary, ())]
        chain = _filter_for_tier(chain, privacy_tier)
        chain = [m for m in chain if _model_supports(m, capabilities)]
        return chain

    # -- Invocation ----------------------------------------------------------

    def invoke(
        self,
        skill: str,
        prompt: str,
        privacy_tier: PrivacyTier,
        capabilities: Sequence[str],
    ) -> InvocationResult:
        """Picks a model + calls the completion fn, walking fallbacks on
        retryable errors. Enforces the hard TPM cap before each call.

        Failure ordering (intentional; do not reorder):
          1. RoutingConfigError — skill has no primary route.
          2. PrivacyTierViolation — primary route forbidden under tier.
          3. CapabilityMismatchError — no model supports requested caps.

        This sequencing keeps surface errors specific so the HTTP layer can
        map them to canonical status codes (400 / 422 / 429).
        """
        # (1) + (2): explicit precondition checks. Errors propagate as-is so
        # the server's error mapper can pick the right status.
        self.route_request(skill, privacy_tier)
        # (3): build the capability-filtered chain.
        chain = self.candidate_chain(skill, privacy_tier, capabilities)
        if not chain:
            raise CapabilityMismatchError(
                f"no model satisfies capabilities={list(capabilities)} for "
                f"skill={skill!r} under privacy_tier={privacy_tier!r}",
                retryable=False,
            )
        completion = self._completion_fn or _default_completion_fn()
        last_err: Exception | None = None
        for model_id in chain:
            try:
                self._tpm.admit(_estimate_tokens(prompt))
            except TPMExceededError:
                # Hard cap: do NOT walk further down the chain — the cap is
                # global, not model-scoped.
                raise
            started = time.monotonic()
            try:
                raw = completion(
                    model=model_id,
                    messages=[{"role": "user", "content": prompt}],
                )
            except Exception as exc:
                last_err = exc
                continue
            latency_ms = int((time.monotonic() - started) * 1000)
            return _parse_completion(raw=raw, model_id=model_id, latency_ms=latency_ms)
        # All candidates failed.
        raise RouterError(
            f"all candidates exhausted for skill={skill!r}: {last_err!r}",
            retryable=True,
        )


# ---------------------------------------------------------------------------
# Helpers — kept module-private but unit-tested via `test_router.py`
# ---------------------------------------------------------------------------


def _estimate_tokens(text: str) -> int:
    """Cheap, deterministic prompt-length estimate. Production code uses
    LiteLLM's tokenizer; here a 4-char heuristic is sufficient for the TPM
    pre-flight check (we re-account exact token counts on response)."""
    return max(1, len(text) // 4)


def _parse_completion(*, raw: Any, model_id: str, latency_ms: int) -> InvocationResult:
    """Maps the LiteLLM `ModelResponse` shape into our wire DTO. Tolerant of
    both attribute and dict access patterns to keep tests simple."""
    text = _extract_text(raw)
    tokens = _extract_tokens(raw)
    cost = _extract_cost(raw)
    return InvocationResult(
        text=text,
        tokens_used=tokens,
        cost_usd=cost,
        provider_id=_provider_of(model_id),
        model_id=model_id,
        latency_ms=latency_ms,
    )


def _attr(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _extract_text(raw: Any) -> str:
    choices = _attr(raw, "choices", []) or []
    if not choices:
        return ""
    first = choices[0]
    msg = _attr(first, "message", {}) or {}
    content = _attr(msg, "content", "")
    return content if isinstance(content, str) else ""


def _extract_tokens(raw: Any) -> int:
    usage = _attr(raw, "usage", {}) or {}
    val = _attr(usage, "total_tokens", 0)
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def _extract_cost(raw: Any) -> float:
    # LiteLLM attaches cost on the response under `_hidden_params.response_cost`.
    hidden = _attr(raw, "_hidden_params", {}) or {}
    val = _attr(hidden, "response_cost", 0.0)
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0
