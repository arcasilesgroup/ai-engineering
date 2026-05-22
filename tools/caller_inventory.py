#!/usr/bin/env python3
"""Generate the spec-146 caller-inventory artifact.

The output is deterministic: no timestamps, no host paths. It scans the
project tree for named simplification candidates and emits a reviewable
Markdown table with the implementation decision for each candidate.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = (
    "src",
    "tests",
    "tools",
    ".ai-engineering/scripts/hooks",
    "docs",
    ".claude",
    ".codex",
    ".agents",
    ".github",
)
EXCLUDED_PARTS = {".git", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache"}


@dataclass(frozen=True)
class Candidate:
    name: str
    target: str
    tokens: tuple[str, ...]
    classification: str
    decision: str
    rationale: str


CANDIDATES: tuple[Candidate, ...] = (
    Candidate(
        "agentsview.py",
        "src/ai_engineering/state/agentsview.py",
        ("agentsview", "write_agentsview_fixture_bundle", "build_agentsview_contract"),
        "test-only/deleted",
        "Hard-delete",
        (
            "Only preservation tests and fail-open hook comments referenced it; "
            "capability data remains in state.db/tool_capabilities."
        ),
    ),
    Candidate(
        "outbox.py",
        "src/ai_engineering/state/outbox.py",
        ("state.outbox", "OutboxRecorder", "OutboxReentrantError"),
        "test-only/deleted",
        "Hard-delete",
        (
            "No production writer used the in-process outbox; canonical audit emission "
            "remains direct and fail-loud."
        ),
    ),
    Candidate(
        "governance/policy_engine.py",
        "src/ai_engineering/governance/policy_engine.py",
        ("governance.policy_engine", "PolicyError"),
        "test-only/deleted",
        "Hard-delete",
        "OPA runner is the production policy path; this file was a downstream-fork insurance shim.",
    ),
    Candidate(
        "cli_ui_skill_ref.py",
        "src/ai_engineering/cli_ui_skill_ref.py",
        ("cli_ui_skill_ref", "skill_ref_tight", "skill_ref("),
        "test-only/deleted",
        "Hard-delete",
        "No production CLI imported the helper; active docs now state the wording rule directly.",
    ),
    Candidate(
        "trace_context.py",
        "src/ai_engineering/state/trace_context.py",
        ("state.trace_context", "current_trace_context", "write_trace_context"),
        "production/hook-parity",
        "Preserve",
        (
            "Observability and hook parity tests use trace/span context; replacement "
            "would need separate migration tests."
        ),
    ),
    Candidate(
        "capabilities.py",
        "src/ai_engineering/state/capabilities.py",
        ("state.capabilities", "build_capability_cards"),
        "production/validator",
        "Preserve",
        "Framework capability generation feeds observability and manifest-coherence validation.",
    ),
    Candidate(
        "context_packs.py",
        "src/ai_engineering/state/context_packs.py",
        ("state.context_packs", "context_packs_dir"),
        "production/validator",
        "Preserve",
        "Manifest-coherence validation uses context pack helpers.",
    ),
    Candidate(
        "relevance.py",
        "src/ai_engineering/state/relevance.py",
        ("state.relevance", "relevance_gate", "AuditPolicy"),
        "production/hook-asset",
        "Preserve",
        "Hook asset runtime packages the relevance gate counterpart for installed hooks.",
    ),
    Candidate(
        "StateService",
        "src/ai_engineering/state/service.py",
        ("StateService", "from ai_engineering.state.service import StateService"),
        "production/facade",
        "Partially flatten",
        (
            "Policy orchestrator no longer needs the forwarding facade; other "
            "CLI/install callsites retain it pending smaller migrations."
        ),
    ),
    Candidate(
        "DurableStateRepository",
        "src/ai_engineering/state/repository.py",
        ("DurableStateRepository", "state.repository"),
        "production/adapter",
        "Preserve",
        "Repository owns model reconstruction from state.db and remains a useful adapter boundary.",
    ),
    Candidate(
        "installer/mechanisms/__init__.py",
        "src/ai_engineering/installer/mechanisms/__init__.py",
        ("installer.mechanisms", "NpmDevMechanism", "GoInstallMechanism"),
        "production/registry",
        "Split with thin re-export",
        (
            "Simple mechanism classes moved to focused modules while package root "
            "preserves the internal import contract."
        ),
    ),
)


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        base = ROOT / root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if EXCLUDED_PARTS & set(path.parts):
                continue
            if path == Path(__file__).resolve():
                continue
            if path.suffix not in {".py", ".md", ".sh", ".yml", ".yaml", ".json", ".toml"}:
                continue
            files.append(path)
    return sorted(files)


def _hits(candidate: Candidate, files: list[Path]) -> list[str]:
    hits: set[str] = set()
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if rel == candidate.target:
            hits.add(rel)
            continue
        if any(token in text for token in candidate.tokens):
            hits.add(rel)
    return sorted(hits)


def render() -> str:
    files = _iter_files()
    lines = [
        "# Spec 146 Caller Inventory",
        "",
        (
            "Command: `rtk .venv/bin/python tools/caller_inventory.py > "
            ".ai-engineering/specs/spec-146-caller-inventory.md`"
        ),
        "",
        (
            "Scope scanned: `src/`, `tests/`, `tools/`, hook scripts, docs, "
            "specs, and active IDE surfaces."
        ),
        "",
        "| Candidate | Classification | Decision | Evidence | Rationale |",
        "|---|---|---|---|---|",
    ]
    for candidate in CANDIDATES:
        hits = _hits(candidate, files)
        evidence = "; ".join(f"`{hit}`" for hit in hits[:8])
        if len(hits) > 8:
            evidence += f"; +{len(hits) - 8} more"
        if not evidence:
            evidence = "No active hits after cleanup"
        lines.append(
            "| "
            f"`{candidate.name}` | {candidate.classification} | {candidate.decision} | "
            f"{evidence} | {candidate.rationale} |"
        )
    lines.extend(
        [
            "",
            "## Summary",
            "",
            "- Deleted candidates are limited to no-production-caller surfaces.",
            (
                "- Production state modules remain because observability, validators, "
                "hooks, or adapters still use them."
            ),
            (
                "- Installer mechanisms are split internally but keep a thin package-root "
                "re-export for current registry imports."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(render(), end="")
