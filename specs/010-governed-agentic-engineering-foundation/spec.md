---
id: "010"
slug: governed-agentic-engineering-foundation
status: shipped
date: 2026-08-13
ref: ""
supersedes: "004"
---

# Governed agentic engineering foundation

## Context and problem

The current product solves a narrow problem honestly: it helps one person use an agent
across many repositories without silent harm or a false green result. Guards fail closed,
telemetry does not decide, and a surface is not proven until a denial has executed there.
Those foundations stay.

The product must now govern the whole engineering journey for a person in an editor and
for bounded autonomous orchestrators: from intended outcome, through decision and change,
to review, evidence and shipping. Today it has no native Solution Intent, no complete
capability boundary, no stable machine meaning for every outcome, and no proven contract
for coordinated writers or safe autonomous reporting.

Spec 004 made rejection of a copied corporate document mould read like rejection of any
native Solution Intent. This spec supersedes 004 and admits a minimal, user-owned Intent.
Specs 001 and 006 remain preserved historical records; they are not wholesale superseded.
P0 will create later MADRs that supersede only the individual mission, CLI or document
decisions that change. The same rule applies to ADR 0004: preserve the record and supersede
only its changed decision. History is never rewritten to make the new design look old.

The evolution proposal informed this contract, but its HTML is neither policy nor proof.
Its duplicate identifiers confer no identity or precedence. Once explicitly approved,
this specification, the schemas it requires and the checks that execute them are authoritative.

For a non-technical reader, the intended result is simple. Before work, the framework says
what it may read, write, execute, send and decide. During work, it reports where it is.
When it stops, it says what happened, what proves it and what is permitted next. An agent
may investigate and propose. It may not convert missing evidence into success, accept its
own risk, publish private material or grant itself authority.

## Options considered

1. **Add isolated skills and flags as requests arrive.** This is locally small, but loses
   the trace from intent to evidence and lets autonomy arrive without one authority model.
2. **Restore the legacy control plane.** This recovers breadth quickly, but also restores
   duplicated files, overlapping prompts and claims that were not executable. A council,
   ownership database and takeover timer still have no demonstrated consumer.
3. **Extend the v1 backbone in six ordered waves.** Keep deterministic facts in code,
   bounded judgement in skills and user-owned records in the repository. Freeze the whole
   P0-P5 destination now, then specify and prove each implementation wave. This delays
   specialist features but preserves the product's honesty. **Chosen.**

## Decision

Choose option 3. `ai-engineering` becomes an open framework for governed agentic
engineering for companies, including regulated ones, startups and individual developers.
It supports human-led and bounded autonomous work from Solution Intent through discovery,
specification, decisions, plans, implementation, review, verification, validation, audit
and shipping.

The full P0-P5 target in this specification is normative. Later specifications and plans
decide **how and in which reviewed increments** each requirement lands; they may not decide
whether a requirement lands, weaken it, or silently drop it. Changing the target requires
a superseding specification. Roadmap labels are not commands or evidence.

Commands decide deterministic facts. Models investigate, propose and review. A human or
an already approved versioned policy supplies authority. `FAIL`, `INCOMPLETE` and missing
authority block. Prose, metadata and reviewer approval cannot override a blocking result.

## Normative foundation

### Identity and native Solution Intent

The Constitution retains its brief hard limits while P0 updates the narrower mission in a
reviewed change. A four-line SOUL may state pragmatism, candour, collaboration and learning
in one home; it is values, never a second policy layer.

Solution Intent is a short, user-owned record in the user's repository, not a copied
corporate mould or framework-owned content. It separates fixed constraints, variables,
facts true now and intended outcomes. Typed links point to specs and decisions instead of
copying their prose. P0 fixes its one home, closed versioned schema, relation checks and
invalid fixtures. Missing, unknown, stale or broken relations fail closed as `INCOMPLETE`.

### Structured MADR v1

`policy/madr-v1.schema.json` is the sole canonical JSON Schema 2020-12 contract for MADR
frontmatter. MADRs live only in `docs/adr/`, retain `type: adr`, and are called MADRs in the
UI. `--adr` is hard-renamed to `--madr` with no alias.

The schema has `additionalProperties: false` and these exact fields and types:

| Field | Type and constraint |
|---|---|
| `schema` | string, constant `urn:ai-engineering:madr:1` |
| `schema_version` | string, constant `1` |
| `type` | string, constant `adr` |
| `id` | string matching `^[0-9]{4}$` |
| `title` | non-empty string |
| `date` | string with JSON Schema `date` format |
| `spec` | string matching `^[0-9]{3}$` and resolving to one spec |
| `status` | string enum `proposed`, `accepted`, `rejected`, `superseded` |
| `supersedes` | string, either empty or a resolving four-digit MADR ID |
| `authority_role` | non-empty string, conditionally required below |
| `approval_ref` | non-empty string, conditionally required below |
| `approved_at` | RFC 3339 UTC date-time string, conditionally required below |

The first nine fields through `supersedes` are always required. A `proposed` MADR must not
contain the three approval fields and cannot authorize work. `accepted`, `rejected` and
`superseded` require all three approval fields. `authority_role` names the accountable
human role or the role named by an already approved policy; an agent or reviewer role is
not authority.

Creation enters `proposed`. The only transitions are `proposed -> accepted`,
`proposed -> rejected`, and `accepted -> superseded`. Rejected and superseded records are
terminal. A replacement names the preserved predecessor in `supersedes`; self-links,
cycles, orphan links, duplicate IDs and edits that simulate a transition without reviewed
history fail closed.

Versioned invalid fixtures cover every missing required field, every wrong type or enum,
unknown fields, malformed IDs and dates, approval fields on `proposed`, missing approval
fields on terminal states, invalid transitions, duplicate IDs, self-links, cycles, orphan
specs and orphan supersession. Each fixture must make the local gate non-zero before the
valid fixture is implemented.

### One `ai-spec` flow and authority

The single agentic-first `ai-spec` flow reads repository evidence and current primary
sources before asking a person. It states the problem, presents at least two real options,
recommends one, challenges the recommendation once, records assumptions and unresolved
risks, and gives observable BDD examples. When a person is available, it asks only
questions whose answers change the decision; the answer overrides inference.

Without a person, it may choose only a reversible, least-scope option within existing
permissions. An irreversible, high-risk, contradictory or cross-cutting decision without
an accountable human decision or exact preapproved policy is `INCOMPLETE`. A fresh
reviewer may find defects or recommend escalation but never grants authority, accepts
risk, approves its own work or changes that outcome.

### Fifteen-skill target and routing boundaries

This is the exact target catalogue. Each row is normative and each trigger, artifact and
refusal is represented in versioned must-trigger, must-not-trigger, overlap and abstention
fixtures plus a behaviour corpus.

| Skill | Trigger | Output | Negative boundary |
|---|---|---|---|
| `ai-explore` | explain this repository or trace a flow | file:line map or tour | no outside research or edits |
| `ai-research` | evidence outside the repository is required | cited claims and marked unknowns | no uncited certainty or implementation |
| `ai-spec` | decide what should be built | approved decision record with options and BDD | no plan or code before approval |
| `ai-plan` | turn an approved spec into tasks | ordered file/check/rollback plan | no unapproved scope or implementation |
| `ai-build` | execute an approved plan | scoped implementation and task evidence | no new scope, parallel writer or invented green |
| `ai-debug` | broken behaviour needs a cause | file:line cause, red reproduction, fix | no speculative edits before reproduction |
| `ai-test` | test strategy or missing coverage is the work | risk-based test design and tests | no claim that tests prove review or production |
| `ai-design` | interface structure, states or accessibility are at issue | brief, system, states and rendered evidence | no decorative redesign or untested accessibility claim |
| `ai-animation` | interaction or motion behaviour is at issue | motion spec and reduced-motion evidence | no gratuitous motion or layout-expensive default |
| `ai-security` | threat, permissions, data flow or scanner coverage is at issue | threat/findings/evidence pack | no compliance claim or self-accepted finding |
| `ai-review` | judge a diff against its claim | prioritized file:line findings | no edits, gate claims or authority grant |
| `ai-verify` | execute and record declared checks | fresh check/evidence result | no invented, stale or metadata-only green |
| `ai-note` | preserve a costly non-obvious finding | commit-stamped markdown note | no routine summary or private data |
| `ai-report` | prepare a governed digest or incident report | local digest/draft or authorized receipt | no broad payload, public security report or silent network |
| `ai-ship` | land already reviewed work | atomic commits, changelog, PR and observed gates | no bypass, force push or unreviewed scope |

A catalogue entry cannot be removed or absorbed by an eval. That requires a superseding
specification, changelog, hard deletion and negative routing proof. Collision, threshold
miss, missing or unexecuted corpus is `INCOMPLETE`. Cross-model replay is advisory until a
later superseding specification proves a stable blocking threshold.

### Closed capability manifest

Every skill, and every mode whose permissions differ, has one closed versioned capability
manifest. Unknown keys are invalid. The required keys and types are:

| Key | Closed meaning |
|---|---|
| `read_roots` | array of normalized repository-relative roots; empty means no reads |
| `write_roots` | array of normalized repository-relative roots; empty means read-only |
| `exec_allowlist` | array of exact executable plus argument-pattern IDs; empty means no execution |
| `network` | array of exact protocol/host/purpose entries; empty means no network |
| `secrets` | array of exact secret capability IDs; empty means no secret access |
| `human_gate` | enum `never`, `before_write`, `before_exec`, `before_network`, `before_publish` |

Roots may not escape the repository; executables, destinations, secrets and modes may not
be inferred from prose or wildcards. Unsupported, undeclared or unrecognized capability is
`INCOMPLETE` and fails closed before the action. Manifest metadata alone is never proof:
positive and negative execution fixtures must show that allowed work succeeds and work
outside every declared boundary is denied from the installed artifact.

### Outcomes, checks and evidence

Exactly one canonical terminal outcome is returned. `RUNNING` is a phase, not an outcome.

| Outcome | Semantic partition | Required next action |
|---|---|---|
| `READY` | Preconditions are freshly proven; no requested mutation ran | begin only the stated permitted operation |
| `PASS` | The requested operation and all applicable checks completed | continue to the next governed stage |
| `WARN` | Work completed with a non-blocking bounded condition | inspect the warning, then continue or remediate |
| `FAIL` | An executed check conclusively found a violation | remediate the violation and rerun |
| `INCOMPLETE` | The framework cannot decide or prove the claim | obtain/repair authority, capability or evidence and rerun |
| `CANCELLED` | Explicit cancellation stopped work before a decision | confirm intent, then restart as a new operation |
| `WOULD_CHANGE` | A complete dry run derived exact changes and made none | review the proposed changes, then run without dry-run |

`READY`, `PASS`, `WARN` and `WOULD_CHANGE` use exit 0; `FAIL` and `INCOMPLETE` exit 1;
invalid CLI use exits 2; `CANCELLED` exits 130. A dry run unable to decide is
`INCOMPLETE`, not `WOULD_CHANGE`. Renderers share the same semantic result and exit.

The check/evidence schema is closed and versioned. Each check record requires `id`
(string), `applicability` (`applicable` or `not_applicable`), `command` (exact string),
`tool_version` (non-empty string), `input_digest` and `artifact_digest`
(`sha256:<64 lowercase hex>`), `started_at` and `finished_at` (RFC 3339 UTC), and `outcome`
(`PASS`, `WARN` or `FAIL`). A not-applicable record additionally requires a deterministic
`reason` and may not be used to cover an applicable lane. Freshness is measured against a
versioned per-check maximum age, never a model judgement.

No green claim is valid unless every applicable check was freshly executed against the
named input and artifact. Missing, stale, malformed or digest-mismatched evidence is
`INCOMPLETE`. An observed conclusive violation is `FAIL`. Human and external checks also
name a stable test ID, accountable owner role, scripted protocol/version, versioned
fixture/environment, observation date, privacy-safe receipt digest and, for an external
check, its independent path and limits. CI may validate receipt schema and age but cannot
claim it performed the human or independent journey.

### Outcome-first CLI and JSON v1

The ten deterministic verbs become `init`, `doctor`, `update`, `spec`, `decide`, `accept`,
`audit`, `report`, `exception` and `uninstall`. `plan` is hard-renamed to `exception` and
`digest` to `report digest`, without aliases. Before mutation, human output states reads,
writes and network use. Long operations show counted real stages. The end names outcome,
evidence, remaining work and next permitted action. A cure appears only when blocked and
never offers bypass.

`--json` emits exactly one object to stdout without prompts, ANSI or surrounding text.
Every top-level field is required: `schema_version`, `command`, `operation_id`,
`started_at`, `finished_at`, `outcome`, `summary`, `changes`, `checks`, `remaining`,
`next_actions`, `error`. Arrays are empty, never null. `error` is null for exit-0 outcomes;
otherwise it requires `code`, `message`, `retryable` and nullable `cure`. Timestamps are
RFC 3339 UTC. `operation_id` is a fresh opaque UUID without user, host or path. Human,
plain and JSON renderers have parity. JSONL waits for a demonstrated streaming consumer.

## Normative wave contracts

### P0 — documentary, CLI and supply-chain foundation

P0 lands the identity, Intent and MADR contracts, the single `ai-spec` flow, capability
manifest, outcome/check/evidence/JSON schemas, hard renames and `report digest`, with
invalid fixtures red before valid implementations. It freezes the P1-P5 contracts below.

P0 hard-renames `design_gate` to `change_scope_guard`, with no alias, because the guard
enforces approved scope and plan presence rather than judging design.

P0 retains the current trusted-publishing, provenance, dependency-audit, installed-wheel
test and security-analysis lanes. Every new dependency is exactly pinned in its governing
lock or action reference. A removed, skipped or missing required lane is `INCOMPLETE` and
blocks release; a new lane supplements rather than silently replaces existing proof.

### P1 — surface adapter contract

The eight surface IDs remain `claude-code`, `opencode`, `codex-cli`, `cursor`,
`copilot-cli`, `vscode-copilot`, `pi` and `zed`. Contexts do not create new IDs or inherit
proof. `pi` and `zed` remain instruction-only T3 until a stable native hook exists.

Each versioned P1 adapter must:

- detect only a native signal it did not write or cause; inability to detect is explicit,
  never self-fabricated presence;
- preserve every foreign config entry and byte-significant value; unreadable or
  unmergeable foreign config causes no write and returns `INCOMPLETE`;
- declare explicit bidirectional translations for canonical payload fields, lifecycle
  event, exit meaning and allow/deny/error reply, with unknown values failing closed;
- expose a heartbeat that distinguishes installed, loaded and recently observed, and a
  trust ceremony where the surface requires trust;
- prove negative behaviour from a wheel-installed artifact, including omitted adapter,
  malformed payload, guard crash and denial; and
- report **discovery**, **invocation** and **enforcement** as separate states and receipts.

Visibility never proves invocation; invocation never proves denial. A T3 surface reports
enforcement not applicable and cannot earn denial proof.

OpenCode uses minimal global `/ai-*` routers that point to the canonical installed skills;
routers contain no copied body and have a receipt, content hash, doctor check and exact
uninstall. Codex restores wheel-owned links under `$HOME/.agents/skills`, proves both
`/skills` discovery and `$ai-*` invocation, and supplies the canonical
`agents/openai.yaml`; none of those artifacts alone proves enforcement.

### P2 — craft, UX and governed reporting

P2 supplies `ai-build`, `ai-test`, `ai-design`, `ai-animation`, `ai-security`, `ai-verify`
and `ai-report` bodies, corpora and functional accessibility evidence. `report digest`
stays local. `report issue draft` creates an ignored local draft from a closed allow-list
without network. `report issue submit <draft>` is the only issue-report network action; it
shows exact bytes and digest, rescans them and requires a human gate unless the following
preauthorization applies. Security findings use private disclosure only.

Autonomous report preauthorization exists only in a committed closed
`.ai/config.toml` section. Each entry has exactly: `id` (non-empty string), `version`
(positive integer), `accountable_role` (non-empty string), `incident_type` (one exact
closed-schema incident ID), `private_destination` (one exact private connector or HTTPS
origin and path, without wildcard), `effective_at` and `expires_at` (RFC 3339 UTC), and
`revoked_at` (RFC 3339 UTC or the empty string). The entry must be effective, unexpired,
unrevoked and match both incident and destination byte-for-byte. Malformed, stale, broad,
unknown or mismatched authorization blocks before network. Regulated profiles never
auto-submit even with a valid entry.

Payloads never include logs, diffs, source, specs, chain, environment, absolute paths,
host, user, email, IP, remotes, prompts, secrets, personal data or customer data. Unknown
fields and scan uncertainty block. `report issue` without `draft` or `submit` refuses.

P1 and P2 planning may begin only after this specification is approved. Their
implementation may begin only after the exact referenced P0 schema and contract versions
have landed on the base branch; prose drafts and unversioned metadata do not satisfy the
dependency.

#### Functional accessibility

P2 targets WCAG 2.2 AAA and sets AA as the release floor. Critical journeys prove native
semantics and accessible name, role, value and state; keyboard operation, visible focus and
dialog focus return; touch and pointer targets, a non-drag alternative and both permitted
orientations; 320 px reflow, 400% zoom, 200% text and forced colors; identified errors,
authentication without cognitive traps, paste and password-manager support, and status
announcements; reduced motion, flash limits and media alternatives. Every unmet applicable
AAA criterion records reason, accountable owner, expiry and executed AA-floor evidence.
Automated axe or contrast output is useful evidence but is never sufficient by itself.

#### Image generation and imported images

Image generation is opt-in. Before upload, screenshots and sources are classified for
personal data, confidential IP and licensing; provider residence and retention require
documented approval and user consent. OCR is untrusted input. Imports strip EXIF, verify
declared versus detected type, scan for malware and sanitize SVG before use. Each generated
asset has a card naming provider, model/version, prompt digest, source references and
license. Generation or scanning never proves accessibility, trademark clearance or
copyright ownership.

#### Terminal accessibility

Terminal output preserves stable reading order, carries meaning in text plus marks rather
than color, honors `NO_COLOR` and `TERM=dumb`, and never rewrites prior lines on a non-TTY.
Prompts are keyboard-operable, cancellation is explicit and leaves a safe state, and
non-interactive mode fails `INCOMPLETE` when required consent is absent rather than choosing
a default. Plain, rich and JSON modes retain outcome parity.

### P3 — coordination

Before P3 is proven, exactly one writer may edit **the entire repository**, regardless of
worktree, branch, path or task. Other agents are read-only researchers or reviewers.

P3 normatively requires fetch-before-claim; an opaque, non-personal work-item ID; one
remote branch and writer; a compare-and-swap claim against the exact fetched base SHA; a
draft PR created with the claim; enforced `claimed_paths` on every write and commit; and
CI on `merge_group` for the combined result. No background rebase, force push or silent
takeover is permitted.

The coordination DAG is deterministic: imports, lockfiles, migrations and schemas create
explicit dependency edges; exclusive resources serialize; a stable topological order is
recorded; and any cycle is `INCOMPLETE`. Before every checkpoint, the writer scans staged
content for secrets, personal data and machine paths, proves it remains within
`claimed_paths`, and executes the checks affected by the actual diff. A checkpoint missing
any of those receipts cannot be claimed or published.

Versioned adversarial fixtures cover a two-writer claim race with exactly one winner, a
stale base SHA, an out-of-scope write, two disjoint claims integrating, and overlapping
claims remaining blocked and visible at the merge gate. Until all pass from the real
remote protocol, P3 is `INCOMPLETE` and the one-writer rule remains.

### P4 — security and release evidence

P4 adds portable threat/data models, the native skill and policy scanner,
provider-neutral semantic review, pinned stack-appropriate scanner lanes, redacted
telemetry review and consumer verification. Optional external products may cross-check;
their absence cannot disable the portable baseline.

The native scanner has deterministic detector classes for hidden instructions, invisible
Unicode, executable content, undeclared egress, excessive permission, path or symlink
escape, downloads, unpinned dependencies and declared-versus-observed capability drift.
It emits the same findings and evidence IDs in closed JSON and SARIF. Every detector has a
malicious fixture and a nearby clean control; an unknown or unexecuted detector is
`INCOMPLETE`.

Every release publishes a wheel, its attestation and a CycloneDX or SPDX SBOM that all
name the same wheel SHA-256 digest. Consumer verification checks equality rather than
filename. A versioned tamper fixture changes one artifact byte and must produce a non-green
result. Missing attestation, SBOM, digest equality, required lane or executable receipt is
`INCOMPLETE` and blocks release.

### Cross-wave observability

The closed event classes remain `blocked`, `allowed`, `bypassed`, `command`, `error` and
`session`. Applicable records add `surface_id`, `surface_version`, `adapter_version` and
`deny_protocol`. Release evidence measures guard p95 latency, denial-proof age, OTLP record
rejections and chain-anchor gaps; an HTTP success with rejected OTLP records is not delivery.
“A hook ran” is never a success claim. Privacy-safe negative fixtures prove redaction and
that each metric becomes non-green when its underlying control or receipt is absent.

### P5 — external pilot

P5 pilots the same `ai-spec` flow with and without human answers; compares sequential,
self-challenged and parallel work; measures defects, cost, wait, conflicts, escalations,
privacy and false greens; and exercises an external version upgrade without silent Intent
or MADR drift. A council, path lease or larger control plane may be proposed only by a
superseding specification if measured evidence shows Git and CI are insufficient.

P5 completes only when parallel work improves elapsed time without worsening defects,
cost, privacy or conflicts and every claimed gate has an executed negative control.

## Normative disposition of all 54 legacy capabilities

This inventory is closed. “Absorb” means only the named target owns the useful behaviour;
“later” requires measured need and a superseding specification; “out” is not core scope.

| Disposition | Capabilities |
|---|---|
| Keep (6) | `ai-debug`, `ai-explore`, `ai-note`, `ai-plan`, `ai-research`, `ai-review` |
| Restore in the 15-skill target (7) | `ai-animation`, `ai-build`, `ai-design`, `ai-engineering-issue` as `ai-report`, `ai-security`, `ai-test`, `ai-verify` |
| Absorb into target skill or deterministic code (19) | `ai-advise`, `ai-brainstorm`, `ai-commit`, `ai-constitution`, `ai-docs`, `ai-explain`, `ai-governance`, `ai-ide-audit`, `ai-learn`, `ai-mcp-audit`, `ai-onboard`, `ai-pipeline`, `ai-pr`, `ai-reliability-eval`, `ai-resolve-conflicts`, `ai-simplify`, `ai-spec-draft`, `ai-start`, `ai-visual` |
| Later only with evidence (3) | `ai-autopilot`, `ai-postmortem`, `ai-schema` |
| Outside core (19) | `ai-board`, `ai-branch-cleanup`, `ai-code`, `ai-fundraising`, `ai-issue`, `ai-marketing`, `ai-media`, `ai-prompt-tune`, `ai-prose`, `ai-scaffold`, `ai-session-watch`, `ai-session-watch-sweep`, `ai-simplify-sweep`, `ai-skill-improve`, `ai-slides`, `ai-sprint`, `ai-standup`, `ai-support`, `ai-video-editing` |

The counts sum to 54. No omitted legacy capability is implicitly retained.

## Non-goals

- No product code, plan, Constitution edit, old-record status change or MADR is created by
  this draft.
- No copied document mould, mirror skill tree, second policy home, coordination database,
  public commit stream, background rebase, force push or automatic task takeover returns.
- No authority-envelope subsystem, permanent council, model vote or agent per review lens
  is added without a demonstrated consumer and a superseding specification.
- No vendor, score, metadata file or model statement becomes a claim of compliance,
  accessibility, certification, enforcement or total security.
- No surface becomes proven because a file exists, documentation says it works, or another
  context sharing a skill root was tested.

## Engineering criteria

**KISS** — extend one v1 backbone; do not create a second framework.  
**YAGNI** — councils and coordination services wait for measured need.  
**DRY** — one home for each schema, datum, surface and proof; links replace copied prose.  
**SOLID** — adapters translate, guards decide, telemetry observes and skills guide.  
**TDD** — deterministic behaviour starts with the real fixture that turns its check red.  
**Clean Code** — names describe behaviour, errors retain cause and cure, and hard renames delete.  
**Clean Architecture** — hooks remain stdlib-only, presentation a leaf and policy data.

## Risks requiring resolution, not acceptance

- This broad target can exceed the repository ceiling. Each plan must measure its
  increment; any ceiling move requires its own justified commit, never a weakened gate.
- Hard renames break callers. Changelog, help, install tests and errors must state the
  break; compatibility aliases remain forbidden.
- Parsers and adapters can create false green. Unknown input, stale relations, unreadable
  foreign config and unproven translation must stay `INCOMPLETE`.
- Human and external evidence can become ceremonial. Promotion requires a checkable
  protocol, attributable role, freshness and privacy-safe receipt.
- CLI renderers can drift. One semantic result and exit mapping must feed parity tests for
  every canonical outcome.

### Immutable risk acceptance records

The previous `ai-eng accept` writer appended YAML by replacing an existing `spec.md`.
That cannot preserve an unrelated writer's bytes under every supported system: Linux
rename provides replace, exchange and no-replace operations but no replacement conditional
on an expected destination identity; Apple's documented exclusive rename refuses an
existing destination rather than comparing it; and Windows `ReplaceFileW` replaces the
named destination without an expected-content predicate. These are primary platform
contracts: [Linux `renameat2`](https://man7.org/linux/man-pages/man2/renameat2.2.html),
[Apple exclusive rename](https://developer.apple.com/documentation/foundation/urlresourcekey/volumesupportsexclusiverenamingkey)
and [Windows `ReplaceFileW`](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilew).
An advisory lock would coordinate this command with itself, not with an editor or another
writer. A final verify-then-replace window would therefore remain a false-green and
foreign-byte-loss path.

Three real options were considered:

1. **Keep embedded YAML and add a lock plus final revalidation.** This preserves the old
   display and costs no new artifact, but an uncooperative writer can still change the
   pathname after revalidation; it also keeps mutating a user's spec after its initial
   write. Rejected.
2. **Put acceptance in a Git-ref CAS or a coordination service.** This can provide an
   expected-value transaction, but makes an offline local decision depend on repository
   state or a new networked control plane, and does not protect the working-tree evidence
   that the person inspected. Deferred unless measured need justifies a superseding spec.
3. **Publish one uniquely named immutable record without replacement.** This adds one
   small artifact per decision, but preserves the spec, the prior history and any
   colliding writer's bytes on Linux, macOS and Windows. **Chosen.**

The strongest challenge is that immutable naming does not make a user-controlled
filesystem tamper-proof. It proves only what this command published and prevents it from
overwriting a conflicting pathname; Git review remains the durable history, and current
spec and evidence digests must still match on every read. That limitation does not restore
option 1's unavoidable overwrite race or justify option 2's new control plane, so option 3
stands.

**Assumption:** the repository is on a filesystem whose native exclusive-publication
contract the backend can positively identify; otherwise it refuses before final
publication. **Unresolved risks:** before Git records the artifact, an authorized
repository owner can still edit or delete it, and the supported native rename APIs do not
prove survival across sudden power loss. The framework therefore claims an observed
digest-bound snapshot and atomic no-replace visibility, not identity, uninterrupted source
currentness, power-loss durability, tamper-proof storage or independent attestation.

Every new acceptance or renewal lives only at
`specs/NNN-slug/acceptance-r-NNN-NN/record.json`, where both `NNN` values equal the owning
spec ID and the final `NN` is the next unused two-digit ordinal. The acceptance command
never opens `spec.md` for write. It selects the ordinal from one validated snapshot of all
legacy and new records in the target's numeric spec namespace, not only the canonical
target directory. A canonical direct child `NNN-slug` owns `NNN`; for a preserved
noncanonical direct child, concatenate the ASCII digits in its leaf name and take the first
three, refusing it as undecidable when fewer than three exist. Valid IDs occupy their
stated ordinals across every home with that extracted owner; each ID-less legacy block
reserves the lowest remaining ordinal in stable `(home byte spelling, block byte offset)`
order and receives the deterministic in-memory relation ID
`R-<owner>-<two-digit reserved ordinal>`;
the new record takes the lowest ordinal still unused. Historical gaps are permitted and
may be filled. A duplicate ID, ID/owner mismatch, exhausted `99` ceiling or undecidable
snapshot is `INCOMPLETE`, not permission to guess another name.

`policy/risk-acceptance-v1.schema.json` is the sole canonical JSON Schema 2020-12 contract.
Its top level has `additionalProperties: false` and requires exactly these fields:

| Field | Type and constraint |
|---|---|
| `schema` | string, constant `urn:ai-engineering:risk-acceptance:1` |
| `schema_version` | string, constant `1` |
| `id` | string matching `^R-[0-9]{3}-[0-9]{2}$`; the leaf directory is `acceptance-` plus its ASCII lowercase value |
| `spec` | string matching `^[0-9]{3}$` and the owning canonical spec directory |
| `spec_digest` | string matching `^sha256:[0-9a-f]{64}$` for the exact `spec.md` bytes shown before confirmation |
| `finding` | non-empty string of at most 128 UTF-8 bytes |
| `severity` | string enum `low`, `medium`, `high`, `critical` |
| `authority_role` | non-empty accountable human role of at most 128 UTF-8 bytes |
| `accepted` | canonical `YYYY-MM-DD` UTC date derived after authority confirmation |
| `expires` | canonical `YYYY-MM-DD` date, not earlier than `accepted` |
| `renewals` | integer from `0` through `2` |
| `renews` | empty string for an original; otherwise the exact prior record ID |
| `renews_digest` | empty string for an original; otherwise `sha256:<64 lowercase hex>` over the prior canonical record or exact legacy block bytes |
| `justification` | non-empty string of at most 2,000 UTF-8 bytes |
| `evidence` | closed object with only required `path` and `content_digest` fields |
| `follow_up` | string of at most 2,000 UTF-8 bytes; it may be empty |
| `record_digest` | `sha256:<64 lowercase hex>` over the canonical JSON projection of every other top-level field |

`evidence.path` is one normalized repository-relative regular-file path of at most 1,024
UTF-8 bytes, with no empty, dot, parent, absolute, backslash or symlink component.
`evidence.content_digest` matches `^sha256:[0-9a-f]{64}$` and binds the exact non-empty
evidence bytes the human was shown. The evidence file is at most 100,000 bytes. Unknown
fields, invalid UTF-8, control characters, non-canonical JSON or mismatches among the path,
ID, spec and digests are `INCOMPLETE`. Canonical JSON is UTF-8 without BOM, sorted keys,
two-space indentation, no non-finite numbers and one trailing newline. New textual values
may not contain secrets, personal data or machine paths. `record_digest` is recomputed over
that exact encoding after omitting only `record_digest`; it is an internal corruption
check, not an external signature or proof against somebody who can rewrite both value and
checksum. A successor's `renews_digest` hashes the predecessor's complete canonical file,
including its `record_digest`.

`authority_role` is a role, never a person's name. After Unicode NFKC plus case-folding and
tokenization on non-alphanumeric characters, any token equal to `agent`, `assistant`, `ai`,
`bot`, `model`, `reviewer`, `self`, `myself`, `unknown`, `unassigned`, `unspecified`,
`someone`, `somebody`, `tbd` or `todo` is invalid. The exact response `ACCEPT <id> AS
<authority_role>` must be read from the OS controlling terminal after the values and
digests are displayed; `isatty` alone, a flag, environment value or piped standard input
is insufficient. The OS observation proves only that matching bytes arrived through the
controlling-terminal boundary. P0 has no cryptographic, identity-provider or other CLI
proof that a particular human was present or entitled to the asserted role, and no record
or outcome may claim otherwise. Treating this bounded interaction as the P0 human-authority
handoff requires renewed human approval of this exact amended specification and plan; it
cannot be inferred from a model, reviewer or earlier digest approval.

At this base, the exact existing executable secret scanner is Gitleaks 8.30.1, run inside
the unpublished record directory as `gitleaks dir . --redact --no-banner --exit-code 1`.
The command verifies that exact version; exit 1 is a conclusive `FAIL`, exit 0 is clean,
and absence, version drift or any other exit is `INCOMPLETE`. There is no existing
executable personal-data or machine-path scanner. The P0 implementation must therefore add
the deterministic checks `acceptance_pii_v1` and `acceptance_machine_path_v1` before
enabling the new writer; a match is `FAIL`, unsupported input or undecidable
classification is `INCOMPLETE`, and only all three clean results may reach publication.
Versioned fixtures include a secret, email, IP address, phone-like identifier,
personal-name ambiguity, POSIX home path, Windows drive path, UNC path, clean role/reason,
missing Gitleaks and wrong-version Gitleaks. The command records no candidate text,
scanner output or terminal name outside `record.json`.

Every spec, evidence, predecessor, legacy block source, new record and staged record is
opened from a repository-root descriptor or handle one exact component at a time. Every
regular file must be on the repository root's device or volume, have exactly one hard link
(`st_nlink == 1` or the native equivalent), and keep the same stable identity, length and
generation through its bounded read. Below the anchored repository root, no component may
be a symlink, POSIX mount crossing, Windows reparse point or junction, alternate/short-name
alias, reserved alias or differently spelled directory entry. A platform that cannot
observe one of those properties returns `INCOMPLETE`; lexical containment or `resolve()`
alone is never evidence.

Before asking, the command reads an anchored, bounded snapshot, computes the spec and
evidence digests and shows the exact finding, severity, authority role, expiry, justification,
follow-up and digest-bound paths. For a renewal it also shows the predecessor ID, its
canonical bytes or exact fenced-block digest, and the observed repository-wide chain head.
Those values form the challenge. A flag, model, reviewer, placeholder, piped answer or
default cannot supply the required controlling-terminal response. This specification
defines no risk-acceptance preauthorization schema, so P0 has no policy path. Missing or
malformed interaction evidence is `INCOMPLETE` and nothing is published.

Immediately after the exact response, the command obtains the UTC date again, rejects an
expiry now in the past, and reopens the same anchored spec, evidence and predecessor. Any
identity, length or digest change observed by that final bounded read is `INCOMPLETE`; the
command never silently binds the response to different bytes. No supported filesystem can
promise that an unrelated writer will not change a source after that last read and before
the publication syscall. The record therefore accepts the exact displayed digest-bound
snapshot, not a claim that its source paths stayed current through that unobservable
window. Every later unified read recomputes all current bindings; a subsequent change is
`INCOMPLETE` until a new human decision, never an invisible update of this record.

Publication writes canonical JSON into an unpublished sibling directory and re-reads its
anchored file before mutation. The staged file and directory are flushed before the final
rename; a precommit read, flush or capability failure is `INCOMPLETE` and cleans only the
owned staging entry. The platform-native exclusive no-replace rename is the sole commit
point and proves atomic visibility plus refusal to replace the final name. Reported rename
success is a committed `PASS`; there is no fallible postcommit check that can relabel it
`INCOMPLETE`, and later rendering failure cannot make retry overwrite it. A collision or
unsupported primitive is `INCOMPLETE`; the existing destination is never replaced,
removed or reinterpreted as this attempt's success. Power-loss durability remains
outside the claim unless a supported runner executes and retains a named crash/recovery
receipt; ordinary rename success, precommit flushes and prose do not prove it.

Historical accepted-risk YAML blocks remain read-only enforcement history in every direct,
non-symlink `specs/*/spec.md`, including preserved pre-canonical directory names. They are
never rewritten, copied into the new shape or used as a new-write target. The frozen
legacy recognizer treats a fenced YAML block as an acceptance only when `finding` and
`expires` are present. Its only permitted fields are `id`, `finding`, `severity`,
`accepted_by`, `accepted`, `expires`, `renewals`, `justification`, `evidence` and
`follow_up`; any other key is malformed rather than ignored. Except for `renewals`, every
present value is a valid UTF-8 string without control characters. The exact constraints
and frozen defaults are:

- `id` is absent or matches `^R-[0-9]{3}-[0-9]{2}$`; when present, its first numeric group
  equals the canonical or noncanonical owner extraction above. Absence normalizes only in
  memory to the derived ID allocated above. The reader labels each displayed ID with
  provenance `stored legacy`, `derived legacy` or `canonical record`; derived provenance
  is never written back into the historical block.
- `finding` is required, non-empty and at most 256 UTF-8 bytes. `severity` is absent or one
  of `low`, `medium`, `high`, `critical`, with absence normalizing to `medium`.
- `accepted` is absent, empty or one canonical `YYYY-MM-DD` date, with absence normalizing
  to empty. `expires` is required and is one canonical `YYYY-MM-DD` date.
- `renewals` is absent, a non-boolean integer, or a string. Absence and a non-decimal string
  containing no ASCII digit normalize to zero, preserving the shipped `once` behavior. An
  integer or an all-ASCII-digit string is parsed in base ten and must be from zero through
  two; every other string or out-of-range value is malformed.
- `accepted_by` is zero to 256 UTF-8 bytes, default `?`; `justification` is zero to 8,192,
  default empty; and `follow_up` is zero to 4,096, default empty. All are strings.
- `evidence` is a string of at most 2,048 UTF-8 bytes, default empty. A non-empty value is
  one normalized repository-relative path followed by `@sha256:` and 64 lowercase hex
  characters; it is historical evidence syntax, never copied into a new record.

Wrong container, boolean or scalar types are malformed, including for an optional field.
These defaults preserve expiry enforcement but never satisfy new authority, digest or
renewal-write requirements. A legacy block digest is `sha256:` over the exact stored byte
span from the first backtick of its opening three-backtick `yaml` delimiter through the
third backtick of its closing delimiter, excluding following whitespace and prose; it is
computed without rewriting or canonicalizing the block.

One unified reader validates both that history and the new records, normalizes them only
in memory, and scans at most 1,000 spec directories, 99 new records per spec, 1 MiB per
`spec.md`, 64 KiB per `record.json` and 64 MiB total including referenced evidence.
Unreadable paths, symlinks, malformed blocks or JSON, duplicate IDs, ambiguous finding
heads and any exceeded bound are `INCOMPLETE`; none may be skipped to produce green.

The reader evaluates two separate states. **Record and chain integrity** covers canonical
bytes, schema and types, `record_digest` where applicable, path/ID/owner agreement, unique
ordinals and finding heads, renewal counters and relations, and every `renews_digest`. A
malformed record, detected byte/checksum modification, missing predecessor, cycle, gap,
fork or predecessor-digest mismatch is integrity-invalid: the register is `INCOMPLETE`,
the record is not a renewable head and no later record may cure it by copying or
recomputing its contents. **Current-binding freshness** is evaluated only after integrity succeeds. It
reopens the current canonical `spec.md` and referenced evidence and compares their bytes to
`spec_digest` and `evidence.content_digest`. A mismatch makes the acceptance view
`INCOMPLETE` and prevents green, but does not alter the immutable record or its valid place
as the latest renewal-chain head.

An integrity-valid but stale head remains renewable. The renewal prompt shows its complete
old canonical bytes and digest, the stale binding result, and the newly observed canonical
spec and evidence bytes. A new human decision creates a new record with fresh
`spec_digest`, `evidence.content_digest` and `renews_digest`; it never edits the stale head
or treats stale bytes as current. This is the only freshness cure. A schema, self-digest or
chain-integrity failure is not staleness and cannot enter that cure path.

Renewal chains are repository-wide by exact `finding`, preserving the existing behavior
where a later spec can renew a predecessor in an earlier spec. A new renewal keeps that
finding, names the single latest chain head in `renews`, binds its canonical JSON bytes or
exact legacy block bytes in `renews_digest`, and sets `renewals` to exactly one more than
the predecessor. New canonical records carry explicit relations; legacy relations are
reconstructed only when each counter from zero to the unique head identifies one record.
An ID-less legacy head may be named in `renews` by its deterministic derived ID, with
`renews_digest` binding its exact block bytes; neither value is inserted into history.

Every renewal requires an exact `--spec NNN` naming the canonical spec that owns the new
decision and artifact; it may differ from the predecessor's spec. Thus a valid predecessor
under a noncanonical historical directory can be renewed only into that explicitly named
canonical target. Missing, ambiguous or noncanonical target selection is `INCOMPLETE` and
never renames the historical owner. The previous record stays unchanged and the unified
expiry view treats only the unique repository-wide chain head as the candidate whose
freshness and expiry decide whether an acceptance is current. At most two
renewals are permitted. A cycle, fork, missing head, changed finding, non-adjacent counter
or predecessor-digest mismatch is integrity-invalid and `INCOMPLETE`; a requested third
renewal is the conclusive policy outcome `FAIL`. Neither writes an artifact. Acceptance
records expire only when the current UTC date is later than `expires`; they cannot
suppress, skip, relabel or turn a failed or incomplete check green.

Observable acceptance examples:

- **Success.** **Given** singly linked anchored inputs, three clean privacy checks, an
  unused final path and the exact controlling-terminal response for the displayed role and
  challenge, **when** `ai-eng accept` publishes, **then** exactly one digest-bound
  `record.json` appears, `spec.md` is byte-identical and the snapshot-publication outcome
  is `PASS`, without claiming the respondent's identity.
- **Missing authority.** **Given** no controlling terminal, a piped response, a denied role
  token or a response that differs by one byte, **when** acceptance is requested, **then**
  the outcome is `INCOMPLETE` and no final or temporary record remains.
- **Concurrent change.** **Given** the displayed spec, evidence or predecessor changes
  before the final bounded read, **when** the command revalidates, **then** it returns
  `INCOMPLETE`; **given** a source changes only after that read, **when** the immutable
  snapshot is published, **then** it remains bound to the bytes actually confirmed and the
  next unified read is `INCOMPLETE`. In both cases no source byte is overwritten.
- **Publication collision.** **Given** another writer publishes the chosen final path,
  **when** exclusive publication runs, **then** exactly one writer commits and the loser is
  `INCOMPLETE` without replacing, removing or renaming the winner.
- **Legacy history.** **Given** one valid embedded acceptance in a preserved legacy spec
  path, **when** the unified expiry view runs, **then** it includes that record exactly
  once, applies its real expiry and never rewrites or copies it; **given** valid ordinals
  `01` and `03`, **when** a new record is numbered, **then** it uses `02` rather than
  treating the historical gap as corruption; **given** one ID-less legacy head in numeric
  owner `001`, **when** it is renewed, **then** the reader displays derived provenance,
  uses `R-001-01` in `renews`, binds its exact block in `renews_digest`, publishes
  `R-001-02` and leaves the legacy bytes unchanged.
- **Noncanonical namespace.** **Given** `R-042-01` is embedded in
  `specs/spec-042-note/spec.md` and one unique canonical `--spec 042` target exists,
  **when** its renewal is numbered, **then** every `042` home participates and the new ID
  is `R-042-02`, never a duplicate `R-042-01`.
- **Malformed history.** **Given** an unreadable, malformed, duplicate, ambiguous,
  hard-linked, symlinked, reparse/junction, mount-crossing, aliased or over-bound legacy or
  new record, **when** either listing or writing evaluates the register, **then** the
  outcome is `INCOMPLETE`, not an empty or partial green result; **given** a wrong
  `record_digest` or `renews_digest`, **when** renewal is requested, **then** it is refused
  as an integrity failure rather than repaired by the renewal.
- **Privacy uncertainty.** **Given** missing or wrong-version Gitleaks, personal-name
  ambiguity or input unsupported by either deterministic privacy check, **when** the
  candidate is evaluated, **then** the outcome is `INCOMPLETE`; **given** a conclusive
  secret, personal datum or machine path, **then** it is `FAIL`. Neither publishes.
- **Midnight.** **Given** a human prompt starts before a UTC date boundary and confirmation
  arrives after it, **when** publication resumes, **then** `accepted` uses the later date
  and an expiry earlier than that date yields `INCOMPLETE` with no live record.
- **Renewal.** **Given** a unique earlier-spec or legacy chain head with fewer than two
  renewals and an exact canonical `--spec` target, **when** its displayed ID and digest are
  confirmed, **then** a new cross-spec-capable record points to that unchanged head and
  increments the counter once; **given** two renewals already exist, **when** another is
  requested, **then** the outcome is `FAIL` and nothing is written.
- **Stale renewal cure.** **Given** a structurally and chain-valid head whose current spec
  or evidence no longer matches its stored digest, **when** the current-acceptance view
  runs, **then** it is `INCOMPLETE` but remains the renewable head; **when** the human
  confirms the displayed old head plus newly observed spec and evidence, **then** the new
  immutable renewal binds the current bytes without changing the stale predecessor.
- **Durability claim.** **Given** exclusive rename succeeds but later rendering fails,
  **when** the execution result is reported or retried, **then** the record remains the one
  committed `PASS` and cannot be overwritten; **given** no crash/recovery receipt, **then**
  no power-loss durability claim appears.

## Decisions

No decision block is recorded before approval. Approval records the decisions above with
the repository CLI and promotes only cross-spec decisions to MADRs.

## Accepted risks

None. Every risk remains open until removed or explicitly accepted by authorized human or
preapproved policy with complete evidence and expiry.

## Production-ready

Nothing gets a URL until every box is ticked by observed evidence.

- [ ] CI/CD — build, lint, test and security analysis on every push; deploy from the default branch
- [ ] Logs — structured JSON, one line per event, with level and service, to stdout
- [ ] Traces — only if this is our code and has more than one hop; no hop, no trace
- [ ] Errors — every uncaught exception leaves as a log with severity 17 and marks its span
- [ ] Health and data age — alive, age of newest datum, and independent recomputation
- [ ] External check — something outside the service verifies it and states its limits
- [ ] Second path — every published number is independently recomputed and compared
- [ ] Security — secrets sealed, no credential in a plain variable, SAST and dependency audit in CI

### Evidence for each box, as of this candidate

One row per box, and every row says the same thing, because it is true: this wave built the
verifier and earned no receipt. A box is ticked by a check-evidence receipt at
`.ai/receipts`, measured against a declaration committed at `.ai/readiness.json`, and this
repository has neither. `INCOMPLETE` is unproven — it is not a failure and it is never a
pass, and writing it eight times is the honest close of a wave whose whole subject was the
green nobody earned.

| Box | Receipt | State |
|---|---|---|
| CI/CD | none written | INCOMPLETE |
| Logs | none written | INCOMPLETE |
| Traces | none written | INCOMPLETE |
| Errors | none written | INCOMPLETE |
| Health and data age | none written | INCOMPLETE |
| External check | none written | INCOMPLETE |
| Second path | none written | INCOMPLETE |
| Security | none written | INCOMPLETE |
