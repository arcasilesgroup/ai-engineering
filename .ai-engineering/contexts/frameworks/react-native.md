## React Native Best Practices

### Component Structure

**Organize by feature:**

- Group related components
- Keep components small and focused
- Use functional components with hooks
- Separate business logic from UI

**Pattern:**

```javascript
// ✅ GOOD: Functional component with hooks
import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';

export function UserProfile({ userId }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchUser(userId).then(setUser).finally(() => setLoading(false));
  }, [userId]);

  if (loading) {
    return <LoadingSpinner />;
  }

  return (
    <View style={styles.container}>
      <Text style={styles.name}>{user.name}</Text>
      <Text style={styles.email}>{user.email}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 16,
  },
  name: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  email: {
    fontSize: 14,
    color: '#666',
  },
});
```text

### Styling

**Use StyleSheet API:**

- Create styles with StyleSheet.create
- Avoid inline styles
- Use Platform-specific styles when needed
- Consider responsive design

**Pattern:**

```javascript
// ✅ GOOD: StyleSheet
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    padding: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 12,
  },
  // Platform-specific
  shadow: Platform.select({
    ios: {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.25,
      shadowRadius: 3.84,
    },
    android: {
      elevation: 5,
    },
  }),
});

// ❌ BAD: Inline styles
<View style={{ flex: 1, backgroundColor: '#fff', padding: 16 }}>
```text

### Performance

**Optimize for performance:**

- Use FlatList/SectionList for long lists
- Implement shouldComponentUpdate or React.memo
- Use useCallback and useMemo appropriately
- Avoid anonymous functions in render
- Optimize images

**Pattern:**

```javascript
// ✅ GOOD: FlatList with optimization
import { FlatList, Image } from 'react-native';

function UserList({ users }) {
  const renderItem = useCallback(({ item }) => (
    <UserItem user={item} />
  ), []);

  const keyExtractor = useCallback((item) => item.id, []);

  return (
    <FlatList
      data={users}
      renderItem={renderItem}
      keyExtractor={keyExtractor}
      removeClippedSubviews
      maxToRenderPerBatch={10}
      windowSize={10}
    />
  );
}

// ✅ GOOD: Memoized component
const UserItem = React.memo(({ user }) => (
  <View>
    <Text>{user.name}</Text>
  </View>
));

// ✅ GOOD: Optimized images
<Image
  source={{ uri: user.avatar }}
  style={styles.avatar}
  resizeMode="cover"
  defaultSource={require('./placeholder.png')}
/>
```text

### Navigation

**React Navigation best practices:**

- Use type-safe navigation
- Keep navigation logic separate
- Handle deep linking
- Manage navigation state properly

**Pattern:**

```javascript
// ✅ GOOD: Navigation setup
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

const Stack = createNativeStackNavigator();

function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Home">
        <Stack.Screen
          name="Home"
          component={HomeScreen}
          options={{ title: 'Home' }}
        />
        <Stack.Screen
          name="Profile"
          component={ProfileScreen}
          options={({ route }) => ({ title: route.params.userName })}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

// ✅ GOOD: Navigation usage
function HomeScreen({ navigation }) {
  const goToProfile = useCallback((userId, userName) => {
    navigation.navigate('Profile', { userId, userName });
  }, [navigation]);

  return <UserList onUserPress={goToProfile} />;
}
```text

### State Management

**Choose appropriate state solution:**

- useState for local state
- useContext for shared state
- Redux/Zustand for global state
- React Query for server state

**Pattern:**

```javascript
// ✅ GOOD: Local state with useState
function Counter() {
  const [count, setCount] = useState(0);

  const increment = useCallback(() => {
    setCount(prev => prev + 1);
  }, []);

  return (
    <View>
      <Text>Count: {count}</Text>
      <Button title="Increment" onPress={increment} />
    </View>
  );
}

// ✅ GOOD: Context for shared state
const UserContext = React.createContext();

export function UserProvider({ children }) {
  const [user, setUser] = useState(null);

  const value = useMemo(() => ({ user, setUser }), [user]);

  return (
    <UserContext.Provider value={value}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUser must be used within UserProvider');
  }
  return context;
}
```text

### Async Operations

**Handle async properly:**

- Use useEffect for side effects
- Clean up subscriptions
- Handle loading and error states
- Use AbortController for cancellation

**Pattern:**

```javascript
// ✅ GOOD: Async with cleanup
function UserProfile({ userId }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const abortController = new AbortController();

    async function loadUser() {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchUser(userId, {
          signal: abortController.signal,
        });
        setUser(data);
      } catch (err) {
        if (err.name !== 'AbortError') {
          setError(err.message);
        }
      } finally {
        setLoading(false);
      }
    }

    loadUser();

    return () => {
      abortController.abort();
    };
  }, [userId]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;
  if (!user) return null;

  return <UserDetails user={user} />;
}
```text

### Forms and Input

**Handle user input:**

- Use controlled components
- Validate input
- Handle keyboard properly
- Provide feedback

**Pattern:**

```javascript
// ✅ GOOD: Controlled form
import { TextInput, KeyboardAvoidingView, Platform } from 'react-native';

function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState({});

  const handleSubmit = useCallback(async () => {
    const newErrors = {};
    if (!email) newErrors.email = 'Email is required';
    if (!password) newErrors.password = 'Password is required';

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    try {
      await login(email, password);
    } catch (error) {
      setErrors({ form: error.message });
    }
  }, [email, password]);

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <TextInput
        value={email}
        onChangeText={setEmail}
        placeholder="Email"
        keyboardType="email-address"
        autoCapitalize="none"
        autoComplete="email"
        style={styles.input}
      />
      {errors.email && <Text style={styles.error}>{errors.email}</Text>}

      <TextInput
        value={password}
        onChangeText={setPassword}
        placeholder="Password"
        secureTextEntry
        autoComplete="password"
        style={styles.input}
      />
      {errors.password && <Text style={styles.error}>{errors.password}</Text>}

      <Button title="Login" onPress={handleSubmit} />
    </KeyboardAvoidingView>
  );
}
```text

### Platform-Specific Code

**Handle platform differences:**

- Use Platform.select
- Separate files: .ios.js and .android.js
- Test on both platforms
- Handle safe areas

**Pattern:**

```javascript
// ✅ GOOD: Platform-specific code
import { Platform, SafeAreaView } from 'react-native';

const headerHeight = Platform.select({
  ios: 44,
  android: 56,
  default: 44,
});

// ✅ GOOD: Safe area
function Screen({ children }) {
  return (
    <SafeAreaView style={styles.container}>
      {children}
    </SafeAreaView>
  );
}

// ✅ GOOD: Separate platform files
// Button.ios.js
export function Button({ title, onPress }) {
  // iOS-specific implementation
}

// Button.android.js
export function Button({ title, onPress }) {
  // Android-specific implementation
}

// Usage
import { Button } from './Button';  // Auto-selects correct file
```text

### Native Modules

**When to use native code:**

- Access platform APIs not available in JS
- Performance-critical operations
- Third-party libraries

**Pattern:**

```javascript
// ✅ GOOD: Using native module
import { NativeModules, NativeEventEmitter } from 'react-native';

const { BiometricAuth } = NativeModules;

async function authenticate() {
  try {
    const result = await BiometricAuth.authenticate({
      reason: 'Authenticate to access your account',
    });
    return result.success;
  } catch (error) {
    console.error('Biometric auth failed:', error);
    return false;
  }
}

// ✅ GOOD: Native events
const eventEmitter = new NativeEventEmitter(NativeModules.MyModule);

useEffect(() => {
  const subscription = eventEmitter.addListener('onEvent', (event) => {
    console.log('Event received:', event);
  });

  return () => {
    subscription.remove();
  };
}, []);
```text

### Error Handling

**Handle errors gracefully:**

- Use error boundaries
- Log errors
- Show user-friendly messages
- Handle network errors

**Pattern:**

```javascript
// ✅ GOOD: Error boundary
class ErrorBoundary extends React.Component {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error caught:', error, errorInfo);
    // Log to error reporting service
  }

  render() {
    if (this.state.hasError) {
      return (
        <View style={styles.errorContainer}>
          <Text>Something went wrong</Text>
          <Button
            title="Try Again"
            onPress={() => this.setState({ hasError: false })}
          />
        </View>
      );
    }

    return this.props.children;
  }
}

// Usage
<ErrorBoundary>
  <App />
</ErrorBoundary>
```text

### Testing

**Testing best practices:**

- Unit test components with React Native Testing Library
- Test user interactions
- Mock native modules
- Test on real devices

**Pattern:**

```javascript
// ✅ GOOD: Component test
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { UserProfile } from './UserProfile';

describe('UserProfile', () => {
  it('should display user information', async () => {
    const { getByText } = render(<UserProfile userId="123" />);

    await waitFor(() => {
      expect(getByText('John Doe')).toBeTruthy();
      expect(getByText('john@example.com')).toBeTruthy();
    });
  });

  it('should handle button press', () => {
    const onPress = jest.fn();
    const { getByText } = render(<Button title="Click Me" onPress={onPress} />);

    fireEvent.press(getByText('Click Me'));

    expect(onPress).toHaveBeenCalledTimes(1);
  });
});
```text

### Common Anti-Patterns

**Avoid:**

- Using index as key in lists
- Anonymous functions in render (causes re-renders)
- Not cleaning up useEffect
- Deep component nesting
- Mutating state directly
- Blocking the main thread
- Not handling Android back button
- Ignoring accessibility
