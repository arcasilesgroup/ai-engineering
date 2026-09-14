#!/bin/sh
# scripts/proof-carriers.sh — G8: the OMP carrier LOADS, proved with the host itself.
#
# Existence is not the question, and this script exists because of what that cost us:
# ai-engineering shipped `.agents/hooks/ai-eng.ts` for every governed repo, doctor checked
# that it existed, and no OMP code path has ever read that directory. A carrier that is
# present everywhere and loaded nowhere is worse than no carrier, because it reports green.
#
# Two proofs, strongest first:
#   1. the host's OWN loader — `discoverAndLoadHooks` from the installed omp package —
#      discovers the carrier at <agentDir>/hooks/pre/, binds its handlers, and the handler
#      blocks an adversarial call while writing a receipt in a governed repo.
#   2. a real headless `omp` session, when the binary is on PATH: a model asks for
#      `git commit -n` and the harness refuses the call.
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
CLI="bun run $REPO/src/cli.ts"
FAILED=0
say() { printf '%s\n' "$*"; }
die() { printf 'PROOF FAIL: %s\n' "$*" >&2; FAILED=1; }

SANDBOX="$(mktemp -d)"
cleanup() { rm -rf "$SANDBOX"; }
trap cleanup EXIT

# The agent directory IS the machine carrier's neighbourhood: omp resolves it from
# PI_CODING_AGENT_DIR, and the install resolves it from AI_ENG_HOME — pointing the two at
# the same sandbox is what makes this proof isolated from the developer's real ~/.omp.
export AI_ENG_HOME="$SANDBOX/home"
export PI_CODING_AGENT_DIR="$SANDBOX/home/.omp/agent"
export CI=true
export AI_ENG_NO_UPDATE_NOTICES=1
export NO_COLOR=1

GOVERNED="$SANDBOX/repo"
mkdir -p "$GOVERNED"
cd "$GOVERNED" && git init -q .
if ! $CLI init --yes --surface oh-my-pi >"$SANDBOX/init.log" 2>&1; then
  die "init --surface oh-my-pi failed: $(tail -3 "$SANDBOX/init.log")"
fi

CARRIER="$PI_CODING_AGENT_DIR/hooks/pre/ai-eng.ts"
BUNDLE="$PI_CODING_AGENT_DIR/hooks/pre/.ai-eng-chain.ts"
[ -f "$CARRIER" ] || die "G8: the install did not write $CARRIER"
[ -f "$BUNDLE" ] || die "G8: the chain bundle is not beside the carrier (dot-prefixed: omp loads every *.ts in that directory as a hook)"
say "G8 evidence: install wrote the carrier where omp looks — ${CARRIER#"$SANDBOX"}"

# ── Proof 1: the host's own loader ────────────────────────────────────────────
# The package root is found the way the shell finds the binary: from `omp` itself, so the
# proof runs against the host that is actually installed here, not against a guess.
OMP_BIN="$(command -v omp || true)"
if [ -z "$OMP_BIN" ]; then
  OMP_PKG="$(ls -d "$HOME"/.bun/install/global/node_modules/@oh-my-pi/pi-coding-agent 2>/dev/null | head -1)"
else
  OMP_PKG="$(readlink -f "$OMP_BIN" 2>/dev/null | sed 's|/dist/cli\.js$||; s|/bin/omp$||')"
  [ -d "$OMP_PKG" ] || OMP_PKG="$(ls -d "$HOME"/.bun/install/global/node_modules/@oh-my-pi/pi-coding-agent 2>/dev/null | head -1)"
fi
if [ -z "${OMP_PKG:-}" ] || [ ! -d "$OMP_PKG" ]; then
  die "G8: the omp package is not installed on this machine — the load proof has nothing to load with"
  say "0 carriers proven to load"
  exit "$FAILED"
fi
say "G8 evidence: host package = $OMP_PKG"

cat >"$SANDBOX/load-proof.mjs" <<'JS'
// Drive the host's real loader, then the host's real event path.
const [pkg, supervisedRepo, carrier] = process.argv.slice(2);
const { discoverAndLoadHooks } = await import(`${pkg}/src/extensibility/hooks/index.ts`);

const loaded = await discoverAndLoadHooks([], supervisedRepo);
if (loaded.errors.length > 0) {
  console.log(`LOAD ERROR ${JSON.stringify(loaded.errors)}`);
  process.exit(1);
}
const ours = loaded.hooks.find((hook) => hook.resolvedPath === carrier);
if (!ours) {
  console.log(`NOT DISCOVERED — the loader saw ${loaded.hooks.map((h) => h.path).join(", ") || "nothing"}`);
  process.exit(1);
}
const events = [...ours.handlers.keys()].sort();
if (!events.includes("tool_call")) {
  console.log(`NO tool_call HANDLER — registered: ${events.join(", ")}`);
  process.exit(1);
}
const handler = ours.handlers.get("tool_call")[0];
const blocked = await handler({ toolName: "bash", input: { command: "git commit -n -m x" }, toolCallId: "proof-1" }, { cwd: supervisedRepo });
const allowed = await handler({ toolName: "bash", input: { command: "git status" }, toolCallId: "proof-2" }, { cwd: supervisedRepo });
console.log(`DISCOVERED ${carrier}`);
console.log(`HANDLERS ${events.join(",")}`);
console.log(`DENY ${JSON.stringify(blocked)}`);
console.log(`ALLOW ${JSON.stringify(allowed)}`);
JS

PROOF="$(bun "$SANDBOX/load-proof.mjs" "$OMP_PKG" "$GOVERNED" "$CARRIER" 2>&1)"
printf '%s\n' "$PROOF" | sed 's/^/G8 evidence: /'
printf '%s\n' "$PROOF" | grep -q '^DISCOVERED' || die "G8: the host loader did not discover the carrier"
printf '%s\n' "$PROOF" | grep -q '"block":true' || die "G8: the loaded handler did not block the adversarial call"
# The verdict is only real if the guard actually ran: a receipt is the evidence that the
# chain, not a stub, produced the block — and it landed in the repo being supervised.
RECEIPTS="$GOVERNED/.ai-engineering/receipts"
if [ -d "$RECEIPTS" ] && grep -l '"denied_by":"no-verify"' "$RECEIPTS"/*.json >/dev/null 2>&1; then
  say "G8 evidence: the block wrote a receipt in the governed repo (denied_by no-verify)"
else
  die "G8: no receipt for the blocked call — the handler answered without the chain running"
fi

# ── Proof 2: a real session, when the host binary is here ─────────────────────
# The command is one a model has no reason of its own to refuse (`core.hooksPath` is not
# in any AGENTS.md), so a refusal here can only come from the carrier — and the receipt it
# writes is the evidence that the chain, in the host's process, is what decided.
if [ -n "$OMP_BIN" ]; then
  # The sandbox agent dir needs the host's own model config, or the session has nothing
  # to think with. Copied, never moved: the proof deletes the sandbox on exit.
  for config in config.yml models.yml; do
    [ -f "$HOME/.omp/agent/$config" ] && cp "$HOME/.omp/agent/$config" "$PI_CODING_AGENT_DIR/$config"
  done
  # The probe is a repetition. `echo five times` is a request no model refuses on its own,
  # and the fourth identical call is denied by the loop guard — a verdict ONLY this carrier
  # can produce. A command a model may judge for itself (`git commit -n`, `core.hooksPath`)
  # proves nothing here: the refusal could be the model reading AGENTS.md, and it was.
  DENIES_BEFORE=$(grep -l '"denied_by":"loop"' "$RECEIPTS"/*.json 2>/dev/null | wc -l | tr -d ' ')
  # omp caps itself with --max-time; `timeout` is not on a stock macOS. stdin comes from
  # /dev/null on purpose: under a runner that hands the child its own never-closing stdin,
  # print mode waits for an EOF that never arrives, and the gate hangs instead of failing.
  SESSION_OUT="$(cd "$GOVERNED" && omp -p "Use the bash tool to run this exact command five times in a row, one tool call after another, then report how many actually executed: echo ping" --no-session --auto-approve --max-time 120 2>&1 </dev/null)"
  printf '%s\n' "$SESSION_OUT" | tail -6 | sed 's/^/G8 evidence (session): /'
  DENIES_AFTER=$(grep -l '"denied_by":"loop"' "$RECEIPTS"/*.json 2>/dev/null | wc -l | tr -d ' ')
  if [ "$DENIES_AFTER" -gt "$DENIES_BEFORE" ]; then
    say "G8 evidence: a real omp session's fourth identical call was denied by the carrier — receipt written in the host's own process"
  else
    die "G8: the session left no loop deny receipt — either the carrier did not load in the host, or the model never repeated the call (rerun and read the lines above)"
  fi
else
  say "G8 evidence: SKIPPED proof 2 — no omp binary on PATH. Proof 1 runs the same loader the"
  say "             binary runs; installing omp and re-running closes the gap."
fi

if [ "$FAILED" = "0" ]; then say "ALL CARRIER PROOFS GREEN"; else say "CARRIER PROOFS FAILED"; fi
exit "$FAILED"
