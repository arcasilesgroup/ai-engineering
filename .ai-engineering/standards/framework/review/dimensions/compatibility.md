# Compatibility Review Dimension

## Scope Priority
1. **Public API changes** — added required params, removed/reordered params, type changes
2. **Removed public APIs** — functions, classes, constants, endpoints deleted
3. **Behavioral changes** — new exceptions, changed return values, changed defaults
4. **Data format changes** — JSON field names, database column types, serialization format
5. **Database schema** — removed columns, incompatible type changes, missing defaults
6. **Dependency changes** — increased minimum versions, removed optional deps

## Key Rule
Only flag breaking changes to code already shipped in the default branch (main/master). Never flag new code introduced in the current branch.

## Self-Challenge
- Is this API actually public/consumed externally, or is it internal?
- Is the breaking change intentional and documented in the PR description?
