#!/bin/sh
# scripts/proof-cli.sh — every human verb and every lane flow, end to end, on one OS:
# init, doctor, work, config (CI provider swap), update (offline), the SessionStart hook,
# the one-writer lease, the no-stash guard and uninstall. It drives a real binary in a
# bare repo, so what passes here is what a person gets. The deep cross-OS workflow
# (platforms-deep.yml) runs it on every runner; locally:
#   AI_ENG_BIN="bun run $PWD/src/cli.ts" sh scripts/proof-cli.sh
#   AI_ENG_BIN="$PWD/dist/ai-eng" sh scripts/proof-cli.sh
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
AI_ENG_BIN="${AI_ENG_BIN:-bun run $REPO/src/cli.ts}"
case "$AI_ENG_BIN" in
  /*|[A-Za-z]:*|"bun run "*) ;;
  *) echo "proof-cli: AI_ENG_BIN must be an absolute path or 'bun run <file>' (got: $AI_ENG_BIN)" >&2; exit 2 ;;
esac
SANDBOX="$(mktemp -d)"
export AI_ENG_HOME="$SANDBOX/home"
export CI=1 NO_COLOR=1
# Offline by construction: the registry is a closed local port, so update syncs only.
export AI_ENG_REGISTRY_URL="http://127.0.0.1:9/ai-engineering/latest"
FAILED=0
say() { printf '%s\n' "$*"; }
die() { printf 'PROOF FAIL: %s\n' "$*" >&2; FAILED=1; }
ai() { $AI_ENG_BIN "$@"; }
# One hook call: the payload on stdin, the exit code back.
hook() { printf '%s' "$2" | $AI_ENG_BIN chain "$1" >"$SANDBOX/hook.out" 2>&1; }

R="$SANDBOX/repo"
mkdir -p "$R" && cd "$R" || exit 1
git init -q --template= -b main
git config user.email proof@example.com && git config user.name proof && git config commit.gpgsign false
echo "base" > README.md && git add README.md && git commit -q -m "chore: base"

# ── 1. init writes the contract, the chosen CI gate and the lock ──
ai init --yes --surface claude-code --ci github-actions >"$SANDBOX/init.out" 2>&1 || die "init exited non-zero: $(tail -3 "$SANDBOX/init.out")"
for f in AGENTS.md .ai-engineering/config.toml .ai-engineering/ai-eng.lock .github/workflows/ai-eng-check.yml; do
  [ -f "$f" ] || die "init did not write $f"
done
grep -q 'provider = "github-actions"' .ai-engineering/config.toml || die "config.toml does not record the CI provider"
say "1 init: contract, GitHub gate and lock written"

# ── 2. doctor answers on the fresh repo ──
ai doctor >"$SANDBOX/doctor.out" 2>&1 || die "doctor exited non-zero: $(tail -5 "$SANDBOX/doctor.out")"
say "2 doctor: exit 0"

# ── 3. work shows the board, and --json is parseable ──
ai work >"$SANDBOX/work.out" 2>&1 || die "work exited non-zero"
grep -q "active lanes:" "$SANDBOX/work.out" || die "work printed no board"
ai work --json >"$SANDBOX/work.json" 2>/dev/null || die "work --json exited non-zero"
grep -q '"lanes"' "$SANDBOX/work.json" || die "work --json has no lanes key"
say "3 work: board and JSON"

# ── 4. config swaps the CI gate and leaves no empty folder behind ──
ai config --ci azure-pipelines >"$SANDBOX/config.out" 2>&1 || die "config --ci azure-pipelines exited non-zero"
[ -f .azure-pipelines/ai-eng-check.yml ] || die "the Azure gate was not written"
[ ! -e .github ] || die "the emptied .github folder was left behind"
ai config --ci none >/dev/null 2>&1 || die "config --ci none exited non-zero"
[ ! -e .azure-pipelines ] || die "--ci none left the Azure gate"
say "4 config: github → azure → none, no empty folders"

# ── 5. update offline: no install, the sync runs ──
ai update --yes >"$SANDBOX/update.out" 2>&1 || die "update exited non-zero offline: $(tail -3 "$SANDBOX/update.out")"
say "5 update: offline sync, exit 0"

# ── 6. hooks: SessionStart answers, the lease and no-stash guards hold ──
hook SessionStart "{\"cwd\":\"$R\"}" || die "SessionStart exited non-zero"
edit() { printf '{"tool_name":"Edit","tool_input":{"file_path":"%s/README.md","old_string":"base","new_string":"next"},"cwd":"%s","session_id":"%s","tool_use_id":"%s"}' "$R" "$R" "$1" "$1-$2"; }
hook PreToolUse "$(edit session-a 1)" || die "the first session's edit was denied: $(cat "$SANDBOX/hook.out")"
if hook PreToolUse "$(edit session-b 1)"; then die "a second session's edit in the same folder was allowed"; fi
grep -q "another session" "$SANDBOX/hook.out" || die "the lease denial does not say why"
ai work release >/dev/null 2>&1 || die "work release exited non-zero"
hook PreToolUse "$(edit session-b 2)" || die "after release, the next session was still denied"
if hook PreToolUse "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"git stash\"},\"cwd\":\"$R\",\"session_id\":\"session-b\",\"tool_use_id\":\"stash-1\"}"; then
  die "git stash was allowed"
fi
say "6 hooks: SessionStart, one writer per folder, no stash"

# ── 7. uninstall takes ai-eng's files and keeps the person's ──
echo "" | ai uninstall >"$SANDBOX/uninstall.out" 2>&1 || die "uninstall exited non-zero"
[ -f AGENTS.md ] || die "uninstall removed AGENTS.md, which is the person's"
say "7 uninstall: the contract stays"

if [ "$FAILED" = "0" ]; then say "proof-cli: all proofs passed"; else say "proof-cli: FAILED"; fi
exit $FAILED
