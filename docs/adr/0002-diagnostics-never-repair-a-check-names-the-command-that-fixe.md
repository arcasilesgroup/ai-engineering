---
status: superseded by 0003
date: 2026-08-08
spec: 005-init-says-what-it-did
supersedes: ""
---

# 0002. Diagnostics never repair; a check names the command that fixes it

## Context and problem statement

The previous version of this product shipped `ai-eng doctor --fix`, with nine remediating
checks. Reading it turned up the shape of the temptation: a doctor already knows exactly
what is wrong, so repairing it looks free. It is not free. Of the four repairs that would
plausibly apply to this tree, two are writes `ai-eng init --project` already performs, and
one rewrites `.ai/config.toml` — the pin, the file that names which version governs a
repository. The verb that legitimately rewrites it, `ai-eng update`, refuses on an
unpinned repository, refuses on a dirty tree, and refuses without a keyboard. A `--fix`
that re-pins is that verb with all three consent gates removed, wearing a diagnostic
verb's name. The old implementation also demonstrated the end state: its interactive
"Fix? (y/n/all)" prompt was decorative, because every fix had already been applied before
the question was asked.

Underneath the request is a real complaint. A person who runs `doctor`, reads a failure
and does not know what to type has been told nothing useful. Every check message in this
tree names the problem and none of them names the cure.

## Considered options

1. **A `--fix` flag with a repair slot on each check.** Delivers the ask. Costs a second
   entry point to writes that already have a consented verb, a fourth outcome in the
   printer, and — measured against this repository's own test-to-product ratio and its
   mutation floor — several times the line count its product half suggests.
2. **A separate `ai-eng repair` verb.** Same writes, same consent problem, plus an
   eleventh verb in a CLI whose table is asserted at ten.
3. **Leave `doctor` read-only and make its messages actionable.** Every check that has a
   cure ends its message with the command that applies it. The person types it, or the
   agent does; the consent gates of that command stay where they are.

## Decision outcome

Option 3.

`doctor` is defined in the verb table as the assertions and the coverage line, and asked
as a question: is the system healthy now? A verb that answers a question and changes the
answer while doing it is two verbs. Keeping it read-only is also what makes it safe to run
anywhere, at any time, in CI and on a stranger's machine, which is the property that makes
it worth having at all.

The rule, stated so it can be applied to checks that do not exist yet: **a check reports;
it never writes. A check that knows the cure ends its message with the command.** If no
command exists for a failure, that is a gap in the verbs, and it is filled by a verb with
its own consent, not by the diagnostic.

## Consequences

Better: `doctor` stays safe to run unattended, the writes keep the gates their verbs
already carry, and the person gets the actionable half of `--fix` for the cost of a few
words per message. The verb table stays at ten.

Worse: repairing several problems takes several commands instead of one flag, and a check
whose cure is a manual edit still hands the person prose rather than a command. Somebody
will ask for `--fix` again; this file is the answer, and the answer is allowed to change
only by superseding it.
