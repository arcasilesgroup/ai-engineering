# Rust Review Guidelines

## Update Metadata
- Rationale: Rust-specific patterns for ownership, error handling, and derive awareness.

## Idiomatic Patterns
- Use `Result<T, E>` with `?` operator for error propagation — no `.unwrap()` in production code.
- Prefer `&str` over `String` for function parameters when ownership isn't needed.
- Use `#[derive(...)]` for common traits — detect manual reimplementation of `Debug`, `Clone`, `Serialize`.
- Prefer `impl Trait` over `dyn Trait` when the concrete type is known at compile time.

## Performance Anti-Patterns
- **Unnecessary `.clone()`**: Often indicates ownership design issue.
- **Allocating in loops**: Move allocations outside loops, reuse buffers.
- **Missing `#[inline]`** on small, frequently-called functions in library code.

## Security Patterns
- Use `secrecy::Secret<T>` for sensitive values — prevents accidental logging.
- Validate all FFI boundary inputs.
- Use `zeroize` for cryptographic key cleanup.

## Derive Awareness
- Detect manual JSON parsing when `serde_json::from_value()` exists.
- Detect manual `Display` implementations when `#[derive(Display)]` (from `derive_more`) suffices.
- Detect manual `Error` implementations when `thiserror` crate provides derive macros.

## Self-Challenge Questions
- Is the `.unwrap()` genuinely unreachable, or does it need error handling?
- Does the suggested ownership change break the borrow checker elsewhere?

## References
- Enforcement: `standards/framework/stacks/rust.md`
