---
name: build
description: "Write code across all supported stacks following standards: implement features, write tests, validate."
metadata:
  version: 2.0.0
  tags: [implementation, code, multi-stack, features]
  ai-engineering:
    scope: read-write
    token_estimate: 800
---

# Build

## Purpose

Core implementation skill for writing code across all 20 supported stacks. Implements features, writes tests, and validates against stack standards. The primary "write code" skill invoked by the build agent.

## Trigger

- Command: `/ai:build`
- Context: implementation tasks requiring code changes across any stack.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"build"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## Procedure

1. **Read context** -- understand the change: spec/task link, affected modules.
2. **Detect stack** -- identify technology from project files, load applicable standards.
3. **Design** -- propose approach with trade-off analysis before writing code.
4. **Implement** -- write code following stack standards and quality baselines.
5. **Test** -- write or update tests for new/changed behavior.
6. **Validate** -- run post-edit validation per stack:
   - Python: `ruff check` + `ruff format --check`
   - .NET: `dotnet build --no-restore` + `dotnet format --verify-no-changes`
   - TypeScript: `tsc --noEmit` + lint
   - Rust: `cargo check` + `cargo clippy`
   - Terraform: `terraform fmt -check` + `terraform validate`
7. **Document** -- explain implementation decisions.

## When NOT to Use

- **Bug fixes** -- use `debug` for systematic diagnosis.
- **Restructuring** -- use `refactor` for structural changes.
- **Reducing complexity** -- use `code-simplifier`.
