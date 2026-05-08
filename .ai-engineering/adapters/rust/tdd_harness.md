# Rust — TDD Harness

`ai-build` runs RED → GREEN → REFACTOR through `cargo test` (or
`cargo nextest`). Tests are deterministic and never reach the network.

## Runner

- **Default**: `cargo test`. Fast, zero deps, ships with the
  toolchain.
- **Optional but recommended**: `cargo nextest` — faster, better
  parallelism, clearer output. Add to CI for repos with large suites.
- Doc-tests via `cargo test --doc` for runnable examples in `///`
  comments.

## Layout

```
crates/markets/
  src/
    lib.rs
    market.rs
    market/
      tests.rs   # private, in-crate tests via #[cfg(test)] mod tests;
  tests/
    integration.rs   # public-API tests via the crate's external API
```

- **Unit tests** live in the same module under
  `#[cfg(test)] mod tests { ... }`.
- **Integration tests** live in `tests/` at the crate root and import
  the crate as an external user would.
- **Bench tests** live in `benches/` and run via `cargo bench`
  (Criterion preferred).

## Naming

- Unit-test modules: `mod tests` inside the unit being tested.
- Test functions: `#[test] fn parses_empty_input_as_error()` —
  assertion-first phrasing.
- Integration files: one per logical surface
  (`tests/it_lookup.rs`, `tests/it_create.rs`).

## RED → GREEN → REFACTOR

1. **RED** — write the failing test. Run
   `cargo test -p markets test_name -- --nocapture`. Confirm the
   failure message matches the assertion.
2. **GREEN** — minimum implementation. Do not modify the test.
3. **REFACTOR** — clean up; suite stays green.

## #[cfg(test)] pattern

```rust
fn normalise(input: &str) -> Result<String, ParseError> { /* ... */ }

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_empty_input() {
        assert!(matches!(normalise(""), Err(ParseError::Empty)));
    }
}
```

## Parameterise

Use `rstest` for parametric tests (or hand-rolled
`#[test_case(...)]`):

```rust
use rstest::rstest;

#[rstest]
#[case("", false)]
#[case("BTC", true)]
fn validates_symbol(#[case] input: &str, #[case] ok: bool) {
    assert_eq!(is_valid(input), ok);
}
```

## Async tests

```rust
#[tokio::test]
async fn loads_market() {
    let m = repo.load("id").await.unwrap();
    assert_eq!(m.symbol, "BTC");
}
```

## Mocks / fakes

- Hand-rolled in-memory fakes for trait-bound dependencies.
- `mockall` for complex mock surfaces; pin the version.

## Coverage

- `cargo llvm-cov --html` (or `cargo tarpaulin` on Linux).
- Floor: 80 % statement coverage on touched files.
