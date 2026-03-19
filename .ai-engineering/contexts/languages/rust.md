## Read Before You Write

Before implementing functionality that operates on a type:

1. Read the struct definition and check its derives (`Deserialize`, `Serialize`, `Clone`, `Default`, etc.)
2. If a derive provides what you need, use it - don't reimplement manually
3. If writing >10 lines for parsing/serialization, stop and check the derives

## Patterns to Detect

Flag these patterns in Rust code:

- **Error type masking**: Converting all error types to a single `Ok(None)` or generic error masks infrastructure issues. Connection failures vs key-not-found should be distinguished for monitoring and alerting.
- **Pass-through without validation**: Data from external sources (cache, API) passed through without validating structure. Malformed data silently accepted, potentially causing downstream issues.
- **Accidental feature removal**: During refactors or migrations, verify existing functionality isn't accidentally removed. Compare old vs new behavior for feature parity.
- **Avoidable clone via reordering**: Unnecessary `clone()` calls can often be avoided by reordering operations - perform non-consuming operations first, then move the value.

## Dependency Management

**Critical checks:**

- Run `cargo shear` - unused deps indicate design problems
- Verify Cargo features actually enable code that exists
- Check new dependencies are actually imported/used
- Avoid `cargo shear` ignores without strong justification

**Golden rule:** If `cargo shear` wants to remove it, either use it properly or remove it.

## Error Handling

**Idiomatic patterns:**

- Use `Result<T, E>` for recoverable errors
- Use `?` operator for error propagation
- Implement `std::error::Error` for custom errors
- Prefer `anyhow` or `thiserror` over custom types

**Anti-patterns:**

- Unwrapping without justification (use `expect` with message)
- Silently ignoring errors
- Panic in library code
- Using `unwrap()` on production code paths
- Never `unwrap()` on user input or external data

### Error Code Consistency

- Use the error type's `error_code()` method instead of hardcoding strings
- Keeps logs, metrics, and API responses consistent

## Ownership & Lifetimes

**Common issues:**

- Unnecessary cloning (pass references instead)
- Fighting the borrow checker (redesign data flow)
- Complex lifetime annotations (simplify structure)
- Mixing `&T` and `&mut T` incorrectly

**Patterns:**

- Use `&str` for string parameters, `String` for owned
- Prefer borrowing over `Clone` when possible
- Use `Cow<'_, T>` for conditional ownership

## Async Patterns

**Critical checks:**

- Blocking operations in async functions (use `spawn_blocking`)
- Missing `.await` on futures
- Holding locks across `.await` points (causes deadlocks)
- Not using `tokio::select!` for cancellation

**Common mistakes:**

- Mixing async runtimes (stick to one)
- CPU-intensive work in async functions
- Not handling cancellation properly

## Guard Patterns (RAII)

- **Log/metric guards that auto-emit on drop**: Never call `emit()` through a mutable reference like `guard.log_mut().emit()`. This emits but doesn't set the guard's `emitted` flag, causing double emission on drop.
- **Correct patterns**:
  - Set fields and let the guard emit on drop
  - Consume the guard with `guard.emit()` or `guard.into_inner()`

## Type Safety

**Leverage the type system:**

- Use newtypes for domain concepts
- `Option<T>` instead of nullable patterns
- Enums for state machines
- Type aliases for complex types

**Anti-patterns:**

- Stringly-typed code
- Using `as` casts unsafely
- Ignoring compiler warnings about unused results

## String Operations

- **Efficient truncation**: Use `s.char_indices().nth(max_chars)` to find the byte position in one pass, then slice. Avoid counting characters twice:

```rust
// Good - O(max_chars)
match s.char_indices().nth(max_chars) {
    None => Cow::Borrowed(s),
    Some((idx, _)) => Cow::Owned(s[..idx].to_string()),
}

// Bad - O(2n)
if s.chars().count() > max { s.chars().take(max).collect() }
```

## Request Pipeline Awareness

- Before adding validation/truncation, check if the request parsing layer already handles it
- Example: distinct_id may already be truncated at parse time

## Filtering with Dependencies

- When optimizing by filtering to a subset (e.g., `flag_keys`), ensure dependencies from the full graph are included in the analysis
- A flag might not be in the filter set but still get evaluated as a dependency

## Testing Patterns

**Rust testing:**

- Unit tests in the same file with `#[cfg(test)]`
- Integration tests in `tests/` directory
- Use `#[should_panic]` for error conditions
- Mock traits, not structs

**Test organization:**

- Test modules named `tests`
- One assertion per test when possible
- Use descriptive test names

## Performance

**Common optimizations:**

- Use iterators instead of loops (lazy evaluation)
- `Vec` pre-allocation with `with_capacity`
- Avoid unnecessary allocations
- Use `&[T]` slices instead of `Vec<T>` in signatures

**Profiling:**

- Profile before optimizing
- Use `cargo flamegraph` for CPU profiling
- Check for unnecessary clones with `cargo clippy`

## Derive Awareness (Critical)

**The most common source of unnecessary complexity in Rust:** Manual code that reimplements what a derive macro already provides.

**Detection signals:**

- Field-name string literals: `.get("user_id")` matching struct fields
- Repetitive per-field operations: N similar `.get().and_then()` calls
- Disproportionate line count: 50+ lines for a simple type conversion
- Error messages naming fields: `"Missing 'id' field"`

**Common patterns to flag:**

| If struct has... | Flag this manual pattern | Use instead |
|------------------|--------------------------|-------------|
| `#[derive(Deserialize)]` | `.get("field").and_then(\|v\| v.as_*())` chains | `serde_json::from_value()` |
| `#[derive(Serialize)]` | Manual `serde_json::json!{}` or HashMap building | `serde_json::to_value()` |
| `#[derive(Clone)]` | `Self { a: self.a.clone(), b: self.b, ... }` | `.clone()` |
| `#[derive(Default)]` | `Self { a: 0, b: String::new(), ... }` | `Default::default()` |
| `#[derive(FromRow)]` | Manual `row.get("column")` extraction | Let sqlx use the derive |
| `#[derive(Debug)]` | Manual `fmt::Debug` impl with same output | Remove manual impl |

**The test:** For any conversion/parsing function, ask: "Does a derive already handle this?"

**Example - what to catch:**

```rust
// RED FLAG: Struct has Deserialize but function does manual parsing
#[derive(Deserialize)]
pub struct Team { id: i32, name: String, /* 30 fields */ }

// This 150-line function should be 3 lines:
pub fn from_json(value: Value) -> Result<Team, Error> {
    let obj = value.as_object().ok_or(Error::Parse)?;
    let id = obj.get("id").and_then(|v| v.as_i64())...;  // repeated 30x
    // ... 140 more lines of manual field extraction ...
}

// CORRECT: Use the derive
pub fn from_json(value: Value) -> Result<Team, Error> {
    serde_json::from_value(value).map_err(|e| Error::Parse(e.to_string()))
}
```

**Why this matters:**

- Manual parsing is 50x more code
- Manual parsing misses edge cases serde handles (nulls, missing fields, type coercion)
- Manual parsing must be updated when struct fields change
- Serde is battle-tested; manual code is not

## Log Safety

**Truncate user-provided strings:**

- User-Agent headers can be KB+ from bots/crawlers
- Truncate to reasonable limits (256-512 chars) in log lines
- Apply to any user-controlled string in structured logs

```rust
// Before logging user input
let user_agent = truncate_chars(raw_user_agent, 512);
tracing::info!(user_agent = ?user_agent, "request received");
```

## Idioms

**Rust conventions:**

- Use `impl Trait` for return types
- Implement `From` and `Into` for conversions
- Use `Default` trait for initialization
- Derive `Debug`, `Clone` where appropriate
- Follow naming conventions (snake_case, CamelCase)

## Common Clippy Warnings

**Address these:**

- `needless_borrow` - unnecessary `&`
- `unnecessary_unwrap` - use pattern matching
- `large_enum_variant` - box large variants
- `too_many_arguments` - use a struct

## Quality Checklist

**Before committing:**

- `cargo fmt` - format code
- `cargo clippy --all-targets --all-features -- -D warnings` - fix all warnings
- `cargo shear` - check for unused dependencies
- Verify Cargo features enable real functionality
- Run tests with `cargo test`
