---
name: ai-issue-report
description: >-
  Reports a reproducible fault to a team or an upstream project — for ai-engineering itself
  or for any service the client is building — as a governed payload: closed allow-listed
  fields, scanned for machine paths, personal data (PII) and secrets before anything is
  written, draft kept local, and the exact bytes shown with their SHA-256 before anybody
  confirms anything. Trigger for "report this bug", "file an issue", "the framework is
  broken", "send this upstream", "write the incident report". Not for a fault in your own
  code that still needs a diagnosis — use /ai-debug first. Not for a vulnerability sent
  anywhere public: that routes to private disclosure, and this skill refuses the other way.
license: Apache-2.0
---

# ai-issue-report — report the fault, collect nothing on the way

## What it produces

A local draft (gitignored) plus the exact bytes that would leave, previewed with their
SHA-256 — and nothing sent by anybody but the user.

## The non-negotiable: what must never leave the machine

The payload is closed to allow-listed fields. Everything else is rejected at the gate,
before the draft exists:

- **Machine paths** — home directories and absolute paths on any OS: they leak the
  username and the project layout. The scan names the field and the match
  (`ACCEPTANCE_MACHINE_PATH_*`); the fix is to describe the same thing without the path.
- **Personal data (PII)** — emails, names, phone numbers, account ids, tokens in URLs.
  `ACCEPTANCE_PII_*` names what was found; rewrite the sentence, not around the value.
- **Secrets** — keys, passwords, session cookies, anything gitleaks would flag.
  `ACCEPTANCE_GITLEAKS_SECRET` is a hard refusal: no draft is written at all.
- **Logs, diffs, tracebacks, full command lines** — there is no field for them, by design.
  A pasted command carries the path it ran from and often the arguments it ran with. Write
  the four fields in your own words instead: title, what happened, what you expected, one
  step per reproduction step.

A vulnerability (`--kind security`) NEVER becomes a public issue: the refusal prints the
private disclosure route (SECURITY.md, the maintainer's security contact) and declines the
public one before asking anything.

## Steps

1. Reproduce it first. A report of something that happened once is a report the person
   reading it cannot act on; the steps field is what makes the difference.
2. Decide the kind before writing. Security → private route, always.
3. Write the four fields in your own words. Never paste logs, diffs or tracebacks.
4. Run the gate. Read the refusal if you get one: each code names what was found and in
   which field. Rewrite that field in words that do not carry the value — do not work
   around the scan.
5. Read the previewed bytes and their SHA-256. They are exactly what would leave. If
   anything in there is not yours to publish, stop.
6. Sending is separate and manual. Nothing is transmitted automatically: take the previewed
   bytes to the route your organisation or the upstream project uses (GitHub issue for
   bugs, SECURITY.md contact for vulnerabilities, your incident channel for incidents).

## Writing the prose

The write-up follows the framework's single writing standard — read it before writing the
fields: [ai-write › references/documentation-writer.md](../ai-write/references/documentation-writer.md).
One idea per sentence, one meaning per word, nothing the environment already says. When the
report is long (an incident post-mortem rather than a bug), hand the prose to /ai-write and
keep this skill's gate as the last step before publishing.

## The ai-engineering seam

1. The governed post-mortem lives at `.ai-engineering/reports/NNN-{slug}.html` — readable
   without session context; the NNN numbering is never rewritten.
2. It is immune while DECISIONS.md cites it; uncited, it expires to gc (§21.3) — history is
   not rewritten, it is archived in git.
3. The gate (paths/PII/secrets) runs on ANY text destined to leave a governed repo — it is
   the same discipline the git floor's gitleaks stage enforces at commit time, applied one
   step earlier, to prose.

## Routing

In scope: reproducible faults bound for a team, an upstream project, or an incident review.
Not for: undiagnosed faults (/ai-debug), internal findings worth remembering (/ai-note),
decisions (/ai-plan), the docs themselves (/ai-write).

Source: ai-engineering v1 skill `ai-report` (own), Apache-2.0 — renamed ai-issue-report.
