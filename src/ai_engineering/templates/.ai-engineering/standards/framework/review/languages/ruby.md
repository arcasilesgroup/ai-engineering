# Ruby Review Guidelines

## Update Metadata
- Rationale: Ruby-specific patterns for idiomatic Ruby, Rails conventions, and testing.

## Idiomatic Patterns
- Use `frozen_string_literal: true` magic comment in all files.
- Prefer `each_with_object` or `transform_values` over manual hash building.
- Use keyword arguments for methods with 3+ parameters.
- `raise` custom errors inheriting from `StandardError`, not generic `RuntimeError`.

## Performance Anti-Patterns
- **N+1 in ActiveRecord**: Use `includes()`, `preload()`, or `eager_load()`.
- **Memory bloat**: Use `find_each` / `in_batches` for large collections instead of `all.each`.
- **Unnecessary object allocation**: Freeze string constants.

## Security Patterns
- Strong parameters in Rails controllers — never trust `params.permit!`.
- Use `bcrypt` for password hashing.
- Sanitize HTML output with Rails helpers.

## Testing Patterns
- RSpec with `describe`/`context`/`it` structure.
- `let` for lazy-evaluated setup, `let!` for eager.
- FactoryBot for test data, not fixtures.

## Self-Challenge Questions
- Is this a Ruby version or Rails version issue?
- Does the suggested refactoring follow Ruby community conventions?

## References
- Enforcement: `standards/framework/stacks/ruby.md`
