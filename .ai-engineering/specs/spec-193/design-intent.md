# Design Intent — spec-193

## Design

`/ai-plan` routed this spec through `/ai-design` because the conservative
substring detector matched `component`, `dashboard`, `form`, and `ui`. The
spec does not introduce a graphical interface; the relevant experience is the
operator-facing terminal flow around credential replacement and irreversible
revocation.

### Direction

**Industrial minimalism: a fail-loud migration ledger.** The operator always
sees the current logical credential, the proven state, the next reversible or
irreversible action, and the recovery path—never a secret, identity, account,
workspace, endpoint, or raw command output.

### Interaction contract

1. Start with a values-free preflight summary: closed surfaces, blocked rows,
   current state, proposed next transition, and recovery command ID.
2. Default every mutation to preview. Applying it requires `--apply` plus the
   exact checkpoint ID shown by the preview; stale IDs fail closed.
3. Checkpoint one uses the explicit phrase
   `CONFIRM <logical-id> REPLACEMENT`; checkpoint two uses
   `CONFIRM <logical-id> INVALIDATE OLD`. Confirmation is per credential and
   never batched.
4. Render state as text, not color alone:
   `DISCOVERED`, `SOURCE_CONTAINED`, `TARGET_READY`, `NEW_AUTH_OK`,
   `CONFIG_CUTOVER`, `OLD_INVALID`, `POSTCHECK`, or `BLOCKED`.
5. Authentication probes show only `PASS`, `BLOCKED`, or `FAIL`, a probe ID,
   exit code, timestamp, and redacted-field count. Raw stdout/stderr stays
   suppressed and is never persisted.
6. Every destructive prompt states impact and recovery before confirmation.
   Escape, interrupt, timeout, or mismatched state leaves the row unchanged.
7. The current agent host is restarted last from a neutral terminal. Resume
   starts from the persisted state and never trusts the interrupted process as
   cold-start evidence.

### Accessibility and terminal compatibility

- Plain text is authoritative; ANSI color is optional reinforcement only.
- `NO_COLOR`, non-TTY, screen readers, copy/paste, and narrow terminals receive
  the same semantic order and complete status labels.
- Prompts accept keyboard input only, use one decision at a time, and never
  depend on animation, icons, emoji, mouse interaction, light/dark themes, or
  positional context.
- Tables have a line-oriented fallback and bounded width; machine mode emits
  the allowlisted receipt schema, never human prose or raw provider output.

### Pre-delivery checklist result

The applicable `/ai-design` gates are satisfied by textual state labels,
single-action prompts, visible error/recovery messages, keyboard-only control,
and color-independent outcomes. Visual, touch, responsive-layout, typography,
theme, image, and motion checks are not applicable because no GUI is created.
