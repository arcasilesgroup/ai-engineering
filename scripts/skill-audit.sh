#!/usr/bin/env bash
# scripts/skill-audit.sh -- spec-106 D-106-04 advisory skill audit.
#
# Iterates every .claude/skills/ai-*/SKILL.md and attempts to invoke the
# skill-creator eval rubric via `uv run ai-eng skill eval <path>`. The
# subcommand is not yet implemented (advisory mode in spec-106), so each
# invocation falls back to a record marked `eval-failed-cli-missing`.
#
# Output: audit-report.json (JSON array). Each entry has the canonical
# shape `{skill: <name>, result: {score: <number>, reason: <string>}}`.
# Override the destination path via OUTPUT=... and the score threshold
# via THRESHOLD=...
#
# Mode: advisory only. Always exits 0 -- never blocks CI. Hard-gate
# enforcement is deferred to a future spec when >=90% of skills meet the
# threshold (see spec-106 NG-2).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
THRESHOLD="${THRESHOLD:-80}"
OUTPUT="${OUTPUT:-audit-report.json}"

# Resolve OUTPUT to an absolute path so cwd-relative invocations from
# subprocess fixtures still write to the expected location.
case "$OUTPUT" in
    /*) OUTPUT_PATH="$OUTPUT" ;;
    *)  OUTPUT_PATH="$(pwd)/$OUTPUT" ;;
esac

if ! command -v jq >/dev/null 2>&1; then
    echo "ERROR: jq is required (install via your package manager)." >&2
    exit 1
fi

# Seed the output as an empty JSON array so we can append with jq.
echo "[]" > "$OUTPUT_PATH"

skill_count=0
sub_threshold=()

# Glob the canonical skill directory pattern from REPO_ROOT so the script
# works no matter the caller's cwd.
shopt -s nullglob
for skill in "$REPO_ROOT"/.claude/skills/ai-*/SKILL.md; do
    name="$(basename "$(dirname "$skill")")"
    skill_count=$((skill_count + 1))

    # Attempt the eval subcommand. The `skill eval` verb is not yet wired
    # into the CLI (spec-106 ships advisory only), so fall back gracefully
    # to a stable JSON literal. Future specs that wire the eval CLI will
    # have it parsed here without script changes.
    if eval_output="$(uv run ai-eng skill eval "$skill" --threshold "$THRESHOLD" --json 2>/dev/null)" \
        && [ -n "$eval_output" ] \
        && echo "$eval_output" | jq -e '.score and .reason' >/dev/null 2>&1; then
        result_json="$eval_output"
    else
        result_json='{"score":0,"reason":"eval-failed-cli-missing"}'
    fi

    score="$(echo "$result_json" | jq -r '.score')"
    if awk -v s="$score" -v t="$THRESHOLD" 'BEGIN { exit !(s+0 < t+0) }'; then
        sub_threshold+=("$name")
    fi

    jq --arg n "$name" --argjson r "$result_json" \
        '. + [{"skill": $n, "result": $r}]' \
        "$OUTPUT_PATH" > "$OUTPUT_PATH.tmp"
    mv "$OUTPUT_PATH.tmp" "$OUTPUT_PATH"
done
shopt -u nullglob

echo "Audit complete. ${skill_count} skills audited."
if [ "${#sub_threshold[@]}" -gt 0 ]; then
    echo "Sub-threshold (score < ${THRESHOLD}): ${sub_threshold[*]}"
else
    echo "Sub-threshold (score < ${THRESHOLD}): none"
fi

# Advisory-mode exit: never block CI. Sub-threshold skills are surfaced
# via stdout + audit-report.json for downstream consumption.
exit 0
