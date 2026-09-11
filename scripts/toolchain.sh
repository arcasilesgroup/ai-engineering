#!/bin/sh
# scripts/toolchain.sh — the CI toolchain, installed the only way this repository is
# allowed to install it. The repository's action policy is `selected`: GitHub-owned
# actions plus nine org patterns, and a workflow that names anything outside that list
# never starts at all — startup_failure, no logs, no jobs. `v2` was blind for ten days
# because `check.yml` named `oven-sh/setup-bun` and `aquasecurity/trivy-action`.
#
# So every tool here is a download whose bytes are checked against the publisher's own
# checksum file: the version says which release we asked for, the sha256 says the bytes
# we got are that release. Version and checksum live here, once, for every workflow.
#
# bun is NOT here: it comes from `oven-sh/setup-bun`, which runs on every OS the build
# matrix needs and is maintained upstream. This script exists for the two tools the
# org's pattern list does not cover.
#
# Usage: sh scripts/toolchain.sh trivy gitleaks
set -eu

TRIVY_VERSION=0.74.0
TRIVY_SHA256=2ae6fe3ee734b7fdf11335663e18c75ea12dccc76062f09f164a3b0f8be4371a
GITLEAKS_VERSION=8.30.0
GITLEAKS_SHA256=79a3ab579b53f71efd634f3aaf7e04a0fa0cf206b7ed434638d1547a2470a66e

if [ "$#" = "0" ]; then
  echo "usage: sh scripts/toolchain.sh trivy|gitleaks [...]" >&2
  exit 2
fi

bin="${HOME}/.local/bin"
mkdir -p "$bin"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

fetch() { # url sha256 outfile
  curl -sSfL -o "$3" "$1"
  echo "$2  $3" | sha256sum -c - >/dev/null || {
    echo "toolchain: sha256 mismatch for $1 — refusing to install it" >&2
    exit 1
  }
  echo "  ✓ $(basename "$3") — sha256 verified"
}

install_trivy() {
  fetch "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" "$TRIVY_SHA256" "$tmp/trivy.tgz"
  tar -xzf "$tmp/trivy.tgz" -C "$tmp" trivy
  install -m 0755 "$tmp/trivy" "$bin/trivy"
  echo "  ✓ trivy ${TRIVY_VERSION} → ${bin}/trivy"
}

install_gitleaks() {
  fetch "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" "$GITLEAKS_SHA256" "$tmp/gitleaks.tgz"
  tar -xzf "$tmp/gitleaks.tgz" -C "$tmp" gitleaks
  install -m 0755 "$tmp/gitleaks" "$bin/gitleaks"
  echo "  ✓ gitleaks ${GITLEAKS_VERSION} → ${bin}/gitleaks"
}

for tool in "$@"; do
  case "$tool" in
    trivy | gitleaks) "install_${tool}" ;;
    *) echo "toolchain: '${tool}' is not one of trivy, gitleaks" >&2; exit 2 ;;
  esac
done

# Later steps find them: GitHub reads this file after the step finishes.
if [ -n "${GITHUB_PATH:-}" ]; then
  echo "$bin" >> "$GITHUB_PATH"
  echo "  ✓ ${bin} appended to \$GITHUB_PATH"
fi
