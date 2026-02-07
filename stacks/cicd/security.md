# CI/CD Security Standards

These standards govern how an AI coding assistant handles security in CI/CD pipelines. Security is not optional. Every pipeline must implement these controls.

---

## Secrets Management

### Rules

- Never echo, print, or log secrets in pipeline output.
- Never pass secrets as command-line arguments. They appear in process listings. Use environment variables instead.
- Never commit secrets to version control, even in encrypted form (unless using a dedicated tool like SOPS or sealed secrets with proper key management).
- Use the platform's built-in secret masking, but do not rely on it as the sole protection.
- Rotate secrets on a regular schedule (at minimum quarterly, immediately if compromised).
- Use short-lived credentials whenever possible. Prefer OIDC tokens over stored secrets.

### Platform-Specific Secret Handling

```yaml
# GitHub Actions: Secrets are masked automatically
- name: Deploy
  run: ./deploy.sh
  env:
    API_KEY: ${{ secrets.API_KEY }}  # Passed as env var, not CLI argument

# Bad: Secret as CLI argument (visible in process listings)
- run: ./deploy.sh --api-key=${{ secrets.API_KEY }}
```

```yaml
# Azure Pipelines: Mark custom variables as secret
variables:
  - name: mySecret
    value: $(fetchedSecret)

steps:
  - script: |
      echo "##vso[task.setvariable variable=MASKED_SECRET;issecret=true]$(curl -s https://vault/secret)"
    displayName: 'Fetch and mask secret'
```

### Secret Scanning in Pipelines

- Run secret detection tools (gitleaks, truffleHog, detect-secrets) in CI to catch accidentally committed secrets.
- Block merges if secrets are detected.

```yaml
- name: Scan for secrets
  uses: gitleaks/gitleaks-action@v2
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## OIDC Authentication

Use OpenID Connect (OIDC) to authenticate with cloud providers. OIDC issues short-lived tokens scoped to a specific workflow run, eliminating the need for stored credentials.

### GitHub Actions OIDC

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write   # Required for OIDC token
      contents: read
    steps:
      # AWS
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-deploy
          aws-region: us-east-1

      # Azure
      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      # GCP
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: 'projects/123/locations/global/workloadIdentityPools/github/providers/github'
          service_account: 'deploy@my-project.iam.gserviceaccount.com'
```

### Azure Pipelines OIDC

Use workload identity federation service connections. Configure these in Azure DevOps project settings.

### OIDC Rules

- Configure the cloud provider's trust policy to restrict which repositories, branches, and environments can assume the role.
- Use separate OIDC roles per environment (staging, production) with different permission levels.
- Audit OIDC role usage through cloud provider logging (CloudTrail, Azure Activity Log).

---

## Least Privilege Principle

Every job, step, and service connection must have the minimum permissions required.

### GitHub Actions Permissions

```yaml
# Set restrictive defaults at the workflow level
permissions:
  contents: read

jobs:
  test:
    permissions:
      contents: read    # Only read access needed
    # ...

  deploy:
    permissions:
      contents: read
      id-token: write   # OIDC authentication
    # ...

  release:
    permissions:
      contents: write   # Create releases
      packages: write   # Publish packages
    # ...
```

### Azure Pipelines Permissions

- Restrict pipeline access to specific repositories, service connections, and variable groups.
- Use environment-level permissions to control who can approve deployments.
- Audit pipeline permissions regularly.

### Permission Rules

- Never use `permissions: write-all` or leave permissions unspecified (which grants broad defaults).
- Declare permissions at the job level, not just the workflow level, for finer control.
- Review and minimize permissions during every pipeline change.

---

## Supply Chain Security

### Pinned Versions

Pin all external dependencies to immutable references.

```yaml
# GitHub Actions: Pin to full SHA
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1
- uses: actions/setup-node@60edb5dd545a775178f52524783378180af0d1f8 # v4.0.2

# Docker: Pin to digest
FROM node:20-alpine@sha256:abc123...

# Terraform: Pin provider versions
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 3.85.0"  # Exact version, not range
    }
  }
}
```

### Dependency Verification

- Use lock files for every package manager (package-lock.json, poetry.lock, go.sum).
- Enable integrity checking (`npm ci` verifies checksums against package-lock.json).
- Review dependency updates before merging. Do not auto-merge major version bumps.

### SLSA Framework

Work toward SLSA (Supply-chain Levels for Software Artifacts) compliance:

- **SLSA 1**: Document the build process.
- **SLSA 2**: Use a hosted build service with generated provenance.
- **SLSA 3**: Use a hardened build platform with non-falsifiable provenance.

```yaml
# Generate SLSA provenance for container images
- name: Generate SLSA provenance
  uses: slsa-framework/slsa-github-generator/.github/workflows/generator_container_slsa3.yml@v2.0.0
  with:
    image: registry.example.com/myapp
    digest: ${{ steps.build.outputs.digest }}
```

### Software Bill of Materials (SBOM)

Generate SBOMs for every release artifact.

```yaml
- name: Generate SBOM
  uses: anchore/sbom-action@v0
  with:
    artifact-name: sbom.spdx.json
    output-file: sbom.spdx.json
```

---

## Dependency Scanning

Scan dependencies for known vulnerabilities in every CI run.

```yaml
# Node.js
- name: Audit dependencies
  run: npm audit --audit-level=high

# Python
- name: Safety check
  run: pip install safety && safety check

# Multi-language with Trivy
- name: Dependency scan
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: 'fs'
    scan-ref: '.'
    severity: 'HIGH,CRITICAL'
    exit-code: '1'
```

### Dependency Scanning Rules

- Fail the pipeline on high or critical vulnerabilities.
- Allow medium and low vulnerabilities with a time-boxed remediation plan.
- Scan on every PR and on a nightly schedule (to catch newly disclosed vulnerabilities in existing dependencies).
- Use Dependabot or Renovate to automate dependency update PRs.

---

## SAST and DAST Integration

### Static Application Security Testing (SAST)

Run SAST tools to find security issues in source code.

```yaml
# CodeQL (GitHub native)
- name: Initialize CodeQL
  uses: github/codeql-action/init@v3
  with:
    languages: javascript, python

- name: Perform CodeQL analysis
  uses: github/codeql-action/analyze@v3

# Semgrep
- name: Semgrep scan
  uses: semgrep/semgrep-action@v1
  with:
    config: >-
      p/security-audit
      p/secrets
```

### Dynamic Application Security Testing (DAST)

Run DAST tools against deployed preview or staging environments.

```yaml
- name: DAST scan with ZAP
  uses: zaproxy/action-full-scan@v0.10.0
  with:
    target: 'https://staging.example.com'
    rules_file_name: 'zap-rules.tsv'
    allow_issue_writing: false
```

### Rules

- Run SAST on every PR. It is fast and catches issues early.
- Run DAST on staging deployments. It requires a running application.
- Never skip security scans, even for "minor" changes.
- Configure security tools to fail the build on high-severity findings.
- Triage and track security findings. Do not let them accumulate.

---

## Container Scanning

Scan container images for OS and application vulnerabilities before pushing to a registry.

```yaml
# Trivy container scan
- name: Scan container image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: 'myapp:${{ github.sha }}'
    format: 'sarif'
    output: 'trivy-results.sarif'
    severity: 'HIGH,CRITICAL'
    exit-code: '1'

- name: Upload scan results
  uses: github/codeql-action/upload-sarif@v3
  if: always()
  with:
    sarif_file: 'trivy-results.sarif'
```

### Container Security Rules

- Scan every image before pushing to a registry.
- Use minimal base images (Alpine, distroless) to reduce the attack surface.
- Do not run containers as root. Create and use a non-root user.
- Do not include package managers, shells, or build tools in production images.
- Rebuild and rescan images regularly to pick up newly disclosed base image vulnerabilities.

---

## Signed Commits and Artifacts

### Commit Signing

- Require signed commits on protected branches when the team supports GPG or SSH signing.
- Verify commit signatures in CI before running the pipeline.

```yaml
# Verify commit signatures
- name: Verify commit signature
  run: |
    git verify-commit HEAD || {
      echo "Commit is not signed or signature is invalid"
      exit 1
    }
```

### Artifact Signing

- Sign container images with cosign (Sigstore).
- Sign release binaries with GPG or Sigstore.
- Verify signatures during deployment.

```yaml
# Sign container image with cosign
- name: Sign image
  run: |
    cosign sign --yes \
      --key env://COSIGN_PRIVATE_KEY \
      registry.example.com/myapp@${{ steps.build.outputs.digest }}
  env:
    COSIGN_PRIVATE_KEY: ${{ secrets.COSIGN_PRIVATE_KEY }}

# Verify signature during deployment
- name: Verify image signature
  run: |
    cosign verify \
      --key env://COSIGN_PUBLIC_KEY \
      registry.example.com/myapp@${{ steps.build.outputs.digest }}
```

---

## Branch Protection Enforcement

Configure and verify branch protection rules programmatically.

### Required Protections for Main Branch

- Require status checks to pass before merging (CI must pass).
- Require at least one approving review (two for high-risk repositories).
- Require branches to be up to date with the base branch before merging.
- Require conversation resolution before merging.
- Disallow force pushes.
- Disallow branch deletion.
- Require signed commits (if the team supports it).

### Verify Branch Protection in CI

```yaml
- name: Verify branch protection
  run: |
    PROTECTION=$(gh api repos/${{ github.repository }}/branches/main/protection 2>&1)
    if echo "$PROTECTION" | grep -q "Branch not protected"; then
      echo "ERROR: Main branch is not protected"
      exit 1
    fi
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## Audit Logging

### What to Log

- Every deployment: who triggered it, what was deployed, which environment, success or failure.
- Every approval: who approved, when, what they approved.
- Every secret access: which pipeline accessed which secret.
- Every infrastructure change: what changed, who triggered it.

### How to Log

- Use the CI/CD platform's built-in audit logging (GitHub Audit Log, Azure DevOps Audit).
- Forward audit logs to a centralized logging system (SIEM).
- Retain audit logs for at least one year.
- Set up alerts for anomalous activity (deployments outside business hours, deployments by unknown actors, repeated failures).

---

## Runner Security

### Ephemeral Runners

- Use ephemeral runners that are provisioned fresh for each job and destroyed afterward.
- Never reuse runner environments across jobs from different repositories.
- Use VM-based isolation, not container-based, for untrusted workloads.

### Runner Hardening

- Keep runner OS and software up to date.
- Do not install unnecessary tools or software on runners.
- Do not store credentials on runners. Use OIDC or platform secret injection.
- Restrict network access from runners to only the services they need.
- Monitor runner resource usage for anomalies (crypto mining, data exfiltration).

### Self-Hosted Runner Rules

- Never use self-hosted runners for public repositories. Malicious PRs can execute arbitrary code on your infrastructure.
- Use runner groups to restrict which repositories and workflows can use which runners.
- Rotate runner registration tokens regularly.
- Use just-in-time (JIT) runner registration where supported.

```yaml
# GitHub Actions: Ephemeral self-hosted runner
# Configure in runner settings: --ephemeral flag
runs-on: [self-hosted, linux, ephemeral]
```

---

## Security Checklist for Pipeline Reviews

When reviewing a pipeline, verify the following:

- [ ] Permissions are set to the minimum required at the job level.
- [ ] All third-party actions are pinned to full commit SHAs.
- [ ] Secrets are passed as environment variables, never as command-line arguments.
- [ ] No secrets are echoed, logged, or written to artifacts.
- [ ] OIDC is used for cloud authentication where supported.
- [ ] Dependency scanning runs on every PR.
- [ ] SAST runs on every PR.
- [ ] Container images are scanned before being pushed to a registry.
- [ ] Branch protection rules are configured and enforced.
- [ ] Timeouts are set on every job.
- [ ] Concurrency controls prevent duplicate runs.
- [ ] Artifacts have appropriate retention periods.
- [ ] Self-hosted runners (if any) are ephemeral and hardened.
