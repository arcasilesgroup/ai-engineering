---
name: feature-verify
description: Cross-verify a just-finished feature with throwaway browser tests driven by chrome-headless-shell — proves the feature actually does what it was supposed to do, and proves the change didn't break the routes and components that depend on it. Reports a verdict with evidence and never edits app code. Use this whenever a feature, fix, refactor, or UI change has just been completed — including when the user says "done", "that's implemented", "verify this", "does it work?", "make sure nothing broke", "check for regressions", or asks whether a change is safe to commit, merge, or ship. Applies to any web app with a dev server (Next.js, Vite, Remix, SvelteKit, CRA, static). Reach for it even when the user never says "e2e", "browser test", or "screenshot".
---

# Feature Verification

You are the independent check on work that was just finished — often work you did yourself. That framing matters: the failure mode here is not "couldn't write a test", it's **writing a test that mirrors the implementation instead of the intent**, so it passes no matter what the code does. Everything below is built to keep those two things apart.

Two questions get answered every run:

1. **Does the feature do what it was meant to do?** Judged against intent stated before you re-read the implementation.
2. **Did building it break anything else?** Judged against the parts of the app that actually consume the changed code.

You report. You do not fix. The user chose report-only deliberately — an agent that grades its own work and then patches it will quietly weaken the test instead of fixing the bug. Diagnose precisely, hand it back.

## Step 1 — Pin down intent, before re-reading the implementation

Write down the acceptance criteria first, from sources that describe what was *wanted*:

- The user's own words in this conversation ("add a filter that persists across reloads")
- A ticket, issue, or spec if one was referenced
- The commit message or PR description for the change

Turn that into 3–7 concrete, observable criteria — things a person could check by using the app, phrased as user-visible behavior:

> - Typing in the search box filters the visible rows to matches only
> - The filter survives a page reload
> - Clearing the box restores all rows
> - An empty result set shows the "no matches" message, not a blank table

If intent is genuinely unclear (you inherited the change, no description, ambiguous ask), say so and ask — one short question beats a confident test of the wrong thing. If the user is unavailable, state your assumed criteria at the top of the report so a wrong assumption is visible rather than buried.

Only after the criteria are written should you look at the implementation in detail. The criteria are the contract; the code is the thing on trial. When you find yourself writing an assertion that only makes sense because of how the code happens to be structured (asserting on a generated class name, an internal state string, a DOM shape nothing depends on), you've drifted — reframe it as something the user would notice.

## Step 2 — Map the blast radius

"Didn't break other parts" needs a definition of *which* other parts. Derive it from the change rather than guessing:

```bash
git -C <repo> diff --name-only HEAD          # uncommitted work
git -C <repo> diff --name-only HEAD~1 HEAD   # the last commit, if already committed
```

Then trace which routes actually consume those files:

```bash
python3 <skill>/scripts/blast_radius.py --repo <repo> --changed <file1> <file2> ...
```

It walks the import graph backwards (following `tsconfig` path aliases) and prints the route entrypoints that transitively depend on each changed file, with URLs where it can infer them. A shared `Button.tsx` lights up ten routes; an isolated `app/settings/page.tsx` lights up one. That spread is your regression surface.

Two things the script can't see, so add them yourself when they apply:

- **Runtime coupling without imports** — shared API routes, database tables, `localStorage` keys, cookies, global CSS, env vars. If the feature changed a response shape or a storage key, every reader of it is at risk even with zero import edges.
- **Ambient/global surfaces** — a change to `layout.tsx`, `globals.css`, middleware, or a provider affects everything; pick a representative sample of routes rather than all of them.

Pick the regression targets by risk, not by count: the most-depended-on route, anything sharing runtime state with the feature, and one route that should be entirely unaffected (a cheap control — if that one fails, something environmental is wrong, not the feature).

## Step 3 — Run the cheap gates first

Static checks take seconds and catch a large share of real breakage before a browser is involved. Run whichever the project actually has — and discover which those are rather than assuming: read the manifest's script block (`package.json`, `Makefile`, `pyproject.toml`), or `CLAUDE.md` / `AGENTS.md` if the commands are written down, and use the package manager its lockfile implies (`pnpm-lock.yaml` → pnpm, `yarn.lock` → yarn, `bun.lockb` → bun, else npm). Typical shape:

```bash
<pm> run typecheck        # or `npx tsc --noEmit` where that is the project's gate
<pm> run lint
<pm> run build
```

A gate the project does not have is not a failure — skip it and say so.

A type error or broken build is a definitive regression — report it immediately with the failing file and message, and skip the browser work. Driving a browser against a project that doesn't compile wastes minutes to tell you what `tsc` already said. Pre-existing failures are different: if the base branch is already red, note it as pre-existing rather than blaming the feature — check by running the same gate on a clean tree if that's cheap, otherwise say the failure is unrelated to the changed files and move on.

## Step 4 — Set up the throwaway harness

```bash
bash <skill>/scripts/setup_harness.sh <repo>
```

This is idempotent and prints the run directory it created. It:

- resolves the lightweight **`chrome-headless-shell`** binary, installing it once via `<pm> dlx @puppeteer/browsers install chrome-headless-shell@stable` into `~/.cache/puppeteer` (a no-op when already cached; either way it prints the absolute path)
- installs `puppeteer-core` as a dev dependency only if it's missing
- creates `<repo>/.feature-verify/` as the run directory, containing `config.json`, `harness.mjs`, `specs/`, and `artifacts/`
- detects the dev-server command and port from `package.json` and probes that port

**Never launch full Chrome or Canary for this.** `chrome-headless-shell` is 3.7x faster on a real page and 9x on a local one, with byte-identical output. The binary path is per-machine, so the install step has to have run wherever this is executing — the script handles that.

The script does **not** start the dev server; backgrounding a long-lived process from a setup script orphans it. If the script reports `NOT RUNNING`, start the dev command yourself as a background command, wait for the port to answer, and remember to kill it in Step 8. If it reports `ALREADY RUNNING`, you're attaching to the user's own server — faster, and it tests the same process they're looking at, but confirm it has picked up the change before reporting "the feature isn't there".

The run directory lives inside the repo so Node resolves `puppeteer-core` normally. Nothing outside `.feature-verify/` is written, so "no code changes" holds literally.

If detection fails (unusual dev command, non-standard port, app needs seeded data or auth), read `references/harness.md`.

## Step 5 — Write the specs

Two files in `<repo>/.feature-verify/specs/`, both named `*.test.mjs` (the runner is `node --test`, which only picks up that pattern):

**`feature.test.mjs`** — one `check()` per acceptance criterion from Step 1, named after the criterion in plain language (`check('filter survives a page reload', ...)`). One criterion per check, so a failure names exactly what's broken instead of "step 4 of 9 failed".

**`regression.test.mjs`** — one `check()` per blast-radius target from Step 2. These are shallow on purpose: load the route, assert its primary content rendered, exercise its main interaction, assert no error boundary or empty shell. You're proving the route still works, not re-testing it.

Everything comes from `../harness.mjs`, which owns the browser lifecycle — **one browser launch per spec file, reused across every page and screenshot**. Relaunching per shot costs ~1.13s; reusing costs ~0.19s per shot, and the reuse is the entire win.

```js
import { check, visible, hidden, count, text, value, url, shot } from '../harness.mjs';

check('typing in the search box narrows the visible rows to matches', async (page) => {
  await page.goto('/products');                                  // relative to baseURL
  await page.locator('input::-p-aria(Search products)').fill('widget');
  await count(page, 'tbody tr:not([hidden])', 2);
  await hidden(page, '::-p-text(No matches found)');             // assert the negative too
});
```

Selector discipline decides whether this run is trustworthy. Prefer, in order: `tag::-p-aria(Name)` (role/accessible name), `::-p-text(copy)`, then `[data-testid="…"]`. Always anchor an aria selector to a tag — an accessible name is computed from descendant text, so bare `::-p-aria(Delete)` also matches the `<td>` wrapping the button and doubles your counts. Reach for a plain CSS or XPath selector only when nothing else identifies the element — those bind to structure that legitimate refactors change, and they produce failures that look like regressions but aren't. If the app has no accessible handle on an element you need, say so in the report as a finding; don't paper over it with a brittle selector, and don't edit the app to add a testid.

Never use fixed sleeps. Every assertion exported by the harness polls until it holds or times out, and puppeteer's `page.locator(...)` waits for the element to be visible and actionable before it acts — so waiting and asserting are the same operation. `references/puppeteer-patterns.md` covers the recurring cases: async data, navigation, forms, dialogs, auth state, and network stubbing.

Diagnostics come for free: `check()` attaches `pageerror`, console-error, and HTTP-5xx listeners, and on failure writes a full-page screenshot, the DOM, and the collected errors into `artifacts/`, then appends the evidence path to the error message. An uncaught exception in that log usually names the cause outright.

## Step 6 — Run, then triage before believing the result

```bash
cd <repo> && node --test .feature-verify/specs/*.test.mjs
```

Pass the files, not the directory — `node --test` skips dot-directories, so a bare `.feature-verify/specs/` argument silently finds nothing.

A failure is a finding only once you've ruled out the test itself. For each one, decide which it is:

- **Real defect** — the app genuinely misbehaves. Confirm by reproducing the steps manually against the dev server, or by reading the failure screenshot and DOM dump in `artifacts/`.
- **Bad test** — wrong selector, wrong assumption about copy or timing, needed fixture data that doesn't exist. Fix the spec and re-run; this doesn't go in the report as a defect.
- **Environmental** — dev server didn't boot, port collision, missing env var, no seeded data. Fix the harness, not the app.

The control route from Step 2 is your fastest discriminator: if it fails too, suspect environment before feature.

There are no automatic retries, so re-run a failing check on its own to see whether it's deterministic:

```bash
node --test --test-name-pattern 'filter survives a page reload' .feature-verify/specs/*.test.mjs
```

Intermittent failures are worth reporting as *flaky/unproven* rather than as a pass or a hard fail — silently re-running until green is how real bugs get shipped.

## Step 7 — Screenshots

Two ways to take one; pick by count, not by habit.

- **Exactly one shot, no waiting or interaction** — call the binary directly. No Node, no `package.json`, ~0.85s. It already waits for the load event, so no extra wait flag is needed. The absolute path is in `.feature-verify/config.json`:

  ```bash
  chrome-headless-shell --headless --disable-gpu --hide-scrollbars \
    --screenshot=out.png --window-size=1280,720 --force-device-scale-factor=1 <url>
  ```

- **Two or more shots, or full-page, waits, or interaction** — use the harness's `shot(page, name)`, which runs on `puppeteer-core` pointed at that same binary and reuses one browser (~0.19s/shot).

Scale and legibility, which decide whether a shot is worth anything:

- `deviceScaleFactor: 3` for deliverables a human will look at. `1` for agent verification shots (the harness default).
- On a tall full-page capture, dSF is wasted entirely — output is capped at 2000px on the long edge either way. That cap is a property of how images are resized before a model sees them, not of the machine.
- Full-page verification shots are fine up to ~3000 CSS px tall. Past that, small text dissolves under the cap: legibility scale = `2000 / page_height_css`, so 11px text needs the page under ~3100px. Taller than that, shoot viewport-sized sections.

## Step 8 — Report

Keep it to what someone deciding "ship or not" needs. Use this shape:

```markdown
# Feature verification: <feature name>

**Verdict:** PASS | FAIL | PASS WITH CONCERNS
<one sentence: what works, what doesn't, what it means for shipping>

## Intent verified against
- <criterion 1> — ✅ / ❌
- <criterion 2> — ✅ / ❌

## Regression surface
Changed: <files>
Routes affected via imports: <routes> — <n> checked
Runtime coupling checked: <shared API / storage / styles, or "none identified">

| Check | Result |
|---|---|
| typecheck / lint / build | ✅ / ❌ |
| feature checks (n) | ✅ / ❌ |
| regression checks (n) | ✅ / ❌ |

## Findings
### 1. <short title> — <severity>
**What happens:** <observed behavior>
**Expected:** <criterion it violates>
**Repro:** <steps or the failing check name>
**Likely cause:** <file:line and why> — *not fixed; reporting only*
**Evidence:** <screenshot / DOM dump path>

## Not covered
<what this run couldn't check and why — auth-gated flows, external APIs, mobile viewports, anything you assumed>
```

The "Not covered" section is not filler. A verdict of PASS means "everything I checked passed", and the user needs to know the shape of what went unchecked to weigh it. Be honest and specific about the gaps.

Severity, briefly: **blocking** — the feature doesn't meet a stated criterion, or an existing route broke. **concern** — works but is fragile, slow, inaccessible, or degrades in a plausible edge case. **note** — cosmetic or informational.

## Step 9 — Clean up

Specs are throwaway; evidence is not.

- **All green:** delete `<repo>/.feature-verify/` entirely and say so.
- **Any failure:** delete `specs/`, keep `artifacts/` (screenshots, DOM dumps, error logs). Give the user the absolute path and note the directory is safe to delete once they're done.
- **If you started the dev server in Step 4**, kill it. Leave the user's own server alone.

The `chrome-headless-shell` binary in `~/.cache/puppeteer` stays — it's shared across runs and repos, and re-downloading it every time is the cost this whole approach exists to avoid. `puppeteer-core` stays in `package.json` if the script added it; say so in the report so the user can drop it if they'd rather.

Never touch anything outside `.feature-verify/`. If the project has its own tests, run them if they're quick and relevant, but never modify or delete them.

## Boundaries

No edits to application code, config, or the user's existing tests — not to fix a bug you found, not to add a `data-testid`, not to loosen an assertion. If a fix looks obvious, describe it in the report and offer to implement it as a separate step. The value of this skill is that its verdict is independent; an agent that edits the code under test cannot give one.

## Reference files

- `references/puppeteer-patterns.md` — selectors, waiting, forms, dialogs, network stubbing, auth, flake diagnosis
- `references/harness.md` — the harness API, custom ports, dev-server handling, auth setup, seeded data, monorepos
