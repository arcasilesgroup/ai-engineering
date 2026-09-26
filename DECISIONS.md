# DECISIONS.md

One standing decision per block. Read the one that covers an area before changing it. To reverse a decision, add a new block that supersedes it. Do not edit the old block.

## D-001: ai-engineering governs this repo

Status: Accepted · Date: 2026-09-15

### Context

A repo with no contract leaves every agent to invent its own rules. The same decision, made the same way every time, belongs in code.

### Decision

{ai} Engineering 2.2.0 is installed here: global skill canon, local receipts, git floor on.

### Consequences

- Init, doctor, and the chain are the contract.
- A machine without the canon is not governed.

### Alternatives considered

- **Per-repo copies of the skills:** they drift. Rejected.

## D-002: Governance improves by observability, not by more stoppers

Status: Accepted · Date: 2026-09-20

### Context

The policy guard finished the command-scope half of least agency. Least agency without a record of what was denied is blind. Evidence is in research/001.

### Decision

The next milestone takes research/001 R1 (richer gc aggregate: per guard, tool, and surface, plus a daily series and a baseline-deviation warning) and R2 (a cross-session deny ledger that is signal only, never a verdict). R3, an OTLP alias, stays off unless there is real demand.

### Consequences

- Receipts keep the signal the 30-day sweep used to throw away.
- A repeated deny is reported. It does not become an automatic block.

### Alternatives considered

- **More stoppers:** they hide the pattern. Rejected.

## D-003: Observability ships as signal inside the gc

Status: Accepted · Date: 2026-09-21

### Context

Receipts already carried the story. The 30-day sweep deleted it.

### Decision

R1 and R2 are built: a richer summary.json, a denies.json ledger, and a deviation warning at 3x. R3 (OTLP) and the injection fold-miss stay out until real demand. If after 90 days the ledger recorded zero repeats and doctor flagged zero deviations on this repo, the layer is removed.

### Consequences

- Doctor can say what is being denied, and how often.
- A layer that never fires does not stay as ceremony.

### Alternatives considered

- **Ship OTLP now:** no consumer asked. Rejected.

## D-004: The prompt is the one leak surface gitleaks cannot see

Status: Accepted · Date: 2026-09-22

### Context

Gitleaks sees shaped keys in commits. The floor already blocks those. A secret a person types enters the transcript before any commit exists. After the turn ends, reverting does not take the bytes out of the history.

### Decision

The spoken-secret guard blocks a prompt that carries a low-entropy credential, with advice, and never echoes the value. It runs on UserPromptSubmit where the host exposes that event (Claude Code, Codex). It stays off, with the cause named, where the host ignores the output or has no prompt event (Copilot, Cursor, Oh My Pi, OpenCode, Pi).

### Consequences

- The only window that works is the turn the secret is typed.
- Hosts without a prompt hook are named, not pretended.

### Alternatives considered

- **Scan the transcript later:** the bytes are already stored. Rejected.
