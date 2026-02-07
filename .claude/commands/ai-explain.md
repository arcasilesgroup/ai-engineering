# /ai-explain — Feynman-Style Explanation Workflow

This skill defines the step-by-step workflow for producing clear, structured, jargon-free explanations of code, concepts, patterns, and architecture. It follows the Feynman technique: if you cannot explain it simply, you do not understand it well enough. Every explanation is anchored by an analogy, builds understanding in layers, and uses the reader's own technology stack for examples.

---

## Session Preamble (execute silently)

Before any user-visible action, silently internalize project context:

1. Read `.ai-engineering/knowledge/learnings.md` — lessons learned during development
2. Read `.ai-engineering/knowledge/patterns.md` — established conventions (use for codebase-specific examples)
3. Read `.ai-engineering/knowledge/anti-patterns.md` — known mistakes to avoid
4. Detect the project stack from package.json, .csproj, pyproject.toml, or equivalent

Do not report this step to the user. Internalize it as context for the explanation.

---

## 3-Tier Depth Selection

Always offer three levels of depth. Start with the level that best matches the user's question, and explicitly offer to go deeper or shallower:

```
TL;DR (1 paragraph): Quick understanding — for when you need the gist in 30 seconds.
Standard (2-3 sections): Solid understanding — analogy, step-by-step, common pitfalls.
Deep Dive (full): Complete mastery — everything above plus context map, advanced examples, and codebase references.
```

Default to **Standard** unless the user signals otherwise. After delivering the explanation, ask: "Want me to go deeper, or is this enough?"

---

## Codebase Context

When explaining a concept, **always look for examples in the current codebase first**. A real example from the user's own project is 10x more valuable than a generic one.

```bash
# Search for the concept in the codebase
grep -r "<concept>" src/
# Find related files
find src/ -name "*<concept>*"
```

If found, use the real code as the primary example and annotate it. If not found, use a generic example in the project's stack.

---

## Trigger

- User invokes `/ai-explain`
- User says "explain", "how does this work", "what is this", "ELI5", "teach me", "break this down", "walk me through", or similar intent
- User points at code and asks "why" or "what does this do"

---

## Step 1: Identify What to Explain

Determine the subject of the explanation. It falls into one of these categories:

### Categories

| Category         | Examples                                                                                |
| ---------------- | --------------------------------------------------------------------------------------- |
| **Code**         | A specific function, class, file, or code block the user points to                      |
| **Concept**      | A programming concept (closures, dependency injection, event loops, CQRS)               |
| **Pattern**      | A design pattern or architectural pattern (observer, middleware, saga, circuit breaker) |
| **Architecture** | How a system, module, or flow works end-to-end                                          |
| **Error**        | Why an error occurred, what it means, and how to fix it                                 |
| **Difference**   | Comparing two approaches, tools, or concepts ("X vs Y", "when to use X over Y")         |

### If the subject is ambiguous:

Ask a focused clarifying question:

```
I can explain this at different levels. Which are you looking for?
  1. The specific code in this file (what it does, line by line)
  2. The concept behind it (e.g., what middleware is and why it exists)
  3. The architectural pattern (how this fits into the larger system)
```

Do not ask more than one clarifying question. If the user's intent is reasonably clear, proceed with your best interpretation and adjust if they redirect.

---

## Step 2: Determine Depth

Choose the explanation depth based on context cues:

### Quick (2-3 minutes to read)

**When to use:**

- User asks a narrow question ("what does this line do?")
- User seems experienced and wants a fast answer
- The subject is a single function, variable, or small code block
- User says "quick", "brief", "in short", "TL;DR"

**Includes:** One-liner, Analogy, Step-by-Step (abbreviated)

### Standard (5-7 minutes to read)

**When to use:**

- User asks a general question ("how does this work?", "explain this")
- No depth hints are given (this is the default)
- The subject is a concept, pattern, or moderate-sized code block

**Includes:** One-liner, Analogy, Step-by-Step, Gap Check, Prove It

### Deep (10-15 minutes to read)

**When to use:**

- User asks for thorough understanding ("teach me", "deep dive", "I want to really understand")
- User says "ELI5" (they want fundamentals, not brevity)
- The subject is an architectural pattern, complex system, or something the user is clearly struggling with

**Includes:** One-liner, Analogy, Step-by-Step, Gap Check, Prove It, Context Map

If unsure, default to **Standard**.

---

## Step 3: Produce the Explanation

Every explanation follows this structure. Sections are included or excluded based on the depth determined in Step 2.

### Section 1: One-Liner

A single sentence that captures **what** it is and **why** it exists. No jargon. No qualifications. No "basically" or "essentially."

**Rules:**

- Maximum one sentence.
- Must answer both "what" and "why."
- A non-technical person should understand the gist.
- No technical terms without an immediate parenthetical definition.

**Examples:**

```
Middleware is code that runs between receiving a request and sending a response,
letting you add shared behavior (logging, authentication, rate limiting) to every
request without repeating yourself in each endpoint.
```

```
A closure is a function that remembers the variables from the place where it was
created, even after that place no longer exists — which is how callbacks and event
handlers hold onto data they need later.
```

```
This function takes a list of database records, groups them by user ID, and returns
a dictionary where each key is a user and the value is their list of orders —
because the frontend needs orders organized per user, not in a flat list.
```

**Anti-patterns (never do these):**

- "It's basically a way to..." (filler, remove "basically")
- "Simply put, ..." (patronizing, remove "simply put")
- "It's kind of like a ..." (vague, commit to a concrete definition)

### Section 2: The Analogy

A real-world mapping that makes the abstract concrete. This section is **mandatory** at every depth level.

**Rules:**

- The analogy must map to something the reader has direct experience with (physical objects, daily activities, common systems).
- It must be structurally accurate, not just superficially similar. The relationships between parts of the analogy must mirror the relationships in the technical concept.
- It must include where the analogy breaks down. Every analogy has limits — state them.
- Avoid overused analogies unless they are genuinely the best fit. ("It's like a factory" is fine for the Factory pattern. "It's like a pipe" is fine for Unix pipes. Do not force novelty.)

**Format:**

```
Think of middleware like airport security checkpoints. Every passenger (request)
passes through the same series of checkpoints (middleware functions) before reaching
their gate (route handler). Each checkpoint does one thing: check your ID
(authentication), scan your bag (input validation), weigh your luggage (rate
limiting). Checkpoints can let you through, send you back (reject the request),
or add a tag to your boarding pass (modify the request).

Where this analogy breaks down: Unlike airport checkpoints which have a fixed order
set by the airport, middleware order is defined by the developer and can vary per
route. Also, middleware can run *after* the response too (response logging), which
has no airport equivalent.
```

### Section 3: Step-by-Step Breakdown

A numbered walkthrough where each step explains **what happens** and **why it matters.**

**Rules:**

- Each step is one logical operation.
- Each step has two parts: "What happens" and "Why it matters."
- Use the reader's technology stack for code examples (TypeScript for a TS project, Python for a Python project, etc.).
- Number the steps. Readers need to track progression.
- If explaining code, reference specific line numbers or variable names.
- If explaining a concept, build from simple to complex — each step must be understandable given only the previous steps.

**Format:**

```
How the token refresh flow works:

1. **Client sends a request with an expired access token.**
   What happens: The auth middleware reads the Authorization header, decodes the JWT,
   and finds that `exp` is in the past.
   Why it matters: Instead of immediately returning 401, the system checks if the
   request also includes a valid refresh token — giving the user a seamless experience.

2. **The refresh token is validated against the database.**
   What happens: The server looks up the refresh token in the `refresh_tokens` table,
   checking that it exists, belongs to this user, and has not expired or been revoked.
   Why it matters: Refresh tokens are long-lived, so they need server-side validation
   (unlike access tokens which are stateless). This prevents stolen refresh tokens
   from working after revocation.

3. **A new access token and refresh token are issued.**
   What happens: The server generates a fresh access token (short-lived, 15 minutes)
   and a new refresh token (long-lived, 7 days), stores the new refresh token, and
   revokes the old one.
   Why it matters: Token rotation — issuing a new refresh token on each use — means
   a stolen refresh token can only be used once. If the attacker and real user both
   try to use the same refresh token, the second attempt fails, alerting the system
   to a potential breach.
```

### Section 4: Gap Check

Address the most common misconception or misunderstanding about this subject.

**Rules:**

- Start with "The part most people get wrong is..." or an equivalent direct framing.
- Identify a specific, common misconception — not a general "be careful."
- Explain why the misconception is wrong and what the correct understanding is.
- This section is included in Standard and Deep depth.

**Format:**

```
The part most people get wrong: Refresh tokens are NOT just "access tokens that
last longer." They serve a fundamentally different purpose. Access tokens are
stateless (the server does not track them) and short-lived (minutes). Refresh
tokens are stateful (stored in a database) and long-lived (days/weeks). This
distinction is what makes token rotation and revocation possible. If you treat
refresh tokens like long-lived access tokens, you lose the ability to revoke
access and detect token theft.
```

### Section 5: Prove It

A minimal, runnable code example that demonstrates the concept in action.

**Rules:**

- The example must be runnable as-is (or with minimal setup that is clearly documented).
- Use the reader's stack. If they work in Python, the example is in Python. If TypeScript, TypeScript.
- The example should be minimal — just enough to demonstrate the concept, nothing more.
- Include comments that connect the code to the step-by-step breakdown.
- If the concept is purely architectural (no single code example captures it), provide a simplified pseudocode example or a diagram instead.
- This section is included in Standard and Deep depth. Omitted for Quick.

**Format:**

```typescript
// Minimal middleware example — run with: npx ts-node example.ts
import express from "express";

const app = express();

// Middleware 1: Log every request (checkpoint 1)
app.use((req, res, next) => {
  console.log(`${req.method} ${req.path}`);
  next(); // Pass to next middleware
});

// Middleware 2: Check for API key (checkpoint 2)
app.use((req, res, next) => {
  if (!req.headers["x-api-key"]) {
    return res.status(401).json({ error: "API key required" });
    // Request rejected here — never reaches the route
  }
  next(); // API key present, continue
});

// Route handler: Only reached if all middleware passed
app.get("/data", (req, res) => {
  res.json({ message: "You passed all checkpoints" });
});

app.listen(3000);
```

### Section 6: Context Map

Explain where this concept fits in the larger picture: when to use it, when NOT to use it, and what the alternatives are.

**Rules:**

- Include at least one "when NOT to use this" scenario.
- Include at least one alternative with a brief tradeoff comparison.
- Do not oversell the concept. Every pattern has a cost.
- This section is included only in Deep depth.

**Format:**

```
Where middleware fits:

When to use it:
  - Cross-cutting concerns that apply to many routes (auth, logging, CORS, rate limiting)
  - Request/response transformation that should be consistent across endpoints
  - Error handling that needs a centralized catch-all

When NOT to use it:
  - Business logic specific to one endpoint. That belongs in the route handler, not middleware.
  - Complex conditional logic ("apply this middleware only if the user is in group X and
    the request contains header Y"). Overly conditional middleware becomes impossible to
    debug. Move the logic into the handler.
  - Performance-critical paths where the middleware chain adds measurable latency.
    Measure before optimizing, but be aware that 15 middleware functions on every
    request adds up.

Alternatives and tradeoffs:
  - Decorators (NestJS, Python Flask): Same concept, different syntax. Better for
    per-route granularity. Worse for global concerns.
  - Aspect-Oriented Programming (AOP): More powerful (can intercept any function
    call, not just HTTP requests). More complex and harder to reason about.
  - Filters / Interceptors (.NET, Spring): Framework-specific middleware equivalents
    with richer lifecycle hooks but tighter framework coupling.
```

---

## Rules and Constraints

These apply to every explanation at every depth.

### Language Rules

- **No jargon without definition.** Every technical term must be defined on first use, either inline or in parentheses. If a term was defined in a previous section, it does not need re-definition.
- **No "it's simple" or "it's obvious."** If it were simple or obvious, the user would not be asking. These phrases make the reader feel stupid for not already knowing. Never use them.
- **No "just" as a minimizer.** "Just add a middleware" implies it is trivial. Remove "just" and say what to do.
- **No "basically" or "essentially."** These are filler words that add nothing. Remove them and say what you mean directly.
- **Prefer "why" over "what."** The reader can often see _what_ the code does. They need to understand _why_ it does it that way and _why_ it matters.
- **Use active voice.** "The server validates the token" not "The token is validated by the server."
- **Use the reader's terminology.** If the codebase uses "handler" instead of "controller", use "handler."

### Example Rules

- Always use the reader's technology stack for examples. If the project is Python, do not show JavaScript examples.
- If the reader's stack is unknown, ask: "Which language/framework would be most useful for examples?"
- Examples must compile/run. Do not write pseudocode unless the concept is purely architectural.
- Examples must be minimal. If the example needs more than 30 lines to demonstrate the concept, it is doing too much.

### Structural Rules

- The One-Liner always comes first. It is the anchor.
- The Analogy always comes second. It makes the abstract concrete before diving into details.
- The Step-by-Step always comes third. It builds systematic understanding.
- Gap Check, Prove It, and Context Map follow in that order when included.
- Never skip the Analogy. It is mandatory at every depth.

---

## Handling Follow-Up Questions

After delivering an explanation, the user may ask follow-up questions:

- **"What about X?"** — Extend the explanation to cover X, maintaining the same depth and style.
- **"I don't understand step N"** — Re-explain that step with a different analogy or more granular breakdown. Do not repeat the same words.
- **"Can you go deeper?"** — Increase depth by one level (Quick to Standard, Standard to Deep) and add the sections that were previously omitted.
- **"Can you give me a simpler version?"** — Decrease depth by one level. Strip to One-Liner, Analogy, and abbreviated Step-by-Step.
- **"Show me in my code"** — Find the concept in the actual codebase and explain it using the real files and functions, not abstract examples.

---

## Error Recovery

| Failure                                             | Action                                                                                                                                               |
| --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Subject is unclear                                  | Ask one focused clarifying question. Do not ask multiple.                                                                                            |
| Subject is too broad ("explain this whole project") | Propose a scoped starting point: "This project has 4 major systems. Want me to start with [the one most relevant to their recent work]?"             |
| Reader's stack is unknown                           | Ask which language/framework to use for examples. Default to the project's primary stack if detectable.                                              |
| Concept has no good analogy                         | Use a structural comparison instead: "This works like [simpler concept the reader knows], except [key difference]." Never skip the analogy section.  |
| The explanation is wrong                            | If the user corrects you, acknowledge the error directly, explain what you got wrong, and provide the corrected explanation. Do not hedge or defend. |

---

## Learning Capture (on completion)

If during the explanation you discovered undocumented patterns or knowledge:

1. **Undocumented pattern** (e.g., the codebase uses a pattern that isn't in knowledge/patterns.md) → Propose adding it
2. **Common confusion** (e.g., this concept is frequently misunderstood in this codebase) → Propose adding to `knowledge/learnings.md`
3. **Missing documentation** (e.g., a critical module has no explanation) → Note it for the user

Ask the user before writing to these files. Never modify them silently.

---

## What This Skill Does NOT Do

- It does not write code for the user. It explains code and concepts. Use `/ai-implement` to write code.
- It does not review code. It explains what code does and why. Use `/ai-review` to find issues.
- It does not make decisions for the user. If the user asks "should I use X or Y?", explain the tradeoffs and let them decide.
- It does not teach entire courses. It explains specific things well. If the user needs a curriculum, suggest resources rather than trying to compress a course into one response.
- It does not assume the reader's skill level. It starts from the One-Liner (accessible to everyone) and builds up. The reader self-selects depth by asking for more or moving on.
