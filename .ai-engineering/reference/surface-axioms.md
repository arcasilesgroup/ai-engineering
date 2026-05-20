# Surface Axioms (spec-133 D-133-04)

> Canonical home for the Surface / No-Twin Axioms. Extracted from
> `CANONICAL.md` §16 by spec-134 sub-005 so the four IDE mirrors stay
> lean (§10.4 DRY — one canonical source) and operator-facing CLI/
> skill design has a stable reference.

The **Surface Axiom** + **No-Twin Axiom** are first-class design
rules. The skill/CLI confusion (B17 root) is eliminated at the
design layer, not just the lint layer.

## A1 — Surface Axiom (when may a capability expose `ai-eng <verb>`?)

A capability MAY expose a `ai-eng <verb>` CLI iff ALL THREE hold:

1. **Scriptable from shell / CI** — there is a credible non-interactive
   use case that does NOT require a human in the loop.
2. **Deterministic happy-path** — the default-args invocation completes
   without any AI judgment (the engine is a state machine, not a model).
3. **Structured-machine-readable output** — `--json` returns a stable
   envelope (`{ok, command, code, data, meta}`); exit codes follow
   `_exit_codes.py` category map (0/1/2/78).

If any condition fails, the capability lives only as a `/ai-<name>`
skill. `/ai-start` is a deterministic logo + reminder (A1.c fails:
no structured data) — correctly remains skill-only.

## A2 — No-Twin Axiom (when does the same verb name appear in both surfaces?)

A capability has **one canonical surface per role**. Skill = chat
entry; CLI = shell entry. The same verb name appears in BOTH iff

1. **Same engine** — both surfaces dispatch the same Python code path
   (skill orchestrator invokes the CLI under the hood OR both wrap a
   shared service in `core/`).
2. **Identical contract** — `--json` shape, exit codes, and side-effects
   are byte-equivalent.

Otherwise the verbs MUST be distinct. `/ai-branch-cleanup` (LLM-orchestrated)
and `ai-eng cleanup` (deterministic 7-mode CLI) are distinct verbs by
A2 because the engines differ — the skill calls the CLI but adds AI
judgment on top.

## Enforcement

- `tests/architecture/test_surface_parity.py` asserts no orphan twin
  surfaces (any name that appears in both `.claude/skills/<name>/` and
  `cli_factory.py` registrations must have identical contracts or be
  documented as A2-distinct in `docs/cli-reference.md`).
- CLI output that mentions chat-only `/ai-*` commands must label them
  as AI-surface commands, not shell commands (D-133-22).
