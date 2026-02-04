---
name: add-component
description: Create a new React/TypeScript component with tests
disable-model-invocation: true
---

## Context

Scaffolds a new React component with TypeScript types, styling, tests, and optional Storybook story.

## Inputs

$ARGUMENTS - Component name and optional type (page, feature, ui)

## Steps

### 1. Parse Arguments

Extract from $ARGUMENTS:
- **Component name** (e.g., `UserProfile`)
- **Type** (page, feature, ui) - defaults to `ui`

### 2. Determine Location

Based on type:
- `ui` → `src/components/ui/{ComponentName}/`
- `feature` → `src/components/features/{ComponentName}/`
- `page` → `src/pages/{ComponentName}/`

### 3. Read Standards

Read `standards/typescript.md` for React component conventions.

### 4. Create Component File

```typescript
// {ComponentName}.tsx
interface {ComponentName}Props {
  // Props here
}

export function {ComponentName}({ }: {ComponentName}Props) {
  return (
    <div>
      {/* Component content */}
    </div>
  );
}
```

### 5. Create Test File

```typescript
// {ComponentName}.test.tsx
import { render, screen } from '@testing-library/react';
import { {ComponentName} } from './{ComponentName}';

describe('{ComponentName}', () => {
  it('renders without crashing', () => {
    render(<{ComponentName} />);
  });
});
```

### 6. Create Index File

```typescript
// index.ts
export { {ComponentName} } from './{ComponentName}';
export type { {ComponentName}Props } from './{ComponentName}';
```

### 7. Verify

Run `npm test` and `npm run build` to confirm.

## Verification

- Component renders without errors
- Tests pass
- TypeScript types are correct
- Follows project component patterns
