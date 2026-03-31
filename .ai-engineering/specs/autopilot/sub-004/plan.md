---
total: 6
completed: 0
---

# Plan: sub-004 Supply Chain Security

```
exports: [SLSA attestation bundle, sbom.json, CHECKSUMS-SHA256.txt as ci-build artifacts and draft release assets]
imports: [ci-build.yml from sub-002, semantic-release tag/draft-release from sub-003]
```

## Plan

### T-4.1: Update ci-build.yml permissions for attestations

Add `id-token: write` and `attestations: write` to the ci-build.yml top-level permissions block. The existing `contents: read` (from sub-002) must be elevated to `contents: write` to allow uploading release assets to the draft release.

**Files**: `.github/workflows/ci-build.yml`
**Done**: ci-build.yml `permissions` block includes `contents: write`, `id-token: write`, and `attestations: write`. Workflow passes `scripts/check_workflow_policy.py` (top-level permissions present).

---

### T-4.2: Add `actions/attest-build-provenance` to ci-build.yml

Add a step in the build job, immediately after `uv build`, that generates SLSA Build provenance for the built artifacts. Must be in the same job as `uv build` (D-097-05). Use `actions/attest-build-provenance` with `subject-path: dist/*`. Gate this step on a version bump having occurred (conditional on semantic-release output from sub-003, e.g., `if: steps.semrel.outputs.released == 'true'`).

The action is under the `actions/` org (first-party), so major-version tag pinning is acceptable per workflow policy. Pin to `v2` (current stable).

```yaml
- name: Attest build provenance
  if: steps.semrel.outputs.released == 'true'
  uses: actions/attest-build-provenance@v2
  with:
    subject-path: dist/*
```

**Files**: `.github/workflows/ci-build.yml`
**Done**: `actions/attest-build-provenance@v2` step exists in the build job after `uv build`, gated on version bump. Step uses `subject-path: dist/*`. Workflow passes actionlint.

---

### T-4.3: Add CycloneDX SBOM generation step

Add a step after `uv build` (and after attestation) to generate a CycloneDX SBOM in JSON format. Use `cyclonedx-bom` CLI installed via pip. Generate SBOM from production dependencies only (not dev deps) to ensure accuracy.

Steps:
1. Install `cyclonedx-bom` via `pip install cyclonedx-bom`.
2. Export production requirements: `uv export --no-dev --frozen > requirements-prod.txt`.
3. Generate SBOM: `cyclonedx-py requirements requirements-prod.txt --output-format json -o sbom.json --spec-version 1.5`.

Gate on version bump (same condition as T-4.2).

```yaml
- name: Generate CycloneDX SBOM
  if: steps.semrel.outputs.released == 'true'
  run: |
    pip install cyclonedx-bom
    uv export --no-dev --frozen > requirements-prod.txt
    cyclonedx-py requirements requirements-prod.txt --output-format json -o sbom.json --spec-version 1.5
```

**Files**: `.github/workflows/ci-build.yml`
**Done**: SBOM generation step produces `sbom.json` in CycloneDX 1.5 JSON format from production-only dependencies. Step is gated on version bump. No third-party GitHub Actions added (CLI tool only). SBOM file is valid CycloneDX JSON.

---

### T-4.4: Add SHA-256 checksum generation step

Add a step after SBOM generation to compute SHA-256 checksums for all build artifacts (wheel, sdist) and the SBOM.

```yaml
- name: Generate SHA-256 checksums
  if: steps.semrel.outputs.released == 'true'
  run: sha256sum dist/* sbom.json > CHECKSUMS-SHA256.txt
```

Gate on version bump.

**Files**: `.github/workflows/ci-build.yml`
**Done**: `CHECKSUMS-SHA256.txt` is generated containing SHA-256 hashes of all files in `dist/` plus `sbom.json`. Step is gated on version bump. File uses standard `sha256sum` output format.

---

### T-4.5: Attach SBOM + checksums to draft GitHub Release

Add a step after checksum generation to upload `sbom.json` and `CHECKSUMS-SHA256.txt` as assets to the draft GitHub Release created by semantic-release (sub-003). Also upload both files as workflow artifacts for sub-005 consumption.

```yaml
- name: Upload supply chain artifacts
  if: steps.semrel.outputs.released == 'true'
  uses: actions/upload-artifact@v7
  with:
    name: supply-chain
    path: |
      sbom.json
      CHECKSUMS-SHA256.txt
    retention-days: 90

- name: Attach to draft release
  if: steps.semrel.outputs.released == 'true'
  env:
    GH_TOKEN: ${{ github.token }}
  run: |
    TAG="${{ steps.semrel.outputs.tag }}"
    gh release upload "$TAG" sbom.json CHECKSUMS-SHA256.txt --clobber
```

The `steps.semrel.outputs.tag` reference depends on the semantic-release step output name established by sub-003. Adjust the step ID reference based on sub-003's actual implementation.

**Files**: `.github/workflows/ci-build.yml`
**Done**: `sbom.json` and `CHECKSUMS-SHA256.txt` are uploaded as workflow artifacts with 90-day retention. Both files are attached to the draft GitHub Release. `gh release upload` uses `--clobber` for idempotency. Step is gated on version bump.

---

### T-4.6: Add attestation verification step

Add a verification step after the attestation is generated to confirm it is valid. This runs `gh attestation verify` against the built artifacts to ensure the attestation bundle is correctly signed and linked.

```yaml
- name: Verify attestation
  if: steps.semrel.outputs.released == 'true'
  env:
    GH_TOKEN: ${{ github.token }}
  run: |
    for f in dist/*; do
      gh attestation verify "$f" --repo "${{ github.repository }}"
    done
```

Gate on version bump. This step provides defense-in-depth: if attestation generation silently fails or produces invalid bundles, verification catches it before the draft release is finalized.

**Files**: `.github/workflows/ci-build.yml`
**Done**: `gh attestation verify` runs against all artifacts in `dist/`. Verification passes for all artifacts. Step is gated on version bump. Verification failure blocks the workflow.

## Confidence

**Overall: HIGH (85%)**

- The implementation is straightforward: 6 sequential steps added to an existing workflow job.
- All tools are well-documented and widely used in the GitHub Actions ecosystem.
- The `actions/attest-build-provenance` action is first-party (GitHub-maintained), reducing version risk.
- Using `cyclonedx-bom` CLI instead of a GitHub Action avoids third-party action SHA-pinning complexity.
- The main uncertainty is the exact step ID and output names from sub-003's semantic-release integration. The plan uses placeholder names (`steps.semrel.outputs.released`, `steps.semrel.outputs.tag`) that must be aligned with sub-003's actual implementation.
- Secondary uncertainty: `cyclonedx-py requirements` mode behavior with uv-exported requirements. May need adjustment if the CLI does not accept the `uv export` format cleanly (pip-compatible requirements.txt format expected, which `uv export` produces).

## Self-Report
[EMPTY -- populated by Phase 4]
