#!/usr/bin/env bash
# Copilot session discovery is delegated to agentsview.
# Keep the hook entrypoint as a fail-open no-op for compatibility.
set -uo pipefail

cat >/dev/null || true
exit 0
