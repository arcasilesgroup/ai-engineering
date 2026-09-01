# prototype — make something rough to react to

Some questions can't be talked out. "How should this look," "how should this feel to use," "does this flow make sense" — the user doesn't know until they see something. Asking harder doesn't help; building something rough does.

It also solves the hardest problem here: **what do you compare against when there's no famous thing to point at?** Most of a business has no Stripe to hold up beside it. So you build a rough version, the user reacts to it, and **the thing you built becomes the reference** — a real, openable artifact where before there was only an adjective.

## Build it rough, and mean it

1. **Throwaway from the first line, and obviously so.** Name it so nobody mistakes it for the real thing.
2. **One command or one double-click to run.** If the user has to think about how to start it, the prototype has already failed.
3. **No persistence, no tests, no error handling, no abstractions.** You're buying a reaction, not building a foundation.
4. **Several variations, not one.** One version gets you "yeah, fine." Three genuinely different versions get you "that one, but the header from the second." Make them differ in the thing actually being decided, not in colour.
5. **Make switching between them trivial** — a toggle, a URL parameter, tabs. The user should be able to flip back and forth in a second.

## The user picks. Always.

Show the variations. **Do not choose.** Do not narrow to a favourite and present it as the outcome. Do not say "I went with the second one because it's cleaner."

Picking is the decision, the decision is the user's, and an agent that builds three options and quietly selects one has replaced the interview with its own taste — which is the exact thing this whole skill exists to prevent.

Ask which one, and why. The *why* matters as much as the pick, because it's usually a general principle in disguise, and general principles produce more checks than a single answer does.

## Capturing it

Once the user has picked:

1. **Keep the chosen prototype, in a form that still opens.** Do not delete it when the decision is folded in — it is now a **reference**, and a reference that can't be opened is worth nothing.

   This is stricter than it sounds. Whoever grades the finished work will be a stranger in a fresh session, possibly weeks later, with no idea how this project runs. A prototype that needs `pnpm dev`, a scratch database, and the right branch checked out is **not** a reference to that person — it's a dead link.

   So park it as **one of two things**:
   - **a single self-contained file that opens on a double-click** — one HTML file with everything inlined, no build step, no server, no dependencies; or
   - **a screenshot**, if what was decided is purely how it looks.

   If the chosen prototype isn't already one of those, convert it before recording the decision. Inline the styles, stub the data, save the file. Then note the exact path in the answer.
2. **Write the answer** into the map: what was picked, why (the user's words, not your summary of them), and the check.
3. **The check for a prototype question is almost always `A/B pick`**, with this prototype as the reference. That's the point of having built it.

Occasionally the reaction produces a hard rule — "the empty state must always tell you what to do next." That's a **run it** check, and it's better than the A/B. Take it when it appears.

## When the prototype changes the question

A prototype often reveals that you were asking the wrong thing. The user sees it and says "actually, none of these — the whole flow is wrong."

That's a success, not a wasted round. Rewrite the question, re-order the list, and say plainly what changed. Finding this out now is worth more than the prototype cost.
