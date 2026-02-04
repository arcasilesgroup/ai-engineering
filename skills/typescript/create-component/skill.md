# Skill: Create React Component

---
id: typescript/create-component
name: Create React Component
complexity: low
estimated_time: 5 minutes
---

## Description

Creates a new React functional component following project conventions with proper typing, styling, and test file.

## Prerequisites

- Target feature/module identified
- Props interface defined
- Styling approach (CSS Modules, Tailwind, Styled Components)

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| Component name | Yes | PascalCase name |
| Props | Yes | Component properties |
| Location | Yes | Feature folder path |
| Has children | No | Accepts children (default: false) |
| Has state | No | Uses local state |

## Outputs

- Component file (`ComponentName.tsx`)
- Types file (`ComponentName.types.ts`)
- Styles file (`ComponentName.module.css`)
- Test file (`ComponentName.test.tsx`)
- Barrel export update

## Execution Steps

### Step 1: Create Types File

```typescript
// ComponentName.types.ts
export interface ComponentNameProps {
  /** Primary label text */
  label: string;
  /** Click handler */
  onClick?: () => void;
  /** Visual variant */
  variant?: 'primary' | 'secondary';
  /** Disabled state */
  disabled?: boolean;
}

export interface ComponentNameState {
  isLoading: boolean;
  error: string | null;
}
```

### Step 2: Create Component File

```typescript
// ComponentName.tsx
import { type FC, useState, useCallback } from 'react';
import type { ComponentNameProps } from './ComponentName.types';
import styles from './ComponentName.module.css';

export const ComponentName: FC<ComponentNameProps> = ({
  label,
  onClick,
  variant = 'primary',
  disabled = false,
}) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleClick = useCallback(() => {
    if (disabled || isLoading) return;
    onClick?.();
  }, [disabled, isLoading, onClick]);

  return (
    <div
      className={`${styles.container} ${styles[variant]}`}
      data-testid="component-name"
    >
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled || isLoading}
        className={styles.button}
      >
        {isLoading ? 'Loading...' : label}
      </button>
    </div>
  );
};

ComponentName.displayName = 'ComponentName';
```

### Step 3: Create Styles File

```css
/* ComponentName.module.css */
.container {
  display: flex;
  align-items: center;
}

.button {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.primary .button {
  background-color: var(--color-primary);
  color: white;
  border: none;
}

.secondary .button {
  background-color: transparent;
  color: var(--color-primary);
  border: 1px solid var(--color-primary);
}
```

### Step 4: Create Test File

```typescript
// ComponentName.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ComponentName } from './ComponentName';

describe('ComponentName', () => {
  it('renders with label', () => {
    render(<ComponentName label="Click me" />);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<ComponentName label="Click" onClick={handleClick} />);
    
    fireEvent.click(screen.getByRole('button'));
    
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('does not call onClick when disabled', () => {
    const handleClick = vi.fn();
    render(
      <ComponentName label="Click" onClick={handleClick} disabled />
    );
    
    fireEvent.click(screen.getByRole('button'));
    
    expect(handleClick).not.toHaveBeenCalled();
  });

  it('applies variant class', () => {
    render(<ComponentName label="Click" variant="secondary" />);
    
    expect(screen.getByTestId('component-name'))
      .toHaveClass('secondary');
  });
});
```

### Step 5: Update Barrel Export

```typescript
// index.ts (in same folder)
export { ComponentName } from './ComponentName';
export type { ComponentNameProps } from './ComponentName.types';
```

## Component Patterns

### With Children

```typescript
interface ContainerProps {
  children: React.ReactNode;
  className?: string;
}

export const Container: FC<ContainerProps> = ({ children, className }) => (
  <div className={className}>{children}</div>
);
```

### With Forwarded Ref

```typescript
import { forwardRef } from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, ...props }, ref) => (
    <label>
      {label}
      <input ref={ref} {...props} />
    </label>
  )
);

Input.displayName = 'Input';
```

### With Context

```typescript
import { useMyContext } from '../../contexts/MyContext';

export const ContextConsumer: FC = () => {
  const { value, setValue } = useMyContext();
  // ...
};
```

## Checklist

- [ ] Types file with exported interfaces
- [ ] Component file with proper FC typing
- [ ] displayName set for debugging
- [ ] data-testid added for testing
- [ ] Styles file created (CSS Modules)
- [ ] Test file with key scenarios
- [ ] Barrel export updated
- [ ] No inline styles
- [ ] Accessibility attributes (aria-*)

## Folder Structure

```
features/
└── my-feature/
    └── components/
        └── ComponentName/
            ├── index.ts
            ├── ComponentName.tsx
            ├── ComponentName.types.ts
            ├── ComponentName.module.css
            └── ComponentName.test.tsx
```

## Related Skills

- [Create Custom Hook](../create-hook/skill.md)
- [Generate Tests](../generate-tests/skill.md)

## Example Invocation

```
Create a React component:
- Name: UserCard
- Props: user (User), onEdit, onDelete, showActions
- Location: features/users/components
- Include: loading state, error boundary
```
