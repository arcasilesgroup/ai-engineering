# Architecture · security run-1 (milestone diff, 2026-09-21)

Target: the milestone diff over base `dd6cb944` — `src/chain/mod.ts` (+37), `src/receipts.ts` (+102), `src/commands/doctor.ts` (+72) — plus the uncommitted `src/guards/policy.ts` the same trigger fires on (`src/guards/**` glob). The diff also drags the pending policy guard; the audit covers both.

## What this system is

A deny-machine hook: one short-lived process per tool call. `runChain` (chain/mod.ts) normalises the host payload, consults a TABLE of guards, and answers allow/deny/rewrite to the host in the host's dialect. Every decision writes a one-JSON receipt into `<repo>/.ai-engineering/receipts/`. `doctor --gc` (commands/doctor.ts) aggregates and deletes old receipts; `summarizeReceipts`/`mergeDaily` (receipts.ts) are the aggregate's readers. Fail-closed is the law: unreadable payload → deny, guard crash → deny.

## Trust boundaries

1. **Host payload is hostile input.** `tool_input`, `session_id`, `cwd`, `tool_use_id` arrive from an external process; a model under prompt injection may shape them. Everything reaching a guard went through `normalise()`; everything reaching a filename goes through a sha256 derivation (never the raw string).
2. **`.ai-engineering/` files are semi-trusted local state** — written by this binary, but a compromised agent session runs inside the repo and CAN write them (the receipts dir is inside the governed tree). Readers must survive torn, forged and hostile content, because "an agent that can Write can write your ledger".
3. **The machine home (`~/.ai-engineering`) is the canon carrier**; `AI_ENG_HOME` is honoured except when it resolves inside the governed repo (audit LOGIC-003).

## Input surfaces the diff newly touches

- `denies.json` — ledger, read on EVERY guard-deny by `upsertDenyLedger`; keyed by `loopExact` (sha256 of tool+input). The file's parsed content flows into an arithmetic count shown in the human-facing deny message (`repeats`).
- `summary.json` — gc merge reads prior `daily`, merges, writes back; `denySpike` reads it on every `doctor` run and renders a WARN string with the top `per_guard` key.
- `receipts/*.json` — `summarizeReceipts` parses each; the new fields `tool`, `guards.denied_by`, `surface` are used as bucket keys straight from parsed JSON.
- `denyOutcome(..., loopKey)` — the clause `· this exact call has been denied N times before` is built from ledger-parsed `n` and travels into the hook's stdout to the host, i.e. into a (possibly injected) model's context.

## What the design claims (the bar to attack)

- "Signal only: never changes a verdict." Every ledger path is try/catch-soft; the verdict string keeps the guard's own words with one clause appended.
- "A corrupt or unwritable ledger changes no verdict and no reason byte."
- "The 50 ms ceiling is untouched" — the ledger write sits on the deny branch only.
- The file-identity invariant: `summary.json`/`denies.json` skip the mtime sweep, skip receipt counting, and only their own content-based prunes delete entries.

No prior security runs exist for this repo (first run-N). Prior known-findings ledger: empty.
