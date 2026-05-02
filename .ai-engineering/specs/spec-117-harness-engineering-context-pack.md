# Spec 117 Context Pack - Harness Engineering Root Refactor

This file preserves the research and repo context needed to resume spec-117 without reopening every source. It is not an implementation plan; it is the evidence pack for the root-refactor program.

## User Intent

The user wants a deep refactor of all ai-engineering, not a narrow cleanup pass. The bar is explicit: every durable file and every line should have a reason to exist, quality should increase rather than fall, and the result should be production-ready. The user also explicitly allowed deleting, merging, or rewriting skills, agents, and runtime surfaces when the current shape is accidental. The focus remains harness engineering, using the NotebookLM research notebook and the educational repo `/Users/soydachi/repos/ejemplo-harness-subagentes` as references.

## Prompt Enhancement

Original intent contains broad words: `refactorizar`, `limpio`, `mejor estructurado`, `menos verbose`, `mas calidad`.

Optimized working input:

> Design a harness-engineering root-refactor roadmap for the full ai-engineering framework. The roadmap must move the repo toward a production-ready local-first coding-agent harness with explicit artifact planes, a spec-scoped work ledger, generated provider mirrors, a single deterministic harness kernel, safer multi-agent execution, slimmer control surfaces, and runtime package boundaries that are justified by tests and ownership. It must preserve the Constitution, spec-driven development, TDD, and generated-mirror guarantees while allowing selective rewrite and deletion of accidental framework surfaces.

## Research Access Note

The NotebookLM preview URL is currently sign-in gated from this environment. The research synthesis below preserves the previously extracted NotebookLM findings already captured during the earlier spec-117 drafting pass and combines them with fresh local exploration of ai-engineering and the reference repo.

## NotebookLM Research Read

Notebook:

- Title: `Harness Engineering: Building Systems Beyond the AI Chatbot`
- URL: https://notebooklm.google.com/notebook/858dc737-739f-4026-a900-6ab641be936b
- Sources: 131
- Notes: none saved in the notebook at read time.

NotebookLM was previously queried across the full source set for:

- the main thesis of harness engineering;
- a feature catalog for production coding-agent harnesses;
- concrete practices from Martin Fowler/Thoughtworks, Addy Osmani, OpenAI/Codex, LangChain/LangGraph, Terminal-Bench/HARBOR, observability, and eval sources.

## Research Synthesis

Harness engineering is the discipline of engineering the deterministic system around a model. The repeated formula in the notebook is:

`Agent = Model + Harness`

The model provides probabilistic reasoning. The harness provides execution loop, tools, context, state, lifecycle policy, and verification. The important operational rule is: when an agent repeats a mistake, do not only improve the prompt; change the environment so that mistake becomes structurally harder or impossible.

The research frames the evolution as:

- Prompt engineering controls what the model is asked to do.
- Context engineering controls what the model sees.
- Harness engineering controls what the agent can do across a full task lifecycle.

The notebook converges on the formal harness shape:

`H = (E, T, C, S, L, V)`

- `E`: Execution loop - observe, plan, act, recover, terminate.
- `T`: Tool registry - typed, scoped, policy-checked tool access.
- `C`: Context manager - what enters context, when, and why.
- `S`: State store - resumable task state, memory, audit trail, rollback anchor.
- `L`: Lifecycle hooks - policy, security, approval, checks, loop detection.
- `V`: Verification/eval interface - traces, tests, metrics, benchmarks, pass/fail.

The core engineering preference is computational controls before inferential controls:

- Feedforward controls: AGENTS.md, skills, conventions, architecture docs, task specs.
- Feedback controls: lint, tests, type checks, structural validators, screenshots, traces.
- Computational controls are preferred where possible because they are cheap, repeatable, and fast.
- Inferential review remains useful for architecture, maintainability, and judgment, but should not substitute for deterministic proof.

## Concrete Practices from the Research

### Progressive Disclosure

Instruction files should act as maps. Long encyclopedic instructions increase token load and can reduce compliance. Use concise root files that point to deeper files, handlers, schemas, and scripts.

Implication for ai-engineering:

- `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, and Copilot instructions should stay slim.
- `SKILL.md` files should contain contracts and route to handlers/references rather than restating shared rules.
- Generated mirrors are distribution surfaces, not new knowledge homes.

### Filesystem-First Interface

The research strongly favors the filesystem as the agent interface: files are readable by native tools, versioned by git, and good for context offloading. The reference repo demonstrates this with `feature_list.json`, `progress/current.md`, `progress/history.md`, and per-agent reports.

Implication for ai-engineering:

- Work state should be file-backed and resumable.
- Subagents should return compact references to progress artifacts.
- Large tool outputs should materialize as files and only summaries should enter chat.

### Small Tool Surface

More tools can degrade agent performance. The recommended pattern is task-scoped tool visibility: start with a small, relevant set and add tools only when evidence shows need.

Implication for ai-engineering:

- Do not expose every possible CLI, MCP, or script to every role.
- Define per-agent and per-task tool scopes.
- Treat MCP configuration and hook files as protected harness configuration.

### Plan-Execute-Verify Separation

The research repeatedly recommends distinct planning, execution, and verification roles. Agents are poor at evaluating their own work without external sensors.

Implication for ai-engineering:

- Preserve spec -> plan -> dispatch.
- Keep build as the only code-writing agent.
- Use verify/review/guard as distinct lenses.
- Add file-backed handoff artifacts so verification does not rely on chat memory.

### Lifecycle Hooks and Loop Detection

Hooks should enforce what agents often forget: tests before stop, no destructive commands, no self-editing of harness config, loop detection, and escalation after repeated failure.

Implication for ai-engineering:

- Make hook output LLM-readable and action-oriented.
- Keep passing checks quiet.
- Add retry/loop limits and blocked-state reports.

### Observability and Evals

Research sources emphasize trajectory observability, not only final pass/fail. Useful metrics include task resolution rate, rework rate, verification tax, defect escape rate, pass@1, context size, tool-call count, and cost per task.

Implication for ai-engineering:

- Extend the current NDJSON event stream into a task-level harness trace model.
- Generate eval cases from real failures.
- Track whether constraints improve outcomes independent of model changes.

### Automated Harness Evolution

HARBOR, AHE, and Meta-Harness sources show that harness configuration can be optimized, but also warn that manually adding memory, reflection, and tools can regress performance.

Implication for ai-engineering:

- v1 should not chase full automated harness optimization.
- Add change manifests, predictions, outcomes, and rollback-ready task slices first.
- Only later automate harness evolution against stable evals.

## Reference Repo Findings

Reference repo: `/Users/soydachi/repos/ejemplo-harness-subagentes`

Key files:

- `AGENTS.md`: map, not bible. It tells agents what to read when needed.
- `feature_list.json`: backlog and state with one feature at a time.
- `progress/current.md`: live session state.
- `progress/history.md`: append-only session history.
- `progress/impl_*.md`: implementer report.
- `progress/review_*.md`: reviewer report.
- `CHECKPOINTS.md`: final-state checklist.
- `docs/architecture.md`: what `good work` means.
- `docs/conventions.md`: style and naming.
- `docs/verification.md`: proof requirements.
- `.claude/agents/leader.md`: orchestrates, never writes code.
- `.claude/agents/implementer.md`: writes one feature, tests, verifies.
- `.claude/agents/reviewer.md`: reviews, never edits code.
- `.claude/settings.json`: hooks that run tests after edits and `./init.sh` on stop.
- `init.sh`: single executable health gate.

Patterns worth copying into ai-engineering:

- Anti-telephone handoff: subagents write details to files and return only `done -> path`.
- Progressive disclosure: root map points to deeper docs only when needed.
- Separate live progress from append-only history.
- Review is separate from implementation.
- Verification is executable and file-backed.
- Session history survives context compaction and IDE restarts.

Patterns that need scaling before copying:

- One global `feature_list.json` is too narrow for ai-engineering. ai-engineering needs spec-scoped task ledgers with dependency DAGs and write ownership.
- One repo-global `current.md` is not safe once parallel work and resumable runs exist.
- A literal `leader/implementer/reviewer` topology is too small for current scale; ai-engineering needs `dispatch`, `autopilot`, and `run` envelopes over `build`, `review`, `verify`, `guard`, and `explore` roles.
- A monolithic `init.sh` is too coarse. ai-engineering should compose preflight, doctor, validate, hooks, and gate checks into one deterministic harness-check contract instead.

## Exploration Refresh

Fresh exploration was run across runtime, instruction surfaces, governance/state/docs, tests/gates/telemetry, and the reference repo. These are the high-signal findings.

### Runtime Architecture Findings

- The repo already has a few seams worth preserving: CLI bootstrap/presentation, the VCS protocol, release orchestration, and the phase/pipeline execution model used by installer/doctor.
- The current runtime also has clear accidental architecture: dual gate/control planes, duplicated installer and doctor tool logic, duplicated manifest loaders, template logic leaking into validator/runtime behavior, and stale maintenance/reporting assumptions.
- Oversized hotspots confirm the need for a later selective rewrite track: `policy/orchestrator.py`, `cli_commands/core.py`, `cli_commands/gate.py`, `state/models.py`, `policy/checks/stack_runner.py`, and installer/update surfaces.
- A future root refactor should aim for a new harness kernel, unified manifest/state repository, a reconciler engine for install/doctor/update, thin CLI adapters, and a clean asset/runtime split.

### Instruction and Mirror Findings

- Generated provider mirrors still contain `.claude`-specific path references in non-Claude surfaces, which is a concrete runtime breakage risk for provider-local installs.
- Generated/manual provenance is weak: generated mirrors do not consistently advertise that they are derived, which makes drift harder to reason about.
- Root surfaces already drift from manifest truth: AGENTS anchors are stale, GEMINI still contains hand-maintained count sections, and platform audit docs encode outdated assumptions.
- The public surface is broader than the actual first-class agent model. Reviewer/verifier specialist files behave more like internal orchestration prompts than public agents.

### Governance, Artifact, and State Findings

- The constitution split is the largest governance ambiguity: root `CONSTITUTION.md` and workspace `.ai-engineering/CONSTITUTION.md` are both active in different surfaces.
- The current spec workspace is structurally broken for resumable execution: `spec.md` points to spec-117 while the generic `plan.md` still reflects completed spec-116 work.
- `manifest.yml` is useful but overloaded. It mixes user config, generated registry counts, ownership metadata, session bootstrap inputs, and policy hints.
- The state directory is too flat. Decisions, audit stream, gate cache, last findings, spec-local evidence, observation logs, and empty placeholders sit beside each other despite radically different lifecycles.
- `framework-capabilities.json` and `docs/solution-intent.md` already show source-of-truth drift against the manifest.

### Verification and Telemetry Findings

- The deterministic plane is strong but architecturally diffuse. The newer orchestrator, legacy gates, validator categories, verify service, hooks, and CI all participate in enforcement.
- The repo needs an explicit split between kernel-grade invariants, repo-governance validators, eval scenarios, and shell/adapter checks.
- Event vocabulary is not fully normalized: some schemas/validators still allow `copilot` while emitters and tests use `github_copilot`.
- Large test files and gap-filler suites increase the cost of deep refactors because they mix multiple contracts in one place.

### Repo Memory and Operational Lessons

- Mirror sync must complete before mirror validation; otherwise transient false failures appear.
- Event-emitting validations should run sequentially because multiple writers append to `framework-events.ndjson`, which can break the audit chain hash sequence.
- `decision-store.json` posture views must be treated as modeled/derived data, not as an unmodeled second source of truth.
- `manifest.version` and `manifest.framework_version` do not mean the same thing as `pyproject.toml [project].version` and must not be mass-aligned casually during cleanup.

## Current ai-engineering Facts

Loaded governance:

- `CONSTITUTION.md`: spec-driven development, TDD, dual-plane security, subscription piggyback, generated mirrors, supply-chain integrity, no suppressions, conventional commits, cognitive-debt telemetry.
- `.ai-engineering/manifest.yml`: framework version `0.4.0`, project version `1.0.0`, GitHub provider, enabled IDEs terminal/vscode, enabled AI providers Claude Code/Copilot/Gemini/Codex, stack Python.
- `.ai-engineering/state/decision-store.json`: active decisions include plan/dispatch split, flat main with feature branches, SonarCloud gate, dual VCS support, generated mirrors, canonical framework-events stream, artifact-driven releases, single-pass gate orchestrator, local fast-slice plus CI authoritative gate, and gate cache.
- `.ai-engineering/specs/spec-115...`: cross-IDE entry-point governance.
- `.ai-engineering/specs/spec-116...`: knowledge placement and governance cleanup.

Measured surfaces at drafting time:

- Canonical `.claude/skills/*/SKILL.md`: 49 skills, 5611 total lines.
- Canonical `.claude/agents/*.md`: 3715 total lines.
- Runtime Python under `src/ai_engineering`: 47636 total lines.
- Tests: 85325 total lines.
- State files: roughly 9490 lines total, including a large append-only event stream and several residual artifacts.

Pre-existing dirty worktree at drafting time:

- Modified skill files and generated mirrors for `ai-autopilot`, `ai-commit`, `ai-eval`, `ai-media`, `ai-pr`, `ai-video-editing`.
- Modified `.ai-engineering/instincts/meta.json`, `.ai-engineering/state/install-state.json`, `.claude/scheduled_tasks.lock`.
- Untracked `.ai-engineering/state/gate-cache/` and `gate-findings.json`.

Implementation agents must inspect these diffs before touching those surfaces and must not revert unrelated user work.

## Stable Seams to Preserve

- CLI bootstrap, envelope, and structured output model.
- VCS protocol and provider adapters.
- Release orchestration service shape.
- Installer/doctor phase pipeline concept.
- Manifest as machine-readable control plane.
- Append-only event stream as the audit substrate.

## Delete / Merge / Rewrite Candidates

- Dual constitutions in active runtime circulation.
- Dual gate/control planes and overlapping verification authority.
- Duplicated installer and doctor tooling logic.
- Duplicated manifest loaders and broad state models.
- Provider-local mirrors with stale `.claude` references.
- Template-shipped executable Python that duplicates packaged runtime behavior.
- Flat state surfaces that mix durable truth with cache/residue.
- Stale maintenance/reporting assumptions and broad, multi-contract test files.

## Engineering Standards to Codify

The user explicitly asked for these to be written down and made actionable:

- Clean Code.
- Clean Architecture.
- SOLID.
- DRY.
- KISS.
- YAGNI.
- TDD.
- SDD.
- Harness Engineering.

The program implication is that these should not only exist as prose. They should become canonical docs, review/verify rubrics, and where practical deterministic checks or templates.

## Program Implications

The exploration changed the character of spec-117 in five ways:

- It is a full-program root refactor of ai-engineering, not only a harness hardening pass.
- The first target is not runtime cleanup; it is control-plane and work-plane normalization so later rewrites have somewhere safe to land.
- The instruction problem is not only verbosity; it is canonical truth, mirror-local references, and generated provenance.
- The state problem is not only missing metrics; it is that durable truth and runtime residue are not clearly separated.
- The runtime problem is not only large files; it is duplicated control planes and subsystem boundaries that are not yet justified.

## Known / Assumed / Unknown

### Known

- The user wants a roadmap first, not runtime implementation.
- The roadmap should live under `.ai-engineering/specs/`.
- The project must respect the Constitution and current spec gates.
- The reference repo should inspire handoffs, progress state, checks, and orchestration.
- The program should explicitly allow deletion, merging, or rewriting of accidental framework surfaces.

### Assumed

- spec-117 remains the umbrella program spec for this root refactor.
- v1 remains local-first and incremental in execution even if the program scope is deep.
- Existing dirty worktree changes belong to the user or prior automation and are not part of this roadmap task.
- Future implementation will be split into follow-on specs rather than a single long-lived mega-branch.

### Unknown

- Which first implementation slice the user wants approved after the roadmap is reviewed.
- Whether worktree isolation should be mandatory for all shared-runtime edits.
- Whether instruction budgets should be hard caps or score-based with waivers.
- Whether the workspace constitution should be renamed, reduced, or removed.

