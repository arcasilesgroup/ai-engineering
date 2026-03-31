---
id: sub-004
parent: spec-097
title: "Supply Chain Security"
status: planning
files: [".github/workflows/ci-build.yml", "scripts/check_workflow_policy.py"]
depends_on: ["sub-002"]
---

# Sub-Spec 004: Supply Chain Security

## Scope

Add SLSA Build provenance via `actions/attest-build-provenance` (same job as `uv build`), CycloneDX SBOM generation, and SHA-256 checksum generation to ci-build.yml. Attach SBOM and checksums to draft GitHub Release. Verify attestation with `gh attestation verify`. Covers spec-097 Phase 4 and decision D-097-05.

## Exploration

### Existing Files

**`.github/workflows/ci-build.yml`** -- Does not exist yet. Will be created by sub-002 (Workflow Architecture Split). Based on the parent spec and sub-002 scope, ci-build.yml will:
- Trigger via `workflow_run` on ci-check success on main branch
- Check out using `github.event.workflow_run.head_sha` for exact commit tracking
- Run `uv build` to produce wheel + sdist in `dist/`
- Upload `dist/` as artifact with 90-day retention
- Have top-level `permissions: contents: read`
- Sub-003 will add semantic-release integration (version bump, tag, draft GitHub Release) to this same workflow

Sub-004 adds supply chain security steps to the build job in ci-build.yml, after `uv build` and in the same job (per D-097-05).

**`.github/workflows/ci.yml`** -- Current monolith (reference). The `build` job (lines 578-611) shows the pattern:
- Runs `uv build` then uploads `dist/` via `actions/upload-artifact@v7`
- Has `needs:` on all validation jobs
- Top-level permissions: `contents: read`

**`.github/workflows/release.yml`** -- Current release workflow (reference for release asset attachment pattern). Uses `gh release create` with `dist/*` as positional arguments. Sub-005 will rewrite this, but sub-004 needs to attach SBOM and checksums to the draft release created by semantic-release (sub-003).

**`pyproject.toml`** -- Build system uses `hatchling>=1.25.0`. Dependencies: typer, pyyaml, pydantic, keyring, rich, questionary, ruamel-yaml. Dev deps: pytest, ruff, ty, pip-audit, etc. The dependency list feeds SBOM generation.

**`uv.lock`** -- Lock file with full transitive dependency graph (version 1, revision 3). Lists all resolved packages with exact versions. CycloneDX SBOM generation will use this for accurate dependency enumeration.

**`scripts/check_workflow_policy.py`** -- Enforces workflow policies: no `pull_request_target`, top-level permissions, job timeouts, concurrency for PR workflows, SHA-pinning for third-party actions. Currently `_FIRST_PARTY_PREFIXES = ("actions/",)`. The parent spec (Phase 1) calls for adding `CycloneDX/*` to the allowlist. However, this is sub-001's responsibility. Sub-004 must SHA-pin any CycloneDX actions to pass the current policy check.

### Patterns to Follow

**SLSA Build Attestation (`actions/attest-build-provenance`)**:
- Must run in the same job that executes `uv build` (D-097-05). This ensures the provenance signature covers the exact artifacts produced.
- Requires `id-token: write` and `attestations: write` permissions at job or workflow level.
- The action takes `subject-path` pointing to the built artifacts (e.g., `dist/*`).
- Produces a Sigstore-signed attestation bundle linked to the OIDC identity of the GitHub Actions runner.
- `actions/attest-build-provenance` is under the `actions/` org, so it passes the current `_FIRST_PARTY_PREFIXES` policy without SHA pinning. However, best practice is to pin to a specific version tag for reproducibility.
- Verification: `gh attestation verify <artifact> --repo OWNER/REPO`

**CycloneDX SBOM Generation**:
- The parent spec references `CycloneDX/cyclonedx-python` (the Python-native CLI tool).
- The security skill references `cdxgen` (OWASP CycloneDX Generator), but for CI pipeline use the Python-specific tool is more appropriate since it directly reads `pyproject.toml` and `uv.lock`.
- Two approaches:
  1. **`cyclonedx-py`** (pip-installable): `pip install cyclonedx-bom && cyclonedx-py environment --output-format json -o sbom.json` -- generates SBOM from the installed environment.
  2. **CycloneDX GitHub Action**: `CycloneDX/gh-python-generate-sbom` -- a GitHub Action wrapper. However, this is a third-party action that must be SHA-pinned per workflow policy.
- Recommended: Install `cyclonedx-bom` via `uv tool install` and run `cyclonedx-py` directly. This avoids adding a third-party GitHub Action dependency and keeps the SBOM generation self-contained.
- Alternative: use `pip install cyclonedx-bom` in a run step. Simpler, no action dependency.
- Output format: CycloneDX JSON (spec version 1.5+), filename `sbom.json`.

**SHA-256 Checksum Generation**:
- Standard pattern: `sha256sum dist/* > CHECKSUMS-SHA256.txt`
- This is a pure shell command, no action needed.
- The file lists each artifact with its SHA-256 hash for integrity verification.

**Draft Release Asset Attachment**:
- Sub-003 integrates semantic-release which creates a draft GitHub Release with a tag.
- Sub-004 must upload SBOM and checksums as additional release assets to this draft release.
- Pattern: `gh release upload <tag> sbom.json CHECKSUMS-SHA256.txt --clobber`
- Requires `contents: write` permission.

### Dependencies Map

- **ci-build.yml** is the only file modified by sub-004.
- **Permissions required**: `id-token: write` (for OIDC-based attestation signing), `attestations: write` (for storing attestation bundles), `contents: write` (for uploading release assets to draft release).
- **Sub-002 dependency**: ci-build.yml must exist with the `uv build` job before sub-004 can add steps.
- **Sub-003 interaction**: semantic-release (sub-003) creates the tag and draft release. Sub-004's release asset upload step must reference the tag created by semantic-release. The tag is available as a git ref after semantic-release runs. Sub-004's steps should be conditional on a version bump having occurred (same condition sub-003 uses).
- **Sub-005 dependency**: sub-005 (release pipeline redesign) depends on sub-004. It will promote the draft release to published and may attach additional assets. Sub-004 must ensure SBOM and checksums are attached to the draft release before sub-005 runs.
- **check_workflow_policy.py**: The `actions/attest-build-provenance` action is under `actions/` prefix (first-party), so no SHA-pinning is required by current policy. Any `CycloneDX/*` action would require SHA-pinning unless sub-001 updates `_FIRST_PARTY_PREFIXES` first. Using `cyclonedx-bom` CLI avoids this entirely.
- **No new Python dependencies**: `cyclonedx-bom` is installed ephemerally in CI (not added to pyproject.toml dev deps).

### Risks

**R-004-1: Attestation action version compatibility**. `actions/attest-build-provenance` is relatively new (GA in 2024). Breaking changes in major versions could fail silently. **Mitigation**: Pin to a specific version tag (e.g., `v2`). The action is first-party (`actions/` org) so major-version tags are acceptable per workflow policy.

**R-004-2: CycloneDX tool installation time**. Installing `cyclonedx-bom` adds time to the build job. **Mitigation**: Expected < 30 seconds. The tool is lightweight. Using `uv tool install` or `pip install` is faster than a separate GitHub Action with its own setup overhead.

**R-004-3: SBOM accuracy**. The SBOM must reflect the actual dependencies of the built artifact, not the dev environment. If `cyclonedx-py` is run against the full environment (including dev deps), the SBOM will include test tools. **Mitigation**: Generate SBOM from a production-only install (`uv sync --no-dev` before SBOM generation, or use `cyclonedx-py requirements` mode with exported requirements). Alternatively, run `cyclonedx-py environment` after a clean `uv sync --no-dev` install.

**R-004-4: Draft release may not exist**. If semantic-release determines no version bump, no draft release exists, and the `gh release upload` step would fail. **Mitigation**: Gate SBOM/checksum upload steps on the same condition that semantic-release uses to determine a bump occurred. Use the output from the semantic-release step (e.g., `steps.semrel.outputs.released == 'true'`).

**R-004-5: `sha256sum` availability**. `sha256sum` is available on Ubuntu runners but may differ on other OS. **Mitigation**: ci-build runs on `ubuntu-latest` only, so this is not a concern. The command is part of GNU coreutils.

**R-004-6: Attestation verification requires `gh` CLI auth**. `gh attestation verify` needs a GitHub token. **Mitigation**: The `GITHUB_TOKEN` is automatically available in GitHub Actions. Add verification as a documentation step or a separate verification job that runs after the build job.
