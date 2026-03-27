# IRRV Evidence Collection Protocol

Canonical reference for evidence-based verification. Loaded by `/ai-verify` in Step 0 and available to any skill or agent that needs to prove claims with commands rather than assumptions.

## Verification Protocol (claim mode)

For every claim, follow IRRV:

**I -- IDENTIFY**: What command proves this claim?
- "Tests pass" -> `uv run pytest tests/ -v`
- "No lint errors" -> `ruff check .`
- "No secrets" -> `gitleaks protect --staged`
- "File exists" -> `ls -la path/to/file`

**R -- RUN**: Execute the FULL command. Not a subset. Not from memory. Fresh execution.

**R -- READ**: Read the FULL output. Check:
- Exit code (0 = success, non-zero = failure)
- Warning lines (even with exit code 0)
- Actual numbers (test count, coverage %, finding count)

**V -- VERIFY**: Does the output CONFIRM the claim?
- If yes: report with evidence (exact command + key output lines)
- If no: report the discrepancy. Do not claim success.

**Forbidden words** (never use these without evidence):
- "should work", "probably fine", "seems to", "looks good"
- "Done!", "Perfect!", "All set!"
- "I believe", "I think", "most likely"
