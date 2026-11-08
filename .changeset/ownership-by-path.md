---
"ai-engineering": patch
---

What ai-eng wrote is ai-eng's, and `init`, `update`, `config` and `uninstall` now treat it that way every time — no more half-updated installs.

- A skill folder ai-eng ships is ai-eng's whole. An edited page in it is rewritten to the installed version, and any file it does not ship is removed (names starting with a dot, such as `.DS_Store`, are left alone) — including the pages older releases left behind that 3.0.1 reported as "cannot prove it wrote" and never deleted. Keep your own skills in a folder with a name of your own: those are never touched.
- A skill, agent or script ai-eng stops shipping is removed on the next `init` or `update`, with its mirror links in `~/.claude/skills`, `~/.agents/skills` and `~/.config/opencode/skill` and its OpenCode slash command.
- The slash command of an ai-eng skill, an ai-eng agent copied into `~/.claude/agents`, and a machine carrier module (OpenCode, OMP, Pi) always hold ai-eng's bytes, even after an edit. A link of yours at those names is still never written through.
- In the repo, `update` no longer asks "What wins?": a file ai-eng wrote (CI workflow, git hook shims, carriers) is rewritten even when edited — an edit you committed stays in git; an uncommitted one (a hook shim is never committed) is overwritten, so copy it first — and `uninstall` removes it. One that ai-eng stops shipping is removed on the next `update`. A git hook shim is the one exception on the way out: `uninstall` removes it only while it still carries the ai-eng shim marker. A file ai-eng never wrote stays yours, and `init` no longer records as ai-eng's a file already there whose bytes differ from ai-eng's.
- Seeded config is the exception: `.ai-engineering/config.toml`, `overrides.toml` and `arch.rules.json` follow ai-eng while untouched and become yours on your first edit.
- `doctor` drops the "canon unproven" row: every extra in a shipped skill folder is counted as stale, and `ai-eng update` sweeps it.
