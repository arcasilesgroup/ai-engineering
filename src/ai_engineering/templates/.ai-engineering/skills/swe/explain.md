# Explain

## Purpose

Feynman-style explanations of code, concepts, patterns, and architecture. When a user asks "how does this work?" or "what is this?", this skill delivers a structured, layered explanation anchored by analogy and grounded in the project's own codebase. Uses 3-tier depth control (Quick/Standard/Deep) and 6 explanation sections to ensure consistent, jargon-free understanding. If you cannot explain it simply, you do not understand it well enough.

## Trigger

- Command: agent invokes explain skill or user requests explanation.
- Context: "explain", "how does this work", "what is this", "ELI5", "teach me", "break this down", "walk me through", user points at code and asks "why".

## Procedure

### Phase 1: Context Gathering

1. **Read project context** — silently internalize learnings, standards, stack.
   - Read `context/learnings.md` — institutional knowledge, past patterns.
   - Read `pyproject.toml` — detect stack, dependencies, project identity.
   - Do not report this step to the user.

2. **Identify the subject** — classify into one of 6 categories:
   - **Code**: specific function, class, module, or block of code.
   - **Concept**: language feature, design principle, programming concept.
   - **Pattern**: design pattern, architectural pattern, coding idiom.
   - **Architecture**: system structure, data flow, component relationships.
   - **Error**: exception, failure mode, unexpected behavior.
   - **Difference**: comparison between two approaches, tools, or implementations.
   - If ambiguous, ask ONE clarifying question (not multiple).

3. **Search the codebase** — find real examples of the concept before explaining.
   - Use Grep/Glob to locate concrete instances in the project.
   - Codebase examples are 10x more valuable than generic ones.
   - If found, use as primary example. If not, use generic example in the project's stack.

### Phase 2: Depth Selection

4. **Determine explanation depth** — Quick / Standard / Deep based on user cues.

   | Depth | Trigger cues | Sections delivered |
   |-------|-------------|-------------------|
   | Quick | narrow question, "TL;DR", "brief", "short" | One-Liner + Analogy + abbreviated Step-by-Step |
   | Standard | general question, no depth cues (DEFAULT) | One-Liner + Analogy + Step-by-Step + Gap Check + Prove It |
   | Deep | "teach me", "deep dive", "ELI5", "thorough" | All 6 sections |

   - Standard is the default when no cues are present.
   - After delivering, ask: "Want me to go deeper, or is this enough?"

### Phase 3: Explanation Delivery

5. **One-Liner** — single sentence: what + why.
   - Must answer both "what is it?" and "why does it matter?"
   - No jargon without immediate parenthetical definition.
   - A non-technical person should understand the gist.

   Format:
   ```
   **One-liner**: [Subject] is [what it does] so that [why it matters].
   ```

6. **Analogy** — real-world mapping. MANDATORY at every depth.
   - Must be structurally accurate, not just superficially similar.
   - Map each component of the concept to a component of the analogy.
   - Must include where the analogy breaks down.

   Format:
   ```
   **Analogy**: Think of [subject] like [real-world thing]...
   [Component mappings]
   **Where it breaks down**: [Limitation of the analogy]
   ```

7. **Step-by-Step** — numbered walkthrough.
   - Each step: "what happens" + "why it matters."
   - Reference specific line numbers or variable names when explaining code.
   - Build from simple to complex — each step depends only on previous steps.
   - For Quick depth: 3-5 steps maximum. For Standard/Deep: as many as needed.

   Format:
   ```
   **Step-by-step**:
   1. [What happens] — [why it matters].
   2. [What happens] — [why it matters].
   ...
   ```

8. **Gap Check** (Standard + Deep only) — most common misconception.
   - Start with "The part most people get wrong is..."
   - Name a specific misconception, not general advice like "be careful."
   - Explain why the misconception is wrong and what the truth is.

   Format:
   ```
   **Gap check**: The part most people get wrong is [specific misconception].
   [Why it's wrong and what the truth is.]
   ```

9. **Prove It** (Standard + Deep only) — minimal, runnable code example in project stack.
   - Must be runnable as-is. Max ~30 lines.
   - Comments connect code to step-by-step breakdown.
   - Detect stack from `pyproject.toml`. Default to Python if unknown.
   - If purely architectural, use simplified pseudocode or ASCII diagram instead.

   Format:
   ```
   **Prove it**:
   ```[language]
   # Step 1: [maps to step-by-step #1]
   [code]
   # Step 2: [maps to step-by-step #2]
   [code]
   ```
   ```

10. **Context Map** (Deep only) — when to use, when NOT to use, alternatives.
    - At least one "when to use" scenario with concrete conditions.
    - At least one "when NOT to use" scenario with concrete conditions.
    - At least one alternative with tradeoff comparison.

    Format:
    ```
    **Context map**:
    - **Use when**: [concrete scenario].
    - **Do not use when**: [concrete scenario] — instead use [alternative].
    - **Alternative**: [name] — tradeoff: [what you gain] vs [what you lose].
    ```

### Phase 4: Follow-Up

11. **Handle follow-ups** — extend, re-explain, go deeper/shallower, show in codebase.
    - "What about X?" → extend at same depth, covering X.
    - "I don't understand step N" → re-explain that step with a different analogy.
    - "Can you go deeper?" → increase depth one level, delivering only the new sections.
    - "Show me in my code" → find the concept in the actual codebase using Grep/Glob.
    - Follow-up depth transitions are smooth — do not re-explain already-covered sections.

12. **Capture learnings** — propose additions to `context/learnings.md` if undocumented patterns found.
    - Only propose if the explanation revealed a pattern not yet in learnings.
    - Ask user before writing. Do not write without confirmation.

## Output Contract

- Explanation following the depth-appropriate section set (see Phase 2 table).
- Real codebase examples used when available.
- No jargon without inline definition.
- Analogy present at every depth level.
- Follow-up depth transitions smooth (no re-explaining already-covered sections).
- Output is explanation only — no code changes, no refactoring, no fixes.

## Governance Notes

### Language Rules

- No jargon without immediate parenthetical definition.
- No "basically", "essentially", "simply" — these words hide complexity.
- No "just" as minimizer (e.g., "you just need to...") — minimizes real difficulty.
- No "it's simple" or "it's obvious" — if it were, they would not be asking.
- Prefer "why" over "what" — understanding motivation beats memorizing mechanics.
- Active voice — "the function returns X", not "X is returned by the function."
- Use the reader's terminology — if they say "function", do not correct to "method" unless the distinction matters.

### Example Rules

- Examples must use the project's technology stack.
- If stack is unknown, detect from `pyproject.toml`.
- Codebase examples take priority over generic examples.
- Code examples must be runnable as-is (no pseudocode in Prove It, except for architecture).

### Boundary Rules

- Never assume the reader's skill level — start accessible, build up.
- Never write code for the user — explain only. Refer to `/swe:refactor` or `/swe:debug` for action.
- Never make decisions for the user — explain tradeoffs, let them decide.
- Never dismiss a question — every "how does this work?" deserves a structured answer.

### Error Recovery

| Situation | Recovery |
|-----------|----------|
| Ambiguous subject | Ask ONE clarifying question |
| Subject too broad | Propose a scoped starting point, ask for confirmation |
| Unknown stack | Detect from `pyproject.toml`; if absent, ask |
| No good analogy | Use structural comparison instead of forced analogy |
| User corrects you | Acknowledge directly, correct immediately, no hedging |
| Concept does not exist in codebase | Use generic example in project stack, note it is generic |

## References

- `context/learnings.md` — institutional knowledge for codebase-specific context.
- `standards/framework/core.md` — governance structure and precedence.
- `skills/swe/code-review.md` — code understanding patterns.
- `skills/swe/architecture-analysis.md` — architecture context methodology.
- `skills/swe/debug.md` — root cause explanation patterns.
- `skills/swe/prompt-engineer.md` — Chain of Thought framework for structured reasoning.
- `agents/debugger.md` — agent that benefits from explanation capability.
- `agents/architect.md` — agent that benefits from architecture explanations.
