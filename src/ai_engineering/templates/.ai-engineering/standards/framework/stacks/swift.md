# Framework Swift Stack Standards

## Update Metadata

- Rationale: establish Swift patterns for iOS/macOS/visionOS apps and server-side Swift.
- Expected gain: consistent Apple platform code quality, safety patterns, and testing standards.
- Potential impact: Swift projects get enforceable build, lint, and testing patterns.

## Stack Scope

- Primary language: Swift 5.9+ (strict concurrency).
- Supporting formats: Markdown, JSON, YAML, Property Lists.
- Toolchain baseline: Xcode 15+, Swift Package Manager (SPM).
- Distribution: App Store, TestFlight, SPM package, container (server-side).

## Required Tooling

- Build: Xcode / `xcodebuild`, Swift Package Manager.
- Lint: `swiftlint` (configured via `.swiftlint.yml`).
- Format: `swiftformat` (configured via `.swiftformat`).
- Test runner: XCTest, `swift test` (SPM).
- Dependency vulnerability scan: `trivy`, manual audit of SPM dependencies.
- Security SAST: `semgrep` (Swift rules), `gitleaks` (secret detection).

## Minimum Gate Set

- Pre-commit: `swiftformat --lint`, `swiftlint`, `gitleaks`.
- Pre-push: `semgrep`, `swift build`, `swift test`.

## Quality Baseline

- All public APIs documented with `///` doc comments.
- Test coverage target: per `standards/framework/quality/core.md`.
- Strict concurrency checking enabled (`-strict-concurrency=complete`).
- No force-unwraps (`!`) in production code without documented safety invariant.

## Code Patterns

- **Error handling**: typed throws (Swift 5.9+), custom `Error` enums. Use `do-catch`, not force-try.
- **Concurrency**: Swift Structured Concurrency (`async/await`, `TaskGroup`, actors). No GCD in new code.
- **Architecture**: SwiftUI + Observation framework (iOS 17+), MVVM for UIKit legacy.
- **Dependency injection**: Environment values (SwiftUI), protocol-based injection.
- **Networking**: `URLSession` async/await. Codable for JSON serialization.
- **Persistence**: SwiftData (preferred), Core Data (legacy), UserDefaults for settings only.
- **Small focused functions**: <50 lines, single responsibility.
- **Project layout**: SPM package structure, `Sources/`, `Tests/`.

## Testing Patterns

- Unit tests: XCTest, `@Test` macro (Swift Testing framework).
- UI tests: XCUITest for critical user flows.
- Snapshot tests: `swift-snapshot-testing` for UI regression.
- Naming: `test_<unit>_<scenario>_<expected>`.
- Mock: protocol-based mocking, no runtime mocking frameworks.

## Update Contract

This file is framework-managed and may be updated by framework releases.
