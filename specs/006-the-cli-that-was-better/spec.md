---
id: "006"
slug: the-cli-that-was-better
status: draft
date: 2026-08-09
ref: ""
supersedes: ""
---

# The CLI that was better, and the measurement of why

## Context and problem

Spec 005 fixed seven things `init` said that were not true, closed at a measured ceiling,
and left the screen looking exactly as it had. The operator installed it, ran `ai-eng init`
and `ai-eng doctor` in a real terminal, and said: still just as ugly — what did you improve?
Both halves of that are correct. What 005 improved was what the software claimed; nothing
in it touched how anything is rendered, and 005 said so in writing when it refused to port
the old installer's shape.

That refusal was argued on cost, and it was argued against the wrong thing. It reasoned
about a selection widget — a general primitive with one caller over a list of four rows —
and concluded the widget was not worth four hundred lines. Measured against the tree the
operator actually prefers, the widget is 140 lines of the answer and the other 1,230 are
somewhere else entirely.

The previous version carries a presentation layer. `cli_ui.py` is 613 lines: a Rich theme
with a brand colour taken from the project's own banner, `NO_COLOR` and `TERM=dumb` and TTY
detection, and the rule that messaging goes to stderr while data goes to stdout.
`cli_help_render.py` is 358, `cli_progress.py` is 139, `installer/ui.py` is 118 — a step
line with an index, a status icon and a detail, and a closing panel with a border — and
`wizard.py` is 140, the checkbox. One thousand three hundred and sixty-eight lines whose
whole job is that a person can read the screen.

This version has `out`. It writes a string and a newline to stdout. Everything else — the
ticks, the alignment, the section headers, the indentation — is f-strings at the call site,
and there are forty-one of them in `init.py` and `doctor.py` alone.

Three things follow from that, and only the first is taste.

**One. Nothing is coloured, so nothing is scannable.** `doctor` prints twenty-one lines of
`ok`, `FAIL` and `?` in one weight and one colour. The five failures in the operator's
screenshot are the reason to run the command and they are typographically identical to the
thirteen passes. The old one had `success`, `warning`, `error`, `muted` and `path` as named
styles, so a failure was red before it was read.

**Two. `doctor` prints nine section headers for six families, and that is a defect rather
than a preference.** The registry is sorted by assertion number and the printer starts a new
section every time the family of the current row differs from the last. The families
interleave, so `The wiring` appears four times, `The record` three, `The context` and
`The pin` twice each. On the screen it reads as a report that lost its place.

**Three. Everything goes to stdout, including the parts that are not data.** The banner is
the only thing this CLI writes to stderr, and it does that because a banner in a log is
noise. The same is true of the survey, the checklist and the closing report, and none of
them know it. There is no `ai-eng doctor > report.txt` that yields a report; it yields the
report plus every line of chrome around it.

What the operator asked for, in his words, is all of it, adapted to how v1 works, with the
quality and the depth the old one had present.

## Options considered

**1. Colour and boxes in the standard library.** Roughly 120 lines: an ANSI wrapper, a TTY
and `NO_COLOR` check, a box-drawing helper, and the family grouping. It buys items one, two
and three above and adds no dependency to a wheel that has none. It loses because it is a
second implementation of a theme, a width calculation, a wrap, and an east-asian-width
correction that `rich` already has and that this project has already paid for once — and
because it cannot do the picker at all, which is half of what was asked for. Writing it
would be the deliberate reinvention this product's own doctrine calls the disease.

**2. Adopt `rich` and `questionary`, adapted to this tree.** One `ui` module every verb
renders through, the two dependencies the old version used, and the picker back. The cost is
real and it is two costs: the wheel gains its first runtime dependencies, and the suite
stops being able to assert whole screens as string literals, which is how roughly a hundred
assertions in `tests/test_mut_init.py` and `tests/test_doctor.py` are written today.

**3. Copy `cli_ui.py`, `installer/ui.py` and `wizard.py` across.** Cheapest to type and the
worst of the three. They are written against `typer`, `pydantic` and thirty verbs, they
import `ai_engineering.updater.service` for a type, and they carry the vocabulary of a
tree that no longer exists — `providers`, `ides`, `stacks`, `DetectionResult`. Landing them
would import the old shape along with the old look, which is the 528-file failure this
rebuild exists to have escaped.

## Decision

Option 2. The operator has used both versions and prefers the earlier one; the refusal in
spec 005 was a cost argument, and the person paying that cost is the one overruling it. This
spec records the reversal rather than quietly contradicting it, so the file that says "no
selection widget" and the file that ships one are readable in the same afternoon.

Adapted, not copied. Every number the old layer knows — thirty verbs, four provider axes,
a stack table of twenty-nine binaries — is a number this tree does not have. What carries
over is the shape: named styles rather than colours at the call site, one console that owns
the terminal questions, messaging on stderr and data on stdout, a step line with an index
and a status, a closing panel, and a picker that is a picker.

What does not carry over is any behaviour spec 005 established. The three questions stay
three questions. `Undecidable` stays never-green. The coverage line stays UNPROVEN where
nothing has been proven. This spec changes how the screen is drawn and adds one input
control; it changes no verdict, no exit code and no file that gets written.

Rule 10, one line each. **KISS** — one module, one console, one theme; a verb asks for a
step or a panel and never for a colour. **YAGNI** — no progress bars, no spinners, no live
regions, no `--json`: none of the ten verbs streams anything slow enough to need the first
three, and the fourth is a different spec with a schema in it. **DRY** — forty-one f-strings
that each re-invent an indent and a tick collapse into one renderer, which is the whole
reason the alignment drifts today. **SOLID** — `hooks/` does not learn about any of this and
a test keeps it that way; the dependency lives in the half of the tree that may import
freely. **TDD** — the suite gains a plain-render mode first, so every assertion that exists
today keeps meaning something before a single glyph changes. **Clean Code** — the family
interleaving is fixed by grouping the registry rather than by teaching the printer to
remember. **Clean Architecture** — presentation is a leaf: `ui` imports from nothing in this
package except `__init__`, and nothing in this package imports `ui` for anything but output.

## Decisions

```yaml
decision: The wheel takes two runtime dependencies, and hooks never see them
date: 2026-08-09
rationale: rich and questionary are what the version the operator prefers used, and reimplementing a theme, a width calculation and a checkbox in the standard library is the reinvention this product calls the disease; they are declared in pyproject and may be imported only under src/ai_engineering, because the guards in hooks/ are executed by path on the hot path where an import of this package already costs about 110 ms and a slow guard is a disabled guard, and a test walks hooks/ and fails the build on any import of either name or of anything outside the standard library.
```
```yaml
decision: One ui module, and no verb spells a colour
date: 2026-08-09
rationale: the ticks, indents and column widths are f-strings at forty-one call sites in init.py and doctor.py, which is why the alignment already drifts between the survey and the checklist; ui owns a console, a theme of named styles, a step line, a section, a panel and a picker, and a verb asks for one of those, so that changing the look is one file and changing a claim is still the verb's own file.
```
```yaml
decision: Messaging goes to stderr and data goes to stdout
date: 2026-08-09
rationale: everything this CLI prints goes to stdout today except the banner, so `ai-eng doctor > report.txt` captures the report and every line of chrome around it; the old version followed the command-line guidelines here and this adopts the same split, with the assertion lines and the coverage table counting as data because they are what a person redirects, and the survey, the questions, the step lines and the closing panel counting as messaging.
```
```yaml
decision: Colour is off unless the terminal asked for it
date: 2026-08-09
rationale: NO_COLOR, TERM=dumb and a stream that is not a terminal each disable styling, which is what the old layer did and what keeps a CI transcript diffable; the suite drives that same plain path, so every assertion in it holds the bytes a user with no colour sees rather than a second rendering nobody reads.
```
```yaml
decision: doctor prints each family once
date: 2026-08-09
rationale: the registry is sorted by assertion number and the printer opens a section whenever the family changes, so the six families produce nine headers and The wiring appears four times; the fix is to group the rows by family and order the families deliberately, not to teach the printer to remember what it has already printed, and the assertion numbers stay exactly as they are because they are cited in prose across this repository.
```
```yaml
decision: The picker returns, and spec 005's refusal of it is reversed here
date: 2026-08-09
rationale: spec 005 refused a selection widget on the grounds that the list is four rows, the default already destroys nothing and the demonstrated defect was a parser that one line fixed; all three remain true and none of them was the operator's reason, which is that typing numbers at a prompt is worse than moving a cursor over a list he can see; the reversal is written here rather than left implicit so the two files can be read together, and the parser stays because -y, --overwrite and every non-terminal run still go through it.
```
```yaml
decision: The suite asserts the plain rendering, and stops asserting whole screens as literals
date: 2026-08-09
rationale: roughly a hundred assertions hold exact indented strings, and a renderer that owns the indent breaks all of them at once, which would make this spec look like a rewrite of the suite; instead ui gains a plain mode that the test fixture forces, the renderer's own output is pinned once per element, and the verb tests assert what the line says rather than how many spaces precede it — the exception being the two screens spec 005 closed, whose whole-screen assertions are the reason the mutation floor holds and which are re-pinned against the new rendering rather than loosened.
```
<!-- ai-eng decide writes yaml blocks here -->

## Accepted risks

```yaml
id: R-006-01
finding: first-runtime-dependencies-widen-the-supply-chain
severity: medium
accepted_by: soydachi
accepted: 2026-08-09
expires: 2026-11-07
renewals: 0
justification: this wheel has had no runtime dependency at all, and rich and questionary bring markdown-it-py, pygments, prompt_toolkit and wcwidth behind them, so a governance tool that audits other people's dependencies acquires five of its own; the mitigation already exists rather than being promised, because trivy and pip-audit and snyk all run over this repository on every push and a CVE in any of the five turns the build red the same day
follow_up: if any of the five is ever the reason a release cannot ship, the plain-stdlib renderer refused as option 1 is the exit and it is 120 lines
```
```yaml
id: R-006-02
finding: the-picker-is-unproven-off-linux
severity: medium
accepted_by: soydachi
accepted: 2026-08-09
expires: 2026-11-07
renewals: 0
justification: questionary needs a real terminal, and the only job that runs init on macOS and Windows drives it with -y, which returns before every prompt, so the picker ships exercised on a developer's machine and by unit tests that fake the keyboard and on no CI runner anywhere; this is the same honesty the coverage line already applies to three surfaces that read UNPROVEN
follow_up: either the install matrix grows a pty-driven case per platform, or this is renewed once with the reason and then fixed
```
<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command.

- [ ] CI/CD — build, lint, test and security analysis on every push; deploy from the default branch
- [ ] Logs — structured JSON, one line per event, with level and service, to stdout
- [ ] Traces — only if this is our code and has more than one hop; no hop, no trace
- [ ] Errors — every uncaught exception leaves as a log with severity 17 and marks its span
- [ ] Health and data age — alive, age of the newest datum, and an independent recomputation
- [ ] External check — something outside the service verifies it and says what it could not check
- [ ] Second path — every published number recomputed by an independent route and compared
- [ ] Security — secrets sealed, no credential in a plain variable, SAST and dependency audit in CI
