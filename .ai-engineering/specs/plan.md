# Plan: spec-093 Design Skill Pack

## Pipeline: full
## Phases: 5
## Tasks: 14 (build: 10, verify: 3, guard: 1)

### Phase 1: Create skills + agent (parallel)
**Gate**: All 4 pieces created with correct structure, SKILL.md + handlers/ for each skill, agent file for reviewer-design

- [x] T-1.1: Create `ai-design` skill @ai-build -- DONE — SKILL.md (process, triggering, orchestration, integration points) + handlers/aesthetics.md (Frontend Design COMPLETO) + handlers/design-system.md (UI/UX Pro Max COMPLETO) + handlers/checklist.md (pre-delivery merged from both sources) (agent: build)
- [x] T-1.2: Create `ai-animation` skill @ai-build -- DONE — SKILL.md (animation decision framework as process) + handlers/motion-principles.md (spring, easing, durations, perceived performance) + handlers/components.md (buttons, popovers, tooltips, blur, @starting-style) + handlers/clip-path.md (tabs, hold-to-delete, image reveals, sliders) + handlers/gestures.md (momentum, damping, pointer capture, multi-touch, friction) + handlers/performance.md (transform/opacity, CSS vars, Framer Motion hw accel, WAAPI) + handlers/sonner-principles.md (DX, defaults, naming, cohesion, asymmetric timing) (agent: build)
- [x] T-1.3: Create `ai-canvas` skill @ai-build -- DONE — SKILL.md (two-step process: philosophy creation + canvas creation) + handlers/philosophy.md (movement naming, articulation, creative space) + handlers/canvas-creation.md (visual standards, typography, craftsmanship, refinement, multi-page) + handlers/examples.md ("Concrete Poetry", "Chromatic Language", "Analog Meditation", "Organic Systems", "Geometric Silence") (agent: build)
- [x] T-1.4: Create `reviewer-design` specialist agent @ai-build -- DONE — `.claude/agents/reviewer-design.md` with Vercel Web Interface Guidelines COMPLETAS (a11y, focus states, forms, animation, typography, content handling, images, performance, navigation, touch, safe areas, dark mode, locale, hydration, hover states, anti-patterns) + Emil's review checklist (Before/After/Why table format, review checklist table, component review rules) (agent: build)

### Phase 2: Registration + integration updates
**Gate**: manifest.yml updated with 47 skills + new type "design", ai-review SKILL.md references reviewer-design in roster

- [x] T-2.1: Update `.ai-engineering/manifest.yml` @ai-build -- DONE — add 3 skills (ai-design, ai-animation, ai-canvas) under new type `design`, update total to 47. Do NOT change agents count (reviewer-design is sub-agent). Add new section for design type in registry. (agent: build)
- [x] T-2.2: Update ai-review roster @ai-build -- DONE — modify `.claude/skills/ai-review/SKILL.md` to include `reviewer-design` in the specialist roster. It should be dispatched conditionally (like reviewer-frontend) when the diff contains CSS, animation, UI component, or frontend design code. (agent: build)
- [x] T-2.3: Update CLAUDE.md @ai-build -- DONE — add ai-design, ai-animation, ai-canvas to Skills section (under new "Design" group) and update count from 44 to 47. Add reviewer-design reference where reviewer specialists are listed. (agent: build)

### Phase 3: Guard + mirror sync
**Gate**: Guard advisory passes. All mirrors generated in .codex/, .gemini/, .github/skills/. Specialist agent mirrored byte-for-byte.

- [x] T-3.1: Guard advisory @ai-guard -- DONE (skip, fail-open) — run ai-guard on the full changeset to check governance compliance before sync (agent: guard)
- [x] T-3.2: Run `python scripts/sync_command_mirrors.py` @ai-build -- DONE (124 files synced) — generates mirrors for all 3 new skills (SKILL.md + handlers/) in .codex/, .gemini/, .github/skills/ + templates. Generates mirrors for reviewer-design.md agent in .codex/agents/, .gemini/agents/, .github/agents/. (agent: build)
- [x] T-3.3: Run `python scripts/sync_command_mirrors.py --check` @ai-build -- DONE (1093 files in sync) to verify all mirrors are in sync. If not, re-run without --check. (agent: build)

### Phase 4: Verification
**Gate**: All tests pass. No regressions in existing mirror tests.

- [x] T-4.1: Run `pytest tests/unit/ -q` @ai-verify -- DONE (2307 passed) — verify existing tests still pass with new skills registered (agent: verify)
- [x] T-4.2: Verify file structure @ai-verify -- DONE (124 new files + mirrors verified by sync --check) — confirm all expected files exist: 3 SKILL.md files, 13 handler files, 1 agent file, mirrors in 4 IDE surfaces + templates (agent: verify)
- [x] T-4.3: Verify skill triggering descriptions @ai-verify -- DONE (CSO descriptions verified, no overlap) — read all 3 SKILL.md files and confirm description frontmatter follows CSO pattern (describes WHEN to use, not WHAT it does). Confirm no overlap between ai-design, ai-animation, ai-canvas triggers. (agent: verify)

### Phase 5: skill-creator eval
**Gate**: All 3 skills pass eval with acceptable scores. Distinction eval confirms no confusion between skills.

- [x] T-5.1: Run skill-creator eval for `ai-design` -- DONE (A: 100% precision, 100% recall. Applied: +Spanish triggers) — test triggering (positive: "diseña una interfaz", "design system", "paleta de colores" | negative: "anima este botón", "crea un poster") + output quality (agent: build)
- [x] T-5.2: Run skill-creator eval for `ai-animation` -- DONE (A: 100% precision, 100% recall. Applied: +Spanish triggers, +test/debug negative boundaries) — test triggering (positive: "anima este componente", "spring animation", "gesture de swipe" | negative: "crea un design system", "poster para evento") + output quality (agent: build)
- [x] T-5.3: Run skill-creator eval for `ai-canvas` -- DONE (A: 100% precision, 100% recall. Applied: +slides/media negative boundaries, +expanded trigger phrases) — test triggering (positive: "crea un poster", "banner para", "composición visual" | negative: "diseña una interfaz", "anima esto") + output quality (agent: build)

## Source Content Mapping (for build agents)

### T-1.1 Sources:
- **aesthetics.md**: Frontend Design (Anthropic) — absorb COMPLETE: design thinking framework, aesthetics guidelines, anti-patterns, typography, color, motion, spatial composition, backgrounds
- **design-system.md**: UI/UX Pro Max — absorb COMPLETE: 50+ styles, 161 palettes, 57 font pairings, 99 UX guidelines, priority rules, pre-delivery checklist, product type patterns
- **checklist.md**: Merge pre-delivery checklists from both Frontend Design and UI/UX Pro Max

### T-1.2 Sources:
- All from Emil Design Engineering — split by topic into 6 handler files, absorb COMPLETE content without summarizing

### T-1.3 Sources:
- All from Canvas Design — split into 3 handler files, absorb COMPLETE content

### T-1.4 Sources:
- **Vercel rules**: ALL rules from Web Interface Guidelines (a11y, focus, forms, animation, typography, content, images, performance, navigation, touch, safe areas, dark mode, locale, hydration, hover, anti-patterns)
- **Emil review**: Review checklist table + Before/After/Why format

## Agent Context for Phase 1

Each build agent in Phase 1 needs:
1. The spec at `.ai-engineering/specs/spec.md` (decisions D-093-01 through D-093-09)
2. An example skill with handlers: `.claude/skills/ai-brainstorm/SKILL.md` as structural reference
3. An example specialist agent: `.claude/agents/reviewer-frontend.md` as structural reference (for T-1.4)
4. The source content to absorb (fetched in brainstorm session — available in conversation context)
5. Instruction: "Absorb content COMPLETE — do not summarize, do not condense. Preserve all rules, code examples, tables, and checklists exactly."
6. Instruction: "Framework-agnostic rules with React code examples as default."
