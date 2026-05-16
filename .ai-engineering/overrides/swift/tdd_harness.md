# Swift — TDD Harness

`ai-build` runs RED → GREEN → REFACTOR through XCTest (or
swift-testing on Swift 6). Tests are deterministic and don't reach
the network.

## Runner

- **CLI**: `swift test` (SwiftPM) is canonical and CI-friendly.
- **Xcode**: `xcodebuild test -scheme <Name>` for iOS / app targets.
- **Swift 6+**: `swift-testing` (Apple's modern test framework) is
  preferred for new test files; XCTest remains for legacy.

## Layout

```
Sources/Markets/Market.swift
Tests/MarketsTests/MarketTests.swift
Tests/MarketsTests/Resources/   # test fixtures
```

- One test class per unit under test, mirrored to source path.
- Resources via SwiftPM `resources: [.process("Resources")]` in the
  test target.

## Naming

- File: `<Unit>Tests.swift`.
- Class: `final class <Unit>Tests: XCTestCase` (or struct + `@Suite`
  in swift-testing).
- Method: `func test_<behaviour>_<condition>()` —
  `test_returnsNil_whenInputIsEmpty`. swift-testing uses
  `@Test func returnsNil_whenInputIsEmpty()` instead.

## RED → GREEN → REFACTOR

1. **RED** — write the failing test. Run
   `swift test --filter MarketsTests/MarketTests/test_x`. Confirm the
   failure message matches the assertion.
2. **GREEN** — minimum implementation. Do not modify the test.
3. **REFACTOR** — clean up; suite stays green.

## XCTest patterns

```swift
import XCTest
@testable import Markets

final class MarketTests: XCTestCase {
    func test_init_normalisesSymbol() throws {
        let market = try Market(symbol: "btc")
        XCTAssertEqual(market.symbol, "BTC")
    }

    func test_init_throwsOnEmptySymbol() {
        XCTAssertThrowsError(try Market(symbol: "")) { error in
            XCTAssertEqual(error as? MarketError, .emptySymbol)
        }
    }
}
```

## swift-testing patterns (Swift 6)

```swift
import Testing
@testable import Markets

@Suite("Market")
struct MarketTests {
    @Test func init_normalisesSymbol() throws {
        let market = try Market(symbol: "btc")
        #expect(market.symbol == "BTC")
    }
}
```

## Async tests

```swift
func test_load_returnsMarket() async throws {
    let market = try await repo.load(id: "id-1")
    XCTAssertEqual(market.symbol, "BTC")
}
```

## Helpers

- `XCTAssertEqual`, `XCTAssertNil`, `XCTAssertThrowsError`.
- `XCTSkipIf(...)` for environment-dependent tests.
- `addTeardownBlock { ... }` for per-test cleanup.

## Mocks / fakes

- Hand-rolled fakes implementing protocol surfaces. Avoid
  Mockingbird / Cuckoo unless the team has invested in them — the
  reflection-based generators add complexity for little gain.

## Coverage

- `swift test --enable-code-coverage`.
- Floor: 80 % statement coverage on touched files.
