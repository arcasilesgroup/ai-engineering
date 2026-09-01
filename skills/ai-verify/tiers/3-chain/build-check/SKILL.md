---
name: build-check
description: Run the project's objective quality gates — typecheck, lint, tests, and a production build, whatever this project actually uses — then diagnose any failure down to the file and root cause. Use before committing, opening a PR, or declaring work done, and whenever asked whether the code compiles, typechecks, lints, tests, or builds.
---

# Build check

The machine's verdict, not an opinion. Everything here either passes or fails,
and a failure is never a judgment call. Run this **before** the reasoning-based
reviews — reviewing code that does not compile wastes effort on a file that is
about to change.

Fast, deterministic, and the highest-value-per-token check in the set.

Read `.claude/review/CONVENTIONS.md` first — §1 for stack detection, §3 for scope
(you need it to tell a pre-existing failure from one this change introduced), and
§6 for where the report goes. Your report format differs from the other skills'
by design: this one reports gates and failures, not severity-ranked findings.

## 1. Discover the gates — never assume them

Do **not** run commands from memory or from a template. A guessed command that
does not exist wastes a minute and produces a scary error that is not a finding.

Read the project's own definition of its gates, in this order:

1. **`CLAUDE.md` / `AGENTS.md`** — if the commands are written down, use exactly
   those and skip the rest of this discovery.
2. **The manifest's script block** — `package.json` `scripts`, `Makefile`
   targets, `pyproject.toml` `[tool.*]` sections, `Cargo.toml`, `composer.json`
   `scripts`, `Taskfile.yml`, `justfile`.
3. **CI config** — `.github/workflows/*.yml`, `.gitlab-ci.yml`, `Jenkinsfile`.
   This is the most reliable source there is: it is the exact set of gates the
   project already enforces on every push, in the order it enforces them.
4. **Config files as evidence a tool is configured** — a `tsconfig.json`, an
   eslint config, `.ruff.toml`, `.golangci.yml`, `pytest.ini`.

Use the project's package manager, detected from its lockfile — `pnpm-lock.yaml`
→ `pnpm`, `yarn.lock` → `yarn`, `bun.lockb` → `bun`, otherwise `npm`. Running
`npm` in a pnpm workspace produces failures that belong to you, not the code.

Typical shapes, as a reference for what to look for — **not** a list to run:

| Ecosystem | Types | Lint | Test | Build |
|---|---|---|---|---|
| Node/TS | `tsc --noEmit` | `eslint .` / `biome check` | `vitest run`, `jest` | framework build script |
| Python | `mypy`, `pyright` | `ruff check` | `pytest` | `python -m build` |
| Go | `go vet` | `golangci-lint run` | `go test ./...` | `go build ./...` |
| Rust | — | `cargo clippy` | `cargo test` | `cargo build --release` |
| JVM | compiler | `spotbugs`, `checkstyle` | `mvn test` | `mvn package` |

## 2. Run them

From the project root, in order: types → lint → tests → build. Cheapest and most
localizing first.

**Do not stop at the first failure.** Run every gate that can still run and
report the complete picture — one root cause often lights up several gates, and
the user wants the whole list, not the first symptom.

Rules that keep the result honest:

- **A gate the project does not have is not a failure.** Report it as
  `not configured` and move on. Never invent one, and never run a tool the
  project has not set up — a first-ever `mypy` run on an untyped codebase emits
  hundreds of errors that are noise, not findings.
- **If dependencies are not installed**, install them with the detected package
  manager's clean-install command first, and say that you did.
- **Allow real time for the build gate.** It is usually the slowest and the most
  valuable, because it catches whole-program errors — bad exports, boundary
  violations, missing assets — that a typechecker alone will not.
- Run from the project root; do not `cd` elsewhere mid-command. In a monorepo,
  run from the affected package's root and say which package.

## 3. Diagnose, don't paste

A wall of compiler output is not a report. For each distinct failure:

1. **Read the file at the reported line.** The error message names a symptom; the
   cause is often a few lines up, or in an imported type.
2. **Group by root cause.** Twenty errors from one bad type export are one
   finding, not twenty. Say which errors collapse into it.
3. **Distinguish** an error introduced by the current change from a pre-existing
   one — check `git diff` to see if the line is new. Pre-existing failures on an
   untouched file are still reported, but flagged as pre-existing so the user
   knows the change did not cause them.
4. **Give the fix**, specifically. Not "fix the type error" — name the change.

For any failure that mentions a framework or library API, apply the
**installed-version rule** from `.claude/review/CONVENTIONS.md` before
diagnosing. The fix for an error in the installed version is frequently not the
fix you remember from an older one, and a confidently wrong fix here costs more
than no fix at all.

## 4. Report

Short and factual. Write to `.claude/reviews/build-check-<stamp>.md` and print
the path.

```markdown
# Build check

**Verdict:** PASS | FAIL
**Stack:** <language, framework + version, package manager>

| Gate | Command | Result | Detail |
|------|---------|--------|--------|
| types | `<cmd>` | ✅ PASS | 0 errors |
| lint | `<cmd>` | ❌ FAIL | 3 errors, 1 warning |
| tests | — | — | not configured |
| build | `<cmd>` | ⏭️ NOT RUN | blocked by lint failure |

## Failures

### `<lint cmd>` — 3 errors, all from one cause
- **Where:** `src/components/Gallery.tsx:12`
- **Cause:** <the actual root cause; the rule fires once per usage at lines 12, 19, 24>
- **Fix:** <the specific change>
- **Introduced by:** this change | pre-existing
```

Rules: any gate failing → `FAIL`. If you skip a gate because an earlier one
blocked it, mark it `NOT RUN` with the reason — never leave it implied. A gate
the project does not have is `not configured`, which is neither a pass nor a
fail.

Record the exact commands you ran. It is what makes the result reproducible, and
it lets the user correct your discovery if you picked the wrong ones.

If everything passes, say so in two lines and stop. A green build does not need
commentary, and this skill does not offer code opinions — that is `code-audit`.

## 5. Fixing

This skill diagnoses. Apply fixes only if the user asks — then re-run the full
gate sequence afterward and report the new state, since fixes routinely surface
the next error behind the one they cleared.
