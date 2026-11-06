---
"ai-engineering": minor
---

Production readiness: the installed command starts with Bun (no Node needed) and a smoke test installs the real packed tarball; the full test suite runs on Linux, macOS and Windows; a release verifies the exact dispatched commit, packs once, publishes that same tarball and ships a runtime-only CycloneDX SBOM; publication requires an annotated tag signed by an allowlisted key and verified redistribution rights. Windows fixes close fail-open paths in the hook chain and self-protect, and the guards now deny shell text they cannot read.
