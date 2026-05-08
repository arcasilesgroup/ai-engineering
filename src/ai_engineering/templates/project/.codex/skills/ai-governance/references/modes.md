# Governance Modes

## compliance — Quality Gate Validation

Validate that rules in `CLAUDE.md`, `manifest.yml`, and boundaries in `CONSTITUTION.md` are enforced.

1. **Hook enforcement** — verify required hooks exist in `.git/hooks/`, are executable, contain no `--no-verify` escapes.
2. **Check coverage** — for each stack in `enforcement.checks`, confirm tool is configured and callable.
3. **Non-negotiables** — walk `standards.non_negotiables`, trace enforcement chain: manifest → hook → CLAUDE.md.
4. **CI workflows** — verify `enforcement.ci.required_workflows` exist under `.github/workflows/`.
5. **Security contract** — gitleaks in pre-commit, semgrep in pre-push, dependency audit per stack.

## ownership — Boundary Validation

Verify files live in correct ownership zones.

1. **Zone mapping** — load `ownership.model` from manifest. Build zones: framework-managed, team-managed, project-managed, system-managed.
2. **File placement** — scan `.ai-engineering/`, verify each file maps to exactly one zone.
3. **Modification history** — `git log` framework-managed files, confirm only framework commits touched them.
4. **Update rule compliance** — team/project paths never overwritten by automation.

## risk — Risk Acceptance Lifecycle

Sub-modes: `accept`, `resolve`, `renew`.

**Accept**: record time-limited risk in `state.db` `decisions` table (spec-124 D-124-12).

- Classify finding, determine severity, register with mandatory `follow_up_action`.
- Auto-expiry: Critical 15d, High 30d, Medium 60d, Low 90d.

**Resolve**: close after remediation. Validate fix committed, scan clean, no regression. Mark `remediated` (preserved for audit trail).

**Renew**: extend before expiry (max 2 renewals). Check eligibility (`renewal_count < 2`). Require justification. Create new decision with `renewed_from` reference.

## integrity — Framework Consistency

Validate manifest claims match disk reality.

1. **Manifest counters** — compare `governance_surface.agents.total` and `skills.total` against actual file counts.
2. **Agent-skill references** — verify every path in agent `references.skills` resolves to an existing SKILL.md.
3. **State file schemas** — confirm `state/` files are valid JSON/NDJSON with required keys.
4. **Command file existence** — verify each SKILL.md has valid YAML frontmatter.
