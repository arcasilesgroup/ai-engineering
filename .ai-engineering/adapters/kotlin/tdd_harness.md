# Kotlin — TDD Harness

`ai-build` runs RED → GREEN → REFACTOR through JUnit 5 by default,
with `kotest` available for repos that prefer assertion DSLs. Tests
are deterministic and never reach the network.

## Runner

- **Default**: JUnit 5 (`org.junit.jupiter`) — universally supported,
  Gradle-native.
- **Optional**: `kotest` (`io.kotest.runner:kotest-runner-junit5`)
  for spec-style tests + property-based testing.
- Forbid: legacy JUnit 4 in new code.

## Layout

```
src/test/kotlin/com/example/markets/MarketTest.kt
src/main/kotlin/com/example/markets/Market.kt
```

- Mirror the source package in `src/test/`.
- Resources / fixtures under `src/test/resources/`; loaded via
  `Class.getResource`.

## Naming

- File: `<Unit>Test.kt`.
- Class: `class <Unit>Test`.
- Method (JUnit 5): `` fun `init throws on empty symbol`() `` —
  backtick-quoted descriptions for readable failure output.
- Method (kotest spec style): `"init throws on empty symbol" { ... }`.

## RED → GREEN → REFACTOR

1. **RED** — write the failing test. Run
   `./gradlew :app:test --tests "com.example.markets.MarketTest.init throws on empty symbol"`.
   Confirm the failure message matches the assertion.
2. **GREEN** — minimum implementation. Do not modify the test.
3. **REFACTOR** — clean up; suite stays green.

## JUnit 5 patterns

```kotlin
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import kotlin.test.assertEquals

class MarketTest {
    @Test
    fun `init throws on empty symbol`() {
        val ex = assertThrows<MarketException> { Market("", 1.0) }
        assertEquals(MarketError.EmptySymbol, ex.error)
    }
}
```

## Parameterised (`@ParameterizedTest`)

```kotlin
import org.junit.jupiter.params.ParameterizedTest
import org.junit.jupiter.params.provider.CsvSource
import kotlin.test.assertEquals

class MarketParamTest {
    @ParameterizedTest
    @CsvSource("btc, BTC", "' eth ', ETH")
    fun `normalises symbol`(input: String, expected: String) {
        val m = Market(input, 1.0)
        assertEquals(expected, m.symbol)
    }
}
```

## Coroutine tests

```kotlin
import kotlinx.coroutines.test.runTest

@Test
fun `load returns market`() = runTest {
    val m = repo.load("id-1")
    assertEquals("BTC", m.symbol)
}
```

## kotest example

```kotlin
import io.kotest.core.spec.style.StringSpec
import io.kotest.matchers.shouldBe

class MarketSpec : StringSpec({
    "normalises lowercase symbol" {
        Market("btc", 1.0).symbol shouldBe "BTC"
    }
})
```

## Mocks / fakes

- **Default**: hand-rolled fakes for small interfaces.
- **When justified**: `mockk` (Kotlin-native) — preferred over Mockito
  for new code.
- For Android: `Robolectric` only when an actual instrumentation test
  would over-cost.

## Coverage

- `./gradlew :app:jacocoTestReport`.
- Floor: 80 % statement coverage on touched files.
