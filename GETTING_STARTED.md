# Getting Started with ai-engineering

## How to install

If you have not installed ai-engineering yet, see the [Install section in README.md](README.md#install) for setup instructions. The recommended method is `pipx install ai-engineering`.

Once installed, navigate to your project and run:

```bash
cd your-project
ai-eng install .
```

This scaffolds the governance root, detects your stack, installs required tools, and mirrors skills to your configured IDEs.

---

## Phase 1: Your first 5 minutes

You have just installed the framework. These three steps show you what it can do before you change a single line of code.

### 1. Start your session

```
/ai-start
```

This is your daily entry point. Every session begins here. You will see a dashboard that shows:

- **Project identity** -- name, version, and active stacks pulled from your manifest
- **Active spec and plan** -- what the team is working on right now, with task progress
- **Recent activity** -- a plain-language summary of the last few commits (not a raw git log)
- **Board status** -- open work items from GitHub Issues or Azure Boards, if configured
- **Context loaded** -- lessons, decisions, and instincts carried forward from previous sessions

The dashboard is compact (under 50 lines) and renders in any IDE. Think of it as your project briefing.

### 2. Tour your project

```
/ai-guide tour
```

The AI walks through your project architecture: directory structure, component relationships, design decisions, key patterns, and entry points. This works on any existing codebase -- you do not need to have used ai-engineering before. The tour maps what is already there and explains it back to you.

This is useful when onboarding onto a new project, returning after time away, or just wanting a second opinion on how your code is organized.

### 3. Check framework health

```bash
ai-eng doctor
```

This validates that everything the framework depends on is working:

- Git hooks are installed and have correct permissions
- Required tools are available (`ruff`, `gitleaks`, `pytest`, `pip-audit`, etc.)
- Manifest is well-formed and consistent
- State files are intact
- IDE mirrors are in sync

If anything is wrong, `doctor` tells you what and how to fix it. You can also run `ai-eng doctor --fix` to auto-repair common issues.

---

## Phase 2: What do you want to do?

Pick the flow that matches your current need. Each one is a self-contained workflow you can run right now.

### Fix a bug

```
/ai-debug
```

Systematic root-cause analysis, not guesswork. The workflow follows a strict sequence: reproduce the failure, isolate the faulty component, apply the fix, then verify the fix actually resolves the issue. It reads error messages, stack traces, logs, and test output to narrow down where the problem lives. You describe the bug; it does the rest.

### Build a new feature

```
/ai-brainstorm
```

```
/ai-plan
```

```
/ai-dispatch
```

This is the core governed workflow, and it runs in three distinct steps:

1. **Brainstorm** interrogates your requirements. It asks clarifying questions, identifies edge cases, considers trade-offs, and produces a spec (`spec.md`) that captures what you are building and why. The spec is written before any code.

2. **Plan** decomposes the approved spec into concrete tasks. Each task gets an agent assignment, dependencies, and acceptance criteria. The plan lives in `plan.md` with checkable items so progress is visible.

3. **Dispatch** executes the approved plan. Tasks run in dependency order. Each task gets a two-stage review: spec compliance (does it match what was planned?) and code quality (is it well-written?). Progress is tracked in the plan file as tasks complete.

You can also run `/ai-autopilot` instead of `/ai-dispatch` for fully autonomous multi-spec execution -- more on that in Phase 3.

### Review code changes

```
/ai-review
```

Nine specialist agents review your changes in parallel, each through their own lens:

- **Security** -- vulnerabilities, injection vectors, auth gaps
- **Backend** -- API contracts, data flow, error handling
- **Performance** -- hot paths, unnecessary allocations, query efficiency
- **Correctness** -- logic errors, off-by-one, null safety
- **Testing** -- coverage gaps, assertion quality, missing edge cases
- **Compatibility** -- breaking changes, version constraints, platform issues
- **Architecture** -- layer violations, coupling, separation of concerns
- **Maintainability** -- naming, complexity, code organization
- **Frontend** -- UI consistency, accessibility, state management

After all specialists report, a finding-validator challenges every finding to filter out false positives. The result is a narrative review, not a list of lint warnings.

### Verify quality before shipping

```
/ai-verify
```

Evidence-first verification. This is not "looks good to me" -- it runs actual tools and reads real output. Seven specialist dimensions are checked:

- **Governance** -- hooks, gates, manifest consistency
- **Security** -- secrets scan (`gitleaks`), dependency audit (`pip-audit`)
- **Architecture** -- layer compliance, coupling analysis
- **Quality** -- lint (`ruff`), type checking, complexity thresholds
- **Performance** -- benchmarks, regression detection
- **Accessibility** -- a11y compliance checks
- **Feature** -- acceptance criteria vs. actual behavior

Each finding comes with evidence: the tool that found it, the output it produced, and the file and line where the issue lives.

### Ship a pull request

```
/ai-commit
```

```
/ai-pr
```

**Commit** handles the governed commit workflow: auto-branch creation, code formatting, linting, and secrets scanning. Nothing leaves your machine without passing local gates.

**PR** creates the pull request with a structured description, runs quality gates, and can watch CI results to auto-fix issues. Documentation subagents update README and changelog if configured.

### Explain code

```
/ai-explain
```

Three tiers of depth depending on what you need:

- **Brief** -- one-paragraph summary of what a file or function does
- **Standard** -- component purpose, design decisions, key patterns, and how it fits into the broader system
- **Deep** -- line-level walkthrough with architecture context, trade-off analysis, and improvement suggestions

All explanations reference your actual codebase, not generic examples.

### Write tests

```
/ai-test
```

Enforces TDD discipline with a strict RED-GREEN-REFACTOR cycle:

1. **RED** -- write failing tests first. AAA pattern (Arrange, Act, Assert), clear names, real assertions. Confirm the test fails for the expected reason.
2. **GREEN** -- implement the minimum code to make the tests pass. Test files from the RED phase are not modified.
3. **REFACTOR** -- clean up implementation without breaking tests.

Also supports `gap` mode to analyze existing code and identify what is not covered.

---

## Phase 3: Unlock the full power

These capabilities build on the workflows above. Come back to this section once you are comfortable with Phase 2.

### Autonomous spec delivery

```
/ai-autopilot
```

A 6-phase pipeline that takes a spec from idea to pull request without intervention:

1. **Decompose** -- break the spec into sub-specs if it is too large for a single pass
2. **Deep-plan** -- generate a detailed plan for each sub-spec
3. **Build DAG** -- create a dependency graph across all tasks
4. **Implement** -- execute tasks in waves, respecting dependency order
5. **Quality convergence** -- run verify, guard, and review in up to 3 rounds until all gates pass
6. **Deliver** -- open a PR with the complete implementation

State is persisted to disk at every phase. If anything fails, you resume from where it stopped -- not from the beginning. The state machine handles retries, rollbacks, and partial progress.

### Backlog execution

```
/ai-run
```

Point at your GitHub Issues or Azure Boards backlog and let the AI execute items end-to-end:

1. **Intake** -- pull prioritized work items from your configured board
2. **Explore** -- deep-read the codebase to understand context for each item
3. **DAG** -- build a dependency graph across work items
4. **Build** -- implement each item in dependency order with full governance
5. **Gate** -- run quality and security gates on the result
6. **PR** -- open a pull request for each completed item

This is fully autonomous, no-HITL (human-in-the-loop) execution. The AI picks up backlog items in priority order and delivers them as governed pull requests.

### Continuous improvement

```
/ai-instinct
```

Passively observes your session. When you correct the AI, change its output, or establish a pattern, instinct captures that as a project-specific learning. Over time, the AI gets better at your project because it remembers how you work.

```
/ai-learn
```

Extracts patterns from merged PR feedback, review comments, and post-merge observations. These become persistent lessons that apply to future work in the same codebase.

### Security and governance

```
/ai-security
```

Full security analysis: SAST scanning, dependency vulnerability audit, secrets detection, and SBOM generation. Findings are severity-rated and actionable.

```
/ai-governance
```

Compliance and ownership tracking: who owns what code, what policies apply, risk lifecycle management, and audit trail generation.

```
/ai-release-gate
```

GO/NO-GO decision across 8 dimensions before any release ships. Aggregates quality, security, test coverage, documentation, governance, and dependency health into a single verdict.

### Design and content

```
/ai-design
```

UI/UX design system generation. Component libraries, spacing systems, color tokens, typography scales, and responsive breakpoints.

```
/ai-animation
```

Motion design specifications. Timing curves, entrance/exit patterns, micro-interactions, and accessibility-compliant animation guidelines.

```
/ai-slides
```

Presentation deck generation from specs, code, or plain descriptions. Produces self-contained HTML/CSS slide decks.

```
/ai-write
```

Technical writing: documentation, blog posts, release notes, architecture decision records, and runbooks.

```
/ai-canvas
```

Visual artifact creation for marketing materials, diagrams, and compositional layouts.

---

## The full skill map

All 47 skills grouped by category. Each is invoked as `/ai-<name>`.

### Workflow (10 skills)

| Skill | Purpose |
|-------|---------|
| `brainstorm` | Interrogate requirements, produce a spec |
| `plan` | Decompose spec into tasks with agent assignments |
| `dispatch` | Execute an approved plan with two-stage review |
| `code` | Context-aware implementation with self-review |
| `test` | TDD enforcement with RED-GREEN-REFACTOR |
| `debug` | Systematic root-cause analysis and fix |
| `verify` | Evidence-first quality verification |
| `review` | Multi-specialist parallel code review |
| `eval` | Quality evaluation and benchmarking |
| `schema` | Database schema design and migrations |

### Delivery (5 skills)

| Skill | Purpose |
|-------|---------|
| `commit` | Governed commit with format, lint, and secrets scan |
| `pr` | Pull request creation with gates and docs subagents |
| `release-gate` | GO/NO-GO decision across 8 dimensions |
| `cleanup` | Branch and artifact cleanup |
| `market` | Go-to-market content and messaging |

### Enterprise (7 skills)

| Skill | Purpose |
|-------|---------|
| `security` | SAST, dependency audit, secrets scan, SBOM |
| `governance` | Compliance, ownership, risk lifecycle |
| `pipeline` | CI/CD pipeline generation |
| `docs` | Documentation generation and maintenance |
| `board-discover` | Discover and map project board structure |
| `board-sync` | Synchronize work items with project boards |
| `platform-audit` | Platform-wide governance audit |

### Teaching (6 skills)

| Skill | Purpose |
|-------|---------|
| `explain` | 3-tier depth code explanation |
| `guide` | Onboarding and project tours |
| `write` | Technical writing and content |
| `slides` | HTML/CSS presentation decks |
| `media` | Media asset generation |
| `video-editing` | Video editing workflows |

### Design (3 skills)

| Skill | Purpose |
|-------|---------|
| `design` | UI/UX design systems |
| `animation` | Motion design specifications |
| `canvas` | Visual artifacts and compositions |

### SDLC (6 skills)

| Skill | Purpose |
|-------|---------|
| `note` | Structured knowledge capture |
| `standup` | Status reporting |
| `sprint` | Sprint planning and review |
| `postmortem` | Incident analysis |
| `support` | Customer issue triage |
| `resolve-conflicts` | Git merge conflict resolution |

### Meta (10 skills)

| Skill | Purpose |
|-------|---------|
| `start` | Session dashboard and context loading |
| `create` | Scaffold new skills and agents |
| `learn` | Extract patterns from merged PR feedback |
| `prompt` | Prompt optimization |
| `analyze-permissions` | Permission and access analysis |
| `instinct` | Session observation and pattern capture |
| `autopilot` | Autonomous multi-spec delivery |
| `run` | Backlog-driven autonomous execution |
| `constitution` | Framework governance initialization |
| `skill-evolve` | Skill improvement and optimization |

---

## CLI reference

The `ai-eng` CLI manages the framework itself. These commands run in your terminal, not inside an AI session.

```bash
ai-eng install [TARGET]          # Install framework in a project directory
ai-eng update [TARGET]           # Preview framework updates (add --apply to execute)
ai-eng doctor [TARGET]           # Diagnose and auto-fix health issues
ai-eng sync                      # Regenerate IDE mirrors from canonical source
ai-eng validate [TARGET]         # Verify manifest and state integrity
ai-eng gate                      # Run git hook gates manually
ai-eng spec verify|list|catalog  # Spec management
ai-eng decision record "TITLE"   # Record a decision in the decision store
ai-eng stack|ide|provider        # Manage stacks, IDEs, and providers
ai-eng release VERSION           # Release lifecycle management
ai-eng version                   # Show installed version
```

---

## Multi-IDE support

ai-engineering works identically across four AI coding assistants:

- **Claude Code** -- `.claude/skills/` and `.claude/agents/`
- **GitHub Copilot** -- `.github/skills/` and `.github/agents/`
- **OpenAI Codex** -- `.codex/skills/` and `.codex/agents/`
- **Gemini CLI** -- `.gemini/skills/` and `.gemini/agents/`

The `.claude/` directory is the canonical source. All other IDE directories are mirrors generated by `ai-eng sync`. When framework content changes, run `ai-eng sync` to regenerate mirrors. Same 47 skills, same 10 agents, same governance -- regardless of which AI assistant you use.

---

## Next steps

- Run `/ai-start` to begin your first session
- Run `/ai-guide tour` to see your project through the framework's eyes
- Pick a workflow from Phase 2 that matches what you need right now
- Come back to Phase 3 when you are ready for autonomous execution
