# The Slop Catalog

A field guide to the specific defaults that make a design read as machine-generated, why each one happens, and what to do instead.

**Contents**
- [The mechanism](#the-mechanism)
- [Color](#color)
- [Typography](#typography)
- [Shape, surface, and elevation](#shape-surface-and-elevation)
- [Layout](#layout)
- [Motion](#motion)
- [Iconography and imagery](#iconography-and-imagery)
- [Language](#language)
- [The three legitimate exceptions](#the-three-legitimate-exceptions)
- [Final checklist](#final-checklist)

---

## The mechanism

None of the items below are *bad* in isolation. Indigo is a fine color. Inter is an excellent typeface. Rounded corners are pleasant. The problem is that each one is the **highest-probability answer** to its question, and a design assembled entirely from highest-probability answers has a recognizable texture: frictionless, competent, and completely anonymous.

Two consequences worth internalizing:

**Slop is a distribution problem, not a quality problem.** You cannot fix it by trying harder at the same choices, or by adding polish. Polished slop is still slop. It's fixed only by moving *off* the center — deliberately, in a direction you can name.

**One authored decision beats ten avoided cliches.** A design that uses Inter but has a genuinely strange, defensible color story reads as authored. A design that dutifully avoids every item on this list but has no argument behind any of its choices just reads as *differently* anonymous. The lists below are diagnostic, not a recipe. The recipe is: commit to a direction, derive from a source, accept a tradeoff.

The reliable test for any token: **can you finish the sentence "this value is what it is because ___" with something other than "it looked good"?**

---

## Color

### The tells

**The indigo-violet complex.** `#6366F1` (Tailwind indigo-500), `#8B5CF6` (violet-500), `#9333EA` (purple-600), `#4F46E5` (indigo-600). These four are the single most reliable signal of unconsidered AI output. They arrived as Tailwind's demo accent, propagated through a decade of bootstrapped SaaS, and are now the default answer to "pick a brand color."

**The purple-to-cyan gradient**, and its siblings: violet→pink→orange, blue→purple, `from-purple-500 via-pink-500 to-orange-400`. Especially as a background mesh or blob behind a hero.

**Gradient text on the headline** — `bg-clip-text` with any two-stop gradient. Was novel in 2021.

**Navy-slate dark mode.** `#0F172A` (slate-900) or `#020617` (slate-950) as the page background, with one saturated accent floating on it. Note that the tell is specifically the *blue-tinted* dark; dark UI is fine, this particular dark is not.

**Untouched framework ramps.** Every color pulled straight from Tailwind's default palette with no modification — `emerald-500` for success, `red-500` for error, `amber-500` for warning, `slate-*` for every neutral. The stock semantic triad is as recognizable as the stock accent.

**Pure neutral greys.** `#808080`, `#CCCCCC`, `#F5F5F5`, or any ramp where R=G=B. Real palettes almost never contain true greys, because real light is never neutral.

**Pure `#FFFFFF` and `#000000`** used as the page background and body text. Both are physically harsh, and both signal that nobody chose them.

**Neon glow shadows** — `shadow-[0_0_40px_rgba(99,102,241,0.5)]` and relatives.

**Accent inflation.** The brand color on the heading, the button, the icon, the border, the link, the badge, and the chart. Once it's on everything it emphasizes nothing.

### What to do instead

**Anchor the hue to a real referent.** Choose a color because it's the oxide on weathered copper, the specific green of hospital corridors, the amber of a phosphor CRT, the ink density of a 1968 Braun manual, the exact orange of Dutch road signage, the paper stock of a Kinfolk issue. Then name the referent in the DESIGN.md prose. This is the single highest-leverage anti-slop move available, because a sourced color is by construction not the median color, and the sourcing is legible to the reader.

**Build ramps in OKLCH.** Perceptual lightness means a 10% step actually looks like a 10% step; HSL lies to you, and ramps built in HSL have visible dead zones and hot spots. Convert to hex for the tokens.

**Bend the ramp.** Two properties separate a hand-built ramp from a generated one:
- *Hue shift* — real pigments shift hue as they lighten or darken. A red that goes toward orange in the tints and toward maroon in the shades looks like a material. A red at a fixed hue angle across nine steps looks like a spreadsheet. Shift 5–20° across the ramp.
- *Chroma taper* — chroma should peak in the mid-lightness range and fall off toward both ends, because the gamut narrows there. Flat chroma produces muddy darks and neon lights.

**Tint every neutral.** Carry a small amount of the brand hue (or its complement, for a cooler feel) through the entire grey ramp — chroma around 0.005–0.02 in OKLCH. The effect is nearly invisible per-swatch and completely transformative in aggregate. Warm neutrals for paper/craft/editorial registers, cool for clinical/technical.

**Move off the endpoints.** Instead of `#FFFFFF`, an off-white with a trace of warmth (`#FAF9F6`, `#F7F5F2`) or coolness (`#F8FAFC` is Tailwind's — build your own). Instead of `#000000`, a near-black carrying the brand hue (`#1A1C1E`, `#141210`).

**Derive semantics from the family.** Your error color should look like it belongs to your brand — a rust, a brick, a vermilion — not like a stock alert red imported from another system.

**Enforce accent scarcity.** Pick one accent, give it exactly one job (usually: "this is the primary action" or "this is live/changed"), and hold it under ~5% of pixels. Everything else does its work through weight, size, spacing, and neutral value. Write this into Do's and Don'ts, because it's the rule most likely to erode later.

---

## Typography

### The tells

**Inter for everything.** Inter is genuinely well-made — that's why it's everywhere, and why using it reflexively signals that no typographic decision was made. Related defaults: **Poppins** (geometric, friendly, exhausted), **Montserrat**, **Roboto**, **Open Sans**, **Nunito**, **Lato**. **Playfair Display** is the same phenomenon on the serif side — it became the default "elegant" answer and now reads as a stock choice.

**One typeface doing every job**, with hierarchy carried entirely by size and weight.

**The full weight ladder** — 400/500/600/700 all in play, producing four steps that are hard to tell apart and none of which read as a decision.

**Framework-default metrics.** Tracking untouched at every size; line-height left at the framework default across the whole scale; a size ramp that's just `text-sm` through `text-6xl` with nothing considered in between.

**The hero configuration**: `text-6xl font-bold tracking-tight` centered, subhead in `text-xl text-slate-400` centered beneath, max-width around 2xl. This exact block appears in an enormous fraction of generated pages.

**Centered body copy** at any length past a sentence.

**Uppercase everything** without added tracking — uppercase needs breathing room; set solid, it looks broken rather than emphatic.

### What to do instead

**Use two typefaces that differ by classification.** A grotesque + a serif, a serif + a mono, a humanist sans + a condensed display. Two grotesques together (Inter + Helvetica) is not a pairing, it's an accident. The classic split: one face carries the *voice* (display and headings), the other carries the *apparatus* (labels, metadata, numerics).

**Pick faces with something specific about them.** A face with real optical sizes, a variable axis you actually use, unusual figures, distinctive italics, a genuine condensed cut. See `typography.md` for a library organized by register, with open-source options throughout — this does not require licensing budget.

**Build the scale with a ratio, then break it.** Generate with a modular ratio (≈1.2 for dense UI, ≈1.25–1.333 for editorial, ≈1.5 for dramatic), then hand-tune. Pure geometric scales are always too timid at the display end and too crowded at the small end. The jump from body to display should feel like a jump.

**Set tracking optically.** Large display sizes need negative tracking (−0.02 to −0.04em) because the default spacing was drawn for text sizes. Small uppercase labels need positive tracking (+0.06 to +0.12em). Body text usually needs nothing. Tracking that changes with size is one of the clearest markers of a considered system.

**Move line-height inversely to size.** Roughly 1.0–1.15 for display, 1.2–1.35 for subheads, 1.5–1.7 for body, ~1.4 for small text. A single line-height across the scale is a tell.

**Two or three weights, far apart.** 400 and 700 reads as intentional contrast. 400/500/600 reads as indecision. If you need a third, make it a genuine extreme (300 or 900), not an intermediate.

**Constrain the measure.** 60–75 characters for body. Wider is unreadable; the default full-width paragraph is a common failure.

---

## Shape, surface, and elevation

### The tells

- **`rounded-2xl` on everything.** One radius, applied uniformly to cards, buttons, inputs, images, avatars, and modals.
- **`shadow-lg` on everything**, particularly neutral black at low opacity with no light direction, applied to elements that aren't actually floating.
- **Glassmorphism** — `backdrop-blur-xl bg-white/5 border border-white/10`. Ubiquitous 2021–2023, still the default "make it look premium" move.
- **Border + shadow + radius together** on every container, so nothing has a distinct rank.
- **Decorative background gradients** — radial blobs, mesh gradients, faint dot-grids and line-grids behind the hero.
- **A visible card around every piece of content**, including content that has no reason to be a discrete object.

### What to do instead

**Make radius hierarchical.** Different element classes get different radii, chosen for a reason: inputs sharper than buttons, cards sharper than avatars. Or commit to `0` everywhere as a real structural position — sharp is a strong, legible choice when it's the whole direction rather than an accident.

**Prefer borders, tonal shifts, and space over shadows.** Most depth problems are actually grouping problems, and grouping is better solved with spacing. A 1px hairline in a tinted neutral does the work of a shadow with none of the mush.

**If you use shadows, give them physics.** A consistent light direction (usually top-down: y-offset positive, x near zero), a color sampled from the palette's dark end rather than neutral black, and at most two or three levels that mean genuinely different things. Ambient + direct layering (one tight dark shadow, one wide soft one) reads far more real than a single blur.

**Reserve elevation for things that are actually above other things.** Modals, dropdowns, drag states. A static card is not floating.

---

## Layout

### The tells

**The landing page template**, in this exact order: centered hero → three-column feature grid with icons in tinted rounded squares → "trusted by" logo strip → three-tier pricing with a ringed "Most Popular" middle → FAQ accordion → full-width CTA band → four-column footer. Any two or three of these in sequence is recognizable.

**Everything centered.** `max-w-7xl mx-auto` with symmetric padding and center-aligned text at every level.

**Uniform grids** — three equal columns, equal gutters, equal card heights, nothing spanning or breaking.

**Uniform density** across the whole page, so nothing is emphasized by contrast.

**Equal vertical rhythm** — every section separated by the same `py-24`, producing a page with no phrasing.

### What to do instead

**Commit to asymmetry, if the direction supports it.** Flush-left with a wide right margin. A 2/3–1/3 split. Content that breaks the grid deliberately. Asymmetry has to be a system-level commitment, though — sprinkled randomly it reads as a bug.

**Vary density on purpose.** A dense block next to a sparse one creates emphasis for free and costs nothing. Uniform generosity is as monotonous as uniform crowding.

**Vary section rhythm.** Sections that belong together sit closer. Spacing is the cheapest and most-ignored hierarchy tool available.

**Question the card.** Cards are for genuinely discrete, comparable objects. For a list of features, a plain list with strong typographic hierarchy is usually better and always less generic.

**Let structure follow content type.** Editorial content wants columns and rules. Data wants tables and alignment. Marketing wants a few large gestures. Copying a template designed for a different content type is how pages end up feeling arbitrary.

---

## Motion

### The tells

- **Fade-up-on-scroll on every section**, at the same distance and duration.
- **One easing curve and duration for everything** (usually 300ms `ease-in-out`).
- **Animation on elements the user is trying to read**, delaying comprehension for decoration.
- **Springy bounces** on interface elements that aren't physical.

### What to do instead

Decide what motion is *for* in this system — confirming an action, explaining a spatial relationship, drawing the eye to a change — and animate only that. Use a small set of named durations (fast ~120ms for state changes, medium ~200–250ms for transitions, slow ~400ms+ for entering surfaces) and easings that differ by purpose: something entering decelerates, something leaving accelerates. **Write down what does not animate.** That sentence is what stops universal fade-up from creeping back in.

---

## Iconography and imagery

- **A single icon set applied uniformly** (Lucide/Heroicons at default stroke on everything) reads as default. Fine to use, but set a deliberate stroke weight, size, and optical alignment relative to your type — and note it in the file.
- **Emoji as feature icons** is an immediate tell.
- **Icons in tinted rounded squares above feature headings** is the single most recognizable AI layout unit in existence.
- **Generic 3D/isometric illustration** and abstract gradient blobs signal stock content.
- Better: a set with actual character (see the direction's notes), or no icons at all — typographic hierarchy usually does the job — or a single strong image instead of many weak ones.

---

## Language

Copy is part of the design because it determines the shape of every block.

Tells: "Supercharge," "Effortlessly," "10x," "Seamlessly," "Unlock," "Take your X to the next level"; ✨🚀🎯 in headings; three-word feature titles with a one-sentence subtitle in exactly parallel structure; em-dash-heavy rhythm.

Better: say the specific thing the product does. Specific copy is shorter, which changes the layout, which changes the design. Vague copy forces the generic three-column grid because there's nothing to differentiate.

---

## The three legitimate exceptions

Do not follow this file off a cliff. There are real cases where the "slop" answer is correct:

1. **An existing brand mandates it.** If the company's color has been indigo for six years, it's indigo. Codify it and put the effort into the neutrals, type, and shape language instead.
2. **The platform convention is the accessible choice.** iOS/Android/system conventions exist so users don't have to relearn. Deviating from a platform pattern for novelty is worse than generic.
3. **Familiarity is the requirement.** Some products — payments, healthcare, government — should look like what users expect, because surprise costs trust. "Boring and credible" is a real direction; execute it deliberately rather than defaulting into it.

The distinction throughout: **choosing** a conventional answer is design; **arriving** at it is slop.

---

## Final checklist

Run this against the finished DESIGN.md before handing off. Every hit needs a fix or a stated reason.

**Color**
- [ ] No indigo/violet/purple in the `#6366F1`–`#9333EA` range as the primary, unless brand-mandated
- [ ] No multi-hue decorative gradients; no gradient text
- [ ] Not slate-900/950 navy as the dark background
- [ ] No color pulled unmodified from a framework's default palette
- [ ] No `R=G=B` neutrals — every grey is tinted
- [ ] No pure `#FFFFFF` background or `#000000` text
- [ ] Semantic colors derive from the brand family
- [ ] Exactly one accent, with one defined job
- [ ] The primary hue traces to a named real-world referent in the prose

**Typography**
- [ ] Not Inter/Poppins/Montserrat/Roboto/Playfair by default (using one deliberately, with a reason, is fine)
- [ ] Two typefaces that differ by classification
- [ ] At most three weights, spaced far apart
- [ ] Tracking varies with size (negative on display, positive on small caps)
- [ ] Line-height varies inversely with size
- [ ] Body measure constrained to 60–75ch

**Shape and surface**
- [ ] Radius is hierarchical, or deliberately zero everywhere
- [ ] Shadows have a light direction and a palette-derived color — or aren't used
- [ ] No glassmorphism unless it's the stated direction
- [ ] Elevation reserved for things actually above other things

**Layout and motion**
- [ ] Layout structure follows the content type, not a landing-page template
- [ ] Density and section rhythm vary purposefully
- [ ] Motion has a stated purpose, and the file says what doesn't animate

**Overall**
- [ ] Every token can complete "this is what it is because ___"
- [ ] The system makes at least one identifiable sacrifice
- [ ] A specific person could have made this and would defend it
