---
name: ai-design
description: "Use when designing or building user interfaces, creating design systems, choosing aesthetic direction, defining color palettes, typography, spatial composition, or structuring text-based information architecture for web, mobile, CLI, or documentation-heavy experiences. Trigger for 'design this page', 'create a design system', 'what style should we use', 'UI for this feature', 'color palette for', 'typography for', 'diseña la interfaz', 'estilo para', or requests where hierarchy, flow, and presentation are the design problem. Not for animation-specific work (use /ai-animation) or visual art/posters/banners (use /ai-canvas)."
effort: high
argument-hint: "[UI or design task description]"
tags: [design, ui, ux, design-system, aesthetics]
---

# Design

## Purpose

Master design skill. Aesthetic direction + design systems + component design + UI/UX and information-architecture guidance. Translates user intent into specific, opinionated design decisions -- never vague suggestions. Every output has a clear conceptual direction executed with precision.

## When to Use

- Designing interfaces (web or mobile)
- Creating or extending a design system
- Choosing aesthetic direction for a project
- Structuring text-heavy or CLI-facing information architecture when hierarchy, framing, and flow are design problems
- Component design and layout decisions
- Responsive design strategy
- Typography and color palette selection
- Spatial composition and visual hierarchy

## Process

### Step 1 -- Load Design Thinking Framework

Read `handlers/aesthetics.md` for the full aesthetic direction philosophy. This establishes the design thinking framework (Purpose, Tone, Constraints, Differentiation) and all frontend aesthetics guidelines.

### Step 2 -- Load UX Rules and Design System Intelligence

Read `handlers/design-system.md` for the priority-ranked UX rule database, covering accessibility, touch targets, performance, style selection, layout, typography, animation, forms, navigation, and data visualization.

### Step 3 -- Analyze the Request

Apply the design thinking framework from `handlers/aesthetics.md` (or directly if the handler is unavailable):

1. **Purpose** -- what problem does this interface solve? Who uses it?
2. **Tone** -- choose an extreme direction with clear character (minimalist, maximalist, organic, luxury, playful, editorial, brutalist, etc.)
3. **Constraints** -- technical requirements (framework, performance budget, accessibility level)
4. **Differentiation** -- "What makes this UNFORGETTABLE? What's the one thing someone will remember?"

### Step 4 -- Apply UX Guidelines by Priority

Use the priority ranking from `handlers/design-system.md`:

| Priority | Category            | Gate                   |
| -------- | ------------------- | ---------------------- |
| 1        | Accessibility       | CRITICAL -- never skip |
| 2        | Touch & Interaction | CRITICAL -- never skip |
| 3        | Performance         | HIGH                   |
| 4        | Style Selection     | HIGH                   |
| 5        | Layout & Responsive | HIGH                   |
| 6        | Typography & Color  | MEDIUM                 |
| 7        | Animation           | MEDIUM                 |
| 8        | Forms & Feedback    | MEDIUM                 |
| 9        | Navigation Patterns | HIGH                   |
| 10       | Charts & Data       | LOW                    |

Address P1-P2 as hard gates. P3-P9 as design considerations. P10 only when data visualization is involved.

### Step 5 -- Generate Design Direction

Produce specific choices, not vague guidance:

- Name the fonts (display + body pairing)
- Define the color system (primary, secondary, accent, surface, background, text hierarchy, state colors)
- Specify spacing scale (4pt/8dp system)
- Describe spatial composition with layout strategy
- Choose motion approach (duration, easing, what animates)
- Declare the conceptual direction in one sentence

### Step 6 -- Delegate Specialized Work

- If motion/animation design is needed beyond micro-interactions, invoke `/ai-animation`
- If visual artifacts (posters, banners, illustrations) are needed, invoke `/ai-canvas`
- If presentation design, invoke `/ai-slides` (which consumes this skill's output)

### Step 7 -- Pre-Delivery Quality Check

Before delivering any design work, run `handlers/checklist.md` and verify all items pass. Do not deliver with unchecked items.

## Integration

- **Called by**: user directly, `/ai-slides`, `/ai-media`, `/ai-dispatch`
- **Calls**: `handlers/aesthetics.md`, `handlers/design-system.md`, `handlers/checklist.md`, `/ai-animation`, `/ai-canvas`
- **Consumed by**: `/ai-slides` (presentation aesthetics), `/ai-media` (visual asset direction)

## Common Mistakes

- Using generic AI aesthetics (the "ChatGPT look" -- purple gradients, Inter font, centered hero)
- Defaulting to Inter, Roboto, or Arial instead of choosing distinctive typography
- Choosing predictable layouts (centered hero, 3-column features, testimonials, CTA)
- Giving vague advice ("use a clean design") instead of specific choices ("use Space Grotesk for headings at 700 weight with 16px Instrument Serif body text")
- Skipping the differentiation question -- every design must answer what makes it unforgettable
- Ignoring accessibility as a hard gate (contrast, touch targets, keyboard nav)
- Treating dark mode as an afterthought instead of designing both themes simultaneously

$ARGUMENTS
