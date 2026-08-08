---
status: proposed
date: 2026-08-08
spec: 005-init-says-what-it-did
supersedes: ""
---

# 0001. A surface is detected only by a path we never write

## Context and problem statement

`policy/surfaces.toml` gives every surface two paths: a `detect` path, whose existence
means the tool is installed here, and a `skills` root, into which the installer links the
eight skills. For four of the eight rows the second is inside the first, or is a file we
write ourselves. Linking creates parent directories, so the installer manufactures the
evidence its own detector reads. One run makes the next run find OpenCode on a machine
that has never had OpenCode, write a plugin there, and then report that plugin as never
having loaded — a doctor that is red by construction and that the operator will eventually
silence. The affected rows are OpenCode (`~/.config/opencode` against
`~/.config/opencode/skills`), pi (`~/.pi` against `~/.pi/agent/skills`), Zed (`~/.agents`
against `~/.agents/skills`), VS Code Copilot, whose detect path is
`~/.claude/settings.json`, a file the Claude Code writer creates — and, counted while this
was implemented and missed when it was written, Claude Code itself: `~/.claude/skills` sits
inside `~/.claude`. Five of eight, not four. It went unnoticed for the reason these always
do: that row is the one surface everybody testing this actually has installed, so its
detector was never wrong on any machine anyone looked at.

This is not a bug in one row. It is a property the table has no rule about, and every
surface added after today can reintroduce it by accident.

## Considered options

1. **Fix the four rows and move on.** Cheapest, and it lasts until the ninth surface.
2. **Detect by a second signal — a binary on the path, a version file, a process.** Solves
   it generally and costs a per-surface probe, network or subprocess time on the hot path,
   and a new failure mode when the probe is slow or absent.
3. **Make the constraint a rule of the table, and assert it.** The detect path of a row
   must not be a prefix of any skills root, any settings path, or any other write site
   this project has. One test reads the table and fails the build when a row breaks it.

## Decision outcome

Option 3, with option 1 as the work it produces today.

The table already calls itself the single source everything derives from, so the rule
belongs to the table rather than to the code that reads it. A test that walks every row
and compares its detect path against every path we write costs a few lines once and holds
for every surface anyone adds later, including surfaces this project has not heard of.
Option 2 is refused because the cost lands on install time for a problem that a data
constraint solves for free, and because a probe that can be slow or absent is a detector
with its own could-not-evaluate state to design.

The rule, stated so it can be applied without reading this file: **a surface's detect path
must be a path this project never creates.** If the only candidate is one we write, the
row is not detectable and the surface is wired by name only.

That absolute form is the rule; the assertion is one step weaker, deliberately, and the
weakening is the other half of the decision. Taken absolutely it fails all eight rows,
because every surface keeps its settings file inside the directory that announces it, and
satisfying it would mean inventing a new detect path for Claude Code, Codex, Cursor and
Copilot as well — four paths nobody here can verify, replacing detection that works today
with detection that might. So the writes are split in two. A surface's own tree is written
only after that surface has been found, which the installer now guarantees by passing the
found surfaces into `install_skills`; that write cannot manufacture anything, because the
evidence already existed. What remains is writing into one row's detect path while wiring a
*different* row, and that is what the test forbids. Two rows failed it — Zed, whose
`~/.agents` is the shared skills root of four other surfaces, and VS Code Copilot, whose
detect path is the file the Claude Code writer creates. Both are fixed by this spec.

The exemption has a price and it is named here rather than discovered later: it holds only
while nothing writes into an undetected surface's tree. `--harness <id>` deliberately does
write into one, on the user's word, and a second `init` will then detect that surface for
real. That is consent, not manufacture, and it is the only route to a surface the table
cannot detect.

## Consequences

Better: detection stops being self-fulfilling, `doctor` stops going red on machines whose
only act was running the installer twice, and the coverage line stops reporting UNPROVEN
rows for tools that were never installed. Adding a surface gains a check that catches the
mistake in review instead of on somebody's laptop.

Worse: some surfaces have no path of their own that predates us, so they become
undetectable and must be named explicitly by the user. That is a real loss of automatic
setup, and it is the honest half of the trade — a surface we cannot detect without
creating the evidence is a surface we were never detecting.
