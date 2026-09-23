# Research Cache: Git-backed sessions

**Topic:** Can ai-engineering adopt Agit's session-over-git model?
**Date:** 2026-09-23
**Report:** `.ai-engineering/research/006-git-backed-sessions.html`

## Key findings

1. **Agit stores sessions as git branches in ~/.agit** — each conversation = one branch (owner/repo@branch), each turn = one commit. Separate from code repo. [1][2]

2. **ai-engineering already has persistent state** — receipts in .ai-engineering/receipts/, loop state in cache, spec/plan in .ai-engineering/. The gap is NOT persistence, it's handoff. [codegraph]

3. **The #1 gap from research 005 is session handoff** — "20/90 sessions need 'continua' manual." Each continuation wastes 30-50 messages rebuilding state. [research 005]

4. **Three improvements worth making (not Agit's full model):**
   - R1: Session handoff briefing (auto-generate state at session start)
   - R2: Receipts with session_id field (group receipts by session)
   - R3: Research cache infrastructure (.ai-engineering/research-cache/)

5. **What NOT to adopt:** separate repo for sessions, fork/merge conversations, cross-runtime portability, Hub sharing. These are Agit's product, not ours.

6. **Agit's secret management is reactive (placeholder substitution); ours is preventive (spoken-secret guard at prompt time).** Our approach is better for our use case.

## Sources used

- agent-git.com docs (everyday, command-reference, quickstart, sharing, memory, mcp-skills)
- npm @einsia/agentgit
- Research 003 (prior Agit evaluation)
- Research 005 (skill pattern analysis — 90 sessions)
- Video transcript (AI Labs tutorial, nan whisper)

## Sources absent

- notebooklm (not configured)

## Three directions worth taking

1. **Implement R1 (session handoff briefing)** — the lowest-hanging fruit. When a session starts, auto-generate a JSON with: gates status, current plan step, recent denies, active overrides. This closes the "rebuild state" gap without git.

2. **Add session_id to receipts** — one field in the Receipt type, one line in writeReceipt(). Enables "what happened in session X?" queries in doctor.

3. **Create .ai-engineering/research-cache/** — already done. The next step is making doctor report on it and auto-pruning stale entries.
