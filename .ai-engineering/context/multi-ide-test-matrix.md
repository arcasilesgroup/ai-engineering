# Multi-IDE Test Matrix

Validation checklists for verifying ai-engineering framework compatibility across IDEs.

## Claude Code (Automated)

Automated via `ai-eng` CLI:

```bash
# 1. Verify CLAUDE.md is loaded
ai-eng governance diff  # checks CLAUDE.md consistency

# 2. Verify skill invocation
# Test: /ai:plan on a trivial task
# Expected: plan agent activates, reads _active.md, produces spec

# 3. Verify checkpoint protocol
ai-eng checkpoint save --spec-id test --current-task 1.1 --progress 1/5 --reasoning "test"
ai-eng checkpoint load

# 4. Verify gate enforcement
ai-eng gate pre-commit
ai-eng gate commit-msg .git/COMMIT_EDITMSG

# 5. Verify doctor
ai-eng doctor --json

# 6. Verify signals
ai-eng signals emit test_event --actor=test --detail='{"test":true}'
```

- [ ] CLAUDE.md loaded and respected
- [ ] Skills invoke correctly (/ai:plan, /ai:commit)
- [ ] Checkpoint save/load works
- [ ] Gates enforce prohibitions
- [ ] Doctor reports all checks
- [ ] Signals emit to audit-log.ndjson

## GitHub Copilot (Semi-Automated)

1. Open project in VS Code with Copilot Chat
2. Verify `.github/copilot-instructions.md` is loaded (ask Copilot about the project)

- [ ] Copilot references governance rules
- [ ] Copilot respects session start protocol (reads _active.md when prompted)
- [ ] Spec-as-Gate pattern works (Copilot produces spec as text)
- [ ] Skill invocation via `/ai:plan` works
- [ ] Prohibitions are respected (no --no-verify suggestions)
- [ ] Quick Reference info is accurate

## Gemini CLI (Semi-Automated)

1. Open project with Gemini CLI
2. Verify `GEMINI.md` is loaded

- [ ] GEMINI.md loaded and respected
- [ ] Skills table accurate (35 skills listed)
- [ ] Agents table accurate (7 agents listed)
- [ ] Progressive disclosure pattern followed (loads metadata first)
- [ ] Session start protocol followed
- [ ] Prohibitions respected

## Codex (Manual)

1. Open project with OpenAI Codex CLI
2. Verify `AGENTS.md` is loaded

- [ ] AGENTS.md loaded and respected
- [ ] Behavior mandates followed (think protocol, parallel execution)
- [ ] Platform adaptors referenced correctly
- [ ] Session start protocol followed
- [ ] Prohibitions respected
- [ ] Checkpoint protocol works

## Cross-IDE Consistency

After running individual IDE tests:

- [ ] All IDEs reference same governance source
- [ ] Skill counts match across all files (35)
- [ ] Agent counts match across all files (7)
- [ ] Prohibitions are identical across all files
- [ ] `ai-eng governance diff` reports zero drift
