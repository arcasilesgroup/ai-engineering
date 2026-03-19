## Flutter Best Practices

### Project Structure

**Organize by feature:**

- Group related widgets, models, services
- Separate presentation from business logic
- Use feature-first structure
- Keep shared code in core

**Pattern:**

```text
lib/
  features/
    user/
      presentation/
        user_screen.dart
        user_list_widget.dart
      models/
        user.dart
      services/
        user_service.dart
    products/
      ...
  core/
    network/
    theme/
    widgets/
    utils/
  main.dart
```text

### Widget Organization

**Build efficient widgets:**

- Keep widgets small and focused
- Extract widgets for reusability
- Use const constructors
- Separate stateless from stateful

**Pattern:**

```dart
// ✅ GOOD: Small, focused widget
class UserProfile extends StatelessWidget {
  final User user;

  const UserProfile({Key? key, required this.user}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            UserAvatar(url: user.avatarUrl),
            const SizedBox(height: 8),
            UserInfo(user: user),
            const SizedBox(height: 8),
            UserActions(userId: user.id),
          ],
        ),
      ),
    );
  }
}

// ✅ GOOD: Extract widget
class UserAvatar extends StatelessWidget {
  final String url;

  const UserAvatar({Key? key, required this.url}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return CircleAvatar(
      radius: 40,
      backgroundImage: NetworkImage(url),
    );
  }
}
```text

### State Management

**Choose appropriate solution:**

- Provider for simple state
- Riverpod for advanced state
- BLoC for complex apps
- setState for local state

**Pattern:**

```dart
// ✅ GOOD: Provider
class UserProvider extends ChangeNotifier {
  User? _user;
  bool _isLoading = false;
  String? _error;

  User? get user => _user;
  bool get isLoading => _isLoading;
  String? get error => _error;

  Future<void> loadUser(String id) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _user = await userService.fetchUser(id);
    } catch (e) {
      _error = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}

// Usage
class UserScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Consumer<UserProvider>(
      builder: (context, provider, child) {
        if (provider.isLoading) {
          return const CircularProgressIndicator();
        }

        if (provider.error != null) {
          return ErrorWidget(provider.error!);
        }

        if (provider.user == null) {
          return const SizedBox();
        }

        return UserProfile(user: provider.user!);
      },
    );
  }
}

// ✅ GOOD: Riverpod
final userProvider = FutureProvider.autoDispose.family<User, String>((ref, id) {
  return userService.fetchUser(id);
});

class UserScreen extends ConsumerWidget {
  final String userId;

  const UserScreen({Key? key, required this.userId}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final userAsync = ref.watch(userProvider(userId));

    return userAsync.when(
      data: (user) => UserProfile(user: user),
      loading: () => const CircularProgressIndicator(),
      error: (error, stack) => ErrorWidget(error.toString()),
    );
  }
}
```text

### Navigation

**Navigator 2.0 or packages:**

- Use go_router for declarative routing
- Handle deep links
- Type-safe navigation
- Manage navigation state

**Pattern:**

```dart
// ✅ GOOD: go_router
final router = GoRouter(
  routes: [
    GoRoute(
      path: '/',
      builder: (context, state) => const HomeScreen(),
    ),
    GoRoute(
      path: '/user/:id',
      builder: (context, state) {
        final id = state.params['id']!;
        return UserScreen(userId: id);
      },
    ),
  ],
);

// Main app
class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      routerConfig: router,
    );
  }
}

// Navigation
context.go('/user/123');
context.push('/user/123');
```text

### Networking

**HTTP client best practices:**

- Use http or dio package
- Handle errors properly
- Use models with fromJson/toJson
- Implement retry logic

**Pattern:**

```dart
// ✅ GOOD: API client
class ApiClient {
  final http.Client client;
  final String baseUrl;

  ApiClient({
    required this.client,
    required this.baseUrl,
  });

  Future<T> get<T>(
    String path, {
    required T Function(Map<String, dynamic>) fromJson,
  }) async {
    final url = Uri.parse('$baseUrl$path');

    try {
      final response = await client.get(url);

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        return fromJson(json);
      } else if (response.statusCode == 404) {
        throw NotFoundException('Resource not found');
      } else {
        throw ApiException('Request failed: ${response.statusCode}');
      }
    } on SocketException {
      throw NetworkException('No internet connection');
    } on FormatException {
      throw ApiException('Invalid response format');
    }
  }

  Future<T> post<T>(
    String path, {
    required Map<String, dynamic> body,
    required T Function(Map<String, dynamic>) fromJson,
  }) async {
    final url = Uri.parse('$baseUrl$path');

    final response = await client.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );

    if (response.statusCode == 201 || response.statusCode == 200) {
      final json = jsonDecode(response.body) as Map<String, dynamic>;
      return fromJson(json);
    }

    throw ApiException('Request failed: ${response.statusCode}');
  }
}

// Usage
class UserService {
  final ApiClient client;

  UserService(this.client);

  Future<User> fetchUser(String id) async {
    return client.get(
      '/users/$id',
      fromJson: (json) => User.fromJson(json),
    );
  }
}
```text

### Data Persistence

**Local storage options:**

- SharedPreferences for key-value
- SQLite/Hive for structured data
- secure_storage for sensitive data
- File system for files

**Pattern:**

```dart
// ✅ GOOD: Hive for local data
@HiveType(typeId: 0)
class User extends HiveObject {
  @HiveField(0)
  final String id;

  @HiveField(1)
  final String name;

  @HiveField(2)
  final String email;

  User({
    required this.id,
    required this.name,
    required this.email,
  });
}

// Initialize
await Hive.initFlutter();
Hive.registerAdapter(UserAdapter());
await Hive.openBox<User>('users');

// Usage
class UserRepository {
  final Box<User> box = Hive.box<User>('users');

  Future<void> saveUser(User user) async {
    await box.put(user.id, user);
  }

  User? getUser(String id) {
    return box.get(id);
  }

  List<User> getAllUsers() {
    return box.values.toList();
  }
}
```text

### Forms and Validation

**Handle user input:**

- Use Form and TextFormField
- Validate input
- Show errors clearly
- Handle keyboard

**Pattern:**

```dart
// ✅ GOOD: Form with validation
class LoginForm extends StatefulWidget {
  @override
  State<LoginForm> createState() => _LoginFormState();
}

class _LoginFormState extends State<LoginForm> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_formKey.currentState!.validate()) {
      final email = _emailController.text;
      final password = _passwordController.text;

      try {
        await authService.login(email, password);
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Login failed: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Form(
      key: _formKey,
      child: Column(
        children: [
          TextFormField(
            controller: _emailController,
            decoration: const InputDecoration(labelText: 'Email'),
            keyboardType: TextInputType.emailAddress,
            validator: (value) {
              if (value == null || value.isEmpty) {
                return 'Email is required';
              }
              if (!value.contains('@')) {
                return 'Invalid email';
              }
              return null;
            },
          ),
          TextFormField(
            controller: _passwordController,
            decoration: const InputDecoration(labelText: 'Password'),
            obscureText: true,
            validator: (value) {
              if (value == null || value.isEmpty) {
                return 'Password is required';
              }
              if (value.length < 8) {
                return 'Password must be at least 8 characters';
              }
              return null;
            },
          ),
          ElevatedButton(
            onPressed: _submit,
            child: const Text('Login'),
          ),
        ],
      ),
    );
  }
}
```text

### Performance

**Optimize for performance:**

- Use const constructors
- Avoid rebuilding widgets unnecessarily
- Use ListView.builder for long lists
- Cache expensive computations
- Optimize images

**Pattern:**

```dart
// ✅ GOOD: ListView.builder
class UserList extends StatelessWidget {
  final List<User> users;

  const UserList({Key? key, required this.users}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      itemCount: users.length,
      itemBuilder: (context, index) {
        final user = users[index];
        return UserListTile(user: user);
      },
    );
  }
}

// ✅ GOOD: Const constructors
class UserListTile extends StatelessWidget {
  final User user;

  const UserListTile({Key? key, required this.user}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: CircleAvatar(
        backgroundImage: NetworkImage(user.avatarUrl),
      ),
      title: Text(user.name),
      subtitle: Text(user.email),
    );
  }
}

// ✅ GOOD: Memoization
class ExpensiveWidget extends StatefulWidget {
  @override
  State<ExpensiveWidget> createState() => _ExpensiveWidgetState();
}

class _ExpensiveWidgetState extends State<ExpensiveWidget> {
  late final List<Item> _cachedItems;

  @override
  void initState() {
    super.initState();
    _cachedItems = _computeExpensiveItems();
  }

  List<Item> _computeExpensiveItems() {
    // Expensive computation
    return [];
  }

  @override
  Widget build(BuildContext context) {
    return ListView(children: _cachedItems.map(_buildItem).toList());
  }

  Widget _buildItem(Item item) {
    return Text(item.name);
  }
}
```text

### Error Handling

**Handle errors gracefully:**

- Use try-catch for async operations
- Show user-friendly error messages
- Log errors for debugging
- Handle network errors

**Pattern:**

```dart
// ✅ GOOD: Error handling
class UserScreen extends StatefulWidget {
  @override
  State<UserScreen> createState() => _UserScreenState();
}

class _UserScreenState extends State<UserScreen> {
  User? _user;
  bool _isLoading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadUser();
  }

  Future<void> _loadUser() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final user = await userService.fetchUser('123');
      setState(() {
        _user = user;
      });
    } on NetworkException {
      setState(() {
        _error = 'No internet connection. Please try again.';
      });
    } on NotFoundException {
      setState(() {
        _error = 'User not found.';
      });
    } catch (e) {
      setState(() {
        _error = 'An error occurred: $e';
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(_error!),
            ElevatedButton(
              onPressed: _loadUser,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (_user == null) {
      return const SizedBox();
    }

    return UserProfile(user: _user!);
  }
}
```text

### Testing

**Testing best practices:**

- Unit test business logic
- Widget test UI components
- Integration test user flows
- Mock dependencies

**Pattern:**

```dart
// ✅ GOOD: Unit test
void main() {
  group('UserService', () {
    late UserService service;
    late MockApiClient mockClient;

    setUp(() {
      mockClient = MockApiClient();
      service = UserService(mockClient);
    });

    test('fetchUser returns user on success', () async {
      final user = User(id: '123', name: 'John', email: 'john@example.com');

      when(() => mockClient.get(any(), fromJson: any(named: 'fromJson')))
          .thenAnswer((_) async => user);

      final result = await service.fetchUser('123');

      expect(result, user);
      verify(() => mockClient.get('/users/123', fromJson: any(named: 'fromJson'))).called(1);
    });

    test('fetchUser throws on error', () async {
      when(() => mockClient.get(any(), fromJson: any(named: 'fromJson')))
          .thenThrow(NetworkException('No connection'));

      expect(
        () => service.fetchUser('123'),
        throwsA(isA<NetworkException>()),
      );
    });
  });
}

// ✅ GOOD: Widget test
void main() {
  testWidgets('UserProfile displays user info', (tester) async {
    final user = User(id: '123', name: 'John', email: 'john@example.com');

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: UserProfile(user: user),
        ),
      ),
    );

    expect(find.text('John'), findsOneWidget);
    expect(find.text('john@example.com'), findsOneWidget);
  });

  testWidgets('UserScreen shows loading indicator', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: UserScreen(),
      ),
    );

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });
}
```text

### Theming

**Use Theme properly:**

- Define app theme
- Use ThemeData
- Support dark mode
- Use theme colors

**Pattern:**

```dart
// ✅ GOOD: Theme definition
class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blue,
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      themeMode: ThemeMode.system,
      home: const HomeScreen(),
    );
  }
}

// ✅ GOOD: Use theme
class MyWidget extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      color: theme.colorScheme.surface,
      child: Text(
        'Hello',
        style: theme.textTheme.headlineMedium,
      ),
    );
  }
}
```text

### Common Anti-Patterns

**Avoid:**

- Not using const constructors
- Building widgets in build method
- Not disposing controllers
- Ignoring platform differences
- Deep widget trees without extraction
- Mutating state in build method
- Not handling null safety properly
- Blocking UI thread with heavy computation
