# Checkpoint ai-triage#8 adversarial review

**Goal:** Publish one current `ai-triage` entry point for GitHub and Azure DevOps, generate the final embedded assets, and pass the complete project verification without private live data.

**Acceptance:** Current docs identify `ai-triage` only; embedded assets contain current skill paths and no retired skill; full feature tests, typecheck, lint and architecture checks pass.

**changed_files:** `README.md`, `CHANGELOG.md`, `FILEMAP.md`, `skills/ai-triage/references/azure-devops.md`, `src/assets.ts`, `scripts/gen-assets.ts`, `tests/generated-payload.test.ts`, `scripts/.embed/ai-triage/scripts/collect-azure.d.mts.txt`, `scripts/.embed/ai-triage/scripts/collect-azure.mjs.txt`, `scripts/.embed/ai-triage/scripts/render-report.d.mts.txt`, `scripts/.embed/ai-triage/scripts/render-report.mjs.txt`, `scripts/.embed/ai-triage/scripts/resolve-target.d.mts.txt`, `scripts/.embed/ai-triage/scripts/resolve-target.mjs.txt`

**Verify:** Checkpoint 8 verify commands in `.ai-engineering/workflow/checkpoints/ai-triage.json`

## Round 1 — 2026-10-07

**Verdict:** PASS
**Findings:** None. **Resolved:** 0. **Open:** 0.

- README lists only `ai-triage`; the retired name appears only in changelog history and as the accurately described replacement target.
- Azure instructions require the already-authenticated `az` CLI plus Azure DevOps extension, prohibit credential persistence, and refuse to guess undocumented route mappings.
- All six embedded `.txt` files byte-match their source modules/declarations. `src/assets.ts` points their original payload keys to `.txt` imports, keeping them as text rather than host modules.
- The added payload test compares each `EMBEDDED` value to its source; the existing copy test checks all `.embed` files against source paths. README/changelog/filemap claims match the skill and payload.
- No live Azure/GitHub calls or source/test edits were made.
