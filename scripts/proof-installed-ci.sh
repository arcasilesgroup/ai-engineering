#!/bin/sh
# scripts/proof-installed-ci.sh — the pipeline WE INSTALL, exercised end to end on the
# code of the current commit: the machine side, the workflow, the fail-closed gate,
# and the pinning rules. It exists because the installed workflow had never been run
# by anyone: the npm package it installed does not exist, the trivy ref it named does
# not exist, and three of its steps could not fail (measured 2026-09-10).
#
# AI_ENG_BIN lets CI point at the compiled binary while a developer gets the source:
#   AI_ENG_BIN="bun dist/ai-eng" sh scripts/proof-installed-ci.sh
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
# What P2 compares against is what init installs, and init installs the template embedded
# in the binary — so this is the shipped file or nothing.
TEMPLATE="$REPO/templates/ci.yml.tpl"
AI_ENG_BIN="${AI_ENG_BIN:-bun run $REPO/src/cli.ts}"
# This script changes directory, so a relative binary path silently points at nothing
# (and `bun dist/ai-eng` asks Bun to interpret a compiled binary as a script).
case "$AI_ENG_BIN" in
  /*|"bun run "*) ;;
  *) echo "proof-installed-ci: AI_ENG_BIN must be an absolute path or 'bun run <file>' (got: $AI_ENG_BIN)" >&2; exit 2 ;;
esac
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
[ -f "$AI_ENG_HOME/skills/ai-proof/scripts/gate-check.mjs" ] || die "P1: the contract runner the installed gate needs is absent"
[ ! -d "$P1DIR/.ai-engineering" ] || die "P1: init --global wrote into the cwd"
say "P1 evidence: canon installed under AI_ENG_HOME, cwd untouched"

# ── P2: a fresh repo receives the workflow, byte-identical to the template ──
P2DIR="$(mktemp -d)"; cd "$P2DIR" || exit 1; git init -q .
$AI_ENG_BIN init --yes --surface claude-code >/dev/null 2>&1 || die "P2: init exited non-zero"
INSTALLED="$P2DIR/.github/workflows/ai-eng-check.yml"
[ -f "$INSTALLED" ] || die "P2: the workflow was not installed"
cmp -s "$INSTALLED" "$TEMPLATE" || die "P2: the installed workflow differs from $TEMPLATE"
say "P2 evidence: workflow installed, byte-identical to $TEMPLATE"

# ── P3: the installed gate is fail-closed, and says why ─────────────────────────
P3OUT=$($AI_ENG_BIN spec run 2>&1); P3CODE=$?
[ "$P3CODE" = "2" ] || die "P3: spec run with no contract exited $P3CODE (expected 2)"
printf '%s' "$P3OUT" | grep -q 'no spec.html' || die "P3: spec run did not name the missing contract"
say "P3 evidence: no contract → exit 2, message names it (green by absence is impossible)"

# The template's own rules (no fail-open, nothing from npm, every action SHA-pinned,
# one declared version) are asserted in tests/installed-ci.spec.ts, against the same
# bytes P2 proved identical to what init installs. Re-checking them here was the same
# fact in two places, free to drift, and the asset probe that followed could not fail.

if [ "$FAILED" = "0" ]; then say "installed-ci: all proofs passed"; else say "installed-ci: FAILED"; fi
exit $FAILED
