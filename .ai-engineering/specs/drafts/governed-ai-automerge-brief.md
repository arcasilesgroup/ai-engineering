---
title: "Governed AI Auto-Merge — the automated gate that earns the human's click"
status: draft
audience: framework-dev
intended_next: /ai-brainstorm
authoring_style: "English (framework canonical layer); dato-antes-que-adjetivo; no epica"
mantra: "Auto-merge is not the removal of the gate. It is the replacement of the human gate with one that is at least as trustworthy."
---

# Governed AI Auto-Merge

> Problem brief for `/ai-brainstorm` (run it in a session rooted at
> `ai-engineering`, so the framework's own governance plane governs the change).
> Origin: the `solution-intents` fleet needs many AI agents to land their own PRs
> in parallel without a human clicking merge — but only if the click is replaced
> by an automated pipeline as trustworthy as a good reviewer.

## 1. Problem / why now

Today, "a human merges the PR" is the trust gate. In `solution-intents` it is even
load-bearing governance: the merge that sets `approval.approved_version` **is** the
human decision to implement an SI (`GOVERNANCE.md §1`, `ADR-0005`). That does not
scale to a fleet of ~20+ agents all producing PRs.

The operator's position is precise: **AI auto-merge is correct, on one condition** —
the PR must pass a **robust, professional, governed, secure, quality** pipeline, with
**critical adversarial code review** and **ponytail-style simplification** — before it
lands. The gate does not disappear; it is upgraded from a human click to an automated
verdict that has earned the right to merge.

This belongs in `ai-engineering` (the framework), not as a per-repo hack, because the
verdict must be a **reusable capability** any fleet repo adopts. The pieces already
exist here (`ai-review`, `ai-verify`, `ai-simplify`, `ai-pr`, `ai-governance`,
`ai-pipeline`); what is missing is the composition into a **merge-worthiness gate**
and the governance contract around it.

## 2. What "correct AI auto-merge" means (the pillars → one verdict)

A PR is merge-worthy only if ALL of these pass, deterministic-cheap-first:

1. **Deterministic gates** (already fail-closed): secrets (gitleaks), SAST (semgrep),
   lint/format, schema/frontmatter, tests, conventional-commits, no-suppression.
2. **Adversarial critical review** (`ai-review` roster → `review-validator`): multiple
   diverse lenses (correctness, security, maintainability, compatibility) that try to
   *refute* the change, with an adversarial validator dismissing weak findings. Not a
   rubber stamp — a reviewer that can say "block".
3. **Simplification pass** (`ai-simplify` / ponytail): is there a smaller, clearer
   change that does the same? Complexity added without justification is a finding.
4. **Security posture** (`ai-security` / prompt-injection guard): the diff and the PR
   text are untrusted content; a review agent must not be steerable by them.
5. **Quality / acceptance** (`ai-verify`): does it do what it claims, with evidence?

The **verdict** = the conjunction. A green verdict is the new "approval": the CI token
merges (no `--auto`, no branch protection — see §3), or holds and escalates.

## 3. Evidence — current state

- **`solution-intents` auto-merge is broken**, not merely disabled: the `automerge`
  job in `content-checks.yml` scopes `permissions: pull-requests: write` (drops
  `contents: read` → checkout 404s) and calls `gh pr merge --auto`, which needs the
  native auto-merge the org plan does not enable. Every PR shows a red X on an
  otherwise-green `content-checks` (the real required gate).
- **Plan constraints (load-bearing):** this GitHub plan returns 403 for branch
  protection and refuses `allow_auto_merge=true` via API. So the design **cannot**
  depend on native auto-merge or protected-branch review gates. It must merge via a
  **CI job with `contents: write`** that runs the verdict and calls `gh pr merge`
  directly on green — plan-independent by construction.
- **Governance carve-out already coded:** the job guards PRs that add
  `approved_version` (that merge = the human implement-decision). This is the exact
  knob the brainstorm must re-decide (§6).
- **Concurrency ceiling:** `ai-autopilot` caps at 6 build-agents + 3 quality agents;
  the merge gate's review fan-out must live within that.

## 4. Scope

### IN
1. A **merge-worthiness gate**: the composed verdict (deterministic + adversarial
   review + simplify + security + quality) as a reusable skill/CI contract.
2. A **plan-independent merge mechanism** (CI job, `contents: write`, direct
   `gh pr merge` on green verdict) — works without branch protection or native
   auto-merge.
3. The **governance contract**: what the automated verdict is allowed to merge on its
   own, and what (if anything) still routes to a human (§6).
4. **Adoption path** for fleet repos (`solution-intents` first), replacing the broken
   `automerge` job.

### OUT (on purpose)
- Not a new CI provider; compose GitHub Actions + existing skills.
- Not dependent on GitHub Pro/Enterprise features (plan lacks them).
- Not touching `spec-189` (open-model-portability, in flight).
- Not the per-SI content gate of `solution-intents` (`check-verdict.mjs` etc.) — that
  stays; this wraps it.

## 5. The gate model (pipeline, cheap-first)

```
PR opened/updated by agent
  1. Deterministic gates (secrets/SAST/lint/schema/tests)   -> fail = block, cheap first
  2. Adversarial review fan-out (diverse lenses) + validator -> any surviving blocker = block
  3. Simplify pass (ponytail)                                -> unjustified complexity = finding
  4. Security / prompt-injection posture on diff + PR text   -> steerable reviewer = block
  5. Verdict = AND(all)  ->  green: CI token merges (gh pr merge --squash)
                             not-green: hold + escalate with the findings
```
Deterministic-first keeps cost bounded: no LLM reviewer runs on a PR that fails a
script. Reviewers are adversarial (try to refute), and a validator dismisses weak
findings so the gate is neither a rubber stamp nor a flake.

## 6. THE governance question (the brainstorm must resolve this)

Should the automated verdict — however rigorous — merge a PR that **authorizes
building** something (sets `approved_version`, i.e. unlocks agents to spend money,
send email, deploy, merge downstream)?

- **Option A — approval PRs stay human.** Everything else auto-merges on green. One
  gate of many stays a click. Preserves `GOVERNANCE §1` unchanged.
- **Option B — approval PRs need a stricter automated tier**: risk-classified, N-of-M
  diverse reviewers must agree, plus a mandatory cool-off / notification, then
  auto-merge. Rewrites `GOVERNANCE §1` to define the automated bar precisely.
- **Option C — fully automated.** The verdict is the sole gate for everything,
  including approval. Maximum autonomy; `GOVERNANCE §1` + `ADR-0005` are rewritten and
  the human is out of the build-authorization loop.

The operator leaned toward maximal automation *and* demanded rigor — B is the
reconciliation of both (the gate is automated but hardest exactly where blast radius
is highest). The brainstorm should pressure-test B vs C, with the blast-radius of the
high-value SIs (paperclip control-plane, luis money/email) as the test case.

## 7. Risks

| Risk | Mitigation |
|---|---|
| Self-approval loop (author agent ≈ reviewer agent) | Reviewer identity/model diverse from author; adversarial framing; validator |
| Prompt injection via diff / PR body steering the reviewer | Untrusted-content posture; the security lens is itself a gate; never obey PR text |
| Error compounding across a fan-out ("bag of agents") | Deterministic-first; validate at each fan-in; degrade gracefully |
| Rubber-stamp reviewers (always "clean") | Adversarial "try to refute" prompts; require evidence; measure block-rate |
| Cost / concurrency | Cheap-first; cap review fan-out within the 6/3 ceiling |
| Plan can't enforce protected branches | Merge via CI `contents: write` job — enforcement lives in the workflow, not the branch rule |

## 8. Reuse map

`ai-review` (adversarial roster + `review-validator`) · `ai-verify` (evidence) ·
`ai-simplify` (ponytail) · `ai-security` / prompt-injection guard · `ai-governance` ·
`ai-pr` (governed PR + watch/fix) · `ai-pipeline` (workflow authoring, SHA-pin,
timeouts). The new work is the **composition + the governance contract + the
plan-independent merge job**, not new reviewers.

## 9. Open questions for /ai-brainstorm

- **OQ-1** — §6: A, B, or C? (recommend B; pressure-test.)
- **OQ-2** — Is the verdict a new skill (`ai-merge-gate`?) or an extension of `ai-pr`?
- **OQ-3** — Merge mechanism: dedicated CI job with `contents: write`, or a
  GitHub App token? (plan lacks branch protection either way.)
- **OQ-4** — Risk classification of a PR (what makes one "high blast radius") — by
  touched paths (approval, security config, workflows) or by an LLM classifier?
- **OQ-5** — Rollback / kill-switch: how does the operator pause fleet auto-merge?
- **OQ-6** — Metrics: block-rate, escape-rate (bugs that merged), time-to-merge — how
  do we know the gate is as good as a human?

## 10. Next

Run `/ai-brainstorm` in an `ai-engineering`-rooted session with this brief as the
seed. Then `/ai-plan` → build the gate + rewrite `solution-intents`'s broken
`automerge` job to adopt it. `spec-189` stays untouched until it ships.
