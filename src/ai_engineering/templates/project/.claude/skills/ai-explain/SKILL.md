---
name: ai-explain
description: "Engineer-grade technical explanations of code, concepts, patterns, and architecture with 3-tier depth control, ASCII diagrams, execution traces, and complexity analysis."
argument-hint: "quick|deep|architecture"
---


# Explain

## Purpose

Technical explanations of code, concepts, patterns, and architecture for engineers working in their own codebase. When a user asks "how does this work?", "trace this", or "why does this do X?", this skill delivers a structured, codebase-anchored explanation with execution traces, ASCII diagrams, and practical gotchas. Uses 3-tier depth control (Quick/Standard/Deep) to scale detail appropriately.

## Trigger

- Command: agent invokes explain skill or user requests explanation.
- Context: "explain", "how does this work", "what is this", "trace this", "why does this do X", "walk me through", "break this down", "teach me", user points at code and asks "why".

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"explain"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## Procedure

### Phase 1: Context Gathering

1. **Read project context** — silently internalize standards, stack.
   - Read `pyproject.toml` or equivalent — detect stack, dependencies, project identity.
   - Do not report this step to the user.

2. **Identify the subject** — classify into one of 6 categories:
   - **Code**: specific function, class, module, or block of code.
   - **Concept**: language feature, design principle, programming concept.
   - **Pattern**: design pattern, architectural pattern, coding idiom.
   - **Architecture**: system structure, data flow, component relationships.
   - **Error**: exception, failure mode, unexpected behavior.
   - **Difference**: comparison between two approaches, tools, or implementations.
   - If ambiguous, ask ONE clarifying question (not multiple).

3. **Search the codebase** — find real instances before explaining.
   - Use Grep/Glob to locate concrete instances in the project.
   - Codebase examples with `file:line` references are the primary evidence.
   - If not found in codebase, use generic example in the project's stack and note it.

### Phase 2: Depth Selection

4. **Determine explanation depth** — Quick / Standard / Deep based on user cues.

   | Depth | Trigger cues | Sections delivered |
   |-------|-------------|-------------------|
   | Quick | narrow question, "TL;DR", "brief", "short" | Summary + Walkthrough (3-5 steps) |
   | Standard | general question, no depth cues (DEFAULT) | Summary + Walkthrough + Diagram + Gotchas + Trace It |
   | Deep | "deep dive", "thorough", "teach me", "everything" | All sections including Context Map + Complexity Notes |

   - Standard is the default when no cues are present.
   - Analogy is optional at any depth — include only when it genuinely clarifies a complex abstraction.
   - After delivering, ask: "Want me to go deeper, trace a different path, or is this enough?"

### Phase 3: Explanation Delivery

5. **Summary** (all depths) — 1-2 technical sentences: what it does and why it exists.
   - Use precise technical terminology. No need to parenthetically define standard terms.
   - Must answer both "what" and "why."

   Format:
   ```
   **Summary**: [Subject] [what it does] [why it exists / what problem it solves].
   ```

6. **Analogy** (optional, any depth) — real-world mapping, only when it adds genuine value.
   - Include only when the concept benefits from structural comparison.
   - Map components of the concept to components of the analogy.
   - State where the analogy breaks down.
   - Omit entirely if the code is straightforward or if an analogy would oversimplify.

   Format:
   ```
   **Analogy**: Think of [subject] like [real-world thing]...
   [Component mappings]
   **Where it breaks down**: [Limitation]
   ```

7. **Walkthrough** (all depths) — numbered steps with `file:line` references.
   - Each step: what happens + why + `file:line` reference when applicable.
   - Build from entry point to outcome — follow the actual execution order.
   - For Quick depth: 3-5 steps maximum. For Standard/Deep: as many as needed.

   Format:
   ```
   **Walkthrough**:
   1. [What happens] — [why] (`path/to/file.py:42`)
   2. [What happens] — [why] (`path/to/file.py:67`)
   ...
   ```

8. **Diagram** (Standard + Deep) — ASCII art reflecting actual code structure.
   - Choose the diagram type that best fits the subject: data flow, call chain, state machine, component layout, or sequence diagram.
   - Always ASCII art — no Mermaid, no external tools.
   - Must reflect actual code, not idealized architecture.
   - Load `references/analysis-playbook.md` § "Diagram Templates" for format guidance.

   Format:
   ```
   **Diagram**:
   ```
   [ASCII diagram]
   ```
   ```

9. **Gotchas** (Standard + Deep) — practical pitfalls specific to this code.
   - Edge cases that will bite you: null paths, empty collections, boundary values.
   - Performance traps: hidden O(n^2), allocations in hot loops, blocking calls.
   - Concurrency hazards: race conditions, deadlocks, stale reads.
   - Subtle bugs: off-by-one, type coercion, implicit ordering assumptions.
   - Each gotcha must be specific to the code under review, not generic advice.

   Format:
   ```
   **Gotchas**:
   - [Specific pitfall] — [why it matters and when it triggers]
   - [Specific pitfall] — [why it matters and when it triggers]
   ```

10. **Trace It** (Standard + Deep) — execution trace through actual codebase paths.
    - Pick a concrete scenario (e.g., "user submits form", "CLI runs validate").
    - Walk through the actual call chain with `file:line` at each hop.
    - Show data transformation at each step: what goes in, what comes out.
    - Highlight decision points: conditionals, early returns, error branches.

    Format:
    ```
    **Trace It** (scenario: [description]):
    1. Entry: `path/file.py:10` — [what triggers this]
    2. Calls `function_name()` at `path/file.py:25` — input: [X], output: [Y]
    3. Branch: if [condition] at `path/file.py:30` — takes [true/false] path
    4. Returns [result] to caller at `path/file.py:12`
    ```

11. **Context Map** (Deep only) — when to use, when NOT to use, alternatives.
    - At least one "use when" scenario with concrete conditions.
    - At least one "do not use when" scenario with concrete conditions.
    - At least one alternative with tradeoff comparison.

    Format:
    ```
    **Context Map**:
    - **Use when**: [concrete scenario].
    - **Do not use when**: [concrete scenario] — instead use [alternative].
    - **Alternative**: [name] — tradeoff: [what you gain] vs [what you lose].
    ```

12. **Complexity Notes** (Deep only) — metrics, performance, concurrency.
    - Cyclomatic complexity estimate and assessment.
    - Nesting depth: max level and what contributes to it.
    - Performance characteristics: time/space complexity of hot paths.
    - Concurrency concerns: thread safety, async pitfalls (if applicable).
    - Load `references/analysis-playbook.md` § "Complexity Analysis Patterns" for methodology.

    Format:
    ```
    **Complexity Notes**:
    - **Cyclomatic**: ~N ([simple/moderate/complex])
    - **Nesting**: max N levels ([assessment])
    - **Performance**: [time/space complexity of critical path]
    - **Concurrency**: [thread safety assessment or "N/A"]
    ```

### Phase 4: Follow-Up

13. **Handle follow-ups** — extend, trace, go deeper/shallower, show in codebase.
    - "What about X?" — extend at same depth, covering X.
    - "I don't understand step N" — re-explain that step with more detail or a different angle.
    - "Can you go deeper?" — increase depth one level, delivering only the new sections.
    - "Trace a different path?" — re-run Trace It with a different scenario.
    - "Show me in my code" — find the concept in the actual codebase using Grep/Glob.
    - Follow-up depth transitions are smooth — do not re-explain already-covered sections.

### Headless Mode

When invoked by another agent (not directly by user) or in CI context:
- Default to Standard depth (skip depth negotiation).
- Skip follow-up prompts (Phase 4).
- If subject is ambiguous, select the most specific interpretation and note the assumption.
- Output the full explanation without asking for confirmation.

## When NOT to Use

- **Generating documentation** (README, CONTRIBUTING, guides) — use `docs` instead. Explain teaches concepts; docs produces documentation artifacts.
- **Simplifying existing docs** (reducing verbosity, removing duplication) — use `code-simplifier` instead.
- **Code changes** (refactoring, bug fixing) — use `refactor` or `debug` instead. Explain never writes code.
- **Changelog entries** — use `changelog` instead.

## Output Contract

- Explanation following the depth-appropriate section set (see Phase 2 table).
- Real codebase references with `file:line` locations used when available.
- ASCII diagrams at Standard and Deep depths reflecting actual code structure.
- Gotchas specific to the code under review, not generic warnings.
- Execution traces through actual codebase paths at Standard and Deep depths.
- Follow-up depth transitions smooth (no re-explaining already-covered sections).
- Output is explanation only — no code changes, no refactoring, no fixes.

## Governance Notes

### Language Rules

- Use precise technical terminology — the audience is engineers.
- No "basically", "essentially", "simply" — these words hide complexity.
- No "just" as minimizer (e.g., "you just need to...") — minimizes real difficulty.
- No "it's simple" or "it's obvious" — if it were, they would not be asking.
- Prefer "why" over "what" — understanding motivation beats memorizing mechanics.
- Active voice — "the function returns X", not "X is returned by the function."
- Use the reader's terminology — if they say "function", do not correct to "method" unless the distinction matters.

### Diagram Rules

- Always ASCII art. No Mermaid, no PlantUML, no external rendering tools.
- Diagrams must reflect the actual code structure, not an idealized version.
- Keep width under 70 characters for terminal readability.
- Label components with actual names from the codebase.
- Choose diagram type based on subject: data flow for pipelines, call chain for function relationships, state machine for lifecycle, sequence for multi-component interactions.

### Boundary Rules

- Assume technical competence — do not over-explain standard concepts.
- Never write code for the user — explain only. Refer to `refactor` or `debug` for action.
- Never make decisions for the user — explain tradeoffs, let them decide.
- Never dismiss a question — every "how does this work?" deserves a structured answer.

### Error Recovery

| Situation | Recovery |
|-----------|----------|
| Ambiguous subject | Ask ONE clarifying question |
| Subject too broad | Propose a scoped starting point, ask for confirmation |
| Unknown stack | Detect from `pyproject.toml`; if absent, ask |
| No good analogy | Omit the analogy — it is optional |
| User corrects you | Acknowledge directly, correct immediately, no hedging |
| Concept does not exist in codebase | Use generic example in project stack, note it is generic |
| Cannot trace execution | Explain why (e.g., dynamic dispatch) and provide best-effort trace |

## References

- `standards/framework/core.md` — governance structure and precedence.
- `.claude/skills/ai-explain/SKILL.md` — diagram templates, complexity patterns, edge case catalog.
- `.claude/skills/ai-quality/SKILL.md` — code understanding patterns.
- `.claude/skills/ai-architecture/SKILL.md` — architecture context methodology.
- `.claude/skills/ai-debug/SKILL.md` — root cause explanation patterns.
- `.claude/agents/ai-build.md` — agent that benefits from explanation capability.
- `.claude/agents/ai-verify.md` — agent that benefits from architecture explanations.
$ARGUMENTS
