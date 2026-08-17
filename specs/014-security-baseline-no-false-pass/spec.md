---
id: "014"
slug: security-baseline-no-false-pass
status: draft
date: 2026-08-15
ref: ""
supersedes: ""
---

# The security baseline that cannot fake a pass

Draft. It carries `status: draft` from the first keystroke and lives in the tree because
this repository has no `drafts/`, so `git clean` cannot eat it. It authorises nothing.
Nothing may be implemented from it until a human approves it at an exact digest, and
approving it approves no plan.

Derived from the P4 contract spec 010 froze, from the twelve P4 statements EP-041..EP-052,
from the twenty-five unassigned contracts EP-258..EP-282, and from
`.ai/reports/security-toolchain-research/index.html` — a third report in that directory
that nothing had audited until this spec read it.

## Context and problem

This repository already runs real scanners, and that is the problem: it runs enough of them
to look finished and not enough to prove anything about the artifact it ships.

**What runs today, measured.** `just security` is inside `just check` and executes three
engines: `gitleaks dir . --redact --no-banner --exit-code 1`, `semgrep scan --config
policy/semgrep.yml --error --quiet`, and `trivy fs --scanners vuln,license,misconfig
--exit-code 1 --severity CRITICAL,HIGH,MEDIUM .`. CI adds `pip-audit --strict` over an
exported `requirements.txt`, SonarCloud and Snyk Code, both conditional on a secret being
present.

**The pins.** CI pins gitleaks, trivy, actionlint, pip-audit, mypy and snyk by version,
plus semgrep and zizmor by package. Locally only semgrep is pinned, in the `justfile`.
`just security` takes whatever `gitleaks` and `trivy` are on the developer's PATH. Local
and CI can therefore disagree on two of three engines with nothing reporting the
difference.

**The scanners themselves are unverified bytes.** `check.yml` downloads three tarballs.
Only actionlint's is checked against a SHA-256. gitleaks and trivy are `curl` then `tar`
with no checksum, no signature and no digest. The tools that guard the supply chain arrive
outside it.

**There is no SBOM.** `grep -rn "cyclonedx\|sbom\|spdx"` over `*.py`, `*.yml`, `*.toml` and
`justfile` returns two hits, both in `tests/test_p0_completeness.py`, where `"SBOM"` is
listed as a word belonging to a later wave. `release.yml` has trusted publishing,
`actions/attest-build-provenance` over `dist/*`, and `pypa/gh-action-pypi-publish`. Nothing
computes a SHA-256 of the wheel and nothing compares one. `release.yml` states in its own
header that attestations ship "so `ai-eng doctor` can verify that the running wheel is the
one this tag produced" — `grep -n "attest" src/ai_engineering/*.py` returns nothing. The
comment describes a verifier that does not exist. That sentence is the exact defect this
product exists to cure, sitting in our own release workflow.

**There is no native scanner and no `ai-security`.** `.agents/skills/` holds eight skills
and none is it. `ai-review/SKILL.md` names a security checklist as one lens among several,
which is judgement, not a detector. Nothing in the repository emits SARIF: `grep -rn
"sarif"` over `*.py`, `*.yml` and `justfile` returns nothing. `policy/semgrep.yml` carries
three rules of our own — `suppression-comment`, `shell-with-user-string`,
`tilde-in-config-value` — and `policy/iocs.yml` sixteen patterns read by
`hooks/injection_guard.py`. Both are pinned in-tree and both are narrow by design. Neither
reads a skill file, an egress declaration, a symlink or an unpinned dependency.

**Fifteen capabilities are declared and none is enforced.** `policy/capabilities.toml`
declares fifteen capabilities with `read_roots`, `write_roots`, `exec_allowlist`, `network`,
`secrets`, `human_gate`, `enforcement` and `proof_requirements`. `capability.preflight`
validates all of it and then returns `INCOMPLETE` with `CAPABILITY_ENFORCEMENT_UNAVAILABLE`
on every path, including the one where the action was fully declared. `ai-eng doctor` check
23 now prints it. The executor is P4 work and this spec owns it.

**Redaction protects less than the word suggests.** `hooks/_otlp.py` keeps eight envelope
fields verbatim and nine data fields verbatim. Everything else in `data` leaves as a hash
and a length — unless `redact` is configured as `"none"`, in which case it leaves whole.
Two things are never redacted in any mode. First, `_otlp.py` rewrites `data["command"]` to
its first two whitespace-separated tokens *after* the opaque pass, so those two tokens
always leave in plaintext, strict included. Second, every payload carries `host.id` from
`machine_id()` and `vcs.repository.id` from `repo_id()` as resource attributes.
`machine_id` is a `uuid4` fragment written once; `repo_id` is derived from the sha of the
first commit so it survives clones and forks. Those are stable pseudonyms, correlatable
across every export, and redaction never touches them. EP-048 names exactly this and does
not define its own scope, so this spec defines it.

**The adversarial suite has one control for thirteen attacks.** `tests/adversarial/run.py`
declares fourteen cases. Thirteen are attacks — injection on file read, injection on tool
result, loop, protected branch, commit message, staged secret, pushed secret, exhausted
retries, guard crash, no plan, `--no-verify`, self-protection, guard gone inert — and one
is `negative_control`, which covers reads, writes, a commit, two pushes and a fixup in a
single case. The two receipts are written separately and neither may hide inside the other.
That is better than one receipt and it is not what EP-286 asks for: each attack needs a
clean control near it, not one shared control near the suite.

**The consumer gets less than we run.** `skeletons.py` writes the client `justfile` with
gitleaks and trivy only, and says so in a comment: static analysis needs a rule set per
language and we do not ship a credible cross-language one. Every consumer repository
therefore has a `just check` whose security lane cannot read code. Separately, `init.py`
states the verb never installs a binary, so a managed gate can be wired before the tool it
calls exists.

**Safe reporting does not exist yet.** `report issue` returns INCOMPLETE and says it is
planned for P2. EP-270..EP-275 are therefore unmet by construction, and nothing today can
leak through a path that has no code.

### What the third report changes

`.ai/reports/security-toolchain-research/index.html` was read in full for this spec. Six
things it changes, and one it does not.

1. **It picks one SCA engine.** Trivy covers dependencies, licences, IaC, images and SBOM
   generation, and can read an SBOM back. OSV-Scanner, Syft and Grype are each evaluated
   and discarded as a second binary, a second matrix and a second deduplication problem
   with no reproducible gap behind them. EP-045 says "OSV/pip-audit"; the report narrows
   that to pip-audit until Trivy over `uv.lock` demonstrates parity, then one engine.
2. **It adds DAST, which EP-041..EP-052 never mention.** OWASP ZAP Baseline as an on-demand
   mode of `ai-security`, post-deploy, target and authorisation supplied by the operator,
   never a stored URL, and never a new `ai-dast` skill. That is new scope, and this spec
   refuses it here (D-014-11) rather than absorbing it silently.
3. **It adds two stack adapters and names the honest hole.** ShellCheck for Bash and
   PSScriptAnalyzer for PowerShell, and it records that PowerShell has no declared coverage
   in the Semgrep, Sonar or Snyk matrices — so a stack manifest may not mark it covered.
4. **It finds one defect this spec must fix, and the finding holds.** It reports that
   gitleaks and Trivy are pinned by version but their downloaded files are not verified by
   checksum or signature, while actionlint is. Verified independently above.
5. **It proposes reversing `init`'s stated contract.** Tools before hooks, with consent
   shown before the first write, pins and integrity, adoption of an existing admitted
   version, receipt and exact uninstall. That contradicts `init.py`'s own never-list, so it
   is a contract change requiring its own decision, not an addition.
6. **It corrects two names in the original request.** "Tavily" was read as Trivy and
   "OWASAP" as OWASP ZAP. Tavily is a search and extraction API and is not an SCA engine.

What it does not change: the four engines stay pinned specialist tools, no vendor becomes a
dependency, the SBOM must name the same digest as the wheel, a missing lane is
`INCOMPLETE`, and there is no `security` verb. It also states plainly that none of this may
be implemented inside P0. This spec agrees on every one of those.

## Options considered

**A. A portable baseline of pinned engines, a native detector layer for what no engine
owns, one findings schema with four states, and a release lane that binds wheel,
attestation and SBOM to one digest.** The three engines stay and get verified bytes and
matched pins. A stdlib-first scanner reads what gitleaks, Semgrep and Trivy structurally
cannot: our own skill files, our own policy files, declared-versus-observed capability
scope. Every lane emits the same closed JSON and SARIF. Every detector has a malicious
fixture and a clean control beside it. The capability executor lands and check 23 goes
quiet because it became false, not because somebody deleted it.

*Gives:* a security answer that can go red for a stated reason, and a release whose
artifact can be checked by somebody who does not trust us. *Costs:* a detector layer, a
findings schema, a fixture per detector, an executor, and a tamper fixture in CI. *Risks:*
a detector layer is where false positives live, and a scanner people learn to ignore is
worse than none — the precision constraint `policy/iocs.yml` already carries has to extend
to every new detector. *Rules out:* treating "the engine exited 0" as the whole answer.

**B. Orchestration only: keep the three engines, add the SBOM and the digest check, skip
the native scanner and the executor.** Roughly a workflow change and a comparator.

*Gives:* EP-047, EP-049, EP-051 and EP-052 closed in a fraction of the work, and the
release becomes verifiable by a stranger. *Costs:* nothing scans a skill file, so the class
of artefact this product actually ships stays unexamined by anything. *Risks:* it
reproduces today's defect at a higher standard — the release would be provably the wheel we
built, and nothing would have looked inside it. *Rules out:* nothing, and leaves check 23
printing its sentence indefinitely.

## Decision

**Option A.** The deciding reason is not coverage: it is that B cannot answer the question
this product is for. gitleaks finds a credential, Semgrep finds a pattern in code and Trivy
finds a known CVE in a dependency. None of the three has an opinion about a skill file that
tells an agent to read a config directory and post the contents somewhere. That artefact is
what this wheel distributes, and no pinned engine owns it. The native layer exists for
exactly that gap and for nothing else.

**Challenged once, honestly:** the strongest case against A is that it is the shape of the
528-file installer this project already deleted once — a control plane, a manifest, a
schema and a scanner, arriving together, most of it unprovable on the day it lands. That
case is real and it changes the shape. The detector layer lands one detector at a time,
each with its malicious fixture red before the detector exists and its clean control beside
it, and a detector with no fixture is not shipped. The executor lands binding one action
kind, not fifteen capabilities. `INCOMPLETE` stays the default answer at every stage, so a
half-built lane reports as half-built rather than as absent.

## Normative contract

Reproduced in obligation from spec 010, which froze it. Where this section and spec 010
differ, spec 010 governs and this document is wrong.

Portable baseline first. gitleaks, Semgrep, an OSV/pip-audit path and Trivy remain pinned
specialist engines. Their parsers, rule engines and vulnerability databases are never
reimplemented here. An engine binary is verified — checksum, signature or OCI digest —
before it is executed, and an engine that cannot be verified is not run and the lane is
`INCOMPLETE`.

Optional external products may cross-check. SkillSpector, Claude Security, SonarCloud and
Snyk are cross-checks only. Their absence never disables the portable baseline, never
lowers a state and never appears as a failure; a cross-check that is configured and did not
run is `INCOMPLETE`, and a cross-check that is absent is `N/A`.

The native scanner is stdlib-first and has deterministic detector classes for hidden
instructions, invisible Unicode, executable content, undeclared egress, excessive
permission, path or symlink escape, downloads, unpinned dependencies and
declared-versus-observed capability drift. It emits the same findings and evidence IDs in
closed JSON and SARIF. Every detector has a malicious fixture and a nearby clean control.
An unknown or unexecuted detector is `INCOMPLETE`.

Every lane reports `PASS`, `FAIL`, `INCOMPLETE` or `N/A`. `PASS` requires that the lane
ran, read a non-empty input it can name, and found no blocking finding. Zero inputs read on
a stack the manifest declares is `INCOMPLETE`, never `PASS`. `N/A` is proved by policy and
is never inferred from absence. `UNKNOWN` normalises to `INCOMPLETE` and blocks.

Every release publishes a wheel, its attestation and a CycloneDX or SPDX SBOM that all name
the same wheel SHA-256 digest. Consumer verification checks digest equality rather than
filename. A versioned tamper fixture changes one artifact byte and must produce a non-green
result. Missing attestation, SBOM, digest equality, required lane or executable receipt is
`INCOMPLETE` and blocks release.

The six closed event classes remain `blocked`, `allowed`, `bypassed`, `command`, `error`
and `session`. "A hook ran" is never a success claim. Redaction is proved by privacy-safe
negative fixtures, and each metric must become non-green when its underlying control or
receipt is absent.

The ten verbs do not change. There is no `security` verb.

## What this closes

The twelve P4 statements and the twenty-five unassigned contracts named in this wave. Each
must move to PROVEN by something that executes, or the wave does not close. "Today" is the
state measured while writing this spec.

| Requirement | Today | What closes it |
|---|---|---|
| EP-041, EP-261 | NO-EVIDENCE | an `ai-security` skill holding the method, the findings schema and the portable baseline; today `.agents/skills/` has eight and none is it |
| EP-042 | NO-EVIDENCE | a threat model and a stack manifest naming required lanes and, per stack, which engine covers it and which file it read |
| EP-043, EP-262 | NO-EVIDENCE | the nine detector classes, stdlib-first, closed JSON and SARIF; `grep -rn "sarif"` finds nothing today |
| EP-044, EP-264 | INCOMPLETE | a security lens bound to a diff with file:line findings and a fresh challenge; `ai-review/SKILL.md` names the lens and nothing forbids auto-accept |
| EP-045 | INCOMPLETE | CI pins five engines; `just security` pins one. Matched pins both sides, and a check that fails when they differ |
| EP-046, EP-282 | NO-EVIDENCE | SkillSpector and Claude Security recorded as optional cross-checks with an executed run of the full baseline with neither present |
| EP-047, EP-280 | NO-EVIDENCE | a CycloneDX or SPDX SBOM produced at release and bound to the wheel SHA-256, plus a consumer verification command |
| EP-048 | INCOMPLETE | `redact = "none"` removed, `command` no longer leaving in plaintext, and `host.id`/`vcs.repository.id` treated as pseudonyms with a stated retention |
| EP-049, EP-052 | NO-EVIDENCE | a release run where `gh attestation verify dist/*` and a CycloneDX validation both pass against one digest |
| EP-050, EP-265 | INCOMPLETE | a lane runner where a missing engine, missing rules, crash, timeout or zero inputs each produce `INCOMPLETE` with its own fixture |
| EP-051 | NO-EVIDENCE | a versioned tamper fixture that flips one byte of scanner, SBOM or wheel and must go non-green |
| EP-258 | PROVEN | `just check`, the mutation floor, the adversarial suite, anti-theatre, typecheck and CI Result all run today; this wave must not weaken them |
| EP-259 | INCOMPLETE | each new detector's malicious fixture red before the detector exists, recorded as a BDD example in this spec's plan |
| EP-260 | NO-EVIDENCE | a rubric per principle with file:line findings and an evidence ID, rather than a box the author ticks |
| EP-263 | INCOMPLETE | today one `trivy fs` line covers vuln, license and misconfig for every repository; per-stack lanes with a named manifest, and containers only where an image exists |
| EP-266..EP-269 | PROVEN | markdown with parseable metadata, `type: adr`, `--adr` refused and `--madr` the only option, and `authority_role`, `justification`, `evidence`, `expires` all required; this wave must not regress them |
| EP-270 | INCOMPLETE | `report issue` returns "planned for P2 and is not implemented"; a local gitignored draft is the first thing that closes it |
| EP-271, EP-272 | NO-EVIDENCE | a closed payload schema, two independent scans, an exact-bytes preview and its SHA-256, with a human confirming each submit |
| EP-273 | NO-EVIDENCE | autonomous submit only under versioned organisational policy naming incident type and destination; no auto-submit in the regulated profile |
| EP-274 | NO-EVIDENCE | negative fixtures proving each named class — logs, diff, source, specs, chain, env, paths, host, user, email, IP, remotes, customer data — cannot reach a payload |
| EP-275 | NO-EVIDENCE | a routing rule that sends a security finding to private disclosure instead of a public issue, with a fixture |
| EP-276, EP-279 | PROVEN | the six classes are closed in `_emit.py`, which records that there is deliberately no "a hook ran"; `_otlp.py` redacts; keep both |
| EP-277 | NO-EVIDENCE | `surface_id`, `surface_version`, `adapter_version` and `deny_protocol` are in neither keep-list in `_otlp.py`, so they leave as hashes if they arrive at all; the field names are spec 011's, the export path is this one's |
| EP-278 | INCOMPLETE | `probe()` already counts rejected records inside a 2xx; p95 guard latency, denial-proof age and chain-anchor gaps are unmeasured |
| EP-281 | NO-EVIDENCE | three separate receipts — attestation, scan, eval — so no one of them can be read as the others |

### Two requirements are sharpened, not adopted as written

Recorded here because a requirement that cannot fail is not a requirement.

**EP-044 — "provider-neutral" semantic review.** The word has no check behind it: no
command can observe neutrality, and every implementation would pass. What is testable is
the output: file:line evidence, a stated challenge, and no path by which the review's own
verdict marks a finding accepted. The intent is kept and the adjective is dropped, because
this repository does not ship words a test cannot reach.

**EP-048 — "pseudonyms and sensitive arguments".** The scope was undefined, so this spec
defines it at three named places rather than as a principle: `redact = "none"`, the two
plaintext tokens of `command`, and the `host.id`/`vcs.repository.id` resource attributes.
Anything else claimed under EP-048 needs its own measurement before it is work.

## Non-goals

- No new verb. `security`, `verify` and `dast` would each be a prompt wearing a command,
  and the ten verbs are frozen (EP-227, EP-228).
- No DAST in this spec. No ZAP image, no stored URL, no scan of a discovered host. It is
  its own spec with its own consent and authorisation contract.
- No second SCA engine. OSV-Scanner, Syft and Grype stay out until a reproducible false
  negative Trivy cannot cover.
- No vendor dependency. SonarCloud and Snyk stay conditional cross-checks and never gate.
- Nothing from P1 (surface adapters), P2, P3 or P5. `surface_id` and friends are spec 011's
  to produce; this spec only stops the exporter from destroying them.
- No claim of compliance, certification or security from a score, a scanner or a model
  (EP-320). This spec states what it will prove and by which command.

## Engineering criteria

- **KISS** — three engines and one native layer, not a scanner per property.
- **YAGNI** — a detector lands when its malicious fixture exists, not before; a second
  engine lands when a reproducible gap exists, not before.
- **DRY** — one findings schema, one state vocabulary, one digest, one receipt shape.
- **SOLID** — the engine scans, the lane runner aggregates, the skill judges, the executor
  binds a decision to an operation. None of the four does another's job.
- **TDD** — every detector's malicious fixture and its clean control are red before the
  detector exists.
- **Clean Code** — `PASS`, `FAIL`, `INCOMPLETE` and `N/A` are the whole vocabulary, and
  absence is never `PASS`.
- **Clean Architecture** — policy stays data in `policy/`, the scanner stays code in `src/`,
  and the hooks keep importing nothing but the standard library.
- **Delete before you abstract** — `redact = "none"` goes; a mode that turns a control off
  is not a configuration option.

## Risks requiring resolution, not acceptance

- **An engine whose bytes nobody checked.** gitleaks and Trivy arrive over `curl` with no
  checksum today. Resolution: verify checksum, signature or OCI digest before execution,
  and a fixture that alters one byte and must refuse to run.
- **A scanner that reads nothing and reports green.** An exit code of 0 is also what a
  scanner returns when it found no files. Resolution: the receipt names every manifest and
  file the lane read, and zero inputs on a declared stack is `INCOMPLETE`.
- **A digest that is only a filename.** Comparing `dist/*.whl` to `dist/*.whl` proves
  nothing. Resolution: a stdlib SHA-256 comparator over the bytes of the wheel, the
  attestation subject and the SBOM reference, with the tamper fixture in CI.
- **Redaction that leaks by design.** Two plaintext command tokens and two stable
  pseudonyms leave on every export today. Resolution: negative fixtures carrying a
  secret-shaped argument and a machine identity, asserting neither reaches the payload in
  strict mode, and no configuration path that turns redaction off.
- **An executor that fails open.** `preflight` currently refuses on every path, which is
  safe because it never allows. The first executor is the moment that can change.
  Resolution: `INCOMPLETE` stays the default return, a permitting answer is reachable only
  for an action kind with an executed denial fixture, and the guard/telemetry split makes a
  fail-open executor impossible to write without renaming it.
- **A detector layer that cries wolf.** `policy/iocs.yml` is precise because a test fires
  the whole catalogue at ordinary technical prose and one false positive fails the build.
  Resolution: every new detector joins that test or does not ship.

## Decisions

**D-014-01 — gitleaks, Semgrep, the OSV/pip-audit path and Trivy stay pinned specialist
engines, and none of their parsers, rule engines or vulnerability databases is reimplemented
here.**
**Rationale:** those four already run in the `justfile` and `check.yml`, and a
reimplementation would be a worse copy carrying our bugs and none of their advisory feeds.
The native work goes where no engine has an owner, not where four do.

**D-014-02 — SkillSpector and Claude Security are optional cross-checks whose absence never
blocks, never lowers a state and never reports a failure.**
**Rationale:** EP-046 and EP-282 both say it and the same rule already governs Snyk, which
is skipped with a warning and an explicit evidence field rather than a red job. A baseline
that needs a vendor to run is a vendor's baseline.

**D-014-03 — the native scanner scans our own skills and policy files, and nothing an
existing engine already owns.**
**Rationale:** this wheel distributes skill files. No pinned engine has an opinion about
one, and that is the only gap that justifies writing a scanner at all.

**D-014-04 — every lane reports `PASS`, `FAIL`, `INCOMPLETE` or `N/A`, and absence is never
`PASS`.**
**Rationale:** the failure this product exists to cure is a green nobody earned. A lane that
cannot say "I did not run" will eventually say "PASS" instead.

**D-014-05 — a scanner binary is verified before it is executed, or the lane is `INCOMPLETE`
and the binary is not run.**
**Rationale:** measured in `check.yml`: three tarballs, one checksum. Two of the three tools
that guard our supply chain currently arrive outside it.

**D-014-06 — Trivy produces the SBOM and a stdlib comparator proves digest equality.**
**Rationale:** Trivy is already installed and already generates CycloneDX and SPDX. Spec 010
asks for the standard and the equality, not a brand, and equality is twenty lines of
`hashlib`, not a fourth engine. Syft and Grype are declined on that basis.

**D-014-07 — the capability executor lands in this wave, binding one action kind at a time,
and `ai-eng doctor` check 23 goes quiet only by becoming false.**
**Rationale:** fifteen capabilities declare six governed fields each and none stops
anything. Deleting the check would remove the only thing telling a reader that. Either the
declaration becomes enforcement or the sentence stays.

**D-014-08 — `redact = "none"` is deleted with no shim, and `command` stops leaving in
plaintext.**
**Rationale:** a configuration value that disables a privacy control is a control that can
be turned off by whoever runs the exporter, and `_otlp.py` currently overwrites the hashed
value with two plaintext tokens after the redaction pass has already run. Rule 4 applies:
hard delete, say it in the changelog.

**D-014-09 — every attack in the adversarial suite gets its own clean control.**
**Rationale:** thirteen attacks share one `negative_control`, so a guard that started firing
on ordinary input would only be caught if it happened to fire on the one control's fixtures.
EP-286 asks for a control per attack and the existing receipt split already proves the split
matters.

**D-014-10 — no `security` verb; the runtime is recipes and the judgement is a skill.**
**Rationale:** EP-228 and the ten-verb contract. `just security` already exists, works and
is inside `just check`. An eleventh verb would cost a doctrine change to run the command a
recipe runs.

**D-014-11 — DAST is refused in this spec and deferred to its own.**
**Rationale:** the security-toolchain research makes a good case for on-demand ZAP inside
`ai-security`, and EP-041..EP-052 do not mention DAST at all. Adding it here would mean
scanning a live host under a spec whose approval nobody granted for that. It needs its own
consent, authorisation and target contract, which is a spec, not a bullet.

**D-014-12 — this document claims no security property. It states measurements and the
commands that produce them.**
**Rationale:** `CONSTITUTION.md` forbids claiming compliance, security or certification
without direct evidence, and EP-320 repeats it. Everything above is either a file and line
that was read, or a thing that must be proved before this wave closes.

## Accepted risks

None. Every risk above stays open until removed or accepted by an authorised human with
complete evidence and an expiry date.

## Production-ready

Nothing gets a URL until every box is ticked by observed evidence.

- [ ] CI/CD — build, lint, test and security analysis on every push; deploy from the default branch
- [ ] Logs — structured JSON, one line per event, with level and service, to stdout
- [ ] Traces — only if this is our code and has more than one hop; no hop, no trace
- [ ] Errors — every uncaught exception leaves as a log with severity 17 and marks its span
- [ ] Health and data age — alive, age of the newest datum, and an independent recomputation
- [ ] External check — something outside the service verifies it and says what it could not check
- [ ] Second path — every published number recomputed by an independent route and compared
- [ ] Security — secrets sealed, no credential in a plain variable, SAST and dependency audit in CI
