---
spec: spec-194
slug: deterministic-context-safety-harness
status: draft
executor: build
safe_next_command: "/ai-build"
automation: semi
concern_count: 4
estimated_files: 12
reason: "Foundation harness for all follow-on specs; single-concern read-only collector with adapter pattern"
execution_route:
  version: "1.0"
  executor: build
  automation: semi
---

# Plan — Deterministic Context and Safety Harness (spec-194)

## Phase 1: Schema + Domain Core (TDD)

- [ ] T-1 — Define `ContextSafetyReport` JSON schema and budget config
  - Agent: build
  - Files: `src/ai_engineering/harness/schema.py`, `src/ai_engineering/harness/budgets.yml`
  - Principles applied: §10.6 SDD (schema before code), §10.1 KISS (single normalized report)
  - Patch (deterministic):
    ```python
    # src/ai_engineering/harness/__init__.py
    """Deterministic context and safety harness (spec-194)."""

    # src/ai_engineering/harness/schema.py
    """ContextSafetyReport schema and redaction rules."""
    from __future__ import annotations
    import json
    from dataclasses import dataclass, field, asdict
    from pathlib import Path
    from typing import Any

    @dataclass(frozen=True)
    class RootMetrics:
        bytes: int
        estimated_tokens: int
        mandatory_reads: int
        source_path: str

    @dataclass(frozen=True)
    class CatalogMetrics:
        unique_ids: int
        duplicate_ids: int
        duplicate_ids_list: list[str] = field(default_factory=list)
        total_skills: int = 0

    @dataclass(frozen=True)
    class HookMetrics:
        injection_count: int
        additional_context_tokens: int
        automatic_writes: int
        hook_names: list[str] = field(default_factory=list)

    @dataclass(frozen=True)
    class McpResidue:
        reachable_registrations: int
        plugins: int
        permissions: int
        operational_instructions: int
        names: list[str] = field(default_factory=list)

    @dataclass(frozen=True)
    class OutputBounds:
        normal_cap: int = 8192
        error_cap: int = 2048
        lines_cap: int = 200

    @dataclass(frozen=True)
    class ContextSafetyReport:
        schema_version: str
        host: str
        fixture: str
        root: RootMetrics
        catalog: CatalogMetrics
        hooks: HookMetrics
        mcp_residue: McpResidue
        output_bounds: OutputBounds
        verdict: str  # "pass" | "fail" | "UNVERIFIED"
        redacted: bool = True

        def to_json(self) -> str:
            return json.dumps(asdict(self), indent=2, sort_keys=True)

        @classmethod
        def from_json(cls, data: str | dict) -> "ContextSafetyReport":
            if isinstance(data, str):
                data = json.loads(data)
            return cls(
                schema_version=data["schema_version"],
                host=data["host"],
                fixture=data["fixture"],
                root=RootMetrics(**data["root"]),
                catalog=CatalogMetrics(**data["catalog"]),
                hooks=HookMetrics(**data["hooks"]),
                mcp_residue=McpResidue(**data["mcp_residue"]),
                output_bounds=OutputBounds(**data["output_bounds"]),
                verdict=data["verdict"],
                redacted=data.get("redacted", True),
            )
    ```
  - Gate: `python -c "from ai_engineering.harness.schema import ContextSafetyReport; print('OK')"`

- [ ] T-2 — Write RED tests for schema serialization, redaction and budget enforcement
  - Agent: build
  - Files: `tests/unit/test_harness_schema.py`
  - Principles applied: §10.5 TDD (RED before GREEN)
  - Gate: `pytest tests/unit/test_harness_schema.py -v` (should fail — no implementation yet)

## Phase 2: Domain Collector + Adapters

- [ ] T-3 — Implement read-only collector for roots, instructions, skills, commands
  - Agent: build
  - Files: `src/ai_engineering/harness/collector.py`
  - Principles applied: §10.8 Hexagonal Architecture (adapters own host probes)
  - Patch (deterministic):
    ```python
    # src/ai_engineering/harness/collector.py
    """Read-only context collector."""
    from __future__ import annotations
    from pathlib import Path
    from .schema import (
        ContextSafetyReport, RootMetrics, CatalogMetrics,
        HookMetrics, McpResidue, OutputBounds,
    )

    def collect_root_metrics(root: Path) -> RootMetrics:
        """Measure a single root instruction file."""
        content = root.read_text(encoding="utf-8") if root.exists() else ""
        return RootMetrics(
            bytes=len(content.encode("utf-8")),
            estimated_tokens=len(content.split()) * 4 // 3,  # rough BPE estimate
            mandatory_reads=content.lower().count("read every session"),
            source_path=str(root),
        )

    def collect_catalog_metrics(skills_dir: Path) -> CatalogMetrics:
        """Count unique and duplicate skill IDs from a skills directory."""
        if not skills_dir.exists():
            return CatalogMetrics(unique_ids=0, duplicate_ids=0, total_skills=0)
        ids: list[str] = []
        for p in skills_dir.iterdir():
            if p.is_dir() and (p / "SKILL.md").exists():
                ids.append(p.name)
        unique = set(ids)
        dupes = [i for i in unique if ids.count(i) > 1]
        return CatalogMetrics(
            unique_ids=len(unique),
            duplicate_ids=len(dupes),
            duplicate_ids_list=sorted(dupes),
            total_skills=len(ids),
        )
    ```
  - Gate: `pytest tests/unit/test_harness_schema.py -v` (GREEN)

- [ ] T-4 — Implement host adapters for Claude Code, Codex, OpenCode, Copilot, Cursor, Antigravity
  - Agent: build
  - Files: `src/ai_engineering/harness/adapters/__init__.py`, `src/ai_engineering/harness/adapters/claude.py`, `src/ai_engineering/harness/adapters/codex.py`, `src/ai_engineering/harness/adapters/opencode.py`
  - Principles applied: §10.8 Hexagonal Architecture (one adapter per host), §10.4 DRY (shared interface)
  - Gate: `pytest tests/unit/test_harness_adapters.py -v`

- [ ] T-5 — Implement hook injection collector and MCP residue scanner
  - Agent: build
  - Files: `src/ai_engineering/harness/hook_collector.py`, `src/ai_engineering/harness/mcp_scanner.py`
  - Principles applied: §10.1 KISS (structure-only parsing, no secret reading)
  - Gate: `pytest tests/unit/test_harness_hooks.py -v`

## Phase 3: Fixtures + Redaction + CLI

- [ ] T-6 — Create clean fixtures for each enabled host
  - Agent: build
  - Files: `tests/fixtures/harness/claude/`, `tests/fixtures/harness/codex/`, `tests/fixtures/harness/opencode/`
  - Principles applied: §10.5 TDD (fixtures pin classifiers)
  - Gate: `pytest tests/unit/test_harness_fixtures.py -v`

- [ ] T-7 — Implement redaction engine and output capping
  - Agent: build
  - Files: `src/ai_engineering/harness/redactor.py`
  - Principles applied: §10.1 KISS (one redaction pass), §10.5 TDD (test secret-shaped fixtures)
  - Gate: `pytest tests/unit/test_harness_redaction.py -v`

- [ ] T-8 — Implement CLI commands: `baseline`, `verify`, `compare`
  - Agent: build
  - Files: `src/ai_engineering/cli_commands/harness.py`
  - Principles applied: §10.6 SDD (commands are thin adapters)
  - Gate: `ai-eng harness baseline --help` succeeds

## Phase 4: Integration + Regression

- [ ] T-9 — Write integration tests: determinism, compare diffs, budget regressions
  - Agent: build
  - Files: `tests/integration/test_harness_integration.py`
  - Principles applied: §10.5 TDD (byte-identical JSON proof)
  - Gate: `pytest tests/integration/test_harness_integration.py -v`

- [ ] T-10 — Verify existing parity and skill-budget tests still pass
  - Agent: verify
  - Files: `tests/architecture/test_surface_parity.py`, `tests/perf/test_skill_lint_budget.py`
  - Principles applied: §10.5 TDD (regression gate)
  - Gate: `pytest tests/architecture/test_surface_parity.py tests/perf/test_skill_lint_budget.py -v`

- [ ] T-11 — Register harness CLI command in cli_factory.py
  - Agent: build
  - Files: `src/ai_engineering/cli_factory.py`
  - Principles applied: §10.4 DRY (reuse existing CLI registration pattern)
  - Gate: `ai-eng harness --help` succeeds

- [ ] T-12 — Documentation and CHANGELOG entry
  - Agent: build
  - Files: `docs/harness.md`, `CHANGELOG.md`
  - Principles applied: §10.7 Clean Code (self-documenting)
  - Gate: `docs/harness.md` exists and is valid markdown
