#!/usr/bin/env bash
# spec-113 G-14 / D-113-11: Alpine Docker minimal smoke test.
#
# Runs a real install + doctor pass inside an Alpine 3.x container with
# nothing but ``git``, ``python3``, ``py3-pip``, and ``uv`` installed.
# This is the strictest Linux case (busybox-only with no curl by default)
# so a pass here is the regression-proof guard against the spec-113
# bugs returning.
#
# Gated by ``AIENG_TEST_ALPINE_SMOKE=1`` so the test does NOT add Docker
# overhead to the default CI matrix. Any maintainer can invoke locally:
#
#     AIENG_TEST_ALPINE_SMOKE=1 ./tests/integration/test_install_alpine_smoke.sh
#
# Exit codes:
#   0   smoke succeeded
#   1   smoke failed (install or doctor exited non-zero, or 'install failed'
#       string was found in the output)
#   77  test was skipped because the gate env var is unset
#       (matches POSIX skip-the-test convention)

set -euo pipefail

if [ "${AIENG_TEST_ALPINE_SMOKE:-0}" != "1" ]; then
    echo "Alpine smoke test skipped (set AIENG_TEST_ALPINE_SMOKE=1 to run)"
    exit 77
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: docker not on PATH; cannot run Alpine smoke test" >&2
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CONTAINER_REPO_PATH="/opt/ai-engineering"

# Capture container output so we can grep + display it.
LOG_FILE="$(mktemp -t aieng-alpine-smoke.XXXXXX)"
trap 'rm -f "$LOG_FILE"' EXIT

echo "=== Running ai-eng install + doctor inside alpine:3 ==="
echo "Repo root mounted at $CONTAINER_REPO_PATH (read-only); workspace at /tmp/x"

set +e
docker run --rm \
    --mount "type=bind,src=${REPO_ROOT},dst=${CONTAINER_REPO_PATH},ro" \
    alpine:3 sh -c '
        set -e
        apk add --no-cache git python3 py3-pip
        python3 -m venv /opt/aieng-venv
        . /opt/aieng-venv/bin/activate
        pip install --quiet uv
        # Install ai-engineering from the bind-mounted source tree (read-only).
        # ``--no-deps`` avoids re-resolving the universe inside the container.
        cd '"${CONTAINER_REPO_PATH}"' && uv pip install -e .
        mkdir -p /tmp/x && cd /tmp/x && git init --quiet
        git config user.email tests@example.com
        git config user.name tests
        # Run install + doctor and collect output.
        ai-eng install --non-interactive
        ai-eng doctor
    ' 2>&1 | tee "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
set -e

echo
echo "=== Result ==="
if [ "$EXIT_CODE" -ne 0 ]; then
    echo "FAIL: docker run exited with $EXIT_CODE"
    exit 1
fi

if grep -q "install failed" "$LOG_FILE"; then
    echo "FAIL: log contains 'install failed' string"
    exit 1
fi

if grep -q "Sha256MismatchError" "$LOG_FILE"; then
    echo "FAIL: log contains 'Sha256MismatchError' (the spec-113 root bug)"
    exit 1
fi

echo "PASS: ai-eng install + doctor completed without errors on Alpine"
exit 0
