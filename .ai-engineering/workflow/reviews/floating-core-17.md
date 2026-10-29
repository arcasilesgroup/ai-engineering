# Checkpoint 17 review

## Goal

Documentation matches the shipped 3.0 CLI and behaviors; the critical doc findings are fixed, the promise table has no broken rows, and a major changeset with a migration guide ships.

## Acceptance

- Every cited CLI command exists.
- Relative documentation links resolve.
- No critical findings remain in the docs audit.
- The promise table matches the product; a major changeset and 3.0 migration guide exist.

## changed_files

- `.changeset/calm-wolves-migrate.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `FILEMAP.md`
- `NOTICE.md`
- `PERMISSIONS.md`
- `README.md`
- `SECURITY.md`
- `docs/blueprint.html`
- `docs/global-carriers.md`
- `docs/recap.html`
- `tests/docs-lint.spec.ts`

## Verify

- `bun test tests/docs-lint.spec.ts`
- `bun test tests/npm-manifest.spec.ts`
- `bun test tests/ceremony-contract.spec.ts`
- `bun run build`
- `bun run typecheck`
- `bun run lint`
- `bun test tests/arch.spec.ts`

## Round 1 findings
- **F1 · MAJOR — CHANGELOG.md:30–32:** The migration guide advertises `ai-eng worktree new <slug> [files...]` and a file-hint manifest, but the CLI rejects extra arguments (`src/commands/worktree.ts:24–28`); tests confirm hints/manifests are removed.
- **F2 · MAJOR — CHANGELOG.md:103,107; docs/blueprint.html:1814–15:** These current-sounding sections still promise `worktree rebase`, fixed `main`/`reviewed_main`, merge-time feature-worktree deletion and refusal on dirty design slots. 3.0 has no rebase; new starts at caller HEAD, merge uses detected base/`reviewed_base` and retains the feature checkout, while dirty design files stay in the source checkout.
- **F3 · MAJOR — PERMISSIONS.md:17:** Comments are documented as selected-membership only, never related items, but `collect-azure.mjs:264–283,587–622` allows recent-comment reads for relation targets; the authorization spec understates the adapter's read scope.

## Verdict
FAIL — 3 MAJOR findings remain, 0 BLOCKER. All seven listed verify commands passed; typecheck and lint emitted existing warnings.

## Round 1 response
- **F1 fixed:** Replaced the unsupported file-hint/manifest claim with the current `worktree new` contract: it starts from the invoking checkout's `HEAD`, accepts a branch name only, and records the detected base for integration.
- **F2 fixed:** Kept the older entries under a historical heading and marked the prior lifecycle as superseded. Current guidance uses native `git rebase <detected base>`, `reviewed_base`, the detected integration base, and a retained feature checkout; dirty design-slot files are reported and stay in the source checkout.
- **F3 fixed:** The permissions row now distinguishes full selected-item discussion reads from recent-window reads for selected items and same-project relation targets; cross-project relation targets remain out of scope.
- **Focused checks:** `tests/docs-lint.spec.ts` 3 pass; `tests/npm-manifest.spec.ts` 4 pass; `tests/ceremony-contract.spec.ts` 4 pass.
- **Report-only docs audit:** Scoped to the corrected F1–F3 claims; 0 critical, 0 warnings, 0 info (0 findings).
