"""Router unit tests.

We deliberately avoid touching real LiteLLM — `litellm.completion` is the
only outbound boundary, captured behind `Router(completion_fn=...)`. Every
test in this file therefore runs in milliseconds with zero network I/O.

Coverage targets per Article II: every public function gets ≥1 positive +
≥1 negative case, plus the privacy-tier matrix.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from ai_eng_litellm_bridge.router import (
    CapabilityMismatchError,
    InvocationResult,
    PrivacyTierViolation,
    Router,
    RoutingConfig,
    RoutingConfigError,
    TPMExceededError,
    _estimate_tokens,
    _extract_text,
    _extract_tokens,
    _filter_for_tier,
    _model_supports,
    _provider_of,
    _TpmWindow,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _baseline_config() -> RoutingConfig:
    return RoutingConfig.from_dict(
        {
            "llm": {
                "routes": {
                    "specify": "claude-opus-4-7",
                    "implement": "claude-sonnet-4-6",
                    "regulated": "bedrock/claude-opus-4-7",
                },
                "fallbacks": {
                    "claude-opus-4-7": ["claude-sonnet-4-6", "gpt-5"],
                    "bedrock/claude-opus-4-7": ["azure/gpt-5"],
                },
                "privacy_tiers": {
                    "default": "standard",
                    "banking": "strict",
                },
            },
        }
    )


class _FakeChoice:
    def __init__(self, text: str) -> None:
        self.message = {"role": "assistant", "content": text}


class _FakeResponse:
    """LiteLLM-shaped fake. Attribute access AND dict access both supported
    via the `_attr` helper inside router.py."""

    def __init__(self, *, text: str, tokens: int = 42, cost: float = 0.0123) -> None:
        self.choices = [_FakeChoice(text)]
        self.usage = {"prompt_tokens": tokens // 2, "total_tokens": tokens}
        self._hidden_params = {"response_cost": cost}


def _fake_completion(*, text: str = "ok", tokens: int = 42, cost: float = 0.001):
    """Returns a callable that mimics `litellm.completion` and records calls."""

    calls: list[dict[str, Any]] = []

    def _fn(**kwargs: Any) -> _FakeResponse:
        calls.append(kwargs)
        return _FakeResponse(text=text, tokens=tokens, cost=cost)

    _fn.calls = calls  # type: ignore[attr-defined]
    return _fn


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class TestProviderOf:
    def test_explicit_prefix_wins(self) -> None:
        assert _provider_of("bedrock/anthropic.claude-3-5-sonnet") == "bedrock"
        assert _provider_of("azure/gpt-5") == "azure"

    def test_falls_back_to_family_heuristic(self) -> None:
        assert _provider_of("claude-opus-4-7") == "anthropic"
        assert _provider_of("gpt-5") == "openai"

    def test_unknown_falls_back_to_stem(self) -> None:
        assert _provider_of("xyz-99") == "xyz"


class TestModelSupports:
    def test_known_model_satisfies_subset(self) -> None:
        assert _model_supports("claude-opus-4-7", ["tool_use", "vision"]) is True

    def test_empty_capabilities_always_supported(self) -> None:
        assert _model_supports("claude-opus-4-7", []) is True

    def test_known_model_rejects_missing_capability(self) -> None:
        # gpt-4o lacks prompt_caching in our matrix — must reject.
        assert _model_supports("gpt-4o", ["prompt_caching"]) is False

    def test_unknown_model_returns_false(self) -> None:
        # Article VII: refuse rather than guess.
        assert _model_supports("totally-unknown-model", ["tool_use"]) is False

    def test_provider_prefixed_inherits_family_caps(self) -> None:
        # bedrock/claude-opus-4-7 should have the same caps as claude-opus-4-7.
        assert _model_supports("bedrock/claude-opus-4-7", ["tool_use", "vision"]) is True


class TestFilterForTier:
    def test_standard_keeps_all(self) -> None:
        models = ["claude-opus-4-7", "gpt-5", "azure/gpt-5"]
        assert _filter_for_tier(models, "standard") == models

    def test_strict_keeps_only_bedrock_and_azure(self) -> None:
        models = ["claude-opus-4-7", "bedrock/claude-3-5", "azure/gpt-5", "gpt-5"]
        kept = _filter_for_tier(models, "strict")
        assert kept == ["bedrock/claude-3-5", "azure/gpt-5"]

    def test_airgapped_keeps_only_bedrock(self) -> None:
        kept = _filter_for_tier(
            ["bedrock/claude-3-5", "azure/gpt-5", "claude-opus-4-7"], "airgapped"
        )
        assert kept == ["bedrock/claude-3-5"]

    def test_unknown_tier_denies_all(self) -> None:
        assert _filter_for_tier(["claude-opus-4-7"], "no-such-tier") == []


class TestEstimateTokens:
    def test_roughly_one_token_per_4_chars(self) -> None:
        assert _estimate_tokens("a" * 40) == 10

    def test_short_string_floors_to_one(self) -> None:
        assert _estimate_tokens("") == 1
        assert _estimate_tokens("a") == 1


class TestExtractors:
    def test_extract_text_handles_dict_choices(self) -> None:
        raw = {"choices": [{"message": {"content": "hi"}}]}
        assert _extract_text(raw) == "hi"

    def test_extract_text_returns_empty_when_no_choices(self) -> None:
        assert _extract_text({"choices": []}) == ""

    def test_extract_tokens_from_dict_usage(self) -> None:
        raw = {"usage": {"total_tokens": 200}}
        assert _extract_tokens(raw) == 200

    def test_extract_tokens_returns_zero_on_garbage(self) -> None:
        assert _extract_tokens({"usage": {"total_tokens": "not-a-number"}}) == 0


# ---------------------------------------------------------------------------
# RoutingConfig
# ---------------------------------------------------------------------------


class TestRoutingConfig:
    def test_from_dict_parses_baseline(self) -> None:
        cfg = _baseline_config()
        assert cfg.routes["specify"] == "claude-opus-4-7"
        assert cfg.fallbacks["claude-opus-4-7"] == (
            "claude-sonnet-4-6",
            "gpt-5",
        )
        assert cfg.privacy_tiers["banking"] == "strict"

    def test_from_path_round_trip(self, tmp_path: Path) -> None:
        path = tmp_path / "routes.toml"
        path.write_text(
            """
            [llm.routes]
            specify = "claude-opus-4-7"

            [llm.fallbacks]
            "claude-opus-4-7" = ["gpt-5"]

            [llm.privacy_tiers]
            default = "standard"
            """,
            encoding="utf-8",
        )
        cfg = RoutingConfig.from_path(path)
        assert cfg.routes == {"specify": "claude-opus-4-7"}
        assert cfg.fallbacks == {"claude-opus-4-7": ("gpt-5",)}

    def test_missing_path_raises(self, tmp_path: Path) -> None:
        with pytest.raises(RoutingConfigError, match="not found"):
            RoutingConfig.from_path(tmp_path / "nope.toml")

    def test_invalid_toml_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.toml"
        bad.write_text("not = valid = toml", encoding="utf-8")
        with pytest.raises(RoutingConfigError, match="invalid TOML"):
            RoutingConfig.from_path(bad)

    def test_fallbacks_must_be_lists(self) -> None:
        with pytest.raises(RoutingConfigError, match="must be a list"):
            RoutingConfig.from_dict(
                {
                    "llm": {
                        "routes": {"a": "claude-opus-4-7"},
                        "fallbacks": {"claude-opus-4-7": "not-a-list"},
                    }
                }
            )

    def test_llm_section_must_be_table(self) -> None:
        with pytest.raises(RoutingConfigError, match="malformed"):
            RoutingConfig.from_dict({"llm": ["not", "a", "table"]})


# ---------------------------------------------------------------------------
# Router.route_request — privacy tier matrix
# ---------------------------------------------------------------------------


class TestRouteRequest:
    def test_standard_returns_primary(self) -> None:
        r = Router(_baseline_config(), completion_fn=_fake_completion())
        assert r.route_request("specify", "standard") == "claude-opus-4-7"

    def test_strict_rejects_non_allowlisted_primary(self) -> None:
        r = Router(_baseline_config(), completion_fn=_fake_completion())
        # `specify` -> `claude-opus-4-7` (anthropic direct) is not in the
        # strict allowlist (only bedrock/azure).
        with pytest.raises(PrivacyTierViolation, match="not permitted"):
            r.route_request("specify", "strict")

    def test_strict_accepts_bedrock_primary(self) -> None:
        r = Router(_baseline_config(), completion_fn=_fake_completion())
        assert r.route_request("regulated", "strict") == "bedrock/claude-opus-4-7"

    def test_unknown_tier_raises(self) -> None:
        r = Router(_baseline_config(), completion_fn=_fake_completion())
        with pytest.raises(PrivacyTierViolation, match="unknown privacy tier"):
            r.route_request("specify", "made-up-tier")

    def test_unknown_skill_raises(self) -> None:
        r = Router(_baseline_config(), completion_fn=_fake_completion())
        with pytest.raises(RoutingConfigError, match="no route configured"):
            r.route_request("does-not-exist", "standard")


class TestCandidateChain:
    def test_chain_includes_primary_and_fallbacks(self) -> None:
        r = Router(_baseline_config(), completion_fn=_fake_completion())
        chain = r.candidate_chain("specify", "standard", [])
        assert chain == ["claude-opus-4-7", "claude-sonnet-4-6", "gpt-5"]

    def test_chain_filtered_by_capability(self) -> None:
        r = Router(_baseline_config(), completion_fn=_fake_completion())
        chain = r.candidate_chain("specify", "standard", ["prompt_caching"])
        # gpt-4o would lack prompt_caching, but it's not in the chain anyway.
        # Only the three baseline models — all support prompt_caching.
        assert chain == ["claude-opus-4-7", "claude-sonnet-4-6", "gpt-5"]

    def test_chain_filtered_by_privacy_tier_strict(self) -> None:
        r = Router(_baseline_config(), completion_fn=_fake_completion())
        chain = r.candidate_chain("regulated", "strict", [])
        assert chain == ["bedrock/claude-opus-4-7", "azure/gpt-5"]

    def test_unknown_skill_raises(self) -> None:
        r = Router(_baseline_config(), completion_fn=_fake_completion())
        with pytest.raises(RoutingConfigError):
            r.candidate_chain("nope", "standard", [])


# ---------------------------------------------------------------------------
# Router.invoke — happy path, fallback, capability mismatch, TPM
# ---------------------------------------------------------------------------


class TestInvokeHappyPath:
    def test_returns_invocation_result(self) -> None:
        fake = _fake_completion(text="hello world", tokens=120, cost=0.0042)
        r = Router(_baseline_config(), completion_fn=fake)
        result = r.invoke("specify", "Hi", "standard", [])
        assert isinstance(result, InvocationResult)
        assert result.text == "hello world"
        assert result.tokens_used == 120
        assert result.cost_usd == pytest.approx(0.0042)
        assert result.model_id == "claude-opus-4-7"
        assert result.provider_id == "anthropic"
        assert result.latency_ms >= 0

    def test_passes_messages_to_completion(self) -> None:
        fake = _fake_completion()
        r = Router(_baseline_config(), completion_fn=fake)
        r.invoke("specify", "Pls help", "standard", [])
        assert fake.calls[0]["messages"] == [{"role": "user", "content": "Pls help"}]
        assert fake.calls[0]["model"] == "claude-opus-4-7"


class TestInvokeFallback:
    def test_falls_through_on_first_failure(self) -> None:
        attempts: list[str] = []

        def _flaky(**kwargs: Any) -> _FakeResponse:
            attempts.append(kwargs["model"])
            if kwargs["model"] == "claude-opus-4-7":
                raise RuntimeError("boom — primary down")
            return _FakeResponse(text=f"served by {kwargs['model']}", tokens=10)

        r = Router(_baseline_config(), completion_fn=_flaky)
        result = r.invoke("specify", "Hi", "standard", [])
        assert attempts == ["claude-opus-4-7", "claude-sonnet-4-6"]
        assert result.model_id == "claude-sonnet-4-6"
        assert result.text == "served by claude-sonnet-4-6"

    def test_all_candidates_failing_raises_router_error(self) -> None:
        from ai_eng_litellm_bridge.router import RouterError

        def _always_fails(**kwargs: Any) -> _FakeResponse:
            raise RuntimeError("upstream offline")

        r = Router(_baseline_config(), completion_fn=_always_fails)
        with pytest.raises(RouterError, match="all candidates exhausted"):
            r.invoke("specify", "Hi", "standard", [])


class TestInvokeCapabilityMismatch:
    def test_no_model_in_chain_supports_capabilities(self) -> None:
        # Configure routes pointing at unknown families so the capability
        # matrix returns False for every entry in the chain.
        cfg = RoutingConfig.from_dict(
            {
                "llm": {
                    "routes": {"weird": "totally-unknown-model"},
                    "fallbacks": {"totally-unknown-model": ["another-mystery"]},
                }
            }
        )
        r = Router(cfg, completion_fn=_fake_completion())
        with pytest.raises(CapabilityMismatchError):
            r.invoke("weird", "Hi", "standard", ["tool_use"])


class TestInvokeTPMLimit:
    def test_exceeding_limit_raises(self) -> None:
        # 4-char heuristic => 25 tokens for a 100-char prompt.
        prompt = "x" * 100
        r = Router(
            _baseline_config(),
            tpm_limit=20,
            completion_fn=_fake_completion(),
        )
        with pytest.raises(TPMExceededError) as exc_info:
            r.invoke("specify", prompt, "standard", [])
        assert exc_info.value.limit == 20
        assert exc_info.value.retryable is False

    def test_under_limit_allows_invocation(self) -> None:
        r = Router(
            _baseline_config(),
            tpm_limit=10_000,
            completion_fn=_fake_completion(text="ok"),
        )
        result = r.invoke("specify", "tiny prompt", "standard", [])
        assert result.text == "ok"

    def test_zero_limit_means_disabled(self) -> None:
        r = Router(
            _baseline_config(),
            tpm_limit=0,
            completion_fn=_fake_completion(),
        )
        # 1000-char prompt would be ~250 tokens; with limit=0 must NOT raise.
        result = r.invoke("specify", "x" * 1000, "standard", [])
        assert isinstance(result, InvocationResult)


class TestTPMWindow:
    def test_admits_under_limit(self) -> None:
        w = _TpmWindow(limit=100)
        w.admit(50, now=0.0)
        w.admit(40, now=10.0)
        # No exception raised => admit succeeded.

    def test_rejects_over_limit(self) -> None:
        w = _TpmWindow(limit=100)
        w.admit(60, now=0.0)
        with pytest.raises(TPMExceededError):
            w.admit(50, now=10.0)

    def test_old_events_evicted_after_60s(self) -> None:
        w = _TpmWindow(limit=100)
        w.admit(80, now=0.0)
        # 61s later, the previous event is outside the 60s window.
        w.admit(80, now=61.0)


# ---------------------------------------------------------------------------
# Env-var integration for TPM
# ---------------------------------------------------------------------------


class TestEnvLimitIntegration:
    def test_env_var_picks_up_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AI_ENGINEERING_LLM_TPM_LIMIT", "5")
        r = Router(_baseline_config(), completion_fn=_fake_completion())
        # 100 chars => ~25 tokens, exceeds limit of 5.
        with pytest.raises(TPMExceededError):
            r.invoke("specify", "x" * 100, "standard", [])

    def test_explicit_arg_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AI_ENGINEERING_LLM_TPM_LIMIT", "5")
        r = Router(
            _baseline_config(),
            tpm_limit=10_000,
            completion_fn=_fake_completion(),
        )
        # Explicit arg wins; no exception.
        r.invoke("specify", "x" * 100, "standard", [])

    def test_garbage_env_value_disables_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AI_ENGINEERING_LLM_TPM_LIMIT", "not-a-number")
        r = Router(_baseline_config(), completion_fn=_fake_completion())
        # Limit silently disabled — fail-safe; the global cap is advisory at
        # the boundary, not a hard guard.
        r.invoke("specify", "x" * 1000, "standard", [])


# ---------------------------------------------------------------------------
# Sanity check: hard pin assertion
# ---------------------------------------------------------------------------


def test_litellm_hard_pin_in_pyproject() -> None:
    """Article VI guard — `litellm` MUST be pinned at 1.51.0. Versions
    1.82.7/8 (March 2026) were a supply chain compromise."""
    pyproject = (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    assert re.search(r'"litellm==1\.51\.0"', pyproject), (
        "litellm pin missing or weakened — see ADR-0008. Do NOT widen."
    )
    # The compromised range must not appear in any litellm pin/spec line.
    forbidden = re.search(r'"litellm[^"]*1\.82\.[^"]*"', pyproject)
    assert forbidden is None, "Compromised LiteLLM 1.82.x present in pin"
