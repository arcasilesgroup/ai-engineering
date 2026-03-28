# Handler: Language -- Flutter/Dart

## Purpose

Language-specific review for Flutter and Dart code. Supplements the 8-concern review agents with state management agnostic checks (BLoC, Riverpod, GetX), widget composition patterns, resource lifecycle management, accessibility enforcement, and i18n readiness.

## Integration

Dispatched as **Step 2b** (between Step 2 dispatch and Step 3 aggregate). Findings use the same YAML format. Language findings receive a **+10% confidence bonus** when corroborated by a concern agent.

## Procedure

### Step 1 -- Detect Flutter Scope

1. Identify `.dart` files in the diff
2. If no Dart files, skip this handler entirely
3. Check `pubspec.yaml` for dependencies:
   - `flutter_bloc` / `bloc` -> BLoC state management context
   - `flutter_riverpod` / `riverpod` -> Riverpod context
   - `get` / `getx` -> GetX context
   - `provider` -> Provider context
4. Detect architecture from directory structure:
   - `lib/domain/`, `lib/data/`, `lib/presentation/` -> clean architecture
   - `lib/features/` -> feature-first organization
5. Read `.ai-engineering/contexts/languages/dart.md` or `flutter.md` if not already loaded

### Step 2 -- Critical Findings (severity: critical)

**Boolean flag soup instead of sealed state**
```dart
// BAD: combinatorial explosion, impossible states representable
class UserState {
  final bool isLoading;
  final bool isError;
  final bool hasData;
  final String? errorMessage;
  final User? user;
  // Can represent isLoading=true AND isError=true -- nonsensical!
}

// GOOD: sealed class makes impossible states unrepresentable
sealed class UserState {}
class UserInitial extends UserState {}
class UserLoading extends UserState {}
class UserLoaded extends UserState {
  final User user;
  UserLoaded(this.user);
}
class UserError extends UserState {
  final String message;
  UserError(this.message);
}
```
- Flag: classes with 2+ boolean state flags (`isLoading`, `isError`, `hasData`, `isEmpty`)
- Confidence 85%: nearly always a design problem

**Non-exhaustive state handling**
```dart
// BAD: misses states silently
Widget build(BuildContext context) {
  if (state is UserLoading) return CircularProgressIndicator();
  if (state is UserLoaded) return UserView(state.user);
  return SizedBox.shrink();  // silently swallows errors!
}

// GOOD: exhaustive switch (Dart 3+)
Widget build(BuildContext context) {
  return switch (state) {
    UserInitial() => const Text('Welcome'),
    UserLoading() => const CircularProgressIndicator(),
    UserLoaded(:final user) => UserView(user: user),
    UserError(:final message) => ErrorView(message: message),
  };
}
```
- Flag: if/else chains or switch without exhaustive state coverage

**Stream and subscription leaks**
```dart
// BAD: never cancelled
class MyWidget extends StatefulWidget {
  @override
  State<MyWidget> createState() => _MyWidgetState();
}
class _MyWidgetState extends State<MyWidget> {
  @override
  void initState() {
    super.initState();
    stream.listen((data) {  // never cancelled!
      setState(() => _data = data);
    });
  }
}

// GOOD: cancel in dispose
class _MyWidgetState extends State<MyWidget> {
  late final StreamSubscription _subscription;

  @override
  void initState() {
    super.initState();
    _subscription = stream.listen((data) {
      setState(() => _data = data);
    });
  }

  @override
  void dispose() {
    _subscription.cancel();
    super.dispose();
  }
}
```
- Flag: `.listen()` without corresponding `.cancel()` in `dispose()`
- Flag: `StreamController` created without `.close()` in `dispose()`
- Flag: `AnimationController`, `TextEditingController`, `ScrollController` without `dispose()`

**.listen() called inside build()**
```dart
// BAD: creates new subscription every rebuild
@override
Widget build(BuildContext context) {
  stream.listen((data) {  // called every rebuild!
    setState(() {});
  });
  return Container();
}

// GOOD: listen in initState or use StreamBuilder
@override
Widget build(BuildContext context) {
  return StreamBuilder<Data>(
    stream: stream,
    builder: (context, snapshot) => /* ... */,
  );
}
```

**Domain layer importing Flutter**
```dart
// BAD: domain depends on framework
import 'package:flutter/material.dart';  // in domain/

// Domain should only import dart:core, dart:async, dart:collection
// and other domain-layer packages
```
- Scan files under `lib/domain/` for `package:flutter/` imports

### Step 3 -- High Findings (severity: major)

**_build helper methods instead of widget extraction**
```dart
// BAD: private build methods prevent framework optimization
class MyWidget extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(children: [
      _buildHeader(),   // cannot be independently rebuilt
      _buildContent(),  // no separate Element in widget tree
    ]);
  }

  Widget _buildHeader() => /* ... */;
  Widget _buildContent() => /* ... */;
}

// GOOD: extract to separate widgets
class MyWidget extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(children: [
      HeaderWidget(),   // separate Element, independent rebuild
      ContentWidget(),  // framework can skip if unchanged
    ]);
  }
}
```
- Flag `_build*()` methods that return `Widget` -- recommend extraction to separate widget classes

**Missing const constructors**
```dart
// BAD: rebuilt unnecessarily
return Padding(
  padding: EdgeInsets.all(16),
  child: Text('Hello'),
);

// GOOD: const enables compile-time optimization
return const Padding(
  padding: EdgeInsets.all(16),
  child: Text('Hello'),
);
```
- Flag widget constructors that could be `const` but are not
- Flag custom widget classes missing `const` constructor when all fields are final

**MediaQuery.of overuse causing unnecessary rebuilds**
```dart
// BAD: rebuilds on ANY MediaQuery change (keyboard, orientation, etc.)
final width = MediaQuery.of(context).size.width;

// GOOD: targeted query (Flutter 3.10+)
final width = MediaQuery.sizeOf(context).width;
// Even better for specific properties:
final padding = MediaQuery.paddingOf(context);
```

**BuildContext used after await**
```dart
// BAD: context may be invalid after async gap
onPressed: () async {
  await fetchData();
  if (!mounted) return;  // required check!
  Navigator.of(context).push(/* ... */);
}

// GOOD: check mounted
onPressed: () async {
  await fetchData();
  if (!context.mounted) return;  // Dart 3.7+
  Navigator.of(context).push(/* ... */);
}
```

**Missing ErrorBoundary-equivalent setup**
- No `ErrorWidget.builder` override for release mode
- No `FlutterError.onError` handler configured
- No `PlatformDispatcher.instance.onError` for async errors

### Step 4 -- Medium Findings (severity: minor)

**! bang operator overuse**
```dart
// BAD: crash on null
final name = user!.name;

// GOOD: safe access
final name = user?.name ?? 'Unknown';
```
- Confidence 70% in widget code, 50% in test code
- Acceptable immediately after null check in same scope

**Overly broad catch**
```dart
// BAD: swallows everything
try {
  await fetchData();
} catch (e) {
  // catches TypeError, RangeError, everything
}

// GOOD: specific exceptions
try {
  await fetchData();
} on NetworkException catch (e) {
  showError(e.message);
} on TimeoutException {
  showRetryDialog();
}
```

**late overuse**
```dart
// BAD: runtime error if accessed before initialization
late final UserService _userService;

// GOOD: nullable with explicit initialization check, or constructor injection
final UserService? _userService;
// or
required this.userService  // constructor parameter
```
- Flag `late` fields that could be constructor parameters or nullable

**Unawaited futures**
```dart
// BAD: fire and forget, errors silently lost
fetchData();  // returns Future but not awaited

// GOOD: explicit
await fetchData();
// or intentionally fire-and-forget with annotation
unawaited(analytics.track('event'));
```

### Step 5 -- Accessibility Checks

**Missing semantic labels**
```dart
// BAD: icon button with no semantic meaning for screen readers
IconButton(
  icon: Icon(Icons.delete),
  onPressed: _deleteItem,
)

// GOOD: semantic label
IconButton(
  icon: Icon(Icons.delete),
  onPressed: _deleteItem,
  tooltip: 'Delete item',  // also serves as semantic label
)
// or
Semantics(
  label: 'Delete item',
  child: IconButton(/* ... */),
)
```

**Tap targets below 48x48**
```dart
// BAD: too small for accessibility
SizedBox(
  width: 24,
  height: 24,
  child: GestureDetector(onTap: _handleTap),
)

// GOOD: minimum 48x48 logical pixels
SizedBox(
  width: 48,
  height: 48,
  child: GestureDetector(onTap: _handleTap),
)
```
- Flag interactive widgets (`GestureDetector`, `InkWell`, `IconButton`) with explicit size constraints below 48x48

### Step 6 -- Internationalization Checks

**Hardcoded strings in UI**
```dart
// BAD: not localizable
Text('Submit Order')
AppBar(title: Text('Settings'))

// GOOD: localized
Text(AppLocalizations.of(context)!.submitOrder)
// or with intl package
Text(S.of(context).submitOrder)
```
- Flag string literals passed directly to `Text()`, `AppBar(title:)`, tooltip, label, hint parameters
- Acceptable: debug widgets, developer-facing strings, log messages

### Step 7 -- Diagnostic Tool Cross-Reference

| Tool | Command | Validates |
|------|---------|-----------|
| dart analyze | `dart analyze` | Type safety, unused imports, style |
| flutter test | `flutter test --coverage` | Test coverage |
| dart fix | `dart fix --dry-run` | Automated fix suggestions |
| custom_lint | Per `analysis_options.yaml` | Project-specific rules |

If a diagnostic tool contradicts a finding, note the discrepancy and adjust confidence accordingly.

## Output Format

```yaml
findings:
  - id: lang-flutter-N
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
