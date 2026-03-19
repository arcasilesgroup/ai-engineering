## JavaScript Best Practices

### Modern JavaScript (ES6+)

**Use modern syntax:**

- `const` and `let` instead of `var`
- Arrow functions for concise syntax
- Template literals for strings
- Destructuring for objects and arrays
- Spread operator for copying/merging

**Pattern:**

```javascript
// ✅ GOOD: Modern JavaScript
const users = [...activeUsers, ...inactiveUsers];
const { name, email } = user;
const greeting = `Hello, ${name}!`;

const getName = (user) => user.name;

// ❌ BAD: Old style
var users = activeUsers.concat(inactiveUsers);
var name = user.name;
var email = user.email;
var greeting = 'Hello, ' + name + '!';
```text

### Async/Await

**Asynchronous programming:**

- Use `async`/`await` instead of callbacks
- Handle errors with try-catch
- Use Promise.all for parallel operations
- Use Promise.race for timeouts

**Pattern:**

```javascript
// ✅ GOOD: Async/await
async function fetchUser(id) {
  try {
    const response = await fetch(`/api/users/${id}`);
    return await response.json();
  } catch (error) {
    console.error('Error fetching user:', error);
    throw error;
  }
}

// ✅ GOOD: Parallel requests
const [user, profile, settings] = await Promise.all([
  fetchUser(id),
  fetchProfile(id),
  fetchSettings(id),
]);

// ❌ BAD: Callback hell
fetchUser(id, function(user) {
  fetchProfile(user.id, function(profile) {
    fetchSettings(profile.id, function(settings) {
      // Nested callbacks
    });
  });
});
```text

### Functions

**Function best practices:**

- Use arrow functions for short, non-method functions
- Use regular functions for methods (for `this` binding)
- Default parameters for optional arguments
- Rest parameters for variable arguments

**Pattern:**

```javascript
// ✅ GOOD: Arrow function
const double = (n) => n * 2;
const sum = (a, b) => a + b;

// ✅ GOOD: Default parameters
function createUser(name, role = 'user') {
  return { name, role };
}

// ✅ GOOD: Rest parameters
function sum(...numbers) {
  return numbers.reduce((a, b) => a + b, 0);
}

// ✅ GOOD: Regular function for methods
const user = {
  name: 'John',
  greet() {
    return `Hello, ${this.name}`;
  },
};
```text

### Objects and Arrays

**Working with data:**

- Use object shorthand
- Use computed property names
- Prefer `const` for objects and arrays (prevents reassignment)
- Use array methods: `map`, `filter`, `reduce`
- Use optional chaining `?.` for safe access

**Pattern:**

```javascript
// ✅ GOOD: Object shorthand
const name = 'John';
const email = 'john@example.com';
const user = { name, email };

// ✅ GOOD: Computed properties
const key = 'status';
const user = { [key]: 'active' };

// ✅ GOOD: Optional chaining
const email = user?.profile?.email;
const firstUser = users?.[0];

// ✅ GOOD: Array methods
const activeUsers = users.filter(u => u.isActive);
const names = users.map(u => u.name);
const total = numbers.reduce((sum, n) => sum + n, 0);

// ✅ GOOD: Nullish coalescing
const name = user.name ?? 'Guest';
```text

### Classes

**Object-oriented patterns:**

- Use class syntax for clear structure
- Use `#` for private fields
- Prefer composition over inheritance
- Use static methods for utilities

**Pattern:**

```javascript
// ✅ GOOD: Modern class
class User {
  #password;  // Private field

  constructor(name, email, password) {
    this.name = name;
    this.email = email;
    this.#password = password;
  }

  // Getter
  get displayName() {
    return `${this.name} <${this.email}>`;
  }

  // Method
  authenticate(input) {
    return this.#password === input;
  }

  // Static method
  static create(data) {
    return new User(data.name, data.email, data.password);
  }
}
```text

### Modules

**ES6 modules:**

- Use `export` and `import`
- Named exports for multiple items
- Default export for single main item
- Group related functionality

**Pattern:**

```javascript
// ✅ GOOD: Named exports
// user.js
export function createUser(data) { ... }
export function deleteUser(id) { ... }
export const USER_ROLES = ['admin', 'user'];

// main.js
import { createUser, deleteUser, USER_ROLES } from './user.js';

// ✅ GOOD: Default export
// userService.js
export default class UserService {
  // Implementation
}

// main.js
import UserService from './userService.js';
```text

### Error Handling

**Handle errors properly:**

- Use try-catch for synchronous errors
- Use try-catch with async/await
- Create custom error classes
- Provide context in error messages

**Pattern:**

```javascript
// ✅ GOOD: Custom error
class UserNotFoundError extends Error {
  constructor(userId) {
    super(`User not found: ${userId}`);
    this.name = 'UserNotFoundError';
    this.userId = userId;
  }
}

// ✅ GOOD: Error handling
async function getUser(id) {
  try {
    const user = await fetchUser(id);
    if (!user) {
      throw new UserNotFoundError(id);
    }
    return user;
  } catch (error) {
    if (error instanceof UserNotFoundError) {
      // Handle specific error
      console.log('User not found');
    } else {
      // Handle other errors
      console.error('Error:', error);
    }
    throw error;
  }
}
```text

### Naming Conventions

**JavaScript style:**

- `camelCase` for variables, functions, parameters
- `PascalCase` for classes and constructors
- `UPPER_CASE` for constants
- Descriptive names, avoid abbreviations
- Prefix booleans with `is`, `has`, `should`

### Equality and Comparisons

**Use strict equality:**

- Use `===` and `!==` instead of `==` and `!=`
- Understand truthy and falsy values
- Use explicit checks when needed

**Pattern:**

```javascript
// ✅ GOOD: Strict equality
if (value === null) { }
if (count !== 0) { }

// ❌ BAD: Loose equality
if (value == null) { }  // Matches both null and undefined
if (count != 0) { }     // Unexpected type coercion

// ✅ GOOD: Explicit checks
if (array.length > 0) { }
if (user !== null && user !== undefined) { }
if (user != null) { }  // OK: specifically checking for null/undefined
```text

### Immutability

**Prefer immutable operations:**

- Don't mutate function arguments
- Use spread for copying arrays/objects
- Use array methods that return new arrays
- Consider libraries like Immer for complex state

**Pattern:**

```javascript
// ✅ GOOD: Immutable update
const updatedUser = { ...user, name: 'Jane' };
const newUsers = [...users, newUser];
const filtered = users.filter(u => u.isActive);

// ❌ BAD: Mutation
user.name = 'Jane';  // Mutating argument
users.push(newUser); // Mutating array
```text

### Node.js-Specific

**Server-side patterns:**

- Use ES modules (`import`/`export`)
- Handle process signals gracefully
- Use environment variables for config
- Use streams for large data
- Always handle promise rejections

**Pattern:**

```javascript
// ✅ GOOD: Environment config
const PORT = process.env.PORT ?? 3000;
const DB_URL = process.env.DATABASE_URL;

// ✅ GOOD: Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('SIGTERM received, closing server');
  await server.close();
  await db.disconnect();
  process.exit(0);
});

// ✅ GOOD: Unhandled rejection
process.on('unhandledRejection', (error) => {
  console.error('Unhandled rejection:', error);
  process.exit(1);
});
```text

### Testing

**Testing best practices:**

- Use descriptive test names
- One assertion concept per test
- Use `beforeEach`/`afterEach` for setup/teardown
- Mock external dependencies
- Test behavior, not implementation

**Pattern:**

```javascript
// ✅ GOOD: Clear test structure
describe('User', () => {
  describe('create', () => {
    it('should create user with valid data', () => {
      const user = User.create({ name: 'John', email: 'john@example.com' });
      expect(user.name).toBe('John');
      expect(user.email).toBe('john@example.com');
    });

    it('should throw error with invalid email', () => {
      expect(() => {
        User.create({ name: 'John', email: 'invalid' });
      }).toThrow('Invalid email');
    });
  });
});
```text

### Browser-Specific

**Client-side patterns:**

- Use `addEventListener` for events
- Remove event listeners when done
- Use `defer` or `async` for scripts
- Prefer `fetch` over `XMLHttpRequest`
- Handle CORS properly

**Pattern:**

```javascript
// ✅ GOOD: Event listeners
const button = document.getElementById('submit');
const handleClick = () => console.log('Clicked');

button.addEventListener('click', handleClick);

// Clean up
button.removeEventListener('click', handleClick);

// ✅ GOOD: Fetch API
async function fetchData(url) {
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error: ${response.status}`);
  }

  return await response.json();
}
```text

### Common Anti-Patterns

**Avoid:**

- Using `var` (use `const` or `let`)
- Callback hell (use async/await)
- Mutating function parameters
- Loose equality `==` (use `===`)
- Ignoring errors
- Global variables
- Synchronous blocking operations (Node.js)
- Not cleaning up event listeners
