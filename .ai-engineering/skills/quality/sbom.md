# SBOM Generation

## Purpose

Software Bill of Materials generation using CycloneDX across multiple stacks. Produces machine-readable dependency inventories for supply chain transparency, vulnerability tracking, and compliance.

## Trigger

- Command: agent invokes SBOM skill or user requests SBOM generation.
- Context: release preparation, compliance audit, supply chain review, dependency inventory.

## Procedure

1. **Detect active stacks** — read `install-manifest.json` for installed stacks.

2. **Generate per-stack SBOM** — use stack-appropriate CycloneDX tool.
   - Python: `cyclonedx-py environment --output-format json --outfile sbom-python.json`.
   - .NET: `dotnet CycloneDX <project.csproj> --json --output sbom-dotnet.json`.
   - Next.js/Node: `cdxgen -o sbom-nextjs.json`.
   - Alternative (universal): `cdxgen -o sbom.json` (auto-detects stack).

3. **Validate SBOM** — verify generated SBOM is well-formed.
   - Check CycloneDX schema compliance.
   - Verify component count is reasonable (non-empty).
   - Confirm format version (CycloneDX 1.5+ preferred).

4. **Analyze dependencies** — extract key metrics from SBOM.
   - Total direct dependencies count.
   - Total transitive dependencies count.
   - License distribution summary.
   - Flag any unknown or restrictive licenses.

5. **Cross-reference vulnerabilities** — correlate SBOM with known CVEs.
   - Compare components against vulnerability databases.
   - Flag components with known unfixed vulnerabilities.

6. **Report** — structured SBOM delivery.
   - Per-stack SBOM files in CycloneDX JSON format.
   - Summary: component counts, license overview, vulnerability cross-reference.
   - Recommendations for dependency updates or replacements.

## Output Contract

- CycloneDX JSON SBOM file(s) per active stack.
- SBOM summary report with component counts, licenses, and vulnerability status.
- Recommendations for high-risk dependencies.

## Governance Notes

- SBOM generation is not a gate hook — it runs on-demand or in CI/CD pipelines.
- SBOM tools are optional — listed in `manifest.yml` under `tooling.optional.sbom`.
- Generated SBOMs are project-managed artifacts (not framework-managed).
- SBOM should be regenerated for each release.

## References

- `standards/framework/security/owasp-top10-2025.md` — OWASP mapping (A06 vulnerable components).
- `standards/framework/core.md` — supply chain security controls.
- `skills/review/security.md` — dependency vulnerability assessment.
