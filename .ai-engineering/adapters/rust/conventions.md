<!-- source: contexts/languages/rust.md @ affdef6d3235a65039813845a467340fa4f70803 -->

# Rust — Build Conventions

Authoritative reference for the `ai-build` agent when generating Rust
code. Distilled from `contexts/languages/rust.md`.

## Toolchain

- **Rust edition**: `edition = "2021"` minimum; `2024` once stable.
- **Channel**: stable. Pin via `rust-toolchain.toml` so contributors
  match CI.
- **Formatter**: `cargo fmt --all -- --check` blocks CI.
- **Linter**: `cargo clippy --all-targets --all-features -- -D warnings`.
  No exceptions; if a lint is wrong for a case, allow it locally with
  a justifying comment.
- **Audit**: `cargo audit` and `cargo deny` in CI.

## Workspace layout

```
Cargo.toml          # workspace manifest
crates/
  app/
    Cargo.toml
    src/main.rs
  domain/
    Cargo.toml
    src/lib.rs
```

- One crate per published unit. Bins under `crates/app/`, libs under
  `crates/<domain>/`.
- `Cargo.lock` committed for app crates, *not* for libraries
  published to crates.io.

## Naming

- Modules / files: `snake_case`.
- Types / traits: `UpperCamelCase`.
- Constants / statics: `UPPER_SNAKE_CASE`.
- Functions / variables: `snake_case`.
- Lifetimes: `'short`, prefer descriptive names over `'a` for
  long-lived borrows.

## Errors

- `Result<T, E>` for fallible APIs. `?` operator everywhere; never
  manual match-and-return for the happy path.
- Library crates: define a domain error enum with `thiserror`. Don't
  expose `anyhow::Error` from a public API.
- Application crates (binaries): `anyhow::Result<()>` is fine in
  `main`.
- `unwrap()` and `expect()` are for tests and provably-infallible
  paths only. Each call site has a comment explaining why.

## Ownership

- Borrow over clone. Reach for `&T`/`&mut T`; clone only when the
  borrow checker forces it AND a redesign is too costly.
- Use `Cow<'_, T>` when ownership is sometimes needed.
- Prefer `&str` parameters over `&String`; `&[T]` over `&Vec<T>`.

## Async

- `tokio` is the default runtime. `async-std` only when a host
  ecosystem mandates it.
- Never block the runtime: CPU-bound code goes to `spawn_blocking`.
- Don't hold a `MutexGuard` across `.await`. Use `tokio::sync::Mutex`
  if you must, but prefer message passing.

## Type-driven design

- Use derives whenever they exist. Manual `Debug`, `Clone`,
  `Serialize`, `Deserialize` impls are red flags.
- Newtype wrappers for domain identifiers (`struct UserId(Uuid);`)
  rather than passing raw primitives.
- Sealed enums (`#[non_exhaustive]`) for state machines that may
  grow.

## Quality gate (pre-commit)

1. `cargo fmt --all -- --check`
2. `cargo clippy --all-targets --all-features -- -D warnings`
3. `cargo nextest run` (or `cargo test`) — see `tdd_harness.md`
4. `cargo audit` and `cargo deny check` in CI
