# Council — 028: the writer model, recorded

Five lenses read only `specs/028-writer-model-recorded/spec.md` and returned findings,
each carrying a command that was actually run on this tree. The second round crossed the
findings: some were refuted by another lens's command and are struck through below but
kept. This record is a reading, not a verdict on the plan.

## Lens: cost

- **Two of the three priced artifacts can land on this tree; the third is priced but
  deferred.** The costs option 1 advertises are "one new ADR, one corpus row, a baseline
  movement", but the ADR creation is refused while `madr.validate` is INCOMPLETE — the
  spec itself pins the refusal to the byte. So the actual landed cost of this decision
  today is one corpus row plus one register edit; the ADR is a cost that waits on a
  repair this decision does not authorize. Command: `grep -n "MADR_SCHEMA_INVALID\|refuses with" specs/028-writer-model-recorded/spec.md`
  → lines 71, 120, 150, 153, 167; line 153 reads "the verb refuses with `INCOMPLETE
  [MADR_SCHEMA_INVALID]` and writes nothing".

- **The "baseline movement" is not a number bump; it is a change of stance.** The
  register today records the skill_eval runner under `[[ungated]]` with reason "no
  baseline is recorded because a deterministic check has nothing to take a delta of, and
  `skill_eval_delta` says so in this register rather than pretending to a number". Moving
  the baseline to 350 as the spec promises means writing a number where the register
  currently argues determinism leaves nothing to measure — the cost is arguing that
  reversal, not editing a digit. Command: `grep -n "skilleval" policy/pilot-register.toml`
  → line 439 holds that reason verbatim.

- **The blast radius is bounded by the spec's own words, so the cost is knowable.**
  "Nothing else changes and nothing is authorized" closes the door on unpriced edits to
  the intent, the sequence policy, or the ai-build skill. Command: `grep -n "Nothing else changes" specs/028-writer-model-recorded/spec.md`
  → line 20: "has no route. Nothing else changes and nothing is authorized."

## Lens: reversibility

- **The change is reversible by delete-and-revert, because the model it records is
  already enforced elsewhere.** The corpus refusal is one row and the register edit is
  one stance; removing them restores the tree to a state where the writer model is still
  enforced by the intent, the sequence policy and the ai-build skill. The record grants
  no authority, so deleting it changes no behavior. Command: `grep -n "grants no authority" specs/028-writer-model-recorded/spec.md`
  → lines 18 and 164.

- **The one thing in view that is not reversible is out of scope, and the spec says so
  three times.** ADR 0025 "whose state lives in git history" is the inherited red; the
  spec refuses to authorize rewriting that history. Reversibility reading: the only
  irreversible part of this picture is the record this decision explicitly does not
  touch. Command: `grep -n "history" specs/028-writer-model-recorded/spec.md` → lines
  114, 116, 122.

- **The refusal's failure mode is loud, so a bad row is caught before it persists.**
  The spec prices the collision risk of the new corpus row and answers it with the check
  that would detect it, which makes an erroneous row a failing run rather than a silent
  drift. Command: `grep -n "collide\|catch it" specs/028-writer-model-recorded/spec.md`
  → lines 68-69: "must not collide with another skill's claim or refusal (it will not,
  and `skill_eval` would catch it)".

## Lens: the undecidable path

- **The ADR's title is a positional variable that the spec never pins.** `ai-eng decide
  "<title>" --spec 028` appears three times and no title is ever chosen; the filename
  `docs/adr/0028-*.md` is therefore undetermined until a caller supplies prose, and the
  record's identity rides on the number alone. Command: `grep -n '"<title>"' specs/028-writer-model-recorded/spec.md`
  → lines 85, 152, 164.

- **The "named person" is never named.** "Accepting it is a named person's act" appears
  twice, and no person appears anywhere in the spec; the acceptance path is an act the
  record does not route to anyone. Command: `grep -n "named person" specs/028-writer-model-recorded/spec.md`
  → lines 86 and 166.

## Lens: what is taken on trust

- **The non-collision of the corpus row is trusted to a check that is asserted, not
  shown.** The spec trusts `skill_eval` to catch a collision without showing the
  mechanism or the current refusal inventory it would collide against. The catch being
  real is the one load-bearing trust of the corpus half of the decision. Command:
  `grep -n "collide\|would catch it" specs/028-writer-model-recorded/spec.md` → lines
  68-69.

- **"Measured in this tree" covers quotations, not measurements.** The spec opens "What
  is true today, measured in this tree" and then quotes five files; only the digest is a
  verifiable token, and the word "measured" is doing the work of "quoted". Command:
  `grep -n "measured" specs/028-writer-model-recorded/spec.md` → lines 24 and 109.

## Lens: the example nobody wrote

- **The only example that can run today is the one least interesting to a person reading
  the decision.** The first two examples (`ai-eng decide --list` contains `0028` with
  status `proposed`; ADR 0028 validates) are both BLOCKED on this tree by the spec's own
  admission, and the third (skill_eval exits 0) is the mechanical one. The example
  nobody wrote is the intermediate tree: `--list` without 0028 while the refusal is
  present and the register is moved. Command: `grep -n "Blocked" specs/028-writer-model-recorded/spec.md`
  → lines 70 and 150.

- **No example quotes the refusal text.** The "labelled refusal" for the "case that
  currently has no route" is named but its label is never written, so the challenged-once
  claim that the refusal "cannot collide because the quoted case is specifically about
  recording the model" cannot be checked against anything. Command: `grep -n "case that currently has no route" specs/028-writer-model-recorded/spec.md`
  → lines 19-20 and 63.

- **The denial example under-covers its own list of fragments.** It denies modification
  of the intent, spec 013, and the one-writer rule, but D-028-01's rationale says the
  sequence policy and the ai-build skill "all record exactly this" model — and they are
  not in the denial. The denial example nobody wrote: "Given the sequence policy and the
  ai-build skill, none of them is modified." Command: `grep -n "Denial" specs/028-writer-model-recorded/spec.md`
  → lines 146-149 name only those three.

### Gaps no single lens named

- **The goal cannot complete on this tree by its own examples.** The cost lens saw two
  of three artifacts landing and the example lens saw the first two examples BLOCKED,
  but no lens connected the two into this: the decision's *first acceptance condition*
  ("the output contains `0028` with status `proposed`") is unreachable by any step this
  spec authorizes, so the entire deliverable of this goal on this tree is one corpus row
  and one register edit — everything else is the other spec's repair. Command: `grep -n "refuses with INCOMPLETE\|writes nothing" specs/028-writer-model-recorded/spec.md`
  → line 153: "the verb refuses with `INCOMPLETE [MADR_SCHEMA_INVALID]` and writes
  nothing".

- **The findability claim is not carried by the record's own metadata.** The decision "a
  reader and a gate can find" is keyed by the number 0028 and nothing else: the
  frontmatter `ref:` and `supersedes:` are both empty, so the numbered ADR carries no
  pointer to the spec that gates it (026) nor to the target it records (013) — the
  number is the entire link, and the number is chosen by a caller's title at promote
  time. Command: `grep -n "^ref:\|^supersedes:" specs/028-writer-model-recorded/spec.md`
  → line 6 `ref: ""`, line 7 `supersedes: ""`.

### Findings cut for carrying no command

- Whether a fourth home for the model is "good documentation" or "duplication" is the
  strongest counter-argument to the decision, and the spec settles it by prose in the
  challenged-once section; no command separates the taste from the fact, so the judgment
  is cut rather than forced into a check it does not have.

### Findings the cross-read refuted, with the command that refuted them

- ~~**Do-nothing is the zero-cost option.** Option 2 "gives: nothing to review" — no
  edits, no row, no register movement — so the cheap path carries no price worth
  weighing. Command: `grep -n "Do nothing" specs/028-writer-model-recorded/spec.md` →
  line 75: "2. **Do nothing; keep the model implicit.**"~~ Refuted by the reversibility
  lens's command `grep -n "drifts silently" specs/028-writer-model-recorded/spec.md` →
  line 78: "Risks: the model drifts silently across the three files." Zero-cost is true
  only for the commit; the spec itself prices the deferred cost, and silent drift across
  three files is the one outcome that cannot be reverted because it was never recorded.

- ~~**The intent digest `ae523990` is taken on trust.** The spec quotes it as the
  "approved digest" and a reader cannot tell from the spec whether the file on disk
  still carries it. Command: `grep -n "ae523990" specs/028-writer-model-recorded/spec.md`
  → line 26 only.~~ Refuted by the trust lens's own cross-check `grep -n "ae523990" .ai/intent.md`
  → lines 8 and 15, `"approval_ref": "ae523990"` both present. The trust is grounded in
  the file and a one-command check resolves it, so the finding's load-bearing claim
  fails; the residue is a doc nit — the spec quotes a digest it could have verified.

- ~~**Whether `ai-eng decide` accepts the ADR is undecidable on this tree.** The spec
  asserts schema-conformance ("it will be") while `madr.validate` is INCOMPLETE, so the
  claim cannot be checked today. Command: `grep -n "schema-conformant\|it will be" specs/028-writer-model-recorded/spec.md`
  → line 67.~~ Refuted by the example lens's command `grep -n "Blocked —\|refuses with" specs/028-writer-model-recorded/spec.md`
  → lines 150 and 153: the spec already pins today's path to the byte — "refuses with
  `INCOMPLETE [MADR_SCHEMA_INVALID]` and writes nothing" — so the path is not
  undecidable, it is deterministically blocked and specified; what remains undecidable is
  only the post-repair path, which the spec also pins ("validates and is not the cause of
  a new MADR failure").

## The two counts

- Gaps that appeared only after the cross-read: **2**
- Findings deleted, for carrying no command or for being refuted: **4**