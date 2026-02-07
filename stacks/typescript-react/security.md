# TypeScript/React Frontend Security Standards

Every TypeScript/React application MUST follow these security practices. Frontend security is a mandatory layer of defense, not optional hardening.

---

## Table of Contents

- [XSS Prevention](#xss-prevention)
- [CSRF Protection](#csrf-protection)
- [Secure Cookie Handling](#secure-cookie-handling)
- [Token Storage](#token-storage)
- [Input Validation](#input-validation)
- [Dependency Security](#dependency-security)
- [Environment Variables](#environment-variables)
- [Content Security Policy](#content-security-policy)
- [Sensitive Data in Client Bundle](#sensitive-data-in-client-bundle)

---

## XSS Prevention

### Never Use dangerouslySetInnerHTML

Do not use `dangerouslySetInnerHTML` unless you have sanitized the input with a trusted library. React escapes content by default -- `dangerouslySetInnerHTML` bypasses that protection.

```typescript
// DON'T: Unsanitized HTML injection
function Comment({ body }: { body: string }): React.ReactElement {
  return <div dangerouslySetInnerHTML={{ __html: body }} />;
  // If body contains <script>alert('xss')</script>, it will execute
}

// DO: Sanitize if you must render HTML
import DOMPurify from 'dompurify';

function Comment({ body }: { body: string }): React.ReactElement {
  const sanitized = DOMPurify.sanitize(body, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li'],
    ALLOWED_ATTR: ['href', 'target', 'rel'],
  });

  return <div dangerouslySetInnerHTML={{ __html: sanitized }} />;
}

// BEST: Use a markdown renderer instead of raw HTML
import ReactMarkdown from 'react-markdown';

function Comment({ body }: { body: string }): React.ReactElement {
  return <ReactMarkdown>{body}</ReactMarkdown>;
}
```

### Sanitize User Input in URLs

User-provided URLs can contain `javascript:` protocol injections.

```typescript
// DON'T: Unsanitized user URL
function UserLink({ url }: { url: string }): React.ReactElement {
  return <a href={url}>Visit</a>;
  // If url is "javascript:alert('xss')", clicking triggers script execution
}

// DO: Validate URL protocol
function sanitizeUrl(url: string): string {
  try {
    const parsed = new URL(url);
    if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
      return parsed.href;
    }
  } catch {
    // Invalid URL
  }
  return '#';
}

function UserLink({ url }: { url: string }): React.ReactElement {
  return (
    <a href={sanitizeUrl(url)} target="_blank" rel="noopener noreferrer">
      Visit
    </a>
  );
}
```

### External Links

All external links MUST include `rel="noopener noreferrer"` when using `target="_blank"`.

```typescript
// DO: Safe external link
<a href={externalUrl} target="_blank" rel="noopener noreferrer">
  External Site
</a>
```

### Do Not Construct HTML Strings

Never build HTML strings through concatenation or template literals. Always use React's JSX, which auto-escapes.

```typescript
// DON'T: HTML string construction
const html = `<div class="user">${userName}</div>`;
element.innerHTML = html; // XSS if userName contains <script>

// DO: Use JSX
return <div className="user">{userName}</div>; // React escapes userName
```

---

## CSRF Protection

### Token-Based Requests

For any state-changing request (POST, PUT, DELETE), include a CSRF token in the request headers. Coordinate with your backend on the token delivery mechanism.

```typescript
// shared/api/client.ts
async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  // Include CSRF token for state-changing requests
  if (method !== 'GET' && method !== 'HEAD') {
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      headers['X-CSRF-Token'] = csrfToken;
    }
  }

  const response = await fetch(url, { method, headers, body: JSON.stringify(body), credentials: 'same-origin' });
  return response.json() as Promise<T>;
}

function getCsrfToken(): string | null {
  // Read from meta tag (set by server-rendered page)
  return document.querySelector<HTMLMetaElement>('meta[name="csrf-token"]')?.content ?? null;
}
```

### SameSite Cookies

Ensure your backend sets cookies with `SameSite=Strict` or `SameSite=Lax`. The frontend cannot set this, but should verify it is configured correctly during security reviews.

---

## Secure Cookie Handling

### Cookie Attributes

When the frontend needs to set cookies (rare -- prefer letting the backend handle auth cookies), always set security attributes.

```typescript
// DO: Set secure cookie attributes
function setCookie(name: string, value: string, days: number): void {
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = [
    `${encodeURIComponent(name)}=${encodeURIComponent(value)}`,
    `expires=${expires}`,
    'path=/',
    'Secure',          // Only sent over HTTPS
    'SameSite=Strict', // Not sent with cross-site requests
    // Note: HttpOnly cannot be set from JavaScript (server only)
  ].join('; ');
}
```

### Do Not Read Auth Cookies in JavaScript

Authentication cookies MUST be `HttpOnly` (set by the server, invisible to JavaScript). If your code reads auth tokens from `document.cookie`, the architecture is wrong.

---

## Token Storage

### Never Store Auth Tokens in localStorage

`localStorage` is accessible to any JavaScript running on the page, including XSS payloads and third-party scripts. Auth tokens stored in `localStorage` can be stolen.

```typescript
// DON'T: Store tokens in localStorage
localStorage.setItem('authToken', token);
const token = localStorage.getItem('authToken');

// DON'T: Store tokens in sessionStorage (same vulnerability)
sessionStorage.setItem('authToken', token);
```

### Preferred Token Storage

Use one of these approaches, in order of preference:

1. **HttpOnly, Secure, SameSite cookies** (set by the server). The frontend never sees or touches the token. The browser automatically includes it in requests.

2. **In-memory only** (for SPAs with short-lived sessions). Store the token in a JavaScript variable or React state/context. The token is lost on page refresh, which is acceptable if your backend supports silent refresh via a refresh token in an HttpOnly cookie.

```typescript
// DO: In-memory token storage
// shared/auth/token-store.ts
let accessToken: string | null = null;

export function setAccessToken(token: string): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function clearAccessToken(): void {
  accessToken = null;
}
```

3. **Refresh token in HttpOnly cookie + access token in memory**. The backend sets a long-lived refresh token as an HttpOnly cookie. The frontend stores the short-lived access token in memory and uses the refresh token cookie to get a new access token when it expires.

### What IS Safe to Store in localStorage

- User preferences (theme, language, sidebar state).
- Non-sensitive UI state.
- Cache keys and non-sensitive cache data.

---

## Input Validation

### Validate on Both Client and Server

Client-side validation is for user experience. Server-side validation is for security. Never trust client-only validation.

```typescript
// DO: Client-side validation for UX
const CreateUserSchema = z.object({
  name: z.string().min(1, 'Name is required').max(255, 'Name too long'),
  email: z.string().email('Invalid email'),
  role: z.enum(['admin', 'editor', 'viewer']),
});

// The server MUST also validate this data independently.
// A malicious client can bypass all frontend validation.
```

### Sanitize Before Display

Even if data comes from your own API, sanitize it before rendering if it was originally user-provided. A compromised API or database can serve XSS payloads.

```typescript
// DO: Treat all user-generated content as untrusted
function UserBio({ bio }: { bio: string }): React.ReactElement {
  // React JSX auto-escapes, so this is safe:
  return <p>{bio}</p>;

  // But if you must render HTML:
  // return <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(bio) }} />;
}
```

### Validate URL Parameters

URL parameters and search params are user input. Validate them before using them in API calls or rendering.

```typescript
// DO: Validate route params
function UserProfilePage(): React.ReactElement {
  const { userId } = useParams<{ userId: string }>();

  // Validate the param format before using it
  const validId = z.string().uuid().safeParse(userId);
  if (!validId.success) {
    return <NotFound />;
  }

  const { user } = useUser(validId.data);
  // ...
}
```

---

## Dependency Security

### npm Audit

Run `npm audit` (or `pnpm audit`) in CI on every build. Fail the build on critical or high severity vulnerabilities.

```yaml
# CI pipeline step
- name: Security audit
  run: pnpm audit --audit-level=high
```

### Lock File Integrity

Always commit your lock file (`package-lock.json`, `pnpm-lock.yaml`). Use `--frozen-lockfile` in CI to ensure reproducible builds.

```yaml
# CI pipeline step
- name: Install dependencies
  run: pnpm install --frozen-lockfile
```

### Minimize Dependencies

Before adding a dependency:

1. Check the package's download count, maintenance status, and known vulnerabilities.
2. Assess whether you can implement the needed functionality in-house (especially for small utilities).
3. Prefer well-known, actively maintained packages with a security policy.
4. Pin exact versions for critical dependencies.

### Renovate / Dependabot

Configure automated dependency updates. Review each update before merging, especially for packages that handle:

- Authentication and authorization
- Cryptography
- HTML sanitization
- URL parsing

---

## Environment Variables

### Client-Side Exposure

Environment variables prefixed with `VITE_` (Vite) or `NEXT_PUBLIC_` (Next.js) are embedded in the client bundle and visible to anyone who views the page source.

```typescript
// These are PUBLIC — anyone can see them:
const apiUrl = import.meta.env.VITE_API_URL;          // OK: Public API endpoint
const analyticsId = import.meta.env.VITE_ANALYTICS_ID; // OK: Public tracking ID

// These MUST NEVER be in client-side env vars:
// VITE_DATABASE_URL        — exposes database credentials
// VITE_API_SECRET_KEY      — exposes server secrets
// VITE_STRIPE_SECRET_KEY   — exposes payment secrets
// NEXT_PUBLIC_JWT_SECRET   — exposes token signing key
```

### Rules

1. Never put API secrets, database credentials, or signing keys in `VITE_` or `NEXT_PUBLIC_` variables.
2. Do not hardcode secrets in source code.
3. Use server-side environment variables for secrets, and proxy requests through your backend.
4. Document all required environment variables in a `.env.example` file (without actual values).

```bash
# .env.example
VITE_API_URL=https://api.example.com
VITE_ANALYTICS_ID=UA-XXXXXXXXX
# Server-side only (not prefixed with VITE_):
# DATABASE_URL=postgresql://...
# JWT_SECRET=...
```

### Never Commit .env Files

Add `.env*` (except `.env.example`) to `.gitignore`. Verify this is in place in every project.

```gitignore
# .gitignore
.env
.env.local
.env.development
.env.production
```

---

## Content Security Policy

### Configure CSP Headers

Set Content Security Policy headers on your server or CDN to restrict what resources the browser is allowed to load.

```
Content-Security-Policy:
  default-src 'self';
  script-src 'self';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https:;
  font-src 'self';
  connect-src 'self' https://api.yourapp.com;
  frame-ancestors 'none';
  base-uri 'self';
  form-action 'self';
```

### Frontend Implications

1. Do not use inline `<script>` tags. Bundle all JavaScript.
2. Do not use `eval()`, `new Function()`, or `setTimeout` with string arguments.
3. Do not load scripts from third-party CDNs unless they are explicitly allowlisted in the CSP.
4. Prefer `'self'` for all resource types and add specific origins only when needed.

```typescript
// DON'T: eval or Function constructor
eval(userInput);
const fn = new Function('return ' + userInput);
setTimeout('alert("hello")', 0); // String argument = eval

// DO: Use proper functions
const fn = (input: string): number => parseInt(input, 10);
setTimeout(() => { alert('hello'); }, 0); // Function argument = safe
```

### CSP Nonce for Inline Scripts

If you must use inline scripts (e.g., for analytics), use a nonce-based CSP. The server generates a random nonce per request and includes it in both the CSP header and the script tag.

```html
<!-- Server sets header: Content-Security-Policy: script-src 'nonce-abc123' -->
<script nonce="abc123">
  // Analytics initialization
</script>
```

---

## Sensitive Data in Client Bundle

### What Must Never Be in the Bundle

1. API secret keys or private keys.
2. Database connection strings.
3. Encryption keys or JWT signing secrets.
4. Internal service URLs that should not be public.
5. User PII that the current user should not see (other users' emails, etc.).
6. Admin-only configuration.

### How to Verify

1. Build the production bundle: `pnpm build`.
2. Search the output for known secret patterns:

```bash
# Check for leaked secrets in the bundle
grep -r "sk_live\|sk_test\|PRIVATE_KEY\|-----BEGIN" dist/
grep -r "password\|secret\|token" dist/assets/*.js
```

3. Use a bundle analyzer to inspect all included code:

```bash
npx vite-bundle-visualizer
```

### Source Maps

Never deploy source maps to production. They expose your original source code to anyone who opens DevTools.

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    sourcemap: false, // Never true in production
  },
});
```

If you need source maps for error tracking (e.g., Sentry), upload them to the error tracking service and do not serve them publicly.

### Logging

Never log sensitive data (tokens, passwords, PII) to the browser console in production.

```typescript
// DO: Strip debug logs in production
if (import.meta.env.DEV) {
  console.log('Debug info:', data);
}

// DON'T: Log sensitive data
console.log('User token:', token);
console.log('API response:', { ...response, password: user.password });
```

Configure your build tool to strip `console.log` statements from production builds:

```typescript
// vite.config.ts
export default defineConfig({
  esbuild: {
    drop: import.meta.env.PROD ? ['console', 'debugger'] : [],
  },
});
```
