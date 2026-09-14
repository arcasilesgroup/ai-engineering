#!/bin/sh
# scripts/proof-security-audit.sh — G17: the audit of THIS milestone, and everything it claims.
#
# The check this replaces was `ls .ai-engineering/security/run-*/findings.json >/dev/null`: a glob
# every run satisfies, printing nothing. With run-1 (the previous milestone's audit) still on disk
# it stayed green while proving nothing, and it reported the same green after the silence rule
# arrived, because a check that prints nothing is not evidence.
#
# The gate's prose promises three things the glob never tested. This script tests exactly those:
#   1. the audit is the one for this milestone — named, not "whichever directory matches";
#   2. it carries both artifacts the skill's pipeline writes, findings.json and REPORT.md;
#   3. findings.json survived the schema the skill ships, and every exploitable finding was closed
#      or accepted with its reason — "Disposition:" on the finding's remediation. That marker is
#      the only place the disposition can live: report-schema.json declares remediation with
#      additionalProperties:false, so a separate `fix` key is rejected by the schema itself.
# Existence is not the question here either: the run directory is named, so a stray run-3 cannot
# carry this green.
set -eu
REPO="$(cd "$(dirname "$0")/.." && pwd)"
RUN=".ai-engineering/security/run-2"

die() { printf 'PROOF FAIL: %s\n' "$*" >&2; exit 1; }

# node is what the skill documents (`node <skill-dir>/references/validate-findings.cjs`); bun runs
# the same CommonJS when a machine has only the runtime this repo pins.
JS="$(command -v node || command -v bun || true)"
[ -n "$JS" ] || die "no node and no bun on PATH — a check that cannot run is red, not green"

cd "$REPO"
[ -f "$RUN/findings.json" ] || die "$RUN/findings.json is missing — this milestone's audit was never written"
[ -f "$RUN/REPORT.md" ] || die "$RUN/REPORT.md is missing — findings without a report are not an audit"

# The structural check is the skill's own, never a reimplementation of it.
"$JS" skills/ai-security/references/validate-findings.cjs "$RUN/findings.json" >/dev/null \
  || die "$RUN/findings.json does not validate against references/report-schema.json"

# Every confirmed finding carries its disposition, and the script says how many. An audit that
# reports a high-severity exploit and never says what happened to it is the shape this refuses.
"$JS" -e '
const fs = require("fs");
const findings = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
if (findings.length === 0) { console.error("findings.json is empty — an audit with nothing to say"); process.exit(1); }
const confirmed = findings.filter((f) => f.verdict === "confirmed");
const undecided = confirmed.filter((f) => !/Disposition:/.test(String(f.remediation && f.remediation.strategy)));
if (undecided.length > 0) {
  console.error("confirmed with no disposition (closed or accepted, with reason): " + undecided.map((f) => f.title).join(" | "));
  process.exit(1);
}
console.log("PASS: findings.json valid, REPORT.md present, " + confirmed.length + " confirmed findings each closed or accepted with its reason");
' "$RUN/findings.json"
