# Handler: Rust Build Resolver

## Purpose

Resolves Rust compilation errors with special emphasis on borrow checker diagnostics, lifetime analysis, and trait bound failures. Covers the full diagnostic chain from `cargo check` through `cargo clippy`, `cargo fmt`, dependency auditing with `cargo-audit`, and duplicate detection with `cargo tree`. Targets Rust 2021 edition and later using Cargo workspaces.

## Activation

Activate this handler when:

- The project contains `Cargo.toml` at the repository root or in a workspace member
- Source files have the `.rs` extension
- Build errors reference Rust compiler codes (e.g., `E0382`, `E0277`, `E0106`)
- The user reports issues with `cargo build`, `cargo test`, or `cargo run`

## Diagnostic Sequence (Phase 2 -- Reproduction)

Run these commands in order. Stop at the first failure and diagnose before continuing.

```bash
# 1. Verify Rust toolchain
rustc --version && cargo --version

# 2. Check compilation without producing binaries (fastest feedback)
cargo check 2>&1

# 3. Run clippy for lint-level diagnostics
cargo clippy --all-targets --all-features -- -D warnings 2>&1

# 4. Verify formatting compliance
cargo fmt --all --check 2>&1

# 5. Check for duplicate dependency versions
cargo tree --duplicates 2>&1

# 6. Audit dependencies for known vulnerabilities (if cargo-audit installed)
cargo audit 2>&1

# 7. Run the full test suite
cargo test --all-targets --all-features 2>&1

# 8. For workspace projects, check all members
cargo check --workspace 2>&1
```

## Error Table (Phase 3 -- Root Cause)

| Error | Cause | Fix |
|-------|-------|-----|
| `cannot borrow X as mutable because it is also borrowed as immutable` | Simultaneous mutable and immutable borrows of the same value within overlapping scopes. | Restructure code so the immutable borrow ends before the mutable borrow begins. Clone the value if shared ownership is needed, or use `RefCell<T>` for interior mutability. |
| `X does not live long enough` | A reference outlives the data it points to. The borrowed value is dropped while still referenced. | Extend the lifetime of the owned value, return owned data instead of references, or use `Arc<T>` / `Rc<T>` for shared ownership. |
| `cannot move out of X which is behind a shared reference` | Attempting to take ownership of data behind `&T` (a shared reference does not permit moves). | Clone the value, use `&mut T` if mutation is needed, or restructure to avoid moving out of the reference. |
| `mismatched types: expected X, found Y` | Function return type, variable assignment, or argument does not match the expected type. | Convert explicitly (`.into()`, `as`, `From::from`). For enum variants, ensure all arms return the same type. For `Result`/`Option`, use `?` or `map`. |
| `the trait X is not implemented for Y` | A generic bound or function signature requires trait `X` but type `Y` does not implement it. | Implement the trait for `Y`, use a type that already implements it, or add `#[derive(X)]` if it is a derivable trait. |
| `unresolved import X` | The module path is wrong, the item is not public, or the crate is not in `Cargo.toml`. | Verify the import path. Check `pub` visibility. Add the crate to `[dependencies]` in `Cargo.toml` and run `cargo check`. |
| `lifetime may not live long enough` | A lifetime annotation is missing or incorrect, causing the compiler to infer conflicting lifetimes. | Add explicit lifetime annotations. Ensure input and output lifetimes are correctly related. Consider returning owned data. |
| `future cannot be sent between threads safely (not Send)` | An async function holds a non-Send type (e.g., `Rc`, `RefCell`, raw pointer) across an `.await` point. | Replace `Rc` with `Arc`, `RefCell` with `Mutex` or `RwLock`. Restructure so non-Send values do not span `.await` points. |
| `value used after move` (E0382) | A value was moved (ownership transferred) and then used again. | Clone before the move, use references instead, or restructure to avoid reuse after move. |
| `type annotations needed` (E0282) | The compiler cannot infer the type and needs explicit annotation. | Add type annotations to the variable, use turbofish syntax (`func::<Type>()`), or annotate the closure parameters. |
| `no method named X found for type Y` | Method does not exist on the type, or the trait providing it is not in scope. | Bring the trait into scope with `use`. Check that `Y` is the correct type (not a reference or wrapper). |
| `this function takes N arguments but M were supplied` | Argument count mismatch in function call. | Check the function signature. Common after refactoring when parameters were added or removed. |

## Borrow Checker Examples

### Simultaneous mutable and immutable borrow

```rust
// BROKEN: immutable borrow `first` still alive when `v` is mutably borrowed
let mut v = vec![1, 2, 3];
let first = &v[0];       // immutable borrow starts
v.push(4);                // mutable borrow -- conflict
println!("{first}");      // immutable borrow used here

// FIXED: end the immutable borrow before mutating
let mut v = vec![1, 2, 3];
let first = v[0];         // copy the value (i32 is Copy)
v.push(4);                // no conflict
println!("{first}");
```

### Value does not live long enough

```rust
// BROKEN: `s` is dropped at end of block, but reference escapes
fn dangling() -> &str {
    let s = String::from("hello");
    &s  // s dropped here, reference is dangling
}

// FIXED: return owned data
fn not_dangling() -> String {
    let s = String::from("hello");
    s  // ownership transferred to caller
}
```

### Cannot move out of shared reference

```rust
// BROKEN: trying to move `name` out of a shared reference
struct User { name: String }

fn get_name(user: &User) -> String {
    user.name  // cannot move out of &User
}

// FIXED: clone or return a reference
fn get_name(user: &User) -> String {
    user.name.clone()
}

// ALTERNATIVE: return a reference with proper lifetime
fn get_name(user: &User) -> &str {
    &user.name
}
```

### Async not Send

```rust
// BROKEN: Rc is not Send, held across .await
use std::rc::Rc;

async fn process() {
    let data = Rc::new(vec![1, 2, 3]);
    some_async_call().await;  // Rc held across await
    println!("{:?}", data);
}

// FIXED: use Arc instead of Rc
use std::sync::Arc;

async fn process() {
    let data = Arc::new(vec![1, 2, 3]);
    some_async_call().await;
    println!("{:?}", data);
}
```

## Dependency Troubleshooting

```bash
# Show the full dependency tree
cargo tree

# Find why a specific crate is included
cargo tree --invert --package some-crate

# List duplicate dependency versions
cargo tree --duplicates

# Update dependencies within semver constraints
cargo update

# Update a specific dependency
cargo update --package some-crate

# Check for yanked crates
cargo install --locked cargo-audit && cargo audit

# Clean build artifacts (resolves stale compilation issues)
cargo clean

# Rebuild with verbose output for linker diagnostics
cargo build --verbose 2>&1
```

## Feature Flag Troubleshooting

```bash
# List all available features for a dependency
cargo metadata --format-version=1 | jq '.packages[] | select(.name == "some-crate") | .features'

# Build with a specific feature enabled
cargo check --features "feature-name"

# Build with all features enabled
cargo check --all-features

# Build with no default features
cargo check --no-default-features
```

## Hard Rules

- **NEVER** use `unsafe` blocks to bypass borrow checker errors. The borrow checker is correct. Restructure the code.
- **NEVER** add `.unwrap()` to silence `Result` or `Option` errors. Use `?`, `match`, `unwrap_or`, `unwrap_or_else`, or `expect` with a descriptive message.
- **NEVER** add `#[allow(clippy::...)]` or `#[allow(unused)]` to suppress warnings. Fix the code or refactor.
- **NEVER** use `mem::transmute` or `mem::forget` to work around ownership issues.
- **ALWAYS** propagate errors with `?` in library code. Reserve `expect()` for cases with a clear invariant message.
- **ALWAYS** run `cargo clippy` after fixes, not just `cargo check`.
- **ALWAYS** verify that `cargo fmt --check` passes after edits.

## Stop Conditions

- The error requires `unsafe` code to resolve (FFI boundary, raw pointer manipulation). Escalate with the exact safety requirement.
- The error involves a compiler bug or ICE (Internal Compiler Error). Report the rustc version and escalate.
- Two fix attempts have failed for the same borrow checker error. Provide the ownership diagram and both attempted approaches to the user.

## Output Format

```
[FIXED] <file>:<line> -- <error code> <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

[FIXED] <file>:<line> -- <error code> <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

Build Status: PASS | cargo check | cargo clippy | cargo test
```
