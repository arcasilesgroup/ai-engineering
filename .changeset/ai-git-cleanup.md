---
"ai-engineering": minor
---

skills: ai-git-cleanup v3 — action-first cleanup: phase 0 automatically makes the checkout safe to move (auto-stash a dirty tree, switch to the default branch, ff-only pull pinned to that branch as destination with HEAD already there, WARN-and-continue), phase 1 classifies every local branch deterministically in code with protection filtered before triage and named evidence on every batch entry, phase 2 asks exactly once per delete batch (delete all, pick, or stop — never zero confirmations), and phase 3 executes the batch then prints the per-branch report (previous branch, stash state, and action/reason/upstream/ahead/behind rows) — local git only: no push, no remote deletion, no reflog GC, no CI.
