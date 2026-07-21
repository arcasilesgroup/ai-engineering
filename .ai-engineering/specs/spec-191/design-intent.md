# Design Intent — spec-191

## Design

`route_required=False` — no `/ai-design` pass.

**Rationale:** The design-routing keyword allowlist matches the substring `page`, which
appears in the spec body as "a fetched web page or file" (i.e. content returned by `WebFetch`,
not a UI screen). No other UI keyword (`component`, `screen`, `dashboard`, `form`, `modal`,
`color palette`, `typography`, `layout`, `ui`, `ux`, `frontend`, `react`, `vue`,
`interface`, `mobile`, `responsive`, `accessibility`) matches a UI concern. spec-191 is a
security-plane refactor: extract an IOC-evaluation module, wire a dead allowlist, and add a
`PostToolUse` guard hook. There is no user-facing surface to design.
