# Example — Jetpack Compose ViewModel

Demonstrates: `StateFlow` for state, `viewModelScope` for coroutines,
`Result<T>` for fallible loads, structured concurrency, no
`!!` or `runBlocking`.

```kotlin
// app/src/main/kotlin/com/example/markets/MarketsViewModel.kt
package com.example.markets

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed interface MarketsUiState {
    data object Idle : MarketsUiState
    data object Loading : MarketsUiState
    data class Loaded(val markets: List<Market>) : MarketsUiState
    data class Failed(val message: String) : MarketsUiState
}

class MarketsViewModel(private val repo: MarketRepository) : ViewModel() {
    private val _state = MutableStateFlow<MarketsUiState>(MarketsUiState.Idle)
    val state: StateFlow<MarketsUiState> = _state.asStateFlow()

    fun load() {
        _state.value = MarketsUiState.Loading
        viewModelScope.launch {
            _state.value = repo.fetchAll().fold(
                onSuccess = { MarketsUiState.Loaded(it) },
                onFailure = { MarketsUiState.Failed(it.message ?: "unknown") },
            )
        }
    }
}
```

```kotlin
// app/src/main/kotlin/com/example/markets/MarketsScreen.kt
package com.example.markets

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Modifier

@Composable
fun MarketsScreen(viewModel: MarketsViewModel) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.load() }

    when (val s = state) {
        MarketsUiState.Idle, MarketsUiState.Loading -> CircularProgressIndicator()
        is MarketsUiState.Loaded -> LazyColumn {
            items(s.markets) { m ->
                ListItem(
                    headlineContent = { Text(m.symbol) },
                    supportingContent = { Text("${m.lastPrice}") },
                )
            }
        }
        is MarketsUiState.Failed -> Text("Error: ${s.message}")
    }
}
```

## TDD pairing — testing the ViewModel

```kotlin
// app/src/test/kotlin/com/example/markets/MarketsViewModelTest.kt
package com.example.markets

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import kotlin.test.assertEquals

class MarketsViewModelTest {
    private val dispatcher = UnconfinedTestDispatcher()

    @BeforeEach fun setup() = Dispatchers.setMain(dispatcher)
    @AfterEach fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `load sets Loaded on success`() = runTest {
        val market = Market.create("BTC", 1.0).getOrThrow()
        val repo = object : MarketRepository {
            override suspend fun fetchAll() = Result.success(listOf(market))
        }
        val vm = MarketsViewModel(repo)
        vm.load()
        assertEquals(MarketsUiState.Loaded(listOf(market)), vm.state.value)
    }
}
```
