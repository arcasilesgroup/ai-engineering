## Elixir Best Practices

### Functional Patterns

**Embrace immutability:**

- Data structures are immutable
- Use pattern matching instead of conditionals
- Chain transformations with pipe operator `|>`
- Avoid mutable state (use processes for state)

**Pattern:**

```elixir
# ✅ GOOD: Pattern matching and pipes
def process_user(%User{active: true} = user) do
  user
  |> update_last_seen()
  |> send_notification()
  |> save()
end

# ❌ BAD: Imperative style
def process_user(user) do
  if user.active == true do
    user2 = update_last_seen(user)
    user3 = send_notification(user2)
    save(user3)
  end
end
```text

### Pattern Matching

**Use pattern matching everywhere:**

- Function clauses for different cases
- Case statements for complex matching
- With statements for sequential operations
- Destructuring in function parameters

**Pattern:**

```elixir
# ✅ GOOD: Pattern matching in function clauses
def format({:ok, value}), do: "Success: #{value}"
def format({:error, reason}), do: "Error: #{reason}"

# ✅ GOOD: With for sequential operations
with {:ok, user} <- find_user(id),
     {:ok, profile} <- load_profile(user),
     {:ok, settings} <- load_settings(profile) do
  {:ok, {user, profile, settings}}
end
```text

### Error Handling

**Use tagged tuples:**

- Return `{:ok, result}` or `{:error, reason}`
- Use `!` suffix for functions that raise: `fetch!`
- Pattern match on results
- Use `case` or `with` for error handling

**Pattern:**

```elixir
# ✅ GOOD: Tagged tuple pattern
def find_user(id) do
  case Repo.get(User, id) do
    nil -> {:error, :not_found}
    user -> {:ok, user}
  end
end

# ✅ Usage
case find_user(id) do
  {:ok, user} -> process(user)
  {:error, :not_found} -> handle_not_found()
end
```text

### Process and GenServer

**Use OTP behaviors:**

- GenServer for stateful processes
- Task for concurrent one-off operations
- Agent for simple state management
- Supervisor for fault tolerance

**Pattern:**

```elixir
# ✅ GOOD: GenServer for state
defmodule Cache do
  use GenServer

  def start_link(opts) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def get(key) do
    GenServer.call(__MODULE__, {:get, key})
  end

  # Callbacks
  def init(_opts), do: {:ok, %{}}

  def handle_call({:get, key}, _from, state) do
    {:reply, Map.get(state, key), state}
  end
end
```text

### Naming Conventions

**Elixir style:**

- `snake_case` for atoms, functions, variables, modules files
- `PascalCase` for module names: `MyApp.UserController`
- `?` suffix for boolean functions: `empty?/1`
- `!` suffix for raising functions: `fetch!/1`
- Underscores for unused variables: `_unused`

### Pipe Operator

**Effective piping:**

- Start with data, transform step by step
- Each function takes previous result as first argument
- Keep pipes readable (break into multiple lines)
- Use parentheses for clarity with multiple arguments

**Pattern:**

```elixir
# ✅ GOOD: Clear pipeline
result =
  user_params
  |> validate_params()
  |> create_user()
  |> send_welcome_email()
  |> update_metrics()

# ❌ BAD: Nested function calls
result = update_metrics(
  send_welcome_email(
    create_user(
      validate_params(user_params)
    )
  )
)
```text

### Structs and Maps

**When to use each:**

- Structs for domain data with known keys
- Maps for dynamic data
- Use `@enforce_keys` for required struct fields
- Pattern match on structs for type safety

**Pattern:**

```elixir
defmodule User do
  @enforce_keys [:email]
  defstruct [:email, :name, active: false]
end

# ✅ Pattern match on struct
def greet(%User{name: name}) when not is_nil(name) do
  "Hello, #{name}!"
end
```text

### Guards and Functions

**Use guards for simple conditions:**

- Guards must be pure and limited functions
- Use multiple function clauses instead of if/else
- Order specific clauses before general ones

**Pattern:**

```elixir
# ✅ GOOD: Guards and multiple clauses
def classify(n) when n < 0, do: :negative
def classify(0), do: :zero
def classify(n) when n > 0, do: :positive

# ❌ BAD: Using if/else
def classify(n) do
  if n < 0 do
    :negative
  else
    if n == 0 do
      :zero
    else
      :positive
    end
  end
end
```text

### Avoid Common Pitfalls

**Enumerable vs Stream:**

- Use `Enum` for small collections
- Use `Stream` for lazy evaluation and large/infinite data
- Streams don't execute until consumed

**Process lifecycle:**

- Link processes that should fail together
- Monitor processes you want to observe
- Use supervisors for automatic restart
- Don't leak processes (always clean up)

### Module Organization

**Best practices:**

- One module per file (matching file name)
- Use `alias` to shorten module names
- Group `use`, `import`, `alias`, `require` at top
- Keep modules focused and cohesive

**Pattern:**

```elixir
defmodule MyApp.UserController do
  use MyApp.Web, :controller

  alias MyApp.{User, Repo}
  import Ecto.Query

  # Functions below
end
```text

### Testing with ExUnit

**Best practices:**

- Use `describe` blocks for grouping
- Use `setup` for test data preparation
- Use `async: true` when tests are independent
- Test tagged tuples explicitly

**Pattern:**

```elixir
defmodule UserTest do
  use ExUnit.Case, async: true

  describe "create_user/1" do
    test "returns {:ok, user} with valid params" do
      params = %{email: "test@example.com"}
      assert {:ok, %User{}} = User.create(params)
    end

    test "returns {:error, changeset} with invalid params" do
      assert {:error, %Ecto.Changeset{}} = User.create(%{})
    end
  end
end
```text

### Common Anti-Patterns

**Avoid:**

- Using processes for non-concurrent work
- Returning different types from same function
- Large `if`/`else` chains (use pattern matching)
- String keys in maps (use atoms for known keys)
- Overusing macros (use functions when possible)
- Ignoring supervisor trees (always supervise processes)
