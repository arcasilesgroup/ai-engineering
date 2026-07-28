"""Per-family capability table (spec-201 D-201-12; supersedes spec-187 D-187-03).

This module records, in one place, how the canonical Claude-Code agent tool
vocabulary surfaces on each model family we care about, each family's tool-CALL
format quirk, and the runtime quirks measured against a live OpenAI-compatible
aggregator during the spec-201 brief (evidence ids E1, E4-E12).

**The copilot ``name_map`` is the SINGLE SOURCE consumed at build time.** The
mirror generator (``scripts/sync_mirrors/core.py``) reads
``TOOL_FAMILY_MAP["copilot"].name_map`` to translate each agent's canonical
tool names into the VS Code Copilot tool ids emitted in
``.github/agents/*.agent.md`` frontmatter — the translated ids (``readFile``,
``editFiles``, ``runCommands``, ``search``, ``agent``) live ONLY here and are
never re-encoded per-agent (spec-189 D-189-06 DRY). Open-weight families carry
no ``name_map`` (``None``): their tool NAMES pass through unchanged on a generic
``tools`` param, which is correct — not a gap.

How the generator uses it:
    1. Read ``CANONICAL_TOOLS`` — the tool literals actually declared in
       ``.claude/agents/*.md`` ``tools:`` frontmatter (the source of truth).
    2. Look up the target family in ``TOOL_FAMILY_MAP``, or resolve a concrete
       model id with ``resolve_capability`` (exact id, then regex pattern, then
       the conservative default — it never raises).
    3. For a family with a ``name_map`` (currently only ``copilot``), translate
       each canonical tool name to the family-native name; for open-weight
       families the tool NAMES pass through unchanged (generic ``tools`` param),
       so ``name_map`` is ``None``.
    4. Apply ``call_format_notes`` when constructing / parsing the tool-call
       request-response for that family (e.g. Kimi special-token IDs, GLM
       ``tool_stream``, DeepSeek JSON-string args), and the measured quirk
       fields when budgeting or validating a response.

**This is build-time data.** D-201-20 upholds D-189-01 unamended: nothing here
detects, routes, selects, ranks or calls a model. The table is read by the
mirror generator and by tests; there is no dispatcher.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ── Canonical tool vocabulary ───────────────────────────────────────────────
# The tool literals actually declared in `.claude/agents/*.md` `tools:`
# frontmatter. This is the portability source of truth: every family record
# below describes how THESE names surface. Keep in sync with the agent
# frontmatter (asserted by tests/unit/config/test_tool_name_map.py).
CANONICAL_TOOLS: tuple[str, ...] = (
    "Read",
    "Write",
    "Edit",
    "Bash",
    "Glob",
    "Grep",
    "Agent",
)

# Canonical Claude → GitHub Copilot (VS Code) per-tool name translation.
# This is the SINGLE source of the copilot tool-name translation: the mirror
# generator (`core.py`) reads `TOOL_FAMILY_MAP["copilot"].name_map` (built from
# this dict) to rename each agent's canonical tools into VS Code ids. `codebase`
# and the other Copilot-native context tools are NOT renames — the generator
# passes them through as authored (`AgentMeta.copilot_native_tools`).
_COPILOT_NAME_MAP: dict[str, str] = {
    "Read": "readFile",
    "Write": "editFiles",
    "Edit": "editFiles",
    "Bash": "runCommands",
    "Glob": "search",
    "Grep": "search",
    "Agent": "agent",
}


# ── Family record ───────────────────────────────────────────────────────────
@dataclass(frozen=True)
class FamilyCapability:
    """Tool surfacing, tool-call format, and measured runtime quirks for one family.

    Replaces the spec-187 four-field profile outright (Hard Rule 3: replaced,
    not wrapped — no alias survives). Those four fields are preserved verbatim;
    the rest record behaviour measured during the spec-201 brief rather than
    inferred, so a caller can budget and validate against evidence.

    Attributes:
        tool_name_style: How the canonical tool names surface / are named for
            this family (native identity, an explicit name map, or pass-through
            on a generic tools param).
        call_format_notes: The family's tool-call FORMAT quirk (request shape /
            response parsing).
        verified: Whether a primary source — secondary portability research or
            a direct probe — backs this row. Every NAMED family is verified;
            ``False`` is reserved for the conservative default an unknown model
            id resolves to.
        name_map: Canonical→family per-tool name translation, when the family
            renames tools (only ``copilot`` today). ``None`` means tool NAMES
            pass through unchanged (open-weight generic ``tools`` param).
        model_ids: Exact model ids this row owns, as returned by the provider's
            ``GET /v1/models`` (E1). First resolution stage.
        model_pattern: Regex searched against a lowercased model id when no
            exact id matches. Second resolution stage. ``None`` for a surface
            that is not addressed by model id (``copilot``).
        schema_enforced_server_side: ``True`` only where a strict JSON-schema
            response contract was MEASURED as honoured (E5). ``False`` means the
            caller must validate client-side — either because a violation was
            measured (mimo returned HTTP 200 with schema-violating content) or
            because no measurement exists. Never infer safety from a 200.
        min_completion_budget: The smallest completion budget worth requesting.
            E9 measured ``max_tokens=16`` with thinking on returning EMPTY
            content and ``finish_reason: "length"`` — a distinct retryable class
            (RK-2), not a parse failure. Reasoning rows carry ≥1024.
        reasoning_field: The response field reasoning text leaks into, when it
            does (E8: ``reasoning_content`` on deepseek and mimo only). Strip it
            before parsing and before replaying history (RK-4).
        prompt_cache: Whether prompt caching was observed reporting counters for
            this family (E6).
        per_request_cost: Whether the response carries a per-request cost (E7
            ``usage.cost``). True on the OpenAI-compatible path only — which is
            precisely why D-201-13 denominates the spend cap in TOKENS: a USD
            cap would be absent on the surface used most.
        fabricates_absolute_paths: Whether the family was observed emitting a
            fabricated absolute working directory in a command (E12, RK-3).
    """

    tool_name_style: str
    call_format_notes: str
    verified: bool = True
    name_map: dict[str, str] | None = field(default=None)
    model_ids: tuple[str, ...] = ()
    model_pattern: str | None = None
    schema_enforced_server_side: bool = False
    min_completion_budget: int = 1024
    reasoning_field: str | None = None
    prompt_cache: bool = False
    per_request_cost: bool = False
    fabricates_absolute_paths: bool = True


# ── The map ─────────────────────────────────────────────────────────────────
# Keyed by family. `content=""` (not None) is the universally-safe tool-call
# message field across every family (research: HF transformers #45419, vLLM).
TOOL_FAMILY_MAP: dict[str, FamilyCapability] = {
    "claude": FamilyCapability(
        tool_name_style=(
            "Native. Canonical names are identity — the `.claude/agents/*.md`"
            " `tools:` frontmatter is authored directly against them."
        ),
        call_format_notes=(
            "Native Anthropic tool_use / tool_result content blocks; no"
            ' translation needed. `content=""` is safe.'
        ),
        model_pattern=r"(^|/)claude[-.]",
        # No `response_format json_schema` contract exists on this path, so
        # there is nothing for the server to enforce — validate client-side.
        schema_enforced_server_side=False,
        # Extended thinking requires a 1024-token budget floor.
        min_completion_budget=1024,
        # Thinking arrives as separate content blocks, not a message field.
        reasoning_field=None,
        # Transcripts report `cache_creation_input_tokens` /
        # `cache_read_input_tokens` (`_lib/transcript_usage.py:24-25`).
        prompt_cache=True,
        # Measured: Claude Code transcripts carry NO cost field of any kind.
        per_request_cost=False,
        fabricates_absolute_paths=False,
    ),
    "copilot": FamilyCapability(
        tool_name_style=(
            "Renamed to VS Code agent tool ids via `name_map` (the same"
            " translation core.py applies per-agent), plus the always-present"
            " `codebase` context tool."
        ),
        call_format_notes=(
            "VS Code Copilot custom-agents `tools: [...]` param; tool ids are"
            " the mapped names, not the canonical ones."
        ),
        name_map=dict(_COPILOT_NAME_MAP),
        # Addressed as a surface, not by model id — the underlying model is the
        # operator's VS Code selection, so there is nothing to resolve against.
        model_pattern=None,
        schema_enforced_server_side=False,
        min_completion_budget=1024,
        fabricates_absolute_paths=False,
    ),
    "gemini": FamilyCapability(
        tool_name_style=("Pass-through — tool NAMES ride a generic tools param unchanged."),
        call_format_notes=(
            "Gemini / Gemma wrap tool-call JSON in Markdown code fences; strip"
            " the fences before parsing. Markdown headers suit the family."
        ),
        model_ids=("gemma4",),
        model_pattern=r"(^|/)(gemini|gemma)",
        schema_enforced_server_side=True,  # E5: schema-valid under strict:true
        min_completion_budget=512,
        per_request_cost=True,
        fabricates_absolute_paths=False,
    ),
    "kimi": FamilyCapability(
        tool_name_style=("Pass-through — tool NAMES ride a generic tools param unchanged."),
        call_format_notes=(
            "Requires `functions.{name}:{idx}` tool-call IDs and special tokens"
            " around the call (Kimi-K2 tool_call_guidance)."
        ),
        model_pattern=r"kimi",
        # Not probed in E4-E12: no strict-schema measurement, so validate.
        schema_enforced_server_side=False,
        min_completion_budget=512,
        per_request_cost=True,
        fabricates_absolute_paths=False,
    ),
    "glm": FamilyCapability(
        tool_name_style=("Pass-through — tool NAMES ride a generic tools param unchanged."),
        call_format_notes=(
            'Streaming tool calls need `extra_body={"tool_stream": true}` on the request.'
        ),
        model_pattern=r"glm",
        schema_enforced_server_side=False,
        min_completion_budget=512,
        per_request_cost=True,
        fabricates_absolute_paths=False,
    ),
    "deepseek": FamilyCapability(
        tool_name_style=("Pass-through — tool NAMES ride a generic tools param unchanged."),
        call_format_notes=(
            "DeepSeek-V3 rejects dict args — arguments must be a JSON *string*;"
            " it also hallucinates extra schema fields, so validate strictly."
        ),
        model_ids=("deepseek-v4-flash",),
        model_pattern=r"deepseek",
        schema_enforced_server_side=True,  # E5
        min_completion_budget=1024,  # E8/E9: reasoning consumes the budget
        reasoning_field="reasoning_content",  # E8
        prompt_cache=True,  # E6: `cache_write_tokens`
        per_request_cost=True,  # E7
        fabricates_absolute_paths=False,
    ),
    "qwen": FamilyCapability(
        tool_name_style=("Pass-through — tool NAMES ride a generic tools param unchanged."),
        call_format_notes=(
            "Hermes-style tool calls; double-escapes arguments and suffers"
            " task-confusion on multi-purpose skills — keep skills"
            " strictly single-purpose."
        ),
        model_ids=("qwen3.6",),
        model_pattern=r"qwen",
        schema_enforced_server_side=True,  # E5
        min_completion_budget=512,
        per_request_cost=True,
        fabricates_absolute_paths=True,  # E12: emitted `cd /home/user/...`
    ),
    "mimo": FamilyCapability(
        tool_name_style=("Pass-through — tool NAMES ride a generic tools param unchanged."),
        call_format_notes=(
            "Probed directly (E4-E6, E8-E11): single, parallel and forced tool"
            " calls all succeed, but a `strict:true` schema contract returns"
            " HTTP 200 with violating content — always validate client-side."
        ),
        # spec-201 probed mimo-v2.5 live, superseding D-187-08's "no primary
        # portability source found"; the row now carries live-behaviour claims.
        verified=True,
        model_ids=("mimo-v2.5",),
        model_pattern=r"mimo",
        schema_enforced_server_side=False,  # E5: 200 with violating content
        min_completion_budget=1024,  # E8/E9
        reasoning_field="reasoning_content",  # E8
        prompt_cache=True,  # E6: `cached_tokens: 192`
        per_request_cost=True,  # E7
        fabricates_absolute_paths=False,
    ),
}


# The row an unresolvable model id lands on. Conservative in every direction:
# unverified, no server-side schema contract, the largest measured completion
# floor, and the failure modes assumed present rather than absent.
_DEFAULT_CAPABILITY = FamilyCapability(
    tool_name_style=("Unknown family — assume pass-through tool NAMES on a generic tools param."),
    call_format_notes=(
        "No measurement for this model id. Validate every response client-side,"
        " strip unknown reasoning fields, and reject model-emitted absolute paths."
    ),
    verified=False,
    schema_enforced_server_side=False,
    min_completion_budget=1024,
    fabricates_absolute_paths=True,
)


def resolve_capability(model_id: str) -> FamilyCapability:
    """Resolve a concrete model id to its capability row. Never raises.

    Three stages, in order: an exact ``model_ids`` hit, then the first
    ``model_pattern`` that matches in declaration order, then
    ``_DEFAULT_CAPABILITY``. A degenerate id (empty, whitespace, ``None``)
    resolves to the default rather than raising — a build-time table must never
    be able to break the generator that reads it.
    """
    normalized = str(model_id or "").strip().lower()
    if not normalized:
        return _DEFAULT_CAPABILITY

    for capability in TOOL_FAMILY_MAP.values():
        if any(normalized == known.lower() for known in capability.model_ids):
            return capability

    for capability in TOOL_FAMILY_MAP.values():
        pattern = capability.model_pattern
        if pattern and re.search(pattern, normalized):
            return capability

    return _DEFAULT_CAPABILITY


__all__ = [
    "CANONICAL_TOOLS",
    "TOOL_FAMILY_MAP",
    "FamilyCapability",
    "resolve_capability",
]
