---
name: ai-adversarial-loop
description: Coordinate a multi-round debate between two agents until the code is clean. adversarial-reviewer (the critic) assumes everything is wrong; fixer implements fixes or disputes them with evidence. They exchange findings through a shared thread file, and each keeps its memory across rounds. Use as the orchestrator's review gate, or when the user asks for an adversarial review-and-fix loop on recent changes (e.g. "/ai-adversarial-loop", "have the critic and fixer go at checkpoint 3").
license: MIT
---

# Adversarial loop

You are the **coordinator**. You run in the main session because only the main session can start and resume agents. Subagents can't launch other agents, and agent-team teammates can't be the lead. You never review code or fix it yourself, and you **never read the thread file**. You pass turns between the two agents and act on their short returns.

## Setup

- **Thread file:** under `/ai-orchestrator`, it's `.ai-engineering/workflow/reviews/<slug>-<id>.md`. Standalone, it's `.ai-engineering/workflow/reviews/<topic>-<YYYY-MM-DD>.md`. Create it with a header: the checkpoint's goal and acceptance criteria (or the user's scope), the `changed_files`, and the verify commands. Nothing else.
- **Scope:** the checkpoint slice and `changed_files`. Run from the selected checkout, whether that is the current checkout or its chosen worktree. Standalone, it's `git diff HEAD` plus untracked files, and the verify commands are the full test suite, lint and build from the **Project config** section of `AGENTS.md`.
- **Under `/ai-orchestrator`,** prompts start with the gate markers: `[checkpoint <slug>#<id> review]` for the critic and `[checkpoint <slug>#<id> fix]` for the fixer.

## Rounds under `/ai-orchestrator`

One critic round. The fixer is the builder the orchestrator already has, resumed with `[checkpoint <slug>#<id> fix]`. Do not start a separate `fixer` agent, an arbiter, or a third round.

1. **Critic, round 1:** start `adversarial-reviewer` with the scope, the thread path, the verify receipt, and "Debate mode, round 1". Keep its agent ID. `VERDICT: PASS` ends the loop.
2. **One fix:** a BLOCKER or MAJOR resumes the builder. Then resume the same critic once: "Round 2: the builder has responded, see the thread. Rule on those findings."
3. A second FAIL returns FAIL to the orchestrator. PASS ends the loop.

## Rounds standalone (at most 4)

1. **Critic, round 1:** start `adversarial-reviewer` with the scope, the thread path and "Debate mode, round 1". Keep its agent ID. If it returns `VERDICT: PASS`, you're done; go to the end.
2. **Fixer, round N:** start the `fixer` agent with the thread path, the scope and "round N". On later rounds, resume the **same** fixer with SendMessage and its ID: "Round N: the critic has ruled, see the thread." Add its `FILES` to `changed_files`.
3. **Critic, round N+1:** resume the **same** critic with SendMessage: "Round N+1: the fixer has responded, see the thread. Verify, rule, and attack the new changes."
4. `VERDICT: PASS` ends the loop. Otherwise repeat from step 2.

The critic remembers what it flagged, and the fixer remembers what it changed. They stay isolated from each other and from you, and the thread file is the only thing they share.

## Deadlock and the round cap

Standalone only. Under `/ai-orchestrator` there is no arbiter and no fourth round.

- **Deadlock:** if a finding is `upheld` twice after a dispute, the two agents disagree. The critic flags this in its return as `DEADLOCK: F<n>` (you never read the thread, so that line is how you know). Start a **fresh** `general-purpose` arbiter. Give it only that finding's block from the thread, the files it cites, `AGENTS.md` and `DECISIONS.md`. It rules `critic` or `fixer` and writes `**Arbiter:** <ruling, why>` into the thread. If it rules for the fixer, it marks the finding `withdrawn`. If it rules for the critic, the fixer must fix it next round and can't dispute it again.
- **Round cap:** after 4 critic rounds without a PASS, stop the loop and report the open findings to the user.

## At the end

- **Learnings:** for every `LESSON:` line the fixer returned, and every arbiter ruling, append a Log entry to `docs/history/learnings-log.md` (append-only, continuing its numbering) and, when it qualifies, promote it into a `LEARNINGS.md` Rule with gate `review`. Disputes the critic withdrew are learnings for the critic; tag them `review-noise`. The worker does not open the log to find a tag; the orchestrator pastes the rules that apply.
- **Commit:** under `/ai-orchestrator`, do not commit inside the loop. The orchestrator makes one commit when the checkpoint passes. Standalone, commit the thread and the fixer's files as `fix(<topic>): review round <k>` and `chore(<topic>): review passed`. The scope has no `#`.
- **Return** (to the orchestrator, or tell the user), in at most 6 lines:
  - PASS or FAIL;
  - the number of rounds;
  - resolved, withdrawn and arbitrated counts;
  - the open findings, only if it failed;
  - `changed_files`;
  - the thread path.
- **Re-check after fixes:** if the fixer changed any code, the builder re-runs verify and returns a new receipt. That receipt is the behavior gate. Re-run the UI gate only when the checkpoint has one. The critic is not asked to re-run verify when the receipt is present.

## Lifecycle

Lane: standard, full
Writes: .ai-engineering/workflow/reviews
Read by: ai-orchestrator, humans
Dies: when the review gate passes or the loop stops
Next: none
