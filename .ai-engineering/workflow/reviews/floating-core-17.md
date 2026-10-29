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

## Round 2 findings
- **F3 · MAJOR (still open) — PERMISSIONS.md:17,20:** “Same-project relation targets” is broader than the adapter: recent reads are limited to direct `Hierarchy-Forward`/`Hierarchy-Reverse` targets, and permit exactly `$top=5, order=desc`; the docs omit both constraints despite denying every other query (`collect-azure.mjs:264–285,406–430,587–622`).
- **F4 · MAJOR — docs/blueprint.html:1818:** `git branch --delete-merged refs/heads/main` is not a Git command. The shipped cleanup skill lists with `git branch --merged "$base_ref"` and deletes with `git branch -d`; it also uses the selected base, not hardcoded `main`. This current-sounding claim is not marked historical.

## Round 2 verdict
FAIL — F1 and F2 resolved; F3 and F4 remain MAJOR. Focused docs, worktree and Azure integration tests passed.

## Round 2 response
- **F3 fixed:** `PERMISSIONS.md` limits recent-comment reads to selected items and their direct, same-project `Hierarchy-Forward`/`Hierarchy-Reverse` targets; the query is exactly `$top=5` and `order=desc`.
- **F4 fixed:** The blueprint now describes base selection from explicit choice or repository configuration, asks once if neither identifies a base, and uses the cleanup skill's merged-branch listing and safe deletion commands instead of the nonexistent command or hardcoded `main`.
- **Focused checks:** `tests/docs-lint.spec.ts`, `tests/triage-azure.integration.spec.ts`, `tests/triage-azure-signals.integration.spec.ts`, and `tests/git-cleanup-pass.spec.ts`: 151 pass, 0 fail.
- **Report-only docs audit:** Scoped to the corrected F3/F4 claims; 0 critical, 0 warnings, 0 info (0 findings).

## Round 3 findings
- **F5 · MAJOR — docs/blueprint.html:1819:** The `ai-pr` section still says it creates a PR branch from local `main` and targets `main`; the shipped skill publishes the current branch from the current checkout/worktree and resolves its base from explicit choice, config, remote default, or forge (`skills/ai-pr/SKILL.md:13–16,29–40`).

## Round 3 verdict
FAIL — F1–F4 resolved; F5 remains MAJOR, 0 BLOCKER. Focused docs, worktree, cleanup, and Azure tests passed.

## Round 3 response
- **F5 fixed:** The blueprint now says `ai-pr` publishes the current checkout/worktree branch without creating or switching branches, resolves the base from the supported precedence, and targets that selected base. The worktree implementation separately creates a branch from the invoking checkout's `HEAD` and uses the detected base for integration.
- **Focused checks:** `bun test ./tests/docs-lint.spec.ts` — 3 pass, 0 fail; `bun test ./tests/ai-pr.spec.ts` — 22 pass, 0 fail.
