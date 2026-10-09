# Checkpoint 9 review

Goal: Read-only discovery scans only configured project roots, lists each discovered repository's Git-registered worktrees using its configured worktree root, and maps explicit Git/checkpoint/lifecycle evidence plus verified pre-worktree approvals to approved lifecycle filters.

Acceptance:
- Discovery scans only canonical configured roots; worktrees appear only when Git registers them to an in-scope repository and respect that repository's configured worktree root.
- Lifecycle labels use matching valid Git/checkpoint evidence; dirty state alone never means active.
- Missing, stale, malformed, detached, prunable or contradictory evidence remains Unknown.
- Closed requires a matching checkpoint on local main, complete gates, Git merge evidence and no registered feature worktree.
- Discovery is read-only, startup/manual refresh only, and partial failures remain visible.

Changed files:
- src/shared-worktree.ts
- src/workspace/discovery.ts
- src/workspace/status.ts
- src/workspace/api.ts
- src/workspace/server.ts
- tests/workspace-discovery.spec.ts
- tests/workspace-server.spec.ts

Verify:
- bun test ./tests/workspace-discovery.spec.ts
- bun test ./tests/workspace-server.spec.ts
- bun test ./tests/worktree-lifecycle.spec.ts
- bun run typecheck
- bun run lint
- bun test ./tests/arch.spec.ts
- bun run build

## Round 1 — Open findings

### CP9-R1-01 · Medium · Canonical-root scan can escape during a symlink swap
- **File:** `/Users/soydachi/repos/arcasilesgroup/ai-engineering.worktrees/worktree-lifecycle-governance/src/workspace/discovery.ts:80`
- **Problem:** The child path is realpathed and checked under `scanRoot`, but recursive traversal later reopens it by pathname. Replacing that directory with a symlink to an outside directory between the check and `readdirSync`/`gitMarker` makes discovery follow the new target and scan outside the configured root.
- **Evidence:** The containment decision is made on `canonicalChild`; subsequent filesystem operations in `findRepositories` use that path again without pinning or revalidating the directory identity.
- **Suggested fix:** Traverse through no-follow directory handles anchored to the checked directory, or otherwise ensure the checked inode remains the one used for all recursive reads.

### CP9-R1-02 · Medium · Stale review evidence still classifies as active
- **File:** `/Users/soydachi/repos/arcasilesgroup/ai-engineering.worktrees/worktree-lifecycle-governance/src/workspace/status.ts:369-414`
- **Problem:** `awaiting-app-review` and `ready-to-merge` accept any feature tip descended from `reviewed_feature`; a later content-changing commit therefore remains `needs-review`/`in-progress` even though the reviewed code is stale. The validator also permits both review SHAs to be absent for `awaiting-app-review`, which is accepted as `needs-review`.
- **Evidence:** These branches only test `isAncestor(reviewedFeature, featureTip)`. The existing lifecycle validation in `/Users/soydachi/repos/arcasilesgroup/ai-engineering.worktrees/worktree-lifecycle-governance/src/shared-worktree.ts:520-525` requires both review SHAs, and its `reviewedFeatureChainProblem` checks that commits after review change only lifecycle metadata.
- **Suggested fix:** Require both review SHAs for app review and apply the reviewed-feature chain/payload checks before returning a lifecycle label; stale or unverifiable review state must be Unknown.

### CP9-R1-03 · Medium · A detached registered worktree can be overwritten by Closed history
- **File:** `/Users/soydachi/repos/arcasilesgroup/ai-engineering.worktrees/worktree-lifecycle-governance/src/workspace/status.ts:434-484`
- **Problem:** Closed-history exclusion matches only `branch === feat/<slug>`. A detached worktree at the configured `<worktreesRoot>/<slug>` has no branch, so it does not block Closed; its earlier Unknown item is then replaced by the Closed item.
- **Evidence:** Detached entries use their directory basename as `slug` in `/Users/soydachi/repos/arcasilesgroup/ai-engineering.worktrees/worktree-lifecycle-governance/src/shared-worktree.ts:119-130`, while the closed check ignores path/slug identity.
- **Suggested fix:** Treat any registered entry identifying the slug/path as live evidence that prevents Closed, and preserve Unknown precedence for detached or prunable entries.

### CP9-R1-04 · Medium · Nested checkpoint JSON can impersonate the canonical checkpoint
- **File:** `/Users/soydachi/repos/arcasilesgroup/ai-engineering.worktrees/worktree-lifecycle-governance/src/workspace/status.ts:513-517`
- **Problem:** Recursive `ls-tree` results are reduced to `basename(path)`, and the parsed record is validated only against that basename. A valid-looking `checkpoints/archive/foo.json` can therefore be accepted as `checkpoints/foo.json` and produce false Closed history without the canonical checkpoint path.
- **Evidence:** `readMainCheckpoint` receives the original nested path but validates only the embedded slug; no check requires the path to equal `.ai-engineering/workflow/checkpoints/<slug>.json`.
- **Suggested fix:** Accept only direct children whose full path exactly matches the slug-derived canonical checkpoint path, and treat duplicate/misplaced records as Unknown.

### CP9-R1-05 · Medium · Explicit refresh drops per-project Git/checkpoint errors
- **File:** `/Users/soydachi/repos/arcasilesgroup/ai-engineering.worktrees/worktree-lifecycle-governance/src/workspace/api.ts:59-65`
- **Problem:** The refresh response serializes only `snapshot.errors`, which contains root-scan errors; Git and checkpoint read failures are held in each `snapshot.projects[].errors` and disappear from this response.
- **Evidence:** `/api/worktrees` and `/api/history` include `project.errors`, but `/api/refresh` returns only project paths plus the global error list, so the caller cannot see partial failures from the refreshed scan in its refresh result.
- **Suggested fix:** Include per-project errors in the refresh response or aggregate them into the response's visible errors.
## Round 2

**Verdict:** FINDINGS

**Resolved:** 4 (F1, F3–F5)
**Withdrawn:** 0
**Arbitrated:** 0

### CP9-R2-01 — Closed history does not validate the reviewed plan payload

**Severity:** Medium
**File:** `src/workspace/status.ts:488-507`

Closed history checks reviewed-SHA ancestry but not whether the current main checkpoint payload still matches `reviewed_feature`. A later main commit can change plan scope while preserving lifecycle metadata, gates, and ancestry, and still be classified closed.

**Suggested fix:** Compare the current main checkpoint payload with the reviewed payload before closing; otherwise return Unknown.

## Fix response

Read and validate the checkpoint at local `reviewed_feature`, then compare its immutable plan payload with local main; lifecycle and gate/runtime fields remain excluded. Missing, malformed, or changed reviewed plans now stay Unknown. Focused discovery tests pass; the ordered CP9 verification stopped at `bun test ./tests/workspace-server.spec.ts`, whose closed-history fixture points `reviewed_feature` to a commit without a checkpoint. That fixture is outside the permitted edit set.

## Round 3

**Verdict:** FINDINGS

**Resolved:** 1 (CP9-R2-01)
**Withdrawn:** 0
**Arbitrated:** 0

### CP9-R3-01 — Plan-level notes are not bound to reviewed payload

**Severity:** Medium
**File:** `src/workspace/status.ts:67-76`

**Problem:** `immutablePlanPayload` omits the top-level `notes` field. A change to plan constraints in `notes` on local main therefore compares equal to the reviewed payload and can still be classified Closed, despite the payload mismatch.

**Evidence:** The CP9 checkpoint metadata contains top-level `notes` with durable constraints (for example, lifecycle-source and local-main-only requirements), and `validateCheckpoint` accepts this field. The comparison copies only the fields enumerated in `PLAN_FIELDS`; U39a exercises changed `summary` and `tasks`, but not `notes`. The current metadata also mixes runtime gate notes into this array, but that does not make the durable plan notes runtime metadata.

**Suggested fix:** Include durable plan notes in the reviewed-payload comparison while excluding any genuinely runtime-only notes, or otherwise classify changed plan notes as Unknown.
