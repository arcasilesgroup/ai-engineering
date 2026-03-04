#!/usr/bin/env python3
"""Sync command wrappers across all mirror surfaces.

Reads canonical skill and agent definitions from .ai-engineering/,
then generates or verifies mirrors in:
  - .claude/commands/ai/     (Claude Code slash commands, unified ai: namespace)
  - .claude/commands/         (root-level workflow aliases: commit, pr, cleanup)
  - .github/prompts/          (GitHub Copilot prompt files)
  - .github/agents/           (GitHub Copilot agent personas)

Usage:
  python scripts/sync_command_mirrors.py           # generate all mirrors
  python scripts/sync_command_mirrors.py --check   # verify, exit 1 on drift
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_ROOT = ROOT / ".ai-engineering" / "skills"
AGENTS_ROOT = ROOT / ".ai-engineering" / "agents"
CLAUDE_COMMANDS = ROOT / ".claude" / "commands"
GITHUB_PROMPTS = ROOT / ".github" / "prompts"
GITHUB_AGENTS = ROOT / ".github" / "agents"

# Directories under skills/ that are NOT skills (no SKILL.md)
SKILLS_EXCLUDE = {"references"}

# Workflow commands with custom preconditions (root-level aliases)
WORKFLOW_PRECONDITIONS: dict[str, str] = {
    "commit": (
        "Before executing, verify these preconditions:\n"
        "\n"
        "1. Current branch is NOT `main` or `master` (abort with warning if so).\n"
        "2. Working tree has staged or unstaged changes (abort if nothing to commit).\n"
        "3. Active spec is read from `.ai-engineering/context/specs/_active.md`.\n"
        "\n"
        "Read and execute the workflow skill defined in "
        "`.ai-engineering/skills/commit/SKILL.md`.\n"
        "\n"
        "Arguments: no arguments = default flow. "
        "`--only` = restricted variant (if defined).\n"
        "\n"
        "Follow the complete procedure. Do not skip steps. "
        "Apply all governance notes. Read the Command Contract in "
        "`.ai-engineering/manifest.yml` under `commands:` "
        "for the authoritative step sequence.\n"
        "\n"
        "$ARGUMENTS\n"
    ),
    "pr": (
        "Before executing, verify these preconditions:\n"
        "\n"
        "1. Current branch is NOT `main` or `master` (abort with warning if so).\n"
        "2. Working tree has staged or unstaged changes, "
        "or commits ahead of remote (abort if nothing to push/PR).\n"
        "3. Active spec is read from `.ai-engineering/context/specs/_active.md`.\n"
        "\n"
        "Read and execute the workflow skill defined in "
        "`.ai-engineering/skills/pr/SKILL.md`.\n"
        "\n"
        "Arguments: no arguments = default flow. "
        "`--only` = restricted variant (if defined).\n"
        "\n"
        "Follow the complete procedure. Do not skip steps. "
        "Apply all governance notes. Read the Command Contract in "
        "`.ai-engineering/manifest.yml` under `commands:` "
        "for the authoritative step sequence.\n"
        "\n"
        "$ARGUMENTS\n"
    ),
}

# Copilot workflow prompt descriptions (richer than generic)
COPILOT_WORKFLOW_DESCRIPTIONS: dict[str, str] = {
    "commit": (
        "Execute governed commit workflow: stage, lint, secret-detect,"
        " commit, and push current branch."
    ),
    "pr": "Execute governed PR workflow: commit + push + create PR + auto-complete.",
    "cleanup": "Repository hygiene: status, sync, prune, branch cleanup, spec reset.",
}

# Copilot preconditions for workflow prompts (root-level aliases)
COPILOT_WORKFLOW_PRECONDITIONS: dict[str, str] = {
    "commit": (
        "Before executing, verify these preconditions:\n"
        "\n"
        "1. Current branch is NOT `main` or `master` (abort with warning if so).\n"
        "2. Working tree has staged or unstaged changes (abort if nothing to commit).\n"
        "3. Active spec is read from `.ai-engineering/context/specs/_active.md`.\n"
        "\n"
        "Read and execute the skill defined in "
        "`.ai-engineering/skills/commit/SKILL.md`.\n"
        "\n"
        "Follow the complete procedure. Do not skip steps. "
        "Apply all governance notes.\n"
    ),
    "pr": (
        "Before executing, verify these preconditions:\n"
        "\n"
        "1. Current branch is NOT `main` or `master` (abort with warning if so).\n"
        "2. Working tree has staged or unstaged changes, "
        "or commits ahead of remote (abort if nothing to push/PR).\n"
        "3. Active spec is read from `.ai-engineering/context/specs/_active.md`.\n"
        "\n"
        "Read and execute the skill defined in "
        "`.ai-engineering/skills/pr/SKILL.md`.\n"
        "\n"
        "Follow the complete procedure. Do not skip steps. "
        "Apply all governance notes.\n"
    ),
}

# Root-level workflow aliases (in .claude/commands/ and .github/prompts/)
ROOT_WORKFLOW_ALIASES = ("commit", "pr", "cleanup")

# Copilot agent tools list (standard set)
COPILOT_AGENT_TOOLS = [
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
]

# Short descriptions for the 6 consolidated agents
AGENT_DESCRIPTIONS: dict[str, tuple[str, str]] = {
    "plan": ("Plan", "Orchestration, planning pipeline, dispatch, work-item sync"),
    "build": (
        "Build",
        "Implementation across all stacks — the only code write agent",
    ),
    "review": (
        "Review",
        "All reviews, security, quality, governance checks (individual modes)",
    ),
    "scan": (
        "Scan",
        "Feature scanner — spec-vs-code gap analysis and architecture drift",
    ),
    "write": ("Write", "Documentation, changelogs, explanations"),
    "triage": ("Triage", "Auto-prioritize work items in Azure Boards / GitHub Issues"),
}


def parse_frontmatter(path: Path) -> dict[str, str]:
    """Extract YAML frontmatter fields from a markdown file using regex."""
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    block = match.group(1)
    result: dict[str, str] = {}
    for line in block.splitlines():
        m = re.match(r"^(\w+):\s*(?:\"(.*?)\"|'(.*?)'|(.+))$", line)
        if m:
            key = m.group(1)
            value = m.group(2) or m.group(3) or m.group(4)
            result[key] = value.strip()
    return result


def discover_skills() -> list[tuple[str, dict[str, str]]]:
    """Discover all skills from flat layout. Returns (name, frontmatter) tuples."""
    skills = []
    for skill_dir in sorted(SKILLS_ROOT.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name in SKILLS_EXCLUDE:
            continue
        skill_file = skill_dir / "SKILL.md"
        if skill_file.is_file():
            fm = parse_frontmatter(skill_file)
            name = fm.get("name", skill_dir.name)
            skills.append((name, fm))
    return skills


def discover_agents() -> list[tuple[str, dict[str, str]]]:
    """Discover all agents. Returns (name, frontmatter) tuples."""
    agents = []
    for agent_file in sorted(AGENTS_ROOT.glob("*.md")):
        fm = parse_frontmatter(agent_file)
        name = fm.get("name", agent_file.stem)
        agents.append((name, fm))
    return agents


def generate_skill_claude_command(name: str) -> str:
    """Generate Claude Code command wrapper for a skill."""
    return (
        f"Read and execute the skill defined in "
        f"`.ai-engineering/skills/{name}/SKILL.md`.\n"
        f"\n"
        f"Follow the complete procedure. Do not skip steps. "
        f"Apply all governance notes. If the skill references "
        f"standards or other skills, read those as needed.\n"
        f"\n"
        f"$ARGUMENTS\n"
    )


def generate_agent_claude_command(name: str) -> str:
    """Generate Claude Code command wrapper for an agent."""
    return (
        f"Activate the agent persona defined in "
        f"`.ai-engineering/agents/{name}.md`.\n"
        f"\n"
        f"Read the agent file completely. Adopt the identity, capabilities, "
        f"and behavior. Follow behavior steps in order. Respect all boundaries. "
        f"Read all referenced skills and standards.\n"
        f"\n"
        f"$ARGUMENTS\n"
    )


def generate_skill_copilot_prompt(name: str, description: str) -> str:
    """Generate Copilot prompt file for a skill."""
    desc = description or f"{name} skill"
    body = (
        f"Read and execute the skill defined in "
        f"`.ai-engineering/skills/{name}/SKILL.md`.\n"
        f"\n"
        f"Follow the complete procedure. Do not skip steps. "
        f"Apply all governance notes.\n"
    )
    return f'---\ndescription: "{desc}"\nmode: "agent"\n---\n\n{body}'


def generate_agent_copilot_agent(name: str) -> str:
    """Generate Copilot agent file for an agent."""
    display_name, desc = AGENT_DESCRIPTIONS.get(
        name, (name.replace("-", " ").title(), f"{name} agent")
    )
    tools_str = ", ".join(COPILOT_AGENT_TOOLS)
    return (
        f"---\n"
        f'name: "{display_name}"\n'
        f'description: "{desc}"\n'
        f"tools: [{tools_str}]\n"
        f"---\n"
        f"\n"
        f"Activate the agent persona defined in "
        f"`.ai-engineering/agents/{name}.md`.\n"
        f"\n"
        f"Read the agent file completely. Adopt the identity, "
        f"capabilities, and behavior.\n"
    )


def sync_all(*, check_only: bool = False) -> int:
    """Generate or check all mirror files. Returns exit code."""
    skills = discover_skills()
    agents = discover_agents()
    agent_names = {name for name, _ in agents}
    diffs: list[str] = []
    generated_paths: set[Path] = set()

    # --- Skills (ai/ namespace) ---
    for name, fm in skills:
        description = fm.get("description", "")
        description = description.strip("\"'")

        # Claude command: .claude/commands/ai/{name}.md
        # Skip if name collides with an agent (agent takes priority)
        if name not in agent_names:
            cc_path = CLAUDE_COMMANDS / "ai" / f"{name}.md"
            cc_content = generate_skill_claude_command(name)
            generated_paths.add(cc_path)
            diff = _check_or_write(cc_path, cc_content, check_only)
            if diff:
                diffs.append(diff)

        # Copilot prompt: .github/prompts/ai-{name}.prompt.md
        cp_path = GITHUB_PROMPTS / f"ai-{name}.prompt.md"
        cp_content = generate_skill_copilot_prompt(name, description)
        generated_paths.add(cp_path)
        diff = _check_or_write(cp_path, cp_content, check_only)
        if diff:
            diffs.append(diff)

    # --- Agents ---
    for name, _fm in agents:
        # Claude command: .claude/commands/ai/{name}.md
        ca_path = CLAUDE_COMMANDS / "ai" / f"{name}.md"
        ca_content = generate_agent_claude_command(name)
        generated_paths.add(ca_path)
        diff = _check_or_write(ca_path, ca_content, check_only)
        if diff:
            diffs.append(diff)

        # Copilot agent: .github/agents/{name}.agent.md
        ga_path = GITHUB_AGENTS / f"{name}.agent.md"
        ga_content = generate_agent_copilot_agent(name)
        generated_paths.add(ga_path)
        diff = _check_or_write(ga_path, ga_content, check_only)
        if diff:
            diffs.append(diff)

    # --- Root-level workflow aliases ---
    for alias in ROOT_WORKFLOW_ALIASES:
        # Claude command: .claude/commands/{alias}.md
        if alias in WORKFLOW_PRECONDITIONS:
            wf_content = WORKFLOW_PRECONDITIONS[alias]
        else:
            # Simple skill wrapper (e.g. cleanup)
            wf_content = generate_skill_claude_command(alias)
        wf_path = CLAUDE_COMMANDS / f"{alias}.md"
        generated_paths.add(wf_path)
        diff = _check_or_write(wf_path, wf_content, check_only)
        if diff:
            diffs.append(diff)

        # Copilot prompt: .github/prompts/{alias}.prompt.md
        desc = COPILOT_WORKFLOW_DESCRIPTIONS.get(alias, f"{alias} workflow")
        if alias in COPILOT_WORKFLOW_PRECONDITIONS:
            body = COPILOT_WORKFLOW_PRECONDITIONS[alias]
        else:
            body = (
                f"Read and execute the skill defined in "
                f"`.ai-engineering/skills/{alias}/SKILL.md`.\n"
                f"\n"
                f"Follow the complete procedure. Do not skip steps. "
                f"Apply all governance notes.\n"
            )
        cp_path = GITHUB_PROMPTS / f"{alias}.prompt.md"
        cp_content = f'---\ndescription: "{desc}"\nmode: "agent"\n---\n\n{body}'
        generated_paths.add(cp_path)
        diff = _check_or_write(cp_path, cp_content, check_only)
        if diff:
            diffs.append(diff)

    # --- Orphan detection ---
    orphans = _detect_orphans(generated_paths)
    if orphans:
        print(f"\nOrphans detected ({len(orphans)}):")
        for o in orphans:
            print(f"  {o.relative_to(ROOT)}")

    # --- Summary ---
    total_generated = len(generated_paths)
    if diffs:
        action = "would change" if check_only else "updated"
        print(f"\n{len(diffs)}/{total_generated} files {action}:")
        for d in diffs:
            print(f"  {d}")
        if check_only:
            print("\nRun without --check to apply changes.")
            return 1
        return 0

    status = "in sync" if check_only else "generated"
    print(f"\nAll {total_generated} mirror files {status}. No changes needed.")
    return 0


def _check_or_write(path: Path, content: str, check_only: bool) -> str | None:
    """Compare or write a file. Returns relative path if changed, else None."""
    rel = str(path.relative_to(ROOT))
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing == content:
            return None
        if check_only:
            return f"DRIFT: {rel}"
        path.write_text(content, encoding="utf-8")
        return f"UPDATED: {rel}"
    if check_only:
        return f"MISSING: {rel}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"CREATED: {rel}"


def _detect_orphans(generated: set[Path]) -> list[Path]:
    """Find files in mirror directories that don't correspond to a source."""
    orphans = []
    # Check Claude commands (ai/ namespace)
    ai_dir = CLAUDE_COMMANDS / "ai"
    if ai_dir.is_dir():
        for f in ai_dir.glob("*.md"):
            if f not in generated:
                orphans.append(f)
    # Check Claude commands (root workflow aliases)
    for f in CLAUDE_COMMANDS.glob("*.md"):
        if f not in generated:
            orphans.append(f)
    # Check Copilot prompts
    if GITHUB_PROMPTS.is_dir():
        for f in GITHUB_PROMPTS.glob("*.prompt.md"):
            if f not in generated:
                orphans.append(f)
    # Check Copilot agents
    if GITHUB_AGENTS.is_dir():
        for f in GITHUB_AGENTS.glob("*.agent.md"):
            if f not in generated:
                orphans.append(f)
    return sorted(orphans)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync command mirror surfaces from canonical sources."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify mirrors are in sync; exit 1 if drift detected.",
    )
    args = parser.parse_args()
    return sync_all(check_only=args.check)


if __name__ == "__main__":
    sys.exit(main())
