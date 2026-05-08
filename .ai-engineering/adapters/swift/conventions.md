<!-- source: contexts/languages/swift.md @ affdef6d3235a65039813845a467340fa4f70803 -->

# Swift — Build Conventions

Authoritative reference for the `ai-build` agent when generating
Swift code. Distilled from `contexts/languages/swift.md` plus
`contexts/frameworks/ios.md`.

## Toolchain

- **Swift version**: 5.10+ (Swift 6 once concurrency-strict is
  shippable in your dependency graph). Pin in `Package.swift`
  `swift-tools-version`.
- **Build**: SwiftPM (`swift build`). Xcode projects are valid for
  apps but the CLI must build from `swift build` for CI.
- **Linter**: SwiftLint with `--strict` in CI.
- **Formatter**: SwiftFormat (apple/swift-format or nicklockwood
  swiftformat) — pick one per repo and stick with it.

## Layout (SwiftPM)

```
Package.swift
Sources/
  Markets/
    Market.swift
Tests/
  MarketsTests/
    MarketTests.swift
```

- One target per logical module. Tests target name is `<Module>Tests`.

## Naming (Swift API Design Guidelines)

| Element | Convention | Example |
|---|---|---|
| Types / protocols | UpperCamelCase | `MarketRepository` |
| Functions / methods / vars | lowerCamelCase | `fetchMarket(id:)` |
| Constants | lowerCamelCase | `maxRetries` (not `MAX_RETRIES`) |
| Acronyms | full case | `URL`, `ID`, `JSON` |
| Booleans | `is`/`has`/`should` prefix | `isReady`, `hasFlag` |

## Optionals

- Force-unwrap (`!`) only on IBOutlets or known-safe constants.
- `if let` / `guard let` for control flow.
- `??` for defaults; `?.` for safe chaining.
- `try?` when the error is unrecoverable noise; `try!` only in tests.

## Errors

- Define error enums conforming to `Error` (and `LocalizedError` when
  they bubble to UI).
- `throws` functions for fallible operations; `Result<T, Error>`
  only at concurrency boundaries.
- Always `do { try ... } catch { ... }`; never bare `try!`.

## Value vs reference types

- Default to `struct` for data models — copy-on-write semantics are
  safer.
- `class` only for shared mutable state, identity, or inheritance.
- `final class` unless inheritance is part of the design.

## Concurrency

- `async`/`await` over completion handlers in new code.
- `Task { ... }` to bridge sync → async.
- `@MainActor` on UI updates; `@globalActor` for module singletons.
- `actor` for shared mutable state; `Sendable` for types crossing
  isolation boundaries.

## SwiftUI

- Prefer many small views over monolithic ones.
- `@State` for view-local state; `@StateObject` for owned reference
  models; `@ObservedObject` only when the parent owns it.
- `@Binding` for child views modifying parent state.
- Use `.task` for view-async work; cancellation is automatic.

## Quality gate (pre-commit)

1. `swift build`
2. `swift format --in-place .` (or SwiftFormat) — verify no diff
3. `swiftlint --strict`
4. `swift test` — see `tdd_harness.md`
