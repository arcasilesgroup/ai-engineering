# Framework Rust Stack Standards

## Update Metadata

- Rationale: establish Rust-specific patterns for systems programming, CLIs, and high-performance services.
- Expected gain: consistent Rust code quality, safety patterns, and testing standards.
- Potential impact: Rust projects get enforceable memory safety, error handling, and testing patterns.

## Stack Scope

- Primary language: Rust (latest stable edition).
- Supporting formats: TOML (Cargo.toml), Markdown, YAML, JSON.
- Toolchain baseline: `rustup`, `cargo`, `clippy`, `rustfmt`.
- Distribution: binary release, crate (crates.io), container image.

## Required Tooling

- Package/build: `cargo` (build, test, run, bench).
- Lint: `clippy` (`cargo clippy -- -D warnings`).
- Format: `rustfmt` (`cargo fmt`).
- Type checking: built-in (Rust compiler).
- Test runner: built-in (`cargo test`) + `cargo-nextest` (preferred for parallel execution).
- Dependency vulnerability scan: `cargo-audit`.
- Coverage: `cargo-tarpaulin` or `cargo-llvm-cov`.
- Security SAST: `semgrep` (Rust rules), `gitleaks` (secret detection).

## Minimum Gate Set

- Pre-commit: `cargo fmt --check`, `cargo clippy -- -D warnings`, `gitleaks`.
- Pre-push: `semgrep`, `cargo audit`, `cargo test`, `cargo build --release`.

## Quality Baseline

- All public APIs documented with `///` doc comments.
- Test coverage target: per `standards/framework/quality/core.md`.
- Clippy warnings treated as errors (`-D warnings`).
- No `unsafe` blocks without documented safety invariants and `// SAFETY:` comments.
- No `unwrap()` or `expect()` in library code — use proper error handling.

## Code Patterns

- **Error handling**: `thiserror` for library errors, `anyhow` for application errors. Define domain-specific error enums.
- **Result propagation**: use `?` operator consistently. Return `Result<T, E>` from fallible functions.
- **Ownership**: prefer borrowing (`&T`, `&mut T`) over cloning. Use `Arc<T>` for shared ownership across threads.
- **Concurrency**: `tokio` for async runtime. `rayon` for data parallelism. No `unsafe` thread primitives.
- **Serialization**: `serde` with `serde_json`/`serde_yaml` for data interchange.
- **CLI**: `clap` (derive macro) for command-line argument parsing.
- **HTTP**: `axum` (preferred) or `actix-web` for web services. `reqwest` for HTTP clients.
- **Logging**: `tracing` crate for structured logging and spans.
- **Small focused functions**: <50 lines, single responsibility.
- **Project layout**: `src/lib.rs` (library), `src/main.rs` (binary), `src/bin/` (multiple binaries), `tests/` (integration tests).

## Testing Patterns

- Unit tests: inline `#[cfg(test)] mod tests` within source files.
- Integration tests: `tests/` directory, each file is a separate test binary.
- Doc tests: `///` examples that compile and run as tests.
- Property tests: `proptest` or `quickcheck` for invariant-based testing.
- Benchmark tests: `criterion` for reliable benchmarking.
- Naming: `#[test] fn test_<unit>_<scenario>_<expected>()`.

## Update Contract

This file is framework-managed and may be updated by framework releases.
