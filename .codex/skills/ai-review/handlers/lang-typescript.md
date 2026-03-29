# Handler: Language -- TypeScript

## Purpose

Language-specific review for TypeScript and JavaScript code. Supplements the 8-concern review agents with type-safety checks, framework-aware patterns (React, Node.js, Next.js), and pre-review PR readiness validation.

## Integration

Dispatched as **Step 2b** (between Step 2 dispatch and Step 3 aggregate). Findings use the same YAML format. Language findings receive a **+10% confidence bonus** when corroborated by a concern agent.

## Procedure

### Step 1 -- Pre-Review PR Readiness

Before analyzing code, check PR health:

1. **Detect base branch**: `gh pr view --json baseRefName,headRefName,mergeable,statusCheckRollup`
2. **Check merge readiness**: report conflicting files, failing checks
3. **Run project typecheck**: `npx tsc --noEmit` (or project-specific command from `package.json`)
4. If typecheck fails, report type errors as critical findings before proceeding

### Step 2 -- Detect TypeScript Scope

1. Identify `.ts`, `.tsx`, `.js`, `.jsx` files in the diff
2. If no TypeScript/JavaScript files, skip this handler entirely
3. Detect frameworks from imports and config:
   - `react` imports -> enable React checks
   - `next` imports or `next.config.*` -> enable Next.js checks
   - `express` / `fastify` / `nestjs` imports -> enable Node.js server checks
4. Read `.ai-engineering/contexts/languages/typescript.md` if not already loaded
5. Check `tsconfig.json` for `strict` mode -- if disabled, increase confidence on type findings

### Step 3 -- Critical Findings (severity: critical)

**eval() and Function constructor**
```typescript
// BAD: code injection
eval(userInput);
new Function("return " + userInput)();
setTimeout(userInput, 0); // string overload

// GOOD: parse data, not code
JSON.parse(userInput);
```

**innerHTML XSS**
```typescript
// BAD: XSS vector
element.innerHTML = userInput;
el.outerHTML = `<div>${data}</div>`;

// GOOD: safe alternatives
element.textContent = userInput;
// React: dangerouslySetInnerHTML requires explicit opt-in and sanitization
```

**SQL string concatenation**
```typescript
// BAD: SQL injection
db.query(`SELECT * FROM users WHERE id = '${userId}'`);

// GOOD: parameterized
db.query("SELECT * FROM users WHERE id = $1", [userId]);
```

**Prototype pollution**
```typescript
// BAD: user-controlled key assignment
obj[userKey] = userValue;
Object.assign(target, untrustedSource);
{ ...defaults, ...userInput }  // shallow merge of untrusted data

// Flag when: key or source originates from request body, query params, or headers
```

### Step 4 -- High Findings (severity: major)

**`any` type without justification**
- Flag every `any` annotation not accompanied by a comment explaining why
- Confidence 80% in library code, 60% in test code
- Check for `// eslint-disable-next-line @typescript-eslint/no-explicit-any` without explanation

**Non-null assertion abuse**
```typescript
// BAD: hiding potential null
const name = user!.name;
document.getElementById("root")!.textContent;

// GOOD: explicit handling
const name = user?.name ?? "Unknown";
const el = document.getElementById("root");
if (el) el.textContent = value;
```

**`as` type casts bypassing type safety**
```typescript
// BAD: lying to the compiler
const data = response as UserData;

// GOOD: runtime validation
const data = UserDataSchema.parse(response);
```
- Acceptable for test fixtures with comment; flag in production code

**Async forEach (parallel execution, no await)**
```typescript
// BAD: fires and forgets
items.forEach(async (item) => {
  await processItem(item);
});

// GOOD: sequential
for (const item of items) {
  await processItem(item);
}
// GOOD: parallel with error handling
await Promise.all(items.map((item) => processItem(item)));
```

**Unhandled promise rejections**
- Floating promises (async calls without `await`, `.catch()`, or `void` operator)
- Missing `.catch()` on promise chains in non-async contexts

**JSON.parse without try/catch**
```typescript
// BAD: throws on invalid JSON
const data = JSON.parse(rawInput);

// GOOD: safe parsing
let data: unknown;
try {
  data = JSON.parse(rawInput);
} catch {
  return { error: "Invalid JSON" };
}
```

### Step 5 -- Medium Findings (severity: minor)

**React hooks dependency issues**
- Missing dependencies in `useEffect`, `useMemo`, `useCallback` dep arrays
- Object/array literals in dep arrays (new reference every render)
- Functions defined inside component used as deps without `useCallback`

**console.log in production code**
- `console.log` / `console.debug` in non-test, non-script files
- Acceptable: `console.error`, `console.warn` for error reporting

**Magic numbers**
- Numeric literals in logic without named constants
- Acceptable: 0, 1, -1, common HTTP status codes, array indices

**Missing error boundaries in React trees**
- Component trees without `ErrorBoundary` wrapping async data sources

### Step 6 -- Node.js Server Checks

**readFileSync in request handlers**
```typescript
// BAD: blocks event loop
app.get("/data", (req, res) => {
  const data = fs.readFileSync("large-file.json");
});

// GOOD: async
app.get("/data", async (req, res) => {
  const data = await fs.promises.readFile("large-file.json");
});
```

**Unvalidated process.env access**
```typescript
// BAD: undefined at runtime
const port = process.env.PORT;

// GOOD: validated with fallback or schema
const port = process.env.PORT ?? "3000";
// Better: zod schema validation of entire env
const env = envSchema.parse(process.env);
```

**Missing rate limiting on public endpoints**

**Missing helmet/security headers in Express apps**

### Step 7 -- Diagnostic Tool Cross-Reference

| Tool | Command | Validates |
|------|---------|-----------|
| tsc | `npx tsc --noEmit` | Type safety findings |
| eslint | `npx eslint {files}` | Style, pattern findings |
| vitest/jest | `npx vitest run --coverage` | Test coverage gaps |

## Output Format

```yaml
findings:
  - id: lang-typescript-N
    severity: critical|major|minor
    confidence: 0-100
    file: path
    line: N
    finding: "description"
    evidence: "code snippet"
    remediation: "how to fix"
    self_challenge:
      counter: "why this might be wrong"
      resolution: "why it stands or adjustment"
      adjusted_confidence: N
```
