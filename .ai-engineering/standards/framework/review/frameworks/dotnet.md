# .NET General Review Guidelines

## Update Metadata
- Rationale: Cross-framework .NET patterns for WPF, MAUI, Blazor, and general .NET.

## Patterns
- Use nullable reference types project-wide.
- Prefer `Span<T>` and `Memory<T>` for performance-critical buffer operations.
- Use `IAsyncDisposable` with `await using` for async resource cleanup.
- Channel<T> for producer-consumer patterns.

## Blazor Specific
- Use `@key` directive for list rendering performance.
- Minimize JS interop calls — batch when possible.
- Use cascading parameters judiciously — they re-render entire subtrees.

## MAUI / WPF Specific
- Use MVVM pattern with data binding.
- Avoid code-behind for business logic.
- Use `ObservableCollection<T>` for dynamic lists.

## References
- Enforcement: `standards/framework/stacks/dotnet.md`
