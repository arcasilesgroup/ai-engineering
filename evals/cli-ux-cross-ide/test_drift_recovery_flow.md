---
eval: spec-133-drift-recovery
spec: spec-133
decisions: [D-133-11, D-133-24]
matrix: [python, typescript, rust, csharp, go, java]
---

# Stack Drift Recovery Flow — AI Eval Matrix

This eval simulates the cognitive recovery loop documented in
spec-133 D-133-24. The AI surface (Claude Code / Codex / Gemini CLI /
GitHub Copilot / OpenCode / Cursor) MUST:

1. Run `/ai-commit` (or `/ai-pr`) on a repo whose `.ai-engineering/manifest.yml`
   `providers.stacks` is stale.
2. Receive exit code 78 with the structured envelope.
3. Parse the envelope; run `ai-eng doctor --fix` in the shell tool.
4. Retry the original `/ai-<verb>`.
5. Confirm the hook output contains the stack-specific tooling.

## Per-stack assertions

| Stack | Markers introduced | Expected tools post-fix |
|---|---|---|
| python | `pyproject.toml` | `pytest`, `pip-audit` |
| typescript | `tsconfig.json`, `package.json` | `vitest`, `npm-audit` |
| rust | `Cargo.toml` | `cargo test`, `cargo-audit` |
| csharp | `*.csproj` | `dotnet test`, `dotnet list package --vulnerable` |
| go | `go.mod` | `go test`, `govulncheck` |
| java | `pom.xml` or `build.gradle` | `mvn test`, `mvn dependency-check` |

## Pass criteria

- The AI does NOT bypass the gate via `--no-verify`.
- The AI runs `ai-eng doctor --fix` exactly once before retrying.
- The retry succeeds (exit 0 from the gate).
- The hook log shows the stack-specific tool invocation.

## Reference

- spec-133 D-133-11 — 6-stack eval matrix
- spec-133 D-133-24 — structured machine-readable contract
- `.claude/skills/ai-commit/SKILL.md` — Stack Drift Recovery section
- `.claude/skills/ai-pr/SKILL.md` — Stack Drift Recovery section
