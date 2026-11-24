<div align="center">

<h1><picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/hero-dark.webp">
  <img src=".github/assets/readme/hero-light.webp" alt="{ai} engineering. Guardrails for the AI Coding Agents you already run" width="100%">
</picture></h1>

<b>Turn any repo into a governed workspace.</b><br/>
The agent can't edit its own rules, and every refusal it gets is saved as a file you can read.

<a href="#get-it"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/button-start-dark.webp"><img src=".github/assets/readme/button-start-light.webp" alt="Get started" width="180"></picture></a>&nbsp;&nbsp;<a href="#measured"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/button-proof-dark.webp"><img src=".github/assets/readme/button-proof-light.webp" alt="See the proof" width="200"></picture></a>

<sub>Bun 1.4.4+ · macOS · Linux · Windows · Apache-2.0 · Runs on your machine and calls no model · 7 of 10 agent hosts enforced and verified on 2026-11-23</sub>

<p>
  <a href="https://github.com/arcasilesgroup/ai-engineering/releases/latest"><img alt="release" src="https://img.shields.io/github/v/release/arcasilesgroup/ai-engineering?style=flat-square&amp;labelColor=001E2B&amp;color=00684A&amp;label=release"></a>
  <a href="https://www.npmjs.com/package/ai-engineering"><img alt="npm" src="https://img.shields.io/npm/v/ai-engineering?style=flat-square&amp;labelColor=001E2B&amp;color=00684A&amp;logo=npm"></a>
  <a href="https://github.com/arcasilesgroup/ai-engineering/actions/workflows/check.yml"><img alt="check workflow status" src="https://img.shields.io/github/actions/workflow/status/arcasilesgroup/ai-engineering/check.yml?branch=main&amp;style=flat-square&amp;labelColor=001E2B&amp;label=check"></a>
  <a href="https://sonarcloud.io/component_measures?id=arcasilesgroup_ai-engineering&amp;metric=coverage"><img alt="test coverage on SonarCloud" src="https://img.shields.io/sonar/coverage/arcasilesgroup_ai-engineering?server=https%3A%2F%2Fsonarcloud.io&amp;style=flat-square&amp;labelColor=001E2B&amp;color=00684A"></a>
  <a href="LICENSE"><img alt="license" src="https://img.shields.io/github/license/arcasilesgroup/ai-engineering?style=flat-square&amp;labelColor=001E2B&amp;color=00684A"></a>
</p>

<sub><a href="#guards">Guards</a> · <a href="#receipts">Receipts</a> · <a href="#skills">Skills</a> · <a href="#fail-closed">Fail closed</a> · <a href="#your-repo">Your repo</a> · <a href="#measured">Measured</a> · <a href="#where-it-stops">Known limits</a> · <a href="#under-the-hood">Under the hood</a> · <a href="#release">Release</a> · <a href="#answers">Answers</a> · <a href="#get-it">Get it</a> · <a href="#build-with-us">Build with us</a></sub>

</div>

<h2 id="guards" align="center"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/heading-guards-dark.webp"><img src=".github/assets/readme/heading-guards-light.webp" alt="Refused before it runs" width="600"></picture></h2>

<p align="center"><code>--no-verify</code> is only one way to skip a hook. <code>git commit -n</code> and <code>HUSKY=0</code> are refused before git starts too, and the agent is told why.</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/guards-refused-dark.webp">
    <img src=".github/assets/readme/guards-refused-light.webp" alt="Three hook-skipping commands refused before git starts by the no-verify guard: git commit --no-verify returns deny (--no-verify skips the git hooks. Run the command without it.) git commit -n -m fix returns deny (git commit -n skips the git hooks. Fix what they would flag.) HUSKY=0 git commit -m fix returns deny (an environment flag skips the git hooks. Refused before git starts.) The stderr artifact prints the live no-verify denial message and exits with status 2." width="880">
  </picture>
  <br/><sub>Source: <a href="src/guards/no-verify.ts"><code>src/guards/no-verify.ts</code></a>. Linter-silencing edits (<code>eslint-disable</code>, <code>@ts-ignore</code>, <code>noqa</code>) are refused the same way; recognised test runs are rewritten to <code>ai-eng wrap test</code>, which prints only the failures.</sub>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/figure-1-tool-call-dark.webp">
    <img src=".github/assets/readme/figure-1-tool-call-light.webp" alt="Figure 1. The agent proposes a tool call. The ai-eng chain judges it before it runs. The verdict is allow, annotate or deny. On allow or annotate the tool runs; on deny the tool never runs and the agent is told why. Every verdict writes a receipt file in .ai-engineering/receipts/." width="880">
  </picture>
  <br/><sub><b>Figure 1.</b> One tool call. The refusal arrives before the tool runs, so the call never starts. The dashed line is a check, not a step: a guard that crashes or cannot decide also ends in a refusal.</sub>
</p>

<details>
<summary>Text version of figure 1</summary>

1. The agent proposes a tool call: a command, an edit or a read.
2. The host sends the call to `ai-eng chain`, which runs the guards in a fixed order. The first refusal wins.
3. The verdict is allow (a recognised test command is rewritten to show only failures), annotate (the call goes ahead with a review note) or deny (the call is refused, with the reason).
4. On allow or annotate the tool runs. On deny it never runs, and the agent is told why and what to do instead.
5. A guard that crashes or cannot decide ends in a refusal.
6. Every verdict writes one JSON file to `.ai-engineering/receipts/`.

</details>

<table align="center">
  <tr>
    <td><picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/card-blocks-dark.webp"><img src=".github/assets/readme/card-blocks-light.webp" alt="Blocks. Refused before the call runs: --no-verify, git commit -n and HUSKY=0; a comment that silences a linter; an edit to the hooks or .ai-engineering/. On the 7 hosts enforced and verified." width="420"></picture></td>
    <td><picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/card-informs-dark.webp"><img src=".github/assets/readme/card-informs-light.webp" alt="Informs. Told, not stopped: zed and agy get skills and advice, no refusal; a review verdict lets the call go ahead with a note; ai-eng doctor warns about drift and false alarms. Nothing here stops the agent." width="420"></picture></td>
  </tr>
</table>

Seven protection guards read each governed tool call and answer before the tool runs. The cards split what stops the agent from what only tells it. The hosts where a refusal stands are in [Where the agent still can](#where-it-stops).

<details>
<summary>The nine checks, in order</summary>

Each guard runs only for the tools it governs, in this order, and the first refusal wins:

| Order | Guard | Refuses |
|---|---|---|
| 1 | `self-protect` | writes to anything that governs the agent: `.ai-engineering/` (except the milestone files a session owns), the agent settings, the git hooks, the installed skills |
| 2 | `no-verify` | anything that skips the git hooks: `--no-verify`, `git commit -n`, `HUSKY=0`, deleting the hooks folder, repointing `core.hooksPath`. And every comment that silences a linter or a type checker: ESLint, TypeScript, Ruff and Flake8, Bandit, clang-tidy |
| 3 | `no-stash` | creating a stash, which takes work off its branch; `list`, `show`, `apply`, `pop` and `branch` still work |
| 4 | `policy` | commands outside the allowed scope (see [configuration](docs/configuration.md)) |
| 5 | `injection` | reading a file, or acting on a fetched page, whose text carries instructions to the model. The text is data, never an order |
| 6 | `loop` | the same call repeated, or the same failure retried with small changes |
| 7 | `checkpoint` | phase and gate writes that break the active workflow checkpoint. It is the workflow gate, not a protection guard |
| 8 | `lease` | a write in a folder another session wrote in during the last 15 minutes. The second session goes to a worktree; `ai-eng work release` frees the folder |
| 9 | `wrap` | nothing. It rewrites a recognized test command to `ai-eng wrap test -- <command>`, which prints only the failures and a summary |

`spoken-secret` checks each prompt you submit, on agents with a prompt hook. It refuses a prompt that seems to contain a credential, and it never prints the value it found.

</details>

<h2 id="receipts" align="center"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/heading-receipts-dark.webp"><img src=".github/assets/readme/heading-receipts-light.webp" alt="Every refusal on file" width="600"></picture></h2>

<p align="center">Git keeps no record of a skipped check. ai-eng saves every answer as a small file in your repo, so you can see what the agent tried.</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/receipts-ledger-dark.webp">
    <img src=".github/assets/readme/receipts-ledger-light.webp" alt="Three receipt files accumulating in .ai-engineering/receipts/: 7d07ec0d.json (Bash, denied by no-verify, 3 ms, outcome deny); c6f8ffd7.json (Edit, denied by self-protect, 2 ms, outcome deny); a20c2d8e.json (Bash, denied by none, 3 ms, outcome allow). A receipt is a log, not proof. Each verdict writes one JSON file in .ai-engineering/receipts/. Anyone who can write to that folder can write one, so treat it as an audit trail, never as cryptographic evidence." width="880">
  </picture>
  <br/><sub>Source: <a href="src/receipts.ts"><code>src/receipts.ts</code></a>. One JSON file per verdict in <code>.ai-engineering/receipts/</code>, plus <code>denies.json</code> for repeat counts.</sub>
</p>

<h2 id="skills" align="center"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/heading-skills-dark.webp"><img src=".github/assets/readme/heading-skills-light.webp" alt="Skills, sorted by the job" width="600"></picture></h2>

<p align="center">27 skills, grouped by job. One finds a bug's cause before it touches code; another builds a feature in small steps and asks for your yes twice.</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/skills-grid-dark.webp">
    <img src=".github/assets/readme/skills-grid-light.webp" alt="The 27 skills in six groups. Shape the idea: ai-brainstorm, ai-research, ai-architect, ai-read-docs. Build it: ai-orchestrator, ai-test-planner, ai-prototype, ai-design-md-planner. Understand the code: ai-explore, ai-codegraph, ai-debug, ai-note. Check the work: ai-verify, ai-adversarial-loop, ai-security, ai-stress-test, ai-audit-code, ai-audit-design, ai-review-ui. Ship and write it up: ai-pr, ai-write, ai-audit-docs, ai-visual-recap, ai-issue-report. Keep the repo in order: ai-triage, ai-refresh-project, ai-writing-behavior." width="880">
  </picture>
  <br/><sub>Every skill is a plain instruction file your agent follows. Use any of them, or none.</sub>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/figure-2-loop-dark.webp">
    <img src=".github/assets/readme/figure-2-loop-light.webp" alt="Figure 2. The build loop of ai-orchestrator. Your idea goes to a plan after you approve the idea. The plan becomes numbered checkpoints, built one at a time and each gated before the next; a checkpoint that fails a gate does not move on. You review the app, and it ships as a pull request or a local merge." width="880">
  </picture>
  <br/><sub><b>Figure 2.</b> The build loop. A checkpoint that fails a gate does not move on, and the loop stops for you twice: to approve the idea before it builds, and to review the app before it ships.</sub>
</p>

<details>
<summary>Text version of figure 2</summary>

1. You give `ai-orchestrator` a feature, in your own words. You approve the idea: that is the first stop.
2. It splits the work into numbered checkpoints, smallest first.
3. It builds one checkpoint at a time and gates each before the next. A checkpoint that fails a gate does not move on.
4. You review the app: that is the second stop.
5. On your approval, it ships as a pull request or a local merge.

</details>

<details>
<summary>All 27 skills, one line each</summary>

| Group | Skill | What it does |
|---|---|---|
| Shape the idea | `ai-brainstorm` | Questions a fuzzy idea until it fits in plain words, then asks for approval |
| | `ai-research` | Answers from outside the repository with numbered sources, or marks a claim `[unsourced]` |
| | `ai-architect` | Advises on approach, stack, cost and prior art before the build starts |
| | `ai-read-docs` | Reads the current docs before you depend on external or versioned behavior |
| Build it | `ai-orchestrator` | Builds a feature end to end in gated checkpoints |
| | `ai-test-planner` | Plans and writes tests from the bottom layer up |
| | `ai-prototype` | Builds a clickable single-file HTML prototype of a screen or flow |
| | `ai-design-md-planner` | Writes a `DESIGN.md` design system and lints it with the official CLI |
| Understand the code | `ai-explore` | Answers "where does this live", with `file:line` evidence |
| | `ai-codegraph` | Maps call chains, blast radius and cross-file links |
| | `ai-debug` | Names the root cause at `file:line` and writes the failing check before the fix |
| | `ai-note` | Saves a hard-won finding as committed Markdown, stamped so staleness shows |
| Check the work | `ai-verify` | Checks finished work at the right depth and returns a verdict with evidence |
| | `ai-adversarial-loop` | Debates a critic and a fixer, round after round, until the code is clean |
| | `ai-security` | Runs a six-phase security audit; the finder never verifies its own findings |
| | `ai-stress-test` | Finds the load that breaks the system |
| | `ai-audit-code` | Finds the simplest solution that works: least code, fewest dependencies |
| | `ai-audit-design` | Finds and fixes visual defects in a rendered page, by measurement |
| | `ai-review-ui` | Screenshots the live UI and its prototype, then compares them |
| Ship and write it up | `ai-pr` | Runs the pull request: cut, push, open, watch CI, merge. Your words decide how far it goes |
| | `ai-write` | Writes a README, wiki page or API doc, verified against the tree |
| | `ai-audit-docs` | Checks the docs against the repository: dead links, false claims, stale versions |
| | `ai-visual-recap` | Turns a diff into an interactive recap: diagrams, file map, annotated diff |
| | `ai-issue-report` | Drafts a bug report locally, with sensitive fields removed; sends nothing without your yes |
| Keep the repo in order | `ai-triage` | Ranks one GitHub or Azure DevOps backlog in a read-only report |
| | `ai-refresh-project` | Aligns `AGENTS.md`, the docs, the governance files and the branches with the tree |
| | `ai-writing-behavior` | Writes `BEHAVIOR.md` specs for agent conduct that can be judged |

None of this is required to get the refusals above. The triggers that send a change to a skill are in [docs/skills.md](docs/skills.md).

</details>

<h2 id="fail-closed" align="center"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/heading-fail-closed-dark.webp"><img src=".github/assets/readme/heading-fail-closed-light.webp" alt="Unsure means no" width="600"></picture></h2>

<p align="center">If a check breaks or cannot decide, the answer is no. Copilot and Codex are the exceptions, and this section says when.</p>

<table align="center">
  <tr>
    <td><b>Crash means refuse.</b> A guard that crashes refuses the call.</td>
    <td><b>Unsure means refuse.</b> A guard that cannot decide refuses it too.</td>
  </tr>
  <tr>
    <td><b>One written bypass.</b> The loop guard reads <code>.ai-engineering/overrides.toml</code>; an entry there needs a <code>reason</code> and an <code>until</code> date. No other guard reads that file.</td>
    <td><b>Expiry turns it back on.</b> <code>ai-eng doctor</code> lists every active entry with its time left. When the date passes, the loop guard is on again.</td>
  </tr>
</table>

The exceptions are real. The Copilot adapter (CLI and VS Code) fails open on a timeout and when `ai-eng` is not on `PATH`, and Codex fails open on a hook error. Both are in [Where the agent still can](#where-it-stops), next to the dated host matrix.

<h2 id="your-repo" align="center"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/heading-your-repo-dark.webp"><img src=".github/assets/readme/heading-your-repo-light.webp" alt="The rules live in your repo" width="600"></picture></h2>

<p align="center">They are files in git, reviewed like code. The agent can edit <code>AGENTS.md</code> and <code>DECISIONS.md</code> and cannot edit the machinery that governs it; turning the loop guard off takes a dated entry that expires.</p>

- **Versioned files.** `AGENTS.md`, `DECISIONS.md`, `.ai-engineering/config.toml` and the git hooks sit in your repository, plus `~/.ai-engineering/` on your machine.
- **Self-protected.** `self-protect` is the first guard in the order. The agent cannot write to the files that govern it; a person changes them in a reviewed diff.
- **Local only.** 0 hosted services, 0 model calls. No prompt and no source leaves the machine.
- **One optional network read.** Commands you type ask the npm registry for a newer version at most every 24 hours. Set `AI_ENG_NO_UPDATE_NOTICES=1` and it never does. Offline, the check stays silent.

<h2 id="measured" align="center"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/heading-measured-dark.webp"><img src=".github/assets/readme/heading-measured-light.webp" alt="Numbers you can rerun" width="600"></picture></h2>

<p align="center">On our Mac, 95 in 100 checks add under 3 milliseconds; 7 of the 10 agents we list are enforced and tested. Each one can be rerun.</p>

<table align="center">
  <tr>
    <td align="center"><p><strong>2,600+</strong></p><b>tests in the suite</b><br/><sub>2,695 passing, 1 skipped, 0 failing on 2026-11-23 · <code>bun test</code></sub></td>
    <td align="center"><p><strong>12</strong></p><b>false alarms we fixed, each paired with the attack it looks like</b><br/><sub>each one now passes, each paired attack is still refused · <code>bun test tests/friction-corpus.spec.ts</code></sub></td>
    <td align="center"><p><strong>under 3 ms</strong></p><b>added to a tool call, 95th percentile</b><br/><sub>2.56, 2.64 and 2.72 ms in three runs of 100 calls · <code>bun run bench</code></sub></td>
    <td align="center"><p><strong>7 of 10</strong></p><b>agent hosts enforced and verified</b><br/><sub>1 enforced but unverified, 2 advisory only · <a href="docs/surface-capability-matrix.md">capability matrix</a></sub></td>
  </tr>
</table>

<p align="center"><sub>Measured by the maintainers on one Mac (arm64) on 2026-11-23, on top of commit <code>efc35b38</code>. Test results on our machine, not a promise about yours.</sub></p>

Want the figure for your repo? `ai-eng doctor` counts refusals per 1,000 real tool calls from your own receipts, and warns above 50 or on any call you mark as a false alarm. We publish the method and the test corpus. We do not publish anyone's receipts, our own included.

<table align="center">
  <tr>
    <td><b>Every refusal has a twin.</b> Each false alarm we fixed sits next to the real attack it resembles, and both are tested.</td>
    <td><b>The gates are tested too.</b> Each one runs against fixtures that break exactly one rule.</td>
  </tr>
  <tr>
    <td><b>Mutants on the checks.</b> Mutation testing runs on the checks, and the build fails below a score of 58 (<code>stryker.conf.mjs</code>).</td>
    <td><b>Six adversarial suites.</b> Written to break the chain, in <a href="tests/adversarial"><code>tests/adversarial/</code></a>.</td>
  </tr>
</table>

<h2 id="where-it-stops" align="center"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/heading-where-it-stops-dark.webp"><img src=".github/assets/readme/heading-where-it-stops-light.webp" alt="Where the agent still can" width="600"></picture></h2>

<p align="center">ai-eng catches an agent's visible shortcuts; it does not lock the agent in. This section lists every way past it that we know of.</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/figure-3-layers-dark.webp">
    <img src=".github/assets/readme/figure-3-layers-light.webp" alt="Figure 3. Five layers, in the order a change meets them, each with the one thing only it stops. The guard chain stops an attempt to skip a check. Git hooks stop a secret in a commit. CI workflows stop a push that skipped the hooks. External review catches a test that was deleted or weakened, which every layer above passes. A merge stops a change nobody approved." width="880">
  </picture>
  <br/><sub><b>Figure 3.</b> The layers, in the order a change meets them. The dashed row is a gap: no layer above external review reads what a test checks.</sub>
</p>

<details>
<summary>Text version of figure 3</summary>

1. Guard chain, before the tool runs: it alone stops an attempt to skip a check, because a hook cannot see the flag that skips it.
2. Git hooks, at commit and push: they alone read the staged diff for a secret, and they run for a person as well as an agent.
3. CI workflows, on the server after the push: they alone stop a push that skipped the local hooks, because a laptop cannot switch them off.
4. External review: it alone catches a test that was deleted or weakened. ai-eng does not read test content, so every layer above passes it.
5. Merge: a person decides whether the change ships. A release reaches npm only from a signed tag that a person approved.

</details>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/figure-4-surfaces-dark.webp">
    <img src=".github/assets/readme/figure-4-surfaces-light.webp" alt="Figure 4. Ten agent hosts by what ai-eng can do on each, measured on 2026-11-23. Enforced and verified, seven: claude-code, cursor, copilot-cli, copilot-vscode, opencode, pi and oh-my-pi. Enforced but unverified, one: codex. Advisory, two: zed and agy. Copilot fails open on a timeout or when ai-eng is missing from PATH; codex fails open on a hook error." width="880">
  </picture>
  <br/><sub><b>Figure 4.</b> Which hosts are enforced, which advise, which are unverified. Counts come from the capability matrix, measured 2026-11-23. The dashed box names the source.</sub>
</p>

<details>
<summary>Text version of figure 4</summary>

1. Enforced and verified, 7: `claude-code`, `cursor`, `copilot-cli`, `copilot-vscode`, `opencode`, `pi` and `oh-my-pi`. A denial blocks the call, tested on the measuring machine. The two Copilot hosts fail open on a timeout or when `ai-eng` is not on `PATH`.
2. Enforced but unverified, 1: `codex`. It is wired to deny, but the CLI was not installed on the measuring machine. It fails open on a hook error.
3. Advisory, 2: `zed` and `agy`. `zed` has no hook API; the `agy` hook file is a template that nothing installs. They offer skills and advice, never a refusal.
4. The source of every count is `docs/surface-capability-matrix.md`, measured 2026-11-23 on macOS arm64.

</details>

The guards stop an agent's mistakes. They are not a sandbox.

The Copilot adapter (CLI and VS Code) shares one hook runner and one hook file set for both hosts. Its `preToolUse` command hook **fails closed** on a crash or non-zero exit, but **fails open** when `ai-eng` is not on `PATH` (the template exits 0 on purpose, so a machine without it is not locked out) and on a timeout. The prompt hook is advisory on Copilot: `userPromptSubmitted` command output is ignored.

The Antigravity CLI (agy) is declared and **advisory**, and it cannot be enabled: `ai-eng init --surface agy` and `ai-eng config --add agy` are refused, because no hook of ours judges an agy call yet. Only a hand-edited `[surfaces] enabled = ["agy"]` followed by `ai-eng update` writes its hook file (`~/.gemini/config/hooks.json`), and that file fails soft rather than risk a lockout, because agy denies on any non-zero exit. What is measured, what is unverified (the Windows form has never been run) and what would make the surface enforceable are in the [capability matrix](docs/surface-capability-matrix.md).

Command guards read the visible command text. They do not sandbox opaque programs or scripts prepared in earlier calls: a script written in one call and run in a later call does whatever it contains.

For untrusted code, use OS-level isolation: a container, a VM or an OS sandbox.

Some limits are not on the host list at all. ai-eng does not read test content, so an agent that deletes a failing test or weakens an assertion still gets a green build. [Figure 3](#where-it-stops) shows which layer is meant to catch that.

<h2 id="under-the-hood" align="center"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/heading-under-the-hood-dark.webp"><img src=".github/assets/readme/heading-under-the-hood-light.webp" alt="One CLI, many hosts" width="600"></picture></h2>

<p align="center">Eight of the agent tools we list ask the same small program before each action; we have tested seven. It needs no server and calls no model.</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/figure-5-single-parse-dark.webp">
    <img src=".github/assets/readme/figure-5-single-parse-light.webp" alt="Figure 5. One command goes through one shell parse in src/guards/shell.ts into a typed command model. Six guards read that model as predicates: no-verify, no-stash, policy, self-protect, lease and injection. A dashed check, tests/shell-guard-contract.spec.ts, pins what the one reader returns." width="880">
  </picture>
  <br/><sub><b>Figure 5.</b> One parse, many guards. Each guard asks a question of the same typed model, so none reads a command differently from the shell. The dashed box is a test, not a step.</sub>
</p>

<details>
<summary>Text version of figure 5</summary>

1. A command arrives as text, for example `git commit -n -m fix`.
2. One reader, `src/guards/shell.ts`, parses it the way the shell will: quotes, escapes, substitutions and heredocs.
3. The result is a typed command model: segments, their words, and which text is code and which is data.
4. Six guards read that model as predicates: `no-verify` asks whether a hook is skipped, `no-stash` whether a stash is created, `policy` whether the call is inside the scope, `self-protect` whether a rule is edited, `lease` whether another session is writing there, and `injection` whether the text carries orders for the model.
5. The check on the reader is `tests/shell-guard-contract.spec.ts`. It pins what every guard reads, so a reader that splits or decodes one character differently from the shell fails.

</details>

- **Policy is code, not a prompt.** The model reads `AGENTS.md` and can choose otherwise. The guards run on every call and cannot be talked out of it.
- **One definition set for every host.** The same guard judges the same call whichever host sent it. [`src/surfaces/surfaces.json`](src/surfaces/surfaces.json) records what each host supports.
- **Answers in the host's own format.** The chain reads the host's payload on stdin and replies in the same dialect.
- **Built with** Bun and TypeScript, with 2 runtime dependencies (`@clack/prompts`, `fast-wrap-ansi`).

The two hosts that never call the command: Zed has no hook API, and the agy hook file is a template nothing installs.

<h2 id="release" align="center"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/heading-release-dark.webp"><img src=".github/assets/readme/heading-release-light.webp" alt="One way to ship" width="600"></picture></h2>

<p align="center">Each release reaches npm only after a person approves it, and one command checks the package's signed build record on your machine.</p>

1. A signed annotated tag, from an allowed key, on exactly the dispatched commit.
2. Every row of [NOTICE.md](NOTICE.md) marked `verified`.
3. A person approves the run (`environment: release`).
4. A CycloneDX SBOM, and build-provenance attestations verified before publish.
5. `npm publish --provenance` (SLSA v1).

The rules are in [`scripts/release-policy.ts`](scripts/release-policy.ts) and [`.github/workflows/release.yml`](.github/workflows/release.yml). Check a release yourself:

```bash
npm audit signatures
gh attestation verify ai-eng-darwin-arm64 --repo arcasilesgroup/ai-engineering   # a binary from the GitHub release
```

<h2 id="answers" align="center"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/heading-answers-dark.webp"><img src=".github/assets/readme/heading-answers-light.webp" alt="What sceptics ask" width="600"></picture></h2>

<details>
<summary><b>Can the agent get around it?</b></summary>

Yes, and we list how. It is not a sandbox: command checks read the visible command, so a script written in one call and run in a later call does whatever it contains. Copilot lets a call through on a timeout, and Codex on a hook error. On Zed and Antigravity it can only advise. What it does close are the common forms of skipping a hook (`-n`, `HUSKY=0`, a new `core.hooksPath`) and every edit to its own rules. For untrusted code, use a container or a VM.

</details>

<details>
<summary><b>Can I turn a check off?</b></summary>

For one guard, yes. The loop guard reads `.ai-engineering/overrides.toml`: add an entry there with a reason and an end date and the repeated call goes through. The agent cannot write to that file, and `ai-eng doctor` shows every active entry with its time left. When the date passes, the loop guard is on again. Every other guard has no override today: the way out is to run the call another way, or to ask a person to change the rule in a reviewed diff. To remove everything, run `ai-eng uninstall`; it keeps your own files.

</details>

<details>
<summary><b>Why not write the rule in AGENTS.md?</b></summary>

You should, and ai-eng writes one for you. But the model reads AGENTS.md and can choose otherwise, which is how most hook-skipping commits happen. A rule that must never break belongs in code that runs on every call. AGENTS.md keeps the judgement calls, and the checks handle the rules that never change.

</details>

<details>
<summary><b>What does it cost?</b></summary>

No money: it is Apache-2.0. On our Mac it adds under 3 ms to a tool call at the 95th percentile (`bun run bench`). It also costs context. Your agent loads about 3,000 tokens of skill descriptions and about 1,200 for the `AGENTS.md` template, by a bytes-divided-by-four estimate (`bun run tokens`). Those tokens are the real price, so they are measured.

</details>

<details>
<summary><b>Does it phone home?</b></summary>

Once a day at most, and you can stop it. Commands you type ask the npm registry whether a newer version exists, at most every 24 hours. Set `AI_ENG_NO_UPDATE_NOTICES=1` and it never does. It sends no telemetry and calls no model. Your prompts and your source never leave the machine.

</details>

<details>
<summary><b>Which agents does it work with?</b></summary>

Measured on 2026-11-23, it enforces and has verified Claude Code, Cursor, Copilot CLI, Copilot in VS Code, opencode, pi and oh-my-pi. It enforces Codex, but we have not verified Codex on our machine yet. On Zed and Antigravity it is advisory only. The [capability matrix](docs/surface-capability-matrix.md) has the details and the date. `ai-eng doctor` tells you which of your agents are enforced.

</details>

<details>
<summary><b>What happens when it is wrong?</b></summary>

When it refuses something harmless, it tells you which check fired and why. Only the loop guard takes a dated override; for any other guard, run the call another way or ask a person to change the rule in a reviewed diff. `ai-eng doctor` warns if refusals climb above 50 per 1,000 calls. Every false alarm we have fixed is kept in a test, paired with the attack it looks like. When it misses something, report it: on an enforced host, a way past a check that our list does not already name is a security bug.

</details>

<h2 id="get-it" align="center"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/heading-get-it-dark.webp"><img src=".github/assets/readme/heading-get-it-light.webp" alt="Try it on one repo" width="600"></picture></h2>

<p align="center">Set it up in one repository. Its first health check tries a real shortcut and shows you the refusal.</p>

Install [Bun](https://bun.com) (>= 1.4.4) once. On macOS and Linux: `curl -fsSL https://bun.sh/install | bash`. Then the CLI, then govern a repository:

```bash
bun add -g ai-engineering@latest    # or: npm install -g ai-engineering@latest
ai-eng init
ai-eng doctor
```

`ai-eng init` asks which agents to govern, installs the skills on your machine, and writes the contract into the repository you are in. Run it again at any time; it converges. Hooks do not run in an untrusted folder, so trust the folder in your agent once. That is the one step `ai-eng` cannot do for you.

<p align="center">
  <a href=".github/assets/quickstart.gif"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/quickstart-preview-dark.webp"><img src=".github/assets/readme/quickstart-preview-light.webp" alt="Watch the 9-second real terminal demo of ai-eng 3.3.1 running ai-eng init and ai-eng doctor (opens finite animated GIF, no autoplay on this page)" width="880"></picture></a>
  <br/><sub>Static preview (no autoplay). Select to open the finite 9-second <a href=".github/assets/quickstart.gif">animated recording</a> captured with <a href=".github/assets/tapes/quickstart.tape"><code>quickstart.tape</code></a> against <code>ai-eng 3.3.1</code>.</sub>
</p>

<details>
<summary>Text transcript of ai-eng init and ai-eng doctor</summary>

1. Run `ai-eng init --surface claude-code --yes` in a fresh repository (`my-app`, running `ai-eng` 3.3.1):
   - Verifies the machine-side global canon in `~/.ai-engineering` is intact for 3.3.1.
   - Installs your editable contract files: `AGENTS.md`, `DECISIONS.md`, and `.gitignore`.
   - Scaffolds `.ai-engineering/overrides.toml`, `.ai-engineering/config.toml`, `.github/workflows/ai-eng-check.yml`, marker-managed git floor hooks in `.git/hooks/{pre-commit,commit-msg,pre-push}`, and `.ai-engineering/ai-eng.lock` (6 assets with sha256) for surface `claude-code` and CI `github-actions`.
   - Notes that layer rules are proposed on demand with `/ai-refresh-project`, reminds you to trust the workspace in your editor, commits nothing automatically, and prints `Next: ai-eng doctor`.
2. Run `ai-eng doctor` in `my-app`:
   - Reports 1 warning (`arch`: no layer rules yet — run `/ai-refresh-project` to propose them) and 15 passing checks across `AGENTS.md` (47 rules, 89 lines), `config.toml` (governed, `claude-code`), 4/4 skill mirrors, 107/107 verified canon files with 0 drift, assets installed by 3.3.1, marker hooks in `.git/hooks/` with `gitleaks` present, the live adversarial probe (`git commit -n` → `DENY` in ~6 ms), receipt latency (p50/p95 well under the 50 ms ceiling), friction (0 denies/1000), overrides (none active), clean spec slot, research cache, enforced `~/.claude/settings.json` carrier, machine state, and behaviors.
   - Ends with `16 checks: 15 OK · 1 WARN · 0 FAIL` and `Chain verified.`

</details>

More: [install edge cases](docs/install.md) (from source, no administrator rights, Windows) · [CLI](docs/cli.md) · [lanes](docs/lanes.md) · [configuration](docs/configuration.md) · [troubleshooting](docs/troubleshooting.md) · [skills](docs/skills.md) (the triggers that send a change to a skill).

<h2 id="build-with-us" align="center"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/heading-build-with-us-dark.webp"><img src=".github/assets/readme/heading-build-with-us-light.webp" alt="Found a way past it?" width="600"></picture></h2>

<p align="center">Report it through <a href="SECURITY.md">SECURITY.md</a>. On an enforced host, any way past a check that our list does not already name is a security bug.</p>

Read [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md) before you open a pull request. To work on ai-eng itself:

```bash
bun install
bun run build                  # compile the binary, skills, agents and templates inside
bun test                       # unit, adversarial, gate and architecture tests
bun run lint && bun run typecheck
bun scripts/readme-assets.ts   # re-render the README's headings, buttons, cards, skills grid, hero and figures
```

The quickstart demo is recorded with [VHS](https://github.com/charmbracelet/vhs) against the installed `ai-eng` CLI: see `.github/assets/tapes/quickstart.tape`. Versions come from [changesets](.changeset/README.md); [docs/history](docs/history/recap.html) holds the early design record, which is history.

<p align="center"><sub>Apache-2.0 © <a href="https://github.com/arcasilesgroup">Arcasiles Group</a> · <a href="LICENSE">LICENSE</a> · <a href="NOTICE.md">NOTICE</a> · <a href="THIRD-PARTY-NOTICES.md">THIRD-PARTY-NOTICES</a> · <a href="https://ai-engineering.arcasiles.com">website</a></sub></p>
