# Handler: Prompt Enhance

## Purpose

Evaluate and optimize the user's brainstorm input for clarity and specificity before interrogation begins. Applies ai-prompt techniques #1 (Be Explicit Over Implicit) and #5 (Positive Framing). Skips optimization when the input is already specific. Shows before/after and auto-continues.

## Procedure

### Step 1 -- Evaluate Input Quality

Scan the user's input for vague markers:

**Vague markers (ES)**: mejorar, optimizar, arreglar, limpiar, refactorizar, actualizar, solucionar
**Vague markers (EN)**: improve, optimize, fix, clean up, refactor, update, solve

**Additional weakness signals**:
- No measurable criteria ("make it faster" vs "reduce response time to under 200ms")
- No specific component named ("fix the API" vs "fix the /api/v2/users endpoint")
- Negation-only framing ("stop it from crashing" vs "add retry logic with exponential backoff")

**Quality threshold**: input passes if it has ZERO vague markers AND contains at least one specific term (endpoint name, file path, metric, component name, or measurable criterion).

### Step 2 -- Decide: Skip or Optimize

**If input passes quality threshold**:
- Output: `Input ya optimo, continuando...`
- Proceed directly to interrogation (exit this handler).

**If input fails quality threshold**:
- Continue to Step 3.

### Step 3 -- Optimize

Apply these two techniques to the input:

**Technique #1 -- Be Explicit Over Implicit**:
- Replace vague verbs with specific actions ("mejorar seguridad" -> "implementar rate limiting y validacion de input en endpoints publicos")
- Add missing specificity where inferable from the term itself (not from the codebase -- no codebase reading in this step)
- Name the type of change: "add", "remove", "replace", "redesign", "extract", "split"

**Technique #5 -- Positive Framing**:
- Rewrite negations as positive targets ("no deberia fallar" -> "debe mantener disponibilidad ante errores de dependencias externas")
- State what to build, not what to avoid

**Preserve exploratory breadth**: if the input is intentionally broad ("repensar la arquitectura de auth", "explorar alternativas al sistema de plugins"), do NOT narrow it. Only clarify ambiguous terms within the broad scope. Exploratory inputs are broad by design -- respect that.

### Step 4 -- Display and Continue

Show the comparison, then auto-continue without waiting for confirmation:

```
**Input original:** [user's raw input]
**Input optimizado:** [enhanced version]
```

The optimized input becomes the working input for the interrogation phase. The user sees the transformation but is not blocked.

## Exit Criteria

- Input evaluated against quality threshold
- Either skipped (already specific) or optimized (vague markers found)
- If optimized: before/after displayed to user
- Control returns to SKILL.md step 2 (Interrogate)
