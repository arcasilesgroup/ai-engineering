# Framework Helm Stack Standards

## Update Metadata

- Rationale: establish Helm chart patterns for Kubernetes application packaging and deployment.
- Expected gain: consistent Helm chart quality, versioning, and testing standards.
- Potential impact: Kubernetes deployments get enforceable chart structure, security, and testing patterns.

## Stack Scope

- Primary format: Helm 3 charts (YAML + Go templates).
- Supporting formats: YAML, JSON, Markdown.
- Toolchain baseline: `helm` 3.x, `helmfile` (optional), `kubectl`.
- Distribution: OCI registry, Helm repository (ChartMuseum, Harbor).

## Required Tooling

- Package: `helm package`, `helm push` (OCI).
- Lint: `helm lint`, `yamllint`.
- Template validation: `helm template` + `kubeconform` (schema validation).
- Test: `helm test`, `ct` (chart-testing).
- Security: `trivy` (config scan), `kubesec`, `gitleaks` (secret detection).

## Minimum Gate Set

- Pre-commit: `helm lint`, `yamllint`, `gitleaks`.
- Pre-push: `helm template | kubeconform`, `ct lint`, `trivy config .`.

## Quality Baseline

- `Chart.yaml` with complete metadata: name, version, appVersion, description, maintainers.
- All values documented in `values.yaml` with comments.
- `README.md` generated from values (via `helm-docs`).
- Semantic versioning for chart version.

## Chart Patterns

- **Structure**: `Chart.yaml`, `values.yaml`, `templates/`, `tests/`, `README.md`.
- **Values**: sensible defaults. No required values without documentation.
- **Templates**: use `_helpers.tpl` for reusable template fragments.
- **Labels**: standard Kubernetes labels (`app.kubernetes.io/*`).
- **Resource limits**: always define requests and limits.
- **Security contexts**: `runAsNonRoot: true`, drop all capabilities, read-only root filesystem.
- **Health checks**: liveness and readiness probes on all containers.
- **Secrets**: reference external secret managers (External Secrets Operator, Sealed Secrets). Never embed secrets in values.

## Testing Patterns

- Lint tests: `ct lint` validates chart structure and values.
- Template tests: `helm template` + snapshot comparison.
- Integration tests: `ct install` in ephemeral cluster (kind, k3d).
- Naming: test pods prefixed with chart name.

## Update Contract

This file is framework-managed and may be updated by framework releases.
