# Analysis Playbook

On-demand reference for the explain skill. Load selectively by heading.

## Diagram Templates

### ASCII: Data Flow

```
  +---------+     +-----------+     +--------+
  |  Input  | --> | Processor | --> | Output |
  +---------+     +-----------+     +--------+
                       |
                       v
                  +---------+
                  |  Store  |
                  +---------+
```

- Use boxes (`+--+`) for components, arrows (`-->`, `|`, `v`) for flow.
- Label arrows when the transformation matters.
- Keep width under 70 characters for terminal readability.

### ASCII: Call Chain

```
  main()
    -> validate_input(data)
         -> parse_schema(raw)      returns Schema
         <- Schema
    -> process(schema)
         -> transform(item)        returns Result
         <- Result
    <- FinalOutput
```

- Indent to show depth. Use `->` for calls, `<-` for returns.
- Annotate return types when they clarify the flow.

### ASCII: State Machine

```
  [Idle] --start--> [Running] --complete--> [Done]
    ^                  |
    |                  |--error-->  [Failed]
    |                                 |
    +----------retry------------------+
```

- Use `[State]` for states, `--label-->` for transitions.
- Show error and recovery paths explicitly.

### ASCII: Component Layout

```
  +----------------+
  |   API Layer    |
  +-------+--------+
          |
  +-------v--------+     +-------------+
  | Business Logic |---->| Event Bus   |
  +-------+--------+     +------+------+
          |                      |
  +-------v--------+     +------v------+
  |   Data Access  |     |  Consumers  |
  +----------------+     +-------------+
```

- Show dependency direction with arrows.
- Group related components visually.

### ASCII: Sequence

```
  Client          Server          Database
    |                |                |
    |-- POST /api -->|                |
    |                |-- INSERT -->   |
    |                |   <-- OK --    |
    |<-- 201 --------|                |
    |                |                |
```

- Columns for participants, `--label-->` for messages.
- Time flows downward. Align columns for readability.

## Complexity Analysis Patterns

### Cyclomatic Complexity

- Count independent paths through the code: `if`, `elif`, `else`, `for`, `while`, `except`, `and`, `or`, ternary.
- Thresholds: 1-10 simple, 11-20 moderate, 21-50 complex, >50 untestable.
- Report as: "Cyclomatic complexity: ~N (moderate/complex)."

### Nesting Depth

- Max recommended: 4 levels. Beyond 4 signals extract-method refactoring.
- Count: function body = 0, each `if`/`for`/`with`/`try` adds 1.
- Report deepest path and what contributes to it.

### Performance Characteristics

- Time complexity: state Big-O for the hot path.
- Space complexity: note allocations in loops, growing collections.
- Hot paths: identify the most-executed code path and its cost.
- Allocation patterns: repeated object creation, string concatenation in loops.

## Concurrency Analysis

### Thread Safety

- Shared mutable state: identify variables accessed by multiple threads/coroutines.
- Synchronization: locks, semaphores, atomics, channels — note presence or absence.
- Race conditions: read-modify-write without protection, check-then-act patterns.
- Deadlock potential: nested locks, lock ordering violations.

### Async Pitfalls

- Unhandled promises/tasks: fire-and-forget without error handling.
- Blocking in async context: synchronous I/O in async functions.
- Starvation: long-running tasks monopolizing the event loop.
- Cancellation: tasks that don't respect cancellation tokens/signals.

## Edge Case Catalog

Common pitfalls to check when analyzing code:

- **Null/None**: unhandled None returns, Optional without guard.
- **Empty collections**: `.first()` on empty list, iteration assumptions.
- **Boundary values**: off-by-one, integer overflow, max/min values.
- **String encoding**: UTF-8 assumptions, multi-byte characters, locale.
- **Timezone**: naive vs aware datetimes, DST transitions, UTC assumptions.
- **Float precision**: equality comparison, accumulated rounding, currency.
- **Concurrency**: TOCTOU races, stale reads, partial writes.
- **Resource exhaustion**: unbounded queues, memory leaks, file handle leaks.
