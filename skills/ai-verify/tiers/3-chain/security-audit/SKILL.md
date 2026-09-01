---
name: security-audit
description: Audit the codebase for exploitable security issues — traces attacker-controlled input to dangerous sinks across HTTP handlers, background jobs, auth and access control, and anything shipped to the client, and checks dependencies for known CVEs. Use when asked for a security review or audit, to check for vulnerabilities or leaked secrets, or before shipping code that handles auth, user input, or external requests.
---

# Security audit

Find issues an attacker could actually exploit. The unit of work is a **trace**:
attacker-controlled input → the path it travels → the dangerous sink it reaches.
A finding without that trace is a guess.

Read `.claude/review/CONVENTIONS.md` first — stack detection, scope, severity,
false-positive gate, report format, and the **installed-version rule**. That last
one matters here more than anywhere: frameworks change their security defaults
between versions, and half of what a reviewer "knows" about a framework's
escaping, CSRF, or cookie behavior is version-specific. Verify against the
installed source before reporting a missing protection the framework now provides
by default — or an assumed protection it no longer does.

This is defensive review of code the user owns. Report vulnerabilities with
enough detail to fix them — the trace and the fix, not a weaponized exploit.

## 1. Map the trust boundaries for *this* stack

Before judging anything, write down which side of the wire each thing lives on.
The boundaries differ by architecture, so derive them rather than assuming:

- **Untrusted** — request bodies, query and path params, headers, cookies, form
  data, uploaded files, webhook payloads, message-queue contents, and anything
  from a third-party API. Also: anything a client can set that the server later
  trusts.
- **Server-only** — code paths that never ship to a client, and the secrets they
  read.
- **Public** — everything reachable from the client bundle or a downloadable
  artifact, every environment variable exposed by the framework's public-variable
  convention, and any config baked into a build. All of it is readable by anyone,
  regardless of whether it is obvious in the UI.

Identify the framework's specific mechanism for each: how it marks a module as
server-only, which env-var prefix it inlines into client builds, and where its
request-handling boundary sits. Get these from the installed docs or source.

## 2. Enumerate the attack surface

List every entry point **before** judging any of them. Grep is the right tool.
Depending on the stack, entry points include: HTTP route definitions and
handlers, RPC/GraphQL resolvers, server-invoked client callable functions,
webhook receivers, queue and cron consumers, CLI arguments, file watchers, and
deserialization of any stored blob.

For each, note who can reach it — unauthenticated, any authenticated user, or a
specific role — and confirm that from the code rather than the route name.

## 3. Checklist

**1. Authorization — the highest-yield category**
Every entry point needs, in this order: authentication → authorization *for this
specific resource* → input validation.

The dominant real bug is a **missing ownership check**: the handler authenticates
the user, then acts on an ID taken straight from the request without confirming
the user owns it (IDOR). Check every handler that reads an identifier from input.

Also: privilege checks performed in the client only, with no server re-check;
authorization enforced at a wrapper or layout layer that direct requests bypass;
role checks that pass for a superset of intended roles; **mass assignment**,
where a whole request body is spread into a persistence call and lets the caller
set fields they should not (`role`, `ownerId`, `isAdmin`, `balance`).

**2. Authentication and session handling**
Cookie flags (`httpOnly`, `secure`, `sameSite`), token expiry, rotation on
privilege change, and invalidation on logout. Tokens in URLs or logs. Password
storage using a modern password hash rather than a general-purpose digest.
Timing-unsafe comparison of secrets and tokens. Missing CSRF protection on
state-changing requests, judged against what the framework does by default. Route
protection patterns that under-cover: a matcher or prefix rule that guards
`/admin` but not `/admin/anything-beneath-it` is a real and common bug — enumerate
the routes that exist under each protected prefix and confirm coverage rather than
reading the rule and assuming intent.

**3. Input validation**
Unvalidated shapes reaching business logic — no schema, or hand-rolled partial
checks. Validation on the client only. Type coercion surprises. Numeric bounds,
string lengths, and collection sizes unchecked. File uploads without type, size,
and destination constraints.

**4. Injection sinks**
Trace any non-literal value reaching: raw SQL or query-filter string
concatenation; command execution with interpolated input; `eval` and its
equivalents; dynamic module loading on user input; template rendering with
autoescaping disabled; raw-HTML insertion APIs; unsanitized markdown or HTML
rendering; LDAP, XPath, and NoSQL query construction; deserialization of
untrusted data into arbitrary types; log injection of unescaped user content.
Also `href`/`src`/redirect targets built from user data (`javascript:` URIs).

**5. Secret exposure**
Secrets in variables the framework inlines into client builds. Server-only
modules imported into the client graph, pulling their secret access with them.
Secrets committed to source, or `.env` files not covered by `.gitignore` — check
the file, and check git history if the change touches secrets handling. Full
error objects, stack traces, or database errors returned to the client. Internal
IDs, paths, and infrastructure hostnames leaked in responses.

**6. SSRF and redirects**
Server-side requests to a URL derived from user input — the classic path to cloud
metadata endpoints and internal services. Allowlist by host, never blocklist.
Open redirects: a redirect target built from a query param without validating it
stays same-origin.

**7. Path traversal**
Any filesystem path built from user input. `..` sequences, absolute paths,
encoded separators, symlinks, and archive-extraction paths (zip-slip). File reads
and writes rooted at user-controlled values.

**8. Rate limiting and resource exhaustion**
Unbounded work triggered by an unauthenticated request: expensive queries,
uncapped uploads, unbounded pagination limits, unbounded recursion, catastrophic
regex backtracking on user input, decompression bombs. Auth endpoints without
throttling.

**9. Dependencies**
Run the ecosystem's audit tool and read the result — `npm audit --json`,
`pip-audit`, `cargo audit`, `govulncheck`, `bundler-audit`, `osv-scanner` as a
generic fallback. Report only vulnerabilities **reachable from this app's code**:
a CVE in a transitive dev-only dependency that never runs in production is a Low
at most, and say why. Also check for unpinned or suspicious direct dependencies.

**10. Transport, headers, and config**
CSP, frame-ancestors / `X-Frame-Options`, HSTS. CORS — `Access-Control-Allow-
Origin: *` combined with credentials is a real finding. Cache headers on
authenticated responses (a CDN-cached private response is a data leak). TLS
verification disabled anywhere. Debug modes, verbose errors, or admin surfaces
enabled in production config.

## 4. Method

1. Detect the stack and resolve scope per `CONVENTIONS.md`.
2. Map trust boundaries (§1) and enumerate the attack surface (§2). Do this
   completely before judging anything — a review that starts with the first
   interesting-looking file misses whole entry points.
3. For each entry point, follow the input forward through the code — reading the
   functions it calls — until it either reaches a sink or is provably validated.
4. **Verify pass.** For each candidate, construct the concrete attack: who sends
   what, from where, and what they get. If you cannot name the attacker and their
   gain, it is not a security finding — it may still be a `code-audit` finding, so
   say so and move on. Then look specifically for the mitigation you might have
   missed: a guard in middleware, a framework default (check the installed
   version), a validation layer upstream, a database constraint.
5. Report.

## 5. Report

Follow the output contract in `CONVENTIONS.md`. Write to
`.claude/reviews/security-audit-<stamp>.md`.

Each finding uses the standard fields, with **Trigger** written as the attack:

- **Trigger:** unauthenticated POST to `/api/items` with `{"ownerId": "<other user>"}`
- **Consequence:** writes to another user's record — horizontal privilege escalation
- **Fix:** derive `ownerId` from the session in the handler; never read it from the body

Severity: Critical for unauthenticated exploitation, data loss, or secret
exposure. High for authenticated privilege escalation or an issue needing a
plausible precondition. Do not inflate theoretical issues — a defense-in-depth
suggestion is Low, and labeling it Critical trains people to ignore the report.

The `Checked and clean` section matters more here than in other reviews: list the
entry points you traced and found properly guarded, so the reader knows the
surface was actually covered rather than sampled.
