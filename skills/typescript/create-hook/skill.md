# Skill: Create Custom Hook

---
id: typescript/create-hook
name: Create Custom Hook
complexity: medium
estimated_time: 8 minutes
---

## Description

Creates a reusable React custom hook with proper typing, memoization, and associated tests.

## Prerequisites

- Hook purpose and API defined
- Dependencies identified

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| Hook name | Yes | useXxx format |
| Parameters | Yes | Hook input parameters |
| Return type | Yes | What the hook returns |
| Dependencies | No | External hooks/services |

## Outputs

- Hook file (`useHookName.ts`)
- Types file (`useHookName.types.ts`)
- Test file (`useHookName.test.ts`)

## Execution Steps

### Step 1: Create Types File

```typescript
// useUserData.types.ts
export interface UseUserDataParams {
  userId: string;
  enabled?: boolean;
}

export interface UseUserDataReturn {
  user: User | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export interface User {
  id: string;
  name: string;
  email: string;
}
```

### Step 2: Create Hook File

```typescript
// useUserData.ts
import { useState, useEffect, useCallback } from 'react';
import type { 
  UseUserDataParams, 
  UseUserDataReturn, 
  User 
} from './useUserData.types';
import { userService } from '../../services/userService';

export function useUserData({
  userId,
  enabled = true,
}: UseUserDataParams): UseUserDataReturn {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchUser = useCallback(async () => {
    if (!userId) return;

    setIsLoading(true);
    setError(null);

    try {
      const data = await userService.getUser(userId);
      setUser(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    if (enabled) {
      fetchUser();
    }
  }, [enabled, fetchUser]);

  const refetch = useCallback(async () => {
    await fetchUser();
  }, [fetchUser]);

  return {
    user,
    isLoading,
    error,
    refetch,
  };
}
```

### Step 3: Create Test File

```typescript
// useUserData.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useUserData } from './useUserData';
import { userService } from '../../services/userService';

vi.mock('../../services/userService');

describe('useUserData', () => {
  const mockUser = { id: '1', name: 'John', email: 'john@test.com' };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches user data on mount', async () => {
    vi.mocked(userService.getUser).mockResolvedValue(mockUser);

    const { result } = renderHook(() => 
      useUserData({ userId: '1' })
    );

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.user).toEqual(mockUser);
    expect(result.current.error).toBeNull();
  });

  it('handles errors', async () => {
    const error = new Error('Network error');
    vi.mocked(userService.getUser).mockRejectedValue(error);

    const { result } = renderHook(() => 
      useUserData({ userId: '1' })
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.user).toBeNull();
    expect(result.current.error).toEqual(error);
  });

  it('does not fetch when disabled', () => {
    renderHook(() => 
      useUserData({ userId: '1', enabled: false })
    );

    expect(userService.getUser).not.toHaveBeenCalled();
  });

  it('refetches on demand', async () => {
    vi.mocked(userService.getUser).mockResolvedValue(mockUser);

    const { result } = renderHook(() => 
      useUserData({ userId: '1' })
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await result.current.refetch();

    expect(userService.getUser).toHaveBeenCalledTimes(2);
  });
});
```

## Hook Patterns

### Debounced Value

```typescript
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}
```

### Local Storage State

```typescript
export function useLocalStorage<T>(
  key: string,
  initialValue: T
): [T, (value: T) => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch {
      return initialValue;
    }
  });

  const setValue = useCallback((value: T) => {
    setStoredValue(value);
    window.localStorage.setItem(key, JSON.stringify(value));
  }, [key]);

  return [storedValue, setValue];
}
```

### Toggle State

```typescript
export function useToggle(
  initialValue = false
): [boolean, () => void, (value: boolean) => void] {
  const [value, setValue] = useState(initialValue);

  const toggle = useCallback(() => {
    setValue(v => !v);
  }, []);

  const set = useCallback((newValue: boolean) => {
    setValue(newValue);
  }, []);

  return [value, toggle, set];
}
```

### Event Listener

```typescript
export function useEventListener<K extends keyof WindowEventMap>(
  eventName: K,
  handler: (event: WindowEventMap[K]) => void,
  element: Window | HTMLElement = window
): void {
  const savedHandler = useRef(handler);

  useEffect(() => {
    savedHandler.current = handler;
  }, [handler]);

  useEffect(() => {
    const eventListener = (event: Event) => {
      savedHandler.current(event as WindowEventMap[K]);
    };

    element.addEventListener(eventName, eventListener);
    return () => element.removeEventListener(eventName, eventListener);
  }, [eventName, element]);
}
```

## Checklist

- [ ] Hook name starts with `use`
- [ ] Types file with params and return interfaces
- [ ] Proper dependency arrays in useEffect/useCallback
- [ ] Cleanup in useEffect where needed
- [ ] Error handling included
- [ ] Loading state exposed
- [ ] Test file with key scenarios
- [ ] Memoization applied appropriately
- [ ] No unnecessary re-renders

## Rules of Hooks

1. Only call hooks at the top level
2. Only call hooks from React functions
3. Include all dependencies in arrays
4. Cleanup side effects properly

## Related Skills

- [Create Component](../create-component/skill.md)
- [Generate Tests](../../dotnet/generate-tests/skill.md)

## Example Invocation

```
Create a custom hook:
- Name: useApiData
- Params: endpoint (string), options (RequestOptions)
- Returns: data, loading, error, refetch, mutate
- Features: caching, automatic retry, error recovery
```
