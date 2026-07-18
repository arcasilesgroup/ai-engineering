"""Documented tool-name / tool-call-convention reference map (spec-187 D-187-03).

This module is a REFERENCE artifact, not an active code path. It records, in one
place, how the canonical Claude-Code agent tool vocabulary surfaces on each model
family we care about, plus each family's tool-CALL format quirk drawn from the
spec-187 fleet-audit research ("Cross-model portability" section).

**No mirror family consumes this map yet.** Per D-187-03, portability this cycle
is achieved by keeping canonical prose model-neutral and *documenting* the mapping
— NOT by widening the mirror tree with new open-weight directories (`.kimi/`,
`.glm/`, …). Wiring is deferred until a real open-weight execution harness exists;
YAGNI until then (spec Non-Goals: "No live open-weight model execution").

How a future harness would use it:
    1. Read ``CANONICAL_TOOLS`` — the tool literals actually declared in
       ``.claude/agents/*.md`` ``tools:`` frontmatter (the source of truth).
    2. Look up the target family in ``TOOL_FAMILY_MAP``.
    3. For families with a ``name_map`` (currently only ``copilot``), translate
       each canonical tool name to the family-native name; for open-weight
       families the tool NAMES pass through unchanged (they ride a generic
       ``tools`` param), so ``name_map`` is ``None``.
    4. Apply ``call_format_notes`` when constructing the tool-call request /
       parsing the tool-call response for that family (e.g. Kimi special-token
       IDs, GLM ``tool_stream``, DeepSeek JSON-string args).

The ``copilot`` ``name_map`` is the same canonical→VS-Code translation already
encoded per-agent in ``core.py`` (Read→readFile, Write/Edit→editFiles,
Bash→runCommands, Glob/Grep→search, Agent→agent, always-present ``codebase``
context tool). It is reproduced here as the single documented per-tool form.

MiMo is present but flagged ``verified=False`` (D-187-08): no primary portability
source surfaced in research, so no live-behavior claim is made — it is covered
structurally by the neutrality lint only.
"""

from __future__ import annotations

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
# This is the documented single form of the per-agent mapping already encoded
# in `core.py` AGENT_METADATA (claude_tools → copilot_tools). `codebase` is the
# always-present context tool Copilot agents carry regardless of canonical set.
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
class FamilyToolProfile:
    """How the canonical tools surface, and the tool-CALL quirk, for one family.

    Attributes:
        tool_name_style: How the canonical tool names surface / are named for
            this family (native identity, an explicit name map, or pass-through
            on a generic tools param).
        call_format_notes: The family's tool-call FORMAT quirk (request shape /
            response parsing), condensed from the spec-187 research.
        verified: Whether a primary portability source backs the notes. MiMo is
            ``False`` per D-187-08; no live-behavior claim is made for it.
        name_map: Canonical→family per-tool name translation, when the family
            renames tools (only ``copilot`` today). ``None`` means tool NAMES
            pass through unchanged (open-weight generic ``tools`` param).
    """

    tool_name_style: str
    call_format_notes: str
    verified: bool = True
    name_map: dict[str, str] | None = field(default=None)


# ── The map ─────────────────────────────────────────────────────────────────
# Keyed by family. `content=""` (not None) is the universally-safe tool-call
# message field across every family (research: HF transformers #45419, vLLM).
TOOL_FAMILY_MAP: dict[str, FamilyToolProfile] = {
    "claude": FamilyToolProfile(
        tool_name_style=(
            "Native. Canonical names are identity — the `.claude/agents/*.md`"
            " `tools:` frontmatter is authored directly against them."
        ),
        call_format_notes=(
            "Native Anthropic tool_use / tool_result content blocks; no"
            ' translation needed. `content=""` is safe.'
        ),
    ),
    "copilot": FamilyToolProfile(
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
    ),
    "gemini": FamilyToolProfile(
        tool_name_style=("Pass-through — tool NAMES ride a generic tools param unchanged."),
        call_format_notes=(
            "Gemini / Gemma wrap tool-call JSON in Markdown code fences; strip"
            " the fences before parsing. Markdown headers suit the family."
        ),
    ),
    "kimi": FamilyToolProfile(
        tool_name_style=("Pass-through — tool NAMES ride a generic tools param unchanged."),
        call_format_notes=(
            "Requires `functions.{name}:{idx}` tool-call IDs and special tokens"
            " around the call (Kimi-K2 tool_call_guidance)."
        ),
    ),
    "glm": FamilyToolProfile(
        tool_name_style=("Pass-through — tool NAMES ride a generic tools param unchanged."),
        call_format_notes=(
            'Streaming tool calls need `extra_body={"tool_stream": true}` on the request.'
        ),
    ),
    "deepseek": FamilyToolProfile(
        tool_name_style=("Pass-through — tool NAMES ride a generic tools param unchanged."),
        call_format_notes=(
            "DeepSeek-V3 rejects dict args — arguments must be a JSON *string*;"
            " it also hallucinates extra schema fields, so validate strictly."
        ),
    ),
    "qwen": FamilyToolProfile(
        tool_name_style=("Pass-through — tool NAMES ride a generic tools param unchanged."),
        call_format_notes=(
            "Hermes-style tool calls; double-escapes arguments and suffers"
            " task-confusion on multi-purpose skills — keep skills"
            " strictly single-purpose."
        ),
    ),
    "mimo": FamilyToolProfile(
        tool_name_style=(
            "Pass-through assumed — tool NAMES ride a generic tools param unchanged. UNVERIFIED."
        ),
        call_format_notes=(
            "No primary portability source found (D-187-08); no live-behavior"
            " claim. Covered structurally by the neutrality lint only."
        ),
        verified=False,
    ),
}


__all__ = [
    "CANONICAL_TOOLS",
    "TOOL_FAMILY_MAP",
    "FamilyToolProfile",
]
