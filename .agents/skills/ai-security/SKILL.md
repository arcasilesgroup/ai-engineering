---
name: ai-security
description: >-
  Reasons about trust boundaries, authentication, data, dependencies, skills and supply
  chain, runs the scanners this repository already pins, and reports PASS, FAIL or
  INCOMPLETE with the command behind each one. Trigger for "threat model this", "is this
  auth safe", "review the trust boundary", "audit these dependencies", "can this skill be
  made to do something else". Not for judging a diff on its merits — use /ai-review, whose
  security lens does that. Not for accepting a risk — use `ai-eng accept`, which needs a
  named person, a reason and an expiry. It replaces neither the guards nor CI, and it never
  declares compliance with anything.
license: Apache-2.0
compatibility: needs ai-eng
disable-model-invocation: true
---

# Say what is exposed, run what can be run, and never call the rest green

## What it produces

A threat and data model in the spec, and a list of findings where each one names the
command that produced it and its outcome. This framework wrote its own first, in
`policy/threat-model.toml`: one row per boundary, each naming what an attacker controls,
what happens with no control, the file that holds the control and the test that proves it
can still say no. Read it as the worked example, and for the shape a row takes when the
control is only half built.

## Steps

1. Draw the boundary before reading any code: what crosses it, who controls each side, and
   what an attacker who owns one side can reach on the other. A finding with no boundary is
   a preference.
2. Say where the data is. Classification, where it rests, where it travels, who can read it,
   and what leaves the machine. `ai-eng report issue` exists because that last one is the
   question people get wrong under pressure.
3. Run the scanners this repository already pins and paste their output: `just security` is
   gitleaks at its exact version, semgrep against `policy/semgrep.yml`, and trivy. A scanner
   that is absent or the wrong version is INCOMPLETE, never PASS — a bound read as clean is
   a bound turned into a bypass.
4. Read what the scanners cannot: authorisation logic, trust in a payload, a guard that
   fails open, a skill whose instructions can be redirected by content it reads.
5. Challenge your own finding once. State the strongest case that it is not exploitable
   here, and keep it only if that case fails. An unexploitable finding spends somebody's
   afternoon and teaches them to skip the next one.
6. Report each finding as PASS, FAIL or INCOMPLETE with the command beside it. Nothing is
   PASS because it looks fine; INCOMPLETE is the honest answer and it is not a failure. One
   finding is seven fields and no eighth: the boundary it crosses, what an attacker controls,
   the reachable effect, the state, the exact command or the file and line that decides it,
   the refutation you tried in step 5, and what would close it. A field left blank makes the
   finding INCOMPLETE — a finding whose effect nobody wrote down is a preference with a
   severity attached.
7. Stop at the boundary of your authority. Accepting a risk is `ai-eng accept` with a named
   person, a reason and an expiry date. Compliance is a claim about an organisation and this
   skill has no standing to make one.

## Done when

- The boundary and the data are written down, not implied.
- Every finding names the command that produced it, and every unrun check says INCOMPLETE.
- No risk was accepted here, no guard was replaced, and no compliance was declared.
