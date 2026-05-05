#!/usr/bin/env python3
"""Core sync logic (moved from scripts/sync_command_mirrors.py).

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

Usage:
  python scripts/sync_command_mirrors.py            # generate all mirrors
  python scripts/sync_command_mirrors.py --check    # verify, exit 1 on drift
  python scripts/sync_command_mirrors.py --verbose  # show detailed info
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# Allow importing from src/ for shared utilities
sys.path.insert(0, str(ROOT / "src"))

from ai_engineering.config.mirror_inventory import (  # noqa: E402
    get_generated_provenance_fields,
    get_internal_specialist_agent_targets,
)

# ── Canonical source paths (repo root .claude/) ──────────────────────────
CLAUDE_SKILLS = ROOT / ".claude" / "skills"
CLAUDE_AGENTS = ROOT / ".claude" / "agents"
MANIFEST_PATH = ROOT / ".ai-engineering" / "manifest.yml"
RUNBOOKS_ROOT = ROOT / ".ai-engineering" / "runbooks"

# ── Mirror surface paths ────────────────────────────────────────────────
CODEX_SKILLS = ROOT / ".codex" / "skills"
CODEX_AGENTS = ROOT / ".codex" / "agents"
GEMINI_SKILLS = ROOT / ".gemini" / "skills"
GEMINI_AGENTS = ROOT / ".gemini" / "agents"
GITHUB_SKILLS = ROOT / ".github" / "skills"
GITHUB_AGENTS = ROOT / ".github" / "agents"
GITHUB_INSTRUCTIONS = ROOT / ".github" / "instructions"

# ── Template project paths (for ai-eng install) ────────────────────────
TPL_PROJECT = ROOT / "src" / "ai_engineering" / "templates" / "project"
TPL_CLAUDE_SKILLS = TPL_PROJECT / ".claude" / "skills"
TPL_CLAUDE_AGENTS = TPL_PROJECT / ".claude" / "agents"
TPL_GEMINI_SKILLS = TPL_PROJECT / ".gemini" / "skills"
TPL_GEMINI_AGENTS = TPL_PROJECT / ".gemini" / "agents"
TPL_CODEX_SKILLS = TPL_PROJECT / ".codex" / "skills"
TPL_CODEX_AGENTS = TPL_PROJECT / ".codex" / "agents"
TPL_CODEX_HOOKS = TPL_PROJECT / ".codex" / "hooks.json"
TPL_CODEX_CONFIG = TPL_PROJECT / ".codex" / "config.toml"
TPL_GITHUB_SKILLS = TPL_PROJECT / ".github" / "skills"
TPL_GITHUB_AGENTS = TPL_PROJECT / "agents"


# ── Dataclasses ─────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class AgentMeta:
    """Per-agent metadata for all mirror surfaces."""

    display_name: str
    description: str
    model: str
    color: str
    copilot_tools: tuple[str, ...]
    claude_tools: tuple[str, ...]
    copilot_agents: tuple[str, ...] = ()
    copilot_handoffs: tuple[dict, ...] = ()
    copilot_hooks: dict | None = None


# ── Agent metadata (single source for all surfaces) ────────────────────────
AGENT_METADATA: dict[str, AgentMeta] = {
    "build": AgentMeta(
        display_name="Build",
        description="Implementation across all stacks -- the only code write agent",
        model="opus",
        color="blue",
        copilot_tools=(
            "codebase",
            "editFiles",
            "fetch",
            "githubRepo",
            "problems",
            "readFile",
            "runCommands",
            "search",
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
        model="opus",
        color="cyan",
        copilot_tools=("codebase", "githubRepo", "readFile", "search"),
        claude_tools=("Read", "Glob", "Grep"),
    ),
    "guard": AgentMeta(
        display_name="Guard",
        description=(
            "Proactive governance advisor -- checks standards, decisions,"
            " and quality trends during development."
            " Never blocks, always advisory."
        ),
        model="opus",
        color="yellow",
        copilot_tools=(
            "codebase",
            "githubRepo",
            "problems",
            "readFile",
            "search",
        ),
        claude_tools=("Read", "Glob", "Grep"),
    ),
    "guide": AgentMeta(
        display_name="Guide",
        description=(
            "Developer education and onboarding -- architecture tours,"
            " decision archaeology, knowledge transfer."
        ),
        model="opus",
        color="cyan",
        copilot_tools=(
            "codebase",
            "fetch",
            "githubRepo",
            "readFile",
            "search",
        ),
        claude_tools=("Read", "Glob", "Grep"),
    ),
    "plan": AgentMeta(
        display_name="Plan",
        description="Advisory planning: classify scope, assess risks, and recommend pipeline",
        model="opus",
        color="purple",
        copilot_tools=(
            "codebase",
            "editFiles",
            "fetch",
            "githubRepo",
            "problems",
            "readFile",
            "runCommands",
            "search",
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
        color="red",
        copilot_tools=(
            "codebase",
            "githubRepo",
            "problems",
            "readFile",
            "search",
        ),
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
        model="opus",
        color="green",
        copilot_tools=(
            "codebase",
            "editFiles",
            "problems",
            "readFile",
            "runCommands",
            "search",
            "testFailures",
        ),
        claude_tools=("Read", "Glob", "Grep", "Edit"),
    ),
    "verify": AgentMeta(
        display_name="Verify",
        description=(
            "Evidence-first verification orchestrator -- dispatches"
            " deterministic + LLM judgment agents for merge readiness."
        ),
        model="opus",
        color="green",
        copilot_tools=(
            "codebase",
            "githubRepo",
            "problems",
            "readFile",
            "runCommands",
            "search",
        ),
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
        color="purple",
        copilot_tools=(
            "codebase",
            "githubRepo",
            "readFile",
            "runCommands",
            "search",
        ),
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
    "run-orchestrator": AgentMeta(
        display_name="Run",
        description=(
            "Autonomous backlog orchestrator -- normalizes work items,"
            " plans safely from architectural evidence, executes through"
            " build, consolidates locally, and delivers through PRs."
        ),
        model="opus",
        color="purple",
        copilot_tools=(
            "codebase",
            "githubRepo",
            "readFile",
            "runCommands",
            "search",
        ),
        claude_tools=("Read", "Glob", "Grep", "Bash"),
        copilot_agents=("Build", "ai-explore", "Verify", "Review", "Guard"),
    ),
}


# ── Cross-reference validation targets ──────────────────────────────────────
# ── Instruction generation from contexts ─────────────────────────────────────
CONTEXTS_LANGUAGES = ROOT / ".ai-engineering" / "contexts" / "languages"
TPL_INSTRUCTIONS = TPL_PROJECT / "instructions"

# Maps language context file stem to Copilot applyTo glob pattern
LANG_EXTENSIONS: dict[str, str] = {
    "python": "**/*.py",
    "typescript": "**/*.ts,**/*.tsx",
    "javascript": "**/*.js,**/*.jsx",
    "rust": "**/*.rs",
    "go": "**/*.go",
    "java": "**/*.java",
    "kotlin": "**/*.kt,**/*.kts",
    "csharp": "**/*.cs",
    "swift": "**/*.swift",
    "dart": "**/*.dart",
    "cpp": "**/*.cpp,**/*.cc,**/*.cxx,**/*.h,**/*.hpp",
    "php": "**/*.php",
    "bash": "**/*.sh,**/*.bash",
    "sql": "**/*.sql",
}

# Hand-maintained instruction files (not auto-generated)
MANUAL_INSTRUCTIONS: set[str] = {
    "testing.instructions.md",
    "markdown.instructions.md",
    "sonarqube_mcp.instructions.md",
}


def generate_instruction_from_context(lang: str, context_path: Path) -> str:
    """Generate an instructions file from a language context.

    Wraps context content with applyTo frontmatter for Copilot auto-injection.
    """
    apply_to = LANG_EXTENSIONS.get(lang, f"**/*.{lang}")
    content = context_path.read_text(encoding="utf-8")
    source = f".ai-engineering/contexts/languages/{lang}.md"
    header = f"# {lang.title()} Instructions"
    return f'---\napplyTo: "{apply_to}"\n---\n\n{header}\n\nGenerated from `{source}`.\n\n{content}'


_FALLBACK_CROSS_REFERENCE_FILES: list[Path] = [
    ROOT / "CLAUDE.md",
    ROOT / "AGENTS.md",
    ROOT / ".github" / "copilot-instructions.md",
]


def _resolve_cross_reference_files(target: Path) -> list[Path]:
    """Return enabled root instruction surfaces for cross-reference validation.

    Uses the manifest provider set when available so provider-specific root
    surfaces like GEMINI.md are validated only when they are actually enabled.
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
            cfg.ai_providers.enabled,
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
      - gemini (.gemini/): .gemini/skills/ai-X/SKILL.md, .gemini/agents/ai-X.md
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
        elif target_ide == "gemini":
            path = f".gemini/skills/ai-{name}/SKILL.md"
        else:  # copilot
            path = f".github/skills/ai-{name}/SKILL.md"
        return f"{bt}{path}{bt}" if bt else path

    def _replace_agent(m: re.Match[str]) -> str:
        bt = m.group(1)
        name = m.group(2)
        if target_ide == "codex":
            path = f".codex/agents/ai-{name}.md"
        elif target_ide == "gemini":
            path = f".gemini/agents/ai-{name}.md"
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
        "gemini": ".gemini",
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
    elif target_ide == "gemini":
        # .claude/skills/ -> .gemini/skills/
        content = re.sub(r"\.claude/skills/(?!ai-)", ".gemini/skills/", content)
        # .claude/agents/ -> .gemini/agents/
        content = re.sub(r"\.claude/agents/(?!ai-)", ".gemini/agents/", content)
    elif target_ide == "copilot":
        # .claude/skills/ -> .github/skills/
        content = re.sub(r"\.claude/skills/(?!ai-)", ".github/skills/", content)
        # .claude/agents/ -> .github/agents/
        content = re.sub(r"\.claude/agents/(?!ai-)", ".github/agents/", content)

    return content


# ═══════════════════════════════════════════════════════════════════════════
# GEMINI.md placeholder rendering (spec-107 D-107-04)
# ═══════════════════════════════════════════════════════════════════════════


def render_gemini_md_placeholders(
    text: str,
    canonical_skills: list,
    canonical_agents: list,
) -> str:
    """Substitute __SKILL_COUNT__ and __AGENT_COUNT__ placeholders in `text`.

    Pure string substitution; no path translation. Lengths are taken from the
    canonical discovered skill/agent collections so the rendered file always
    matches disk reality (spec-107 G-5).
    """
    skill_count = len(canonical_skills)
    agent_count = len(canonical_agents)
    text = text.replace("__SKILL_COUNT__", str(skill_count))
    text = text.replace("__AGENT_COUNT__", str(agent_count))
    return text


def write_gemini_md(canonical_skills: list, canonical_agents: list) -> str:
    """Render the canonical GEMINI.md content for `.gemini/` and root surfaces.

    Pipeline (spec-107 D-107-04, R-4 mitigation):
      1. Read template at TPL_PROJECT / "GEMINI.md".
      2. Substitute __SKILL_COUNT__ / __AGENT_COUNT__ placeholders FIRST.
      3. Apply translate_refs(..., "gemini") on the substituted body.

    Order matters: substitution runs first so translate_refs never sees the
    placeholders (which contain underscores that some path regexes might
    accidentally chew). Returned string is the final rendered content.
    """
    gemini_md_tpl = TPL_PROJECT / "GEMINI.md"
    raw = gemini_md_tpl.read_text(encoding="utf-8")
    substituted = render_gemini_md_placeholders(raw, canonical_skills, canonical_agents)
    return translate_refs(substituted, "gemini")


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
# Generation -- .gemini/skills/ and .gemini/agents/ (Gemini CLI)
# ═══════════════════════════════════════════════════════════════════════════


def generate_gemini_skill(name: str, skill_path: Path) -> str:
    """Generate .gemini/skills/ai-<name>/SKILL.md -- translated refs, strip metadata."""
    fm = read_frontmatter(skill_path)
    body = read_body(skill_path)

    fm["name"] = f"ai-{name}"
    fm.pop("metadata", None)
    fm.update(
        get_generated_provenance_fields(
            "gemini-skills",
            canonical_source=f".claude/skills/ai-{name}/SKILL.md",
        )
    )

    header = _serialize_frontmatter(fm)
    body = translate_refs(body, "gemini")

    return f"{header}\n\n{body.rstrip()}\n"


def generate_gemini_agent(name: str, agent_path: Path) -> str:
    """Generate .gemini/agents/ai-<name>.md -- translated refs, strip tools/metadata."""
    fm = read_frontmatter(agent_path)
    body = read_body(agent_path)

    fm.pop("tools", None)  # tools are IDE-specific
    fm.pop("metadata", None)
    fm.update(
        get_generated_provenance_fields(
            "gemini-agents",
            canonical_source=f".claude/agents/ai-{name}.md",
        )
    )

    header = _serialize_frontmatter(fm)
    body = translate_refs(body, "gemini")

    return f"{header}\n\n{body.rstrip()}\n"


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

    # Build tools list — inject "agent" when subagents are declared
    tools = list(meta.copilot_tools)
    if meta.copilot_agents:
        tools.append("agent")
    tools_str = ", ".join(tools)

    lines = [
        "---",
        f'name: "{meta.display_name}"',
        f'description: "{meta.description}"',
        f"color: {meta.color}",
        f"model: {meta.model}",
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


def _specialist_agent_output_paths(spec_path: Path) -> tuple[Path, ...]:
    """Return all generated specialist-agent mirror paths for a canonical file."""
    targets = [TPL_CLAUDE_AGENTS / spec_path.name]
    for repo_rel, template_rel in get_internal_specialist_agent_targets().values():
        targets.append(ROOT / repo_rel / spec_path.name)
        targets.append(ROOT / template_rel / spec_path.name)
    return tuple(targets)


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


def generate_agents_md(*, skill_count: int, agent_count: int) -> str:
    """Generate AGENTS.md as canonical cross-IDE entry point (spec-110 D-110-02).

    AGENTS.md is the canonical multi-IDE rulebook for shared root runtime
    behavior. Canonical skill and agent content still lives under
    ``.claude/``; IDE overlays delegate to this file for cross-IDE entry
    point behavior. Hard rules live in CONSTITUTION.md; this file
    enumerates the shared workflow contract and canonical pointers.

    The function is self-contained: it does NOT read CLAUDE.md (which is
    now a slim overlay per spec-110 T-1.9) and produces a stable
    canonical document that contains the headers + Source-of-Truth rows
    asserted by ``test_generate_agents_md_preserves_provider_rows_and_counts``.
    """
    return f"""# AGENTS.md — Canonical Cross-IDE Rulebook

> Hard rules live in [CONSTITUTION.md](CONSTITUTION.md). This file is
> the canonical multi-IDE entry point and shared runtime contract for
> root IDE behavior. Canonical skills and agents live under `.claude/`;
> IDE-specific overlays (CLAUDE.md, GEMINI.md,
> .github/copilot-instructions.md) delegate to this file.

## Step 0 — First Action

Every session, the first action is:

1. Read [CONSTITUTION.md](CONSTITUTION.md) (non-negotiable rules).
2. Read `.ai-engineering/manifest.yml` (configuration source of truth).
3. Read `.ai-engineering/state/decision-store.json` (active decisions and risk posture).
4. No implementation without an approved spec — invoke `/ai-brainstorm`
   first when a task has no spec.

## Workflow

Implementation is spec-gated by default:

1. `/ai-brainstorm` produces or refines the approved spec when scope is unclear or missing.
2. `/ai-plan` decomposes the approved spec into concrete tasks without writing production code.
3. `/ai-dispatch` executes the approved plan for standard scoped work.
4. `/ai-autopilot` executes the approved spec autonomously for large multi-concern work.
5. If no approved spec exists, stop and return to `/ai-brainstorm` before implementation.

## Skills ({skill_count})

The full registry is in `.ai-engineering/manifest.yml` under
`skills.registry`. Canonical skill definitions live under
`.claude/skills/ai-<name>/SKILL.md`; other IDE skill surfaces are
generated mirrors.

Invoke skills via `/ai-<name>` in the IDE agent surface (slash command).
Do not invent `ai-eng <skill>` terminal equivalents unless the CLI
reference explicitly lists them.

## Agents ({agent_count})

The {agent_count} first-class agents are listed in
`.ai-engineering/manifest.yml` under `agents.registry` and documented at
`.claude/agents/ai-<name>.md`. Other IDE agent surfaces are generated
mirrors; each runs in its own context window, so offload research and
parallel analysis to them.

## Hard Rules

The non-negotiable rules are in [CONSTITUTION.md](CONSTITUTION.md).
Read them before any commit, push, or risk-acceptance decision. Gate
failure: diagnose, fix, retry. Use `ai-eng doctor --fix` when needed.

## Observability

Hook, gate, governance, security, and quality outcomes flow to
`.ai-engineering/state/framework-events.ndjson` (audit chain). Registered
skills, agents, contexts, and hooks are catalogued in
`.ai-engineering/state/framework-capabilities.json`. Session discovery
and transcript viewing are delegated to the separately installed
`agentsview` companion tool.

## Source of Truth

| What | Where |
|------|-------|
| Skills ({skill_count}) | `.claude/skills/ai-<name>/SKILL.md` |
| Agents ({agent_count}) | `.claude/agents/ai-<name>.md` |
| Placement contract | `.ai-engineering/contexts/knowledge-placement.md` |
| Config | `.ai-engineering/manifest.yml` |
| Decisions | `.ai-engineering/state/decision-store.json` |
| Audit chain | `.ai-engineering/state/framework-events.ndjson` |
| Constitution | [CONSTITUTION.md](CONSTITUTION.md) |
"""


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
    """Generate .github/copilot-instructions.md (slim Copilot overlay).

    spec-122-a (D-122-01): the Copilot overlay is now ≤30 lines and only
    contains Copilot-specific content (hook event-name mapping +
    first-action). Skills, agents, source-of-truth, observability, hard
    rules, quality gates are all delegated to AGENTS.md / CONSTITUTION.md.

    The `skills` and `agents` parameters are kept for API compatibility
    with `--check` callers that still pass them in.
    """
    _ = skills, agents  # parity with prior signature; counts are in AGENTS.md

    return (
        "# GitHub Copilot Instructions\n"
        "\n"
        "> See [AGENTS.md](../AGENTS.md) for canonical cross-IDE rules\n"
        "> (Step 0, skills, agents, hard rules, quality gates, observability,\n"
        "> source of truth). Non-negotiable rules in\n"
        "> [CONSTITUTION.md](../CONSTITUTION.md). Read those first.\n"
        "\n"
        "## FIRST ACTION — Mandatory\n"
        "\n"
        "Run `/ai-start` first in every session. `/ai-*` are IDE slash\n"
        "commands, not `ai-eng` CLI subcommands.\n"
        "\n"
        "## Hooks Wiring (Copilot-specific)\n"
        "\n"
        "Hook config in `.github/hooks/hooks.json`. Canonical script in\n"
        "`.ai-engineering/scripts/hooks/` via bash/PowerShell adapter.\n"
        "\n"
        "| Cross-IDE primitive        | Copilot event |\n"
        "|----------------------------|---------------|\n"
        "| Progressive disclosure     | `userPromptSubmitted` |\n"
        "| Tool offload + loop detect | `postToolUse` |\n"
        "| Checkpoint + Ralph Loop    | `sessionEnd` |\n"
        "| Deny-list enforcement      | `preToolUse` |\n"
        "| Error capture              | `errorOccurred` |\n"
        "\n"
        "PreCompact / PostCompact not surfaced by Copilot; snapshot\n"
        "primitive degrades gracefully.\n"
        "\n"
        "## Observability\n"
        "\n"
        "See [AGENTS.md → Observability](../AGENTS.md#observability) for the\n"
        "canonical telemetry posture and audit chain wiring. Copilot-specific\n"
        "hook events are listed in the table above.\n"
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
    for name, fm, _path in agents:
        if not fm.get("name"):
            warnings.append(f"Agent '{name}': missing 'name' in frontmatter")
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


def validate_cross_references(*, verbose: bool = False) -> list[str]:
    """Check that .ai-engineering/ paths in instruction files exist."""
    warnings: list[str] = []
    pattern = re.compile(r"`\.ai-engineering/([^`]+)`")

    for ref_file in _resolve_cross_reference_files(ROOT):
        if not ref_file.is_file():
            continue
        text = ref_file.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            ref_path = ROOT / ".ai-engineering" / match.group(1)
            # Allow glob-like references and placeholder patterns
            if "*" in match.group(1) or "<" in match.group(1) or "{" in match.group(1):
                continue
            if not ref_path.exists():
                rel_file = ref_file.relative_to(ROOT)
                warnings.append(f"{rel_file}: broken reference `.ai-engineering/{match.group(1)}`")
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

    # Surface 2.1: .gemini/skills/ai-<name>/SKILL.md (keep ai- prefix, strip metadata)
    for name, _fm, skill_path in skills:
        path = GEMINI_SKILLS / f"ai-{name}" / "SKILL.md"
        tpl = TPL_GEMINI_SKILLS / f"ai-{name}" / "SKILL.md"
        content = generate_gemini_skill(name, skill_path)
        _generate_surface(path, content, check_only, verbose, generated_paths, diffs)
        _generate_surface(tpl, content, check_only, verbose, generated_paths, diffs)

        for handler_name, handler_path in skill_handlers[name]:
            translated = translate_refs(skill_raw[handler_path], "gemini")
            for target in (
                GEMINI_SKILLS / f"ai-{name}" / "handlers" / f"{handler_name}.md",
                TPL_GEMINI_SKILLS / f"ai-{name}" / "handlers" / f"{handler_name}.md",
            ):
                _generate_surface(target, translated, check_only, verbose, generated_paths, diffs)

        for ref_name, ref_path in skill_references[name]:
            translated = translate_refs(skill_raw[ref_path], "gemini")
            for target in (
                GEMINI_SKILLS / f"ai-{name}" / "references" / ref_name,
                TPL_GEMINI_SKILLS / f"ai-{name}" / "references" / ref_name,
            ):
                _generate_surface(target, translated, check_only, verbose, generated_paths, diffs)

        for script_name, script_path in skill_scripts[name]:
            translated = translate_refs(skill_raw[script_path], "gemini")
            for target in (
                GEMINI_SKILLS / f"ai-{name}" / "scripts" / script_name,
                TPL_GEMINI_SKILLS / f"ai-{name}" / "scripts" / script_name,
            ):
                _generate_surface(target, translated, check_only, verbose, generated_paths, diffs)

        for res_name, res_path in skill_resources[name]:
            translated = translate_refs(skill_raw[res_path], "gemini")
            for target in (
                GEMINI_SKILLS / f"ai-{name}" / res_name,
                TPL_GEMINI_SKILLS / f"ai-{name}" / res_name,
            ):
                _generate_surface(target, translated, check_only, verbose, generated_paths, diffs)

    # Surface 2.2: .gemini/agents/ai-<name>.md (strip tools/metadata)
    for name, _fm, agent_path in agents:
        path = GEMINI_AGENTS / f"ai-{name}.md"
        tpl = TPL_GEMINI_AGENTS / f"ai-{name}.md"
        content = generate_gemini_agent(name, agent_path)
        _generate_surface(path, content, check_only, verbose, generated_paths, diffs)
        _generate_surface(tpl, content, check_only, verbose, generated_paths, diffs)

    # Surface 2b: specialist agents (reviewer-*, verifier-*, review-*, verify-*)
    # Mirrored into provider-local internal roots with generated provenance.
    specialists = discover_specialist_agents()
    for spec_path in specialists:
        content = generate_specialist_agent(spec_path)
        for target in _specialist_agent_output_paths(spec_path):
            _generate_surface(target, content, check_only, verbose, generated_paths, diffs)

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

    # Surface 5.5: templates/project/CLAUDE.md (canonical root instruction file)
    _generate_surface(
        TPL_PROJECT / "CLAUDE.md",
        (ROOT / "CLAUDE.md").read_text(encoding="utf-8"),
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
        # Gemini
        gemini_content = translate_refs(raw, "gemini")
        for target in (
            GEMINI_SKILLS / "_shared" / rel_path,
            TPL_GEMINI_SKILLS / "_shared" / rel_path,
        ):
            _generate_surface(target, gemini_content, check_only, verbose, generated_paths, diffs)
        # GitHub Copilot
        copilot_content = translate_refs(raw, "copilot")
        for target in (
            GITHUB_SKILLS / "_shared" / rel_path,
            TPL_GITHUB_SKILLS / "_shared" / rel_path,
        ):
            _generate_surface(target, copilot_content, check_only, verbose, generated_paths, diffs)

    # Surface 6: instructions/{lang}.instructions.md (generated from contexts)
    if CONTEXTS_LANGUAGES.is_dir():
        for ctx_file in sorted(CONTEXTS_LANGUAGES.glob("*.md")):
            lang = ctx_file.stem
            if lang in LANG_EXTENSIONS:
                content = generate_instruction_from_context(lang, ctx_file)
                for target in (
                    GITHUB_INSTRUCTIONS / f"{lang}.instructions.md",
                    TPL_INSTRUCTIONS / f"{lang}.instructions.md",
                ):
                    _generate_surface(target, content, check_only, verbose, generated_paths, diffs)

    for manual_name in sorted(MANUAL_INSTRUCTIONS):
        source = TPL_INSTRUCTIONS / manual_name
        if source.is_file():
            _generate_surface(
                GITHUB_INSTRUCTIONS / manual_name,
                source.read_text(encoding="utf-8"),
                check_only,
                verbose,
                generated_paths,
                diffs,
            )

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

    # Surface 7.5: GEMINI.md (root + .gemini/, rendered from TPL_PROJECT / GEMINI.md)
    # Spec-107 D-107-04: template at src/ai_engineering/templates/project/GEMINI.md
    # is the canonical hand-maintained source containing `__SKILL_COUNT__` /
    # `__AGENT_COUNT__` placeholders. The template is NOT rewritten by sync;
    # instead, write_gemini_md materializes counts + translate_refs(target=gemini)
    # and writes to both the repo-root GEMINI.md (Gemini CLI primary directive)
    # and `.gemini/GEMINI.md` (Gemini IDE canonical mirror).
    gemini_md_tpl = TPL_PROJECT / "GEMINI.md"
    if gemini_md_tpl.is_file():
        gemini_md_content = write_gemini_md(skills, agents)
        _generate_surface(
            ROOT / "GEMINI.md", gemini_md_content, check_only, verbose, generated_paths, diffs
        )
        _generate_surface(
            ROOT / ".gemini" / "GEMINI.md",
            gemini_md_content,
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
        (GEMINI_SKILLS, "rglob_subdirs_multi", _SKILL_SUBDIR_PREFIXES),
        (GEMINI_AGENTS, "glob", "*.md"),
        (GEMINI_AGENTS / "internal", "glob", "*.md"),
        (GITHUB_INSTRUCTIONS, "glob", "*.instructions.md"),
        (GITHUB_SKILLS, "rglob_subdirs_multi", _SKILL_SUBDIR_PREFIXES),
        (GITHUB_AGENTS, "glob", "*.md"),
        (GITHUB_AGENTS / "internal", "glob", "*.md"),
        (TPL_CLAUDE_SKILLS, "rglob_subdirs_multi", _SKILL_SUBDIR_PREFIXES),
        (TPL_CLAUDE_AGENTS, "glob", "*.md"),
        (TPL_GEMINI_SKILLS, "rglob_subdirs_multi", _SKILL_SUBDIR_PREFIXES),
        (TPL_GEMINI_AGENTS, "glob", "*.md"),
        (TPL_GEMINI_AGENTS / "internal", "glob", "*.md"),
        (TPL_CODEX_SKILLS, "rglob_subdirs_multi", _SKILL_SUBDIR_PREFIXES),
        (TPL_CODEX_AGENTS, "glob", "*.md"),
        (TPL_CODEX_AGENTS / "internal", "glob", "*.md"),
        (TPL_CODEX_HOOKS.parent, "glob", "hooks.json"),
        (TPL_CODEX_CONFIG.parent, "glob", "config.toml"),
        (TPL_GITHUB_SKILLS, "rglob_subdirs_multi", _SKILL_SUBDIR_PREFIXES),
        (TPL_GITHUB_AGENTS, "glob", "*.md"),
        (TPL_GITHUB_AGENTS / "internal", "glob", "*.md"),
    ]

    # Legacy reviewer/verifier path forwarders: spec-116 moved these agents
    # from <surface>/agents/<name>.md to <surface>/agents/internal/<name>.md.
    # The flat-path stubs are kept as deprecation aliases so external configs
    # that reference the old path still resolve. They carry `deprecated: true`
    # in their YAML frontmatter; treat them as legitimate, not orphan drift.
    def _is_legacy_alias(path: Path) -> bool:
        if path.suffix != ".md":
            return False
        name = path.name
        if not any(name.startswith(p) for p in ("reviewer-", "verifier-", "review-", "verify-")):
            return False
        try:
            head = path.read_text(encoding="utf-8", errors="replace")[:300]
        except OSError:
            return False
        return "deprecated: true" in head and "canonical: agents/internal/" in head

    orphans: list[Path] = []
    for root, mode, pattern in _ORPHAN_SURFACES:
        if not root.is_dir():
            continue
        if mode == "glob":
            for f in root.glob(str(pattern)):
                if f in generated:
                    continue
                if _is_legacy_alias(f):
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
