# Example — Swift value type + XCTest

A `struct` Market with a typed parser + Equatable conformance, plus
XCTest cases. Demonstrates: value semantics, error enum, no force
unwrap, async-free unit testing.

```swift
// Sources/Markets/Market.swift
import Foundation

public enum MarketError: Error, Equatable {
    case emptySymbol
    case symbolTooLong
    case symbolNonLetter
}

public struct Market: Equatable, Hashable, Sendable {
    public let symbol: String
    public let lastPrice: Decimal

    public init(symbol: String, lastPrice: Decimal) throws {
        let trimmed = symbol.trimmingCharacters(in: .whitespaces)
        guard !trimmed.isEmpty else { throw MarketError.emptySymbol }
        guard trimmed.count <= 10 else { throw MarketError.symbolTooLong }
        guard trimmed.allSatisfy({ $0.isLetter && $0.isASCII }) else {
            throw MarketError.symbolNonLetter
        }
        self.symbol = trimmed.uppercased()
        self.lastPrice = lastPrice
    }
}
```

```swift
// Tests/MarketsTests/MarketTests.swift
import XCTest
@testable import Markets

final class MarketTests: XCTestCase {
    func test_init_throwsOnEmptySymbol() {
        XCTAssertThrowsError(try Market(symbol: "", lastPrice: 1)) { error in
            XCTAssertEqual(error as? MarketError, .emptySymbol)
        }
    }

    func test_init_normalisesSymbolToUppercase() throws {
        let m = try Market(symbol: "btc", lastPrice: 65000)
        XCTAssertEqual(m.symbol, "BTC")
    }

    func test_equatable_compares_by_value() throws {
        let a = try Market(symbol: "BTC", lastPrice: 1)
        let b = try Market(symbol: "BTC", lastPrice: 1)
        XCTAssertEqual(a, b)
    }
}
```
