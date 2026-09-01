# {ai} Engineering v2

**Plant. Guard. Prove.** — governance floor for AI coding agents.

One binary (`ai-eng`, Bun `--compile`), ~3.8k LOC of our own TypeScript, and a
global canon of 19 integrated skills. The creative work stays with your agent in
its IDE; ai-eng puts the floor under its feet:

- **5 guards compiled in the binary** — no-verify, self-protect, injection, loop,
  wrap. Editing a markdown file switches nothing off; the only bypass is
  `.ai-engineering/overrides.toml` with a written reason and an expiry date.
- **The git floor** — `core.hooksPath` shims that run gitleaks, the DECISIONS.md
  gate, and the `Receipt-Id` trailer even when the agent is not involved.
- **The executable contract** — `spec.html` (QUÉ) + `plan.html` (CÓMO) per
  milestone; a contract nobody approved refuses to run, and a check that cannot
  run is red, never silent green.
- **Proof > promise** — one receipt per execution; `doctor` executes a real
  adversarial payload and measures real latency.

## Install

```bash
bun add -g ai-engineering   # → ai-eng in PATH
```

## Use

```bash
cd my-project && ai-eng init   # plants the contract (creates the repo if needed)
ai-eng doctor                  # 12 checks + one real test
```

Human verbs: `init · doctor · config · update · upgrade · uninstall`.
Machine verbs (called by hooks and CI, no human UX): `chain · git · wrap · spec`.

## Skill canon

19 skills (`ai-proof`, `ai-plan`, `ai-goal`, `ai-verify`, `ai-security`, …) live
once per machine in `~/.ai-engineering/skills/` and are symlinked per surface
(`~/.claude/skills`, `~/.agents/skills`, `~/.config/opencode/skill`). Attribution
and licenses: NOTICE.md.

## Development

```bash
bun install
bun run build        # the binary IS the payload — skills/templates are embedded
bun test             # unit + adversarial (H1 oracle)
bun run arch         # archunit over .ai-engineering/arch.rules.json
bunx tsc --noEmit    # typecheck
```

License: Apache-2.0 (see LICENSE, NOTICE.md, THIRD-PARTY-NOTICES.md).
