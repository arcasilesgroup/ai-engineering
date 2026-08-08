---
id: "001"
slug: v1-from-scratch
---

# Plan — build order

Written as the order the tree was actually built in, because the dependency order is the
plan: the contracts had to exist before anything could be checked against them.

## 1. The record and the two contracts

- **file** `hooks/_emit.py`, `hooks/_wrap.py` · **check** `pytest -k closed_set` ·
  **rollback** delete both · **done when** the six event classes are a closed set and
  `emit` raises on anything else.
- **file** `hooks/chain.py` · **check** `pytest -k classified` · **rollback** delete ·
  **done when** every hook on a blocking event is a guard and the table is the only way in.

## 2. The guards

- **file** the five guards and the two telemetry hooks · **check**
  `python tests/adversarial/run.py` · **rollback** remove the row from `TABLE` ·
  **done when** each one is fired by a case in the suite and the clean control stays quiet.

## 3. The wiring

- **file** `policy/surfaces.toml`, `src/ai_engineering/wiring.py`, `surfaces/opencode.ts` ·
  **check** `ai-eng doctor` assertions 2, 13 and 21 · **rollback** `ai-eng uninstall` ·
  **done when** an entry exists per found surface and each points at a file that exists.

## 4. The ten verbs

- **file** `src/ai_engineering/*.py` · **check** the install matrix, which runs a
  stranger's first five minutes on three operating systems · **rollback** none needed;
  additive · **done when** `init`, `doctor`, `spec new`, `audit verify` and `uninstall`
  all run in a repository the tool has never seen.

## 5. CI/CD (mandatory — this ships)

- **file** `.github/workflows/check.yml`, `release.yml`, `install-matrix.yml` ·
  **check** the workflows' own runs, plus `zizmor` over them · **rollback** delete the
  workflow · **done when** the gate, the suite and the three-platform install all run on
  every push, and release publishes from a tag with attestations.

## 6. Observability (mandatory — this ships)

- **file** `hooks/_otlp.py`, `src/ai_engineering/digest.py` · **check**
  `pytest -k free_text` for the leak, `ai-eng doctor` assertion 20 for the void ·
  **rollback** clear the `[observability]` block · **done when** a canary in a free-text
  field never leaves the machine and a configured destination must answer 2xx with zero
  rejected records.

## Not doing

- The enterprise plugin artifact. Not built until a buyer under `allowManagedHooksOnly`
  asks, and named as the valve the budget would pull next.
- Azure Pipelines as a CLI surface. It ships as a documentation snippet with its three
  manual steps written beside it, because a YAML file in an Azure Repos repository is
  inert until a human registers a pipeline and its `pr:` block is ignored outright.
- The real-model half of the acceptance suite. It needs a key and spend that cannot run on
  somebody else's behalf; recorded as an accepted risk with a date.
