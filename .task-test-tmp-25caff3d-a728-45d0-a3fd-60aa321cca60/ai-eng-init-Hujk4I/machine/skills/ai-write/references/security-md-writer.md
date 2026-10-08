# SECURITY.md writer — the vulnerability-reporting discipline

Loaded when writing or reviewing SECURITY.md. Sources: the standard .github
SECURITY.md pattern, the Yocto Project SECURITY file convention, and this
repo's own policy (the product IS a security boundary).

## The contract

SECURITY.md tells a stranger with a vulnerability exactly where to take it and
what happens next. Its quality is measurable: a reporter can reach the right
channel without reading any other file.

## Section order

1. **Security policy statement** — one paragraph: what the product protects,
   so a reporter can classify their finding.
2. **Reporting a vulnerability** — the private channel (email with PGP where
   available); an explicit NEVER-public-issue rule; response-time commitments
   (acknowledgement window, triage window); who validates the fix (never the
   finder); what to include (affected component, repro, diagnostics).
3. **Supported versions** — the table: version → supported yes/no, with the
   archive tag or successor noted for expired lines.
4. **Scope** — what counts as a vulnerability, ranked (critical/high), with
   the invariants an attacker would break; explicitly out-of-scope items so
   triage is fast.
5. **Hardening notes** — the design decisions that already close known paths;
   each names the mechanism (fail-closed, zero-network, pinned checks).
6. **Disclosure policy** — coordinated disclosure, credit, timeline.

## Writing rules

- **One channel, unambiguous** — a single private address; no "or open an
  issue if unsure".
- **Commitments are numbers** — 72 hours, 7 days; vague SLAs are broken SLAs.
- **The version table is maintained** — an expired "supported" row is a false
  safety claim; update it at every major release.
- **Never leak exploit detail** — the file states scope, not attack recipes.
- English only; no machine paths.
