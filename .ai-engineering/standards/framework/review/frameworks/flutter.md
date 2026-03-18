# Flutter Review Guidelines

## Update Metadata
- Rationale: Flutter-specific patterns for widgets, state management, and platform integration.

## Widget Patterns
- Keep `build()` methods lean — extract sub-widgets for complex UI.
- Use `const` constructors wherever possible for performance.
- Prefer `StatelessWidget` over `StatefulWidget` when no state needed.
- Use `Key` for list items that change order.

## State Management
- Use `Riverpod` or `Bloc` for complex state — avoid `setState()` in large widgets.
- Keep state close to where it's used — don't lift unnecessarily.
- Use `AsyncValue` pattern for loading/error/data states.

## Performance
- Use `ListView.builder()` for long lists — never `ListView(children: [...])`.
- Avoid rebuilding expensive widgets — use `const`, `RepaintBoundary`.
- Profile with Flutter DevTools before optimizing.

## Platform Integration
- Use `Platform.isAndroid` / `Platform.isIOS` for platform-specific code.
- Use `MethodChannel` for native communication — validate responses.
- Handle permissions gracefully with fallback UI.

## References
- Enforcement: `standards/framework/stacks/flutter.md` (if exists)
