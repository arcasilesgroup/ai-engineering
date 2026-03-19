## Ruby Best Practices

### Idiomatic Ruby

**Use Ruby idioms:**

- Use blocks and `yield` for flexible APIs
- Prefer `each` over `for` loops
- Use symbols (`:symbol`) for hash keys and identifiers
- Use string interpolation: `"Hello #{name}"` not `"Hello " + name`
- Use safe navigation: `user&.name` (Ruby 2.3+)

**Pattern:**

```ruby
# ✅ GOOD: Ruby idioms
users.each { |user| puts user.name }
user&.profile&.email

# ❌ BAD: Not idiomatic
for i in 0...users.length
    puts users[i].name
end
```text

### Naming Conventions

**Ruby style:**

- `snake_case` for methods, variables, file names
- `CamelCase` for classes and modules
- `SCREAMING_SNAKE_CASE` for constants
- `?` suffix for predicate methods: `empty?`, `valid?`
- `!` suffix for dangerous/mutating methods: `save!`, `sort!`

### Blocks, Procs, and Lambdas

**When to use each:**

- Blocks: For iteration and simple callbacks
- Procs: When you need to pass code as object
- Lambdas: When you need strict argument checking

**Patterns:**

```ruby
# ✅ Block for iteration
[1, 2, 3].map { |n| n * 2 }

# ✅ Lambda for strict behavior
double = ->(x) { x * 2 }
double.call(5)  # Returns 10

# ✅ Proc for flexible behavior
increment = Proc.new { |x| x + 1 }
```text

### Exception Handling

**Best practices:**

- Use `raise` to throw exceptions
- Rescue specific exceptions, not `Exception`
- Use `ensure` for cleanup (like finally)
- Use `rescue` modifier for simple cases

**Pattern:**

```ruby
# ✅ GOOD: Specific exception
begin
  dangerous_operation
rescue ActiveRecord::RecordNotFound => e
  handle_not_found(e)
ensure
  cleanup
end

# ✅ GOOD: Inline rescue for simple cases
value = risky_call rescue default_value

# ❌ BAD: Catching all exceptions
rescue Exception => e  # Too broad
```text

### Metaprogramming

**Use carefully:**

- `define_method` for dynamic method creation
- `method_missing` only when absolutely necessary (define `respond_to_missing?` too)
- `class_eval` and `instance_eval` sparingly
- Prefer explicit methods over meta when possible

**Anti-pattern:**

```ruby
# ❌ BAD: Overusing method_missing
def method_missing(name, *args)
  # Complex logic
end

# ✅ GOOD: Explicit methods or define_method
[:name, :email, :phone].each do |attr|
  define_method(attr) do
    @attributes[attr]
  }
end
```text

### Class Design

**Best practices:**

- Use `attr_reader`, `attr_writer`, `attr_accessor` for attributes
- Keep classes focused (Single Responsibility)
- Prefer composition over inheritance
- Use modules for shared behavior (mixins)
- Make methods private unless needed publicly

**Pattern:**

```ruby
class User
  attr_reader :name, :email

  def initialize(name, email)
    @name = name
    @email = email
  end

  private

  def internal_helper
    # Implementation
  end
end
```text

### Enumerable Methods

**Prefer enumerable methods:**

- Use `map`, `select`, `reject`, `find`, `reduce`
- Use `any?`, `all?`, `none?` for boolean checks
- Chain methods for readability
- Use `with_index` when you need index

**Pattern:**

```ruby
# ✅ GOOD: Chained enumerable
active_user_names = users
  .select(&:active?)
  .map(&:name)
  .sort

# ✅ GOOD: Boolean checks
if users.any?(&:admin?)
  # Handle admin presence
end
```text

### String and Symbol Usage

**Best practices:**

- Use symbols for identifiers and hash keys
- Use strings for data
- Use string interpolation, not concatenation
- Use `%w` for word arrays: `%w[one two three]`
- Use `%Q` or `%q` for complex strings

### Hash and Array Patterns

**Modern Ruby:**

- Use keyword arguments (hash syntax)
- Use trailing commas in multi-line hashes/arrays
- Use `fetch` with default for safe hash access
- Use `dig` for nested hash access (Ruby 2.3+)

**Pattern:**

```ruby
# ✅ GOOD: Keyword arguments
def create_user(name:, email:, admin: false)
  # Implementation
end

# ✅ GOOD: Safe hash access
config.fetch(:timeout, 30)
user.dig(:address, :city, :name)
```text

### Performance Considerations

**Common optimizations:**

- Use `freeze` for constants to prevent modification
- Use `||=` for lazy initialization
- Avoid string concatenation in loops (use array join or `<<`)
- Use symbols over strings for repeated values
- Consider `Set` for membership checks on large collections

**Pattern:**

```ruby
# ✅ GOOD: Lazy initialization
def expensive_value
  @expensive_value ||= calculate_expensive_value
end

# ✅ GOOD: String building
parts = []
items.each { |item| parts << item.to_s }
result = parts.join('')
```text

### Testing with RSpec

**Best practices:**

- Use `let` for test data setup
- Use `subject` for what's being tested
- Keep tests readable with descriptive strings
- Use `before` hooks sparingly
- One assertion per example when possible

### Rails-Specific (if using Rails)

**Follow Rails conventions:**

- Use ActiveRecord associations properly
- Avoid N+1 queries (use `includes`, `joins`)
- Use scopes for reusable queries
- Keep controllers thin, models fat (but not too fat)
- Use service objects for complex business logic

### Common Anti-Patterns

**Avoid:**

- Monkey-patching core classes (use refinements if needed)
- Overusing class variables (`@@var`)
- Ignoring exceptions silently
- Using `eval` (security risk)
- Long method chains that are hard to debug
