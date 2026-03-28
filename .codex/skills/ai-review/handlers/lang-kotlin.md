# Handler: Language -- Kotlin

## Purpose

Language-specific review for Kotlin code, with emphasis on Android/KMP architecture. Supplements the 8-concern review agents with clean architecture boundary enforcement, coroutine safety, Compose stability checks, and Android security patterns.

## Integration

Dispatched as **Step 2b** (between Step 2 dispatch and Step 3 aggregate). Findings use the same YAML format. Language findings receive a **+10% confidence bonus** when corroborated by a concern agent.

## Procedure

### Step 1 -- Detect Kotlin Scope

1. Identify `.kt`, `.kts` files in the diff
2. If no Kotlin files, skip this handler entirely
3. Detect project type from build files and imports:
   - `build.gradle.kts` with `com.android.application` -> Android app
   - `build.gradle.kts` with `com.android.library` -> Android library
   - `@Composable` imports -> enable Compose checks
   - `kotlinx.coroutines` imports -> enable coroutine checks
   - Multi-module project -> enable module boundary checks
4. Read `.ai-engineering/contexts/languages/kotlin.md` if not already loaded
5. Map module structure: identify `domain`, `data`, `presentation`, `app` modules

### Step 2 -- Critical Findings (severity: critical)

**Domain module importing framework**
```kotlin
// BAD: domain module depends on Android/framework
// In domain/src/main/kotlin/com/example/domain/usecase/GetUserUseCase.kt
import android.content.Context         // framework leak
import androidx.lifecycle.ViewModel    // presentation concern
import retrofit2.Response              // data layer concern

// GOOD: domain depends only on Kotlin stdlib and domain interfaces
import com.example.domain.repository.UserRepository
import com.example.domain.model.User
```
- Scan import statements in files under `domain/` module paths
- Confidence 95%: this is a fundamental architecture violation

**Data entities leaking to presentation layer**
```kotlin
// BAD: API/DB entity used directly in UI
@Composable
fun UserScreen(user: UserApiResponse) {  // data layer type in UI

// GOOD: mapped to domain/presentation model
@Composable
fun UserScreen(user: UserUiModel) {
```
- Flag data-layer types (`Entity`, `Dto`, `Response`, `ApiModel`) in Composable parameters or ViewModel state

**Business logic in ViewModel**
```kotlin
// BAD: ViewModel contains business rules
class OrderViewModel : ViewModel() {
    fun placeOrder(items: List<Item>) {
        val total = items.sumOf { it.price * it.quantity }
        val tax = total * 0.21  // business rule!
        val discount = if (total > 100) total * 0.1 else 0.0  // business rule!
        // ...
    }
}

// GOOD: delegated to use case
class OrderViewModel(
    private val placeOrderUseCase: PlaceOrderUseCase
) : ViewModel() {
    fun placeOrder(items: List<Item>) {
        viewModelScope.launch {
            placeOrderUseCase(items)
        }
    }
}
```
- Flag: calculations, conditionals, data transformations beyond simple UI state mapping

**Circular module dependencies**
- Module A imports from Module B AND Module B imports from Module A
- Check `build.gradle.kts` `dependencies` blocks and import statements across modules

### Step 3 -- High Findings (severity: major)

**GlobalScope usage**
```kotlin
// BAD: unstructured concurrency, outlives lifecycle
GlobalScope.launch {
    fetchData()
}

// GOOD: structured concurrency
viewModelScope.launch {
    fetchData()
}
// or
lifecycleScope.launch {
    fetchData()
}
// or inject a CoroutineScope
```

**Catching CancellationException without rethrow**
```kotlin
// BAD: breaks structured concurrency cancellation
try {
    suspendingWork()
} catch (e: Exception) {
    // CancellationException is caught here!
    logger.error("Failed", e)
}

// GOOD: rethrow CancellationException
try {
    suspendingWork()
} catch (e: CancellationException) {
    throw e  // must rethrow!
} catch (e: Exception) {
    logger.error("Failed", e)
}

// ALSO GOOD: use runCatching carefully
runCatching { suspendingWork() }
    .onFailure { e ->
        if (e is CancellationException) throw e
        logger.error("Failed", e)
    }
```
- Confidence 85%: catching `Exception` or `Throwable` in a suspend function almost always catches `CancellationException`

**Compose unstable parameters**
```kotlin
// BAD: lambda causes recomposition every time
@Composable
fun ItemList(items: List<Item>, onClick: (Item) -> Unit) {
    // List and lambda are unstable -> recomposes every parent recomposition
}

// GOOD: stable types
@Composable
fun ItemList(items: ImmutableList<Item>, onClick: (Item) -> Unit) {
    // ImmutableList is stable; lambda should be remembered at call site
}
```
- Flag `List`, `Map`, `Set` parameters in Composable functions (use `kotlinx.collections.immutable`)

**NavController passed deep into composable tree**
```kotlin
// BAD: tight coupling to navigation
@Composable
fun UserCard(user: User, navController: NavController) {
    Button(onClick = { navController.navigate("details/${user.id}") })
}

// GOOD: event callback
@Composable
fun UserCard(user: User, onNavigateToDetails: (String) -> Unit) {
    Button(onClick = { onNavigateToDetails(user.id) })
}
```

**remember {} missing keys**
```kotlin
// BAD: stale computation when input changes
val formatted = remember { formatCurrency(amount) }

// GOOD: recomputes when amount changes
val formatted = remember(amount) { formatCurrency(amount) }
```

### Step 4 -- Medium Findings (severity: minor)

**!! (non-null assertion) overuse**
```kotlin
// BAD: crash if null
val name = user!!.name

// GOOD: safe handling
val name = user?.name ?: "Unknown"
```
- Confidence 70% in production code, 40% in test code
- Acceptable after explicit null check in the same scope

**Java-style patterns in Kotlin**
- `getInstance()` singleton -> `object` declaration
- JavaBean getters/setters -> Kotlin properties
- `static` utility class -> top-level functions or `object`
- `StringBuilder` manual building -> string templates

**Hardcoded strings in UI**
```kotlin
// BAD: not localizable
Text("Submit Order")

// GOOD: string resource
Text(stringResource(R.string.submit_order))
```

**Missing sealed class/interface for state modeling**
- Multiple boolean flags (`isLoading`, `isError`, `hasData`) instead of sealed state hierarchy

### Step 5 -- Android Security Checks

**Exported components without permission protection**
```xml
<!-- BAD: any app can start this -->
<activity android:name=".DeepLinkActivity" android:exported="true" />

<!-- GOOD: protected -->
<activity
    android:name=".DeepLinkActivity"
    android:exported="true"
    android:permission="com.example.DEEP_LINK" />
```
- Check `AndroidManifest.xml` for `exported="true"` without `permission` attribute

**WebView JavaScript bridge exposure**
```kotlin
// BAD: exposes Kotlin objects to JS
webView.addJavascriptInterface(bridge, "Android")
webView.settings.javaScriptEnabled = true

// Requires: validate URL before enabling JS, restrict interface methods with @JavascriptInterface
```
- Confidence 80% if URL is not validated before loading

**Cleartext traffic in production**
- `android:usesCleartextTraffic="true"` in manifest
- HTTP URLs in network calls without TLS

### Step 6 -- Diagnostic Tool Cross-Reference

| Tool | Command | Validates |
|------|---------|-----------|
| ktlint | `ktlint --reporter=json` | Code style findings |
| detekt | `detekt --report xml` | Complexity, style, potential bugs |
| Android Lint | `./gradlew lint` | Android-specific issues |
| Dependency Check | `./gradlew dependencyCheckAnalyze` | Vulnerable dependencies |

If a diagnostic tool contradicts a finding, note the discrepancy and adjust confidence accordingly.

## Output Format

```yaml
findings:
  - id: lang-kotlin-N
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
