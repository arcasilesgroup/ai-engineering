#!/usr/bin/env bash
# spec-152 W3.T22 (D-152-12) — pinned, checksum-verified runtime-tool installer.
#
# Downloads a single release tarball, verifies its SHA-256 against an
# expected digest BEFORE extracting, then extracts one named binary into a
# destination directory. Centralising the download->verify->extract sequence
# keeps the version+checksum declared once per tool at the call site (DRY) and
# guarantees no tarball is ever unpacked unverified.
#
# Usage:
#   scripts/ci/install_tool.sh <url> <sha256> <dest_dir> <binary_name>
#
# Args:
#   url          Direct download URL of a .tar.gz release asset.
#   sha256       Expected lowercase hex SHA-256 of the downloaded tarball.
#   dest_dir     Directory the binary is extracted into (e.g. /usr/local/bin).
#   binary_name  Name of the single binary member to extract from the tarball.
#
# The expected SHA-256 for each tool is taken from that release's official
# published `*_checksums.txt`; see the call sites in ci-check.yml for the
# source line for each digest.
set -euo pipefail

if [ "$#" -ne 4 ]; then
  echo "::error::install_tool.sh requires 4 args: <url> <sha256> <dest_dir> <binary_name>" >&2
  exit 2
fi

url="$1"
expected_sha256="$2"
dest_dir="$3"
binary_name="$4"

workdir="$(mktemp -d)"
trap 'rm -rf "${workdir}"' EXIT

tarball="${workdir}/tool.tar.gz"

echo "Downloading ${binary_name} from ${url}"
curl --proto '=https' --tlsv1.2 -sSfL "${url}" -o "${tarball}"

echo "Verifying SHA-256 (expected ${expected_sha256})"
printf '%s  %s\n' "${expected_sha256}" "${tarball}" | sha256sum -c -

echo "Extracting ${binary_name} into ${dest_dir}"
sudo tar -xzf "${tarball}" -C "${dest_dir}" "${binary_name}"

echo "Installed ${binary_name} -> ${dest_dir}/${binary_name}"
