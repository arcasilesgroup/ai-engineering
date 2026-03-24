---
name: instinct
description: Use when setting up session learning, reviewing learned instincts, exporting/importing instinct libraries, evolving instincts into skills, or promoting project instincts to global scope.
effort: max
argument-hint: "[status|evolve|export|import|promote|projects]"
tags: [meta, learning, continuous-improvement]
---


# ai-instinct

Instinct-based continuous learning for AI coding agents. Instincts are lightweight behavioral rules that emerge from repeated observations during coding sessions. Unlike static configuration, instincts are earned through experience -- they start tentative, grow in confidence with reinforcement, and decay when contradicted. The system observes tool usage patterns, user corrections, and session outcomes, then distills them into reusable rules that shape future behavior. Instincts live at two scopes: project-level (specific to a codebase) and global (cross-project patterns). When a project instinct proves universal, it can be promoted to global scope automatically.

## The Instinct Model

Each instinct is a YAML file with structured frontmatter and a markdown body:

```yaml
---
id: prefer-ruff-over-flake8
trigger: "When linting Python files"
confidence: 0.7
domain: tooling
source: observation
scope: project
project_id: a1b2c3d4e5f6
project_name: ai-engineering
created_at: "2025-11-15T10:30:00Z"
updated_at: "2026-01-20T14:22:00Z"
observations: 12
reinforcements: 8
contradictions: 1
---

## Action

Use `ruff check` and `ruff format` instead of flake8 or black. This project
standardizes on ruff for all Python linting and formatting. Always check
`pyproject.toml` for ruff configuration before running.

## Evidence

- 2025-11-15: User corrected flake8 usage, pointed to ruff config
- 2025-12-03: Observed ruff in CI pipeline, confirmed standard
- 2026-01-10: User reinforced preference when reviewing PR
- 2026-01-20: Contradicted once when legacy script required flake8 compat
```

### Frontmatter Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Kebab-case unique identifier |
| `trigger` | string | Natural language condition for activation |
| `confidence` | float | Current confidence score (0.0 - 1.0) |
| `domain` | string | Category: `tooling`, `style`, `architecture`, `testing`, `workflow`, `naming`, `security`, `performance` |
| `source` | string | Origin: `observation`, `correction`, `import`, `promotion` |
| `scope` | string | `project` or `global` |
| `project_id` | string | 12-char hash (project scope only) |
| `project_name` | string | Human-readable project name |
| `created_at` | ISO 8601 | First observed |
| `updated_at` | ISO 8601 | Last modified |
| `observations` | int | Total observation count |
| `reinforcements` | int | Times the pattern was confirmed |
| `contradictions` | int | Times the pattern was contradicted |

## How It Works

```
+------------------+     +------------------+     +---------------------+
|   Observation    |     |     Storage      |     | Pattern Detection   |
|                  |     |                  |     |                     |
| tool_start       +---->+ observations     +---->+ Cluster by trigger  |
| tool_complete    |     |   .jsonl         |     | Detect frequency    |
| user_correction  |     |                  |     | Measure consistency |
| session_outcome  |     +--------+---------+     +----------+----------+
+------------------+              |                           |
                                  |                           v
+------------------+     +--------+---------+     +---------------------+
|    Evolution     |     |  Instinct Layer  |     |  Confidence Engine  |
|      Layer       |     |                  |     |                     |
| Skill candidates |<----+ instincts/       |<----+ Score adjustments   |
| Command candidates|    |   *.yml          |     | Reinforcement       |
| Agent candidates |     |                  |     | Contradiction       |
+------------------+     +------------------+     | Time decay          |
                                                  +---------------------+
```

**Flow:**

1. **Observation** -- During each session, tool invocations (start/complete), user corrections, and outcomes are recorded as structured events.
2. **Storage** -- Events append to `observations.jsonl` as newline-delimited JSON. Each line captures timestamp, event type, tool name, truncated input/output, session ID, and project context.
3. **Pattern Detection** -- Observations are clustered by normalized trigger text. Frequency, consistency, and recency are measured to identify emerging patterns.
4. **Confidence Engine** -- Scores are calculated from reinforcements vs contradictions, with time decay applied to stale patterns. New instincts start tentative and must earn trust.
5. **Instinct Layer** -- Mature patterns are persisted as YAML instinct files. Active instincts are loaded at session start and influence tool selection, code style, and workflow decisions.
6. **Evolution Layer** -- High-confidence instinct clusters are analyzed for promotion to skills, commands, or agent specializations.

## Project Detection

Projects are identified using a priority chain to determine the correct scope:

1. **`CLAUDE_PROJECT_DIR` environment variable** -- Highest priority. Used when explicitly set by the IDE or launch configuration.
2. **Git remote URL hash** -- If a git remote exists, compute a 12-character SHA256 hash of the normalized remote URL. This ensures the same project is recognized across clones on different machines.
3. **Git root path hash** -- If no remote exists (local-only repo), compute a 12-character SHA256 hash of the absolute path to the git root.
4. **Global scope** -- If none of the above resolve, instincts are stored in global scope only.

Hash computation:

```
echo -n "git@github.com:org/repo.git" | sha256sum | cut -c1-12
# Result: a1b2c3d4e5f6
```

The 12-character truncated SHA256 hash is used as the `project_id` throughout the system. This is short enough to be human-readable in file paths while being collision-resistant for practical purposes.

## Commands

| Command | Description |
|---------|-------------|
| `/ai-instinct status` | Show current instincts for detected project + global scope |
| `/ai-instinct evolve` | Analyze instinct clusters for skill/command/agent candidates |
| `/ai-instinct export` | Export instincts to a portable YAML file |
| `/ai-instinct import <file>` | Import instincts from a file or URL |
| `/ai-instinct promote [id]` | Promote project instinct(s) to global scope |
| `/ai-instinct projects` | List all known projects with instinct counts |

### `/ai-instinct status`

Detect the current project using the priority chain. Load all instincts from the project scope and global scope. Display them grouped by domain, sorted by confidence descending.

**Output format:**

```
Project: ai-engineering (a1b2c3d4e5f6)
Instincts: 14 project + 8 global = 22 total

tooling (5)
  [0.9] ========= prefer-ruff-over-flake8
  [0.7] =======   use-uv-not-pip
  [0.5] =====     run-gitleaks-staged
  [0.3] ===       try-ty-for-type-checking
  [0.3] ===       prefer-pytest-xdist

style (4)
  [0.8] ========  no-suppression-comments
  [0.7] =======   guard-clauses-over-nesting
  [0.5] =====     max-function-length-30
  [0.3] ===       prefer-pathlib

architecture (3) [global]
  [0.9] ========= single-responsibility-modules
  [0.7] =======   domain-driven-boundaries
  [0.5] =====     hexagonal-port-adapters
```

Confidence bars use `=` characters scaled to the 0.0-1.0 range (10 chars wide). Project instincts display normally; global instincts are marked with `[global]` on the domain header.

### `/ai-instinct export`

Export instincts to a portable YAML file for sharing across machines or teams.

**Flags:**

| Flag | Description | Default |
|------|-------------|---------|
| `--domain <name>` | Filter by domain | all domains |
| `--min-confidence <float>` | Minimum confidence threshold | 0.0 |
| `--output <path>` | Output file path | `./instincts-export.yml` |
| `--scope <project\|global>` | Filter by scope | both |

**Procedure:**

1. Detect current project.
2. Load instincts matching the filter criteria.
3. Strip `project_id` and `project_name` from exported instincts (portability).
4. Write YAML array to the output file.
5. Report count and file path.

**Example:**

```bash
/ai-instinct export --domain tooling --min-confidence 0.5 --output ./my-tooling-instincts.yml
```

### `/ai-instinct import <file>`

Import instincts from a local file path or HTTP URL.

**Arguments:**

| Argument | Description |
|----------|-------------|
| `<file>` | Local file path or HTTP/HTTPS URL to a YAML instinct export |

**Flags:**

| Flag | Description | Default |
|------|-------------|---------|
| `--dry-run` | Show what would be imported without writing | false |
| `--force` | Overwrite existing instincts even if local confidence is higher | false |

**Merge behavior:**

- If an instinct with the same `id` already exists:
  - **Without `--force`:** Keep the version with the higher confidence score. Log the decision.
  - **With `--force`:** Always overwrite with the imported version.
- New instincts are assigned to the current project scope with `source: import`.
- Imported instincts retain their original `created_at` but update `updated_at` to now.

**Procedure:**

1. Resolve the file (download if URL, read if local path).
2. Parse YAML array of instincts.
3. Validate each instinct has required fields (`id`, `trigger`, `confidence`, `domain`).
4. For each instinct, check for existing match by `id`.
5. Apply merge rules (confidence comparison or force overwrite).
6. Write new/updated instinct YAML files to the appropriate scope directory.
7. Report: imported count, skipped count, updated count.

### `/ai-instinct evolve`

Analyze the current instinct library for patterns that have matured enough to become permanent capabilities.

**Analysis tiers:**

| Tier | Criteria | Output |
|------|----------|--------|
| **Skill candidates** | 2+ instincts in the same cluster (normalized trigger similarity) | Proposed SKILL.md outline |
| **Command candidates** | Instincts in the `workflow` domain with confidence >= 0.7 | Proposed command script outline |
| **Agent candidates** | 3+ instincts in the same cluster with average confidence >= 0.75 | Proposed agent specialization |

**Clustering:**

Instincts are clustered by normalized trigger text. Normalization involves:
1. Lowercase the trigger.
2. Remove stop words (when, the, a, an, is, are, to, for, of, in, on, with).
3. Stem remaining words.
4. Group instincts with >= 60% word overlap after normalization.

**Flags:**

| Flag | Description | Default |
|------|-------------|---------|
| `--generate` | Create the proposed skill/command/agent files | false |

**Procedure:**

1. Load all instincts (project + global).
2. Normalize triggers and build clusters.
3. Evaluate each cluster against the tier criteria.
4. Display candidates with their source instincts and proposed structure.
5. If `--generate` is set, create the files in the appropriate locations:
   - Skills: `.agents/skills/<name>/SKILL.md`
   - Commands: `scripts/<name>.sh`
   - Agents: `.agents/agents/ai-<name>.md`
6. Report what was generated and next steps.

**Example output:**

```
Evolution Analysis
==================

Skill Candidates (2):
  1. "python-linting" -- 4 instincts, avg confidence 0.72
     Sources: prefer-ruff-over-flake8, no-suppression-comments,
              run-gitleaks-staged, use-uv-not-pip
     Proposed: .agents/skills/python-linting/SKILL.md

  2. "test-patterns" -- 3 instincts, avg confidence 0.68
     Sources: aaa-pattern-tests, pytest-fixtures-over-setup,
              mock-external-only
     Proposed: .agents/skills/test-patterns/SKILL.md

Command Candidates (1):
  1. "pre-commit-check" -- workflow domain, confidence 0.85
     Source: always-run-ruff-before-commit
     Proposed: scripts/pre-commit-check.sh

Agent Candidates (0):
  No clusters meet the agent threshold yet.
```

### `/ai-instinct promote [id]`

Promote project-scoped instincts to global scope so they apply across all projects.

**Arguments:**

| Argument | Description |
|----------|-------------|
| `[id]` | Optional. Specific instinct ID to promote. If omitted, auto-detect candidates. |

**Flags:**

| Flag | Description | Default |
|------|-------------|---------|
| `--dry-run` | Show what would be promoted without writing | false |
| `--force` | Promote even if auto-promotion criteria are not met | false |

**Auto-promotion criteria:**

An instinct is automatically eligible for promotion when:
1. The same `id` exists in **2 or more projects**.
2. The **average confidence** across those projects is **>= 0.8**.

**Procedure:**

1. If `[id]` is provided:
   - Look up the instinct in the current project.
   - If `--force` is not set, verify auto-promotion criteria.
   - Copy to global scope, update `scope: global`, clear `project_id` and `project_name`.
   - Set `source: promotion`.
2. If `[id]` is omitted:
   - Scan all project directories for instincts.
   - Group by `id` across projects.
   - Filter to those meeting auto-promotion criteria.
   - Display candidates and prompt for confirmation (unless `--force`).
3. Report promoted count and any conflicts resolved.

### `/ai-instinct projects`

List all known projects that have instinct data, with summary statistics.

**Output format:**

```
Known Projects (3)
==================

  ID            Name              Instincts  Last Seen
  a1b2c3d4e5f6  ai-engineering         14    2026-03-20
  b2c3d4e5f6a1  my-api                  7    2026-03-18
  c3d4e5f6a1b2  data-pipeline           3    2026-02-28

Global instincts: 8
Total instincts:  32
```

**Procedure:**

1. Read `projects.json` from the instincts root directory.
2. For each project, count instinct files in its directory.
3. Count global instinct files.
4. Display sorted by last_seen descending.

## Configuration

Configuration lives in `~/.ai-engineering/instincts/config.json`:

```json
{
  "observer": {
    "enabled": true,
    "run_interval_minutes": 5,
    "min_observations_to_analyze": 10
  },
  "confidence": {
    "initial": 0.3,
    "reinforcement_increment": 0.1,
    "contradiction_decrement": 0.15,
    "decay_per_week_inactive": 0.02,
    "min_threshold": 0.1,
    "max_threshold": 0.95
  },
  "promotion": {
    "min_projects": 2,
    "min_avg_confidence": 0.8,
    "auto_promote": false
  },
  "export": {
    "scrub_secrets": true,
    "max_input_chars": 5000,
    "max_output_chars": 5000
  }
}
```

### Observer Settings

| Setting | Type | Description |
|---------|------|-------------|
| `enabled` | bool | Whether the observation pipeline is active |
| `run_interval_minutes` | int | How often to analyze new observations |
| `min_observations_to_analyze` | int | Minimum buffered observations before pattern detection runs |

## File Structure

```
~/.ai-engineering/instincts/
  config.json                           # Observer and scoring configuration
  projects.json                         # Known projects registry
  global/                               # Global-scope instincts
    instincts/
      single-responsibility-modules.yml
      domain-driven-boundaries.yml
      hexagonal-port-adapters.yml
    observations.jsonl                  # Global observation log
  projects/
    a1b2c3d4e5f6/                       # Project: ai-engineering
      instincts/
        prefer-ruff-over-flake8.yml
        use-uv-not-pip.yml
        no-suppression-comments.yml
      observations.jsonl                # Project observation log
    b2c3d4e5f6a1/                       # Project: my-api
      instincts/
        prefer-fastapi-over-flask.yml
        use-pydantic-v2.yml
      observations.jsonl
```

### Key directories:

| Path | Purpose |
|------|---------|
| `~/.ai-engineering/instincts/` | Root directory for all instinct data |
| `config.json` | Observer, confidence, promotion, and export settings |
| `projects.json` | Registry mapping project hashes to metadata |
| `global/instincts/` | Global-scope instinct YAML files |
| `global/observations.jsonl` | Global observation event log |
| `projects/<hash>/instincts/` | Project-scope instinct YAML files |
| `projects/<hash>/observations.jsonl` | Project-scope observation event log |

## Scope Decision Guide

| Pattern Type | Scope | Rationale |
|--------------|-------|-----------|
| Tool preference (ruff, uv, pytest) | project | Tooling varies per project config |
| Code style (guard clauses, naming) | project | Style guides differ across teams |
| Architecture pattern | global | Architectural principles are transferable |
| Security practice | global | Security rules should be universal |
| Framework convention | project | Framework choices are project-specific |
| Git workflow | project | Branching strategies vary per team |
| Language idiom | global | Language best practices are universal |
| Performance pattern | global | Performance principles transcend projects |
| CI/CD pipeline pattern | project | Pipelines are highly project-specific |
| Error handling pattern | global | Error handling principles are universal |

**Rule of thumb:** If the pattern depends on project configuration or team conventions, keep it at project scope. If it represents a universal engineering principle, promote it to global scope.

## Confidence Scoring

### Score Levels

| Score | Level | Meaning |
|-------|-------|---------|
| 0.3 | Tentative | First observation, not yet validated. May apply but needs confirmation. |
| 0.5 | Moderate | Seen multiple times, no contradictions. Reasonable to follow. |
| 0.7 | Strong | Repeatedly confirmed, rarely contradicted. Reliable behavioral rule. |
| 0.9 | Near-certain | Extensively validated across sessions. Core behavioral instinct. |

### Score Adjustment Rules

**Increase (reinforcement):**
- Pattern observed again in a new session: +0.1
- User explicitly confirms the behavior: +0.15
- Pattern succeeds (no error, no correction): +0.05
- Maximum score: 0.95 (never reaches 1.0 -- always leave room for doubt)

**Decrease (contradiction):**
- User corrects the behavior: -0.15
- Pattern leads to an error: -0.1
- Conflicting observation from same session: -0.05
- Minimum score: 0.1 (never fully forgotten -- can be resurrected)

**Decay (time-based):**
- For each week with no observations related to the instinct: -0.02
- Decay stops at 0.1 (floor)
- Any new observation resets the decay timer
- Decay ensures stale instincts gradually lose influence without being deleted

### Score Lifecycle Example

```
Week 1:  Created at 0.30 (tentative)
Week 2:  Reinforced  -> 0.40
Week 3:  Reinforced  -> 0.50 (moderate)
Week 4:  Confirmed   -> 0.65
Week 5:  Reinforced  -> 0.75 (strong)
Week 6:  Contradicted -> 0.60
Week 7:  Reinforced  -> 0.70
Week 8:  (inactive)  -> 0.68
Week 9:  (inactive)  -> 0.66
Week 10: Reinforced  -> 0.76
```

## Instinct Promotion

### Auto-Promotion Criteria

An instinct is eligible for automatic promotion to global scope when:

1. **Cross-project presence:** The same instinct `id` exists in **2 or more** distinct projects.
2. **High average confidence:** The average confidence across all project instances is **>= 0.8**.

Both criteria must be met simultaneously.

### Promotion Process

1. **Detection:** During `/ai-instinct status` or `/ai-instinct promote`, the system scans all project instinct directories.
2. **Candidate identification:** Instincts sharing the same `id` across multiple projects are grouped.
3. **Threshold check:** Average confidence is computed. If >= 0.8 and present in >= 2 projects, the instinct is a candidate.
4. **Merge:** The promoted instinct uses the highest confidence version as the base. The `scope` is set to `global`, `source` is set to `promotion`, and `project_id`/`project_name` are cleared.
5. **Cleanup:** Project-level copies remain but are marked as `superseded_by: global` in their frontmatter. They stop being loaded during session start.

### Manual Promotion

Use `/ai-instinct promote <id> --force` to bypass auto-promotion criteria. This is useful when you know an instinct is universally applicable but it only exists in one project so far.

## Privacy

- **Observations stay local.** The `observations.jsonl` files contain raw tool invocation data including truncated inputs and outputs. These files never leave the local machine and are excluded from exports.
- **Only instincts are exportable.** The `/ai-instinct export` command produces a clean YAML file containing only the distilled instinct rules (trigger, action, confidence, domain). No raw observation data, no tool inputs/outputs, no session identifiers.
- **Secret scrubbing.** Before writing any observation, inputs and outputs are scrubbed for common secret patterns (API keys, tokens, passwords, connection strings). Matches are replaced with `[REDACTED]`.
- **Truncation.** Observation inputs and outputs are truncated to 5000 characters maximum to limit data exposure.
- **No telemetry.** The instinct system does not send any data externally. All processing happens locally.

## Storage Format Specifications

### observations.jsonl Line Format

Each line in `observations.jsonl` is a JSON object with the following fields:

```json
{
  "timestamp": "2026-03-20T14:30:22Z",
  "event": "tool_complete",
  "tool": "Edit",
  "input": "{ truncated to 5000 chars, secrets scrubbed }",
  "output": "{ truncated to 5000 chars, secrets scrubbed }",
  "session": "sess_abc123def456",
  "project_id": "a1b2c3d4e5f6",
  "project_name": "ai-engineering"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | ISO 8601 | When the event occurred |
| `event` | string | Event type: `tool_start` or `tool_complete` |
| `tool` | string | Tool name (Read, Write, Edit, Bash, Glob, Grep) |
| `input` | string | Tool input, truncated to 5000 characters, secrets scrubbed |
| `output` | string | Tool output, truncated to 5000 characters, secrets scrubbed |
| `session` | string | Session identifier for grouping related events |
| `project_id` | string | 12-char project hash |
| `project_name` | string | Human-readable project name |

### Instinct YAML Format

Each instinct file (`<id>.yml`) contains YAML frontmatter and a markdown body:

```yaml
---
id: prefer-ruff-over-flake8
trigger: "When linting Python files"
confidence: 0.7
domain: tooling
source: observation
scope: project
project_id: a1b2c3d4e5f6
project_name: ai-engineering
created_at: "2025-11-15T10:30:00Z"
updated_at: "2026-01-20T14:22:00Z"
observations: 12
reinforcements: 8
contradictions: 1
---

## Action

Describe the behavior to apply when the trigger condition is met.

## Evidence

Chronological log of observations that shaped this instinct.
```

### projects.json Format

```json
{
  "a1b2c3d4e5f6": {
    "id": "a1b2c3d4e5f6",
    "name": "ai-engineering",
    "root": "/Users/dev/repos/ai-engineering",
    "remote": "git@github.com:org/ai-engineering.git",
    "created_at": "2025-11-15T10:30:00Z",
    "last_seen": "2026-03-20T14:30:22Z"
  },
  "b2c3d4e5f6a1": {
    "id": "b2c3d4e5f6a1",
    "name": "my-api",
    "root": "/Users/dev/repos/my-api",
    "remote": "git@github.com:org/my-api.git",
    "created_at": "2025-12-01T09:00:00Z",
    "last_seen": "2026-03-18T16:45:00Z"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | 12-char SHA256 hash (matches the directory name) |
| `name` | string | Human-readable project name (from git remote or directory) |
| `root` | string | Absolute path to the project root |
| `remote` | string | Git remote URL (null if no remote) |
| `created_at` | ISO 8601 | When the project was first observed |
| `last_seen` | ISO 8601 | When the project was last active |
