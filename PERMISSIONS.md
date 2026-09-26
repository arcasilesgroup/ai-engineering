# Permissions

Who can call what. This is the authorization spec: any change to access must update this file in the same commit, and the adversarial reviewer checks endpoints against it.

**Status: n/a** — this product has no endpoints yet. Replace this note with the matrix below when the first endpoint ships.

<!-- TEMPLATE. One row per endpoint (or server action). Columns are the roles from AGENTS.md → Project config → Roles. -->

Legend: ✓ allowed · own = only their own records · — denied

| Endpoint | <role 1> | <role 2> | <role 3> | Notes |
|---|---|---|---|---|
| `GET /<resource>` | ✓ | own | — | <scope rules, filters> |
| `POST /<resource>` | ✓ | — | — | |
