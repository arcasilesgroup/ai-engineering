# `.ai-engineering/`

Local governance root for a {ai} engineering workspace. Specs, plans, runtime state, framework references, and audit evidence live here so AI-assisted delivery remains reviewable as ordinary repository files.

See also: [root README](../README.md) | [AGENTS.md](../AGENTS.md) | [CONSTITUTION.md](../CONSTITUTION.md) | [persistence doctrine](../docs/persistence-doctrine.md)

## Quick Start

Install or refresh the framework, then start the governed flow:

```bash
ai-eng install .
ai-eng doctor
```

```text
/ai-start
/ai-brainstorm → /ai-plan → /ai-build → /ai-pr
```

[PASS] First success stays inline: install, verify, start, then move through the canonical chain.

## Installed Shape

```text
.ai-engineering/
├── LESSONS.md
├── manifest.yml
├── overrides/          # stack-specific conventions
├── reference/          # framework doctrine and authoring rules
├── runbooks/           # portable automation contracts
├── scripts/            # hooks and helper scripts
├── specs/              # active spec.md, plan.md, and lifecycle history
├── state/              # audit log, SQLite cache, risks, decisions
├── runtime/            # transient execution state such as autopilot runs
└── team/               # team-owned local conventions
```

## Four-Tier Persistence

The four-tier model is defined in [docs/persistence-doctrine.md](../docs/persistence-doctrine.md). Use one canonical writable store per datum:

| Tier | Store | Canonical for |
|------|-------|---------------|
| 1 | `state/framework-events.ndjson` | append-only framework events and gate decisions |
| 2 | `state/state.db` | stateful lifecycle data: decisions, risks, findings, ownership |
| 3 | `manifest.yml` and JSON/YAML state | machine-readable configuration |
| 4 | Markdown specs and references | human-authored doctrine, specs, plans, changelog, runbooks |

Derived caches must be rebuildable. Do not dual-write the same datum into two authoritative places.

## Specs and Runtime

| Path | Role |
|------|------|
| `specs/spec.md` | active approved specification |
| `specs/plan.md` | active execution plan |
| `specs/_history.md` | lifecycle ledger created when work closes |
| `runtime/autopilot/` | transient sub-specs, manifests, waves, and quality-loop evidence |
| `state/framework-events.ndjson` | append-only audit chain |
| `state/state.db` | rebuildable SQLite projection and lifecycle tables |

Autopilot writes to `.ai-engineering/runtime/autopilot/`, not `specs/autopilot/`.

## Ownership

[CONSTITUTION.md](../CONSTITUTION.md) defines ownership boundaries. In short:

- Framework-managed: `.ai-engineering/reference/`, `.ai-engineering/runbooks/`, `.ai-engineering/scripts/`, generated IDE mirrors, and installer templates.
- Team-managed: `.ai-engineering/team/`, product specs, and project-specific conventions.
- System-generated: `.ai-engineering/state/`, `.ai-engineering/runtime/`, review artifacts, and gate reports.

Do not hand-edit generated mirrors. Update canonical sources, then run:

```bash
ai-eng dev sync
ai-eng dev sync --check
```

## Reference Map

| Need | Start here |
|------|------------|
| AI operating rules | [AGENTS.md](../AGENTS.md) |
| Project identity and hard prohibitions | [CONSTITUTION.md](../CONSTITUTION.md) |
| Current configuration | [manifest.yml](manifest.yml) |
| Engineering principles | [principles](reference/principles.md) |
| Brand voice | [brand voice](reference/brand-voice.md) |
| Persistence doctrine | [docs/persistence-doctrine.md](../docs/persistence-doctrine.md) |
| Release notes | [CHANGELOG](../CHANGELOG.md) |

## Sync Contract

`ai-eng dev sync` regenerates IDE mirrors and template surfaces from canonical sources. `ai-eng dev sync --check` is the drift gate. If a mirror differs, fix the canonical source or generator; do not patch the mirror directly.
