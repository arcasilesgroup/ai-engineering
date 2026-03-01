# Spec-028: .NET & Azure Standards Expansion + Principal Engineer Evolution

## Summary

Expand existing standards (`dotnet.md`, `azure.md`) as single source of truth for all .NET knowledge. Evolve `principal-engineer` agent from read-only reviewer to read-write implementor with multi-stack references.

## Strategy

Standards-only expansion. Zero new skills — existing generic skills (`api-design`, `test-runner`, `database-ops`, `cicd-generate`, `infrastructure`, `performance`) already read applicable stack standards and automatically consume expanded patterns.

## Deliverables

1. Expand `dotnet.md` (57 -> 155 lines): SDK pinning, NuGet management, 18 code patterns, 15 EF Core patterns, test tiers, 12 testing patterns, 10 performance patterns, C# conventions.
2. Expand `azure.md` (70 -> 134 lines): Azure Functions, App Service, Logic Apps, Well-Architected Framework, 17 cloud design patterns.
3. Evolve `principal-engineer` (v1 -> v2, read-only -> read-write): implementation capabilities, stack detection, multi-stack references.
4. Update 4 skill cross-references: test-runner, database-ops, data-modeling, performance.

## Decision

D028-001: Standards-only expansion strategy. See `state/decision-store.json`.
