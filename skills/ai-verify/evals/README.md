# Evals — test the reviewer, not just the code

> An untested review skill reports "no issues found" when it is broken, and that reads
> exactly like good news. — §15 of the setup guide

This is the harness for that section. It plants known defects in a working repo, runs your
review skill against them, and scores the report on the two numbers that matter:

- **Recall** — how many planted defects did it find? Misses mean the instructions are too
  vague about what to look for.
- **Precision** — of everything it reported, how much was real? Noise means the
  false-positive gate is too weak, usually because you did not require a concrete failure
  case.

Both numbers, always. A skill tuned only for recall reports everything and gets ignored; a
skill tuned only for precision reports nothing and looks clean. The pair is the signal.

Python 3.8+, stdlib only. Nothing to install.

---

## The one rule

**The answer key never enters the repo.** `plant.py` writes it to
`~/.claude/evals/<repo>-<stamp>/`, outside the working tree, because a review that finds
the planted bugs by reading the list of planted bugs tells you nothing — and an agent with
`Read` will find that file if it is anywhere under the project root.

Do not paste the key into the session. Do not summarise it for the reviewer. Do not tell
the reviewer how many defects there are: "find the 6 bugs" turns a precision test into a
scavenger hunt, and the agent will keep reaching until it has six things to say.

---

## Run one

```bash
AV=/path/to/ai-verify

# 1. plant — from a clean tree, on a scratch branch
python3 $AV/evals/scripts/plant.py --pack $AV/evals/packs/example-node-web/answer-key.json

# 2. review — in your agent, on the branch it just created
#    "run code-audit on this branch"   (or full-review, or the skill under test)

# 3. score
python3 $AV/evals/scripts/score.py --run ~/.claude/evals/<repo>-<stamp>/manifest.json

# 4. put the repo back
python3 $AV/evals/scripts/plant.py --cleanup
```

`plant.py` refuses to run on a dirty tree — planting on top of uncommitted work makes the
diff scope meaningless, and the reviewer would be reading your work-in-progress as if it
were the change under test.

Step 2 is the part that must stay honest. Run it in a **fresh session** with no memory of
this one, phrased the way a normal person would phrase it. If you have to coach the skill
into firing, that is a finding about the `description`, and it is worth more than the
recall number.

### Scoring, and what it will not do for you

Recall is computed automatically — a defect is at a known `file:line`, so a finding either
points at it or does not (±8 lines by default; `--window` to change).

Precision is not automatic, and pretending otherwise would be the same flattery this
harness exists to catch. Every finding that does not map to a planted defect goes into
`triage.json` as `unknown`, and you decide:

```jsonc
{
  "code-audit::Prefer const assertions on the status union": "noise",
  "security-audit::Race between check and write in the payment path": "real"
}
```

Then `score.py --run ... --adjudicate`. Until every finding is judged, precision reads
`pending` rather than guessing in the skill's favour.

Two judgments worth making consistently:

- **A real bug you did not plant is `real`.** It counts as a true positive. Reviewers that
  find genuine unplanted bugs are the good outcome, not an accounting problem.
- **A finding you cannot decide about is `noise`.** If the report did not make it
  decidable, nobody would have actioned it either.

The scorer also reports two things beyond the headline numbers:

| Signal | What it means |
|---|---|
| **Weak match** | The finding points at the right line but describes something else. The reviewer noticed the area and misread the defect — usually an instruction problem, not a retrieval problem. |
| **Wrong lane** | The defect was found, but by a lane that does not own it. Fine once; a pattern means your lane boundaries in `CONVENTIONS.md` are not landing, and `full-review`'s dedupe is doing work the lanes should have done. |

---

## Write your own pack

The example pack is a demo. The packs that improve *your* skills are built from **your**
repo, because the defects that matter are the ones your codebase actually produces.

A pack is one JSON file. Each bug is a find/replace edit against a real file, plus the
metadata the scorer needs:

```json
{
  "pack": "my-app-v1",
  "bugs": [
    {
      "id": "B1",
      "class": "missing-authorization",
      "lane": "security-audit",
      "severity": "critical",
      "file": "src/api/orders.ts",
      "find": "  requireAdmin(session, now);",
      "replace": "  requireUser(session, now);",
      "expect": "any logged-in user can now delete any order",
      "match": ["admin|authoriz|permission"]
    }
  ]
}
```

| Field | Notes |
|---|---|
| `find` | Must match **exactly once** in the file, or set `"occurrence": n`. `plant.py` fails loudly rather than guessing. |
| `replace` | The defect. Keep it small — a one-line edit that a human reviewer would plausibly write. |
| `lane` | Which skill *should* catch it. Drives the wrong-lane signal. |
| `expect` | Plain-English description of the failure. This is what you read when it gets missed. |
| `match` | Optional case-insensitive regexes, **all** of which must appear in the finding's text for a full match. Location alone counts as a weak match. Keep these loose — you are checking the reviewer described the defect, not that it used your words. |

Build a pack from a real commit history: `git log` for the bugs you actually shipped and
fixed, then re-plant them. Defects invented from scratch test the reviewer against your
imagination; defects from your own history test it against reality.

Keep packs small — six to ten defects. Beyond that the review's own scope handling starts
dominating the score and you stop learning anything about the instructions.

When the repo moves and a `find` no longer matches, `plant.py` stops with an error. Fix
the pack. Do not loosen the match to make it apply — a fuzzy anchor plants the defect
somewhere you did not intend and the line numbers in the key go quietly wrong.

See [`bug-catalog.md`](bug-catalog.md) for what to plant.

---

## Reading the result

| Shape | What to change |
|---|---|
| Low recall, low precision | The skill is not really running. Check it fired at all, and that scope resolved to the branch rather than the whole repo. |
| Low recall, high precision | Instructions too vague about *what* to look for. Add the specific constructs — name the sinks, name the states, name the patterns. |
| High recall, low precision | The false-positive gate is not biting. Require trigger + consequence + evidence per finding, and make "reporting zero findings is a valid result" explicit. |
| High recall, high precision | Ship it. Then re-run the same pack after any edit to the skill — this is a regression suite now. |
| Recall drops after an edit you thought was neutral | Trust the number. This is the whole reason the harness exists. |

Two failure modes the numbers will not show you, so watch for them by hand:

- **The skill never fired.** Zero findings and a perfect false-positive record look
  identical to a skill that did not load. Confirm it activated before you read any score.
- **The skill fixed the bugs.** A reviewer that edits source is out of contract
  (`CONVENTIONS.md` §7) and will also quietly change the lines the scorer is looking for.
  `git status` after the run; if the tree is dirty, the score is meaningless.

---

## Files

```
evals/
├── README.md                 this
├── bug-catalog.md            what to plant, by class and by lane
├── scripts/
│   ├── plant.py              apply a pack on a scratch branch; write the key outside the repo
│   └── score.py              parse reports, compute recall, collect precision triage
├── packs/
│   └── example-node-web/
│       └── answer-key.json   6 defects across 4 lanes
└── fixtures/
    └── node-web/             a tiny correct repo the example pack applies cleanly to
```

To try the whole loop without touching a real project:

```bash
cp -R $AV/evals/fixtures/node-web /tmp/eval-demo && cd /tmp/eval-demo
git init -q && git add -A && git commit -qm init
python3 $AV/evals/scripts/plant.py --pack $AV/evals/packs/example-node-web/answer-key.json
```
