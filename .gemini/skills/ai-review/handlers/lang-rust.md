# Handler: Language -- Rust

## Purpose

Language-specific review for Rust code. Supplements the 8-concern review agents with ownership-aware checks, unsafe block auditing, error handling patterns, and performance-sensitive idiom validation.

## Integration

Dispatched as **Step 2b** (between Step 2 dispatch and Step 3 aggregate). Findings use the same YAML format. Language findings receive a **+10% confidence bonus** when corroborated by a concern agent.

## Procedure

### Step 1 -- Detect Rust Scope

1. Identify `.rs` files in the diff
2. If no Rust files, skip this handler entirely
3. Check `Cargo.toml` for dependencies and edition
4. Detect usage patterns from imports:
   - `tokio` / `async-std` -> enable async runtime checks
   - `actix-web` / `axum` / `rocket` -> enable web framework checks
   - `diesel` / `sqlx` / `sea-orm` -> enable database checks
   - `serde` -> enable serialization checks
5. Read `.ai-engineering/contexts/languages/rust.md` if not already loaded

### Step 2 -- Critical Findings (severity: critical)

**unwrap() / expect() in production code**
```rust
// BAD: panics at runtime
let value = map.get("key").unwrap();
let file = File::open("config.toml").unwrap();

// GOOD: propagate or handle
let value = map.get("key").ok_or_else(|| Error::MissingKey("key"))?;
let file = File::open("config.toml").context("failed to open config")?;
```
- Confidence 90% in `src/` (non-test) code
- Acceptable in tests, examples, build scripts, and provably-safe cases with documented invariant

**unsafe blocks without SAFETY comment**
```rust
// BAD: no justification
unsafe {
    ptr::write(dest, value);
}

// GOOD: documented invariant
// SAFETY: `dest` is valid for writes because it was allocated on line 42
// and has not been deallocated. Alignment is guaranteed by the layout.
unsafe {
    ptr::write(dest, value);
}
```
- Every `unsafe` block must have a `// SAFETY:` comment explaining why it is sound

**Discarding #[must_use] values**
```rust
// BAD: Result silently ignored
let _ = sender.send(message);  // send returns Result
map.insert(key, value);        // when return value matters

// GOOD: handle the result
sender.send(message).map_err(|e| warn!("send failed: {e}"))?;
if let Some(old) = map.insert(key, value) {
    debug!("replaced existing value: {old:?}");
}
```
- Flag `let _ =` on `#[must_use]` types: `Result`, `MustUse`, iterator adaptors

**Return Err without context**
```rust
// BAD: loses context chain
fn load_config(path: &Path) -> Result<Config> {
    let content = fs::read_to_string(path)?;  // bare ? loses "what were we doing"
    toml::from_str(&content)?;
}

// GOOD: contextual errors (anyhow or thiserror)
fn load_config(path: &Path) -> Result<Config> {
    let content = fs::read_to_string(path)
        .with_context(|| format!("reading config from {}", path.display()))?;
    toml::from_str(&content).context("parsing config TOML")?;
}
```

**panic!, todo!, unreachable! in production paths**
```rust
// BAD: process crashes
panic!("unexpected state");
todo!("implement later");
unreachable!();  // without proof

// GOOD: return error or use debug_assert
return Err(Error::UnexpectedState(state));
```
- Acceptable: `unreachable!()` after exhaustive match, `todo!()` behind feature flags in dev branches

### Step 3 -- High Findings (severity: major)

**Unnecessary .clone()**
```rust
// BAD: cloning when a borrow suffices
let name = user.name.clone();
println!("{}", name);

// GOOD: borrow
println!("{}", user.name);
```
- Flag `.clone()` where the cloned value is only read, never mutated or moved into owned context
- Confidence 70% (borrow checker sometimes requires clone for valid reasons)

**String when &str suffices**
```rust
// BAD: unnecessary allocation
fn greet(name: String) {
    println!("Hello, {name}");
}

// GOOD: accepts both &str and String
fn greet(name: &str) {
    println!("Hello, {name}");
}
```
- Flag function parameters that take `String` but never mutate or store it

**Blocking in async context**
```rust
// BAD: blocks the async runtime thread
async fn handle_request() {
    let data = std::fs::read_to_string("file.txt");  // blocking!
    std::thread::sleep(Duration::from_secs(1));       // blocking!
}

// GOOD: async alternatives
async fn handle_request() {
    let data = tokio::fs::read_to_string("file.txt").await;
    tokio::time::sleep(Duration::from_secs(1)).await;
}
```
- Flag `std::fs::*`, `std::thread::sleep`, `std::net::*` inside `async fn`

**Unbounded channels**
```rust
// CAUTION: unbounded can consume unlimited memory
let (tx, rx) = tokio::sync::mpsc::unbounded_channel();

// BETTER: bounded with backpressure
let (tx, rx) = tokio::sync::mpsc::channel(100);
```
- Confidence 60% (unbounded is sometimes intentional for low-volume signals)

### Step 4 -- Medium Findings (severity: minor)

**to_string() / format!() in hot paths**
- Allocations in loops, iterators, or frequently-called functions
- Suggest `write!` to a buffer or `Cow<str>` for conditional allocation

**Vec without with_capacity**
```rust
// BAD: multiple reallocations
let mut items = Vec::new();
for i in 0..known_count {
    items.push(compute(i));
}

// GOOD: pre-allocate
let mut items = Vec::with_capacity(known_count);
```
- Only flag when the size is known or estimable at creation time

**Derive order convention**
```rust
// Convention: Debug, Clone, Copy first; then PartialEq, Eq, Hash; then Serialize, Deserialize
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
```
- Confidence 40% (style preference)

**Missing #[must_use] on public functions returning values**
- Public functions that return `Result`, `Option`, or meaningful values without `#[must_use]`

### Step 5 -- Diagnostic Tool Cross-Reference

| Tool | Command | Validates |
|------|---------|-----------|
| cargo clippy | `cargo clippy -- -W clippy::all -W clippy::pedantic` | Idiomatic patterns, performance, correctness |
| cargo-audit | `cargo audit` | Known vulnerabilities in dependencies |
| cargo-deny | `cargo deny check` | License compliance, duplicate deps, advisories |
| cargo test | `cargo test` | Test coverage verification |
| miri | `cargo +nightly miri test` | Undefined behavior in unsafe code |

If a diagnostic tool contradicts a finding, note the discrepancy and adjust confidence accordingly.

## Output Format

```yaml
findings:
  - id: lang-rust-N
    severity: critical|major|minor
    confidence: 0-100
    file: path
    line: N
    finding: "description"
    evidence: "code snippet"
    remediation: "how to fix"
    self_challenge:
      counter: "why this might be wrong"
      resolution: "why it stands or adjustment"
      adjusted_confidence: N
```
