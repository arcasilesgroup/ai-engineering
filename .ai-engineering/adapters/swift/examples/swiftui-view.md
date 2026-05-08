# Example — SwiftUI view + ViewModel

Demonstrates: small focused view, `@StateObject` for owned model,
`@MainActor` for UI updates, `.task` for async loads.

```swift
// Sources/MarketsApp/MarketsListView.swift
import SwiftUI
import Markets

@MainActor
final class MarketsListViewModel: ObservableObject {
    enum State: Equatable {
        case idle
        case loading
        case loaded([Market])
        case failed(String)
    }

    @Published private(set) var state: State = .idle

    private let repo: MarketRepository

    init(repo: MarketRepository) { self.repo = repo }

    func load() async {
        state = .loading
        do {
            let markets = try await repo.fetchAll()
            state = .loaded(markets)
        } catch {
            state = .failed(error.localizedDescription)
        }
    }
}

struct MarketsListView: View {
    @StateObject var viewModel: MarketsListViewModel

    var body: some View {
        Group {
            switch viewModel.state {
            case .idle, .loading:
                ProgressView()
            case .loaded(let markets):
                List(markets, id: \.symbol) { market in
                    HStack {
                        Text(market.symbol)
                        Spacer()
                        Text("\(market.lastPrice)")
                    }
                }
            case .failed(let message):
                Text("Error: \(message)").foregroundStyle(.red)
            }
        }
        .task { await viewModel.load() }
    }
}
```

## TDD pairing — testing the ViewModel

```swift
// Tests/MarketsAppTests/MarketsListViewModelTests.swift
import XCTest
@testable import MarketsApp
@testable import Markets

private struct StubRepo: MarketRepository {
    let result: Result<[Market], Error>
    func fetchAll() async throws -> [Market] {
        switch result {
        case .success(let v): return v
        case .failure(let e): throw e
        }
    }
}

@MainActor
final class MarketsListViewModelTests: XCTestCase {
    func test_load_setsLoadedOnSuccess() async throws {
        let m = try Market(symbol: "BTC", lastPrice: 1)
        let vm = MarketsListViewModel(repo: StubRepo(result: .success([m])))
        await vm.load()
        XCTAssertEqual(vm.state, .loaded([m]))
    }
}
```
