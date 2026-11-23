---
"ai-engineering": minor
---

Copilot, and every other IDE, in one measured capability matrix.

`docs/surface-capability-matrix.md` records, per host, what `ai-eng` enforces and what it
cannot: the hook event and where it lives, the denial envelope, whether a denied call is
really denied, how the host treats a broken guard, and whether the prompt hook blocks.
`ai-eng doctor` closes every `surface <id>` row with `enforced` or `advisory` from the same
table, and the README's tier table points at it.

`agy` (Antigravity CLI) is declared there as **advisory** and ships no hook. Its contract
was probed on 1.5.14 — a top-level `decision: deny` blocks a call, `{}` and any non-zero
exit deny, silence allows — but the payload names no repository, only `run_command` /
`CommandLine` are known, no rewrite field was measured, and a carrier line that says bare
`ai-eng` denies every tool call when the app the editor was launched from cannot resolve
the binary. `init --surface agy` refuses it like any surface with nowhere to run the
guards, and its skills are mirrored into `~/.gemini/config/skills`.
