# Review · git-worktree-flow #7 — the smallest piece of each outside habit

## Goal
The smallest text additions: `skills/ai-audit-code/SKILL.md` gains the `file:line` citation discipline, a "Looks bad but is fine" section and the anti-false-positive plus verify-before-deleting guardrails; `skills/ai-security/SKILL.md` gains "no severity without an attack path" and the split between the hunter, the proof-of-concept and the validator. Nothing else from the three attachments is imported.

## Acceptance
1. `ai-audit-code` cites `file:line` and carries a "Looks bad but is fine" section.
2. `ai-security` states that no severity is given without an attack path and separates the hunter/PoC from the validator.
3. No other content from the three attachments is imported; the embedded assets are in sync.

## changed_files
- `skills/ai-audit-code/SKILL.md`
- `skills/ai-security/SKILL.md`
- `src/assets.ts` (regenerated)

## Verify commands
- `rg -q 'Looks bad but is fine' skills/ai-audit-code/SKILL.md`
- `rg -q 'file:line' skills/ai-audit-code/SKILL.md`
- `rg -q 'attack path' skills/ai-security/SKILL.md`
- `bun test tests/skills.spec.ts`
- `bun test tests/embed-canon.spec.ts`
- `bun run typecheck`
- `bun run lint`
- `bun run build`

## Context the reviewer should know
This is the last checkpoint, and the only one whose source is outside the repository: three skills a colleague passed in were reviewed during the design and only their best habits were kept. Attack the additions on two axes the gates cannot: whether a rule added here contradicts a rule the same file already states, and whether anything crept in beyond what the plan named. A skill that grows a second, softer version of a rule it already enforces is worse than one that grew nothing.

## F1 · BLOCKER · fixed
**Where:** skills/ai-audit-code/SKILL.md:75
**Critic (r1):** The new guardrail says "never a text search", but line 57 orders "grep every caller of the function you're about to touch" — grep *is* a text search. A reader now picks the softer of two versions, or obeys :75 and skips the caller sweep :57 mandates, shipping the sibling-caller bug line 60 warns about. → make :57 say "ask the language server for references (never a bare text search)" so one version of the rule survives. Check: `grep -n 'grep every caller\|never a text search' skills/ai-audit-code/SKILL.md` must show one rule, not two.
**Fixer (r1):** fixed — :75 now reads "search to locate, language-server references to prove"; :57's `grep every caller` stays as the locate step, so the two clauses name different jobs instead of two versions of one. verify: `grep -n 'grep every caller\|search to locate\|language-server references' skills/ai-audit-code/SKILL.md` ✓

## F2 · MAJOR · fixed
**Where:** skills/ai-security/SKILL.md:65
**Critic (r1):** "no severity without an attack path … one without a path is a note, not a finding" contradicts the file's own taxonomy: line 89 defines INFORMATIONAL as "a confirmed but minimal-impact observation with no standalone exploit" — a severity reserved for exactly the no-path case this line calls a note. It also restates §"Only report what you can exploit" (:61-63) and "Severity requires impact" (:81-91), a third copy of one meaning. → scope :65 to the CRITICAL–LOW grades, or amend :89; leave one statement. Check: does `findings.json` schema still admit INFORMATIONAL with no attack path?
**Fixer (r1):** fixed — :65 scoped in the headline itself: "CRITICAL through LOW take no severity without an attack path; INFORMATIONAL is the confirmed observation with no exploit, not a finding." The sentence survives because acceptance 2 names it; the contradiction with :89 is gone. verify: `rg -q 'attack path' skills/ai-security/SKILL.md` ✓

## F3 · MAJOR · fixed
**Where:** skills/ai-audit-code/SKILL.md:76
**Critic (r1):** "Never remove an entry point or a barrel re-export" is absolute and contradicts line 66 ("Deletion over addition") and rung 1 (:42): when a whole feature dies, its entry point and barrel re-export are dead weight the skill asks you to delete, and this guardrail forbids it. → qualify it ("while callers remain — verify references first"), the condition the same section already names. Check: is any barrel re-export in this worktree dead?
**Fixer (r1):** fixed — :76 qualified to "stays while callers remain — verify references first; the guard is the callers, not the file's role", so a dead barrel re-export is deletable again.

## F4 · MINOR · fixed
**Where:** skills/ai-audit-code/SKILL.md:77
**Critic (r1):** "Keep a symbol a test or a public API still uses — both are consumers" freezes a symbol whose only referent is a stale test, so dead code and its dead test survive together; the lazy fix is to delete both. → "a test or a public API that still needs it — delete the test with the symbol, never keep one for the other." Check: grep a renamed symbol's test references.
**Fixer (r1):** fixed — :77 now "Keep a symbol only while a caller or a public API needs it; a test that only asserted the symbol is not a consumer — delete the test with the symbol."

## F5 · MINOR · fixed
**Where:** skills/ai-audit-code/SKILL.md:73
**Critic (r1):** "A finding without a citation is a rumour" has no carve-out for a finding whose subject is a whole file, a missing abstraction, or a repo-wide pattern — none of which has one line, yet is a real audit result, not a rumour. → allow a whole-file or path citation. Check: name one legitimate no-single-line finding this rule would refuse.
**Fixer (r1):** fixed — :74 widens the citation to "`file:line`, or a file, symbol, or path when a line is not the right unit"; "rumour" now covers only a finding with no citation at all.

## F6 · MINOR · fixed
**Where:** skills/ai-audit-code/SKILL.md:79-85
**Critic (r1):** Every bullet already lives in the file — no interface/factory/config = :64, stdlib/native = rungs 3-4, one-liner = rung 6, todo `:` ceiling = :70 — so the section is a second source of truth for four rungs, against the documentation-writer's "one source of truth per meaning". Only the intro ("name the rung and stop") carries the new habit. → keep the intro and point at the ladder instead of re-listing it. Check: subtract the bullets and see whether any rule is lost.
**Fixer (r1):** fixed — the five bullets are deleted; §"Looks bad but is fine" now reads "Patterns a reader flags as bad that are deliberate under this skill, because each is a rung of the ladder above, not debt. Name the rung and stop." No rule is lost: each bullet was a rung or a Rules line already present.

ROUND 1: resolved 0 · withdrawn 0 · upheld 0 · new 6
Fixer round 1: fixed 6 · disputed 0

## Critic round 2 — rulings (all statuses updated on the finding blocks above: F1–F6 → resolved)

- **F1:** resolved — :75 now separates locate (`search`) from prove (`language-server references`); :57's `grep every caller` is the locate step, not a rival version. Read :57/:75; greps pass.
- **F2:** resolved — :65 is scoped to CRITICAL–LOW and names INFORMATIONAL as the no-path grade; no longer contradicts :89.
- **F3:** resolved — :76 is conditioned on callers ("stays while callers remain … the guard is the callers, not the file's role"); a dead barrel is deletable again, consistent with :66.
- **F4:** resolved — :77 deletes the test with the symbol instead of freezing both.
- **F5:** resolved — :74 widens the citation to file/symbol/path; "rumour" now covers only a total absence.
- **F6:** resolved — bullets gone, no rule lost (each was :64, rungs 3-4/6, or :70); the section keeps only the new habit, "name the rung and stop".
- **F6b:** the "Looks bad but is fine" heading now carries one sentence and no examples — accepted as the smallest delta the goal asked for; not a finding.
- **Regressions:** `bun test tests/skills.spec.ts tests/embed-canon.spec.ts` = 32 pass, gates green.

## F7 · MINOR · open
**Where:** skills/ai-security/SKILL.md:65
**Critic (r2):** The lead clause "No severity without an attack path" is absolute, and the file's own taxonomy makes INFORMATIONAL a severity with no path (:89) — the sentence's second half and :89 both contradict the headline, so a skimmer keeps the blanket version. → state the rule as "CRITICAL through LOW require an attack path" and drop the absolute lead; the `rg 'attack path'` gate still passes. Check: read :65 and :89 side by side.

ROUND 2: resolved 6 · withdrawn 0 · upheld 0 · new 1
