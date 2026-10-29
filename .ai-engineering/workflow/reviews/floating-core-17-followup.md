# Checkpoint 17 follow-up review

## Goal

Preserve the hook denial reason and exit status while enforcing the three-line output cap without coupling the test to incidental newline formatting.

## Acceptance

- Successful hook output remains silent, including with an active override.
- Denied output retains its reason and exit status and remains within the output cap.
- The floor-gates test verifies diagnostic content without requiring verbatim multiline formatting.

## changed_files

- `src/floor/entry.ts`
- `tests/floor-gates.spec.ts`
- `tests/token-budget.spec.ts`

## Verify

- `bun test tests/floor-gates.spec.ts`
- `bun test tests/token-budget.spec.ts`

## Follow-up review

- **Verdict:** PASS — no findings (no finding IDs or severities).
- **Blocker/major remaining:** None.
