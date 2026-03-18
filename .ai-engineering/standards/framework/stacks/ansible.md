# Framework Ansible Stack Standards

## Update Metadata

- Rationale: establish Ansible patterns for configuration management and infrastructure automation.
- Expected gain: consistent playbook quality, testing, and security standards.
- Potential impact: Ansible projects get enforceable lint, testing, and secret management patterns.

## Stack Scope

- Primary format: Ansible playbooks and roles (YAML + Jinja2).
- Supporting formats: YAML, INI (inventory), Markdown.
- Toolchain baseline: Ansible 2.15+, `ansible-lint`, `molecule`.
- Distribution: Ansible Galaxy collection, Git repository.

## Required Tooling

- Runner: `ansible-playbook`, `ansible-navigator` (execution environments).
- Lint: `ansible-lint` (configured via `.ansible-lint`).
- Format: `yamllint` (configured via `.yamllint`).
- Test: `molecule` (role testing), `ansible-test` (collection testing).
- Security: `ansible-lint` security rules, `gitleaks` (secret detection).

## Minimum Gate Set

- Pre-commit: `yamllint`, `ansible-lint`, `gitleaks`.
- Pre-push: `molecule test`, `ansible-playbook --syntax-check`.

## Quality Baseline

- All roles documented with `README.md` (generated via `ansible-docs`).
- All variables documented with comments and defaults in `defaults/main.yml`.
- Idempotent playbooks: running twice produces no changes.
- No `command`/`shell` modules when a purpose-built module exists.

## Playbook Patterns

- **Structure**: follow Ansible best practices directory layout (roles, group_vars, host_vars, inventory).
- **Roles**: reusable roles for repeated configurations. One responsibility per role.
- **Variables**: layered variable precedence. Use `defaults/` for overridable values, `vars/` for fixed values.
- **Tags**: tag all tasks for selective execution.
- **Handlers**: use handlers for service restarts. `notify` from tasks, not direct restarts.
- **Secrets**: Ansible Vault for sensitive data. Reference external secret managers when possible.
- **Inventory**: dynamic inventory plugins for cloud (AWS, Azure, GCP). Static inventory for on-premises.

## Testing Patterns

- Syntax check: `ansible-playbook --syntax-check`.
- Lint: `ansible-lint` with strict profile.
- Unit: `molecule` with Docker/Podman driver for role testing.
- Integration: `molecule converge` + `molecule verify` (Testinfra or Ansible assertions).
- Naming: scenario-based molecule scenarios (`default`, `upgrade`, `ha`).

## Update Contract

This file is framework-managed and may be updated by framework releases.
