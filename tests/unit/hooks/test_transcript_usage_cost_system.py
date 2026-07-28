"""spec-201 sub-003: per-request cost + model-derived ``gen_ai.system``.

``_lib/transcript_usage.py`` shipped two hardcoded ``"system": "anthropic"``
literals and read no cost at all. Both are defects the moment a non-Anthropic
driver writes a Claude-shaped transcript (the whole point of the open-model
harness).

Three contracts pinned here:

1. :func:`resolve_genai_system` maps a model string onto an OTel
   ``gen_ai.system`` value, case-insensitively, with ``"unknown"`` as the
   terminal floor -- **never** a vendor literal for an unrecognised model.
2. :func:`_usage_cost` extracts a per-request cost across the
   ``cost_usd`` / ``cost`` / ``costUSD`` aliases. An absent cost is ``None``,
   NOT ``0.0`` -- "unknown" must never read as "free". ``bool`` is rejected
   (mirroring ``_safe_int``).
3. :func:`aggregate_session_usage` / :func:`read_latest_usage` surface both
   the derived system and the extracted cost.

Note (spec-201 Risk 1): Claude Code transcripts carry no cost field at all, so
every cost-bearing fixture here is synthetic and models the OpenAI-compatible
path. The pipeline is real; on Claude Code it honestly yields ``None``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
LIB_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "transcript_usage.py"


@pytest.fixture
def lib():
    sys.modules.pop("aieng_transcript_usage_cost", None)
    spec = importlib.util.spec_from_file_location("aieng_transcript_usage_cost", LIB_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _assistant_line(
    *,
    model: str,
    in_tok: int,
    out_tok: int,
    cost: object = None,
    cost_key: str = "cost_usd",
) -> str:
    usage: dict = {
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }
    if cost is not None:
        usage[cost_key] = cost
    return json.dumps(
        {
            "type": "assistant",
            "message": {
                "model": model,
                "role": "assistant",
                "content": [],
                "usage": usage,
            },
            "sessionId": "sess-cost",
        }
    )


def _write_transcript(tmp: Path, lines: list[str]) -> Path:
    path = tmp / "transcript.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# (a) resolve_genai_system -- OTel gen_ai.system values
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("claude-opus-5", "anthropic"),
        ("claude-sonnet-4-5", "anthropic"),
        ("gpt-4o", "openai"),
        ("o3-mini", "openai"),
        ("codex-mini", "openai"),
        ("gemini-2.5-pro", "gcp.gemini"),
        ("deepseek-v3", "deepseek"),
        ("mistral-large", "mistral_ai"),
        ("grok-4", "xai"),
    ],
)
def test_resolve_genai_system_maps_known_models(lib, model: str, expected: str) -> None:
    assert lib.resolve_genai_system(model) == expected


# ---------------------------------------------------------------------------
# (b) unknown floor -- never a vendor literal
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("model", ["", "some-unlisted-model", "   "])
def test_resolve_genai_system_floors_to_unknown(lib, model: str) -> None:
    """An unrecognised (or absent) model is honestly ``unknown``.

    The old code returned a confidently-wrong ``"anthropic"`` for every
    model on earth; that is the exact defect this floor closes.
    """
    assert lib.resolve_genai_system(model) == "unknown"


def test_resolve_genai_system_rejects_non_string(lib) -> None:
    assert lib.resolve_genai_system(None) == "unknown"


# ---------------------------------------------------------------------------
# (c) case-insensitive resolution
# ---------------------------------------------------------------------------


def test_resolve_genai_system_is_case_insensitive(lib) -> None:
    assert lib.resolve_genai_system("Claude-Opus-5") == "anthropic"
    assert lib.resolve_genai_system("GPT-4O") == "openai"
    assert lib.resolve_genai_system("Gemini-2.5-Pro") == "gcp.gemini"


# ---------------------------------------------------------------------------
# (d) / (e) / (f) _usage_cost
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", ["cost_usd", "cost", "costUSD"])
def test_usage_cost_accepts_every_alias(lib, key: str) -> None:
    assert lib._usage_cost({key: 0.0143}) == pytest.approx(0.0143)


def test_usage_cost_accepts_int(lib) -> None:
    assert lib._usage_cost({"cost_usd": 2}) == pytest.approx(2.0)


def test_usage_cost_absent_is_none_not_zero(lib) -> None:
    """Absent cost must be ``None``: "unknown" is not "free"."""
    assert lib._usage_cost({}) is None
    assert lib._usage_cost({"input_tokens": 10}) is None


def test_usage_cost_rejects_bool(lib) -> None:
    """``bool`` is an ``int`` subclass; reject it like ``_safe_int`` does."""
    assert lib._usage_cost({"cost_usd": True}) is None
    assert lib._usage_cost({"cost_usd": False}) is None


def test_usage_cost_rejects_string(lib) -> None:
    assert lib._usage_cost({"cost_usd": "0.02"}) is None


# ---------------------------------------------------------------------------
# (g) aggregate_session_usage sums only the messages that carry a cost
# ---------------------------------------------------------------------------


def test_aggregate_sums_only_cost_bearing_messages(lib, tmp_path: Path) -> None:
    transcript = _write_transcript(
        tmp_path,
        [
            _assistant_line(model="gpt-4o", in_tok=100, out_tok=200, cost=0.01),
            _assistant_line(model="gpt-4o", in_tok=50, out_tok=75),  # no cost
            _assistant_line(model="gpt-4o", in_tok=10, out_tok=15, cost=0.005),
        ],
    )

    out = lib.aggregate_session_usage(transcript)

    assert out["cost_usd"] == pytest.approx(0.015)
    assert out["input_tokens"] == 160
    assert out["output_tokens"] == 290


def test_aggregate_cost_is_none_when_no_message_carries_one(lib, tmp_path: Path) -> None:
    """The live Claude Code shape: tokens yes, cost never."""
    transcript = _write_transcript(
        tmp_path,
        [
            _assistant_line(model="claude-opus-5", in_tok=100, out_tok=200),
            _assistant_line(model="claude-opus-5", in_tok=50, out_tok=75),
        ],
    )

    out = lib.aggregate_session_usage(transcript)

    assert out["cost_usd"] is None
    assert out["total_tokens"] == 425


def test_aggregate_missing_transcript_reports_no_cost(lib, tmp_path: Path) -> None:
    out = lib.aggregate_session_usage(tmp_path / "nope.jsonl")
    assert out["cost_usd"] is None
    assert out["system"] == "unknown"


# ---------------------------------------------------------------------------
# (h) read_latest_usage carries the latest message's cost
# ---------------------------------------------------------------------------


def test_read_latest_usage_returns_latest_cost(lib, tmp_path: Path) -> None:
    transcript = _write_transcript(
        tmp_path,
        [
            _assistant_line(model="gpt-4o", in_tok=1, out_tok=1, cost=0.99),
            _assistant_line(model="gpt-4o", in_tok=2, out_tok=3, cost=0.25),
        ],
    )

    out = lib.read_latest_usage(transcript)

    assert out is not None
    assert out["cost_usd"] == pytest.approx(0.25)
    assert out["system"] == "openai"


def test_read_latest_usage_cost_absent_is_none(lib, tmp_path: Path) -> None:
    transcript = _write_transcript(
        tmp_path,
        [_assistant_line(model="claude-opus-5", in_tok=1, out_tok=1)],
    )

    out = lib.read_latest_usage(transcript)

    assert out is not None
    assert out["cost_usd"] is None
    assert out["system"] == "anthropic"


# ---------------------------------------------------------------------------
# (i) the ``"anthropic"`` hardcode is gone
# ---------------------------------------------------------------------------


def test_aggregate_derives_system_from_model_not_a_literal(lib, tmp_path: Path) -> None:
    transcript = _write_transcript(
        tmp_path,
        [_assistant_line(model="gpt-4o", in_tok=10, out_tok=20, cost=0.001)],
    )

    out = lib.aggregate_session_usage(transcript)

    assert out["model"] == "gpt-4o"
    assert out["system"] == "openai"


def test_aggregate_unknown_model_reports_unknown_system(lib, tmp_path: Path) -> None:
    transcript = _write_transcript(
        tmp_path,
        [_assistant_line(model="house-brand-llm-9", in_tok=10, out_tok=20)],
    )

    out = lib.aggregate_session_usage(transcript)

    assert out["system"] == "unknown"


def test_no_vendor_literal_remains_in_module_source() -> None:
    """No bare ``"system": "anthropic"`` literal may survive in the module.

    Both hardcodes (``aggregate_session_usage`` and ``_shape_usage``) must be
    replaced by :func:`resolve_genai_system`; the literal is only legitimate
    inside the needle table.
    """
    source = LIB_PATH.read_text(encoding="utf-8")
    assert '"system": "anthropic"' not in source
