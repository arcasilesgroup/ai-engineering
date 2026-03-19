## Android Development Best Practices

### Project Structure

**Organize by feature:**

- Use feature modules
- Separate presentation, domain, data layers
- Follow clean architecture principles
- Use Gradle modules for large projects

**Pattern:**

```text
app/
  src/
    main/
      java/com/example/app/
        features/
          user/
            presentation/
              UserViewModel.kt
              UserFragment.kt
            domain/
              User.kt
              UserRepository.kt
            data/
              UserRepositoryImpl.kt
              UserDao.kt
        core/
          network/
          database/
          di/
```text

### Jetpack Compose

**Modern UI with Compose:**

- Use composable functions
- Hoist state appropriately
- Use remember and rememberSaveable
- Keep composables pure

**Pattern:**

```kotlin
// ✅ GOOD: Stateless composable
@Composable
fun UserProfile(
    user: User,
    onEditClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(modifier = modifier.padding(16.dp)) {
        AsyncImage(
            model = user.avatarUrl,
            contentDescription = "User avatar",
            modifier = Modifier
                .size(80.dp)
                .clip(CircleShape)
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = user.name,
            style = MaterialTheme.typography.headlineMedium
        )

        Text(
            text = user.email,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Button(onClick = onEditClick) {
            Text("Edit Profile")
        }
    }
}

// ✅ GOOD: Stateful composable
@Composable
fun UserScreen(
    viewModel: UserViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    when (val state = uiState) {
        is UserUiState.Loading -> LoadingScreen()
        is UserUiState.Success -> UserProfile(
            user = state.user,
            onEditClick = viewModel::onEditClick
        )
        is UserUiState.Error -> ErrorScreen(state.message)
    }
}
```text

### ViewModel

**Android Architecture Components:**

- Extend ViewModel
- Use StateFlow or LiveData
- Handle configuration changes
- Don't hold Context or View references

**Pattern:**

```kotlin
// ✅ GOOD: ViewModel
@HiltViewModel
class UserViewModel @Inject constructor(
    private val userRepository: UserRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<UserUiState>(UserUiState.Loading)
    val uiState: StateFlow<UserUiState> = _uiState.asStateFlow()

    init {
        loadUser()
    }

    fun loadUser() {
        viewModelScope.launch {
            _uiState.value = UserUiState.Loading

            userRepository.getUser()
                .onSuccess { user ->
                    _uiState.value = UserUiState.Success(user)
                }
                .onFailure { error ->
                    _uiState.value = UserUiState.Error(error.message ?: "Unknown error")
                }
        }
    }

    fun onEditClick() {
        // Handle edit
    }
}

sealed interface UserUiState {
    object Loading : UserUiState
    data class Success(val user: User) : UserUiState
    data class Error(val message: String) : UserUiState
}
```text

### Dependency Injection

**Hilt for DI:**

- Use @Inject for dependencies
- Define modules with @Module
- Use @Singleton for app-level singletons
- Use @ViewModelScoped for ViewModel dependencies

**Pattern:**

```kotlin
// ✅ GOOD: Hilt module
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides
    @Singleton
    fun provideRetrofit(): Retrofit {
        return Retrofit.Builder()
            .baseUrl("https://api.example.com/")
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    @Provides
    @Singleton
    fun provideApiService(retrofit: Retrofit): ApiService {
        return retrofit.create(ApiService::class.java)
    }
}

@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {

    @Binds
    @Singleton
    abstract fun bindUserRepository(
        impl: UserRepositoryImpl
    ): UserRepository
}

// ✅ GOOD: Inject in ViewModel
@HiltViewModel
class UserViewModel @Inject constructor(
    private val userRepository: UserRepository,
    private val analyticsService: AnalyticsService
) : ViewModel()
```text

### Networking

**Retrofit + Coroutines:**

- Use suspend functions
- Handle errors properly
- Use sealed classes for results
- Implement retry logic

**Pattern:**

```kotlin
// ✅ GOOD: API service
interface ApiService {
    @GET("users/{id}")
    suspend fun getUser(@Path("id") id: String): User

    @POST("users")
    suspend fun createUser(@Body user: CreateUserRequest): User
}

// ✅ GOOD: Repository with error handling
class UserRepositoryImpl @Inject constructor(
    private val apiService: ApiService
) : UserRepository {

    override suspend fun getUser(id: String): Result<User> {
        return try {
            val user = apiService.getUser(id)
            Result.success(user)
        } catch (e: Exception) {
            when (e) {
                is HttpException -> {
                    if (e.code() == 404) {
                        Result.failure(UserNotFoundException(id))
                    } else {
                        Result.failure(e)
                    }
                }
                else -> Result.failure(e)
            }
        }
    }
}
```text

### Database

**Room for local storage:**

- Define entities with @Entity
- Create DAOs with @Dao
- Use suspend functions
- Handle migrations

**Pattern:**

```kotlin
// ✅ GOOD: Entity
@Entity(tableName = "users")
data class UserEntity(
    @PrimaryKey val id: String,
    val name: String,
    val email: String,
    @ColumnInfo(name = "created_at") val createdAt: Long
)

// ✅ GOOD: DAO
@Dao
interface UserDao {
    @Query("SELECT * FROM users WHERE id = :id")
    suspend fun getUser(id: String): UserEntity?

    @Query("SELECT * FROM users")
    fun getAllUsers(): Flow<List<UserEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertUser(user: UserEntity)

    @Delete
    suspend fun deleteUser(user: UserEntity)
}

// ✅ GOOD: Database
@Database(
    entities = [UserEntity::class],
    version = 1,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun userDao(): UserDao
}
```text

### Navigation

**Jetpack Navigation:**

- Define navigation graph
- Use type-safe arguments
- Handle deep links
- Use single Activity with Fragments or Compose

**Pattern:**

```kotlin
// ✅ GOOD: Navigation with Compose
@Composable
fun AppNavigation() {
    val navController = rememberNavController()

    NavHost(
        navController = navController,
        startDestination = "home"
    ) {
        composable("home") {
            HomeScreen(
                onNavigateToUser = { userId ->
                    navController.navigate("user/$userId")
                }
            )
        }

        composable(
            route = "user/{userId}",
            arguments = listOf(
                navArgument("userId") { type = NavType.StringType }
            )
        ) { backStackEntry ->
            val userId = backStackEntry.arguments?.getString("userId")
            UserScreen(userId = userId)
        }
    }
}
```text

### State Management

**Manage state properly:**

- Use StateFlow for data streams
- Use SavedStateHandle for process death
- Hoist state appropriately
- Use remember for composition-scoped state

**Pattern:**

```kotlin
// ✅ GOOD: StateFlow in ViewModel
class UserViewModel @Inject constructor(
    private val userRepository: UserRepository,
    private val savedStateHandle: SavedStateHandle
) : ViewModel() {

    private val _searchQuery = MutableStateFlow("")
    val searchQuery = _searchQuery.asStateFlow()

    val users: StateFlow<List<User>> = searchQuery
        .debounce(300)
        .flatMapLatest { query ->
            userRepository.searchUsers(query)
        }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = emptyList()
        )

    fun updateSearchQuery(query: String) {
        _searchQuery.value = query
        savedStateHandle["search_query"] = query
    }
}

// ✅ GOOD: State in Compose
@Composable
fun UserSearchScreen(viewModel: UserViewModel = hiltViewModel()) {
    val searchQuery by viewModel.searchQuery.collectAsState()
    val users by viewModel.users.collectAsState()

    Column {
        TextField(
            value = searchQuery,
            onValueChange = viewModel::updateSearchQuery,
            label = { Text("Search") }
        )

        LazyColumn {
            items(users) { user ->
                UserItem(user)
            }
        }
    }
}
```text

### Background Work

**WorkManager for deferrable work:**

- Use for guaranteed execution
- Chain workers
- Add constraints
- Handle retry

**Pattern:**

```kotlin
// ✅ GOOD: Worker
class SyncWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        return try {
            val repository = // Get from DI
            repository.syncData()
            Result.success()
        } catch (e: Exception) {
            if (runAttemptCount < 3) {
                Result.retry()
            } else {
                Result.failure()
            }
        }
    }
}

// ✅ GOOD: Schedule work
class SyncScheduler @Inject constructor(
    @ApplicationContext private val context: Context
) {
    fun scheduleSync() {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .setRequiresBatteryNotLow(true)
            .build()

        val syncRequest = PeriodicWorkRequestBuilder<SyncWorker>(
            repeatInterval = 1,
            repeatIntervalTimeUnit = TimeUnit.HOURS
        )
            .setConstraints(constraints)
            .build()

        WorkManager.getInstance(context)
            .enqueueUniquePeriodicWork(
                "sync",
                ExistingPeriodicWorkPolicy.KEEP,
                syncRequest
            )
    }
}
```text

### Testing

**Testing best practices:**

- Unit test ViewModels
- UI test with Compose testing
- Mock dependencies with MockK
- Test coroutines with TestDispatcher

**Pattern:**

```kotlin
// ✅ GOOD: ViewModel test
@ExperimentalCoroutinesApi
class UserViewModelTest {

    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    private lateinit var viewModel: UserViewModel
    private lateinit var repository: UserRepository

    @Before
    fun setup() {
        repository = mockk()
        viewModel = UserViewModel(repository)
    }

    @Test
    fun `loadUser success updates ui state`() = runTest {
        val user = User("123", "John", "john@example.com")
        coEvery { repository.getUser("123") } returns Result.success(user)

        viewModel.loadUser("123")

        val state = viewModel.uiState.value
        assertThat(state).isInstanceOf(UserUiState.Success::class.java)
        assertThat((state as UserUiState.Success).user).isEqualTo(user)
    }
}

// ✅ GOOD: Compose UI test
@Test
fun userProfile_displaysUserData() {
    val user = User("123", "John", "john@example.com")

    composeTestRule.setContent {
        UserProfile(
            user = user,
            onEditClick = {}
        )
    }

    composeTestRule
        .onNodeWithText("John")
        .assertIsDisplayed()

    composeTestRule
        .onNodeWithText("john@example.com")
        .assertIsDisplayed()
}
```text

### Performance

**Optimize performance:**

- Use lazy lists (LazyColumn, LazyRow)
- Avoid unnecessary recomposition
- Use derivedStateOf for computed values
- Profile with Android Profiler

**Pattern:**

```kotlin
// ✅ GOOD: Lazy list with key
@Composable
fun UserList(users: List<User>) {
    LazyColumn {
        items(
            items = users,
            key = { user -> user.id }
        ) { user ->
            UserItem(user)
        }
    }
}

// ✅ GOOD: Derived state
@Composable
fun UserStats(users: List<User>) {
    val activeCount by remember {
        derivedStateOf {
            users.count { it.isActive }
        }
    }

    Text("Active users: $activeCount")
}

// ✅ GOOD: Avoid unnecessary recomposition
@Composable
fun UserItem(user: User) {
    // This lambda is stable, won't cause recomposition
    val onClick = remember(user.id) {
        { handleClick(user.id) }
    }

    ListItem(
        headlineContent = { Text(user.name) },
        onClick = onClick
    )
}
```text

### Common Anti-Patterns

**Avoid:**

- Holding Context in ViewModel
- Blocking main thread
- Memory leaks with listeners
- Not using lifecycle-aware components
- Ignoring configuration changes
- Direct View access from ViewModel
- Hardcoding strings (use resources)
- Not handling process death
