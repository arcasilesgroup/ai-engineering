---
name: ai-report
description: >-
  Reports a reproducible fault in this framework through `ai-eng report issue`: a payload
  closed to nine allow-listed fields, scanned for machine paths, personal data and secrets,
  written as a local gitignored draft, and shown as the exact bytes with their SHA-256
  before anybody confirms anything. Trigger for "report this bug", "file an issue about
  ai-engineering", "the framework is broken", "send this upstream". Not for a fault in your
  own code — use /ai-debug, which finds a cause at file:line. Not for a vulnerability sent
  anywhere public: that routes to private disclosure and this command refuses the other way.
license: Apache-2.0
compatibility: needs ai-eng
disable-model-invocation: true
---

# Report the framework's own fault, and collect nothing on the way

## What it produces

`.ai/issue/draft.json` — local, gitignored, previewed byte for byte, and sent by nobody
but you.

## Steps

1. Reproduce it first. A report of something that happened once is a report the person
   reading it cannot act on, and the steps field is what makes the difference.
2. Decide the kind before you write. `--kind security` never becomes a public issue: the
   command refuses that route before it asks you anything, and prints the private one.
3. Write the four fields in your own words: the title, what happened, what you expected,
   and one `--step` per step. Never paste a log, a diff, a traceback or a command line —
   there is no field for any of them, and a pasted command carries the path it ran from.
4. Run it:

   ```bash
   ai-eng report issue --kind bug --title "…" --what-happened "…" \
     --expected "…" --step "…" --step "…"
   ```
5. Read the refusal if you get one. `ACCEPTANCE_MACHINE_PATH_*`, `ACCEPTANCE_PII_*` and
   `ACCEPTANCE_GITLEAKS_SECRET` each name what was found, no draft is written, and the fix
   is to say the same thing without the value it carried.
6. Read the bytes it prints. They are exactly what would leave, and the SHA-256 beside them
   is of those bytes. If anything in there is not yours to publish, stop.
7. Sending is separate and manual. `--submit` asks for a phrase carrying that digest at your
   keyboard, and then says there is nowhere to send: no destination is configured and this
   package has no transport. Take the previewed bytes to the route your organisation uses.

## Done when

- Every field is a sentence you wrote, and nothing in the payload was collected.
- The scan came back clean, or you rewrote the field it named rather than working around it.
- A vulnerability went to private disclosure and no public issue exists for it.
