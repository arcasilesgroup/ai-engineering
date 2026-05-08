# Example — Kotlin sealed class for state

Demonstrates: sealed class for finite state, exhaustive `when`,
data class for payloads, no `!!`, Result<T> for error paths.

```kotlin
// app/src/main/kotlin/com/example/markets/Market.kt
package com.example.markets

sealed interface MarketResult {
    data class Loaded(val market: Market) : MarketResult
    data object NotFound : MarketResult
    data class Failed(val cause: Throwable) : MarketResult
}

enum class MarketError {
    EmptySymbol,
    SymbolTooLong,
    SymbolNonLetter,
}

class MarketException(val error: MarketError)
    : RuntimeException(error.name)

data class Market(val symbol: String, val lastPrice: Double) {
    init {
        require(symbol.isNotBlank()) { throw MarketException(MarketError.EmptySymbol) }
        require(symbol.length <= 10) { throw MarketException(MarketError.SymbolTooLong) }
        require(symbol.all { it.isLetter() && it.code <= 0x7F }) {
            throw MarketException(MarketError.SymbolNonLetter)
        }
    }

    companion object {
        fun create(symbol: String, lastPrice: Double): Result<Market> = runCatching {
            Market(symbol.trim().uppercase(), lastPrice)
        }
    }
}
```

```kotlin
// app/src/test/kotlin/com/example/markets/MarketTest.kt
package com.example.markets

import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class MarketTest {
    @Test
    fun `create rejects empty symbol`() {
        val result = Market.create("", 1.0)
        assertTrue(result.isFailure)
        val ex = assertThrows<MarketException> { result.getOrThrow() }
        assertEquals(MarketError.EmptySymbol, ex.error)
    }

    @Test
    fun `create normalises symbol`() {
        val m = Market.create("btc", 1.0).getOrThrow()
        assertEquals("BTC", m.symbol)
    }
}
```

## Exhaustive `when` over sealed result

```kotlin
fun describe(result: MarketResult): String = when (result) {
    is MarketResult.Loaded -> "Loaded ${result.market.symbol}"
    is MarketResult.Failed -> "Error: ${result.cause.message}"
    MarketResult.NotFound -> "Not found"
}
```
