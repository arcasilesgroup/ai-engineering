---
status: proposed
date: 2026-08-09
spec: 007-the-install-a-stranger-can-follow
supersedes: "0002"
---

# 0003. A diagnostic may run the consented verb that cures what it found

## Context and problem statement

ADR 0002, three days old, refused `ai-eng doctor --fix` and made every check name its cure
in prose instead. It closed with the line that this answer may change only by superseding
it. This is that.

What 0002 examined was the previous version's `--fix`: nine remediating checks that
performed the writes themselves. Its argument is exact and it still holds against that
design. One of those repairs rewrote `.ai/config.toml` — the pin, the file that names which
version governs a repository. The verb that legitimately rewrites it, `ai-eng update`,
refuses on an unpinned repository, refuses on a dirty tree, and refuses without a keyboard.
A `--fix` that re-pins is that verb with all three consent gates removed, wearing a
diagnostic's name. And that implementation's own `Fix? (y/n/all)` prompt was decorative,
because every fix had been applied before the question was asked.

What 0002 did not distinguish is the difference between a diagnostic that reimplements the
writes and one that calls the verb. Its option 1 is written as "a `--fix` flag with a repair
slot on each check", and the cost it prices is a second entry point to those writes. A flag
that shells no logic of its own and instead invokes `ai-eng update` by name is not a second
entry point. It is the same one, reached from a different keystroke, with every gate it has
still in front of it.

The complaint 0002 identified is also real and it was only half-answered. Prose that says
"`ai-eng init --global` repoints it" is readable by a person and unreadable by anything
else, so a person copies it and an agent parses English or gives up. Worse, the cure lived
in the message, which is one string and two facts: the message and the command drifted
apart in exactly the way this repository's own comments predict, and nothing could notice
because nothing asserted them separately.

## Considered options

1. **Keep 0002 as it stands.** Costs nothing. Leaves the cure unreachable by anything but
   a human's copy-paste, and leaves seventeen of twenty-one failures giving a reader no
   signal at all about whether a command exists.
2. **A cure field, and no flag.** The cure becomes data rather than prose, so it can be
   printed in a column of its own and a failure without one says so out loud. Delivers most
   of the readability and none of the "one command" the operator asked for.
3. **A cure field, and a flag that runs the consented verbs by name.** Option 2, plus
   `--fix`: it runs each distinct cure once, in this process, through `cli.main`, and then
   re-runs the diagnosis and prints the new verdict. Every consent gate stays where it is,
   because the gate is inside the verb and the verb is what runs.

## Decision outcome

Option 3.

The rule, stated so it applies to checks that do not exist yet: **a check reports, and it
never writes. A check that knows the cure carries the command as a field. `--fix` may
invoke that command and may not reimplement it.** A cure that cannot be expressed as an
existing `ai-eng` command is not a cure; it is an empty field and the check says a person
does this one.

Three consequences are load-bearing and each is asserted:

- `ai-eng update` runs with its dirty-tree refusal, its no-keyboard refusal and its typed
  `y` intact. On a machine with no keyboard `--fix` therefore repairs the wiring and stops
  at the pin, which is the correct outcome and not a bug in the flag.
- `ai-eng init` runs with `-y`, which takes every default. Its defaults destroy nothing:
  the file picker arrives with nothing ticked, so `-y` overwrites none of the user's own
  files. `--fix` names `--no-project`, added for this, so repairing a machine never also
  sets up whatever repository the person happened to be standing in.
- **`init` does not write the pin when the pin exists.** This did not hold when this ADR
  was first written, and it is the one place the argument above was actually false: with
  `--project` naming a path, `init` rewrote `.ai/config.toml` unconditionally — taking a
  dated backup, which is a receipt and not a gate — and that resets the pinned version, the
  guard windows and the observability endpoint. Through `--fix` that is exactly the "verb
  with all three consent gates removed" ADR 0002 refused, arriving by the route this ADR
  says is safe. The rule is now the one this ADR needs to be true: `init` writes the pin
  when it is absent, `update` is the only verb that changes it, and a re-run says so.
- `doctor` with no flag is unchanged and still writes nothing. It stays safe to run
  anywhere, at any time, in CI and on a stranger's machine, which is the property 0002
  correctly identified as the reason it is worth having.

The verb table stays at ten. `--fix` is a flag on `doctor`, not an eleventh verb, which is
what option 2 of ADR 0002 was rejected for.

## Consequences

Better: a failure that a command can repair is one keystroke from being repaired, and a
failure that no command can repair says so in as many words instead of leaving the reader
to work it out. The cure is a field, so a test can assert the command without asserting a
sentence, and an agent reading the output does not have to parse English.

Also worse, and worth stating rather than discovering: two of the cures cannot reach every
shape of the failure they are named for. A Codex entry is appended and never reordered, so
a stale one stays stale; a skill root belonging to a surface that has been uninstalled is
linked by nothing. `--fix` re-runs the diagnosis and says so when the second pass is still
red, rather than leaving a person to run the same command again.

Worse: `doctor` now has a mode that writes, and "doctor is read-only" stops being true
without a qualifier. The qualifier is the rule above and it is enforced by `FIXES` holding
commands rather than callables — a check cannot smuggle a write in, because the only thing
it can name is a verb that already exists and already has its own consent. The honest cost
is that somebody reading `doctor --fix` in a script has to know that `ai-eng init -y` runs
underneath it; the flag prints every command before it runs it, for that reason.
