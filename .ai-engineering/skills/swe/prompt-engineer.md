# Prompt Engineer

## Purpose

Advanced prompt engineering skill for crafting high-quality AI interactions. Covers intent analysis, framework selection, blending strategies for complex tasks, and quality validation of AI-generated outputs. Adapted to the ai-engineering context where prompts drive governance, code generation, and workflow execution.

## Trigger

- Command: agent invokes prompt-engineer skill or user requests prompt optimization.
- Context: crafting instructions for AI agents, writing skill documents, optimizing copilot-instructions, designing agent personas, improving AI-assisted code quality.

## Procedure

### Phase 1: Intent Analysis

1. **Classify the task type** — determine what the prompt needs to achieve.
   - **Generative**: create new content (code, docs, configs).
   - **Analytical**: review, audit, assess existing content.
   - **Transformative**: refactor, migrate, restructure.
   - **Diagnostic**: debug, troubleshoot, identify root cause.
   - **Instructional**: teach, guide, document procedures.

2. **Identify constraints** — what boundaries apply.
   - Token/context limits.
   - Output format requirements (code, markdown, JSON).
   - Governance compliance (standards, quality gates).
   - Domain specificity (Python, security, testing).

3. **Define success criteria** — what does a good response look like.
   - Completeness: all requested elements present.
   - Correctness: factually accurate, syntactically valid.
   - Actionability: output can be used directly without rework.
   - Compliance: follows referenced standards and patterns.

### Phase 2: Framework Selection

Choose the appropriate prompting framework based on task type:

#### RTF (Role-Task-Format)
- **Best for**: simple, well-defined tasks.
- **Structure**: define role, specify task, describe output format.
- **Example**: "As a Python security reviewer, analyze this module for injection vulnerabilities. Output a severity-tagged findings list."

#### Chain of Thought (CoT)
- **Best for**: complex reasoning, multi-step analysis, debugging.
- **Structure**: instruct step-by-step reasoning before conclusion.
- **Example**: "First, identify the bug. Then, explain why it occurs. Then, propose a fix. Finally, write a test that validates the fix."

#### RISEN (Role-Instructions-Steps-End goal-Narrowing)
- **Best for**: complex procedural tasks with specific outcomes.
- **Structure**: define persona, give instructions, list steps, state end goal, add constraints.

#### RODES (Role-Objective-Details-Examples-Sense check)
- **Best for**: tasks requiring examples and self-validation.
- **Structure**: set role, state objective, provide details, give examples, ask for self-check.

#### RACE (Role-Action-Context-Expectation)
- **Best for**: reviewer and auditor agents.
- **Structure**: define reviewer role, specify review action, provide context, state expectations.

#### RISE (Role-Input-Steps-Expectation)
- **Best for**: data transformation and processing tasks.
- **Structure**: define role, describe input, list processing steps, state expected output.

#### STAR (Situation-Task-Action-Result)
- **Best for**: incident response, debugging narratives, case studies.
- **Structure**: describe situation, define task, specify actions, state expected result.

#### SOAP (Situation-Objective-Action-Plan)
- **Best for**: architectural planning and design decisions.
- **Structure**: assess situation, state objective, define actions, create plan.

#### CLEAR (Context-Limitation-Expectation-Action-Result)
- **Best for**: constrained optimization problems.
- **Structure**: provide context, state limitations, define expectations, specify actions, describe result.

#### GROW (Goal-Reality-Options-Way forward)
- **Best for**: strategic decision-making, tech debt prioritization.
- **Structure**: state goal, assess reality, evaluate options, choose way forward.

#### Chain of Density (CoD)
- **Best for**: content compression, summary generation, documentation.
- **Structure**: iterative summarization — each pass denser than the last while retaining key information.

### Phase 3: Blending Strategy

For complex, multi-type tasks, blend frameworks:

1. **Analyze task components** — decompose into sub-tasks.
2. **Map each sub-task to optimal framework** — one framework per component.
3. **Sequence the blend** — order frameworks for coherent flow.
4. **Insert transitions** — connect frameworks with bridging instructions.

**Common blends for ai-engineering**:
- **Code generation**: RTF (role setup) + CoT (reasoning) + RISEN (procedure).
- **Code review**: RACE (reviewer setup) + CoT (analysis) + Chain of Density (summary).
- **Architecture analysis**: SOAP (planning) + GROW (decisions) + RODES (validation).
- **Debugging**: STAR (situation) + CoT (diagnosis) + RISEN (fix procedure).
- **Security review**: RACE (reviewer) + CoT (analysis) + CLEAR (constraints).

### Phase 4: Quality Checks

1. **Completeness check** — does the prompt cover all required elements?
   - Role/persona defined.
   - Task clearly stated.
   - Output format specified.
   - Constraints and governance rules referenced.

2. **Ambiguity check** — is there exactly one valid interpretation?
   - Remove vague terms ("good", "better", "appropriate").
   - Replace with measurable criteria ("coverage ≥80%", "cyclomatic complexity ≤10").

3. **Token efficiency** — is the prompt concise?
   - Remove redundant instructions.
   - Reference standards by path instead of embedding full content.
   - Use structured formats (lists, tables) over prose.

4. **Governance compliance** — does the prompt enforce framework rules?
   - References to `standards/framework/core.md` non-negotiables where applicable.
   - No bypass or skip guidance.
   - Security and quality gates embedded in expected outputs.

5. **Testability** — can the output be validated?
   - Define acceptance criteria for the output.
   - Include examples of good vs. bad output where helpful.

## Output Contract

- Optimized prompt following selected framework(s).
- Framework selection rationale.
- Blending strategy (if multi-framework).
- Quality check results (completeness, ambiguity, token efficiency, compliance).

## Governance Notes

- Prompts must never include bypass or skip guidance for governance gates.
- Security-sensitive prompts must reference the security review skill.
- Prompts for agent personas must follow the agent template structure.
- Prompts for skills must follow the skill template structure.
- Always prefer referencing canonical documents over embedding duplicate content.

## References

- `standards/framework/core.md` — non-negotiables that prompts must enforce.
- `context/product/framework-contract.md` — product principles and context efficiency.
- `agents/principal-engineer.md` — example of a well-structured agent persona.
- All agent and skill templates defined in `context/specs/001-rewrite-v2/plan.md`.
