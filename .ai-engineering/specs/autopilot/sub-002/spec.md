---
id: sub-002
parent: spec-080
title: "Unified Stack Detection"
status: planning
files: [".claude/agents/ai-build.md", ".claude/skills/ai-security/SKILL.md", ".claude/skills/ai-pipeline/SKILL.md", ".claude/skills/ai-review/handlers/review.md", ".ai-engineering/manifest.yml", ".ai-engineering/schemas/manifest.schema.json", "src/ai_engineering/cli_commands/doctor.py"]
depends_on: []
---

# Sub-Spec 002: Unified Stack Detection

## Scope
Make manifest.yml `providers.stacks` the single source of truth for stack detection. Replace file-based heuristics in ai-build, ai-security, ai-pipeline, and ai-review with manifest reads. Separate the stacks schema enum into languages vs frameworks. Add `ai-eng doctor` drift check between manifest stacks and actual project files. Auto-detection remains as install-time only fallback.

## Exploration

### 1. Current Stack Detection Logic Per Agent/Skill

#### ai-build (`.claude/agents/ai-build.md`, lines 26-28)
- **Section "1. Detect Stack"**: file-based heuristics -- `pyproject.toml` -> Python, `*.csproj` -> .NET, `next.config.*` -> Next.js, `Cargo.toml` -> Rust, `*.tf` -> Terraform.
- **Section "2. Load Contexts"**: after detecting, reads `contexts/languages/{lang}.md` (14 available), `contexts/frameworks/{fw}.md` (15 available), `contexts/team/*.md`.
- Same text duplicated across 5 mirrors:
  - `.github/agents/build.agent.md` (lines 41-49)
  - `.agents/agents/ai-build.md` (lines 26-38)
  - `src/.../templates/project/.claude/agents/ai-build.md`
  - `src/.../templates/project/.github/agents/build.agent.md`
  - `src/.../templates/project/.agents/agents/ai-build.md`

#### ai-security (`.claude/skills/ai-security/SKILL.md`, line 28)
- **static mode, step 1**: "Detect stacks -- read project files for active languages." No further detail, no manifest reference.
- **deps mode, step 1**: "Detect lock files -- `uv.lock`, `package-lock.json`, `Cargo.lock`, `*.csproj`." Also file-based heuristics.
- Same text in 4 mirrors:
  - `.github/skills/ai-security/SKILL.md`
  - `.agents/skills/security/SKILL.md`
  - `src/.../templates/project/.claude/skills/ai-security/SKILL.md`
  - `src/.../templates/project/.github/skills/ai-security/SKILL.md`
  - `src/.../templates/project/.agents/skills/security/SKILL.md`

#### ai-pipeline (`.claude/skills/ai-pipeline/SKILL.md`, line 50)
- **Integration section**: "Stack detection: reads `pyproject.toml`, `*.csproj`, `package.json`, `Cargo.toml`." File-based heuristics.
- **Handler `handlers/generate.md`**, step 1: "Read project files for stacks: `pyproject.toml` (Python), `*.csproj` (.NET), `package.json` (Node), `Cargo.toml` (Rust)." Same file-based heuristics.
- Same text in 4 mirrors per file:
  - `.github/skills/ai-pipeline/SKILL.md` + `handlers/generate.md`
  - `.agents/skills/pipeline/SKILL.md` + `handlers/generate.md`
  - All 3 template mirrors

#### ai-review (`handlers/review.md`, lines 13-18)
- **Step 1, sub-step 3**: "Detect languages in the diff (file extensions) and read contexts." This is diff-scoped detection (file extensions in the diff), not project-level detection. It reads `contexts/languages/{lang}.md` and `contexts/frameworks/{fw}.md`.
- This is a different pattern -- it is diff-scoped rather than project-scoped. It should ALSO read the manifest for project-level context but can keep diff-scoping for which review handlers to dispatch.

### 2. Current Manifest Stacks Enum (schema)

From `.ai-engineering/schemas/manifest.schema.json` (lines 44-49), the `providers.stacks` enum contains 19 values:

```
python, dotnet, react, typescript, nextjs, node, nestjs, react_native,
rust, yaml, terraform, astro, github_actions, azure_pipelines, azure,
bash, powershell, sql, postgresql
```

This is a flat list mixing languages and frameworks/platforms:
- **Languages**: python, typescript, rust, bash, powershell, sql
- **Frameworks/runtimes**: dotnet, react, nextjs, node, nestjs, react_native, astro
- **IaC/CI**: terraform, github_actions, azure_pipelines, azure, yaml
- **Database-specific**: postgresql

### 3. Autodetect.py Vocabulary vs Schema Enum

From `src/ai_engineering/installer/autodetect.py`:

**autodetect.py `_STACK_POPULARITY` tuple** (line 34-51) uses 16 values:
```
typescript, python, javascript, java, csharp, go, php, rust, ruby,
kotlin, swift, dart, elixir, sql, bash, universal
```

**autodetect.py `_FILE_MARKERS` dict** (lines 98-113) detects these stacks:
```
python, go, rust, java, kotlin, ruby, dart, elixir, swift, php,
csharp, typescript, javascript
```

**Vocabulary mismatch table**:

| In autodetect.py only | In schema enum only | Naming conflicts |
|----------------------|--------------------|--------------------|
| javascript | dotnet | csharp (autodetect) vs dotnet (schema) |
| java | react | -- |
| go | nextjs | -- |
| php | node | -- |
| ruby | nestjs | -- |
| kotlin | react_native | -- |
| swift | astro | -- |
| dart | github_actions | -- |
| elixir | azure_pipelines | -- |
| universal | azure | -- |
| -- | yaml | -- |
| -- | powershell | -- |
| -- | postgresql | -- |

Key conflict: autodetect uses `csharp` (language name) while schema uses `dotnet` (framework name). The schema mixes abstraction levels.

### 4. Doctor Phase Structure

- `doctor/service.py` iterates over `PHASE_ORDER = (detect, governance, ide_config, state, hooks, tools)`.
- Each phase module in `doctor/phases/{name}.py` exposes `check(ctx) -> list[CheckResult]` and `fix(ctx, failed, dry_run) -> list[CheckResult]`.
- The **detect phase** (`doctor/phases/detect.py`) currently runs 3 checks:
  1. `install-state-exists` -- file presence
  2. `install-state-coherent` -- schema version + readiness status
  3. `detection-current` -- VCS provider match (stored vs git remote)
- The detect phase is the natural place to add a stack drift check (`stack-drift`).
- The `DoctorContext` already carries `manifest_config: ManifestConfig | None`, which provides `manifest_config.providers.stacks` -- the manifest stacks field is already accessible in every phase.
- The `detect_stacks()` function from `autodetect.py` can be called to get the file-system-detected stacks for comparison.
- Existing test file: `tests/unit/test_doctor_phases_detect.py` -- 3 test classes + 1 parity check class, follows `DoctorContext` fixture pattern.

### 5. Schema Separation: Languages vs Frameworks

The spec requires separating `providers.stacks` into languages vs frameworks. However, the current schema is flat and the manifest field is a single array. Splitting into two fields (`providers.languages` and `providers.frameworks`) would be a **breaking schema change** requiring schema_version bump and migration logic.

**Simpler alternative**: keep `providers.stacks` as a single array but expand the enum to include all autodetect vocabulary, and tag values in the schema description as language vs framework. The agent/skill instructions can document which stacks map to which context files. This avoids a breaking change.

### 6. Files Requiring Changes (Full Mirror Audit)

**Primary source files** (6 unique content files):
1. `.claude/agents/ai-build.md` -- replace "Detect Stack" section
2. `.claude/skills/ai-security/SKILL.md` -- replace "Detect stacks" step
3. `.claude/skills/ai-pipeline/SKILL.md` -- replace "Stack detection" line
4. `.claude/skills/ai-pipeline/handlers/generate.md` -- replace step 1 detection
5. `.claude/skills/ai-review/handlers/review.md` -- add manifest read as Step 0
6. `.ai-engineering/schemas/manifest.schema.json` -- expand stacks enum

**IDE mirrors** (each primary has 2 mirrors):
- `.github/agents/build.agent.md`
- `.github/skills/ai-security/SKILL.md`
- `.github/skills/ai-pipeline/SKILL.md`
- `.github/skills/ai-pipeline/handlers/generate.md`
- `.agents/agents/ai-build.md`
- `.agents/skills/security/SKILL.md`
- `.agents/skills/pipeline/SKILL.md`
- `.agents/skills/pipeline/handlers/generate.md`

**Template mirrors** (each primary has 3 template copies -- .claude, .github, .agents):
- `src/.../templates/project/.claude/agents/ai-build.md`
- `src/.../templates/project/.github/agents/build.agent.md`
- `src/.../templates/project/.agents/agents/ai-build.md`
- `src/.../templates/project/.claude/skills/ai-security/SKILL.md`
- `src/.../templates/project/.github/skills/ai-security/SKILL.md`
- `src/.../templates/project/.agents/skills/security/SKILL.md`
- `src/.../templates/project/.claude/skills/ai-pipeline/SKILL.md`
- `src/.../templates/project/.github/skills/ai-pipeline/SKILL.md`
- `src/.../templates/project/.agents/skills/pipeline/SKILL.md`
- `src/.../templates/project/.claude/skills/ai-pipeline/handlers/generate.md`
- `src/.../templates/project/.github/skills/ai-pipeline/handlers/generate.md`
- `src/.../templates/project/.agents/skills/pipeline/handlers/generate.md`
- `src/.../templates/project/.claude/skills/ai-review/handlers/review.md`

**Python source files** (2 files):
- `src/ai_engineering/doctor/phases/detect.py` -- add `_check_stack_drift()`
- `src/ai_engineering/installer/autodetect.py` -- no changes needed (install-time only, keeps existing vocabulary)

**Schema files** (1 file):
- `.ai-engineering/schemas/manifest.schema.json` -- expand stacks enum

**Test files** (1 file):
- `tests/unit/test_doctor_phases_detect.py` -- add `TestStackDrift` class

**Total unique content changes**: 6 primary skill/agent files + 1 schema + 1 doctor phase + 1 test = 9 files
**Total mirror propagation**: ~20 mirror files
**Grand total**: ~29 files
