---
name: second-opinion
description: Get an independent review of code you just wrote by spawning a fresh reviewer instance — a separate one-shot agent session with read-only tools that cannot see your reasoning. Use this immediately after finishing ANY implementation — a feature, a bugfix, a refactor, a migration, a schema change — before you tell the user the work is done. Also use whenever the user says "review this", "double-check that", "get a second opinion", "have another agent look at it", or asks whether an implementation is actually correct. Especially worth it when the change touches money, auth, permissions, migrations, or data deletion, or when you noticed yourself feeling uncertain while writing it.
---

# Second opinion

Spawn an independent reviewer — a fresh model instance that cannot see your reasoning — to review the implementation you just finished, triage what it finds, and fix the real bugs.

## Why this catches things you cannot catch yourself

When you re-read code you just wrote, you check it against your intent. You remember what each line was *for*, so you read the intent into the code and skip right over the place where the code says something slightly different. That is not carelessness — it is unavoidable. You cannot un-know your own plan.

A fresh reviewer has no plan to un-know. It sees only the task and the code, so a gap between them shows up as a gap. That is the entire mechanism, and it is also why the one thing that ruins this technique is leaking your reasoning into the review packet.

## The rule that makes or breaks it

**Give the reviewer the spec and the code. Never give it your justifications.**

Concretely, keep all of these out of the packet:

- "I handled the empty case by …" — if the handling is real, the reviewer will see it in the code; if you have to point at it, that is exactly the claim worth testing
- "I already tested this" / "this works" — this reads as permission to skim
- "The tricky part was X, but I resolved it by Y" — this hands over your conclusion and the reviewer will adopt it
- Your commit message, if it explains rationale rather than what changed

Describe files neutrally: *what the file is*, never *why your version is right*. A packet line reads `src/cart.ts — new; discount + total calculation`, not `src/cart.ts — new; correctly clamps at zero`.

## Step 1 — Assemble the packet

Write the packet to a scratch path (use the session scratchpad directory if you have one, otherwise `/tmp`). Use this shape:

```markdown
# Review request

## Original task
<The user's request in THEIR words, quoted verbatim. If it spanned several
messages, quote each. This is what "spec adherence" is measured against —
paraphrasing it into your own words launders your interpretation into the
spec, and then the reviewer can only check your code against your reading.>

## Stated constraints and acceptance criteria
<Anything explicit: "must not break existing callers", "keep it under 100ms",
"don't touch the schema". Omit this section if there were none — do not invent
criteria to fill it.>

## Files changed
- path/to/file.ts — new; <one neutral clause on what it is>
- path/to/other.ts — modified; <one neutral clause>

## Diffs
<For each MODIFIED file, paste `git diff` output here. The reviewer has no
shell, so anything you do not paste, it cannot see. New/untracked files do not
need pasting — it can Read them.>

## Your task
Review this change for two things:

1. **Bugs** — logic errors, off-by-ones, wrong operators, unhandled null/empty/
   zero cases, broken error paths, race conditions, resource leaks, incorrect
   API usage, changes that break existing callers.
2. **Spec adherence** — places where the code does something other than what
   the Original task asked for, including requirements silently skipped.

Read the surrounding code before judging. The listed files are the change, but
the repo is open to you — check callers, types, tests, and config to see how
this code is actually used.

Skip style, naming, formatting, and refactors that do not change behavior.

For every finding, give:
- `file:line`
- what is wrong, in one sentence
- **a concrete failure case: specific inputs or state, and the wrong output or
  crash that results**
- severity: high (wrong results, data loss, crash on a normal path) / medium
  (breaks on an edge case) / low (works, but fragile)

If a finding cannot be expressed as a concrete failure case, do not report it.
That test is the whole difference between a review and a list of suspicions.

If you find nothing, say so explicitly and say what you checked. Do not pad.

## Output
Print your review to stdout as your final message. You have no write tools; do
not try to save files.
```

**Scope**: list the files you touched this session. Do not list the whole branch — re-reviewing already-reviewed code burns tokens and buries new findings in old noise. The reviewer can still read anything it wants for context, which covers the main risk of a narrow file list: ripple effects into files you did not edit.

## Step 2 — Run the reviewer

```bash
<skill-dir>/scripts/second-opinion.sh <packet-path>
```

`<skill-dir>` is the installed `second-opinion` skill directory (in Claude Code, `.claude/skills/second-opinion`).

Run it from the repo root so the reviewer picks up the project's agent-rules files (`AGENTS.md`, `CLAUDE.md`) — project conventions are frequently what "correct" means, and a reviewer that does not know them reports false positives against the house style. The highest-value thing those files can carry is a warning that some installed dependency postdates training data — that single line is what turns a confident finding into a correctly-discarded one.

Give the run a generous timeout — `600000` ms if your harness lets you set per-command timeouts. Reviews typically take 20–60s, but a large diff can run several minutes, and a timeout kills the review after you have already paid for it.

The script gives the reviewer `Read,Grep,Glob` and nothing else, so it cannot modify the repo, run commands, or reach MCP servers. It saves the report next to the packet as `<packet>.review.md`.

**Cost**: each run is a fresh process with no prompt-cache reuse, so expect roughly $0.20–$1.00 depending on model and diff size. If you are reviewing something small and mechanical, pass a cheaper model with `--model` — in testing it caught the same planted bugs at a fraction of the cost. Default to the session model for anything subtle, concurrent, or security-relevant.

## Step 3 — Triage before you touch anything

The reviewer is confident by construction and context-free by design. Both of those produce false positives. **Verify every finding against the actual code before acting on it** — read the file, follow the callers, check the types. Its confidence is not evidence.

Findings that are usually wrong:

- **Already handled elsewhere** — a guard in the caller, a validation layer, a type constraint, a DB check. The reviewer read a slice of the repo, not all of it.
- **Intentional per this conversation** — the user asked for exactly this behavior, or you two ruled out the alternative earlier. The reviewer cannot see that.
- **Style wearing a bug costume** — "should validate inputs" with no failure case behind it, on a private function whose only caller already validates.
- **Invented API behavior** — a claim about what a library or framework does, from memory. Check the actual docs or source, especially in this repo, where the installed framework version may not match anyone's training data.

Findings that are usually right: off-by-ones, inverted conditions, wrong operators, an unhandled empty/zero/null case with a stated repro, and *anything about a requirement in the Original task that the code does not implement*. That last category is where this technique earns its keep, so weigh it accordingly.

## Step 4 — Fix, then report

Fix every finding you confirmed. Then re-run the project's tests or typecheck if it has them — an unverified fix is just a second unreviewed change.

Escalate to the user instead of auto-fixing when the fix would:

- change public API, behavior, or output the user explicitly chose
- require a refactor substantially larger than the original change
- land outside the scope of what you were asked to do (a real bug in code you did not touch — report it, don't quietly widen the diff)
- resolve a genuine ambiguity in the spec, where you would be picking for them

Then report, briefly:

```
Second opinion: <N> findings, <M> fixed.

Fixed:
- <file:line> — <what was wrong> → <what you changed>

Rejected:
- <file:line> — <what it claimed> — <why it's wrong, from the code you read>

Needs your call:
- <file:line> — <the issue and the options>
```

Include the rejected findings. They are how the user audits your triage — a review where you silently dropped half the findings is indistinguishable from one that found half as much.

If the reviewer found nothing, say that in one line and move on. Do not manufacture findings to justify the run, and do not re-run it hoping for a different answer.

## When to skip this

Not every edit needs a second pair of eyes. Skip it for one-line typo fixes, comment and doc changes, formatting, dependency version bumps, and generated files. Running it on trivial changes trains the user to ignore its output, which costs you the times it matters.

If the reviewer command fails or the script exits nonzero, tell the user the review did not run. Never let a failed review get reported as a clean one.
