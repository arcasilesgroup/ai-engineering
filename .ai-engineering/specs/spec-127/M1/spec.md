---
id: sub-002
parent: spec-127
milestone: M1
title: "Conformance rubric as code"
status: planning
files:
  - tools/skill_domain/__init__.py
  - tools/skill_domain/rubric.py
  - tools/skill_app/__init__.py
  - tools/skill_infra/__init__.py
  - tools/skill_lint/cli.py
  - tests/conformance/test_skills_rubric.py
  - tests/conformance/test_agents_rubric.py
  - docs/conformance-report.md
  - .pre-commit-config.yaml
depends_on: []
---

# Sub-Spec 002: M1 — Conformance rubric as code

## Scope

Scaffold the hexagonal Python packages (`tools/skill_domain/`,
`tools/skill_app/`, `tools/skill_infra/`) using PEP 8 underscore naming per
D-127-13. Implement the conformance rubric (`tools/skill_domain/rubric.py`) as
pure-Python validator dataclasses covering brief §3 ten rules: frontmatter
validation, third-person CSO description, ≥3 trigger phrases, negative scoping,
≤500 line hard / ≤120 line internal target, ≤5000 tokens, required sections,
≥2 examples, refs nesting, ≥3 evals, no anti-patterns. Add the parallel agent
rubric (frontmatter CSO, tools whitelist, model declared, dispatch ref, no
orphan). Ship `tools/skill_lint/cli.py` with `--check` and `--baseline` modes;
wire `--check` into pre-commit at ≤200 ms parallel walk. Generate
`docs/conformance-report.md` baseline section over current 50 skills.

## Exploration

### Current-state findings

- **Skills surface**: `.claude/skills/` contains 51 dirs — 50 active skills
  (each ships `SKILL.md`); 1 is `_shared/` (hosts `execution-kernel.md`,
  intentionally not a skill).
- **Agents surface**: `.claude/agents/*.md` contains 26 markdown files. Roster:
  10 `reviewer-*`, 3 `verifier-*`, 2 `verify-*`, 2 `review-*` (prefix mismatch
  flagged in brief §2.2), 9 `ai-*` orchestrators/dispatchers.
- **Tooling layout**: No `tools/` directory at repo root. Hexagonal package
  locations greenfield. PEP 8 underscore per D-127-13.
- **Tests layout**: `tests/` has `unit/`, `integration/`, `e2e/`, `perf/`,
  `fixtures/`. No `tests/conformance/` or `tests/architecture/`. Both
  greenfield.
- **Pre-commit machinery**: NO `.pre-commit-config.yaml`. Repo uses custom hook
  `.git/hooks/pre-commit` whose body is `ai-eng gate pre-commit`. Wiring
  `skill_lint --check` happens through that registry, not a YAML hook.
- **Anthropic skill-creator standard**: At `~/.agents/skills/skill-creator/`.
  Source-of-truth for §3 ten-rule conformance bar.
- **Hot-path budget**: brief §14.3 sets pre-commit ≤1.0 s. D-127-08 reserves
  ≤200 ms for `skill_lint --check` parallel walk over 50 skills (~4 ms/skill).
  Achievable with stdlib `ThreadPoolExecutor` + cached frontmatter parsing.
- **Baseline grades** (brief §2.1): 28 A, 14 B, 6 C, 1 D (`ai-entropy-gc`);
  0/50 skills carry `## Examples`; 5 SKILL.md > 150 lines.
- **Naming**: console script `skill_lint = skill_lint.cli:main` in
  `pyproject.toml [project.scripts]`.

### Architecture (hexagonal, scaffolded here)

```
tools/
├── skill_domain/         # ZERO external deps; pure Python
│   ├── __init__.py
│   ├── rubric.py         # @dataclass Rule, RubricResult, Grade
│   ├── skill_model.py    # Skill, Frontmatter dataclasses
│   └── agent_model.py    # Agent dataclass
├── skill_app/            # Use cases; domain only
│   ├── __init__.py
│   ├── lint_skills.py    # LintSkillsUseCase(scanner_port, reporter_port)
│   ├── lint_agents.py    # LintAgentsUseCase
│   └── ports.py          # ScannerPort, ReporterPort (Protocol)
├── skill_infra/          # Adapters; depends on app + domain
│   ├── __init__.py
│   ├── fs_scanner.py     # FilesystemScanner(ScannerPort) — parallel walk
│   └── markdown_reporter.py # MarkdownReporter(ReporterPort)
└── skill_lint/           # CLI shim; entry point only
    ├── __init__.py
    └── cli.py            # argparse → wires app + infra
```

**Layer rules** (M5 enforces; prefigured here by careful imports):

1. `tools/skill_domain/**` MUST NOT import `skill_app`/`skill_infra`/
   `skill_lint`/non-stdlib package.
2. `tools/skill_app/**` MUST NOT import `skill_infra` or `skill_lint`.
3. `tools/skill_lint/cli.py` is the only place wiring concretes into the use
   case.
