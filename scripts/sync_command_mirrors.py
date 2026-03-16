#!/usr/bin/env python3
"""Sync command wrappers across all mirror surfaces.

Reads canonical skill and agent definitions from .ai-engineering/,
then generates or verifies mirrors in:
  - .claude/skills/          (Claude Code native skills)
  - .agents/skills/          (generic IDE skills — Windsurf, Cursor, etc.)
  - .agents/agents/          (generic IDE agents)
  - .github/prompts/         (GitHub Copilot prompt files)
  - .github/agents/          (GitHub Copilot agent personas)

Validates:
  - .claude/agents/          (Claude Code native agents — validate-only, not generated)
  - manifest.yml             (governance surface counts)
  - Cross-references         (instruction files referencing .ai-engineering/ paths)

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

# ── Canonical source paths ──────────────────────────────────────────────────
SKILLS_ROOT = ROOT / ".ai-engineering" / "skills"
AGENTS_ROOT = ROOT / ".ai-engineering" / "agents"
MANIFEST_PATH = ROOT / ".ai-engineering" / "manifest.yml"
RUNBOOKS_ROOT = ROOT / ".ai-engineering" / "runbooks"

# ── Mirror surface paths ────────────────────────────────────────────────────
CLAUDE_SKILLS = ROOT / ".claude" / "skills"
CLAUDE_AGENTS = ROOT / ".claude" / "agents"
AGENTS_SKILLS = ROOT / ".agents" / "skills"
AGENTS_AGENTS = ROOT / ".agents" / "agents"
GITHUB_PROMPTS = ROOT / ".github" / "prompts"
GITHUB_AGENTS = ROOT / ".github" / "agents"

# Directories under skills/ that are NOT skills (no SKILL.md)
SKILLS_EXCLUDE = {"references"}


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
    claude_max_turns: int


@dataclass(frozen=True)
class AgentActivation:
    """Mapping from skill name to agent activation."""

    agent_name: str
    description: str
    argument_hint: str = ""


# ── Agent metadata (single source for all surfaces) ────────────────────────
AGENT_METADATA: dict[str, AgentMeta] = {
    "build": AgentMeta(
        display_name="Build",
        description="Implementation across all stacks — the only code write agent",
        model="opus",
        color="green",
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
        claude_max_turns=50,
    ),
    "explorer": AgentMeta(
        display_name="Explorer",
        description=(
            "Context gatherer — deep codebase research, architecture mapping,"
            " dependency tracing, pattern identification, risk surfacing."
            " Read-only."
        ),
        model="opus",
        color="teal",
        copilot_tools=("codebase", "githubRepo", "readFile", "search"),
        claude_tools=("Read", "Glob", "Grep"),
        claude_max_turns=20,
    ),
    "guard": AgentMeta(
        display_name="Guard",
        description=(
            "Proactive governance advisor — checks standards, decisions,"
            " and quality trends during development."
            " Never blocks, always advisory."
        ),
        model="opus",
        color="purple",
        copilot_tools=(
            "codebase",
            "githubRepo",
            "problems",
            "readFile",
            "search",
        ),
        claude_tools=("Read", "Glob", "Grep"),
        claude_max_turns=20,
    ),
    "guide": AgentMeta(
        display_name="Guide",
        description=(
            "Developer education and onboarding — architecture tours,"
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
        claude_max_turns=25,
    ),
    "operate": AgentMeta(
        display_name="Operate",
        description=(
            "Operational runbook execution — incident response,"
            " health monitoring, maintenance tasks, and recovery procedures."
        ),
        model="sonnet",
        color="orange",
        copilot_tools=(
            "codebase",
            "githubRepo",
            "problems",
            "readFile",
            "runCommands",
            "search",
        ),
        claude_tools=("Bash", "Read", "Glob", "Grep"),
        claude_max_turns=30,
    ),
    "plan": AgentMeta(
        display_name="Plan",
        description=("Advisory planning: classify scope, assess risks, and recommend pipeline"),
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
        claude_tools=("Read", "Glob", "Grep", "Bash", "Write", "Edit"),
        claude_max_turns=30,
    ),
    "simplifier": AgentMeta(
        display_name="Simplifier",
        description=(
            "Background code simplifier — guard clauses, extract methods,"
            " flatten nesting, remove dead code."
            " Runs post-build or continuous."
        ),
        model="opus",
        color="lime",
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
        claude_max_turns=30,
    ),
    "verify": AgentMeta(
        display_name="Verify",
        description=(
            "7-mode assessment: governance, security, quality, performance,"
            " a11y, feature-gap, architecture"
            " — produces GO/NO-GO verdicts."
        ),
        model="opus",
        color="red",
        copilot_tools=(
            "codebase",
            "githubRepo",
            "problems",
            "readFile",
            "runCommands",
            "search",
        ),
        claude_tools=("Read", "Glob", "Grep", "Bash"),
        claude_max_turns=40,
    ),
}


# ── Agent-activation skills ────────────────────────────────────────────────
# These .claude/skills/ entries activate an agent instead of a canonical skill.
AGENT_ACTIVATION_SKILLS: dict[str, AgentActivation] = {
    "code": AgentActivation(
        "build",
        "Activate the ai-build agent for multi-stack implementation,"
        " testing, debugging, refactoring.",
    ),
    "explore": AgentActivation(
        "explorer",
        "Activate the ai-explorer agent for deep codebase research,"
        " architecture mapping, and context gathering.",
    ),
    "guard": AgentActivation(
        "guard",
        "Activate the ai-guard agent for proactive governance advisory,"
        " drift detection, and shift-left enforcement.",
        "all|advise|gate|drift",
    ),
    "guide": AgentActivation(
        "guide",
        "Activate the ai-guide agent for teaching, onboarding,"
        " architecture tours, and decision archaeology.",
        "teach|tour|why|onboard",
    ),
    "ops": AgentActivation(
        "operate",
        "Activate the ai-operate agent for runbook execution,"
        " incident response, and operational health monitoring.",
        "run|incident|status",
    ),
    "plan": AgentActivation(
        "plan",
        "Activate the ai-plan agent for architecture, planning,"
        " spec creation, and roadmap guidance.",
        "[topic]",
    ),
    "simplify": AgentActivation(
        "simplifier",
        "Activate the ai-simplifier agent for code simplification:"
        " guard clauses, extract methods, flatten nesting, remove dead code.",
    ),
    "verify": AgentActivation(
        "verify",
        "Activate the ai-verify agent for 7-mode scanning:"
        " governance, security, quality, performance, a11y,"
        " feature-gap, architecture.",
        "governance|security|quality|performance|a11y|feature|architecture|platform",
    ),
}

# Skills that are ONLY agent-activation (no canonical SKILL.md exists)
AGENT_ONLY_SKILLS = frozenset({"explore", "guide", "verify"})


# ── Claude-specific skill extras ───────────────────────────────────────────
# Additional body content for .claude/skills/ wrappers (context:fork, modes)
CLAUDE_SKILL_EXTRAS: dict[str, str] = {
    "accessibility": (
        "\nUse context:fork for isolated execution when performing heavy analysis.\n"
    ),
    "architecture": (
        "\nUse context:fork for isolated execution"
        " when performing heavy analysis.\n"
        "\nModes: `architecture` (default),"
        " `compatibility` (backwards compatibility analysis).\n"
    ),
    "dashboard": (
        "\nUse context:fork for isolated execution"
        " when performing heavy analysis.\n"
        "\nModes: `engineer`, `team`, `ai`, `dora`, `health`.\n"
    ),
    "evolve": ("\nUse context:fork for isolated execution when performing heavy analysis.\n"),
    "gap": (
        "\nUse context:fork for isolated execution"
        " when performing heavy analysis.\n"
        "\nModes: `all` (default), `feature`, `wiring`,"
        " `framework` (self-audit),"
        " `correctness` (verify code does what PR/spec claims).\n"
    ),
    "governance": ("\nUse context:fork for isolated execution when performing heavy analysis.\n"),
    "performance": ("\nUse context:fork for isolated execution when performing heavy analysis.\n"),
    "quality": ("\nUse context:fork for isolated execution when performing heavy analysis.\n"),
    "security": ("\nUse context:fork for isolated execution when performing heavy analysis.\n"),
}


# ── Copilot workflow aliases ────────────────────────────────────────────────
ROOT_WORKFLOW_ALIASES = ("commit", "pr", "cleanup")

COPILOT_WORKFLOW_DESCRIPTIONS: dict[str, str] = {
    "commit": (
        "Execute governed commit workflow:"
        " stage, lint, secret-detect, commit, and push current branch."
    ),
    "pr": ("Execute governed PR workflow: commit + push + create PR + auto-complete."),
    "cleanup": ("Repository hygiene: status, sync, prune, branch cleanup, spec reset."),
}

COPILOT_WORKFLOW_PRECONDITIONS: dict[str, str] = {
    "commit": (
        "Before executing, verify these preconditions:\n"
        "\n"
        "1. Current branch is NOT `main` or `master`"
        " (abort with warning if so).\n"
        "2. Working tree has staged or unstaged changes"
        " (abort if nothing to commit).\n"
        "3. Active spec is read from"
        " `.ai-engineering/context/specs/_active.md`.\n"
        "\n"
        "Read and execute the skill defined in"
        " `.ai-engineering/skills/commit/SKILL.md`.\n"
        "\n"
        "Follow the complete procedure."
        " Do not skip steps. Apply all governance notes.\n"
    ),
    "pr": (
        "Before executing, verify these preconditions:\n"
        "\n"
        "1. Current branch is NOT `main` or `master`"
        " (abort with warning if so).\n"
        "2. Working tree has staged or unstaged changes,"
        " or commits ahead of remote"
        " (abort if nothing to push/PR).\n"
        "3. Active spec is read from"
        " `.ai-engineering/context/specs/_active.md`.\n"
        "\n"
        "Read and execute the skill defined in"
        " `.ai-engineering/skills/pr/SKILL.md`.\n"
        "\n"
        "Follow the complete procedure."
        " Do not skip steps. Apply all governance notes.\n"
    ),
}


# ── Cross-reference validation targets ──────────────────────────────────────
CROSS_REFERENCE_FILES: list[Path] = [
    ROOT / "CLAUDE.md",
    ROOT / "AGENTS.md",
    ROOT / ".github" / "copilot-instructions.md",
    ROOT / ".github" / "copilot" / "code-generation.md",
    ROOT / ".github" / "copilot" / "code-review.md",
    ROOT / ".github" / "copilot" / "commit-message.md",
    ROOT / ".github" / "copilot" / "test-generation.md",
    ROOT / ".github" / "instructions" / "python.instructions.md",
    ROOT / ".github" / "instructions" / "testing.instructions.md",
    ROOT / ".github" / "instructions" / "markdown.instructions.md",
    ROOT / ".github" / "instructions" / "sonarqube_mcp.instructions.md",
]


# ═══════════════════════════════════════════════════════════════════════════
# Discovery
# ═══════════════════════════════════════════════════════════════════════════


def parse_frontmatter(path: Path) -> dict[str, str]:
    """Extract YAML frontmatter fields from a markdown file."""
    from ai_engineering.lib.parsing import parse_frontmatter as _parse

    text = path.read_text(encoding="utf-8")
    return _parse(text)


def discover_skills() -> list[tuple[str, dict[str, str], Path]]:
    """Discover all skills from flat layout.

    Returns (name, frontmatter, skill_file_path) tuples.
    """
    skills = []
    for skill_dir in sorted(SKILLS_ROOT.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name in SKILLS_EXCLUDE:
            continue
        skill_file = skill_dir / "SKILL.md"
        if skill_file.is_file():
            fm = parse_frontmatter(skill_file)
            name = fm.get("name", skill_dir.name)
            skills.append((name, fm, skill_file))
    return skills


def discover_agents() -> list[tuple[str, dict[str, str]]]:
    """Discover all agents. Returns (name, frontmatter) tuples."""
    agents = []
    for agent_file in sorted(AGENTS_ROOT.glob("*.md")):
        fm = parse_frontmatter(agent_file)
        name = fm.get("name", agent_file.stem)
        agents.append((name, fm))
    return agents


# ═══════════════════════════════════════════════════════════════════════════
# Generation — .claude/skills/
# ═══════════════════════════════════════════════════════════════════════════


def generate_claude_skill(name: str, fm: dict[str, str]) -> str:
    """Generate .claude/skills/ai-<name>/SKILL.md wrapper."""
    desc = fm.get("description", "").strip("\"'")
    hint = fm.get("argument-hint", "").strip("\"'")
    extras = CLAUDE_SKILL_EXTRAS.get(name, "")

    lines = ["---"]
    lines.append(f"name: ai-{name}")
    lines.append(f'description: "{desc}"')
    if hint:
        lines.append(f'argument-hint: "{hint}"')
    lines.append("---")
    lines.append("")
    lines.append(f"Read and execute the skill defined in `.ai-engineering/skills/{name}/SKILL.md`.")
    if extras:
        lines.append(extras)
    lines.append("$ARGUMENTS")
    lines.append("")
    return "\n".join(lines)


def generate_claude_agent_activation(
    skill_name: str,
    activation: AgentActivation,
) -> str:
    """Generate .claude/skills/ai-<name>/SKILL.md for agent-activation skills."""
    lines = ["---"]
    lines.append(f"name: ai-{skill_name}")
    lines.append(f'description: "{activation.description}"')
    if activation.argument_hint:
        lines.append(f'argument-hint: "{activation.argument_hint}"')
    lines.append("---")
    lines.append("")
    lines.append(f"Activate the `@ai-{activation.agent_name}` agent for this task.")
    lines.append("")
    lines.append(
        f"Read the agent file at"
        f" `.ai-engineering/agents/{activation.agent_name}.md` completely."
        f" Adopt the identity, capabilities, and behavior."
        f" Follow behavior steps in order."
        f" Respect all boundaries."
        f" Read all referenced skills and standards."
    )
    lines.append("")
    lines.append("$ARGUMENTS")
    lines.append("")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# Generation — .agents/skills/ and .agents/agents/
# ═══════════════════════════════════════════════════════════════════════════


def generate_agents_skill(canonical_path: Path) -> str:
    """Generate .agents/skills/<name>/SKILL.md — full copy of canonical."""
    return canonical_path.read_text(encoding="utf-8")


def generate_agents_agent(name: str, meta: AgentMeta) -> str:
    """Generate .agents/agents/ai-<name>.md — thin wrapper."""
    return (
        f"---\n"
        f"name: {name}\n"
        f'description: "{meta.description}"\n'
        f"---\n"
        f"\n"
        f"Activate the agent persona defined in"
        f" `.ai-engineering/agents/{name}.md`.\n"
        f"Read the agent file completely."
        f" Adopt the identity, capabilities, and behavior.\n"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Generation — .github/prompts/ and .github/agents/
# ═══════════════════════════════════════════════════════════════════════════


def generate_skill_copilot_prompt(name: str, description: str) -> str:
    """Generate Copilot prompt file for a skill."""
    desc = description or f"{name} skill"
    body = (
        f"Read and execute the skill defined in"
        f" `.ai-engineering/skills/{name}/SKILL.md`.\n"
        f"\n"
        f"Follow the complete procedure."
        f" Do not skip steps. Apply all governance notes.\n"
    )
    return f'---\ndescription: "{desc}"\nmode: "agent"\n---\n\n{body}'


def generate_copilot_agent(name: str, meta: AgentMeta) -> str:
    """Generate Copilot agent file with per-agent metadata."""
    tools_str = ", ".join(meta.copilot_tools)
    return (
        f"---\n"
        f'name: "{meta.display_name}"\n'
        f'description: "{meta.description}"\n'
        f"model: {meta.model}\n"
        f"color: {meta.color}\n"
        f"tools: [{tools_str}]\n"
        f"---\n"
        f"\n"
        f"Activate the agent persona defined in"
        f" `.ai-engineering/agents/{name}.md`.\n"
        f"\n"
        f"Read the agent file completely."
        f" Adopt the identity, capabilities, and behavior.\n"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════════════════════


def validate_canonical(
    skills: list[tuple[str, dict[str, str], Path]],
    agents: list[tuple[str, dict[str, str]]],
) -> tuple[list[str], list[str]]:
    """Validate canonical frontmatter: name + description required."""
    errors: list[str] = []
    warnings: list[str] = []
    for _name, fm, path in skills:
        rel = path.relative_to(ROOT)
        if not fm.get("description"):
            errors.append(f"{rel}: missing 'description' in frontmatter")
    for name, fm in agents:
        if not fm.get("name"):
            warnings.append(f"Agent '{name}': missing 'name' in frontmatter")
    return errors, warnings


def validate_manifest(
    skills: list[tuple[str, dict[str, str], Path]],
    agents: list[tuple[str, dict[str, str]]],
) -> tuple[list[str], list[str]]:
    """Validate governance_surface counts in manifest.yml."""
    errors: list[str] = []
    warnings: list[str] = []

    try:
        import yaml
    except ImportError:
        warnings.append("pyyaml not installed — skipping manifest validation")
        return errors, warnings

    if not MANIFEST_PATH.is_file():
        errors.append(f"Manifest not found: {MANIFEST_PATH.relative_to(ROOT)}")
        return errors, warnings

    data = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    gov = data.get("governance_surface", {})
    m_agents = gov.get("agents", {})
    m_skills = gov.get("skills", {})

    expected_agent_count = m_agents.get("total", 0)
    expected_agent_names = set(m_agents.get("names", []))
    expected_skill_count = m_skills.get("total", 0)

    actual_agent_names = {name for name, _ in agents}
    actual_skill_count = len(skills)

    if len(agents) != expected_agent_count:
        errors.append(
            f"Agent count mismatch: manifest={expected_agent_count}, discovered={len(agents)}"
        )
    if actual_agent_names != expected_agent_names:
        missing = expected_agent_names - actual_agent_names
        extra = actual_agent_names - expected_agent_names
        if missing:
            errors.append(f"Agents in manifest but not found: {sorted(missing)}")
        if extra:
            errors.append(f"Agents found but not in manifest: {sorted(extra)}")

    if actual_skill_count != expected_skill_count:
        errors.append(
            f"Skill count mismatch: manifest={expected_skill_count},"
            f" discovered={actual_skill_count}"
        )

    return errors, warnings


def validate_claude_agents() -> list[str]:
    """Validate .claude/agents/ exist with required frontmatter."""
    warnings: list[str] = []
    required_fields = {"name", "model", "description", "tools"}

    for agent_name in AGENT_METADATA:
        path = CLAUDE_AGENTS / f"ai-{agent_name}.md"
        if not path.is_file():
            warnings.append(f"Missing Claude agent: {path.relative_to(ROOT)}")
            continue
        fm = parse_frontmatter(path)
        missing = required_fields - set(fm.keys())
        if missing:
            warnings.append(
                f"{path.relative_to(ROOT)}: missing frontmatter fields: {sorted(missing)}"
            )
    return warnings


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
            # Allow glob-like references (e.g. **) and placeholders (e.g. <stack>)
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
    print("Validating canonical sources...")
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

    agent_warnings = validate_claude_agents()
    if agent_warnings:
        _print_issues("Claude agent warnings", agent_warnings)

    xref_warnings = validate_cross_references(verbose=verbose)
    if xref_warnings:
        _print_issues("Cross-reference warnings", xref_warnings)

    runbook_warnings = validate_runbooks()
    if runbook_warnings:
        _print_issues("Runbook warnings", runbook_warnings)

    skill_count = len(skills)
    agent_count = len(agents)
    print(
        f"Discovered: {skill_count} skills, {agent_count} agents,"
        f" {len(AGENT_ACTIVATION_SKILLS)} agent-activation skills"
    )

    # ── Phase 2: Generate surfaces ──────────────────────────────────────

    # Surface 1: .claude/skills/
    for name, fm, _path in skills:
        if name in AGENT_ACTIVATION_SKILLS:
            continue  # Handled below as agent-activation
        path = CLAUDE_SKILLS / f"ai-{name}" / "SKILL.md"
        content = generate_claude_skill(name, fm)
        generated_paths.add(path)
        diff = _check_or_write(path, content, check_only, verbose)
        if diff:
            diffs.append(diff)

    for skill_name, activation in AGENT_ACTIVATION_SKILLS.items():
        path = CLAUDE_SKILLS / f"ai-{skill_name}" / "SKILL.md"
        content = generate_claude_agent_activation(skill_name, activation)
        generated_paths.add(path)
        diff = _check_or_write(path, content, check_only, verbose)
        if diff:
            diffs.append(diff)

    # Surface 2: .agents/skills/ (full copies of canonical, skip agent-only)
    for name, _fm, skill_path in skills:
        if name in AGENT_ONLY_SKILLS:
            continue
        path = AGENTS_SKILLS / name / "SKILL.md"
        content = generate_agents_skill(skill_path)
        generated_paths.add(path)
        diff = _check_or_write(path, content, check_only, verbose)
        if diff:
            diffs.append(diff)

    # Surface 3: .agents/agents/
    for name, _fm in agents:
        meta = AGENT_METADATA.get(name)
        if not meta:
            print(f"  WARNING: No metadata for agent '{name}', skipping")
            continue
        path = AGENTS_AGENTS / f"ai-{name}.md"
        content = generate_agents_agent(name, meta)
        generated_paths.add(path)
        diff = _check_or_write(path, content, check_only, verbose)
        if diff:
            diffs.append(diff)

    # Surface 4: .github/prompts/ (skills, skip agent-only)
    for name, fm, _path in skills:
        if name in AGENT_ONLY_SKILLS:
            continue
        description = fm.get("description", "").strip("\"'")
        path = GITHUB_PROMPTS / f"ai-{name}.prompt.md"
        content = generate_skill_copilot_prompt(name, description)
        generated_paths.add(path)
        diff = _check_or_write(path, content, check_only, verbose)
        if diff:
            diffs.append(diff)

    # Surface 4b: .github/prompts/ (workflow aliases)
    for alias in ROOT_WORKFLOW_ALIASES:
        desc = COPILOT_WORKFLOW_DESCRIPTIONS.get(alias, f"{alias} workflow")
        if alias in COPILOT_WORKFLOW_PRECONDITIONS:
            body = COPILOT_WORKFLOW_PRECONDITIONS[alias]
        else:
            body = (
                f"Read and execute the skill defined in"
                f" `.ai-engineering/skills/{alias}/SKILL.md`.\n"
                f"\n"
                f"Follow the complete procedure."
                f" Do not skip steps. Apply all governance notes.\n"
            )
        path = GITHUB_PROMPTS / f"{alias}.prompt.md"
        content = f'---\ndescription: "{desc}"\nmode: "agent"\n---\n\n{body}'
        generated_paths.add(path)
        diff = _check_or_write(path, content, check_only, verbose)
        if diff:
            diffs.append(diff)

    # Surface 5: .github/agents/
    for name, _fm in agents:
        meta = AGENT_METADATA.get(name)
        if not meta:
            continue
        path = GITHUB_AGENTS / f"{name}.agent.md"
        content = generate_copilot_agent(name, meta)
        generated_paths.add(path)
        diff = _check_or_write(path, content, check_only, verbose)
        if diff:
            diffs.append(diff)

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
    """Find and handle orphan files across all generated surfaces."""
    orphans: list[Path] = []

    # .claude/skills/ai-*/SKILL.md
    if CLAUDE_SKILLS.is_dir():
        for skill_dir in CLAUDE_SKILLS.iterdir():
            if skill_dir.is_dir() and skill_dir.name.startswith("ai-"):
                skill_file = skill_dir / "SKILL.md"
                if skill_file.is_file() and skill_file not in generated:
                    orphans.append(skill_file)

    # .agents/skills/*/SKILL.md
    if AGENTS_SKILLS.is_dir():
        for skill_dir in AGENTS_SKILLS.iterdir():
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.is_file() and skill_file not in generated:
                    orphans.append(skill_file)

    # .agents/agents/ai-*.md
    if AGENTS_AGENTS.is_dir():
        for f in AGENTS_AGENTS.glob("ai-*.md"):
            if f not in generated:
                orphans.append(f)

    # .github/prompts/*.prompt.md
    if GITHUB_PROMPTS.is_dir():
        for f in GITHUB_PROMPTS.glob("*.prompt.md"):
            if f not in generated:
                orphans.append(f)

    # .github/agents/*.agent.md
    if GITHUB_AGENTS.is_dir():
        for f in GITHUB_AGENTS.glob("*.agent.md"):
            if f not in generated:
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
                # Remove empty parent directories
                parent = orphan.parent
                if parent.is_dir() and not any(parent.iterdir()):
                    parent.rmdir()
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
        description="Sync mirror surfaces from canonical .ai-engineering/ sources.",
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
