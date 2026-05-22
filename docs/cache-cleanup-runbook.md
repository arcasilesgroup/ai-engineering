# GitHub Actions Cache Cleanup Runbook

> Operator runbook for listing, deleting, and rotating GitHub Actions
> caches on this repo. Spec-152 (D-152-09/10/11/25), Wave 5 (T-36). Pairs
> with the cache trust-tier policy in
> [`scripts/check_workflow_policy.py`](../scripts/check_workflow_policy.py)
> (`classify_cache_usage`) and the schema test
> [`tests/integration/test_ci_cache_key_schema.py`](../tests/integration/test_ci_cache_key_schema.py).

## When to use this runbook

Run a cache cleanup when any of the following is true:

1. **Suspected cache poisoning** — a PR (especially from a fork), a
   compromised dependency, or an untrusted `workflow_run` may have written
   attacker-controlled bytes into a restorable cache. Caches are mutable and
   are restored by later jobs, so a poisoned entry can taint a build.
2. **Post trust-tier key migration** — Wave 3 (D-152-09) retyped every cache
   key with a `pr-` / `main-` trust-tier prefix. Caches written under the
   **old, untiered key shapes** are now orphaned (never restored) and should
   be purged so they do not consume the repo's 10 GiB cache quota:
   - `gate-cache-${{ runner.os }}-…` (old; now `gate-cache-${tier}-${os}-…`)
   - `semgrep-packs-${{ runner.os }}-…` (old; now `semgrep-packs-${tier}-${os}-…`)
3. **Quota pressure** — the repo is at/near the GitHub Actions cache limit and
   evictions are thrashing (oldest-first eviction degrades hit rate).
4. **Stale tool pin** — a runtime-tool version pin changed (e.g. the semgrep
   CLI in the `semgrep-packs-…-<version>` key) and old packs linger.

## Ownership

| Surface | Owner |
|---------|-------|
| This runbook + cache policy | `@arcasilesgroup/maintainers` |
| The caches themselves (`ci-check.yml` `gate-cache-*`, `security` job `semgrep-packs-*`) | `@arcasilesgroup/maintainers` |
| Branch protection / required `CI Result` | `@arcasilesgroup/maintainers` (operator-applied) |

Cache deletion is a maintainer action. It is safe — caches are a
performance optimization, not a source of truth; a cold rebuild repopulates
them on the next run.

## Prerequisites

- `gh` (GitHub CLI) authenticated with repo access:
  ```bash
  gh auth status
  ```
- The cache extension ships with current `gh`; `gh cache --help` confirms it.
- Permissions: deleting a cache requires write access to the repository.

## 1. List caches

```bash
# All caches, newest first, with key + size + last-used.
gh cache list --repo arcasilesgroup/ai-engineering --limit 100

# Sort by size to find the heaviest entries.
gh cache list --repo arcasilesgroup/ai-engineering --sort size_in_bytes --order desc

# Only the stale untiered keys left over from the Wave 3 migration.
gh cache list --repo arcasilesgroup/ai-engineering --key gate-cache- --limit 100
gh cache list --repo arcasilesgroup/ai-engineering --key semgrep-packs- --limit 100
```

`gh cache list` prints the cache `ID`, `KEY`, `SIZE`, `CREATED`, and
`ACCESSED` columns. Note the IDs (or keys) you intend to delete.

## 2. Delete caches

```bash
# Delete one cache by ID (from `gh cache list`).
gh cache delete <CACHE_ID> --repo arcasilesgroup/ai-engineering

# Delete by exact key.
gh cache delete 'gate-cache-pr-Linux-<hash>-<sha>' --repo arcasilesgroup/ai-engineering

# Nuke ALL caches (use after a confirmed poisoning, or to force a clean
# trust-tier baseline). Destructive — every cache repopulates cold next run.
gh cache delete --all --repo arcasilesgroup/ai-engineering
```

### Targeted purge of the orphaned (pre-Wave-3) keys

After the trust-tier migration, delete only the untiered leftovers and keep
the live tiered caches warm:

```bash
# Dry-run first: list what matches the old shapes.
gh cache list --repo arcasilesgroup/ai-engineering --key gate-cache- --json id,key \
  --jq '.[] | select(.key | test("gate-cache-(Linux|macOS|Windows)-")) | "\(.id)\t\(.key)"'

# Then delete each matched ID:
gh cache list --repo arcasilesgroup/ai-engineering --key gate-cache- --json id,key \
  --jq '.[] | select(.key | test("gate-cache-(Linux|macOS|Windows)-")) | .id' \
  | while read -r id; do
      gh cache delete "$id" --repo arcasilesgroup/ai-engineering
    done
```

> The selector `test("gate-cache-(Linux|macOS|Windows)-")` matches the OLD
> shape `gate-cache-<os>-…`. The NEW shape interposes a tier token —
> `gate-cache-<pr|main>-<os>-…` — so it does **not** match and the live
> caches are preserved. Adjust the OS tokens to match `runner.os` values.

## 3. Rotate caches (force a clean baseline)

GitHub Actions caches are **immutable per key** and evicted oldest-first.
The supported "rotation" mechanism is to change the key so a fresh entry is
written and the old one ages out (or is deleted explicitly):

1. **Automatic rotation** already happens for content-addressed keys: the
   `gate-cache-…-${{ hashFiles('pyproject.toml', '.ruff.toml', '.gitleaks.toml') }}`
   segment changes whenever those files change, writing a new cache.
2. **Tool-pin rotation**: the `semgrep-packs-…-<version>` key embeds the
   pinned semgrep CLI version, so bumping the pin (in `ci-check.yml`'s
   `security` job) rotates the pack cache cleanly (D-141-05).
3. **Forced rotation after poisoning**: delete the affected caches (step 2),
   then re-run the workflow on a trusted ref (push to `main`) so the cache is
   repopulated from a trusted build, not a fork PR.

## 4. Post-incident verification

After a poisoning cleanup:

1. Confirm the caches are gone: `gh cache list --repo arcasilesgroup/ai-engineering`.
2. Re-run the affected workflow on `main` (trusted context) to repopulate from
   a clean build:
   ```bash
   gh workflow run "CI Check" --repo arcasilesgroup/ai-engineering --ref main
   ```
3. Verify the cache trust-tier policy still holds (no privileged-context cache):
   ```bash
   uv run python scripts/check_workflow_policy.py
   ```
4. Record the incident + actions taken in the security log and, if a finding
   was risk-accepted, via `ai-eng risk accept --finding-id … `.

## Reference: cache trust model (why tiers exist)

PR/fork jobs and trusted `main`/release jobs must never share a restorable
cache key — a fork PR could otherwise poison a cache that a privileged job
later restores. The Wave 3 migration enforces this by prefixing every key
with a `pr-` / `main-` tier (release jobs run **cold**, D-152-10), and
`classify_cache_usage` rejects any `actions/cache` step (or `setup-*`
composite with `enable-cache: true`) inside a `pull_request_target`,
untrusted `workflow_run`, or `id-token: write` job. This runbook is the
operational complement: when a tier boundary is suspected breached, purge and
rebuild cold.
