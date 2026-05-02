# Guard Review: HX-03 T-2 Mirror Inventory Reference Model

## Verdict

- `PASS-WITH-NOTES`

## Findings

- Concern: `manual-instructions` is modeled as manual/non-generated in the shared inventory, but the instruction generation pipeline still writes generated language instruction files into that same surface. Provenance semantics are therefore mixed inside `.github/instructions/`.
- Warning: `specialist-agents` is correctly excluded from the public Copilot `.agent.md` contract, but the shared inventory currently models it only as a GitHub Copilot family even though internal specialist mirrors are still copied into Codex, Gemini, and template surfaces.
- Info: filtered public counts and provider compatibility look sufficient for the next phase. The current shared inventory and tests do not expose an obvious blocker for Phase 3 leak/filter work.

## Outcome

- Phase 3 test work can proceed now.
- The mixed provenance of generated instruction files and the incomplete specialist-family modeling stay queued as local HX-03 follow-up gaps rather than blockers for provider-leak tests.