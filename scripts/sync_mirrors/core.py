#!/usr/bin/env python3
"""Core mirror synchronization logic.

This module owns the full discovery + generator pipeline. Per-concern
modules in this package re-export from here for organizational clarity.

Original docstring follows:

Sync command mirrors across all IDE surfaces from canonical .claude/ sources.

Canonical source (repo root):
  .claude/skills/ai-*/SKILL.md   (+ optional handlers/, references/, scripts/)
  .claude/agents/ai-*.md

Generates mirrors in:
  - .codex/skills/           (Codex IDE skills -- keep ai- prefix, + handlers/references/)
  - .codex/agents/           (Codex IDE agents -- copy as-is)
  - src/ai_engineering/templates/project/.codex/hooks.json
  - src/ai_engineering/templates/project/.codex/config.toml
  - .github/skills/          (Copilot Agent Skills -- per skill dir + handlers/)
  - .github/agents/          (GitHub Copilot agent personas)
  - src/ai_engineering/templates/project/.claude/skills/   (install template)
  - src/ai_engineering/templates/project/.claude/agents/   (install template)
  - src/ai_engineering/templates/project/.codex/skills/    (install template)
  - src/ai_engineering/templates/project/.codex/agents/    (install template)
  - src/ai_engineering/templates/project/.github/skills/   (install template)
  - src/ai_engineering/templates/project/agents/           (install template)
  - .agents/skills/ and .agents/agents/                    (Antigravity)
  - src/ai_engineering/templates/project/.agents/           (install template)

Usage:
  uv run python -m scripts.sync_mirrors            # generate all mirrors
  uv run python -m scripts.sync_mirrors --check    # verify, exit 1 on drift
  uv run python -m scripts.sync_mirrors --verbose  # show detailed info
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from ai_engineering.config.mirror_inventory import (
    get_generated_provenance_fields,
    get_internal_specialist_agent_targets,
)
from scripts.sync_mirrors.tool_name_map import TOOL_FAMILY_MAP

ROOT = Path(__file__).resolve().parent.parent.parent

# ── Canonical source paths (repo root .claude/) ──────────────────────────
CLAUDE_SKILLS = ROOT / ".claude" / "skills"
CLAUDE_AGENTS = ROOT / ".claude" / "agents"
MANIFEST_PATH = ROOT / ".ai-engineering" / "manifest.yml"
RUNBOOKS_ROOT = ROOT / ".ai-engineering" / "runbooks"

# ── Mirror surface paths ────────────────────────────────────────────────
CODEX_SKILLS = ROOT / ".codex" / "skills"
CODEX_AGENTS = ROOT / ".codex" / "agents"
ANTIGRAVITY_SKILLS = ROOT / ".agents" / "skills"
ANTIGRAVITY_AGENTS = ROOT / ".agents" / "agents"
GITHUB_SKILLS = ROOT / ".github" / "skills"
GITHUB_AGENTS = ROOT / ".github" / "agents"
# spec-128 D-128-04, D-128-07: .github/instructions/ surface deleted entirely.

# ── Template project paths (for ai-eng install) ────────────────────────
TPL_PROJECT = ROOT / "src" / "ai_engineering" / "templates" / "project"
TPL_CLAUDE_SKILLS = TPL_PROJECT / ".claude" / "skills"
TPL_CLAUDE_AGENTS = TPL_PROJECT / ".claude" / "agents"
TPL_CODEX_SKILLS = TPL_PROJECT / ".codex" / "skills"
TPL_CODEX_AGENTS = TPL_PROJECT / ".codex" / "agents"
TPL_CODEX_HOOKS = TPL_PROJECT / ".codex" / "hooks.json"
TPL_CODEX_CONFIG = TPL_PROJECT / ".codex" / "config.toml"
TPL_GITHUB_SKILLS = TPL_PROJECT / ".github" / "skills"
TPL_GITHUB_AGENTS = TPL_PROJECT / "agents"
# spec-128 Wave 4 (supersedes spec-133 D-133-06, D-133-07): install templates
# for OpenCode + Cursor + Antigravity surfaces. OpenCode, Cursor, and
# Antigravity read native skills from ``.{ide}/skills/<name>/SKILL.md`` (folder per skill, on-
# demand lazy-load by the agent). Per official Cursor 2.4+ and OpenCode docs,
# skills supersede the prior ``.cursor/rules/`` and ``.opencode/commands/``
# mappings, which were saved-prompt and always-included patterns respectively
# — wrong fit for 48 on-demand skills.
TPL_OPENCODE_SKILLS = TPL_PROJECT / ".opencode" / "skills"
TPL_OPENCODE_COMMANDS = TPL_PROJECT / ".opencode" / "commands"
TPL_OPENCODE_AGENTS = TPL_PROJECT / ".opencode" / "agents"
TPL_CURSOR_SKILLS = TPL_PROJECT / ".cursor" / "skills"
TPL_CURSOR_AGENTS = TPL_PROJECT / ".cursor" / "agents"
TPL_ANTIGRAVITY_SKILLS = TPL_PROJECT / ".agents" / "skills"
TPL_ANTIGRAVITY_AGENTS = TPL_PROJECT / ".agents" / "agents"
# spec-159 D-159-04: installer template copy of the canonical hook-scripts
# subtree. Surface 10 mirrors only the `.py` files here; the `.sh/.ps1`
# launchers in the same tree are a separate packaging concern and must never
# be orphan-deleted by this sync step.
TPL_HOOK_SCRIPTS = TPL_PROJECT.parent / ".ai-engineering" / "scripts" / "hooks"

# spec-187 follow-up (doc-twin root fix): the installer ships the
# `.ai-engineering/{reference,runbooks}/**.md` docs verbatim, so every
# canonical edit must reach its install-template twin under
# `src/ai_engineering/templates/.ai-engineering/**` or it drifts silently
# (previously caught only by full-suite byte-parity tests and hand-`cp`'d each
# wave). Surface 11 makes `dev sync` the single regen command for these twins.
#
# The allowlist is DELIBERATELY narrow: `reference/` and `runbooks/` are the
# only `.ai-engineering/**` doc trees that are byte-identical mirrors. Siblings
# such as `overrides/`, `specs/`, and `LESSONS.md` are intentionally divergent
# (generic starter template / placeholder / project-accumulated state, not a
# verbatim mirror) and MUST NOT be blanket-synced from the live tree.
CANONICAL_AIENG = ROOT / ".ai-engineering"
TPL_AIENG = TPL_PROJECT.parent / ".ai-engineering"
_DOC_TWIN_SUBTREES: tuple[str, ...] = ("reference", "runbooks")


# ── Dataclasses ─────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class AgentMeta:
    """Per-agent metadata for all mirror surfaces.

    spec-189 D-189-04: ``effort`` (cheap | mid | high) is the SOLE semantic
    source of truth for agent model selection. Every mirror surface derives
    its Claude-valid ``model:`` literal from ``effort`` via ``_effort_to_model``
    so no per-surface literal can drift from the semantic intent. The ``model``
    field is retained only to mirror the hand-typed Claude ``model:`` in
    ``.claude/agents/<name>.md`` (which is never regenerated) and is not read by
    any generator; the build-time validator cross-checks that hand-typed model
    against ``effort``.

    spec-189 D-189-06: the Copilot ``tools:`` list is split into its two honest
    halves so the canonical→VS-Code translation is sourced from a single place.
    ``copilot_renamed_tools`` holds CANONICAL tool names (a subset of
    ``CANONICAL_TOOLS``); ``generate_copilot_agent`` translates them to VS Code
    ids via ``tool_name_map`` — the translated ids live only in that map, never
    here (DRY). ``copilot_native_tools`` holds the Copilot-native context tools
    (``codebase``, ``githubRepo``, …) that have no canonical equivalent and pass
    through unchanged. The delegation ``agent`` tool is injected separately when
    ``copilot_agents`` is non-empty.
    """

    display_name: str
    description: str
    model: str
    effort: str
    color: str
    copilot_renamed_tools: tuple[str, ...]
    copilot_native_tools: tuple[str, ...]
    claude_tools: tuple[str, ...]
    copilot_agents: tuple[str, ...] = ()
    copilot_handoffs: tuple[dict, ...] = ()
    copilot_hooks: dict | None = None


# ── Copilot tool-name translation (spec-189 D-189-06) ───────────────────────
# The copilot mirror is the ONE renaming surface. Its canonical→VS-Code
# tool-name translation is sourced from the single documented map in
# ``tool_name_map`` — the translated ids (readFile, editFiles, runCommands,
# search, agent) live there, not re-encoded here (DRY). Open-weight /
# pass-through families keep canonical names, which is correct, not a gap.
_COPILOT_NAME_MAP: dict[str, str] = dict(TOOL_FAMILY_MAP["copilot"].name_map or {})


def _translate_copilot_tools(canonical_tools: tuple[str, ...]) -> set[str]:
    """Rename canonical tool names to their VS Code Copilot ids via the map."""
    return {_COPILOT_NAME_MAP[tool] for tool in canonical_tools}


# ── Agent metadata (single source for all surfaces) ────────────────────────
AGENT_METADATA: dict[str, AgentMeta] = {
    "build": AgentMeta(
        display_name="Build",
        description="Implementation across all stacks -- the only code write agent",
        model="opus",
        effort="high",
        color="blue",
        copilot_renamed_tools=("Read", "Write", "Edit", "Bash", "Glob", "Grep"),
        copilot_native_tools=(
            "codebase",
            "fetch",
            "githubRepo",
            "problems",
            "terminalLastCommand",
            "testFailures",
        ),
        claude_tools=("Read", "Write", "Edit", "Bash", "Glob", "Grep"),
        copilot_agents=("Guard", "ai-explore"),
        # send: True is required for Copilot Agent Skills handoff buttons to
        # auto-dispatch to the target agent (send: False only previews the prompt).
        copilot_handoffs=(
            {
                "label": "✅ Verify Changes",
                "agent": "Verify",
                "prompt": "Verify the implementation changes made above.",
                "send": True,
            },
            {
                "label": "🔍 Review Changes",
                "agent": "Review",
                "prompt": "Review the code changes made above.",
                "send": True,
            },
        ),
        copilot_hooks={"PostToolUse": [{"type": "command", "command": "ruff format --quiet"}]},
    ),
    "explore": AgentMeta(
        display_name="ai-explore",
        description=(
            "Context gatherer -- deep codebase research, architecture mapping,"
            " dependency tracing, pattern identification, risk surfacing."
            " Read-only."
        ),
        model="sonnet",
        effort="mid",
        color="cyan",
        copilot_renamed_tools=("Read", "Glob", "Grep"),
        copilot_native_tools=("codebase", "githubRepo"),
        claude_tools=("Read", "Glob", "Grep"),
    ),
    "advise": AgentMeta(
        display_name="Advise",
        description=(
            "Proactive governance advisor -- checks standards, decisions,"
            " and quality trends during development."
            " Never blocks, always advisory."
        ),
        model="sonnet",
        effort="mid",
        color="yellow",
        copilot_renamed_tools=("Read", "Glob", "Grep"),
        copilot_native_tools=("codebase", "githubRepo", "problems"),
        claude_tools=("Read", "Glob", "Grep"),
    ),
    "onboard": AgentMeta(
        display_name="Onboard",
        description=(
            "Developer education and onboarding -- architecture tours,"
            " decision archaeology, knowledge transfer."
        ),
        model="sonnet",
        effort="mid",
        color="cyan",
        copilot_renamed_tools=("Read", "Glob", "Grep"),
        copilot_native_tools=("codebase", "fetch", "githubRepo"),
        claude_tools=("Read", "Glob", "Grep"),
    ),
    "plan": AgentMeta(
        display_name="Plan",
        description="Advisory planning: classify scope, assess risks, and recommend pipeline",
        model="opus",
        effort="high",
        color="purple",
        copilot_renamed_tools=("Read", "Write", "Edit", "Bash", "Glob", "Grep"),
        copilot_native_tools=(
            "codebase",
            "fetch",
            "githubRepo",
            "problems",
            "terminalLastCommand",
            "testFailures",
        ),
        claude_tools=("Read", "Glob", "Grep", "Bash", "Write", "Edit"),
        copilot_agents=("ai-explore", "Guard"),
        copilot_handoffs=(
            {
                "label": "▶ Dispatch Implementation",
                "agent": "Autopilot",
                "prompt": "Execute the plan outlined above following the approved spec.",
                "send": True,
            },
        ),
    ),
    "review": AgentMeta(
        display_name="Review",
        description=(
            "Code review orchestrator -- dispatches specialist agents"
            " for deep parallel review with context isolation."
        ),
        model="opus",
        effort="high",
        color="red",
        copilot_renamed_tools=("Read", "Glob", "Grep"),
        copilot_native_tools=("codebase", "githubRepo", "problems"),
        claude_tools=("Read", "Glob", "Grep", "Bash", "Agent"),
        copilot_agents=("ai-explore",),
        copilot_handoffs=(
            {
                "label": "🔧 Fix Issues",
                "agent": "Build",
                "prompt": "Fix the issues identified in the review above.",
                "send": True,
            },
        ),
    ),
    "simplify": AgentMeta(
        display_name="Simplifier",
        description=(
            "Background code simplifier -- guard clauses, extract methods,"
            " flatten nesting, remove dead code."
            " Runs post-build or continuous."
        ),
        model="sonnet",
        effort="mid",
        color="green",
        copilot_renamed_tools=("Read", "Edit", "Bash", "Glob", "Grep"),
        copilot_native_tools=("codebase", "problems", "testFailures"),
        claude_tools=("Read", "Glob", "Grep", "Edit"),
    ),
    "verify": AgentMeta(
        display_name="Verify",
        description=(
            "Evidence-first verification orchestrator -- dispatches"
            " deterministic + LLM judgment agents for merge readiness."
        ),
        model="opus",
        effort="high",
        color="green",
        copilot_renamed_tools=("Read", "Bash", "Glob", "Grep"),
        copilot_native_tools=("codebase", "githubRepo", "problems"),
        claude_tools=("Read", "Glob", "Grep", "Bash", "Agent"),
        copilot_agents=("ai-explore",),
        copilot_handoffs=(
            {
                "label": "🔧 Fix Issues",
                "agent": "Build",
                "prompt": "Fix the issues identified in the verification above.",
                "send": True,
            },
        ),
    ),
    "autopilot": AgentMeta(
        display_name="Autopilot",
        description=(
            "Autonomous multi-spec orchestrator -- splits large specs into"
            " focused sub-specs, executes sequentially with fresh-context"
            " agents, verifies anti-hallucination gates, delivers via PR."
        ),
        model="opus",
        effort="high",
        color="purple",
        copilot_renamed_tools=("Read", "Bash", "Glob", "Grep"),
        copilot_native_tools=("codebase", "githubRepo"),
        claude_tools=("Read", "Glob", "Grep", "Bash"),
        copilot_agents=("Build", "ai-explore", "Verify", "Plan", "Guard"),
        copilot_handoffs=(
            {
                "label": "📋 Create PR",
                "agent": "agent",
                "prompt": "Create a PR with the changes from the autopilot execution.",
                "send": True,
            },
        ),
    ),
    # Note: `run-orchestrator` AgentMeta deleted per spec-127 D-127-12.
    # Functionality absorbed by `ai-autopilot --backlog --source <github|ado|local>`.
}


# ── effort <-> model mapping (spec-189 D-189-04) ─────────────────────────────
# ``effort`` is the SOLE semantic source of truth for agent model selection.
# Every mirror surface derives its Claude-valid ``model:`` literal from
# ``effort`` through this ONE mapping so no per-surface model literal can drift
# from the semantic intent. The build-time validator (``validate_canonical``)
# cross-checks each hand-typed ``.claude/agents/<name>.md`` ``model:`` against
# the model derived from ``AGENT_METADATA[name].effort``.
_EFFORT_TO_MODEL: dict[str, str] = {
    "high": "opus",
    "mid": "sonnet",
    "cheap": "haiku",
}
_MODEL_TO_EFFORT: dict[str, str] = {model: effort for effort, model in _EFFORT_TO_MODEL.items()}
VALID_EFFORTS: frozenset[str] = frozenset(_EFFORT_TO_MODEL)


def _effort_to_model(effort: str) -> str:
    """Map a semantic ``effort`` (cheap|mid|high) to its Claude-valid model literal."""
    try:
        return _EFFORT_TO_MODEL[effort]
    except KeyError:
        raise ValueError(
            f"unknown effort {effort!r}; expected one of {sorted(_EFFORT_TO_MODEL)}"
        ) from None


def _model_to_effort(model: str) -> str:
    """Map a Claude-valid model literal (opus|sonnet|haiku) back to its ``effort``."""
    try:
        return _MODEL_TO_EFFORT[model]
    except KeyError:
        raise ValueError(
            f"unknown model {model!r}; expected one of {sorted(_MODEL_TO_EFFORT)}"
        ) from None


def _effort_model_for_agent(name: str, fallback: str | None) -> str | None:
    """Return the effort-derived ``model:`` for a registered agent, else ``fallback``.

    spec-189 D-189-04: mirror surfaces derive ``model:`` from the single
    ``effort`` source. Specialist agents (no ``AgentMeta``) are not
    effort-governed and keep their canonical passthrough ``model:``.
    """
    meta = AGENT_METADATA.get(name)
    if meta is None:
        return fallback
    return _effort_to_model(meta.effort)


# ── Cross-reference validation targets ──────────────────────────────────────
# spec-128 D-128-07: lang instructions generator surface removed.
# AGENTS.md (next surface) and copilot-instructions.md provide instruction
# coverage per GitHub Copilot official guidance.


_FALLBACK_CROSS_REFERENCE_FILES: list[Path] = [
    ROOT / "CLAUDE.md",
    ROOT / "AGENTS.md",
    ROOT / ".github" / "copilot-instructions.md",
]


def _resolve_cross_reference_files(target: Path) -> list[Path]:
    """Return enabled root instruction surfaces for cross-reference validation.

    Uses the manifest Surface set when available so Surface-specific root
    provider-specific root files are validated only when they are actually enabled.
    Falls back to the historical hardcoded list when the manifest is absent.
    """
    manifest_path = target / ".ai-engineering" / "manifest.yml"
    if not manifest_path.is_file():
        return list(_FALLBACK_CROSS_REFERENCE_FILES)

    from ai_engineering.config.loader import load_manifest_config
    from ai_engineering.installer.templates import resolve_instruction_file_destinations

    cfg = load_manifest_config(target)
    return [
        target / destination
        for destination in resolve_instruction_file_destinations(
            cfg.surfaces.enabled,
            root_entry_points=cfg.ownership.root_entry_points,
            include_mirror_paths=True,
        )
    ]


# ═══════════════════════════════════════════════════════════════════════════
# Canonical content helpers
# ═══════════════════════════════════════════════════════════════════════════


def read_body(path: Path) -> str:
    """Read a markdown file and return the body (without YAML frontmatter)."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return text
    end = text.find("---", 3)
    if end == -1:
        return text
    body_start = end + 3
    if body_start < len(text) and text[body_start] == "\n":
        body_start += 1
    return text[body_start:]


def read_frontmatter(path: Path) -> dict:
    """Read a markdown file and return the parsed YAML frontmatter dict."""
    import yaml

    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    fm_text = text[3:end].strip()
    return yaml.safe_load(fm_text) or {}


def _serialize_frontmatter(data: dict) -> str:
    """Serialize a frontmatter dict to YAML string (between --- fences)."""
    ordered_keys = [
        "name",
        "description",
        "model",
        "effort",
        "color",
        "argument-hint",
        "disable-model-invocation",
        "user-invocable",
        "allowed-tools",
        "mode",
        "version",
        "tags",
        "requires",
        "tools",
    ]
    lines = ["---"]
    for key in ordered_keys:
        if key in data:
            lines.append(_format_yaml_field(key, data[key]))
    for key in data:
        if key not in ordered_keys:
            lines.append(_format_yaml_field(key, data[key]))
    lines.append("---")
    return "\n".join(lines)


def _format_yaml_field(key: str, value) -> str:
    """Format a single YAML field for frontmatter."""
    if isinstance(value, str):
        if any(c in value for c in ":#{}[]|>&*!%@`"):
            return f'{key}: "{value}"'
        return f"{key}: {value}"
    if isinstance(value, list):
        items = ", ".join(str(v) for v in value)
        return f"{key}: [{items}]"
    if isinstance(value, dict):
        import yaml

        block = yaml.dump({key: value}, default_flow_style=False, allow_unicode=True).rstrip()
        return block
    return f"{key}: {value}"


# ── Cross-reference path translation ────────────────────────────────────────
# Matches .claude/skills/ai-X/SKILL.md and .claude/agents/ai-X.md references
_XREF_CLAUDE_SKILL = re.compile(r"(`?)\.claude/skills/ai-([^/`\s]+)/SKILL\.md(`?)")
_XREF_CLAUDE_AGENT = re.compile(r"(`?)\.claude/agents/ai-([^.`\s]+)\.md(`?)")


def translate_refs(content: str, target_ide: str) -> str:
    """Translate .claude/ path references to target IDE paths.

    Canonical form: .claude/skills/ai-X/SKILL.md, .claude/agents/ai-X.md
    Target surfaces:
      - codex (.codex/): .codex/skills/ai-X/SKILL.md, .codex/agents/ai-X.md
      - cursor (.cursor/): .cursor/skills/ai-X/SKILL.md, .cursor/agents/ai-X.mdc
      - antigravity (.agents/): .agents/skills/ai-X/SKILL.md, .agents/agents/ai-X.md
      - copilot (.github/): .github/skills/ai-X/SKILL.md, .github/agents/X.agent.md
      - claude: unchanged (canonical)
    """
    if target_ide == "claude":
        return content

    def _replace_skill(m: re.Match[str]) -> str:
        bt = m.group(1)
        name = m.group(2)
        if target_ide == "codex":
            path = f".codex/skills/ai-{name}/SKILL.md"
        elif target_ide == "cursor":
            path = f".cursor/skills/ai-{name}/SKILL.md"
        elif target_ide == "antigravity":
            path = f".agents/skills/ai-{name}/SKILL.md"
        else:  # copilot
            path = f".github/skills/ai-{name}/SKILL.md"
        return f"{bt}{path}{bt}" if bt else path

    def _replace_agent(m: re.Match[str]) -> str:
        bt = m.group(1)
        name = m.group(2)
        if target_ide == "codex":
            path = f".codex/agents/ai-{name}.md"
        elif target_ide == "cursor":
            path = f".cursor/agents/ai-{name}.mdc"
        elif target_ide == "antigravity":
            path = f".agents/agents/ai-{name}.md"
        else:  # copilot
            # Spec-107 D-107-03: explore is renamed to ai-explore for cross-IDE
            # parity. Other Copilot agents keep bare slugs (build.agent.md etc.).
            copilot_slug = f"ai-{name}" if name == "explore" else name
            path = f".github/agents/{copilot_slug}.agent.md"
        return f"{bt}{path}{bt}" if bt else path

    content = _XREF_CLAUDE_SKILL.sub(_replace_skill, content)
    content = _XREF_CLAUDE_AGENT.sub(_replace_agent, content)

    # Subpath and bare-prefix references under ai-* skills/agents
    # (handlers/, references/, scripts/, shell variables like
    # `.claude/skills/ai-${SKILL_NAME}`, etc.). The XREF_CLAUDE_SKILL regex
    # only matches the canonical SKILL.md reference; everything else needs
    # explicit rewrite. The bare-prefix rewrite runs second so the
    # subpath rewrite (with trailing `/`) wins where applicable.
    ide_target_map = {
        "codex": ".codex",
        "cursor": ".cursor",
        "antigravity": ".agents",
        "copilot": ".github",
    }
    target_root = ide_target_map.get(target_ide)
    if target_root:
        content = re.sub(r"\.claude/skills/(ai-[^/\s`]+/)", rf"{target_root}/skills/\1", content)
        content = re.sub(r"\.claude/agents/(ai-[^/\s`]+/)", rf"{target_root}/agents/\1", content)
        # Bare prefix: `.claude/skills/ai-X` (no trailing slash, e.g. shell
        # variable expansions like `.claude/skills/ai-${VAR}`). Use a
        # negative-lookahead so we don't double-rewrite paths that already
        # had their subpath segment rewritten by the rules above.
        content = re.sub(r"\.claude/skills/(ai-[^/\s`]+)", rf"{target_root}/skills/\1", content)
        content = re.sub(r"\.claude/agents/(ai-[^/\s`]+)", rf"{target_root}/agents/\1", content)
        # spec-187 D-187-04: specialist agents (reviewer-*/verifier-*/review-*/
        # verify-*) live under <surface>/agents/internal/ in every mirror tree;
        # the flat forwarder stubs were hard-deleted. Route references there so
        # regeneration yields no dangling flat-path ref. Must run before the
        # broad `.claude/agents/(?!ai-)` directory translation below.
        content = re.sub(
            r"\.claude/agents/((?:reviewer|verifier|review|verify)-[^/\s`]+\.md)",
            rf"{target_root}/agents/internal/\1",
            content,
        )

    # Spec-107 D-107-03: explore agent reference path adjustment for copilot.
    # The block path translations below (.claude/agents/ -> .github/agents/)
    # run on raw `.claude/agents/explore.md` references that miss the canonical
    # `ai-` prefix; rewrite them to the canonical Copilot filename now.
    if target_ide == "copilot":
        content = re.sub(
            r"\.github/agents/explore\.agent\.md",
            ".github/agents/ai-explore.agent.md",
            content,
        )

    # Directory path translations (broader patterns -- run AFTER specific file translations)
    if target_ide == "codex":
        # .claude/skills/ -> .codex/skills/
        content = re.sub(r"\.claude/skills/(?!ai-)", ".codex/skills/", content)
        # .claude/agents/ -> .codex/agents/
        content = re.sub(r"\.claude/agents/(?!ai-)", ".codex/agents/", content)
    elif target_ide == "cursor":
        content = re.sub(r"\.claude/skills/(?!ai-)", ".cursor/skills/", content)
        content = re.sub(r"\.claude/agents/(?!ai-)", ".cursor/agents/", content)
    elif target_ide == "antigravity":
        content = re.sub(r"\.claude/skills/(?!ai-)", ".agents/skills/", content)
        content = re.sub(r"\.claude/agents/(?!ai-)", ".agents/agents/", content)
    elif target_ide == "copilot":
        # .claude/skills/ -> .github/skills/
        content = re.sub(r"\.claude/skills/(?!ai-)", ".github/skills/", content)
        # .claude/agents/ -> .github/agents/
        content = re.sub(r"\.claude/agents/(?!ai-)", ".github/agents/", content)

    return content


# ═══════════════════════════════════════════════════════════════════════════
# Discovery (from canonical .claude/ sources)
# ═══════════════════════════════════════════════════════════════════════════


def parse_frontmatter_simple(path: Path) -> dict[str, str]:
    """Extract YAML frontmatter fields from a markdown file.

    Uses full YAML parsing to handle complex values (lists, nested dicts)
    then flattens to string values for the discovery interface.
    """
    fm = read_frontmatter(path)
    # Flatten to strings for compatibility with discovery interface
    result: dict[str, str] = {}
    for key, value in fm.items():
        if isinstance(value, str):
            result[key] = value
        elif isinstance(value, list):
            result[key] = ", ".join(str(v) for v in value)
        elif value is not None:
            result[key] = str(value)
    return result


def is_copilot_compatible(skill_path: Path) -> bool:
    """Return True if the skill's frontmatter does not opt out of Copilot."""
    fm = read_frontmatter(skill_path)
    return str(fm.get("copilot_compatible", "true")).lower() != "false"


def discover_skills() -> list[tuple[str, dict[str, str], Path]]:
    """Discover all skills from .claude/skills/ai-*/SKILL.md.

    Returns (name, frontmatter, skill_file_path) tuples.
    Name is the bare name without the ai- prefix.
    """
    skills = []
    for skill_dir in sorted(CLAUDE_SKILLS.iterdir()):
        if not skill_dir.is_dir() or not skill_dir.name.startswith("ai-"):
            continue
        skill_file = skill_dir / "SKILL.md"
        if skill_file.is_file():
            fm = parse_frontmatter_simple(skill_file)
            # Strip ai- prefix for the bare name
            bare_name = skill_dir.name.removeprefix("ai-")
            skills.append((bare_name, fm, skill_file))
    return skills


def discover_shared_handlers() -> list[tuple[str, Path]]:
    """Discover shared handlers from .claude/skills/_shared/*.md.

    Shared handlers are NOT user-invocable skills; they are reusable
    instruction modules consumed by orchestrator skills (dispatch,
    autopilot, run). They are mirrored byte-for-byte across IDE surfaces
    so cross-IDE consumers see the same kernel.

    Returns (relative_path, absolute_path) tuples sorted by path.
    """
    shared_root = CLAUDE_SKILLS / "_shared"
    if not shared_root.is_dir():
        return []
    handlers: list[tuple[str, Path]] = []
    for f in sorted(shared_root.rglob("*")):
        if f.is_file() and f.suffix == ".md":
            handlers.append((f.relative_to(shared_root).as_posix(), f))
    return handlers


def discover_agents() -> list[tuple[str, dict[str, str], Path]]:
    """Discover all agents from .claude/agents/ai-*.md.

    Returns (name, frontmatter, agent_file_path) tuples.
    Name is the bare name without the ai- prefix.
    """
    agents = []
    for agent_file in sorted(CLAUDE_AGENTS.glob("ai-*.md")):
        fm = parse_frontmatter_simple(agent_file)
        bare_name = agent_file.stem.removeprefix("ai-")
        agents.append((bare_name, fm, agent_file))
    return agents


# Specialist agent prefixes dispatched by orchestrators (not user-facing).
_SPECIALIST_PREFIXES = ("reviewer-", "verifier-", "review-", "verify-")


def discover_specialist_agents() -> list[Path]:
    """Discover specialist agents from .claude/agents/ (non-ai-* prefix).

    These are sub-agents dispatched by orchestrator agents (ai-review, ai-verify).
    They are mirrored into provider-local internal roots with generated provenance.
    """
    specialists = []
    for agent_file in sorted(CLAUDE_AGENTS.glob("*.md")):
        if agent_file.stem.startswith("ai-"):
            continue
        if any(agent_file.stem.startswith(p) for p in _SPECIALIST_PREFIXES):
            specialists.append(agent_file)
    return specialists


def discover_handlers(skill_dir: Path) -> list[tuple[str, Path]]:
    """Discover handler files under a skill's handlers/ directory.

    Returns (handler_name, handler_path) tuples sorted by name.
    """
    handlers_dir = skill_dir / "handlers"
    if not handlers_dir.is_dir():
        return []
    handlers = []
    for handler_file in sorted(handlers_dir.glob("*.md")):
        handlers.append((handler_file.stem, handler_file))
    return handlers


def discover_resources(skill_dir: Path) -> list[tuple[str, Path]]:
    """Discover resource files at the skill root (non-SKILL.md markdown files).

    Returns (filename, path) tuples sorted by name.
    """
    resources = []
    for f in sorted(skill_dir.glob("*.md")):
        if f.is_file() and f.name != "SKILL.md":
            resources.append((f.name, f))
    return resources


def discover_reference_files(skill_dir: Path) -> list[tuple[str, Path]]:
    """Discover files under a skill's references/ directory.

    Returns (relative_path, absolute_path) tuples sorted by path.
    Relative paths use POSIX separators so they can be joined onto
    target mirror directories without additional normalization.
    """
    references_dir = skill_dir / "references"
    if not references_dir.is_dir():
        return []
    references = []
    for ref_file in sorted(references_dir.rglob("*")):
        if ref_file.is_file():
            references.append((ref_file.relative_to(references_dir).as_posix(), ref_file))
    return references


def discover_scripts(skill_dir: Path) -> list[tuple[str, Path]]:
    """Discover script files under a skill's scripts/ directory.

    Returns (script_name, script_path) tuples sorted by name.
    """
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return []
    scripts = []
    for script_file in sorted(scripts_dir.glob("*")):
        if script_file.is_file():
            scripts.append((script_file.name, script_file))
    return scripts


# ═══════════════════════════════════════════════════════════════════════════
# Generation -- .codex/skills/ (Codex IDE)
# ═══════════════════════════════════════════════════════════════════════════


def generate_codex_skill(name: str, skill_path: Path) -> str:
    """Generate .codex/skills/ai-<name>/SKILL.md -- translated refs, keep ai- prefix."""
    fm = read_frontmatter(skill_path)
    body = read_body(skill_path)

    # Keep ai- prefix for skills in .codex/ surface
    fm["name"] = f"ai-{name}"
    fm.pop("metadata", None)
    fm.update(
        get_generated_provenance_fields(
            "codex-skills",
            canonical_source=f".claude/skills/ai-{name}/SKILL.md",
        )
    )

    header = _serialize_frontmatter(fm)
    body = translate_refs(body, "codex")

    return f"{header}\n\n{body.rstrip()}\n"


def generate_codex_agent(name: str, agent_path: Path) -> str:
    """Generate .codex/agents/ai-<name>.md -- translated refs."""
    fm = read_frontmatter(agent_path)
    body = read_body(agent_path)

    # Keep ai- prefix for agents in .codex/ surface
    fm.pop("tools", None)  # tools are IDE-specific
    fm.pop("metadata", None)
    # spec-189 D-189-04: derive model: from the single `effort` source so all
    # surfaces share one derivation. Specialists (no AgentMeta) keep canonical.
    derived_model = _effort_model_for_agent(name, fm.get("model"))
    if derived_model is not None:
        fm["model"] = derived_model
    fm.update(
        get_generated_provenance_fields(
            "codex-agents",
            canonical_source=f".claude/agents/ai-{name}.md",
        )
    )

    header = _serialize_frontmatter(fm)
    body = translate_refs(body, "codex")

    return f"{header}\n\n{body.rstrip()}\n"


# ═══════════════════════════════════════════════════════════════════════════
# Generation -- translated markdown+frontmatter surfaces
# ═══════════════════════════════════════════════════════════════════════════


def _generate_translated_skill(
    name: str, skill_path: Path, *, target_ide: str, family_id: str
) -> str:
    """Generate an agent skill for a markdown+frontmatter surface."""
    fm = read_frontmatter(skill_path)
    body = read_body(skill_path)

    fm["name"] = f"ai-{name}"
    fm.pop("metadata", None)
    fm.update(
        get_generated_provenance_fields(
            family_id,
            canonical_source=f".claude/skills/ai-{name}/SKILL.md",
        )
    )

    header = _serialize_frontmatter(fm)
    body = translate_refs(body, target_ide)

    return f"{header}\n\n{body.rstrip()}\n"


def _generate_translated_agent(
    name: str, agent_path: Path, *, target_ide: str, family_id: str
) -> str:
    """Generate an agent persona for a markdown+frontmatter surface."""
    fm = read_frontmatter(agent_path)
    body = read_body(agent_path)

    fm.pop("tools", None)  # tools are IDE-specific
    fm.pop("metadata", None)
    fm.pop("color", None)  # not in Cursor/Antigravity schemas
    # spec-189 D-189-04: derive model: from the single `effort` source so all
    # surfaces share one derivation. Specialists (no AgentMeta) keep canonical.
    derived_model = _effort_model_for_agent(name, fm.get("model"))
    if derived_model is not None:
        fm["model"] = derived_model
    fm.update(
        get_generated_provenance_fields(
            family_id,
            canonical_source=f".claude/agents/ai-{name}.md",
        )
    )

    header = _serialize_frontmatter(fm)
    body = translate_refs(body, target_ide)

    return f"{header}\n\n{body.rstrip()}\n"


def generate_cursor_skill(name: str, skill_path: Path) -> str:
    """Generate .cursor/skills/ai-<name>/SKILL.md."""
    return _generate_translated_skill(
        name, skill_path, target_ide="cursor", family_id="cursor-skills"
    )


def generate_cursor_agent(name: str, agent_path: Path) -> str:
    """Generate .cursor/agents/ai-<name>.mdc."""
    return _generate_translated_agent(
        name, agent_path, target_ide="cursor", family_id="cursor-agents"
    )


def generate_antigravity_skill(name: str, skill_path: Path) -> str:
    """Generate .agents/skills/ai-<name>/SKILL.md."""
    return _generate_translated_skill(
        name,
        skill_path,
        target_ide="antigravity",
        family_id="antigravity-skills",
    )


def generate_antigravity_agent(name: str, agent_path: Path) -> str:
    """Generate .agents/agents/ai-<name>.md."""
    return _generate_translated_agent(
        name,
        agent_path,
        target_ide="antigravity",
        family_id="antigravity-agents",
    )


# ═══════════════════════════════════════════════════════════════════════════
# Generation -- .github/skills/ and .github/agents/ (Copilot)
# ═══════════════════════════════════════════════════════════════════════════


def generate_copilot_skill(name: str, skill_path: Path) -> str:
    """Generate .github/skills/ai-<name>/SKILL.md -- directory-based Agent Skill.

    Keeps SKILL.md as a standalone file. Handlers are copied separately.
    """
    fm = read_frontmatter(skill_path)
    body = read_body(skill_path)

    # Adapt frontmatter for Copilot Agent Skills
    fm["name"] = f"ai-{name}"
    fm["mode"] = "agent"
    fm.pop("metadata", None)
    fm.update(
        get_generated_provenance_fields(
            "copilot-skills",
            canonical_source=f".claude/skills/ai-{name}/SKILL.md",
        )
    )

    header = _serialize_frontmatter(fm)
    body = translate_refs(body, "copilot")

    return f"{header}\n\n{body.rstrip()}\n"


def generate_copilot_handler(handler_path: Path) -> str:
    """Generate a handler file for .github/skills/ai-<name>/handlers/."""
    content = handler_path.read_text(encoding="utf-8")
    return translate_refs(content, "copilot")


def generate_copilot_agent(name: str, meta: AgentMeta, agent_path: Path) -> str:
    """Generate .github/agents/<name>.agent.md with full embedded content."""
    import yaml

    body = read_body(agent_path)
    body = translate_refs(body, "copilot")

    # Build tools list — translate canonical renamed tools via the single
    # `tool_name_map` source, merge the Copilot-native context tools, then
    # inject the delegation `agent` tool (also map-sourced) when subagents are
    # declared. spec-189 D-189-06: the translated ids live only in the map.
    tools = sorted(
        _translate_copilot_tools(meta.copilot_renamed_tools) | set(meta.copilot_native_tools)
    )
    if meta.copilot_agents:
        tools.append(_COPILOT_NAME_MAP["Agent"])
    tools_str = ", ".join(tools)

    # ``color`` is intentionally omitted: GitHub Copilot's documented
    # custom-agents schema (name/description/target/tools/model/mcp-servers/
    # metadata/handoffs) does not include color. Stripping here mirrors
    # the Cursor/Antigravity policy applied in translated-agent generators.
    lines = [
        "---",
        f'name: "{meta.display_name}"',
        f'description: "{meta.description}"',
        # spec-189 D-189-04: derive model: from the single `effort` source.
        f"model: {_effort_to_model(meta.effort)}",
        f"tools: [{tools_str}]",
    ]

    if meta.copilot_agents:
        agents_str = ", ".join(meta.copilot_agents)
        lines.append(f"agents: [{agents_str}]")

    if meta.copilot_handoffs:
        handoffs_yaml = yaml.dump(
            {"handoffs": [dict(h) for h in meta.copilot_handoffs]},
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        ).rstrip()
        lines.append(handoffs_yaml)

    if meta.copilot_hooks is not None:
        hooks_yaml = yaml.dump(
            {"hooks": meta.copilot_hooks},
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        ).rstrip()
        lines.append(hooks_yaml)

    provenance = get_generated_provenance_fields(
        "copilot-agents",
        canonical_source=f".claude/agents/ai-{name}.md",
    )
    for key, value in provenance.items():
        lines.append(f"{key}: {value}")

    lines.append("---")

    return "\n".join(lines) + f"\n\n{body.rstrip()}\n"


def generate_specialist_agent(agent_path: Path) -> str:
    """Generate an internal specialist agent mirror with governed provenance."""
    fm = read_frontmatter(agent_path)
    body = read_body(agent_path)
    fm.update(
        get_generated_provenance_fields(
            "specialist-agents",
            canonical_source=f".claude/agents/{agent_path.name}",
        )
    )

    return f"{_serialize_frontmatter(fm)}\n\n{body.rstrip()}\n"


# ═══════════════════════════════════════════════════════════════════════════
# Generation -- AGENTS.md (from CLAUDE.md as canonical source)
# ═══════════════════════════════════════════════════════════════════════════

# Don't item 7 references .claude/settings.json -- Claude-specific, strip for generic IDE
_DONT_ITEM_7_RE = re.compile(
    r"^\d+\.\s+\*\*NEVER\*\*\s+disable or modify\s+`\.claude/settings\.json`\s+deny rules\.\n",
    re.MULTILINE,
)
_SKILLS_HEADER_RE = re.compile(r"^## Skills \(\d+\)$", re.MULTILINE)
_SOURCE_OF_TRUTH_SKILLS_RE = re.compile(
    r"^\| Skills \(\d+\) \| `[^`]+` \|$",
    re.MULTILINE,
)
_SOURCE_OF_TRUTH_AGENTS_RE = re.compile(
    r"^\| Agents \(\d+\) \| `[^`]+` \|$",
    re.MULTILINE,
)


def read_canonical_payload(template_root: Path = TPL_PROJECT) -> str:
    """Read the canonical "how AI works in this repo" payload from CANONICAL.md.

    spec-131 D-131-14 / D-131-03: the four IDE-native mirrors (AGENTS.md,
    CLAUDE.md, .github/copilot-instructions.md) share a single
    canonical payload sourced from
    ``src/ai_engineering/templates/project/CANONICAL.md``. Each mirror
    appends an optional ``<!-- ide-extras:start -->…<!-- ide-extras:end -->``
    fence carrying content unique to that IDE; the fence is stripped by
    ``tools/skill_lint/checks/md_mirror.py`` before sha256 equivalence.

    spec-134 sub-005 mirror diet: the §10 Engineering Principles, §14
    Strict Content Contracts, §15 IDE-Extras Escape Hatch, and §16
    Surface Axioms prose moved out of CANONICAL.md into ``docs/``
    (``principles.md`` / ``mirror-authoring.md`` / ``surface-axioms.md``).
    The mirrors now carry only pointer rows referencing those homes.

    The payload still carries ``__SKILL_COUNT__`` / ``__AGENT_COUNT__``
    placeholders — substitution happens in ``assemble_mirror_payload``.
    """
    canonical_md = template_root / "CANONICAL.md"
    if not canonical_md.is_file():
        raise FileNotFoundError(
            f"CANONICAL.md not found at {canonical_md} — "
            "spec-131 S1 requires this template as the canonical source"
        )
    return canonical_md.read_text(encoding="utf-8")


def assemble_mirror_payload(
    canonical_payload: str,
    ide_extras: str,
    *,
    skill_count: int,
    agent_count: int,
) -> str:
    """Interpolate counts and append the IDE-extras fence.

    spec-131 D-131-14: every mirror is canonical_payload + optional
    fenced extras. AGENTS.md passes ``ide_extras=""`` (it is the base
    mirror). CLAUDE.md / copilot-instructions.md pass their
    IDE-specific content as a single string that gets wrapped in the
    fence.

    The canonical payload carries one terminal empty
    ``<!-- ide-extras:start --><!-- ide-extras:end -->`` placeholder
    pair (sync contract: exactly one placeholder per file at
    end-of-file) — this helper replaces that placeholder with the
    actual fenced content (or strips it entirely when ``ide_extras``
    is empty, since AGENTS.md is the base mirror). The fence-contract
    documentation lives in ``.ai-engineering/reference/mirror-authoring.md``
    (spec-134 sub-005 mirror diet + spec-136 D-136-04; §10.4 DRY — one
    canonical home).
    """
    substituted = canonical_payload.replace("__SKILL_COUNT__", str(skill_count)).replace(
        "__AGENT_COUNT__", str(agent_count)
    )
    if ide_extras.strip():
        replacement = (
            "<!-- ide-extras:start -->\n" + ide_extras.rstrip() + "\n<!-- ide-extras:end -->"
        )
    else:
        replacement = "<!-- ide-extras:start -->\n<!-- ide-extras:end -->"
    return substituted.replace(
        "<!-- ide-extras:start -->\n<!-- ide-extras:end -->",
        replacement,
        1,
    )


# ── IDE-extras boilerplate per surface (spec-131 D-131-14) ────────────
# Each block is a single fenced payload appended after the canonical
# body. The fence itself is added by ``assemble_mirror_payload``.

_CLAUDE_EXTRAS = """\
## Hot-Path Discipline (Claude Code)

Claude Code triggers pre-commit and pre-push hooks on every save and
commit, so the deterministic gate must finish fast:

- **Pre-commit budget**: under 1 second wall-clock (lint, format check,
  secret scan on staged hunks only).
- **Pre-push budget**: under 5 seconds for residual checks before the
  push pipeline takes over.
- **Heavier work belongs in CI**: full test suite, dependency audit, and
  governance evaluation never run on the local hot path.

If a check exceeds budget, profile it and move work off the hot path
before adding new logic to the hook.

## Hooks Configuration (Claude Code)

Claude Code reads hook wiring from `.claude/settings.json`. The project
registers **11 canonical hook events** (audited in spec-122-d D-122-27,
CI-guarded by `tests/unit/hooks/test_canonical_events_count.py`):
`UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PostToolUseFailure`,
`Stop`, `PreCompact`, `PostCompact`, `SessionStart`, `SubagentStop`,
`Notification`, `SessionEnd`.

Hook scripts live under `.ai-engineering/scripts/hooks/` (canonical).
`.claude/hooks/` is a read-only symlink to that directory. Hook bytes
are pinned in `.ai-engineering/state/hooks-manifest.json` (sha256 per
script); `run_hook_safe` enforces integrity per
`AIENG_HOOK_INTEGRITY_MODE` (default `enforce`).

## Runtime Layer Tunables

```
# Established
AIENG_TOOL_OFFLOAD_BYTES         # default 16384
AIENG_LOOP_WINDOW                # default 6
AIENG_RALPH_MAX_RETRIES          # default 5
AIENG_RALPH_BLOCK                # default 0 (observe-only)
AIENG_HOOK_INTEGRITY_MODE        # default enforce

# spec-139 M1 — concurrency budget primitive
AIENG_MAX_WAVE_AGENTS            # default auto (floor=2, ceiling=6)
AIENG_MAX_QUALITY_AGENTS         # default 3 (Phase 5 assessor cap)
AIENG_MAX_THREAD_WORKERS         # default 4 (orchestrator ThreadPoolExecutor cap)

# spec-139 M5 — hook hot-path cache/debounce controls
AIENG_HOOK_CACHE_TTL_SEC            # default 300 (IOC/decision cache TTL seconds)
AIENG_AUTOFORMAT_DEBOUNCE_SEC       # default 1.0 (per-file formatter debounce seconds)

# spec-139 M6 — SessionEnd rotation controls
AIENG_RUNTIME_ROTATE_THROTTLE_SEC   # default 3600 (1 hour throttle)
AIENG_NDJSON_MAX_LINES              # default 100000 (rotation signal line cap)
AIENG_NDJSON_MAX_BYTES              # default 52428800 (rotation signal byte cap; 50 MiB)

# spec-147 G2 — escape-hatch toggles + overrides (behavior-changing; unset = the safe/standard path)
AIENG_RALPH_DISABLED                # set "1" to disable the Ralph Stop-loop guard
AIENG_RISK_ACCUMULATOR_DISABLED     # set "1" to disable the risk accumulator
AIENG_INSTINCT_BATCH_DISABLED       # set "1" to disable instinct batch extraction
AIENG_TELEMETRY_DEBUG               # set "1" to enable verbose telemetry logging
AIENG_HOOK_ENGINE                   # override the detected IDE engine (unset -> claude_code)
AIENG_HOOK_ENGINE_DEFAULT           # fallback engine label when none is detected (unset -> unknown)
AIENG_EVENT_SIDECAR_BYTES           # 3072 bytes; event sidecar threshold
AIE_MCP_HEALTH_FAIL_OPEN            # "1" pass-through MCP health gate; SECURITY RISK
AIENG_IOC_FAIL_CLOSED               # set "1" to deny on a missing/corrupt iocs.json (default off)

# spec-182 — governed-git advisory nudge
AIENG_GOVERNED_GIT_ADVISOR_DISABLED  # "1" disables the raw-git advisory (PreToolUse:Bash)

# spec-190 D-190-02 — error/integrity storm coalescer
AIENG_ERROR_STORM_THRESHOLD         # default 20; repeated errors raise a storm alarm
                                  # in the AIENG_HOOK_CACHE_TTL_SEC window

# spec-175 — /ai-research Tier 3 deep-research (notebooklm-py CLI)
AIENG_RESEARCH_NLM_WAIT_SEC         # default 300 (ceiling 900; bounded harvest wait)
AIENG_RESEARCH_NLM_DEEP_TIMEOUT_SEC  # default 1800; ceiling 7200 for the detached job

# Reserved roadmap — not implemented
AIENG_HOST_PREFLIGHT_DISABLED       # reserved spec-139 M2
AIENG_HOST_PREFLIGHT_MIN_FREE_MB    # reserved spec-139 M2
AIENG_HOST_PREFLIGHT_MAX_PRESSURE_PCT  # reserved spec-139 M2
AIENG_HOOK_BUDGET_PROFILE           # reserved spec-139 M5
```

State lives under `.ai-engineering/runtime/` (gitignored — session
state, not source of truth).

## Token Efficiency

- Use `/clear` aggressively when context is no longer load-bearing.
- Dispatch `ai-explore` for deep codebase research (read-only, fresh
  context).
- Cite files with `startLine:endLine:filepath`; never paste large code
  blocks the user did not ask for.

## Optional: Engram (third-party memory)

`ai-engineering` ships without a built-in memory layer. Engram is a
peer product maintained by `Gentleman-Programming/engram`; install it
separately if you want cross-session memory (spec-132 D-132-06; the
installer no longer wires Engram automatically).

Install:

```bash
# macOS
brew install engram
# Linux
ENGRAM_URL="https://github.com/Gentleman-Programming/engram/releases/latest"
curl -fsSL "$ENGRAM_URL/download/engram-linux-x86_64" -o "$HOME/.local/bin/engram"
chmod +x "$HOME/.local/bin/engram"
# Windows
winget install Engram
```

Then run the IDE-specific setup once per project (use the entry that
matches your IDE):

```bash
engram setup claude_code   # Claude Code
engram setup codex          # OpenAI Codex
```

GitHub Copilot is not currently supported by Engram. Verify the
integration with `ai-eng doctor`.

## Audit Observability (files-only)

```bash
ai-eng audit verify                            # verify the framework-events.ndjson hash chain
ai-eng audit tokens --by skill|agent|session   # token rollup over the NDJSON
ai-eng audit replay --session <id>             # depth-first span-tree walk over the NDJSON
```
"""

_COPILOT_EXTRAS = """\
## First Action (GitHub Copilot)

Run `/ai-start` first in every session. `/ai-*` are IDE slash commands,
not `ai-eng` CLI subcommands.

## Hooks Wiring (Copilot-specific)

Hook config in `.github/hooks/hooks.json`. Canonical script in
`.ai-engineering/scripts/hooks/` via bash/PowerShell adapter.

| Cross-IDE primitive        | Copilot event |
|----------------------------|---------------|
| Progressive disclosure     | `userPromptSubmitted` |
| Tool offload + loop detect | `postToolUse` |
| Checkpoint + Ralph Loop    | `sessionEnd` |
| Deny-list enforcement      | `preToolUse` |
| Error capture              | `errorOccurred` |

PreCompact / PostCompact are not surfaced by Copilot; the snapshot
primitive degrades gracefully.
"""


# AGENTS.md is the engine-neutral surface: Claude Code and Copilot carry
# their own hook wiring in their mirrors, so a generic (Codex / OpenCode /
# Cursor / Antigravity / raw-API) host got NO hook or hot-path guidance
# before spec-187 W4. This portable pointer names where the wiring and
# budgets live without any engine-specific tool name (D-187-09 portability;
# ASCII-only per D-187-10). The fence is stripped before the surface-parity
# sha, so this content does not break byte-equivalence with the other roots.
_AGENTS_EXTRAS = """\
## Hooks & Hot-Path (portable entry point)

AGENTS.md is the engine-neutral surface. Claude Code and Copilot ship
their own hook wiring in their mirrors; other engines (Codex, OpenCode,
Cursor, Antigravity, raw-API hosts) apply the same discipline through
whatever session-lifecycle mechanism they provide:

- Keep any pre-commit / pre-save gate under ~1s and any pre-push gate
  under ~5s; move the full test suite, dependency audit, and governance
  evaluation into CI, never onto the local hot path.
- Canonical hook scripts live under `.ai-engineering/scripts/hooks/` and
  are byte-pinned in `.ai-engineering/state/hooks-manifest.json`; invoke
  them through the integrity-checked runner (or the host's equivalent) so
  the pin stays enforced. IDE-specific hook config is per-surface.
- The `/ai-*` slash idiom and the trailing `$ARGUMENTS` token are provided
  by the host agent surface. On a host with no slash layer, invoke the
  skill body at `.claude/skills/ai-<name>/SKILL.md` directly.
"""


def generate_agents_md(*, skill_count: int, agent_count: int) -> str:
    """Generate AGENTS.md as the byte-equivalent base mirror (spec-131 D-131-14).

    AGENTS.md is the engine-neutral base mirror. The canonical payload
    (CANONICAL.md) carries the full "how AI works in this repo" contract;
    AGENTS.md is what Codex and any future native-AGENTS.md consumer reads.
    CLAUDE.md / copilot-instructions.md carry the same payload + their own
    IDE-extras fence. AGENTS.md's fence now carries a *portable* hook /
    hot-path pointer (``_AGENTS_EXTRAS``) so non-Claude/non-Copilot engines
    are not left without guidance; the fence is still stripped before the
    surface-parity sha, so byte-equivalence with the other roots holds.

    The function preserves the test-asserted invariants:
    - ``## Skills ({skill_count})`` header (after placeholder
      substitution).
    - ``Canonical skills and agents live under `.claude/``` text.
    - Source-of-Truth table rows for Skills / Agents / Placement
      contract.
    """
    payload = read_canonical_payload()
    return assemble_mirror_payload(
        payload,
        ide_extras=_AGENTS_EXTRAS,
        skill_count=skill_count,
        agent_count=agent_count,
    )


def _renumber_dont_items(content: str) -> str:
    """Renumber the Don't section items sequentially after stripping."""
    lines = content.splitlines(keepends=True)
    in_dont = False
    item_num = 0
    result: list[str] = []

    for line in lines:
        if line.strip() == "## Don't":
            in_dont = True
            result.append(line)
            continue

        if in_dont and line.startswith("## "):
            in_dont = False

        if in_dont and re.match(r"^\d+\.\s+", line):
            item_num += 1
            line = re.sub(r"^\d+\.", f"{item_num}.", line, count=1)

        result.append(line)

    return "".join(result)


# ═══════════════════════════════════════════════════════════════════════════
# Generation -- copilot-instructions.md (from CLAUDE.md as canonical source)
# ═══════════════════════════════════════════════════════════════════════════


def generate_copilot_instructions(
    skills: list[tuple[str, dict[str, str], Path]],
    agents: list[tuple[str, dict[str, str], Path]],
) -> str:
    """Generate .github/copilot-instructions.md as byte-equivalent Copilot mirror.

    spec-131 D-131-14: Copilot overlay carries the same canonical payload
    as AGENTS.md plus a Copilot-specific IDE-extras fence (hooks wiring
    table, first-action banner). The cross-ref line that pointed
    operators to AGENTS.md is REMOVED (D-131-14): every mirror is
    self-contained, no cross-references.
    """
    payload = read_canonical_payload()
    return assemble_mirror_payload(
        payload,
        ide_extras=_COPILOT_EXTRAS,
        skill_count=len(skills),
        agent_count=len(agents),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Generation -- templates/project/ (for ai-eng install)
# ═══════════════════════════════════════════════════════════════════════════


def generate_install_claude_skill(skill_path: Path) -> str:
    """Copy .claude/skills/ai-<name>/SKILL.md as-is for install template."""
    return skill_path.read_text(encoding="utf-8")


def generate_install_claude_agent(agent_path: Path) -> str:
    """Copy .claude/agents/ai-<name>.md as-is for install template."""
    return agent_path.read_text(encoding="utf-8")


def generate_install_codex_surface(path: Path) -> str:
    """Copy a root Codex provider surface as-is for the install template."""
    return path.read_text(encoding="utf-8")


# ── Copilot hooks.json (single canonical event→script source, D-159-06) ──
# Before spec-159 this file was hand-maintained in two divergent copies
# (122-line repo root vs 101-line install template). The mapping below is the
# single source of truth; ``generate_copilot_hooks_json()`` serializes it and
# the sync loop dual-writes it to repo root + install template (R2: the output
# must reproduce the reviewed 122-line root copy byte-for-byte).
_COPILOT_HOOK_DIR = "./.ai-engineering/scripts/hooks"

_COPILOT_HOOKS_SPEC: tuple[tuple[str, tuple[dict[str, object], ...]], ...] = (
    (
        "sessionStart",
        (
            {
                "script": "copilot-session-start",
                "timeoutSec": 10,
                "comment": "Emit session_start telemetry on session initialization",
            },
        ),
    ),
    (
        "sessionEnd",
        (
            {
                "script": "copilot-session-end",
                "timeoutSec": 10,
                "comment": "Emit session_end telemetry when session closes",
            },
            {
                "script": "copilot-instinct-extract",
                "timeoutSec": 20,
                "comment": (
                    "Aggregate recent instinct observations into the canonical "
                    "project instinct store"
                ),
            },
            {
                "script": "copilot-runtime-stop",
                "timeoutSec": 15,
                "comment": ("Write runtime checkpoint + Ralph Loop resume marker (runtime-stop)"),
            },
        ),
    ),
    (
        "userPromptSubmitted",
        (
            {
                "script": "copilot-skill",
                "timeoutSec": 10,
                "comment": "Emit skill_invoked telemetry on /ai-* commands",
            },
            {
                "script": "copilot-runtime-progressive-disclosure",
                "timeoutSec": 5,
                "comment": ("Rank skills by prompt relevance, surface top-K via additionalContext"),
            },
        ),
    ),
    (
        "preToolUse",
        (
            {
                "script": "copilot-injection-guard",
                "timeoutSec": 15,
                "comment": ("Scan tool inputs for prompt injection attacks before execution"),
            },
            {
                "script": "copilot-mcp-health",
                "timeoutSec": 15,
                "comment": "Monitor MCP server health on tool invocations",
            },
            {
                "script": "copilot-deny",
                "timeoutSec": 5,
                "comment": (
                    "Enforce deny-list: block dangerous operations "
                    "(rm -rf, force push, --no-verify)"
                ),
            },
            {
                "script": "copilot-instinct-observe",
                "args": "pre",
                "timeoutSec": 10,
                "comment": "Capture sanitized pre-tool observations for instinct learning",
            },
        ),
    ),
    (
        "postToolUse",
        (
            {
                "script": "copilot-agent",
                "timeoutSec": 10,
                "comment": "Emit agent_dispatched telemetry on agent tool use",
            },
            {
                "script": "copilot-instinct-observe",
                "args": "post",
                "timeoutSec": 10,
                "comment": "Capture sanitized post-tool observations for instinct learning",
            },
            {
                "script": "copilot-auto-format",
                "timeoutSec": 15,
                "comment": "Auto-format edited files after tool use",
            },
            {
                "script": "copilot-runtime-guard",
                "timeoutSec": 10,
                "comment": "Tool-call offload + loop detection (runtime-guard)",
            },
        ),
    ),
    (
        "errorOccurred",
        (
            {
                "script": "copilot-error",
                "timeoutSec": 10,
                "comment": "Emit error_occurred telemetry on failures",
            },
        ),
    ),
)


def generate_copilot_hooks_json() -> str:
    """Deterministically build ``.github/hooks/hooks.json`` from one source.

    Serializes ``_COPILOT_HOOKS_SPEC`` with ``indent=2`` + trailing newline so
    the output is byte-identical to the reviewed canonical root copy (D-159-06).
    """
    hooks: dict[str, list[dict[str, object]]] = {}
    for event, entries in _COPILOT_HOOKS_SPEC:
        event_entries: list[dict[str, object]] = []
        for entry in entries:
            script = entry["script"]
            args = entry.get("args")
            suffix = f" {args}" if args else ""
            event_entries.append(
                {
                    "type": "command",
                    "bash": f"{_COPILOT_HOOK_DIR}/{script}.sh{suffix}",
                    "powershell": f"{_COPILOT_HOOK_DIR}/{script}.ps1{suffix}",
                    "timeoutSec": entry["timeoutSec"],
                    "comment": entry["comment"],
                }
            )
        hooks[event] = event_entries
    payload = {"version": 1, "hooks": hooks}
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


# ═══════════════════════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════════════════════


def validate_canonical(
    skills: list[tuple[str, dict[str, str], Path]],
    agents: list[tuple[str, dict[str, str], Path]],
) -> tuple[list[str], list[str]]:
    """Validate canonical frontmatter: name + description required."""
    errors: list[str] = []
    warnings: list[str] = []
    for _name, fm, path in skills:
        rel = path.relative_to(ROOT)
        if not fm.get("description"):
            errors.append(f"{rel}: missing 'description' in frontmatter")
    for name, fm, path in agents:
        if not fm.get("name"):
            warnings.append(f"Agent '{name}': missing 'name' in frontmatter")
        # spec-189 D-189-04: `effort` is the sole SEMANTIC source of truth. The
        # hand-typed Claude-valid `model:` in .claude/agents/<name>.md is never
        # regenerated, so it must agree with the model derived from
        # AGENT_METADATA[name].effort. This build-time cross-check (mirror
        # generation, NOT the pre-commit hot path) catches drift between the
        # hand-typed model and the semantic effort before it reaches any mirror.
        meta = AGENT_METADATA.get(name)
        if meta is not None:
            expected_model = _effort_to_model(meta.effort)
            declared_model = fm.get("model")
            if declared_model != expected_model:
                rel = path.relative_to(ROOT)
                errors.append(
                    f"{rel}: model: {declared_model!r} disagrees with effort "
                    f"{meta.effort!r} (expected model: {expected_model!r}). Fix the "
                    f"hand-typed model: or AGENT_METADATA[{name!r}].effort."
                )
    return errors, warnings


def validate_manifest(
    skills: list[tuple[str, dict[str, str], Path]],
    agents: list[tuple[str, dict[str, str], Path]],
) -> tuple[list[str], list[str]]:
    """Validate skill and agent counts against manifest.yml."""
    errors: list[str] = []
    warnings: list[str] = []

    try:
        import yaml
    except ImportError:
        warnings.append("pyyaml not installed -- skipping manifest validation")
        return errors, warnings

    if not MANIFEST_PATH.is_file():
        errors.append(f"Manifest not found: {MANIFEST_PATH.relative_to(ROOT)}")
        return errors, warnings

    data = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))

    # spec-128 slim manifest: framework-managed sections (skills.registry,
    # agents.names, etc.) are injected by the loader. Apply the same merge
    # here so the sync script validates against the EFFECTIVE manifest, not
    # the raw user-facing slice.
    try:
        from ai_engineering.config.framework_defaults import apply_framework_defaults

        data = apply_framework_defaults(data)
    except ImportError:
        warnings.append(
            "ai_engineering not importable from sync script — registry "
            "check operates on raw manifest only."
        )

    # Skills validation
    m_skills = data.get("skills", {})
    expected_skill_count = m_skills.get("total", 0)
    actual_skill_count = len(skills)

    if actual_skill_count != expected_skill_count:
        errors.append(
            f"Skill count mismatch: manifest={expected_skill_count},"
            f" discovered={actual_skill_count}"
        )

    # Check skill names match registry
    registry = m_skills.get("registry", {})
    expected_skill_names = {name.removeprefix("ai-") for name in registry}
    actual_skill_names = {name for name, _, _ in skills}

    missing_skills = expected_skill_names - actual_skill_names
    extra_skills = actual_skill_names - expected_skill_names
    if missing_skills:
        errors.append(f"Skills in manifest but not found: {sorted(missing_skills)}")
    if extra_skills:
        errors.append(f"Skills found but not in manifest: {sorted(extra_skills)}")

    # Agents validation
    m_agents = data.get("agents", {})
    expected_agent_count = m_agents.get("total", 0)
    expected_agent_names = set(m_agents.get("names", []))
    actual_agent_names = {name for name, _, _ in agents}
    actual_agent_count = len(agents)

    if actual_agent_count != expected_agent_count:
        errors.append(
            f"Agent count mismatch: manifest={expected_agent_count},"
            f" discovered={actual_agent_count}"
        )
    if actual_agent_names != expected_agent_names:
        missing = expected_agent_names - actual_agent_names
        extra = actual_agent_names - expected_agent_names
        if missing:
            errors.append(f"Agents in manifest but not found: {sorted(missing)}")
        if extra:
            errors.append(f"Agents found but not in manifest: {sorted(extra)}")

    return errors, warnings


# spec-148 files-only: per-install runtime state files are gitignored and
# legitimately absent on a clean checkout, so references to them are not
# "broken". (framework-events.ndjson + the JSON SoTs are written by install /
# decision / risk / ownership flows, never committed.)
_RUNTIME_STATE_REFS: frozenset[str] = frozenset(
    {
        "state/framework-events.ndjson",
        "state/observation-events.ndjson",
        "state/decision-store.json",
        "state/ownership-map.json",
        "state/install-state.json",
        "state/framework-capabilities.json",
        "state/gate-findings.json",
    }
)


def validate_cross_references(*, verbose: bool = False) -> list[str]:
    """Check that .ai-engineering/ paths in instruction files exist."""
    warnings: list[str] = []
    pattern = re.compile(r"`\.ai-engineering/([^`]+)`")

    for ref_file in _resolve_cross_reference_files(ROOT):
        if not ref_file.is_file():
            continue
        text = ref_file.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            ref = match.group(1)
            ref_path = ROOT / ".ai-engineering" / ref
            # Allow glob-like references, placeholder patterns, and the
            # gitignored per-install runtime state files (absent on a clean
            # checkout by design).
            if "*" in ref or "<" in ref or "{" in ref or ref in _RUNTIME_STATE_REFS:
                continue
            if not ref_path.exists():
                rel_file = ref_file.relative_to(ROOT)
                warnings.append(f"{rel_file}: broken reference `.ai-engineering/{ref}`")
    return warnings


def validate_runbooks() -> list[str]:
    """Validate runbooks directory has expected files."""
    warnings: list[str] = []
    if not RUNBOOKS_ROOT.is_dir():
        warnings.append("Runbooks directory not found")
        return warnings
    runbook_files = list(RUNBOOKS_ROOT.glob("*.md"))
    if not runbook_files:
        warnings.append("No runbooks found in .ai-engineering/runbooks/")
    return warnings


# ═══════════════════════════════════════════════════════════════════════════
# Sync engine
# ═══════════════════════════════════════════════════════════════════════════


def _generate_surface(
    path: Path,
    content: str,
    check_only: bool,
    verbose: bool,
    generated_paths: set[Path],
    diffs: list[str],
) -> None:
    """Generate a mirror file."""
    generated_paths.add(path)
    diff = _check_or_write(path, content, check_only, verbose)
    if diff:
        diffs.append(diff)


def sync_all(*, check_only: bool = False, verbose: bool = False) -> int:
    """Generate or check all mirror files.

    Returns:
        0 = clean (no changes needed / applied successfully)
        1 = drift detected (check_only mode)
        2 = integrity error (canonical validation failed)
    """
    skills = discover_skills()
    agents = discover_agents()
    diffs: list[str] = []
    generated_paths: set[Path] = set()

    # ── Phase 1: Validate ───────────────────────────────────────────────
    print("Validating canonical sources (.claude/)...")
    errors, warnings = validate_canonical(skills, agents)
    if warnings:
        _print_issues("Canonical warnings", warnings)
    if errors:
        _print_issues("CANONICAL ERRORS", errors)
        return 2

    m_errors, m_warnings = validate_manifest(skills, agents)
    if m_warnings:
        _print_issues("Manifest warnings", m_warnings)
    if m_errors:
        _print_issues("MANIFEST ERRORS", m_errors)
        return 2

    xref_warnings = validate_cross_references(verbose=verbose)
    if xref_warnings:
        _print_issues("Cross-reference warnings", xref_warnings)

    runbook_warnings = validate_runbooks()
    if runbook_warnings:
        _print_issues("Runbook warnings", runbook_warnings)

    skill_count = len(skills)
    agent_count = len(agents)
    print(f"Discovered: {skill_count} skills, {agent_count} agents")

    # ── Pre-discover handlers/scripts/references/resources once per skill ───────────
    skill_handlers: dict[str, list[tuple[str, Path]]] = {}
    skill_references: dict[str, list[tuple[str, Path]]] = {}
    skill_scripts: dict[str, list[tuple[str, Path]]] = {}
    skill_resources: dict[str, list[tuple[str, Path]]] = {}
    skill_raw: dict[Path, str] = {}  # cache raw file reads
    for name, _fm, skill_path in skills:
        skill_handlers[name] = discover_handlers(skill_path.parent)
        skill_references[name] = discover_reference_files(skill_path.parent)
        skill_scripts[name] = discover_scripts(skill_path.parent)
        skill_resources[name] = discover_resources(skill_path.parent)
        skill_raw[skill_path] = skill_path.read_text(encoding="utf-8")
        for _h_name, h_path in skill_handlers[name]:
            skill_raw[h_path] = h_path.read_text(encoding="utf-8")
        for _r_name, r_path in skill_references[name]:
            skill_raw[r_path] = r_path.read_text(encoding="utf-8")
        for _s_name, s_path in skill_scripts[name]:
            skill_raw[s_path] = s_path.read_text(encoding="utf-8")
        for _r_name, r_path in skill_resources[name]:
            skill_raw[r_path] = r_path.read_text(encoding="utf-8")

    for _name, _fm, agent_path in agents:
        skill_raw[agent_path] = agent_path.read_text(encoding="utf-8")

    # ── Phase 2: Generate surfaces ──────────────────────────────────────

    # Surface 1: .codex/skills/ai-<name>/SKILL.md (keep ai- prefix)
    for name, _fm, skill_path in skills:
        path = CODEX_SKILLS / f"ai-{name}" / "SKILL.md"
        tpl = TPL_CODEX_SKILLS / f"ai-{name}" / "SKILL.md"
        content = generate_codex_skill(name, skill_path)
        _generate_surface(path, content, check_only, verbose, generated_paths, diffs)
        _generate_surface(tpl, content, check_only, verbose, generated_paths, diffs)

        for handler_name, handler_path in skill_handlers[name]:
            translated = translate_refs(skill_raw[handler_path], "codex")
            for target in (
                CODEX_SKILLS / f"ai-{name}" / "handlers" / f"{handler_name}.md",
                TPL_CODEX_SKILLS / f"ai-{name}" / "handlers" / f"{handler_name}.md",
            ):
                _generate_surface(target, translated, check_only, verbose, generated_paths, diffs)

        for ref_name, ref_path in skill_references[name]:
            translated = translate_refs(skill_raw[ref_path], "codex")
            for target in (
                CODEX_SKILLS / f"ai-{name}" / "references" / ref_name,
                TPL_CODEX_SKILLS / f"ai-{name}" / "references" / ref_name,
            ):
                _generate_surface(target, translated, check_only, verbose, generated_paths, diffs)

        for script_name, script_path in skill_scripts[name]:
            translated = translate_refs(skill_raw[script_path], "codex")
            for target in (
                CODEX_SKILLS / f"ai-{name}" / "scripts" / script_name,
                TPL_CODEX_SKILLS / f"ai-{name}" / "scripts" / script_name,
            ):
                _generate_surface(target, translated, check_only, verbose, generated_paths, diffs)

        for res_name, res_path in skill_resources[name]:
            translated = translate_refs(skill_raw[res_path], "codex")
            for target in (
                CODEX_SKILLS / f"ai-{name}" / res_name,
                TPL_CODEX_SKILLS / f"ai-{name}" / res_name,
            ):
                _generate_surface(target, translated, check_only, verbose, generated_paths, diffs)

    # Surface 2: .codex/agents/ai-<name>.md
    for name, _fm, agent_path in agents:
        path = CODEX_AGENTS / f"ai-{name}.md"
        tpl = TPL_CODEX_AGENTS / f"ai-{name}.md"
        content = generate_codex_agent(name, agent_path)
        _generate_surface(path, content, check_only, verbose, generated_paths, diffs)
        _generate_surface(tpl, content, check_only, verbose, generated_paths, diffs)

    # Surface 2a: provider-owned Codex config/hooks mirrored into install templates.
    for root_path, tpl_path in (
        (ROOT / ".codex" / "hooks.json", TPL_CODEX_HOOKS),
        (ROOT / ".codex" / "config.toml", TPL_CODEX_CONFIG),
    ):
        content = generate_install_codex_surface(root_path)
        _generate_surface(tpl_path, content, check_only, verbose, generated_paths, diffs)

    # Surface 2c: Copilot hooks.json generated from one canonical event→script
    # source (D-159-06). Dual-write the repo-root copy + the install template so
    # the two hand-maintained copies can no longer drift (R2).
    copilot_hooks_json = generate_copilot_hooks_json()
    for hooks_json_path in (
        ROOT / ".github" / "hooks" / "hooks.json",
        TPL_PROJECT / ".github" / "hooks" / "hooks.json",
    ):
        _generate_surface(
            hooks_json_path, copilot_hooks_json, check_only, verbose, generated_paths, diffs
        )

    # Surface 2b: internal specialist agents (reviewer/verifier families).
    # These are dispatched by orchestrator agents and must be present in the
    # install templates for every provider that exposes local subagents.
    # D-159-05 (corrected): the .claude install TEMPLATE is a GENERATED mirror
    # that carries governed provenance frontmatter (canonical body + provenance),
    # enforced by validator/_check_claude_specialist_agents_mirror. Only the
    # authored canonical .claude/agents/* source is provenance-free; the dogfood
    # `ai-eng update --preview` "updated" delta on these 10 files is by design
    # (canonical-vs-generated-template), not drift. An earlier draft wrote the
    # template verbatim — that violated the mirror-sync governance contract.
    for specialist_path in discover_specialist_agents():
        provenance = generate_specialist_agent(specialist_path)
        _generate_surface(
            TPL_CLAUDE_AGENTS / specialist_path.name,
            provenance,
            check_only,
            verbose,
            generated_paths,
            diffs,
        )
        for repo_rel, template_rel in get_internal_specialist_agent_targets().values():
            for target in (
                ROOT / repo_rel / specialist_path.name,
                ROOT / template_rel / specialist_path.name,
            ):
                _generate_surface(target, provenance, check_only, verbose, generated_paths, diffs)

    # Surface 3: .github/skills/ai-<name>/SKILL.md + handlers/ (Agent Skills)
    for name, _fm, skill_path in skills:
        if not is_copilot_compatible(skill_path):
            continue
        path = GITHUB_SKILLS / f"ai-{name}" / "SKILL.md"
        tpl = TPL_GITHUB_SKILLS / f"ai-{name}" / "SKILL.md"
        content = generate_copilot_skill(name, skill_path)
        _generate_surface(path, content, check_only, verbose, generated_paths, diffs)
        _generate_surface(tpl, content, check_only, verbose, generated_paths, diffs)

        for handler_name, handler_path in skill_handlers[name]:
            handler_content = generate_copilot_handler(handler_path)
            for target in (
                GITHUB_SKILLS / f"ai-{name}" / "handlers" / f"{handler_name}.md",
                TPL_GITHUB_SKILLS / f"ai-{name}" / "handlers" / f"{handler_name}.md",
            ):
                _generate_surface(
                    target, handler_content, check_only, verbose, generated_paths, diffs
                )

        for ref_name, ref_path in skill_references[name]:
            ref_content = translate_refs(skill_raw[ref_path], "copilot")
            for target in (
                GITHUB_SKILLS / f"ai-{name}" / "references" / ref_name,
                TPL_GITHUB_SKILLS / f"ai-{name}" / "references" / ref_name,
            ):
                _generate_surface(target, ref_content, check_only, verbose, generated_paths, diffs)

        for script_name, script_path in skill_scripts[name]:
            translated = translate_refs(skill_raw[script_path], "copilot")
            for target in (
                GITHUB_SKILLS / f"ai-{name}" / "scripts" / script_name,
                TPL_GITHUB_SKILLS / f"ai-{name}" / "scripts" / script_name,
            ):
                _generate_surface(target, translated, check_only, verbose, generated_paths, diffs)

        for res_name, res_path in skill_resources[name]:
            res_content = translate_refs(skill_raw[res_path], "copilot")
            for target in (
                GITHUB_SKILLS / f"ai-{name}" / res_name,
                TPL_GITHUB_SKILLS / f"ai-{name}" / res_name,
            ):
                _generate_surface(target, res_content, check_only, verbose, generated_paths, diffs)

    # Surface 4: .github/agents/<name>.agent.md
    # Spec-107 D-107-03: explore is renamed to ai-explore for cross-IDE parity.
    # Other Copilot agents keep bare slugs (build.agent.md, plan.agent.md, etc.).
    for name, _fm, agent_path in agents:
        meta = AGENT_METADATA.get(name)
        if not meta:
            print(f"  WARNING: No metadata for agent '{name}', skipping .github/agents/")
            continue
        copilot_slug = f"ai-{name}" if name == "explore" else name
        path = GITHUB_AGENTS / f"{copilot_slug}.agent.md"
        tpl = TPL_GITHUB_AGENTS / f"{copilot_slug}.agent.md"
        content = generate_copilot_agent(name, meta, agent_path)
        _generate_surface(path, content, check_only, verbose, generated_paths, diffs)
        _generate_surface(tpl, content, check_only, verbose, generated_paths, diffs)

    # Surface 5: templates/project/.claude/ (copy canonical as-is for install)
    for name, _fm, skill_path in skills:
        tpl = TPL_CLAUDE_SKILLS / f"ai-{name}" / "SKILL.md"
        content = generate_install_claude_skill(skill_path)
        _generate_surface(tpl, content, check_only, verbose, generated_paths, diffs)

        for handler_name, handler_path in skill_handlers[name]:
            tpl_handler = TPL_CLAUDE_SKILLS / f"ai-{name}" / "handlers" / f"{handler_name}.md"
            _generate_surface(
                tpl_handler, skill_raw[handler_path], check_only, verbose, generated_paths, diffs
            )

        for ref_name, ref_path in skill_references[name]:
            tpl_ref = TPL_CLAUDE_SKILLS / f"ai-{name}" / "references" / ref_name
            _generate_surface(
                tpl_ref, skill_raw[ref_path], check_only, verbose, generated_paths, diffs
            )

        for script_name, script_path in skill_scripts[name]:
            tpl_script = TPL_CLAUDE_SKILLS / f"ai-{name}" / "scripts" / script_name
            _generate_surface(
                tpl_script, skill_raw[script_path], check_only, verbose, generated_paths, diffs
            )

        for res_name, res_path in skill_resources[name]:
            tpl_res = TPL_CLAUDE_SKILLS / f"ai-{name}" / res_name
            _generate_surface(
                tpl_res, skill_raw[res_path], check_only, verbose, generated_paths, diffs
            )

    for name, _fm, agent_path in agents:
        tpl = TPL_CLAUDE_AGENTS / f"ai-{name}.md"
        content = generate_install_claude_agent(agent_path)
        _generate_surface(tpl, content, check_only, verbose, generated_paths, diffs)

    # Surface 5b: templates/project/.opencode/ (spec-128 Wave 4 + Wave 5).
    # OpenCode separates two skill surfaces (researched 2026-05-14 against
    # https://opencode.ai/docs/skills/ + https://opencode.ai/docs/commands/):
    #
    #   * skills/<name>/SKILL.md — agent-discovered lazy-load (not in `/` menu)
    #   * commands/<name>.md     — slash-menu prompts (visible in `/` menu)
    #
    # Wave 4 emitted skills only. Operators hitting the TUI with `/ai-` saw
    # "No matching items" because OpenCode does not surface skills in the
    # slash menu. Wave 5 (this surface) adds thin saved-prompt commands so
    # the `/ai-<name>` UX is restored. The command body is a one-liner that
    # invokes the matching skill by name; OpenCode lazy-loads the skill body
    # via the `skill` tool, so SKILL.md remains the single source of truth.
    from scripts.sync_mirrors.opencode_target import (
        generate_opencode_agent,
        generate_opencode_command,
        generate_opencode_skill,
    )

    for name, _fm, skill_path in skills:
        tpl_skill = TPL_OPENCODE_SKILLS / f"ai-{name}" / "SKILL.md"
        skill_content = generate_opencode_skill(name, skill_path)
        _generate_surface(tpl_skill, skill_content, check_only, verbose, generated_paths, diffs)

        tpl_cmd = TPL_OPENCODE_COMMANDS / f"ai-{name}.md"
        cmd_content = generate_opencode_command(name, skill_path)
        _generate_surface(tpl_cmd, cmd_content, check_only, verbose, generated_paths, diffs)
    for name, _fm, agent_path in agents:
        tpl = TPL_OPENCODE_AGENTS / f"ai-{name}.md"
        content = generate_opencode_agent(name, agent_path)
        _generate_surface(tpl, content, check_only, verbose, generated_paths, diffs)

    # Surface 5c: templates/project/.cursor/ (spec-128 Wave 4, supersedes D-133-07).
    # Cursor 2.4+ reads native skills from .cursor/skills/<name>/SKILL.md (folder
    # per skill, agent-discovered lazy-load). Per https://cursor.com/help/customization/skills
    # skills are the on-demand counterpart to always-included rules. Agents stay
    # at .cursor/agents/<name>.mdc.
    for name, _fm, skill_path in skills:
        tpl = TPL_CURSOR_SKILLS / f"ai-{name}" / "SKILL.md"
        content = generate_cursor_skill(name, skill_path)
        _generate_surface(tpl, content, check_only, verbose, generated_paths, diffs)
    for name, _fm, agent_path in agents:
        tpl = TPL_CURSOR_AGENTS / f"ai-{name}.mdc"
        content = generate_cursor_agent(name, agent_path)
        _generate_surface(tpl, content, check_only, verbose, generated_paths, diffs)

    # Surface 5d: .agents/ + templates/project/.agents/ (Antigravity app + agy CLI).
    # Antigravity uses AGENTS.md for root context and .agents/ for workspace skills.
    for name, _fm, skill_path in skills:
        content = generate_antigravity_skill(name, skill_path)
        for target in (
            ANTIGRAVITY_SKILLS / f"ai-{name}" / "SKILL.md",
            TPL_ANTIGRAVITY_SKILLS / f"ai-{name}" / "SKILL.md",
        ):
            _generate_surface(target, content, check_only, verbose, generated_paths, diffs)

        for handler_name, handler_path in skill_handlers[name]:
            translated = translate_refs(skill_raw[handler_path], "antigravity")
            for target in (
                ANTIGRAVITY_SKILLS / f"ai-{name}" / "handlers" / f"{handler_name}.md",
                TPL_ANTIGRAVITY_SKILLS / f"ai-{name}" / "handlers" / f"{handler_name}.md",
            ):
                _generate_surface(target, translated, check_only, verbose, generated_paths, diffs)

        for ref_name, ref_path in skill_references[name]:
            translated = translate_refs(skill_raw[ref_path], "antigravity")
            for target in (
                ANTIGRAVITY_SKILLS / f"ai-{name}" / "references" / ref_name,
                TPL_ANTIGRAVITY_SKILLS / f"ai-{name}" / "references" / ref_name,
            ):
                _generate_surface(target, translated, check_only, verbose, generated_paths, diffs)

        for script_name, script_path in skill_scripts[name]:
            translated = translate_refs(skill_raw[script_path], "antigravity")
            for target in (
                ANTIGRAVITY_SKILLS / f"ai-{name}" / "scripts" / script_name,
                TPL_ANTIGRAVITY_SKILLS / f"ai-{name}" / "scripts" / script_name,
            ):
                _generate_surface(target, translated, check_only, verbose, generated_paths, diffs)

        for res_name, res_path in skill_resources[name]:
            translated = translate_refs(skill_raw[res_path], "antigravity")
            for target in (
                ANTIGRAVITY_SKILLS / f"ai-{name}" / res_name,
                TPL_ANTIGRAVITY_SKILLS / f"ai-{name}" / res_name,
            ):
                _generate_surface(target, translated, check_only, verbose, generated_paths, diffs)

    for name, _fm, agent_path in agents:
        content = generate_antigravity_agent(name, agent_path)
        for target in (
            ANTIGRAVITY_AGENTS / f"ai-{name}.md",
            TPL_ANTIGRAVITY_AGENTS / f"ai-{name}.md",
        ):
            _generate_surface(target, content, check_only, verbose, generated_paths, diffs)

    # Surface 5.5: CLAUDE.md (root + template, byte-equivalent mirror of CANONICAL.md).
    # spec-131 D-131-14: CLAUDE.md is now generated from CANONICAL.md + the
    # Claude-specific IDE-extras fence (Hot-Path, Hooks Configuration,
    # Runtime layer hooks, Token Efficiency, Engram, Audit observability).
    # Both the repo-root surface and the install template carry identical
    # bytes so `ai-eng install` ships the same canonical payload.
    claude_md_content = assemble_mirror_payload(
        read_canonical_payload(),
        ide_extras=_CLAUDE_EXTRAS,
        skill_count=skill_count,
        agent_count=agent_count,
    )
    _generate_surface(
        ROOT / "CLAUDE.md", claude_md_content, check_only, verbose, generated_paths, diffs
    )
    _generate_surface(
        TPL_PROJECT / "CLAUDE.md",
        claude_md_content,
        check_only,
        verbose,
        generated_paths,
        diffs,
    )

    # Surface 5.6: shared handlers (.claude/skills/_shared/*.md)
    # Mirrored byte-for-byte across all IDE surfaces + install templates so
    # orchestrator skills (dispatch, autopilot, run) can delegate to a single
    # canonical kernel that every IDE consumer sees identically. Refs are
    # translated per-target so each IDE's path scheme stays consistent.
    shared_handlers = discover_shared_handlers()
    for rel_path, src_path in shared_handlers:
        raw = src_path.read_text(encoding="utf-8")
        # Canonical .claude/ surfaces (root + install template) -- as-is
        for target in (
            CLAUDE_SKILLS / "_shared" / rel_path,
            TPL_CLAUDE_SKILLS / "_shared" / rel_path,
        ):
            _generate_surface(target, raw, check_only, verbose, generated_paths, diffs)
        # Codex
        codex_content = translate_refs(raw, "codex")
        for target in (
            CODEX_SKILLS / "_shared" / rel_path,
            TPL_CODEX_SKILLS / "_shared" / rel_path,
        ):
            _generate_surface(target, codex_content, check_only, verbose, generated_paths, diffs)
        # Cursor
        cursor_content = translate_refs(raw, "cursor")
        for target in (TPL_CURSOR_SKILLS / "_shared" / rel_path,):
            _generate_surface(target, cursor_content, check_only, verbose, generated_paths, diffs)
        # Antigravity
        antigravity_content = translate_refs(raw, "antigravity")
        for target in (
            ANTIGRAVITY_SKILLS / "_shared" / rel_path,
            TPL_ANTIGRAVITY_SKILLS / "_shared" / rel_path,
        ):
            _generate_surface(
                target, antigravity_content, check_only, verbose, generated_paths, diffs
            )
        # GitHub Copilot
        copilot_content = translate_refs(raw, "copilot")
        for target in (
            GITHUB_SKILLS / "_shared" / rel_path,
            TPL_GITHUB_SKILLS / "_shared" / rel_path,
        ):
            _generate_surface(target, copilot_content, check_only, verbose, generated_paths, diffs)

    # spec-128 D-128-07: lang instructions generator removed.
    # spec-128 D-128-04: Manual instruction files (testing/markdown/sonarqube_mcp)
    # also removed — copilot-instructions.md + AGENTS.md provide coverage.

    # Surface 7: AGENTS.md (root + template, generated from CLAUDE.md)
    agents_md_content = generate_agents_md(skill_count=skill_count, agent_count=agent_count)
    _generate_surface(
        ROOT / "AGENTS.md", agents_md_content, check_only, verbose, generated_paths, diffs
    )
    _generate_surface(
        TPL_PROJECT / "AGENTS.md",
        agents_md_content,
        check_only,
        verbose,
        generated_paths,
        diffs,
    )

    # Surface 8: copilot-instructions.md (root + template, generated from CLAUDE.md)
    copilot_md_content = generate_copilot_instructions(skills, agents)
    _generate_surface(
        ROOT / ".github" / "copilot-instructions.md",
        copilot_md_content,
        check_only,
        verbose,
        generated_paths,
        diffs,
    )
    _generate_surface(
        TPL_PROJECT / "copilot-instructions.md",
        copilot_md_content,
        check_only,
        verbose,
        generated_paths,
        diffs,
    )

    # Surface 9: consumer scripts skills subtree lockstep (spec-128 Wave 4).
    # The dogfood `.ai-engineering/scripts/skills/` tree (skill_scripts_lib +
    # skill_scripts) MUST mirror into the installer template tree so every
    # consumer repo gets the lib via `ai-eng install`. Without this, the
    # spec-129 D-129-08 lib lives only in source and `session_bootstrap.py`
    # / `commit_compose.py` / `pr_body_compose.py` / `standup_render.py` all
    # raise ModuleNotFoundError in installed targets (the user-reported bug).
    consumer_scripts_src = ROOT / ".ai-engineering" / "scripts" / "skills"
    consumer_scripts_dst = (
        ROOT / "src" / "ai_engineering" / "templates" / ".ai-engineering" / "scripts" / "skills"
    )
    if consumer_scripts_src.is_dir():
        for src_file in sorted(consumer_scripts_src.rglob("*.py")):
            if "__pycache__" in src_file.parts:
                continue
            relative = src_file.relative_to(consumer_scripts_src)
            dst_file = consumer_scripts_dst / relative
            _generate_surface(
                dst_file,
                src_file.read_text(encoding="utf-8"),
                check_only,
                verbose,
                generated_paths,
                diffs,
            )

    # Surface 10: consumer hook-scripts subtree lockstep (spec-159 D-159-04).
    # The canonical `.ai-engineering/scripts/hooks/` tree (incl. the `_lib/`
    # shared lib) had no propagation path into the installer template, so every
    # hook edit silently drifted the packaged copy (the updater's comparison
    # baseline). Mirror every `.py` (incl. `_lib/`, skipping `__pycache__`) so
    # `dev sync` is the single regen command for hook parity. The `.sh/.ps1`
    # launchers are a separate packaging concern and are not touched here.
    hook_scripts_src = ROOT / ".ai-engineering" / "scripts" / "hooks"
    hook_scripts_dst = TPL_HOOK_SCRIPTS
    if hook_scripts_src.is_dir():
        for src_file in sorted(hook_scripts_src.rglob("*.py")):
            if "__pycache__" in src_file.parts:
                continue
            relative = src_file.relative_to(hook_scripts_src)
            dst_file = hook_scripts_dst / relative
            _generate_surface(
                dst_file,
                src_file.read_text(encoding="utf-8"),
                check_only,
                verbose,
                generated_paths,
                diffs,
            )

    # Surface 11: .ai-engineering doc twins (spec-187 follow-up).
    # The `.ai-engineering/{reference,runbooks}/**.md` docs ship to consumers
    # byte-identical, but no propagation path existed into the installer
    # template, so a canonical edit silently drifted the packaged copy (caught
    # only by full-suite byte-parity tests + a manual `cp` every wave). Mirror
    # every canonical `.md` in the allowlisted doc subtrees to its twin so
    # `dev sync` is the single regen command. Fail-open on consumer projects:
    # `src/…/templates` is absent there, so the loop is a no-op (no twin root).
    if TPL_AIENG.is_dir():
        for subtree in _DOC_TWIN_SUBTREES:
            canonical_subtree = CANONICAL_AIENG / subtree
            if not canonical_subtree.is_dir():
                continue
            for src_file in sorted(canonical_subtree.rglob("*.md")):
                relative = src_file.relative_to(CANONICAL_AIENG)
                dst_file = TPL_AIENG / relative
                _generate_surface(
                    dst_file,
                    src_file.read_text(encoding="utf-8"),
                    check_only,
                    verbose,
                    generated_paths,
                    diffs,
                )

    # ── Phase 3: Orphan detection ───────────────────────────────────────
    orphan_diffs = _handle_orphans(generated_paths, check_only, verbose)

    # ── Phase 4: Summary ────────────────────────────────────────────────
    all_diffs = diffs + orphan_diffs
    if all_diffs:
        action = "would change" if check_only else "synced"
        print(f"\n{len(all_diffs)}/{len(generated_paths)} files {action}:")
        for d in all_diffs:
            print(f"  {d}")
        if check_only:
            print("\nRun without --check to apply changes.")
            return 1
        return 0

    status = "in sync" if check_only else "generated"
    print(f"\nAll {len(generated_paths)} mirror files {status}. No changes.")
    return 0


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


def _check_or_write(
    path: Path,
    content: str,
    check_only: bool,
    verbose: bool = False,
) -> str | None:
    """Compare or write a file. Returns relative path if changed, else None."""
    rel = str(path.relative_to(ROOT))
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing == content:
            return None
        if check_only:
            if verbose:
                _show_content_diff(rel, existing, content)
            return f"DRIFT: {rel}"
        path.write_text(content, encoding="utf-8")
        return f"UPDATED: {rel}"
    if check_only:
        return f"MISSING: {rel}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"CREATED: {rel}"


def _show_content_diff(rel: str, existing: str, expected: str) -> None:
    """Show a simple content diff for verbose mode."""
    old_hash = hashlib.sha256(existing.encode()).hexdigest()[:12]
    new_hash = hashlib.sha256(expected.encode()).hexdigest()[:12]
    print(f"    {rel}: {old_hash} -> {new_hash}")


def _handle_orphans(
    generated: set[Path],
    check_only: bool,
    verbose: bool,
) -> list[str]:
    """Find and handle orphan files across all generated surfaces.

    Uses a data-driven surface registry so every surface is scanned consistently.
    Two scan modes:
      - "glob": flat pattern match directly in the root directory
      - "rglob_subdirs": iterate subdirectories, recursively scan all files
    """
    # (root, mode, prefix_filter) -- prefix_filter="" means all subdirs.
    # Skill surfaces accept both "ai-" (per-skill) and "_shared" (kernel
    # handlers consumed by orchestrators) as valid subdirectory prefixes;
    # "rglob_subdirs_multi" iterates subdirs matching ANY of the listed
    # prefixes, so cross-IDE shared handlers do not get flagged as orphans.
    _SKILL_SUBDIR_PREFIXES = ("ai-", "_shared")
    _ORPHAN_SURFACES: list[tuple[Path, str, object]] = [
        (CODEX_SKILLS, "rglob_subdirs_multi", _SKILL_SUBDIR_PREFIXES),
        (CODEX_AGENTS, "glob", "*.md"),
        (CODEX_AGENTS / "internal", "glob", "*.md"),
        (ANTIGRAVITY_SKILLS, "rglob_subdirs_multi", _SKILL_SUBDIR_PREFIXES),
        (ANTIGRAVITY_AGENTS, "glob", "*.md"),
        (ANTIGRAVITY_AGENTS / "internal", "glob", "*.md"),
        # spec-128 D-128-07: GITHUB_INSTRUCTIONS orphan surface entry removed.
        (GITHUB_SKILLS, "rglob_subdirs_multi", _SKILL_SUBDIR_PREFIXES),
        (GITHUB_AGENTS, "glob", "*.md"),
        (GITHUB_AGENTS / "internal", "glob", "*.md"),
        (TPL_CLAUDE_SKILLS, "rglob_subdirs_multi", _SKILL_SUBDIR_PREFIXES),
        (TPL_CLAUDE_AGENTS, "glob", "*.md"),
        (TPL_CURSOR_SKILLS, "rglob_subdirs_multi", _SKILL_SUBDIR_PREFIXES),
        (TPL_CURSOR_AGENTS, "glob", "*.mdc"),
        (TPL_CODEX_SKILLS, "rglob_subdirs_multi", _SKILL_SUBDIR_PREFIXES),
        (TPL_CODEX_AGENTS, "glob", "*.md"),
        (TPL_CODEX_AGENTS / "internal", "glob", "*.md"),
        (TPL_CODEX_HOOKS.parent, "glob", "hooks.json"),
        (TPL_CODEX_CONFIG.parent, "glob", "config.toml"),
        (TPL_GITHUB_SKILLS, "rglob_subdirs_multi", _SKILL_SUBDIR_PREFIXES),
        (TPL_GITHUB_AGENTS, "glob", "*.md"),
        (TPL_GITHUB_AGENTS / "internal", "glob", "*.md"),
        # spec-144: newer installer-template provider surfaces must also
        # participate in orphan cleanup. Otherwise a canonical skill rename
        # creates the new OpenCode/Cursor/Agent files while stale old-slug
        # template files survive indefinitely.
        (TPL_OPENCODE_SKILLS, "rglob_subdirs_multi", _SKILL_SUBDIR_PREFIXES),
        (TPL_OPENCODE_COMMANDS, "glob", "*.md"),
        (TPL_OPENCODE_AGENTS, "glob", "*.md"),
        (TPL_ANTIGRAVITY_SKILLS, "rglob_subdirs_multi", _SKILL_SUBDIR_PREFIXES),
        (TPL_ANTIGRAVITY_AGENTS, "glob", "*.md"),
        (TPL_ANTIGRAVITY_AGENTS / "internal", "glob", "*.md"),
        # spec-159 D-159-04: Surface 10 mirrors the canonical hook-scripts
        # subtree into the installer template. Scope orphan cleanup to `*.py`
        # ONLY so a renamed/deleted canonical hook does not leave a stale copy
        # shipping in the wheel. The `.sh/.ps1` launchers in this same tree are
        # a separate packaging concern and must NEVER be orphan-deleted.
        (TPL_HOOK_SCRIPTS, "rglob", "*.py"),
        # spec-187 follow-up: Surface 11 doc twins. Scope orphan cleanup to
        # `*.md` in the two allowlisted subtrees so a renamed/deleted canonical
        # doc does not leave a stale twin shipping in the wheel. Only these two
        # subtree roots are scanned (never the divergent overrides/specs/
        # LESSONS siblings, which have no canonical mirror to compare against).
        *(
            (TPL_AIENG / subtree, "rglob", "*.md")
            for subtree in _DOC_TWIN_SUBTREES
            if (TPL_AIENG / subtree).is_dir()
        ),
    ]

    # spec-187 D-187-04: the flat-path reviewer-*/verifier-* forwarder stubs
    # (the legacy deprecation aliases) were hard-deleted — CLAUDE.md §13.3
    # forbids backwards-compat shims. The former `_is_legacy_alias` exemption
    # is gone, so any surviving flat stub is now treated as orphan drift and
    # cleaned on regen. Real specialist bodies live under `<surface>/agents/internal/`.
    orphans: list[Path] = []
    for root, mode, pattern in _ORPHAN_SURFACES:
        if not root.is_dir():
            continue
        if mode == "glob":
            for f in root.glob(str(pattern)):
                if f in generated:
                    continue
                orphans.append(f)
        elif mode == "rglob_subdirs":
            for sub in root.iterdir():
                if not sub.is_dir():
                    continue
                if pattern and not sub.name.startswith(str(pattern)):
                    continue
                for f in sub.rglob("*"):
                    if f.is_file() and f not in generated:
                        orphans.append(f)
        elif mode == "rglob_subdirs_multi":
            prefixes = pattern if isinstance(pattern, tuple) else (str(pattern),)
            for sub in root.iterdir():
                if not sub.is_dir():
                    continue
                if not any(sub.name.startswith(p) for p in prefixes):
                    continue
                for f in sub.rglob("*"):
                    if f.is_file() and f not in generated:
                        orphans.append(f)
        elif mode == "rglob":
            # Recursively scan the whole subtree but only consider files
            # matching the suffix pattern (e.g. "*.py"). This deliberately
            # leaves sibling files of other types untouched -- spec-159 relies
            # on this to keep the `.sh/.ps1` hook launchers out of the orphan
            # candidate set even though they live alongside the synced `.py`.
            for f in root.rglob(str(pattern)):
                if "__pycache__" in f.parts:
                    continue
                if f.is_file() and f not in generated:
                    orphans.append(f)

    orphans.sort()
    diffs: list[str] = []
    if orphans:
        print(f"\nOrphans detected ({len(orphans)}):")
        for orphan in orphans:
            rel = orphan.relative_to(ROOT)
            print(f"  {rel}")
            if check_only:
                diffs.append(f"ORPHAN: {rel}")
            else:
                orphan.unlink()
                # Remove empty parent directories up to the surface root
                parent = orphan.parent
                while parent != ROOT and parent.is_dir() and not any(parent.iterdir()):
                    parent.rmdir()
                    parent = parent.parent
                diffs.append(f"REMOVED: {rel}")
    return diffs


def _print_issues(header: str, items: list[str]) -> None:
    """Print a labeled list of issues."""
    print(f"\n{header} ({len(items)}):")
    for item in items:
        print(f"  {item}")


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync mirror surfaces from canonical .claude/ sources.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify mirrors are in sync; exit 1 if drift detected.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed diff and hash information.",
    )
    args = parser.parse_args()
    return sync_all(check_only=args.check, verbose=args.verbose)
