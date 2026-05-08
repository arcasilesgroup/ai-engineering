# Batch Mode (`all`)

When `$ARGUMENTS` is `all`:

1. List skills from `.claude/skills/` in priority order:
   - **Tier 1 workflow**: plan, dispatch, review, verify, commit, pr, code, test.
   - **Tier 2 enterprise**: security, governance, pipeline, docs, release-gate, debug.
   - **Tier 3 meta/teaching**: create, learn, explain, guide, instinct.
   - **Tier 4 specialized**: everything else.
2. Run Phases 1-6 per skill; re-read LESSONS.md between skills (previous improvements may update it).
3. After all skills: run the full test suite and produce a summary:

   ```
   ## Batch Evolution Summary
   | Skill | Before | After | Delta | Key Change |
   |-------|--------|-------|-------|-----------|
   ```

4. Rate limits are real. If you hit them, save progress and tell the user which skills are done and which remain. Use `--dry-run` first to preview changes without running evals.
