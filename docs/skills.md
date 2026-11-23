# Skills

`ai-eng init` and `ai-eng update` install every skill from `skills/`, with its resources.
They write the skill files and never run them. Attribution for upstream skills travels with
them: [NOTICE.md](../NOTICE.md) and [THIRD-PARTY-NOTICES.md](../THIRD-PARTY-NOTICES.md).

One skill is the build loop: `ai-orchestrator`. Give it a feature. It splits the work into
checkpoints, smallest first, and builds each one through its gates. A checkpoint that fails a
gate does not move on. The loop stops for you twice: to approve the plan, and to review the
app.

- **Before the loop (optional):** `ai-brainstorm` pins the idea in plain words,
  `ai-research` brings evidence, `ai-architect` sets the layer rules.
- **After the loop (optional):** `ai-verify` gives a verdict, `ai-security` an audit,
  `ai-write` the updated docs.
- **Any time:** every other skill, on demand. None adds a required step.

Five triggers send work to the skill that declares them. A **path** trigger reads the diff. A
**judgment** trigger cannot be read from a diff, so the loop asks you once.

| Trigger | Kind | Skill | Fires when |
|---|---|---|---|
| `ui` | path | `ai-audit-design` | the diff touches TSX, JSX, CSS, SCSS, SASS, LESS, Vue, Svelte, components or the Tailwind config, outside `docs/` and `.ai-engineering/` |
| `security` | path | `ai-security` | the diff touches auth, sessions, crypto, secrets, SQL, migrations, dependency manifests, `.github/workflows/`, `src/chain/` or `src/guards/` |
| `open-questions` | judgment | `ai-research` | the brainstorm has open questions, or the plan cites an external API or version |
| `arch-change` | judgment | `ai-architect` | the work adds a subsystem, or changes a layer contract or a dependency direction |
| `public-interface` | judgment | `ai-write` | the diff changes a public interface, a documented behavior or a command shown in this README |

## All 27 skills

| Skill | What it does |
|---|---|
| `ai-adversarial-loop` | Debates a critic and a fixer, round after round, until the code is clean. The review gate of the loop |
| `ai-architect` | Advises on approach, stack, cost and prior art before the build starts |
| `ai-audit-code` | Finds the simplest solution that works: least code, fewest dependencies |
| `ai-audit-design` | Finds and fixes visual defects in a rendered page, by measurement |
| `ai-audit-docs` | Checks the docs against the repository: dead links, false claims, stale versions |
| `ai-brainstorm` | Questions a fuzzy idea until it fits in plain words, then asks for approval |
| `ai-codegraph` | Maps call chains, blast radius and cross-file links |
| `ai-debug` | Names the root cause at `file:line` and writes the failing check before the fix |
| `ai-design-md-planner` | Writes a `DESIGN.md` design system and lints it with the official CLI |
| `ai-explore` | Answers "where does this live", with `file:line` evidence |
| `ai-issue-report` | Drafts a bug report locally, with sensitive fields removed; sends nothing without your yes |
| `ai-note` | Saves a hard-won finding as committed Markdown, stamped so staleness shows |
| `ai-orchestrator` | Builds a feature end to end in gated checkpoints |
| `ai-pr` | Runs the pull request: cut, push, open, watch CI, merge. Your words decide how far it goes |
| `ai-prototype` | Builds a clickable single-file HTML prototype of a screen or flow |
| `ai-read-docs` | Reads the current docs before you depend on external or versioned behavior |
| `ai-refresh-project` | Aligns `AGENTS.md`, the docs, the governance files and the branches with the tree |
| `ai-research` | Answers from outside the repository with numbered sources, or marks a claim `[unsourced]` |
| `ai-review-ui` | Screenshots the live UI and its prototype, then compares them |
| `ai-security` | Runs a six-phase security audit; the finder never verifies its own findings |
| `ai-stress-test` | Finds the load that breaks the system |
| `ai-test-planner` | Plans and writes tests from the bottom layer up |
| `ai-triage` | Ranks one GitHub or Azure DevOps backlog in a read-only report |
| `ai-verify` | Checks finished work at the right depth and returns a verdict with evidence. Its lanes are in `skills/ai-verify/lanes/` |
| `ai-visual-recap` | Turns a diff into an interactive recap: diagrams, file map, annotated diff |
| `ai-write` | Writes a README, wiki page or API doc, verified against the tree |
| `ai-writing-behavior` | Writes `BEHAVIOR.md` specs for agent conduct that can be judged |
