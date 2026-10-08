# Review conventions

Shared rules for every review skill in this repo (`design-check`, `code-audit`,
`security-audit`, `build-check`, `a11y-audit`, `perf-audit`). Read this before
starting a review. It defines stack detection, scope, severity, the
false-positive gate, and the output contract that lets `full-review` merge
reports from parallel agents.

---

## 1. Detect the stack before you judge anything

These skills are stack-agnostic by design. Before reviewing, spend one minute
establishing what you are actually looking at, and state it in the report header.

Read the manifest that exists, in this order — the first hit determines the
ecosystem:

| File | Ecosystem | Where the real versions live |
|---|---|---|
| `package.json` | Node / JS / TS | `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `node_modules/<pkg>/package.json` |
| `pyproject.toml`, `requirements.txt` | Python | `poetry.lock`, `uv.lock`, `pip freeze` |
| `go.mod` | Go | `go.sum` |
| `Cargo.toml` | Rust | `Cargo.lock` |
| `Gemfile` | Ruby | `Gemfile.lock` |
| `pom.xml`, `build.gradle` | JVM | the lock/report the build tool emits |
| `composer.json` | PHP | `composer.lock` |
| `*.csproj`, `*.sln` | .NET | `packages.lock.json` |

Then read, if present: `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, and the
`README`. These frequently state conventions that define what "correct" means
here, and a reviewer who has not read them reports false positives against the
house style.

Record for the report header: **language, framework(s) with installed versions,
package manager, and test framework (or "none configured")**.

Monorepos: identify which package the change is in and review from that
package's root. Its manifest governs, not the workspace root's.

## 2. The installed-version rule (non-negotiable)

**The installed version of a dependency is the source of truth, not your memory
of it.** Frameworks change APIs, defaults, file conventions, and security
behavior between versions, and the version in this repo may postdate your
training data. Confident recall about a fast-moving framework is the single
largest source of false positives in these reviews.

Before claiming any framework or library API is misused, deprecated, removed, or
wrong, verify against the installed copy:

1. **Bundled docs**, if the package ships them (some do — check the installed
   package directory before assuming it does not).
2. **The installed source or type definitions** — the `.d.ts`, the module source,
   the function signature as actually installed.
3. **The project's own usage elsewhere** — a pattern used consistently across a
   codebase that builds and ships is evidence, not a bug.

Then:

- A finding contradicted by the installed source is a false positive. Delete it.
- A finding you could not verify against the installed source: downgrade to
  **Low** and label it `unverified against installed version`.
- "This looks different from how I remember version N" is not a finding.

This rule has veto power over every other heuristic in every review skill.

If `CLAUDE.md` or `AGENTS.md` warns that a dependency postdates training data,
treat that as a hard instruction and raise your verification bar for that
dependency specifically.

## 3. Scope resolution

Default scope is **the current change**, not the whole repo:

1. Uncommitted work — `git status --porcelain`, `git diff`, `git diff --staged`
2. Branch commits — `git diff <base>...HEAD`, where base is the first of
   `origin/main`, `origin/master`, `origin/develop`, `main`, `master` that exists
   and is not HEAD
3. If that yields nothing (fresh repo, or you are on the base branch with no
   diff), fall back to a **whole-repo review of first-party source** and say so
   explicitly in the report header.

An explicit scope from the user (a path, a commit range, "the whole app") always
wins over the above.

**Identify first-party source rather than assuming a layout.** Read the manifest
and any build config for the configured source roots. Common ones are `src/`,
`lib/`, `app/`, `internal/`, `pkg/`, and the package-named directory in Python
projects — but confirm against this repo instead of guessing.

**Never review generated, vendored, or dependency code.** Determine what that
means here rather than working from a fixed list:

- Everything matched by `.gitignore`
- Dependency directories — `node_modules/`, `vendor/`, `.venv/`, `target/`,
  `Pods/`
- Build output — `dist/`, `build/`, `out/`, `.next/`, `__pycache__/`
- Lockfiles, generated clients, compiled protobufs, migration snapshots, and any
  file whose header says it was generated
- Minified or bundled assets, and binaries

Findings in generated or vendored files are not findings. If generated output is
wrong, the finding belongs at the generator or its input.

## 4. Severity

| Severity | Bar |
|---|---|
| **Critical** | Exploitable by an untrusted party, loses/corrupts data, or breaks the app for all users in normal operation. |
| **High** | Produces wrong behavior on a realistic path, or a security issue that needs a plausible precondition. |
| **Medium** | Degraded behavior, real edge-case failure, or maintainability cost you can name concretely. |
| **Low** | Polish, consistency, minor latent risk. |

Do not inflate. If the honest framing is "you might consider", it is Low — or it
is not a finding at all.

## 5. False-positive gate

Apply to every candidate finding **before** it reaches the report. A finding
ships only if you can state all three:

1. **Trigger** — the concrete input, state, or user action that reaches it.
2. **Consequence** — what observably goes wrong.
3. **Evidence** — a `file:line` you have actually **read**, not grepped and
   assumed.

If you cannot supply all three, delete it. Then re-read the surrounding code once
more, actively trying to **disprove** each surviving finding — check the callers,
the types, the guard clauses you might have skipped, and the installed version
per §2.

- Survives the disproof attempt → `CONFIRMED`
- You believe it but could not fully trace it → `PLAUSIBLE`
- Disproved → gone, silently

These reviews are judged on precision, not on finding count. A report with two
real bugs beats one with two real bugs and nine speculative ones — the noise is
what makes reviews get ignored. Reporting zero findings is a valid, useful
result.

## 6. Output contract

Write the report to `.claude/reviews/<skill-name>-<YYYYMMDD-HHMMSS>.md`
(`mkdir -p .claude/reviews` first; get the stamp from `date +%Y%m%d-%H%M%S`).
Print the path as the last line of your response.

````markdown
# <Skill name> — <short scope description>

**Verdict:** PASS | PASS WITH NOTES | FAIL
**Stack:** <language, framework + installed version, package manager, test framework>
**Scope:** <what was reviewed — diff range or file list>
**Coverage:** <N> files read · Findings: <c> critical, <h> high, <m> medium, <l> low

## Findings

### [HIGH] <one-line claim, the defect itself>
- **Where:** `<path>:<line>`
- **Trigger:** <concrete path that reaches it>
- **Consequence:** <what breaks>
- **Fix:** <specific change, not "add validation">
- **Confidence:** CONFIRMED | PLAUSIBLE

## Checked and clean
- <area> — <what you verified, one line>

## Not covered
- <anything in scope you could not assess, and why>
````

**Verdict rule:** any Critical or High → `FAIL`. Only Medium/Low → `PASS WITH
NOTES`. Nothing → `PASS`.

The `Stack` line is not decoration — it is how the reader knows whether §2 was
actually applied, and how `full-review` spots two agents that resolved different
stacks in a monorepo.

The `Not covered` section is required and must be honest. A review that silently
skipped half its scope reads as clean coverage when it was not.

## 7. Reviews are read-only

Review skills do not edit source files. Propose fixes in the report; apply them
only when the user asks. The one exception is the report file itself.
