# Handler: Aesthetics

## Purpose

Aesthetic direction and design thinking framework. Absorbed COMPLETE from Anthropic's frontend-design skill. Every rule, guideline, and anti-pattern is preserved.

## Design Thinking Framework

**Purpose:** Understand what problem the interface solves and who uses it

**Tone:** Choose an extreme direction with clear character:
- Minimalist, maximalist, organic, luxury, playful, editorial, brutalist, art deco, soft, industrial
- More options: retro-futuristic, neo-brutalist, glassmorphism, neumorphism, swiss, japanese, bauhaus, memphis, cyberpunk, vaporwave

**Constraints:** Technical requirements (framework, performance, accessibility)

**Differentiation:** "What makes this UNFORGETTABLE? What's the one thing someone will remember?"

**Critical Principle:** "Choose a clear conceptual direction and execute it with precision. Bold maximalism and refined minimalism both work - the key is intentionality, not intensity."

## Frontend Aesthetics Guidelines

### Typography

Use beautiful, unique, interesting fonts. Avoid Arial, Inter, Roboto. Pair distinctive display fonts with refined body fonts. Typography is the single most impactful design decision -- it sets tone before color or layout.

### Color & Theme

Commit to cohesive aesthetics using CSS variables. "Dominant colors with sharp accents outperform timid, evenly-distributed palettes." Build a complete color system: primary, secondary, accent, surface, background, text hierarchy, state colors (success, warning, error, info).

### Motion

Use CSS-only animations for HTML, Motion library for React. Focus on orchestrated page loads with staggered reveals and scroll-triggered effects. Motion should serve purpose -- spatial consistency, state indication, feedback, preventing jarring changes.

### Spatial Composition

Implement unexpected layouts:
- Asymmetry: break the grid intentionally
- Overlap: layer elements for depth
- Diagonal flow: guide the eye with angles
- Grid-breaking elements: hero sections that defy the grid
- Generous negative space OR controlled density -- both work if intentional

### Backgrounds & Visual Details

Create atmosphere with:
- Gradient meshes and multi-stop gradients
- Noise textures and grain overlays
- Geometric patterns and SVG backgrounds
- Layered transparencies and glassmorphism
- Dramatic shadows (both hard-edge and soft)
- Decorative borders and custom dividers
- Custom cursors for interactive elements

## Anti-Patterns (NEVER Use)

- Generic AI-generated aesthetics (the "ChatGPT look")
- Overused fonts: Inter, Roboto, Arial, system fonts as primary
- Cliched color schemes: purple-to-blue gradients, generic SaaS blue
- Predictable layouts: centered hero, 3-column features, testimonials, CTA
- Cookie-cutter component styling -- every project should feel different
- Converging on common choices -- if every AI generates the same thing, it's wrong

## Implementation Guidance

"Match implementation complexity to the aesthetic vision. Maximalist designs need elaborate code with extensive animations and effects. Minimalist or refined designs need restraint, precision, and careful attention to spacing, typography, and subtle details."

Final directive: "Don't hold back, show what can truly be created when thinking outside the box and committing fully to a distinctive vision."
