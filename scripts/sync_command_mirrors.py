#!/usr/bin/env python3
"""Sync command mirrors across all IDE surfaces from canonical .claude/ sources.

Canonical source (repo root):
  .claude/skills/ai-*/SKILL.md   (+ optional handlers/)
  .claude/agents/ai-*.md

Generates mirrors in:
  - .agents/skills/          (generic IDE skills -- strip ai- prefix from dir, + handlers/)
  - .agents/agents/          (generic IDE agents -- copy as-is)
  - .github/skills/          (GitHub Copilot Agent Skills -- directory per skill, + handlers/)
  - .github/agents/          (GitHub Copilot agent personas)
  - src/ai_engineering/templates/project/.claude/skills/   (install template)
  - src/ai_engineering/templates/project/.claude/agents/   (install template)
  - src/ai_engineering/templates/project/.agents/skills/   (install template)
  - src/ai_engineering/templates/project/.agents/agents/   (install template)
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

ROOT = Path(__file__).resolve().parent.parent

# Allow importing from src/ for shared utilities
sys.path.insert(0, str(ROOT / "src"))

# ── Canonical source paths (repo root .claude/) ──────────────────────────
CLAUDE_SKILLS = ROOT / ".claude" / "skills"
CLAUDE_AGENTS = ROOT / ".claude" / "agents"
MANIFEST_PATH = ROOT / ".ai-engineering" / "manifest.yml"
RUNBOOKS_ROOT = ROOT / ".ai-engineering" / "runbooks"

# ── Mirror surface paths ────────────────────────────────────────────────
AGENTS_SKILLS = ROOT / ".agents" / "skills"
AGENTS_AGENTS = ROOT / ".agents" / "agents"
GITHUB_SKILLS = ROOT / ".github" / "skills"
GITHUB_AGENTS = ROOT / ".github" / "agents"

# ── Template project paths (for ai-eng install) ────────────────────────
TPL_PROJECT = ROOT / "src" / "ai_engineering" / "templates" / "project"
TPL_CLAUDE_SKILLS = TPL_PROJECT / ".claude" / "skills"
TPL_CLAUDE_AGENTS = TPL_PROJECT / ".claude" / "agents"
TPL_AGENTS_SKILLS = TPL_PROJECT / ".agents" / "skills"
TPL_AGENTS_AGENTS = TPL_PROJECT / ".agents" / "agents"
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
        copilot_agents=("Guard", "Explorer"),
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
        display_name="Explorer",
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
        copilot_agents=("Explorer", "Guard"),
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
            "Code review agent -- multi-pass review with"
            " architecture, security, quality, and style checks."
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
        claude_tools=("Read", "Glob", "Grep"),
        copilot_agents=("Explorer",),
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
            "7-mode assessment: governance, security, quality, performance,"
            " a11y, feature-gap, architecture"
            " -- produces GO/NO-GO verdicts."
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
        claude_tools=("Read", "Glob", "Grep", "Bash"),
        copilot_agents=("Explorer",),
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
        copilot_agents=("Build", "Explorer", "Verify", "Plan", "Guard"),
        copilot_handoffs=(
            {
                "label": "📋 Create PR",
                "agent": "agent",
                "prompt": "Create a PR with the changes from the autopilot execution.",
                "send": True,
            },
        ),
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
    "ruby": "**/*.rb",
    "php": "**/*.php",
    "elixir": "**/*.ex,**/*.exs",
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


CROSS_REFERENCE_FILES: list[Path] = [
    ROOT / "CLAUDE.md",
    ROOT / "AGENTS.md",
    ROOT / ".github" / "copilot-instructions.md",
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
      - generic (.agents/): .agents/skills/X/SKILL.md, .agents/agents/ai-X.md
      - copilot (.github/): .github/skills/ai-X/SKILL.md, .github/agents/X.agent.md
      - claude: unchanged (canonical)
    """
    if target_ide == "claude":
        return content

    def _replace_skill(m: re.Match[str]) -> str:
        bt = m.group(1)
        name = m.group(2)
        if target_ide == "generic":
            path = f".agents/skills/{name}/SKILL.md"
        else:  # copilot
            path = f".github/skills/ai-{name}/SKILL.md"
        return f"{bt}{path}{bt}" if bt else path

    def _replace_agent(m: re.Match[str]) -> str:
        bt = m.group(1)
        name = m.group(2)
        if target_ide == "generic":
            path = f".agents/agents/ai-{name}.md"
        else:  # copilot
            path = f".github/agents/{name}.agent.md"
        return f"{bt}{path}{bt}" if bt else path

    content = _XREF_CLAUDE_SKILL.sub(_replace_skill, content)
    content = _XREF_CLAUDE_AGENT.sub(_replace_agent, content)

    # Directory path translations (broader patterns -- run AFTER specific file translations)
    if target_ide == "generic":
        # .claude/skills/ (directory, not followed by ai-) -> .agents/skills/
        content = re.sub(r"\.claude/skills/(?!ai-)", ".agents/skills/", content)
        # .claude/agents/ (directory) -> .agents/agents/
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
# Generation -- .agents/skills/ (generic IDE)
# ═══════════════════════════════════════════════════════════════════════════


def generate_agents_skill(name: str, skill_path: Path) -> str:
    """Generate .agents/skills/<name>/SKILL.md -- translated refs, stripped ai- prefix."""
    fm = read_frontmatter(skill_path)
    body = read_body(skill_path)

    # Adapt frontmatter: use bare name (no ai- prefix)
    fm["name"] = name
    fm.pop("metadata", None)

    header = _serialize_frontmatter(fm)
    body = translate_refs(body, "generic")

    return f"{header}\n\n{body.rstrip()}\n"


def generate_agents_agent(name: str, agent_path: Path) -> str:
    """Generate .agents/agents/ai-<name>.md -- translated refs."""
    fm = read_frontmatter(agent_path)
    body = read_body(agent_path)

    # Keep ai- prefix for agents in .agents/ surface
    fm.pop("tools", None)  # tools are IDE-specific
    fm.pop("metadata", None)

    header = _serialize_frontmatter(fm)
    body = translate_refs(body, "generic")

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

    lines.append("---")

    return "\n".join(lines) + f"\n\n{body.rstrip()}\n"


# ═══════════════════════════════════════════════════════════════════════════
# Generation -- AGENTS.md (from CLAUDE.md as canonical source)
# ═══════════════════════════════════════════════════════════════════════════

# Don't item 7 references .claude/settings.json -- Claude-specific, strip for generic IDE
_DONT_ITEM_7_RE = re.compile(
    r"^\d+\.\s+\*\*NEVER\*\*\s+disable or modify\s+`\.claude/settings\.json`\s+deny rules\.\n",
    re.MULTILINE,
)


def generate_agents_md() -> str:
    """Generate AGENTS.md from CLAUDE.md as canonical source.

    Applies:
    1. Title replacement: ``# CLAUDE.md`` -> ``# AGENTS.md``
    2. Path translation: ``.claude/`` -> ``.agents/`` via ``translate_refs``
    3. Strip Claude-specific Don't item 7 (``.claude/settings.json`` deny rules)
    4. Renumber remaining Don't items
    """
    claude_md = ROOT / "CLAUDE.md"
    content = claude_md.read_text(encoding="utf-8")

    # Replace title
    content = content.replace("# CLAUDE.md\n", "# AGENTS.md\n", 1)

    # Strip Don't item 7 (Claude-specific .claude/settings.json deny rules)
    content = _DONT_ITEM_7_RE.sub("", content)

    # Renumber Don't items after stripping item 7
    content = _renumber_dont_items(content)

    # Translate .claude/ paths to .agents/ paths
    content = translate_refs(content, "generic")

    return content


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
    """Generate .github/copilot-instructions.md from CLAUDE.md.

    Produces a condensed Copilot-specific version with:
    - Source of Truth (condensed)
    - Session Start Protocol (from Workflow Orchestration + Context Loading)
    - Plan/Execute Flow (from Task Management)
    - Absolute Prohibitions (from Don't, excluding Claude-specific items)
    - Observability (Copilot hook event names)
    - Subagent Orchestration (from AGENT_METADATA)
    - Quick Reference (counts and paths)
    """
    skill_count = len(skills)
    agent_count = len(agents)

    lines: list[str] = []

    # Header
    lines.append("# GitHub Copilot Instructions")
    lines.append("")
    lines.append("Project instructions are canonical in `.ai-engineering/`.")
    lines.append("")

    # Source of Truth (condensed)
    lines.append("## Source of Truth")
    lines.append("")
    lines.append("- Config: `.ai-engineering/manifest.yml`")
    lines.append("- Decisions: `.ai-engineering/state/decision-store.json`")
    lines.append("- Contexts: `.ai-engineering/contexts/` (languages, frameworks, team)")
    lines.append("")

    # Session Start Protocol
    lines.append("## Session Start Protocol")
    lines.append("")
    lines.append("Before non-trivial work:")
    lines.append("")
    lines.append(
        "1. **Read active spec** -- `.ai-engineering/specs/spec.md`"
        " and `.ai-engineering/specs/plan.md`."
    )
    lines.append("2. **Read decision store** -- `.ai-engineering/state/decision-store.json`.")
    lines.append(
        "3. **Read project identity** -- `.ai-engineering/contexts/project-identity.md`"
        " (if it exists)."
    )
    lines.append(
        "4. **Load contexts** -- read `.ai-engineering/contexts/languages/{lang}.md`,"
        " `frameworks/{fw}.md`, and `team/*.md` for each detected stack before writing code."
    )
    lines.append("5. **Run cleanup** -- sync repo (status, git pull, prune, branch cleanup).")
    lines.append("6. **Verify tooling** -- ruff, gitleaks, pytest, ty.")
    lines.append("")

    # Plan/Execute Flow
    lines.append("## Plan/Execute Flow (Spec-as-Gate)")
    lines.append("")
    lines.append("During `/ai-plan`:")
    lines.append("")
    lines.append("1. **Analyze** -- read code, discover requirements, assess risk (read-only).")
    lines.append(
        "2. **Produce spec as text** -- write the full spec as markdown in the conversation."
    )
    lines.append("3. **Persist via Write tool** -- write spec.md and plan.md directly to `specs/`.")
    lines.append("4. **Commit** -- stage and commit the new files.")
    lines.append(
        "5. **STOP** -- present the result and wait for the user to invoke `/ai-dispatch`."
    )
    lines.append("")

    # Absolute Prohibitions (Don't section, excluding Claude-specific items)
    lines.append("## Absolute Prohibitions")
    lines.append("")
    lines.append("1. **NEVER** `--no-verify` on any git command.")
    lines.append("2. **NEVER** skip/silence a failing gate -- fix root cause.")
    lines.append("3. **NEVER** weaken gate severity.")
    lines.append("4. **NEVER** push to protected branches (main, master).")
    lines.append(
        "5. **NEVER** dismiss security findings without"
        " `state/decision-store.json` risk acceptance."
    )
    lines.append(
        "6. **NEVER** add suppression comments to bypass static analysis or security scanners."
    )
    lines.append("")
    lines.append("Gate failure: diagnose -> fix -> retry.")
    lines.append("")

    # Observability (Copilot hook event names)
    lines.append("## Observability")
    lines.append("")
    lines.append(
        "Telemetry is **automatic via hooks** -- configured in `.github/hooks/hooks.json`."
    )
    lines.append("- `sessionStart` hook emits `session_start` events on session initialization")
    lines.append("- `sessionEnd` hook emits `session_end` events on session close")
    lines.append("- `userPromptSubmitted` hook emits `skill_invoked` events on `/ai-*` commands")
    lines.append("- `preToolUse` hook enforces deny-list (blocks dangerous operations)")
    lines.append("- `postToolUse` hook emits `agent_dispatched` events on agent use")
    lines.append("- `errorOccurred` hook emits `error_occurred` events on failures")
    lines.append("- All events -> `.ai-engineering/state/audit-log.ndjson`")
    lines.append("- Dashboards: `ai-eng observe [engineer|team|ai|dora|health]`")
    lines.append("")

    # Subagent Orchestration (from AGENT_METADATA)
    lines.append("## Subagent Orchestration")
    lines.append("")
    lines.append(
        "Orchestrator agents can delegate tasks to specialized subagents via the `agent` tool:"
    )
    lines.append("")
    lines.append("| Orchestrator | Delegates To | Handoffs |")
    lines.append("|-------------|-------------|----------|")
    for _name, meta in AGENT_METADATA.items():
        if not meta.copilot_agents:
            continue
        delegates = ", ".join(meta.copilot_agents)
        if meta.copilot_handoffs:
            handoffs = ", ".join(f"-> {h['agent']}" for h in meta.copilot_handoffs)
        else:
            handoffs = "--"
        lines.append(f"| {meta.display_name} | {delegates} | {handoffs} |")

    # Add leaf agents note
    leaf_agents = [meta.display_name for meta in AGENT_METADATA.values() if not meta.copilot_agents]
    lines.append("")
    lines.append(
        f"Leaf agents ({', '.join(sorted(leaf_agents))})"
        " cannot delegate -- they are terminal nodes."
    )
    lines.append("")
    lines.append(
        "Handoffs provide guided transitions between agents in VS Code (buttons after responses)."
    )
    lines.append(
        "Per-agent hooks (e.g., auto-format in Build) require `chat.useCustomAgentHooks: true`."
    )
    lines.append("")

    # Quick Reference
    lines.append("## Quick Reference")
    lines.append("")
    lines.append(f"- Skills ({skill_count}): `.github/skills/ai-<name>/SKILL.md`")
    lines.append(f"- Agents ({agent_count}): `.github/agents/<name>.agent.md`")
    lines.append("- Quality: coverage 80%, duplication <=3%, cyclomatic <=10, cognitive <=15")
    lines.append("- Security: zero medium+ findings, zero leaks, zero dependency vulns")
    lines.append("")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# Generation -- templates/project/ (for ai-eng install)
# ═══════════════════════════════════════════════════════════════════════════


def generate_install_claude_skill(skill_path: Path) -> str:
    """Copy .claude/skills/ai-<name>/SKILL.md as-is for install template."""
    return skill_path.read_text(encoding="utf-8")


def generate_install_claude_agent(agent_path: Path) -> str:
    """Copy .claude/agents/ai-<name>.md as-is for install template."""
    return agent_path.read_text(encoding="utf-8")


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

    for ref_file in CROSS_REFERENCE_FILES:
        if not ref_file.is_file():
            continue
        text = ref_file.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            ref_path = ROOT / ".ai-engineering" / match.group(1)
            # Allow glob-like references and placeholders
            if "*" in match.group(1) or "<" in match.group(1):
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

    # ── Pre-discover handlers/scripts/resources once per skill ───────────
    skill_handlers: dict[str, list[tuple[str, Path]]] = {}
    skill_scripts: dict[str, list[tuple[str, Path]]] = {}
    skill_resources: dict[str, list[tuple[str, Path]]] = {}
    skill_raw: dict[Path, str] = {}  # cache raw file reads
    for name, _fm, skill_path in skills:
        skill_handlers[name] = discover_handlers(skill_path.parent)
        skill_scripts[name] = discover_scripts(skill_path.parent)
        skill_resources[name] = discover_resources(skill_path.parent)
        skill_raw[skill_path] = skill_path.read_text(encoding="utf-8")
        for _h_name, h_path in skill_handlers[name]:
            skill_raw[h_path] = h_path.read_text(encoding="utf-8")
        for _s_name, s_path in skill_scripts[name]:
            skill_raw[s_path] = s_path.read_text(encoding="utf-8")
        for _r_name, r_path in skill_resources[name]:
            skill_raw[r_path] = r_path.read_text(encoding="utf-8")

    # ── Phase 2: Generate surfaces ──────────────────────────────────────

    # Surface 1: .agents/skills/<name>/SKILL.md (strip ai- prefix)
    for name, _fm, skill_path in skills:
        path = AGENTS_SKILLS / name / "SKILL.md"
        tpl = TPL_AGENTS_SKILLS / name / "SKILL.md"
        content = generate_agents_skill(name, skill_path)
        _generate_surface(path, content, check_only, verbose, generated_paths, diffs)
        _generate_surface(tpl, content, check_only, verbose, generated_paths, diffs)

        for handler_name, handler_path in skill_handlers[name]:
            translated = translate_refs(skill_raw[handler_path], "generic")
            for target in (
                AGENTS_SKILLS / name / "handlers" / f"{handler_name}.md",
                TPL_AGENTS_SKILLS / name / "handlers" / f"{handler_name}.md",
            ):
                _generate_surface(target, translated, check_only, verbose, generated_paths, diffs)

        for script_name, script_path in skill_scripts[name]:
            for target in (
                AGENTS_SKILLS / name / "scripts" / script_name,
                TPL_AGENTS_SKILLS / name / "scripts" / script_name,
            ):
                _generate_surface(
                    target, skill_raw[script_path], check_only, verbose, generated_paths, diffs
                )

        for res_name, res_path in skill_resources[name]:
            translated = translate_refs(skill_raw[res_path], "generic")
            for target in (
                AGENTS_SKILLS / name / res_name,
                TPL_AGENTS_SKILLS / name / res_name,
            ):
                _generate_surface(target, translated, check_only, verbose, generated_paths, diffs)

    # Surface 2: .agents/agents/ai-<name>.md
    for name, _fm, agent_path in agents:
        path = AGENTS_AGENTS / f"ai-{name}.md"
        tpl = TPL_AGENTS_AGENTS / f"ai-{name}.md"
        content = generate_agents_agent(name, agent_path)
        _generate_surface(path, content, check_only, verbose, generated_paths, diffs)
        _generate_surface(tpl, content, check_only, verbose, generated_paths, diffs)

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

        for script_name, script_path in skill_scripts[name]:
            for target in (
                GITHUB_SKILLS / f"ai-{name}" / "scripts" / script_name,
                TPL_GITHUB_SKILLS / f"ai-{name}" / "scripts" / script_name,
            ):
                _generate_surface(
                    target, skill_raw[script_path], check_only, verbose, generated_paths, diffs
                )

        for res_name, res_path in skill_resources[name]:
            res_content = translate_refs(skill_raw[res_path], "copilot")
            for target in (
                GITHUB_SKILLS / f"ai-{name}" / res_name,
                TPL_GITHUB_SKILLS / f"ai-{name}" / res_name,
            ):
                _generate_surface(target, res_content, check_only, verbose, generated_paths, diffs)

    # Surface 4: .github/agents/<name>.agent.md
    for name, _fm, agent_path in agents:
        meta = AGENT_METADATA.get(name)
        if not meta:
            print(f"  WARNING: No metadata for agent '{name}', skipping .github/agents/")
            continue
        path = GITHUB_AGENTS / f"{name}.agent.md"
        tpl = TPL_GITHUB_AGENTS / f"{name}.agent.md"
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

    # Surface 6: instructions/{lang}.instructions.md (generated from contexts)
    if CONTEXTS_LANGUAGES.is_dir():
        for ctx_file in sorted(CONTEXTS_LANGUAGES.glob("*.md")):
            lang = ctx_file.stem
            if lang in LANG_EXTENSIONS:
                tpl = TPL_INSTRUCTIONS / f"{lang}.instructions.md"
                content = generate_instruction_from_context(lang, ctx_file)
                _generate_surface(tpl, content, check_only, verbose, generated_paths, diffs)

    # Surface 7: AGENTS.md (root + template, generated from CLAUDE.md)
    agents_md_content = generate_agents_md()
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
    # (root, mode, prefix_filter) -- prefix_filter="" means all subdirs
    _ORPHAN_SURFACES: list[tuple[Path, str, str]] = [
        (AGENTS_SKILLS, "rglob_subdirs", ""),
        (AGENTS_AGENTS, "glob", "ai-*.md"),
        (GITHUB_SKILLS, "rglob_subdirs", "ai-"),
        (GITHUB_AGENTS, "glob", "*.agent.md"),
        (TPL_CLAUDE_SKILLS, "rglob_subdirs", "ai-"),
        (TPL_CLAUDE_AGENTS, "glob", "ai-*.md"),
        (TPL_AGENTS_SKILLS, "rglob_subdirs", ""),
        (TPL_AGENTS_AGENTS, "glob", "ai-*.md"),
        (TPL_GITHUB_SKILLS, "rglob_subdirs", "ai-"),
        (TPL_GITHUB_AGENTS, "glob", "*.agent.md"),
    ]

    orphans: list[Path] = []
    for root, mode, pattern in _ORPHAN_SURFACES:
        if not root.is_dir():
            continue
        if mode == "glob":
            for f in root.glob(pattern):
                if f not in generated:
                    orphans.append(f)
        elif mode == "rglob_subdirs":
            for sub in root.iterdir():
                if not sub.is_dir():
                    continue
                if pattern and not sub.name.startswith(pattern):
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


if __name__ == "__main__":
    sys.exit(main())
