# Setting Up Verification

How to build verification that runs inside each node of a graph, before that node's
output becomes the next node's input.

Covers the three kinds of verification skill, the Skill Creator prompts to generate each,
how to chain several under one orchestrator, and how to test that a review skill actually
works. The skills in `tiers/` are working implementations of everything described here.

## Read this much

**Just want it working?** §9 → §12. Copy in `second-opinion`, put your commands in
your agent-rules file. Ten minutes, no skill-writing, no Skill Creator.

> **Pick this if** you want a safety net today, or you want to find out whether
> verification is worth the tokens before spending an afternoon on it. `second-opinion`
> needs nothing configured — no conventions file, no thresholds, no stack assumptions,
> just a way to spawn a fresh reviewer — so it works on any language from the first run.
> (`verify-feature` in `tiers/1-standalone/` is the other zero-config one, if you'd
> rather check the build against the requirements than hunt for bugs.)
>
> **What you give up:** it's generic. It reviews the change against whatever spec you
> hand it, so it catches bugs and dropped requirements — but it doesn't know your
> conventions, your severity bar, or what your app is supposed to do. And you get one
> lens, not six.

**Building your own?** Read straight through. §4 installs the tool, §5 decides what
you're building, §6–§10 build it, §15 proves it works.

> **Pick this if** you're running graphs regularly. Three things a pre-built skill
> can't do for you: encode what *your* project counts as a defect, fire automatically at
> a point you choose rather than when you remember to ask, and — the one that matters at
> scale — produce output consistent enough that an orchestrator can merge five parallel
> reviews into one ranked list (§10).
>
> **What it costs:** an afternoon, and §15 is not optional. An untested review skill
> reports nothing and that reads exactly like a pass.

**Already have review skills that return noise?** Start at §11. Model choice is a common
cause, and it's the one that looks like success while it's happening — a cheap reviewer
returns *more* findings, not fewer, so the failure looks like thoroughness.

Sections are marked **Skip if** where they're safely skippable.

---

## Contents

1. [Why this matters more in a graph](#1-why-this-matters-more-in-a-graph)
2. [How skills load, and why it decides everything](#2-how-skills-load-and-why-it-decides-everything)
3. [What you already have, and what it costs](#3-what-you-already-have-and-what-it-costs)
4. [Install Skill Creator](#4-install-skill-creator)
5. [Pick which kind you need](#5-pick-which-kind-you-need)
6. [Build a standalone skill](#6-build-a-standalone-skill)
7. [Build an embedded skill](#7-build-an-embedded-skill)
8. [Add browser verification the cheap way](#8-add-browser-verification-the-cheap-way)
9. [Add a second opinion](#9-add-a-second-opinion)
10. [Chain several skills under one orchestrator](#10-chain-several-skills-under-one-orchestrator)
11. [Choosing the model — the expensive lesson](#11-choosing-the-model--the-expensive-lesson)
12. [Wire it into your agent rules](#12-wire-it-into-your-agent-rules)
13. [Wire it into GitHub Actions](#13-wire-it-into-github-actions)
14. [Using it inside a graph](#14-using-it-inside-a-graph)
15. [Test that your skill actually works](#15-test-that-your-skill-actually-works)
16. [Common mistakes](#16-common-mistakes)
17. [Final checklist](#17-final-checklist)

---

## 1. Why this matters more in a graph

> **Skim** if you already run graphs — but the three failure modes below each point at
> the section that fixes them, which is the fastest way to navigate the rest of this.

With one agent, you can see what it did. You read the messages and catch the wrong turn as
it happens. A graph trades that visibility for speed, and three separate things break as a
result. Naming them matters, because each one needs a different fix.

**The volume problem.** Everything finishes at once and lands on you together. Nobody
reviews six parallel reports properly, so in practice you skim them and trust the verdict.
*Fix: an orchestrator that merges and ranks before you see anything — §10.*

**The attribution problem.** Something is wrong and you can't tell which node did it. The
intermediate work is gone; you kept the result. *Fix: every node reports a verdict with
evidence instead of silently fixing what it finds (§7), and those reports get written to
disk rather than returned through the agent (§10).*

**The context problem, which is the one that actually bites.** Each node only ever sees
its own slice. It doesn't know the original requirement, so it *cannot* notice that it
drifted — there's nothing to compare against. It hands back work that is internally
consistent and wrong, and the next node builds on top of it. *Fix: the criteria-first
rule in §7 — the node writes down what was asked for before it looks at what was built.
The ready-made version is `verify-feature` in `tiers/1-standalone/`.*

The pattern across all three: verification has to happen **at each node, before its output
becomes someone else's input.** Verifying at the end is too late by definition — by then
every downstream node has already built on the mistake.

> **A note on cost before you start.** A graph burns far more tokens than a single agent,
> because you're running a set of them at once. If you're paying per token on API pricing,
> don't run graphs at all. On a subscription plan, expect to hit your limits much sooner
> than you're used to.

---

## 2. How skills load, and why it decides everything

> **Skip if** you've shipped a skill with `references/` and `scripts/` and tuned a
> description until it triggered reliably.

You know the shape: a folder, a `SKILL.md`, frontmatter with `name` and `description`.
What matters for verification is the loading model underneath it, because it dictates
where you put things, and why a verification skill can end up never firing.

### Four tiers, four very different cost profiles

| Tier | When it's in context | Budget |
|---|---|---|
| `name` + `description` | **always**, for every installed skill, every turn | ~100 words. Genuinely scarce. |
| `SKILL.md` body | only once the skill triggers | ~500 lines. Paid only when it fires. |
| `references/*.md` | only when the body tells the agent to read one | unlimited |
| `scripts/*` | **never** — they execute, output only | unlimited |

The asymmetry is the whole design. Your description is competing for attention against
every other installed skill's description on every single turn — so it's the one place
where a wasted word costs you on turns the skill never even fires. The body only costs
you on the runs that use it, which is why the good skills in `tiers/` are long,
specific, and full of exact commands rather than gestures at them.

That asymmetry should change how you build:

- **Bulk reference material goes in `references/`.** `feature-verify` keeps its Puppeteer
  selector patterns and harness API in two reference files. A run that never hits a flaky
  selector never pays for that page.
- **Determinism goes in `scripts/`.** `blast_radius.py` walks an import graph to find which
  routes consume the changed files. As a script it costs zero context and returns the same
  answer every time. Written as prose instructions, it would cost context on every run and
  return a slightly different answer each time. For verification specifically this matters
  a lot: anything you want *identical* across parallel nodes belongs in a script.
- **The body is where the judgment lives** — the false-positive gate, the severity
  definitions, the output contract. That's reasoning, not lookup, so it needs to be
  resident once the skill fires.

### Triggering is a retrieval problem

The router sees descriptions and nothing else. So a description isn't documentation — it's
the query text you're hoping the situation matches. Two consequences.

**Name situations and literal phrases, not capabilities.** Compare:

> `description: Reviews code for bugs.`

against what `feature-verify` actually ships:

> `…Use this whenever a feature, fix, refactor, or UI change has just been completed —
> including when the user says "done", "that's implemented", "verify this", "does it
> work?", "make sure nothing broke", or asks whether a change is safe to commit, merge,
> or ship. Reach for it even when the user never says "e2e", "browser test", or
> "screenshot".`

The quoted phrases look like padding. They're the mechanism. That last sentence is doing
something subtler — it's covering the case where the user describes the *situation*
without ever using the skill's vocabulary, which is most of the time.

**Verification skills have a trigger problem no other skill has.** They need to fire at
the exact moment the agent believes it's finished — which is the moment it is least
inclined to go looking for more work. If your description only triggers on "review this",
you've built something that fires when the user already remembered to ask, which is the
case that never needed automation. Trigger on **completion language**: "done",
"implemented", "ready to commit", "wrapping up", plus the midpoint of any multi-step
feature.

### Skills compete, so draw the boundaries explicitly

Overlapping descriptions are a common reason the wrong skill fires.
The fix is negative space — say what a skill is *not*:

- `code-audit` states outright that security is `security-audit`'s, accessibility is
  `a11y-audit`'s, performance is `perf-audit`'s, and "Overlap is fine; do not go hunting
  outside your lane."
- `verify-feature` ends its description with "this answers *did we build the right thing*
  — it is not the code-quality gate and not `security-review`."

That one clause per skill is what makes a chain of six routable instead of a coin flip.
It also feeds directly into lane discipline once an orchestrator is fanning them out.

### Where skills live

| Location | Scope | Use it for |
|---|---|---|
| your harness's project skill directory (`.claude/skills/` in Claude Code) | this project only | anything that encodes project-specific conventions, thresholds, or commands |
| your harness's user skill directory (the same path under your home directory) | every project | portable skills — `second-opinion` is the obvious one |

Project scope wins on a name collision. Useful deliberately: install a skill globally,
then shadow it in one repo with a stricter variant under the same name.

The skills in `tiers/` are written to be project-agnostic — they detect the stack at
runtime rather than hardcoding it — so most of them work at user scope as-is. The
exception is the chain, which reads `.claude/review/CONVENTIONS.md` by project-relative
path; that file has to exist in each repo even when the skills are installed globally.

### Then verify the trigger, don't assume it

A skill that never fires is worth nothing, and you won't notice — the absence of a review
looks exactly like nothing happening. Skill Creator can generate a trigger eval for you:
20 realistic queries, half that should fire and half that shouldn't, scored against your
description.

The valuable half is the negatives, and they have to be **near-misses** — queries that
share vocabulary with your skill but need something else. "Write a fibonacci function" as
a negative for a review skill tests nothing. "the build is failing on CI, can you look at
the error" as a negative for `code-audit` tests something real, because that's
`build-check`'s job and a sloppy description will grab it.

---

## 3. What you already have, and what it costs

> **Skip if** you know what `/help` lists and that built-in skills can't be made to
> fire automatically.

Before you build anything, know what's already there — no sense rebuilding it.

**None of it is free.** It's already *installed*, which is a different thing. Every check
below spends tokens and turns when it runs, and in a graph it runs once per node. A
built-in review that costs you nothing to set up still multiplies by your fan-out width.
Treat "already there" as saving you the build, not the bill.

**Agents self-verify whether you ask or not.** If you're working in code, the agent runs
your scripts and reads the errors that come back. That's real, and it needs no setup from
you. But it only catches what breaks *loudly*. Code that runs is not the same as code that's right — a
wrong discount calculation compiles perfectly.

**Tool chaining.** Your agent already knows to run the tools that check its work: typecheck,
lint, tests, build. It can usually work out your project's commands on its own by reading
`package.json`. Writing them into your agent-rules file saves it the trouble every single
time — [see below](#12-wire-it-into-your-agent-rules).

**Built-in review skills.** Your harness may ship some. Run `/help` (or your harness's
equivalent) to see what you have — commonly `/code-review` (checks the working diff),
`/simplify` (quality cleanups on changed code), `/security-review` (security pass on the
current branch), and `/review` (a GitHub PR). Anthropic's own team chains these together
and adds their own design skill that checks the interface against `design.md`.

**The catch with built-ins:** you can't make them fire automatically. Their instructions
live inside the product and you don't get to edit them. That limitation is the entire
reason [embedded skills](#7-build-an-embedded-skill) exist.

So: use the built-ins for what they cover, and build your own for the rest. The
verification that works best is the one you set up yourself.

---

## 4. Install Skill Creator

> **Skip if** `/skill-creator` already works for you.

You *can* write `SKILL.md` by hand. Don't, at least not for your first one. Skill Creator
structures the file properly, and when a skill needs helper scripts it writes and tests
them as part of the process.

1. Run your harness's plugin command — in Claude Code, `/plugin`
2. Search for **skill-creator**
3. Install it
4. Choose a scope when asked:
   - **User** — available in every folder. Right answer for this one; you'll use it
     constantly.
   - **Project** — only where you're standing right now.
5. Reload plugins (or just restart your agent)

Verify it took:

```bash
cat ~/.claude/plugins/installed_plugins.json
```

On Claude Code you should see `skill-creator@claude-plugins-official` (other harnesses
keep their own plugin registry). It's now available as `/skill-creator`.

---

## 5. Pick which kind you need

> **Don't skip.** This decides what you build in §6–§10, and building the wrong kind is
> an easy afternoon to waste.

How and when a skill gets invoked splits them into three kinds. Pick before you build —
it changes what you write.

| | **Standalone** | **Embedded** | **Chained** |
|---|---|---|---|
| **Fires when** | you run it | automatically, mid-workflow | you (or a node) run the orchestrator |
| **Depth** | deep, comprehensive | fast, focused | deep, from several angles at once |
| **Runs on** | finished work | work in progress | finished work, before merge |
| **Cost** | high, occasional | low, constant | highest |
| **Build it when** | you want a heavy pass before shipping | every feature needs the same check | one skill has gotten too broad |

**How to choose, in one line each:**

- If running it after every small change would be wasteful → **standalone**.
- If you'd forget to run it → **embedded**.
- If your one review skill is trying to cover security *and* accessibility *and* design
  conformance → **chain**, one skill per angle.

Most setups end up with all three. Build them in that order.

---

## 6. Build a standalone skill

A standalone skill only runs when you invoke it yourself. That's deliberate: it's built to
go deep on something that already exists, and you don't want a heavy comprehensive review
firing on work that isn't finished yet.

The reference example is Cursor's **thermonuclear code review** — it fans a set of agents
across the code, each from a different security angle, and collects everything in one
place so the fixes can be worked through together. That's a once-the-app-is-done review.

### The prompt

Run `/skill-creator` and give it something shaped like this. Fill in the bracketed parts:

```
Build me a standalone code review skill.

Area to review: [security / correctness / performance / accessibility — pick ONE]
Stack: [e.g. Next.js 16, React 19, TypeScript 5, Tailwind 4]

Requirements:
- The review must be COMPREHENSIVE — a deep pass, not a quick scan. It should read
  the surrounding code, follow callers, and check types before judging.
- Only I invoke it. It should never fire automatically.
- Every finding must include: file:line, one sentence on what is wrong, and a
  CONCRETE FAILURE CASE — specific inputs or state, and the wrong output or crash
  that results. If a finding can't be expressed as a concrete failure case, it must
  not be reported at all.
- Severity: critical / high / medium / low, defined by real-world consequence.
- Skip style, naming, and formatting. Those aren't this skill's job.
- Default scope is the current change (git diff), not the whole repo. Never review
  node_modules, build output, or lockfiles.
- Output: a markdown report, findings ranked worst-first, plus an explicit verdict.
```

### Why each of those lines is there

The **comprehensive** instruction is what separates a deep pass from a skim. Say it
explicitly or you get a skim.

The **concrete failure case** rule is the line that does the most work here.
Without it you get a list of suspicions — "should validate inputs", "could be a race
condition" — that all look like findings and mostly aren't. Requiring a reproducible
failure forces the model to actually check, and it kills most false positives before they
reach you.

The **one area** constraint matters because a skill covering four angles is worse at all
four. That's what [chaining](#10-chain-several-skills-under-one-orchestrator) solves.

### Try the finished ones first

`tiers/3-chain/` in this folder has six of these already written — `code-audit`,
`security-audit`, `perf-audit`, `a11y-audit`, `design-check`, `build-check`. Read one
before you write your own. `code-audit` is the best starting point.

---

## 7. Build an embedded skill

A standalone skill is no use to a node that's still working, because someone has to run
it. An embedded skill fires as part of the workflow you're already running, without being
asked.

The pattern that pays off most: **a skill that fires whenever a feature gets built, checks
every component against your rules, and won't let the implementation finish until it
passes.**

### The prompt

```
Build me an embedded verification skill that runs automatically after every feature
implementation.

It must trigger on its own — not only when I ask. The description should fire on
"done", "that's implemented", "finished", and at the point any multi-step feature
is being wrapped up.

What it does, in order:
1. Write down the acceptance criteria FIRST, from what I actually asked for, BEFORE
   re-reading the implementation. 3-7 concrete, observable, user-visible criteria.
2. Then run the cheap static gates: typecheck, lint, build. A failure there is a
   definitive regression — report it and stop, don't go further.
3. Then test the feature end to end and confirm each criterion.
4. Then check that the change didn't break what already worked: find which routes
   and components import the changed files, and test those too.
5. Report a verdict with evidence. Do NOT edit app code.

Rules:
- Ordering in step 1 is not optional. Read the code first and you'll reconstruct
  requirements the code happens to satisfy.
- Never write a test that asserts on internal implementation detail (generated class
  names, internal state strings). Assert only on what a user would notice.
- Report only. An agent that grades its own work and then patches it will weaken the
  test instead of fixing the bug.
```

### The two rules doing the real work

**Criteria before code.** This is the most important line and it's the one people skip. If
the agent reads the implementation first, it unconsciously reconstructs requirements that
the implementation already satisfies. You asked for "filter posts *and* remember the
choice per user", it reads a filter, and it remembers the ask as "filter posts". Then it
verifies that and passes. Freezing the criteria first makes that failure *impossible*
rather than merely discouraged.

**Report, don't fix.** Let a verifier fix its own findings and it will sometimes fix the
test instead of the bug. Both make the run go green. Only one is real.

### Also check what broke

"Didn't break anything else" needs a definition of *which* else. Derive it from the change
rather than guessing:

```bash
git diff --name-only HEAD          # what changed
```

Then walk the import graph backwards to find which routes consume those files. A shared
`Button.tsx` lights up ten routes; an isolated page lights up one. That spread is your
regression surface. `tiers/2-embedded/feature-verify/scripts/blast_radius.py` does exactly
this, following `tsconfig` path aliases.

Two things an import graph can't see, so add them by hand:

- **Runtime coupling with no import** — a shared API route, a database table, a
  `localStorage` key, a cookie, global CSS. Change a response shape and every reader is at
  risk with zero import edges between them.
- **Ambient surfaces** — `layout.tsx`, `globals.css`, middleware, a provider. These affect
  everything; sample a few representative routes rather than all of them.

One more trick worth stealing: **include one route that should be entirely unaffected.**
It's a free control. If that one fails, something environmental is wrong and the feature
is innocent.

---

## 8. Add browser verification the cheap way

> **Skip if** you have no UI to verify.

To verify a feature actually works, the agent opens a browser, loads the page, and takes
screenshots. By default that's full Chrome. If you've wired up Puppeteer or Playwright —
the usual tools for driving a browser automatically — same thing.

Full Chrome is famously heavy on memory and slow to start. Inside a workflow that checks a
page over and over, that's real time you're paying for on every single run.

**Use `chrome-headless-shell` instead.** It's a stripped-down browser with the extra parts
removed. The agent still loads the page and screenshots it the same way — the output is
byte-identical — it just gets there far faster. Measured on the reference skill: **3.7x
faster on a real page, 9x on a local one.**

Install it once:

```bash
npx @puppeteer/browsers install chrome-headless-shell@stable
```

That caches the binary in `~/.cache/puppeteer` and prints its absolute path. The path is
per-machine, so this has to have run wherever the verification executes.

Then add this to your skill prompt:

```
Use chrome-headless-shell for all browser verification — never full Chrome or Canary.
Resolve the binary via `npx @puppeteer/browsers install chrome-headless-shell@stable`,
which is a no-op once cached and prints the path either way.
Launch the browser ONCE per spec file and reuse it across every page and screenshot.
```

**That last line is most of the win.** Relaunching the browser per screenshot costs about
1.13s each. Reusing one costs about 0.19s. If you take twenty shots in a run, that's the
difference between 23 seconds and 4.

### Three more things that make browser tests trustworthy

**Never use fixed sleeps.** `await sleep(2000)` is either too short and flaky, or too long
and slow, and it's usually both on different machines. Use assertions that poll until they
hold or time out. Puppeteer's `page.locator(...)` already waits for the element to be
visible and actionable before acting, so waiting and asserting become the same operation.

**Pick selectors by what the user sees**, in this order:

1. Role and accessible name — `button::-p-aria(Save changes)`
2. Visible text — `::-p-text(No matches found)`
3. A test id — `[data-testid="row"]`
4. Raw CSS or XPath — last resort only

Raw CSS binds to structure that legitimate refactors change, and it produces failures that
look like regressions but aren't. Always anchor an aria selector to a tag — a bare
`::-p-aria(Delete)` also matches the `<td>` wrapping the button and silently doubles your
counts.

**Assert the negatives too.** "Two rows are visible" passes on a broken page that shows two
rows and an error banner. Also assert the error banner is *absent*.

If the app has no accessible handle on an element you need, report that as a finding.
Don't paper over it with a brittle selector, and don't edit the app to add a test id — the
verifier changing the code it's verifying defeats the point.

---

## 9. Add a second opinion

If you only install one skill from this bundle, install this one — it needs no
configuration and applies to any language. It ships ready to use — from your project root:

```bash
# VERIFY = this skill's folder; SKILLS = your harness's project skill directory
# (in Claude Code, that's .claude/skills)
VERIFY=/path/to/ai-verify
SKILLS=.claude/skills

mkdir -p "$SKILLS"
cp -R "$VERIFY/tiers/2-embedded/second-opinion" "$SKILLS/"
chmod +x "$SKILLS/second-opinion/scripts/second-opinion.sh"
```

Restart your agent and it will start firing on its own after implementations. The rest of
this section is why it works and how not to waste it — read it before you trust its output.

**The agent that built the thing is the worst possible reviewer of it.** Not because it's
careless — because it can't un-know its own plan. When it re-reads code it just wrote, it
checks the code against its *intent*. It remembers what each line was *for*, so it reads
the intent into the code and skips straight over the place where the code says something
slightly different.

A fresh reviewer has no plan to un-know. It sees only the task and the code, so a gap between
them shows up as a gap. That's the entire mechanism.

### How it works

The wrapper spawns a whole separate reviewer session in the background by handing the
`claude` CLI a prompt. `tiers/2-embedded/second-opinion/scripts/second-opinion.sh` wraps it:

```bash
claude -p "Read $PACKET and follow its instructions exactly." \
  --tools "Read,Grep,Glob" \
  --permission-mode bypassPermissions \
  --strict-mcp-config \
  --no-session-persistence \
  > "$OUT" 2>&1
```

The reviewer gets `Read,Grep,Glob` and nothing else — it cannot edit files, run commands,
or reach MCP servers. That's what makes bypassing its permission prompts safe, and the
bypass matters: a review that stops halfway to ask permission just hangs the session that
spawned it.

### The one rule that makes or breaks it

**Give the reviewer the spec and the code. Never give it your justifications.**

Leak your reasoning into the packet and you've destroyed the only thing you were buying.
Keep all of these out:

- *"I handled the empty case by…"* — if the handling is real, the reviewer will see it in
  the code. Having to point at it is exactly the signal that it's worth testing.
- *"I already tested this"* / *"this works"* — reads as permission to skim.
- *"The tricky part was X, but I resolved it by Y"* — hands over your conclusion, and the
  reviewer will adopt it.
- Your commit message, if it explains rationale rather than what changed.

Describe files neutrally. `src/cart.ts — new; discount + total calculation`. **Not**
`src/cart.ts — new; correctly clamps at zero`.

Quote the original task **in the user's own words, verbatim**. Paraphrasing it launders
your interpretation into the spec, and then the reviewer can only check your code against
your reading of it.

### Two practical warnings

**It's slow.** It's an entirely separate session with no prompt-cache reuse. Typically
20–60 seconds, but a large diff can run several minutes. Set your command timeout to
`600000` — a timeout kills the review *after* you've already paid for it.

**Run it on your strongest model.** The whole point is a smarter second read. Say so explicitly:

```bash
<skill-dir>/scripts/second-opinion.sh <packet> --model <strongest>
```

For something small and mechanical, a cheaper model via `--model` catches the same planted bugs at a
fraction of the cost. Default to the strong model for anything subtle, concurrent, or
security-relevant.

### Then triage — don't just apply what comes back

The reviewer is confident by construction and context-free by design. Both produce false
positives. **Verify every finding against the actual code before acting on it.** Its
confidence is not evidence.

Usually **wrong**:
- Already handled elsewhere — a guard in the caller, a validation layer, a type
  constraint, a DB check. The reviewer read a slice of the repo, not all of it.
- Intentional, and decided earlier in the session — you and your agent ruled out the
  alternative an hour ago. The reviewer wasn't there and can't see that.
- Style wearing a bug costume — "should validate inputs", no failure case, on a private
  function whose only caller already validates.
- Invented API behavior — a confident claim about what a library does, from memory. Check
  the real docs, especially where your installed version postdates anyone's training data.

Usually **right**:
- Off-by-ones, inverted conditions, wrong operators
- An unhandled empty/zero/null case with a stated repro
- **Anything about a requirement in the original task that the code doesn't implement** —
  this is where the technique earns its keep. Weigh it accordingly.

Then report both what you fixed *and* what you rejected, with your reasoning. The rejected
list is how the user audits your triage — a review where you silently dropped half the
findings is indistinguishable from one that found half as much.

### Note on the built-in Advisor

Some harnesses have a built-in advisor that does something along these lines. But it reads the
chat you're currently in, so it inherits all the same context — that's useful for other
reasons, and it's not what this is. `second-opinion` is for when you want the review
*without* the context.

---

## 10. Chain several skills under one orchestrator

One skill can't cover everything. Review something properly and you're reviewing it from
several angles — correctness, security, accessibility, performance, conformance to the
design — and each angle has its own way of measuring. Stuff all of that into one skill and
it gets worse at all of it.

So build one skill per angle and chain them.

Anthropic's own team works this way: they chain a code review skill with a simplify skill
and a verification skill — built-ins, so check `/help` for what your version actually
ships and under what names — and add their own design skill that checks the interface
against `design.md`, the file that holds every design decision for the product. That's a
review coming from four directions instead of one.

### You can't just say "run all of them"

Telling the agent to run six skills in one session means six reviews sharing one context
window, each one contaminated by the last. What you need is **one more skill sitting above
the rest — an orchestrator whose only job is to run other skills.**

It spins up an agent per review skill, hands each one its skill, they all review at the
same time in their own separate context windows, and it pulls every finding back into one
report the fixing agents can work from.

### The prompt

```
Build me an orchestrator skill called full-review. Its only job is to run my other
review skills and merge their output. It performs no review itself.

My review skills are: [list them]

How it must work:
1. Resolve the review scope ONCE, up front, and pass the identical scope string to
   every agent. Agents that each resolve their own scope drift apart, and then their
   findings can't be compared or deduplicated.
2. Run the objective gate (typecheck/lint/build) first, synchronously, alone. If it
   fails on a compile or type error, STOP and ask whether to fix first — reviewing
   code that doesn't compile is wasted work. If it fails only on lint, carry on and
   fold those findings in.
3. Fan out one agent per remaining skill, ALL IN A SINGLE MESSAGE so they run
   concurrently. Give each agent one lane and tell it to stay strictly in it — if it
   notices something outside its lane, note it in one line and do not investigate,
   another agent owns it.
4. Each agent writes its FULL report to a file and returns ONLY: the verdict, a
   one-line summary per finding with severity and file:line, and the report path.
   Never the full report text.
5. Wait for all of them. If one fails or returns nothing, mark that lane NOT COVERED
   in the merged report. A silent failure must never read as a clean pass.
6. Merge: deduplicate by file:line, re-rank globally by real-world consequence, and
   report conflicts between lanes rather than suppressing either side.
7. Output one report, worst-first, with a "fix before merge" list at the top.
```

### The four lines that matter most

**One scope, resolved once.** If each agent decides its own scope, they review different
code, and then you can't dedupe or compare anything — a chain that silently produces
garbage while appearing to work.

**Return summaries, not reports.** This is what keeps it affordable. Full reports live on
disk; the orchestrator reads the files it needs instead of absorbing five complete reviews
through agent return values. Skip this line and your orchestrator's context fills up with
review text and it starts truncating.

**Lanes, strictly.** Without lane discipline, five agents all report the same unlabeled
button, and your merge is 80% duplicates.

**Report conflicts, don't resolve them away.** The most valuable output of a chained review
is the disagreement. `design-check` says the code matches the spec; `a11y-audit` says the
same element is inaccessible. Both are right — the *spec* mandated something that fails
WCAG. That finding only exists because the lanes were separate, and it's often the most
important thing the review produces.

### Then it's one line in your graph prompt

This is the payoff. When you build a graph, the only verification instruction you need is:

> Every node must invoke the `full-review` skill before returning its output.

Each node loads that one skill, and the whole review fans out underneath it on its own.

`tiers/3-chain/full-review/SKILL.md` is a complete working version. Read it.

---

## 11. Choosing the model — the expensive lesson

> **Don't skip this one.** Model choice on judging nodes decides whether the rest of this
> setup returns signal or noise.

A skill is only ever as good as the model you run it on. This is worth a section because
the intuition is backwards.

**What happened.** Building the verification system for a community website's UI, the
reviewer ran on **Haiku** — cheap, and the job looked simple. It came back with a long
list of issues. Going off the number of findings alone, it looked like it had done a great
job.

The same review on **Opus** flagged far fewer things.

That looks like the worse result. It wasn't. Reading the reasoning: a lot of what Haiku
reported was stuff that had been left there **on purpose**. Opus had worked that out from
the surrounding code. Haiku had missed the context completely.

So the cheap review saved nothing, because now **the review itself needed reviewing.**

**Now put that inside a graph.** A whole set of nodes, all checking their own work with
that same skill. You'd have agents burning time and tokens fixing things that were never
broken — and because it's happening across separate agents all at once, you'd have no way
of telling which one started it.

**Finding count is not a quality metric.** A cheap reviewer produces more findings, and
that's the tell, not the win. What you measure is: how many of these are real, and did it
correctly leave the deliberate stuff alone?

### The rule

| Node type | Model |
|---|---|
| Mechanical work — renaming, moving files, formatting, applying a decided fix | cheap |
| Implementation | mid-tier |
| **Anything that judges** — reviews, verification, the orchestrator's merge | **strongest available** |

Splitting work across a graph *does* let you pick a model per node, and that's a real
saving. Just don't take it out of the judging nodes.

**The node that does the judging is the one place where saving tokens costs you
everything.** The model you pick there doesn't just decide the quality of the review — it
decides the quality of the whole graph.

---

## 12. Wire it into your agent rules

> **Skip if** your agent-rules file already lists your commands and warns about anything
> that generates false positives.

Your agent-rules file — `AGENTS.md` at the repo root, or `CLAUDE.md` on harnesses that
read it — is loaded automatically at the start of every session, including by every
subagent in a graph. Two things belong in it.

**Your exact commands.** Your agent can work these out on its own by reading `package.json`,
but writing them down saves it the trouble every single time — and in a graph that's once
per node.

```markdown
## Commands

- Typecheck: `npm run typecheck`
- Lint: `npm run lint`
- Test: `npm test`
- Build: `npm run build`
- Dev server: `npm run dev` (port 3000)

## Before declaring any work done

Run typecheck and lint. If either fails, fix it before reporting.
```

**Anything that would otherwise generate false positives.** This is the underrated one. If
your installed framework version postdates the model's training data, say so — otherwise
every reviewer confidently flags correct code as wrong, from memory:

```markdown
## Stack — read before reviewing

<Your framework and its exact installed version — e.g. "Acme 16.2.12 / TypeScript 5".>

This version is NEWER than your training data and several APIs changed. Before flagging
any framework usage as incorrect, check the installed package source or its type
definitions. A confident claim from memory about this stack is probably wrong.
```

One paragraph like that eliminates an entire category of false positive across every node
in your graph.

---

## 13. Wire it into GitHub Actions

> **Skip if** your CI already runs typecheck, lint, and build on every PR.

GitHub Actions let you set up jobs that fire on their own whenever something happens in
your repo. Point one at a pull request and your verification runs on every change without
anyone remembering to trigger it.

`.github/workflows/verify.yml`:

```yaml
name: Verify
on: [pull_request]

jobs:
  gates:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0          # reviews need the diff against the base
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
      - run: npm ci
      - run: npm run typecheck
      - run: npm run lint
      - run: npm run build
```

Start there. Those three gates are objective, fast, and free, and they catch a real share
of breakage before a human or an agent looks at anything.

Adding an agent review on top is a bigger step — it needs an API key in repository
secrets, and it costs tokens on every push. Get the free gates running and stable first.

`fetch-depth: 0` is easy to miss and breaks everything downstream: without full history
there's no base commit to diff against, so any review scoped to "the current change"
either reviews nothing or falls back to the whole repo.

---

## 14. Using it inside a graph

Putting it together. A graph is built from **nodes** (a single job, running on its own —
an agent, a task, anything that takes something in and gives something back) and **edges**
(what carries one node's output to the right next node).

Two shapes to know:

**Diamond** — one task at the top splits into several agents running side by side, then
narrows back into a single agent that pulls everything they found into one answer. Useful
when the parts are genuinely independent.

**Fan-in at a barrier** — the same problem goes out to a set of agents, each looking at it
through a different lens. **Nothing moves forward until every one has reported back.** Only
then do the fixes run. This is the shape you want when one thing has to be judged from
several angles, and it's exactly what `full-review` implements.

### Where verification goes

Every node verifies **before** its output becomes an edge into another node. Not at the
end. If you verify only at the end, every agent downstream has already built on top of the
mistake, and you're debugging a finished result with no idea which node started it.

### A working setup

```
.claude/
├── skills/
│   ├── full-review/          ← orchestrator, the one nodes invoke
│   ├── build-check/          ← objective gate, runs first
│   ├── code-audit/
│   ├── security-audit/
│   ├── design-check/
│   ├── feature-verify/       ← embedded, browser
│   └── second-opinion/       ← embedded, fresh eyes
├── review/
│   └── CONVENTIONS.md        ← shared severity + output contract
└── ...
agent-rules file              ← commands + stack warnings
design.md                     ← what design-check measures against
```

`CONVENTIONS.md` is the piece people leave out. It's a single file defining scope
resolution, the severity scale, the false-positive gate, and the exact output format. All
your review skills read it first. Without it, six agents invent six different severity
scales and the merge is meaningless — a "critical" from the perf lane and a "critical"
from the security lane aren't remotely the same thing, and the orchestrator can't rank
them against each other.

There's a copy in `tiers/3-chain/_support/review/CONVENTIONS.md`. Read it before writing
your own.

### And in the graph prompt

> Every node invokes `full-review` before returning. Judging nodes run on your strongest model.

That's it. Two sentences, because the structure lives in the skills.

---

## 15. Test that your skill actually works

> **Don't skip.** An untested review skill reports "no issues found" when it's broken,
> and that reads exactly like good news.

Don't trust a review skill you haven't tested. It will happily report "no issues found"
because it's broken, and that reads exactly like good news.

**Plant bugs and see if it finds them.** Take a working branch, introduce a handful of
defects of different kinds and severities — an off-by-one, an inverted condition, a
missing null check, a dropped requirement, a real security hole — and keep the list in a
file the skill is explicitly told never to read.

Then run it and score it on two numbers:

- **Recall** — how many planted bugs did it find? Misses tell you the instructions are too
  vague.
- **Precision** — of everything it reported, how much was real? Noise tells you the
  false-positive gate is too weak, usually because you didn't require a concrete failure
  case.

Keep the answer key **outside** the paths the skill is told to review, and add an
explicit instruction never to read it — a review that finds the planted bugs by reading
the list of planted bugs tells you nothing. The chain these skills came from did exactly
that: an answer-key file next to the conventions, and a hard rule against opening it.

**Then test the trigger separately.** A perfect skill that never fires is worth nothing.
Start a fresh session, type the thing a normal person would type — "does this work?", "is
this done?" — and see whether it activates. If it doesn't, the body is fine and the
`description` is the problem: add the actual phrases people use.

Skill Creator can also run evals for you if you ask it to — worth doing once the skill is
otherwise finished.

---

## 16. Common mistakes

**Reading the code before writing down the criteria.** The one that quietly ruins
everything. You end up verifying that the code does what the code does. Write the criteria
first, always, and show them before you look at the implementation.

**Cheap models on judging nodes.** [Section 11.](#11-choosing-the-model--the-expensive-lesson)
More findings from a cheaper model is a warning sign, not a win.

**Leaking reasoning into a second-opinion packet.** "I already handled that" turns an
independent review back into your own review, and you paid extra for the privilege.

**Letting the verifier fix its own findings.** It will sometimes fix the test instead of
the bug. Both go green.

**Agents resolving their own scope.** Five agents reviewing five different diffs. Nothing
dedupes, nothing compares, and it looks like it worked.

**Silent failures reading as passes.** An agent that dies and returns nothing must show up
as `NOT COVERED`, loudly. Otherwise you ship believing something was checked.

**Fixed sleeps in browser tests.** Flaky on a slow machine, wasteful on a fast one. Poll
until the assertion holds.

**One skill covering four angles.** It'll be mediocre at all four. Split and chain.

**Skipping CONVENTIONS.md.** Six incompatible severity scales, one meaningless merged
report.

**Running the full chain on every small change.** It spawns five agents that each read a
real amount of code. For a two-line fix, one targeted skill beats the sweep. Save the
chain for a merge, a release, or a branch with real work on it.

**A description that doesn't name real trigger phrases.** The skill never fires and you
conclude skills don't work.

---

## 17. Final checklist

Setup:

- [ ] Skill Creator installed at user scope
- [ ] your agent-rules file has your exact commands
- [ ] your agent-rules file warns about anything that generates false positives (framework versions)
- [ ] `.claude/review/CONVENTIONS.md` exists — shared severity, scope, output contract
- [ ] `chrome-headless-shell` installed if you're verifying UI

Skills:

- [ ] At least one standalone deep-review skill, one angle per skill
- [ ] At least one embedded skill that fires without being asked
- [ ] `second-opinion` installed, and set to run on your strongest model
- [ ] An orchestrator, if you have three or more review skills
- [ ] Every skill's `description` names real trigger phrases

Rules baked into every one:

- [ ] Criteria written down before the implementation is read
- [ ] Every finding requires a concrete failure case
- [ ] Verifiers report, they don't fix
- [ ] Scope resolved once and passed down, never re-resolved per agent
- [ ] Agents return summaries and paths; full reports go to disk
- [ ] A failed or empty agent is marked `NOT COVERED`, never a pass

Before trusting it:

- [ ] Tested against planted bugs — recall and precision both checked
- [ ] Trigger tested in a fresh session with the words a normal person would type
- [ ] Judging nodes confirmed to be on your strongest model

---

## Where to go next

Read the real skills in `tiers/`, in this order:

1. `2-embedded/second-opinion/SKILL.md` — shortest, highest value, mostly portable
2. `3-chain/code-audit/SKILL.md` — what a tight false-positive gate looks like
3. `3-chain/full-review/SKILL.md` — how orchestration and merging actually work
4. `2-embedded/feature-verify/SKILL.md` — the browser harness, blast radius, evidence

They're written to be project-agnostic — each one detects the stack from your manifest
and lockfile at runtime instead of hardcoding it, and verifies claims about a library
against the installed source rather than from memory. The handful of things worth
adjusting per project — your agent-rules file (§12) and the chain's `CONVENTIONS.md`
(§14) — are both covered above.
