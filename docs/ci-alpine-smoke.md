# Alpine Docker Smoke Test

Status: optional, gated CI workflow.
Owner: spec-113.

## Purpose

Validates the spec-113 fix for the Linux install regression on the
strictest Linux case: an Alpine Docker minimal image with no `curl`
available out of the box. The smoke test runs a real `ai-eng install`
plus `ai-eng doctor` pass and asserts:

- exit code 0 from both commands;
- no `install failed` line in the combined output;
- no `Sha256MismatchError` in the output (the spec-113 root bug).

If this test passes, every release-binary install pathway (gitleaks, jq,
shellcheck, shfmt, ktlint, checkstyle, google-java-format, composer,
clang-tidy, clang-format, cppcheck) works on the most constrained
Linux runner ai-engineering targets.

## Local invocation

```bash
AIENG_TEST_ALPINE_SMOKE=1 ./tests/integration/test_install_alpine_smoke.sh
```

The script exits with 77 (POSIX "skip") when `AIENG_TEST_ALPINE_SMOKE`
is unset, so the default test runner does not block on Docker
availability. Set the env var to opt in.

The test runs `apk add git python3 py3-pip` inside the container, then
`pip install -e <bind-mounted repo>`, then `ai-eng install
--non-interactive`, then `ai-eng doctor`. The repo is bind-mounted
**read-only** so a hostile install cannot write back to the developer's
working tree.

## CI integration

GitHub Actions example (placeholder; not auto-enrolled into the default
matrix to keep CI time bounded):

```yaml
jobs:
  alpine-smoke:
    name: Alpine smoke (spec-113)
    runs-on: ubuntu-latest
    if: contains(github.event.pull_request.labels.*.name, 'alpine-smoke')
    steps:
      - uses: actions/checkout@v4
      - name: Run Alpine smoke
        env:
          AIENG_TEST_ALPINE_SMOKE: "1"
        run: ./tests/integration/test_install_alpine_smoke.sh
```

## Failure triage

If the smoke test fails, the most likely causes (in order) are:

1. **SHA-pin regression**: a future change reset
   `sha256_pinned=False` to `sha256_pinned=True` for a registry entry
   without populating `expected_sha256`. The audit event log inside the
   container will show `sha_pin_skipped` events stop firing, and the
   `Sha256MismatchError` returns. Check
   `src/ai_engineering/installer/tool_registry.py` for any
   `GitHubReleaseBinaryMechanism(...)` entry that flipped to pinned
   without a real digest.

2. **Driver chain regression**: the curl -> wget -> urllib fallback in
   `src/ai_engineering/installer/mechanisms/__init__.py` short-circuited
   because `wget` was removed from `DRIVER_BINARIES`. Look for a recent
   diff to `src/ai_engineering/installer/user_scope_install.py`.

3. **Hostname allowlist regression**: a new `objects.githubusercontent.com`
   redirect target was added but the allowlist still has only the legacy
   set. Check `_DOWNLOAD_DRIVER_HOSTNAME_ALLOWLIST` in
   `src/ai_engineering/installer/mechanisms/__init__.py`.

4. **Distro detection regression**: a hint that used to recommend `apk add`
   now recommends `brew`/`winget`/`scoop`. Inspect
   `src/ai_engineering/installer/distro.py` and
   `src/ai_engineering/installer/user_scope_install.py:_build_install_hint`.

## Maintenance

The smoke test pins `alpine:3` (rolling tag) so distro updates flow
through automatically. If Alpine ever drops `python3` from the
`apk add` baseline, update the package list in the script.

The test does NOT pin a specific ai-engineering version; it always
installs the bind-mounted source tree. This keeps the smoke valid for
spec branches under development.
