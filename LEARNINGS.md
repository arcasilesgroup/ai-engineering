# Learnings

Accumulated failures and lessons from building features, mostly written by `/ai-orchestrator`. Every planner, implementer, test writer and reviewer reads **Rules** before starting.

- **Log** lives in [docs/history/learnings-log.md](docs/history/learnings-log.md) and is
  append-only: never edit or delete an entry; new entries are appended there, continuing its
  numbering.
- **Rules** is the distilled version. A lesson is promoted here once it has recurred (2 or more log entries) or caused a human-review rejection or a circuit-breaker stop. Each rule cites the entries it came from.

## Rules

- R1: Assert the current approved behavior, ordering, and exact consumer-visible contents (exact bytes, not presence or `toContain`), not source text, stale prose or field names, or a bare type check; prove each test fails under the mutation it guards against, changing person-controlled state before a poll. (from L2, L11, L102, L160, L187, L207, L246, L247)
- R2: Assert every field and linkage a consumer relies on — in a test, and in a guard that reads output: every path a record can carry, not one string that happens to equal the value. (from L13, L14, L22, L207)
- R3: Check status and approval gates before continuation; cover every acceptance branch, test passing and refusing transitions, and place each guard in the exact configuration where it alone stands between input and harm. (from L7, L12, L18, L83, L84, L143)
- R4: Emit only commands whose target is unambiguous — pin the ref or worktree a command mutates, and never anchor what a command targets (default-branch selection during analysis included) to mutable HEAD. (from L16, L17; the cp2 adversarial review and behavior spot-check both passed it — run emitted commands in the current≠default configuration)
- R5: A fixture must hold its premise against real Git state — prove the relevant SHA, HEAD, base, and owner count before asserting a derived classification, and never let it sit on the guarded branch. (from L19, L20, L158, L182)
- R6: Enforce protection and normalize values at the one choke point every consumer funnels through, not per path — a guard placed only where a test pinned one configuration is forgotten by the next path — and exclude protected refs before presenting deletion candidates. (from L18, L20, L30, L188, L248)
- R7: Derive every list, count, path and precedence from the thing that owns it — the command's own contract or the tool itself (ask Git, do not re-implement it), re-derived at write time — never a neighbour command's sweep, a remembered list, or a number copied into prose, which is only a cache of the command that produces it. (from L15, L21, L27, L248)
- R8: Pin read scope and fail closed: HEAD, user/global config, or repository-locating environment must not decide what a read sees; a read failure is not absence, and a guard that cannot decide denies. Resolve a value only where it is used. (from L16, L23, L139, L140, L165, L248)
- R9: Define remote commands with a closed allowlist; inspect complete command examples before acceptance, reject shell composition and unsafe forms, and accept only bare allowlisted executable names. A static Markdown allowlist cannot secure executable resolution from `PATH`. (from L37–L42, L44–L45)
- R10: Use the already-authenticated Azure CLI and its Azure DevOps extension for Azure DevOps access; never write tokens or credentials. (from L57)
- R11: Scope each contract assertion to the specific command it governs; a neighboring command or generic assertion cannot stand in for it. (from L34–L36)
- R12: Narrow optional and indexed values where they are consumed, and fail closed when a required value is absent. (from L46, L50–L51, L94, L110, L186)
- R13: Sanitize untrusted values at the output boundary; HTML-escape text, validate raw and decoded URLs separately, and do not reprocess inserted content. (from L52–L55, L131)
- R14: Redact credential assignments at the shared output boundary by semantic key families, including nested assignments, while preserving safe near-matches. (from L58–L62)
- R15: Keep executable `.mjs` APIs explicitly declared, and embed script/declaration payloads as text when they are data rather than host modules. (from L47, L64)
- R16: Route repository-owned artifacts through their repository procedure and test the caller-to-procedure handoff; a same-named installed copy may have a conflicting contract. (from L66)
- R17: For runtime p95 checks under parallel test load, use enough samples for nearest-rank p95 to tolerate scheduler outliers without loosening the budget. (from L65, L67)
- R18: Normalize Markdown formatting without altering identifiers; preserve underscores, case, and other contract-significant characters before matching. (from L82, L89, L97, L103)
- R19: Treat ignored paths as user data: explain destructive loss before approval, then carry the irreversible action and actual remaining state through every outcome and caller. (from L105, L107, L169, L195)
- R20: Gate 1 CLI acceptance must assert physical total and unknown classification together; physical presence is not lifecycle certainty. (from L126)
- R21: Preserve state before recording a failure; report rollback only after restoration is proven. (from L91, L92)
- R22: When a workflow moves into a command, update and test the caller handoff before documenting or reviewing the lifecycle. (from L99, L100)
- R23: Bind approval and closure to every immutable plan field and the exact reviewed revision; keep runtime gate state outside that fingerprint. (from L115, L117, L124)
- R24: Regenerate embedded assets after the final source or skill edit, then verify the generated payload. (from L146, L149, L161)
- R25: Keep documentation aligned with current behavior, enforced scope, and supported commands; mark superseded behavior as historical. (from L162, L171, L209, L210)
- R26: Route artifacts and next-step handoffs from the selected lane, as declared by each skill's Lifecycle. (from L189, L193, L194)
- R27: Resolve worktree source and ownership from the invoking or Git-registered checkout, consistent branch-to-path mapping, and a fresh checkpoint—not branch prefixes or directory layout. Establish freshness and owner ambiguity before matching a supplied SHA; unknown ownership stays ambiguous. (from L86, L167, L170, L172, L175, L177–L182)
- R28: What ai-eng wrote is ai-eng's and always converges to the binary, edited or not: a skill folder it ships is its whole (dot-led entries aside), a recorded path stays its after an edit, and install, update and uninstall share that one rule. Two recorded kinds follow a marker instead: a git hook shim is rewritten by update but removed by uninstall only while it carries the shim marker, and a shared settings file only ever has ai-eng's marked entries merged in or stripped out. Only what it never wrote (a skill in a folder of your own name, a file already there whose bytes differ from ai-eng's, a link of yours) and seeded config you edited are yours and never touched; a file already there byte-identical to ai-eng's cannot be told from ai-eng's write and is recorded as its. Test repair with missing files; when a finding names one write path, sweep its siblings. (from L203, L205, L236, L238, L241, L243, L244, L271)
- R29: Apply defaults and explicit values in one render, and preserve the distinction between omitted and explicitly empty configuration. (from L198, L199, L201, L204)
- R30: Serialize shared claims at the claim boundary and hold the lock across the whole claim; a liveness check or read-then-write does not provide exclusive ownership. A lock records its owner and is reclaimed only when that owner is provably dead; when staleness cannot be proven, hold it. (from L125, L136, L238, L239, L241)
- R31: Merged into R38.
- R32: Reconcile evidence by chronology and direct identity before classifying status; a current comment or shared field does not prove event time or identity. (from L76, L77, L78)
- R33: A PR publishes the existing current branch and verifies publication before forge creation; opening a PR does not create or switch branches. (from L191, L211)
- R34: Derive managed hook commands from canonical artifacts and remove only exact owned entries, preserving user commands and groups. (from L148, L150, L153, L154)
- R35: Derive test-hygiene scope from the active test tree rather than a handwritten suite list. (from L135, L184)
- R36: Keep the invoking checkout's source HEAD separate from its integration base; never refresh from a historical base. (from L163, L168)
- R37: Separate baseline configuration/test-contract failures and pre-existing hygiene artifacts from feature regressions; do not change feature code or budgets to hide them. (from L129, L130, L230)
- R38: Verify path identity, canonical containment and every alias (symlink, hard link, unselected surface) at filesystem boundaries, and bind the check to the exact file and folder the mutation acts on, revalidating after directory creation; a path checked earlier does not establish the current inode. On mismatch abort and preserve the replacement; when the API cannot make that binding, refuse with a warning. (from L87, L88, L183, L220, L222–L224, L226, L228, L229, L234, L235)
- R39: Route every install and cleanup write through the one guarded helper; catch filesystem refusals there and return a named refusal that callers report as a warning while the rest (lock file included) completes. A failed cleanup never changes a file's ownership class. (from L237, L242, L243)
- R40: Edit a user's config by byte offset at the smallest unit requested; parse original and result and write only when the sole difference is the requested key, else refuse with the file byte-identical; run destructive steps only after that write succeeds. (from L218, L245, L246)
- R41: Run gate suites from a Git-backed clone at the exact HEAD, never an archive, with locked dependencies, test homes outside the clone, the default `TMPDIR`, and no injected global or system config. (from L197, L219, L221, L231)
- R42: A failed gate keeps its first failing test, assertion and environment; capture and reproduce that before changing code. (from L197, L215, L217)

## Historical log

Historical log: docs/history/learnings-log.md — the chronological L1–L271 entries whose lessons are distilled into the Rules above.
