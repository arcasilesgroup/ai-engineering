#!/bin/sh
# scripts/proof-planted-ci.sh — the pipeline WE PLANT, exercised end to end on the
# code of the current commit: the machine side, the workflow, the fail-closed gate,
# and the pinning rules. It exists because the planted workflow had never been run
# by anyone: the npm package it installed does not exist, the trivy ref it named does
# not exist, and three of its steps could not fail (measured 2026-09-10).
#
# AI_ENG_BIN lets CI point at the compiled binary while a developer gets the source:
#   AI_ENG_BIN="bun dist/ai-eng" sh scripts/proof-planted-ci.sh
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
# The template to validate: the caller may name it (the workflow passes it explicitly
# so the file the e2e proves is visible in the run), default is the shipped one.
TEMPLATE="${1:-templates/ci.yml.tpl}"
case "$TEMPLATE" in /*) ;; *) TEMPLATE="$REPO/$TEMPLATE" ;; esac
AI_ENG_BIN="${AI_ENG_BIN:-bun run $REPO/src/cli.ts}"
export AI_ENG_HOME="$(mktemp -d)/ai-eng-home"
export CI=true
export NO_COLOR=1
export AI_ENG_NO_UPDATE_NOTICES=1
FAILED=0
say() { printf '%s\n' "$*"; }
die() { printf 'PROOF FAIL: %s\n' "$*" >&2; FAILED=1; }

# ── P1: the machine side installs with no repo in sight (the template's own step) ──
P1DIR="$(mktemp -d)"; cd "$P1DIR" || exit 1
$AI_ENG_BIN init --global --yes >/dev/null 2>&1 || die "P1: init --global exited non-zero"
[ -f "$AI_ENG_HOME/skills/ai-proof/scripts/gate-check.mjs" ] || die "P1: the contract runner the planted gate needs is absent"
[ ! -d "$P1DIR/.ai-engineering" ] || die "P1: init --global wrote into the cwd"
say "P1 evidence: canon installed under AI_ENG_HOME, cwd untouched"

# ── P2: a fresh repo receives the workflow, byte-identical to the template ──
P2DIR="$(mktemp -d)"; cd "$P2DIR" || exit 1; git init -q .
$AI_ENG_BIN init --yes --surface claude-code >/dev/null 2>&1 || die "P2: init exited non-zero"
PLANTED="$P2DIR/.github/workflows/ai-eng-check.yml"
[ -f "$PLANTED" ] || die "P2: the workflow was not planted"
cmp -s "$PLANTED" "$TEMPLATE" || die "P2: the planted workflow differs from $TEMPLATE"
say "P2 evidence: workflow planted, byte-identical to $TEMPLATE"

# ── P3: the planted gate is fail-closed, and says why ─────────────────────────
P3OUT=$($AI_ENG_BIN spec run 2>&1); P3CODE=$?
[ "$P3CODE" = "2" ] || die "P3: spec run with no contract exited $P3CODE (expected 2)"
printf '%s' "$P3OUT" | grep -q 'no spec.html' || die "P3: spec run did not name the missing contract"
say "P3 evidence: no contract → exit 2, message names it (green by absence is impossible)"

# ── P4: no step can be skipped, nothing comes from npm, every action is pinned ──
grep -q '|| true' "$PLANTED" && die "P4: a step still swallows its own failure"
grep -q 'bun add -g ai-engineering' "$PLANTED" && die "P4: the governor still comes from npm"
P4UNPINNED="$(grep -oE 'uses: [^ ]+' "$PLANTED" | grep -vE '@[0-9a-f]{40}$' || true)"
[ -z "$P4UNPINNED" ] || die "P4: unpinned actions: $P4UNPINNED"
P4VERSION="$(grep -m1 'AI_ENG_VERSION:' "$PLANTED" | awk '{print $2}')"
[ -n "$P4VERSION" ] || die "P4: the governor version is not declared in one place"
say "P4 evidence: no fail-open, no npm, every uses: SHA-pinned, governor pinned to $P4VERSION"

# ── P5: the asset the client downloads — reported, not fatal (G6 owns the release) ──
P5URL="https://github.com/arcasilesgroup/ai-engineering/releases/download/$P4VERSION/ai-eng-linux-x64"
P5CODE="$(curl -sSL -o /dev/null -w '%{http_code}' "$P5URL" 2>/dev/null || echo 000)"
if [ "$P5CODE" = "200" ]; then
  say "P5 evidence: $P4VERSION/ai-eng-linux-x64 → 200"
else
  say "P5 evidence: $P4VERSION/ai-eng-linux-x64 → HTTP $P5CODE (not published yet; gate G6 is what fails)"
fi

if [ "$FAILED" = "0" ]; then say "planted-ci: all proofs passed"; else say "planted-ci: FAILED"; fi
exit $FAILED
