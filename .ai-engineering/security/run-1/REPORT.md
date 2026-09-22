# Security audit · run-1 · milestone gobernabilidad-observabilidad (2026-09-21)

## Executive summary

The milestone's own claim held where it matters most: **the ledger and its clause never change a verdict.** Every adversarial attempt to flip deny→allow through `denies.json` (torn bytes, hostile `n` shapes, unwritable file) failed — the chain answers identically, and the 50 ms p95 read path never touches the ledger. What the audit *did* find is that the observability layer trusts files an agent inside the repo is designed to be able to write (`.ai-engineering/receipts/` is session material per `self-protect.ts:81-88`'s own comment), and a display built on that trust can be made to lie. All four aggregate-layer findings plus two hot-path findings were **fixed in the working tree during this audit** with pinning regression tests (suite: 734 pass / 0 fail). The policy-guard findings live in uncommitted parallel work (`src/guards/policy.ts`, D-002) and are reported open for that owner; the `findings.json` dispositions are `open` for everything because no fix commit exists yet — flip to `fixed` with the landing sha when the milestone commits.

## Baseline

Comparable: host-based guard hook systems (bash-guard, whose policy.rs this repo ported). The port inherited the textual-fence idea faithfully; the gaps found here (variable indirection, unexpanded `$`) are the known weakness of raw-string classifiers, present in the original design, not introduced by the port's mechanics. The receipts-as-session-material trust model differs from the comparable (which has no in-repo state) — that difference is the root of findings F1-F6.

## Findings

| # | Severity | Title | Status |
|---|----------|-------|--------|
| F1 | high | Forged `summary.json` silences the deviation WARN forever while the row prints ✓ ok | fixed in worktree (rule reads the raw receipt trail) |
| F2 | medium | Type-unchecked aggregates: string denies fabricate `spike 0999999`; `n:{}` NaN-erases the repeats count | fixed in worktree (`count()` coercion) |
| F3 | high | Receipt keys with `\n`/ESC forge whole doctor rows (fake `✓ chain test` line) inside the governed frame | fixed in worktree (`printable()` at summarize source) |
| F4 | medium | Planted directory named `bomb.json` throws gc before the summary write — permanent collection DoS, freezes F1's baseline | fixed in worktree (`lstat().isFile()` sweep) |
| F5 | medium | Unbounded attacker-writable ledger read+rewritten on every deny (16 MB plant measured 49.7-78.5 ms/deny) | fixed in worktree (hot-path `LEDGER_CAP` trim) |
| F6 | medium | Wrap rewrites cached as hard denials — redelivery of the same physical call flips rewrite→deny | fixed in worktree (never cache a rewrite) |
| P1 | high | Bare `rm -rf ~` / `rm -rf $HOME` allowed by the 0467 matrix (token never classified) | open — parallel policy-guard work |
| P2 | high | Unexpanded `$` paths launder to WORKSPACE: `cat $HOME/.ssh/id_rsa`, `rm -rf /${x}`, `x=/etc; cat $x/passwd` | open — policy-guard owner |
| P3 | high | `curl …\|sh` (no space) and `bash <(curl …)` execute remote code; the spaced form denies | open — policy-guard owner |
| P4 | medium | Symlink two-step: `ln -s ~/.ssh x && rm -rf x/*` destroys external trees as pure workspace ops | open — policy-guard owner |
| S1 | medium | self-protect's textual fence evaded by `f=.ai-engineering/config.toml; >> $f` (plain form denies, indirect form allows) | open — pre-existing design (guard owner) |

Each carries a full trace, exact payloads and remediation in `findings.json`. Repro commands for the policy classes (P1-P3, verified by direct execution): `bun mk6.ts`-style harness feeding `runPolicy(cmd, cwd, "0467")`; contrast spellings deny, bypass spellings allow, 12/12.

## Hardening notes (not findings)

- The deny clause interpolates `repeats` from the ledger with a `typeof === "number"` guard, so an attacker can inflate the *number* a human sees (e.g. `n: 999999`) but not the text. Accepting a lie in a count of your own denies is within the "bell, not enforcement" design.
- `loopExact` is a 16-hex (64-bit) truncated sha — collision-resistant enough for a per-repo bell; not for anything enforcement-shaped.
- Coverage: single run finds ~half of total. A second run against this diff (especially the dialect fail-open contract in `chain/dialect.ts:9-13` combined with slower hosts) is recommended.

## Positive patterns

Fail-closed discipline is real and held under every attempt: guard crash → deny, torn JSON → counted as data not crash, corrupt ledger → verdict bytes unchanged, unwritable state → chain proceeds. `printable()` existed precisely because a prior audit learned host text must be stripped — the pattern was simply not wired to the new reads (now it is). The verdict-cache correctly refused double-counting; PostToolUse routing means the write-guards never see reads.
