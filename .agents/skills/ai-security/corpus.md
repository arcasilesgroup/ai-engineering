# Corpus: ai-security

Reasons about trust boundaries, authentication, data, dependencies, skills and supply
chain; runs the pinned scanners and reports PASS, FAIL or INCOMPLETE with the command
behind each answer. It accepts no risk, replaces no guard and declares no compliance.

## Routes here

- "threat model this feature before we build it" — the boundary and the data model are this skill's first two steps.
- "is this token check actually safe" — authorisation logic is what the scanners cannot read, which is why a person routes it here.
- "audit our dependencies and tell me what is exposed" — deterministic scanners per stack, with their output pasted and their absences reported as INCOMPLETE.
- "can this skill be talked into doing something else by a file it reads" — a skill whose instructions can be redirected by content is exactly this skill's territory.
- "what data leaves this machine and who can read it" — where data rests, where it travels and what crosses the boundary.
- "the supply chain for this release, end to end" — dependencies, provenance and what is unverifiable, each with its own outcome word.

- "scan our deployed staging URL for vulnerabilities" — routes here and the answer today is INCOMPLETE: no scanner in this repository touches a running target, and the contract for one is a spec nobody has approved.

## Refuses

- "accept this risk for now, we will fix it next quarter" — use `ai-eng accept`, because a risk needs a named person, a reason and an expiry date, and no skill can supply any of the three.
- "tell the customer we are SOC 2 compliant" — refused outright: compliance is a claim about an organisation, and this skill has no standing to make one.
- "review this diff and tell me if it is good enough to merge" — use `/ai-review`, because merge-ready judgement is a separate pass with its own lenses, one of which is security.
- "the scanner is failing the build, make it stop" — use `/ai-debug` for the cause, and rule 3 for the rest: silencing a linter or a scanner is never this skill's answer.
- "write the fix for the vulnerability you found" — use `/ai-build`, because implementing against a plan is its job, and the same hands that found a hole do not quietly patch it and call it reviewed.
- "report this vulnerability upstream" — use `/ai-report`, which routes a vulnerability to private disclosure and refuses to put it in a public issue.
- "we do not need CI, this skill checks everything" — refused: it replaces neither the guards nor CI, and a scan run once by hand is not a control.
- "this dependency version is vulnerable, I remember the advisory" — refused: the installed version decides (`versions.verify_against_installed`); a memory claim is unverified, and a finding that contradicts the installed bytes is dropped.
