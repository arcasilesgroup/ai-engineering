# TypeScript Coding Standards

> TypeScript conventions for React and Node.js projects.

---

## General Principles

- Enable strict mode in `tsconfig.json`
- Avoid `any` - use `unknown` and type guards instead
- Prefer interfaces for object shapes, types for unions/intersections
- Use explicit return types for exported functions

---

## Type Definitions

### Interfaces vs Types

```typescript
// ✅ Interface for object shapes (extensible)
interface User {
  id: string;
  name: string;
  email: string;
}

// ✅ Type for unions, intersections, mapped types
type Status = 'active' | 'inactive' | 'pending';
type UserWithRole = User & { role: string };

// ✅ Type for function signatures
type UserHandler = (user: User) => Promise<void>;
```

### Avoid `any`

```typescript
// ❌ BAD: any disables type checking
function process(data: any) { }

// ✅ GOOD: Use unknown with type guards
function process(data: unknown): User | null {
  if (isUser(data)) {
    return data;
  }
  return null;
}

function isUser(value: unknown): value is User {
  return (
    typeof value === 'object' &&
    value !== null &&
    'id' in value &&
    'name' in value
  );
}
```

---

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Files | kebab-case | `user-service.ts`, `use-auth.ts` |
| Components | PascalCase | `UserProfile.tsx` |
| Interfaces | PascalCase | `UserResponse`, `ApiConfig` |
| Types | PascalCase | `UserId`, `Status` |
| Functions | camelCase | `getUser`, `handleSubmit` |
| Variables | camelCase | `userName`, `isLoading` |
| Constants | UPPER_SNAKE_CASE or camelCase | `API_BASE_URL`, `defaultConfig` |
| Enums | PascalCase | `UserStatus.Active` |

---

## Function Patterns

### Explicit Return Types

```typescript
// ✅ Explicit return type for exported functions
export async function fetchUser(id: string): Promise<User | null> {
  const response = await api.get(`/users/${id}`);
  return response.data;
}

// ✅ Inferred types OK for local/private functions
const transform = (data: RawData) => ({
  id: data.userId,
  name: data.fullName,
});
```

### Optional Parameters & Defaults

```typescript
// ✅ GOOD: Optional with default
interface FetchOptions {
  page?: number;
  pageSize?: number;
  sortBy?: string;
}

async function fetchUsers(options: FetchOptions = {}): Promise<User[]> {
  const { page = 1, pageSize = 20, sortBy = 'name' } = options;
  // ...
}
```

---

## Async/Await

### Error Handling

```typescript
// ✅ GOOD: Try/catch with typed error handling
async function fetchData(): Promise<Result<Data>> {
  try {
    const response = await api.get('/data');
    return { success: true, data: response.data };
  } catch (error) {
    if (error instanceof ApiError) {
      return { success: false, error: error.message };
    }
    return { success: false, error: 'Unknown error occurred' };
  }
}

// ✅ Result type pattern (similar to .NET)
interface Result<T> {
  success: boolean;
  data?: T;
  error?: string;
}
```

---

## Null Handling

### Strict Null Checks

```typescript
// ✅ GOOD: Explicit null handling
function getUser(id: string): User | null {
  const user = users.find(u => u.id === id);
  return user ?? null;
}

// ✅ GOOD: Optional chaining
const userName = user?.profile?.name ?? 'Anonymous';

// ✅ GOOD: Non-null assertion only when certain
const element = document.getElementById('root')!;
```

---

## Imports

### Organization

```typescript
// 1. External libraries
import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';

// 2. Internal modules (absolute imports)
import { api } from '@/services/api';
import { Button } from '@/components/ui';

// 3. Relative imports
import { UserCard } from './UserCard';
import type { User } from './types';

// 4. Styles
import styles from './UserList.module.css';
```

### Type-Only Imports

```typescript
// ✅ Use type-only imports for types
import type { User, UserResponse } from './types';
import { fetchUser } from './api';
```

---

## Enums vs Union Types

```typescript
// ✅ PREFERRED: Union types (tree-shakeable)
type Status = 'active' | 'inactive' | 'pending';

// ✅ ACCEPTABLE: Const objects (when you need values)
const Status = {
  Active: 'active',
  Inactive: 'inactive',
  Pending: 'pending',
} as const;
type Status = typeof Status[keyof typeof Status];

// ⚠️ USE SPARINGLY: Enums (can have bundle size impact)
enum Status {
  Active = 'active',
  Inactive = 'inactive',
  Pending = 'pending',
}
```

---

## Best Practices

### Do

- ✅ Enable `strict: true` in tsconfig.json
- ✅ Use explicit return types for public APIs
- ✅ Prefer `interface` for extensible types
- ✅ Use `readonly` for immutable data
- ✅ Export types separately from implementations

### Don't

- ❌ Use `any` (use `unknown` instead)
- ❌ Use `!` non-null assertion without certainty
- ❌ Ignore TypeScript errors with `// @ts-ignore`
- ❌ Mix default and named exports in same file
