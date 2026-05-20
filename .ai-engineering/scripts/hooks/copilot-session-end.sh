#!/usr/bin/env bash
# Copilot session discovery is handled by the host.
# Keep the hook entrypoint as a fail-open no-op.
set -uo pipefail

cat >/dev/null || true
exit 0
