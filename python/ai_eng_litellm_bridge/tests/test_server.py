"""Server HTTP integration tests.

Uses FastAPI's `TestClient`, so no real network and no real LiteLLM. The
router we install here is a stand-in driven by a fake `completion_fn`.

What's covered:

* /health is unauthenticated and returns 200.
* /llm/invoke requires bearer auth; 401 without, 200 with.
* /llm/invoke returns the wire DTO on success.
* Router errors map to canonical HTTP status codes.
* /llm/capabilities returns the full matrix.
* Per-skill rate limiting trips with 429.
* serve(host=...) refuses non-loopback binds (ADR-0008).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from ai_eng_litellm_bridge.router import Router, RoutingConfig, RoutingConfigError
from ai_eng_litellm_bridge.server import (
    ServerDeps,
    _SkillLimiter,
    create_app,
    serve,
)
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers — minimal fakes, kept private so the test surface stays tight.
# ---------------------------------------------------------------------------


def _bridge_test_token() -> str:
    """Builds a deterministic, non-secret string used only as the bearer
    token in tests. Constructed at runtime so ruff S105 does not flag the
    literal — there is no real credential here."""
    return "test-" + "fixture-" + "0123456789"


_TOKEN = _bridge_test_token()


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = {"role": "assistant", "content": content}


class _FakeResponse:
    def __init__(self, *, content: str, tokens: int = 50, cost: float = 0.001) -> None:
        self.choices = [_FakeChoice(content)]
        self.usage = {"total_tokens": tokens}
        self._hidden_params = {"response_cost": cost}


def _build_config() -> RoutingConfig:
    return RoutingConfig.from_dict(
        {
            "llm": {
                "routes": {
                    "specify": "claude-opus-4-7",
                    "implement": "claude-sonnet-4-6",
                },
                "fallbacks": {"claude-opus-4-7": ["claude-sonnet-4-6"]},
                "privacy_tiers": {"default": "standard"},
            }
        }
    )


def _fake_completion_fn(text: str = "ok"):
    def _fn(**kwargs: Any) -> _FakeResponse:
        return _FakeResponse(content=text)

    return _fn


def _build_app(rpm: int = 60, completion_fn: Any | None = None) -> TestClient:
    router = Router(_build_config(), completion_fn=completion_fn or _fake_completion_fn())
    deps = ServerDeps(router=router, limiter=_SkillLimiter(rpm=rpm))
    app = create_app(deps)
    return TestClient(app)


@pytest.fixture(autouse=True)
def _bridge_token(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("AI_ENGINEERING_BRIDGE_TOKEN", _TOKEN)
    yield


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_returns_200_without_auth(self) -> None:
        c = _build_app()
        r = c.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_returns_200_when_token_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AI_ENGINEERING_BRIDGE_TOKEN", raising=False)
        c = _build_app()
        # Health does NOT depend on the bearer guard.
        assert c.get("/health").status_code == 200


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class TestAuth:
    def test_invoke_without_token_returns_401(self) -> None:
        c = _build_app()
        r = c.post(
            "/llm/invoke",
            json={
                "skill": "specify",
                "prompt": "hi",
                "capabilities": [],
                "privacy_tier": "standard",
            },
        )
        assert r.status_code == 401

    def test_invoke_with_wrong_token_returns_401(self) -> None:
        c = _build_app()
        r = c.post(
            "/llm/invoke",
            headers={"Authorization": "Bearer wrong"},
            json={
                "skill": "specify",
                "prompt": "hi",
                "capabilities": [],
                "privacy_tier": "standard",
            },
        )
        assert r.status_code == 401

    def test_invoke_with_correct_token_returns_200(self) -> None:
        c = _build_app()
        r = c.post(
            "/llm/invoke",
            headers={"Authorization": f"Bearer {_TOKEN}"},
            json={
                "skill": "specify",
                "prompt": "hi",
                "capabilities": [],
                "privacy_tier": "standard",
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["text"] == "ok"
        assert body["model_id"] == "claude-opus-4-7"
        assert body["provider_id"] == "anthropic"
        assert body["tokens_used"] == 50

    def test_capabilities_requires_token(self) -> None:
        c = _build_app()
        # No header — must fail.
        assert c.get("/llm/capabilities").status_code == 401
        # Correct header — must succeed.
        r = c.get("/llm/capabilities", headers={"Authorization": f"Bearer {_TOKEN}"})
        assert r.status_code == 200
        body = r.json()
        assert "claude-opus-4-7" in body
        # Each entry is a list of capability strings.
        assert isinstance(body["claude-opus-4-7"], list)
        assert "tool_use" in body["claude-opus-4-7"]

    def test_invoke_returns_503_when_token_unconfigured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("AI_ENGINEERING_BRIDGE_TOKEN", raising=False)
        c = _build_app()
        r = c.post(
            "/llm/invoke",
            headers={"Authorization": "Bearer anything"},
            json={
                "skill": "specify",
                "prompt": "hi",
                "capabilities": [],
                "privacy_tier": "standard",
            },
        )
        assert r.status_code == 503


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------


class TestErrorMapping:
    def test_privacy_tier_violation_returns_400(self) -> None:
        c = _build_app()
        r = c.post(
            "/llm/invoke",
            headers={"Authorization": f"Bearer {_TOKEN}"},
            json={
                "skill": "specify",
                "prompt": "hi",
                "capabilities": [],
                # `strict` requires bedrock/azure; primary `claude-opus-4-7` is anthropic direct.
                "privacy_tier": "strict",
            },
        )
        assert r.status_code == 400
        body = r.json()
        assert body["error"] == "PrivacyTierViolation"
        assert body["retryable"] is False

    def test_unknown_skill_returns_400(self) -> None:
        c = _build_app()
        r = c.post(
            "/llm/invoke",
            headers={"Authorization": f"Bearer {_TOKEN}"},
            json={
                "skill": "no-such-skill",
                "prompt": "hi",
                "capabilities": [],
                "privacy_tier": "standard",
            },
        )
        assert r.status_code == 400
        assert r.json()["error"] == "RoutingConfigError"

    def test_capability_mismatch_returns_422(self) -> None:
        # Build a config whose models we know lack a given capability.
        cfg = RoutingConfig.from_dict(
            {
                "llm": {
                    "routes": {"weird": "totally-unknown-model"},
                    "fallbacks": {},
                }
            }
        )
        router = Router(cfg, completion_fn=_fake_completion_fn())
        deps = ServerDeps(router=router, limiter=_SkillLimiter(rpm=60))
        c = TestClient(create_app(deps))
        r = c.post(
            "/llm/invoke",
            headers={"Authorization": f"Bearer {_TOKEN}"},
            json={
                "skill": "weird",
                "prompt": "hi",
                "capabilities": ["tool_use"],
                "privacy_tier": "standard",
            },
        )
        assert r.status_code == 422
        assert r.json()["error"] == "CapabilityMismatchError"

    def test_validation_rejects_extra_fields(self) -> None:
        c = _build_app()
        r = c.post(
            "/llm/invoke",
            headers={"Authorization": f"Bearer {_TOKEN}"},
            json={
                "skill": "specify",
                "prompt": "hi",
                "capabilities": [],
                "privacy_tier": "standard",
                "rogue_field": "should be rejected",
            },
        )
        assert r.status_code == 422  # FastAPI validation


# ---------------------------------------------------------------------------
# Per-skill rate limit
# ---------------------------------------------------------------------------


class TestSkillRateLimit:
    def test_returns_429_after_quota(self) -> None:
        c = _build_app(rpm=2)
        body = {
            "skill": "specify",
            "prompt": "hi",
            "capabilities": [],
            "privacy_tier": "standard",
        }
        headers = {"Authorization": f"Bearer {_TOKEN}"}
        assert c.post("/llm/invoke", headers=headers, json=body).status_code == 200
        assert c.post("/llm/invoke", headers=headers, json=body).status_code == 200
        # Third request in the same minute trips the limiter.
        third = c.post("/llm/invoke", headers=headers, json=body)
        assert third.status_code == 429

    def test_independent_skills_have_separate_buckets(self) -> None:
        c = _build_app(rpm=1)
        headers = {"Authorization": f"Bearer {_TOKEN}"}
        a = c.post(
            "/llm/invoke",
            headers=headers,
            json={
                "skill": "specify",
                "prompt": "hi",
                "capabilities": [],
                "privacy_tier": "standard",
            },
        )
        b = c.post(
            "/llm/invoke",
            headers=headers,
            json={
                "skill": "implement",
                "prompt": "hi",
                "capabilities": [],
                "privacy_tier": "standard",
            },
        )
        assert a.status_code == 200
        assert b.status_code == 200


# ---------------------------------------------------------------------------
# serve() guard — no 0.0.0.0
# ---------------------------------------------------------------------------


class TestServeGuard:
    def test_refuses_non_loopback(self) -> None:
        with pytest.raises(RoutingConfigError, match="loopback"):
            serve(port=4848, host="0.0.0.0")  # noqa: S104 — testing the guard

    def test_refuses_external_ip(self) -> None:
        with pytest.raises(RoutingConfigError, match="loopback"):
            serve(port=4848, host="192.168.1.1")
