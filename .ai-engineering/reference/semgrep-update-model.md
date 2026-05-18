# Semgrep update model (spec-124 D-124-13; rewritten by spec-141 M4)

`ai-engineering` ships a **two-tier scan model** with manual quarterly
bumps of the Semgrep CLI version that backs the security gate. There
is no auto-update path: rule freshness is a deliberate, reviewed
action, not a background daemon's responsibility.

## How the gate is wired

The repository's `.semgrep.yml` carries only **in-tree rules** under
the `aieng.<area>.` namespace (spec-141 M1 rename) plus standard
Semgrep `rules:` block syntax. There is no top-level `extends` key —
that key is not part of the documented Semgrep YAML schema (see
https://semgrep.dev/docs/running-rules). Multi-pack coverage is wired
via repeated `--config` flags at invocation time.

### Tier 1 — Pre-push (hot path)

`ai-eng gate pre-push` runs only the in-tree rules with an
incremental scope:

```bash
semgrep --config .semgrep.yml \
        --baseline-commit "$(git merge-base HEAD origin/<default-branch>)" \
        --error .
```

The `--baseline-commit` flag scopes the scan to files changed since
the merge base, keeping the run under the 5-second pre-push budget
declared in `CLAUDE.md` "Hot-Path Discipline". The pre-push tier is
network-free and deterministic.

Pre-commit deliberately does **not** run Semgrep — the full-pack
invocation budget exceeds 30 seconds, well over the sub-1s pre-commit
SLO. Full-pack coverage lives in CI.

### Tier 2 — CI (full coverage backstop)

`.github/workflows/ci-check.yml` runs the four community packs plus
the in-tree rules via repeated `--config` flags — the canonical
Semgrep multi-pack invocation per
https://semgrep.dev/docs/running-rules:

```yaml
- name: semgrep
  run: |
    semgrep \
      --config .semgrep.yml \
      --config p/python \
      --config p/owasp-top-ten \
      --config p/security-audit \
      --config p/bash \
      --error --json . > semgrep-results.json
```

The Semgrep CLI version is pinned in the workflow's install step:

```yaml
- name: install semgrep
  run: pip install "semgrep==<pinned-version>"
```

The CLI pin is the **only** deterministic anchor: pack aliases like
`p/python` resolve to the live HEAD of `semgrep/semgrep-rules` at scan
time, and that registry indirection cannot be version-pinned via
Semgrep syntax (see https://semgrep.dev/docs/cli-reference). The
GitHub Actions cache keyed by Semgrep CLI version softens transient
registry failures.

## What semgrep is, and is not

Semgrep is a **pattern-matching engine** with a community-curated rule
set. It is **not** a CVE database. The distinction matters:

| Question | Answer |
|---|---|
| Does Semgrep find a new CVE the moment it is published? | No. |
| When does Semgrep find a new CVE? | When the pack maintainer ships a rule for it, AND the CI CLI pin is bumped, AND the gate is re-run. |
| Does the CLI version pin protect against rule drift? | Partially. The CLI is pinned; pack aliases still roll forward from HEAD. Full determinism requires vendoring the pack YAML, which `ai-engineering` does not currently do. |
| Does pinning protect against missed CVEs? | No — pinning trades determinism for freshness. The quarterly bump is what closes the gap. |

If you need timely CVE coverage for your dependency tree, that is the
job of `pip-audit` (Python) and the equivalent tools wired into the
pre-push gate per stack. Semgrep covers code-level patterns:
hardcoded secrets, insecure subprocess calls, weak crypto, prompt
injection in LLM client code, and similar signals.

## Quarterly bump procedure

Every quarter (or sooner, if a high-impact CVE drives an out-of-band
bump):

1. Open <https://semgrep.dev/docs/release-notes> and identify the
   latest stable Semgrep CLI release.
2. Update the `semgrep==<version>` pin in the CI workflow install
   step (`.github/workflows/ci-check.yml`).
3. Run the CI workflow on a throwaway PR to surface any new findings
   the bump introduces. Two outcomes are valid:
   - Fix the finding (preferred) and re-run.
   - Open a risk acceptance via `ai-eng risk accept --finding <hash>`
     if remediation cannot land before the publish window closes
     (see `risk-acceptance-flow.md`).
4. Commit the version bump as a single conventional commit:
   `chore(security): bump semgrep CLI to <version>`. The body should
   record the release-notes highlights so future readers understand
   which signals the bump unlocked.
5. Merge after CI re-runs the gate as the final authority.

## When NOT to bump out of band

Resist the urge to bump the CLI to silence a noisy CI run:

- A CLI update that introduces hundreds of false positives in a
  legacy module is a signal to schedule a sweep refactor, not to
  pin back to the prior CLI version.
- A CLI update that rewrites an existing rule's severity is logged
  in the release notes — read them before assuming the new finding
  is a false positive.
- Rule deletions are rare but happen; if a previously-firing rule
  disappears after a bump, confirm intentionality from the release
  notes rather than relying on the rule's continued existence.

## `# nosemgrep:` markers (spec-141 M3 Article VII parity)

`# nosemgrep:` markers in code are first-class citizens of the
suppression-allowlist pipeline alongside `# noqa` and `# nosec`. The
scanner emits a `nosemgrep_hash` finding; allowlist entries declare
`pattern: nosemgrep_hash` with the standard fields (`path`, `rule`,
`justification`, `spec_ref`, `expires_at`, `dec_id`). Unauthorised
markers fail the gate per CONSTITUTION.md Article VII.

## Operator visibility

`ai-eng doctor` surfaces a `secrets_gate` runtime probe that verifies
`semgrep` is on PATH and `.semgrep.yml` is present. The probe does
**not** verify CLI freshness — there is no machine-checkable signal
for "your quarterly bump is overdue". That cadence is enforced by the
quarterly review on the maintainer's calendar, not by the framework.

## See also

- [`risk-acceptance-flow.md`](risk-acceptance-flow.md) — how to
  document a finding the team chose to defer.
- [`gate-policy.md`](gate-policy.md) — which gates run when, and
  what their SLOs are.
- [`CONSTITUTION.md`](../../CONSTITUTION.md) Article XII — the
  governance contract for the secrets-gate pipeline.
- Semgrep canonical multi-pack syntax:
  <https://semgrep.dev/docs/running-rules>
- Semgrep CLI reference:
  <https://semgrep.dev/docs/cli-reference>
