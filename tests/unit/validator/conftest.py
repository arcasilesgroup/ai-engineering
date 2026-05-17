"""Shared fixtures and helpers for tests/unit/validator/.

Extracted from the monolithic tests/unit/test_validator.py during
spec-140 W2.5.T4. Helpers stay as plain module-level functions so the
split test files can import them by name without rewriting every call
site (the original monolith referenced them directly).
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.config.mirror_inventory import get_generated_provenance_fields
from ai_engineering.state.defaults import default_ownership_map
from ai_engineering.state.io import write_json_model
from ai_engineering.state.models import EvidenceRef, HandoffRef

# Dynamic discovery from real project -- never hardcode lists that can drift.
# Canonical source is templates/project/.claude/ (skills and agents live here post spec-055).
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_TEMPLATES_CLAUDE_DIR = (
    _PROJECT_ROOT / "src" / "ai_engineering" / "templates" / "project" / ".claude"
)

_SKILL_PATHS = sorted(
    f"skills/{d.name}/SKILL.md"
    for d in (_TEMPLATES_CLAUDE_DIR / "skills").iterdir()
    if d.is_dir() and (d / "SKILL.md").is_file()
)

# CLAUDE.md / AGENTS.md canonical contract: only first-class `ai-*` agents are
# enumerated (9). reviewer-* / verifier-* / verify-* are specialists dispatched
# internally and NOT counted in the manifest registry (see
# scripts/sync_mirrors/core.discover_agents).
_AGENT_PATHS = sorted(
    f"agents/{f.name}" for f in (_TEMPLATES_CLAUDE_DIR / "agents").glob("ai-*.md")
)


def _make_governance(root: Path) -> Path:
    """Create a minimal .ai-engineering governance tree."""
    ai = root / ".ai-engineering"
    # spec-136 D-136-01/D-136-06: contexts/ hard-deleted; reference/ is the
    # single framework reference home and team/ lifts to top-level.
    for d in ["reference", "team", "specs", "state"]:
        (ai / d).mkdir(parents=True, exist_ok=True)
    return ai


def _write_skill(ai: Path, rel: str) -> None:
    """Create a skill/agent markdown file.

    Skills use flat directory layout: skills/<name>/SKILL.md.
    Agents remain flat: agents/<name>.md.
    """
    path = ai / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if rel.startswith("skills/"):
        # Flat layout: name = parent dir.
        skill_name = path.parent.name
        path.write_text(
            f"---\nname: {skill_name}\nversion: 1.0.0\n---\n\n# {skill_name}\n",
            encoding="utf-8",
        )
    else:
        path.write_text(f"# {path.stem}\n", encoding="utf-8")


def _make_instruction_content(
    skills: list[str] | None = None,
    agents: list[str] | None = None,
) -> str:
    """Build instruction file content with skill/agent listings (IDE-specific paths).

    The parser (_SKILL_PATH_PATTERN / _AGENT_PATH_PATTERN) expects IDE-specific
    paths like ``.claude/skills/<name>/SKILL.md`` -- not ``.ai-engineering/``.
    """
    skill_list = skills if skills is not None else _SKILL_PATHS
    agent_list = agents if agents is not None else _AGENT_PATHS
    lines = ["# Instructions", "", "## Skills", ""]
    for s in skill_list:
        lines.append(f"- `.claude/{s}`")
    lines.append("")
    lines.extend(["## Agents", ""])
    for a in agent_list:
        lines.append(f"- `.claude/{a}`")
    lines.append("")
    return "\n".join(lines)


def _write_all_instruction_files(
    root: Path,
    content: str | None = None,
) -> None:
    """Write identical instruction files to all 8 standard locations."""
    text = content if content is not None else _make_instruction_content()
    files = [
        root / ".github" / "copilot-instructions.md",
        root / "AGENTS.md",
        root / "CLAUDE.md",
        root / "src" / "ai_engineering" / "templates" / "project" / "copilot-instructions.md",
        root / "src" / "ai_engineering" / "templates" / "project" / "AGENTS.md",
        root / "src" / "ai_engineering" / "templates" / "project" / "CLAUDE.md",
    ]
    for f in files:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")


def _write_manifest(
    ai: Path,
    *,
    providers: tuple[str, ...] = ("claude-code", "github-copilot"),
    skills_total: int | None = None,
    agents_total: int | None = None,
) -> None:
    """Write a minimal manifest.yml."""
    m = ai / "manifest.yml"
    skills_block = f"skills:\n  total: {skills_total}\n" if skills_total is not None else ""
    agents_block = f"agents:\n  total: {agents_total}\n" if agents_total is not None else ""
    m.write_text(
        "name: test-project\nversion: 1.0.0\n"
        f"{skills_block}{agents_block}"
        f"surfaces:\n  enabled: [{', '.join(providers)}]\n  primary: {providers[0]}\n"
        "ownership:\n"
        '  framework: [".ai-engineering/**"]\n'
        "  root_entry_points:\n"
        "    CLAUDE.md:\n"
        "      owner: framework\n"
        "      canonical_source: CLAUDE.md\n"
        "      runtime_role: ide-overlay\n"
        "      sync:\n"
        "        mode: copy\n"
        "        template_path: src/ai_engineering/templates/project/CLAUDE.md\n"
        "        mirror_paths: []\n"
        "    AGENTS.md:\n"
        "      owner: framework\n"
        "      canonical_source: scripts/sync_command_mirrors.py:generate_agents_md\n"
        "      runtime_role: shared-runtime-contract\n"
        "      sync:\n"
        "        mode: generate\n"
        "        template_path: src/ai_engineering/templates/project/AGENTS.md\n"
        "        mirror_paths: []\n"
        '    ".github/copilot-instructions.md":\n'
        "      owner: framework\n"
        "      canonical_source: CLAUDE.md\n"
        "      runtime_role: ide-overlay\n"
        "      sync:\n"
        "        mode: generate\n"
        "        template_path: src/ai_engineering/templates/project/copilot-instructions.md\n"
        "        mirror_paths: []\n"
        '  team: [".ai-engineering/team/**"]\n'
        '  system: [".ai-engineering/state/**"]\n',
        encoding="utf-8",
    )


def _write_manifest_with_capabilities(ai: Path) -> None:
    """Write a manifest fixture with enough registry data for capability cards."""
    _write_manifest(ai)
    manifest = ai / "manifest.yml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8")
        + "skills:\n"
        + "  total: 2\n"
        + "  registry:\n"
        + "    ai-code:\n"
        + "      type: workflow\n"
        + "      tags: [implementation]\n"
        + "    ai-analyze-permissions:\n"
        + "      type: meta\n"
        + "      tags: [permissions]\n"
        + "agents:\n"
        + "  total: 3\n"
        + "  names: [plan, build, explore]\n",
        encoding="utf-8",
    )


def _source_repo_manifest_text(version: str = "1.2.3") -> str:
    return (
        f'framework_version: "{version}"\n'
        "session:\n"
        "  context_files:\n"
        "    - .ai-engineering/LESSONS.md\n"
        "    - CONSTITUTION.md\n"
        "    - .ai-engineering/manifest.yml\n"
        "    - .ai-engineering/state/decision-store.json\n"
        "control_plane:\n"
        "  constitutional_authority:\n"
        "    primary: CONSTITUTION.md\n"
        "    compatibility_aliases: []\n"
        "  manifest_field_roles:\n"
        "    canonical_input:\n"
        "      - providers\n"
        "      - surfaces\n"
        "      - artifact_feeds\n"
        "      - work_items\n"
        "      - quality\n"
        "      - documentation\n"
        "      - cicd\n"
        "      - contexts.precedence\n"
        "      - session.context_files\n"
        "      - ownership.framework\n"
        "      - ownership.root_entry_points\n"
        "      - telemetry\n"
        "      - gates\n"
        "      - hot_path_slos\n"
        "    generated_projection:\n"
        "      - skills\n"
        "      - agents\n"
        "    descriptive_metadata:\n"
        "      - schema_version\n"
        "      - framework_version\n"
        "      - name\n"
        "      - version\n"
    )


def _write_source_repo_markers(root: Path, ai: Path, *, version: str = "1.2.3") -> None:
    """Add the minimal source-repo files that enable source-only validator checks."""
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "test-project"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    (ai / "manifest.yml").write_text(_source_repo_manifest_text(version), encoding="utf-8")
    template_manifest = (
        root / "src" / "ai_engineering" / "templates" / ".ai-engineering" / "manifest.yml"
    )
    template_manifest.parent.mkdir(parents=True, exist_ok=True)
    template_manifest.write_text(_source_repo_manifest_text(version), encoding="utf-8")


def _write_source_repo_control_plane_files(root: Path, ai: Path) -> None:
    (root / "CONSTITUTION.md").write_text("# Root Constitution\n", encoding="utf-8")
    project_template_constitution = (
        root / "src" / "ai_engineering" / "templates" / "project" / "CONSTITUTION.md"
    )
    project_template_constitution.parent.mkdir(parents=True, exist_ok=True)
    project_template_constitution.write_text("# Template Constitution\n", encoding="utf-8")


def _write_work_plane(
    specs_dir: Path,
    spec_name: str = "006-test",
) -> Path:
    """Write compatibility files and seeded work-plane assets at a specs root."""
    specs_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / "spec.md").write_text(
        f'---\nid: "006"\n---\n\n# {spec_name}\n\nTest spec.\n',
        encoding="utf-8",
    )
    (specs_dir / "plan.md").write_text(
        "---\ntotal: 3\ncompleted: 1\n---\n\n# Plan\n\n- [x] Done\n- [ ] Todo\n- [ ] Todo\n",
        encoding="utf-8",
    )
    (specs_dir / "_history.md").write_text(
        "# Spec History\n\nNo lifecycle entries yet.\n",
        encoding="utf-8",
    )
    # Spec-123: dead HX-02 work-plane artifacts no longer required, but the
    # fixture continues to seed them for tests that exercise legacy paths.
    (specs_dir / "current-summary.md").write_text(
        "# Current Summary\n\nNo active current summary yet.\n",
        encoding="utf-8",
    )
    (specs_dir / "history-summary.md").write_text(
        "# History Summary\n\nNo history summary yet.\n",
        encoding="utf-8",
    )
    (specs_dir / "task-ledger.json").write_text(
        '{\n  "schemaVersion": "1.0",\n  "tasks": []\n}\n',
        encoding="utf-8",
    )
    (specs_dir / "handoffs").mkdir(exist_ok=True)
    (specs_dir / "evidence").mkdir(exist_ok=True)
    return specs_dir


def _write_task_artifacts(
    specs_dir: Path,
    task_id: str,
) -> tuple[HandoffRef, EvidenceRef]:
    """Write handoff and evidence files for a task-ledger test task."""
    handoff_path = specs_dir / "handoffs" / f"{task_id}.md"
    evidence_path = specs_dir / "evidence" / f"{task_id}.log"
    handoff_path.write_text(f"# Handoff {task_id}\n", encoding="utf-8")
    evidence_path.write_text(f"evidence for {task_id}\n", encoding="utf-8")
    return (
        HandoffRef(kind="build", path=f"handoffs/{task_id}.md"),
        EvidenceRef(kind="pytest", path=f"evidence/{task_id}.log"),
    )


def _write_active_spec(ai: Path, spec_name: str = "006-test") -> Path:
    """Write Working Buffer compatibility files and seeded work-plane assets."""
    return _write_work_plane(ai / "specs", spec_name)


def _write_readme(ai: Path) -> None:
    """Write a minimal README.md for the governance tree."""
    readme = ai / "README.md"
    readme.write_text("# ai-engineering\n\nGovernance framework.\n", encoding="utf-8")


def _setup_full_project(root: Path) -> Path:
    """Set up a complete project for happy-path testing."""
    ai = _make_governance(root)
    for s in _SKILL_PATHS:
        _write_skill(ai, s)
    for a in _AGENT_PATHS:
        _write_skill(ai, a)
    _write_all_instruction_files(root)
    _write_manifest(ai)
    _write_source_repo_control_plane_files(root, ai)
    _write_readme(ai)
    _write_active_spec(ai)
    return ai


def _setup_governance_mirror(root: Path) -> None:
    """Create minimal governance template mirror so _check_mirror_sync doesn't early-return."""
    ai = root / ".ai-engineering"
    mirror_root = root / "src" / "ai_engineering" / "templates" / ".ai-engineering"
    # spec-136 D-136-01: governance mirror syncs reference/, manifest, README.
    for subdir in ("reference",):
        src_dir = ai / subdir
        if not src_dir.is_dir():
            continue
        for f in sorted(src_dir.rglob("*.md")):
            rel = f.relative_to(ai)
            dest = mirror_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(f.read_bytes())
    for root_file in ("manifest.yml", "README.md"):
        src = ai / root_file
        if src.is_file():
            dest = mirror_root / root_file
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())


def _frontmatter_with_provenance(
    base_fields: list[tuple[str, str]],
    *,
    family_id: str,
    canonical_source: str,
    body: str,
) -> str:
    """Build a markdown document with generated provenance frontmatter."""
    frontmatter_lines = [f"{key}: {value}" for key, value in base_fields]
    for key, value in get_generated_provenance_fields(family_id, canonical_source).items():
        frontmatter_lines.append(f"{key}: {value}")
    return "---\n" + "\n".join(frontmatter_lines) + f"\n---\n\n{body}"


# Common mirror-test path roots; expressed as tuples to keep call-sites short.
_TEMPLATES_PROJECT = ("src", "ai_engineering", "templates", "project")


def _mirror_pair(
    tmp_path: Path,
    ide_root: str,
    kind: str,
    name: str | None = None,
) -> tuple[Path, Path]:
    """Return (canonical, mirror) paths for an IDE skill/agent under tmp_path.

    ``ide_root`` is ``.github`` / ``.claude`` / ``.codex`` / ``.gemini``; ``kind``
    is ``skills`` / ``agents``; ``name`` (optional) appends a sub-directory.
    """
    canonical = tmp_path / ide_root / kind
    mirror = tmp_path.joinpath(*_TEMPLATES_PROJECT, ide_root, kind)
    if name is not None:
        canonical = canonical / name
        mirror = mirror / name
    return canonical, mirror


def _copilot_agents_pair(tmp_path: Path) -> tuple[Path, Path]:
    """Return (canonical, mirror) for Copilot agents (mirror lives at agents/)."""
    canonical = tmp_path / ".github" / "agents"
    mirror = tmp_path.joinpath(*_TEMPLATES_PROJECT, "agents")
    return canonical, mirror


# Re-exports kept for backward compatibility with callers that imported names
# directly from the previous monolithic conftest (none yet -- introduced in
# spec-140 W2.5).
__all__ = [
    "_AGENT_PATHS",
    "_PROJECT_ROOT",
    "_SKILL_PATHS",
    "_TEMPLATES_CLAUDE_DIR",
    "_copilot_agents_pair",
    "_frontmatter_with_provenance",
    "_make_governance",
    "_make_instruction_content",
    "_mirror_pair",
    "_setup_full_project",
    "_setup_governance_mirror",
    "_source_repo_manifest_text",
    "_write_active_spec",
    "_write_all_instruction_files",
    "_write_manifest",
    "_write_manifest_with_capabilities",
    "_write_readme",
    "_write_skill",
    "_write_source_repo_control_plane_files",
    "_write_source_repo_markers",
    "_write_task_artifacts",
    "_write_work_plane",
    "default_ownership_map",
    "write_json_model",
]
