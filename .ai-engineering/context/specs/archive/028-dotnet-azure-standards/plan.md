# Spec-028 Plan: .NET & Azure Standards Expansion + Principal Engineer Evolution

## Approach

Standards-only expansion strategy. Expand existing `dotnet.md` and `azure.md` as single source of truth for all .NET/Azure knowledge. Zero new skills — existing generic skills automatically consume expanded patterns via standard references. Evolve `principal-engineer` agent to read-write multi-stack implementor.

## Phases

1. **Phase 1**: Expand `dotnet.md` (57 -> ~155 lines) — SDK pinning, NuGet, 18 code patterns, 15 EF Core patterns, test tiers, testing patterns, performance patterns, C# conventions.
2. **Phase 2**: Expand `azure.md` (70 -> ~134 lines) — Azure Functions, App Service, Logic Apps, Well-Architected Framework, 17 cloud design patterns.
3. **Phase 3**: Evolve `principal-engineer` (v1 -> v2) — read-write scope, implementation capabilities, stack detection, multi-stack references.
4. **Phase 4**: Update skill cross-references, product-contract, changelog, mirror sync.

## Files Changed

14 files total (canonicals + mirrors). Zero new skills. Zero new slash commands.

## Decision

D028-001: Standards-only expansion. See `state/decision-store.json`.
