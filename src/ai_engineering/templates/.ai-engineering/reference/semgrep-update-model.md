# Semgrep update model (spec-124 D-124-13)

`ai-engineering` ships a **manual quarterly bump** model for the
semgrep community packs that back the pre-push security gate. There is
no auto-update path: rule freshness is a deliberate, reviewed action,
not a background daemon's responsibility.

## How the gate is wired

`.semgrep.yml` extends version-pinned community packs:

```yaml
extends:
  - p/python@1.96.0
  - p/bash@1.96.0
  - p/owasp-top-ten@1.96.0
  - p/security-audit@1.96.0
```

Plus the repository's own `rules:` block (project-specific patterns
maintained in-tree). Each invocation fetches the pinned packs from the
semgrep.dev registry; there is **no offline cache** -- a transient
network failure on the registry side surfaces as a noisy gate run, not
a silent regression.

The semgrep gate fires in two places:

1. **Pre-push** -- `ai-eng gate pre-push` runs
   `semgrep --config .semgrep.yml --error .` against the working tree
   before the push reaches the remote. Pre-commit deliberately does
   **not** run semgrep because the warm-cache invocation budget
   exceeds 30 seconds, well over the sub-1s pre-commit SLO.
2. **CI** -- the same command re-runs in CI as a backstop, so a
   developer who skipped local hooks (`--no-verify`, forbidden by
   Article VIII but technically possible) cannot land an unscanned
   change.

## What semgrep is, and is not

Semgrep is a **pattern-matching engine** with a community-curated rule
set. It is **not** a CVE database. The distinction matters:

| Question | Answer |
|---|---|
| Does semgrep find a new CVE the moment it is published? | No. |
| When does semgrep find a new CVE? | When the pack maintainer ships a rule for it, AND you bump your pin, AND you re-run the gate. |
| Does pinning a pack version protect against rule drift? | Yes -- the gate is reproducible across runs and across hosts. |
| Does pinning protect against missed CVEs? | No -- the trade-off is determinism vs freshness. The quarterly bump is what closes the gap. |

If you need timely CVE coverage for your dependency tree, that is the
job of `pip-audit` (Python) and the equivalent tools wired into the
pre-push gate per stack. Semgrep covers code-level patterns:
hardcoded secrets, insecure subprocess calls, weak crypto, prompt
injection in LLM client code, and similar signals.

## Quarterly bump procedure

Every quarter (or sooner, if a high-impact CVE drives an out-of-band
bump):

1. Open <https://semgrep.dev/changelog> and identify the latest
   version of each pack listed in `.semgrep.yml`.
2. Bump the `@<version>` suffix in `extends:` for every pack.
3. Run `semgrep --config .semgrep.yml --error .` locally and triage
   any new findings. Two outcomes are valid:
   - Fix the finding (preferred) and re-run.
   - Open a risk acceptance via
     `ai-eng risk accept --finding <hash>` if remediation cannot land
     before the publish window closes (see
     `risk-acceptance-flow.md`).
4. Commit the version bump as a single conventional commit:
   `chore(security): bump semgrep packs to <quarter>`. The body
   should record the pack changelog highlights so future readers
   understand which signals the bump unlocked.
5. Push and let CI re-run the gate as the final authority.

## When NOT to bump out of band

Resist the urge to bump packs to silence a noisy local gate run:

- A pack update that introduces hundreds of false positives in a
  legacy module is a signal to schedule a sweep refactor, not to
  pin-back the pack.
- A pack update that rewrites an existing rule's severity is logged
  in the changelog -- read it before assuming the new finding is a
  false positive.
- Rule deletions are rare but happen; if a previously-firing rule
  disappears after a bump, confirm intentionality from the changelog
  rather than relying on the rule's continued existence.

## Operator visibility

`ai-eng doctor` surfaces a `secrets_gate` runtime probe that verifies
`semgrep` is on PATH and `.semgrep.yml` is present. The probe does
**not** verify pack freshness -- there is no machine-checkable signal
for "your quarterly bump is overdue". That cadence is enforced by the
quarterly review on the maintainer's calendar, not by the framework.

## See also

- [`risk-acceptance-flow.md`](risk-acceptance-flow.md) -- how to
  document a finding the team chose to defer.
- [`gate-policy.md`](gate-policy.md) -- which gates run when, and
  what their SLOs are.
- [`CONSTITUTION.md`](../../CONSTITUTION.md) Article XII -- the
  governance contract for the secrets-gate pipeline.
