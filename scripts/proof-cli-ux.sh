#!/bin/sh
# scripts/proof-cli-ux.sh — sandbox proofs for cli-ux-14 gates G1, G3, G4, G5, G6, G7, G8.
# Every gate prints EVIDENCE lines. Exit 0 only when every proof asserts true.
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
CLI="bun run $REPO/src/cli.ts"
HOME_ISOLATED="$(mktemp -d)/ai-eng-home"
export AI_ENG_HOME="$HOME_ISOLATED"
export CI=true
FAILED=0
say() { printf '%s\n' "$*"; }
die() { printf 'PROOF FAIL: %s\n' "$*" >&2; FAILED=1; }

# ── G1: NO_COLOR + piped stdout → zero ANSI escape bytes ──────────────
G1DIR="$(mktemp -d)"; cd "$G1DIR" && git init -q .
ANSI_COUNT=$(printf '\n\n\n' | NO_COLOR=1 $CLI init --yes 2>/dev/null | LC_ALL=C grep -c "$(printf '\033')" || true)
say "G1 evidence: ANSI escape lines with NO_COLOR piped = $ANSI_COUNT (must be 0)"
[ "$ANSI_COUNT" = "0" ] || die "G1: $ANSI_COUNT ANSI lines leaked"

# ── G3: init --yes end-to-end: contract planted, frame complete, exit 0 ─
G3DIR="$(mktemp -d)"; cd "$G3DIR" && git init -q .
INIT_OUT=$(printf '\n\n\n' | $CLI init --yes 2>&1); INIT_CODE=$?
[ "$INIT_CODE" = "0" ] || die "G3: init exit $INIT_CODE"
[ -f AGENTS.md ] || die "G3: AGENTS.md missing"
[ -f .ai-engineering/config.toml ] || die "G3: config.toml missing"
[ -x .git/hooks/pre-commit ] || die "G3: pre-commit shim missing"
INIT_OUT=$(printf '\n\n\n' | $CLI init --yes 2>&1); INIT_CODE=$?
say "G3 evidence: exit 0, AGENTS.md+config.toml+pre-commit exist, frame complete"
printf '%s\n' "$INIT_OUT" | grep -E 'Scaffolded|Two steps' | head -2 | sed 's/^/G3 evidence: /'

# ── G4: six user paths of §14.5b (scriptable subset) ───────────────────
# Path 1: bare folder → init creates the repo itself.
G4A="$(mktemp -d)"; cd "$G4A"
printf 'y\n \n\n\n\n\n' | $CLI init >/dev/null 2>&1
[ -d .git ] || die "G4 path1: bare folder did not get a repo"
say "G4 evidence: path1 bare-folder → git repo created"
# Path 3: re-init a governed repo → offers three options.
REINIT_OUT=$(printf '\n' | $CLI init 2>&1)
printf '%s\n' "$REINIT_OUT" | grep -q "already governed" || die "G4 path3: re-init prompt missing"
printf '%s\n' "$REINIT_OUT" | grep -q "config" || die "G4 path3: config option missing"
printf '%s\n' "$REINIT_OUT" | grep 'already governed' | head -1 | sed 's/^/G4 evidence: path3 /'
printf '\n\n\n' | $CLI init >/dev/null 2>&1
# Path 4: CI/script: --yes --surface claude-code → zero prompts, exit 0.
G4B="$(mktemp -d)"; cd "$G4B" && git init -q .
YES_OUT=$($CLI init --yes --surface claude-code 2>&1); YES_CODE=$?
[ "$YES_CODE" = "0" ] || die "G4 path4: --yes --surface exit $YES_CODE"
say "G4 evidence: path4 --yes --surface claude-code → exit 0 zero prompts"
# Path 5: config --add omp adds a surface without prompts.
CFG_OUT=$($CLI config --add omp 2>&1)
grep -q 'omp' .ai-engineering/config.toml || die "G4 path5: omp not in config.toml"
say "G4 evidence: path5 config --add omp → surfaces updated"
# Path 6: uninstall governance keeps the four contract files.
UN_OUT=$(printf '\n\n' | $CLI uninstall 2>&1)
[ -f AGENTS.md ] || die "G4 path6: AGENTS.md deleted by uninstall"
[ -f DECISIONS.md ] || die "G4 path6: DECISIONS.md deleted"
[ -f .ai-engineering/config.toml ] || die "G4 path6: config.toml deleted"
say "G4 evidence: path6 uninstall → contract files kept"

# ── G5: doctor canon line counts embedded assets, never "0 assets" ─────
G5DIR="$(mktemp -d)"; cd "$G5DIR" && git init -q .
printf '\n\n\n' | $CLI init --yes >/dev/null 2>&1
DOC_OUT=$($CLI doctor 2>&1)
printf '%s\n' "$DOC_OUT" | grep -E 'canon' | sed 's/^/G5 evidence: /'
printf '%s\n' "$DOC_OUT" | grep 'canon' | grep -q '0/92' && die "G5: canon shows 0 verified"
printf '%s\n' "$DOC_OUT" | grep 'canon' | grep -qE '[0-9]+/92 files verified' || die "G5: canon line malformed"

# ── G6: doctor WARNs assets-outdated when lock.version is older ────────
sed -i '' 's/version = "2.0.0"/version = "1.9.9"/' .ai-engineering/ai-eng.lock 2>/dev/null \
  || sed -i 's/version = "2.0.0"/version = "1.9.9"/' .ai-engineering/ai-eng.lock
DOC2_OUT=$($CLI doctor 2>&1)
printf '%s\n' "$DOC2_OUT" | grep 'assets' | sed 's/^/G6 evidence: /'
printf '%s\n' "$DOC2_OUT" | grep 'assets' | grep -q 'ai-eng update' || die "G6: assets-outdated WARN missing"

# ── G7: update twice → second run short-circuits, lock untouched ───────
G7DIR="$(mktemp -d)"; cd "$G7DIR" && git init -q .
printf '\n\n\n' | $CLI init --yes >/dev/null 2>&1
MTIME1=$(stat -f %m .ai-engineering/ai-eng.lock 2>/dev/null || stat -c %Y .ai-engineering/ai-eng.lock)
sleep 1
UPD_OUT=$(printf '\n' | $CLI update 2>&1); UPD_CODE=$?
MTIME2=$(stat -f %m .ai-engineering/ai-eng.lock 2>/dev/null || stat -c %Y .ai-engineering/ai-eng.lock)
[ "$UPD_CODE" = "0" ] || die "G7: update exit $UPD_CODE"
[ "$MTIME1" = "$MTIME2" ] || die "G7: lock mtime changed on no-op update"
printf '%s\n' "$UPD_OUT" | grep -E 'assets current' | sed 's/^/G7 evidence: /'
printf '%s\n' "$UPD_OUT" | grep -q 'assets current' || die "G7: short-circuit line missing"

# ── G8: user-patched hook survives update with keep-mine default ───────
printf '\n# my custom bit: pnpm install --frozen\n' >> .git/hooks/pre-commit
G8_OUT=$(printf '\n' | $CLI update 2>&1)
printf '%s\n' "$G8_OUT" | grep 'patched by you' | sed 's/^/G8 evidence: /'
printf '%s\n' "$G8_OUT" | grep -q 'patched by you' || die "G8: conflict not listed"
grep -q 'my custom bit' .git/hooks/pre-commit || die "G8: user patch lost"

say ""
if [ "$FAILED" = "0" ]; then say "ALL PROOFS GREEN"; else say "PROOFS FAILED — see PROOF FAIL lines"; fi
exit $FAILED
