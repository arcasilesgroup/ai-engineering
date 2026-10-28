# Style Directions

Fifteen named aesthetic directions with real lineage, concrete values, and honest tradeoffs. Use these to convert "modern and clean" into a choice the user can actually make.

**How to use this file:** pick 3–4 directions that genuinely suit the product and present them with their tradeoffs. Don't present a random sample — a payments product and a music app should get different shortlists. Hex values here are **starting anchors**, not final tokens: derive your ramps from them using `color-craft.md` rather than pasting them in.

Blending two directions is usually stronger than a pure pick. Blending three cancels out the distinctions and lands you back in the middle.

**Index**
1. [Swiss Editorial](#1-swiss-editorial) · 2. [Editorial Print](#2-editorial-print) · 3. [Structural Brutalist](#3-structural-brutalist) · 4. [Neo-Brutalist Playful](#4-neo-brutalist-playful) · 5. [Terminal Precision](#5-terminal-precision) · 6. [Warm Analog](#6-warm-analog) · 7. [Archival Institutional](#7-archival-institutional) · 8. [Utility Dense](#8-utility-dense) · 9. [Luxury Minimal](#9-luxury-minimal) · 10. [Nordic Calm](#10-nordic-calm) · 11. [Clinical Precision](#11-clinical-precision) · 12. [Retro-Futurist HUD](#12-retro-futurist-hud) · 13. [Naturalist Field Guide](#13-naturalist-field-guide) · 14. [Bauhaus Constructivist](#14-bauhaus-constructivist) · 15. [Soft Technical](#15-soft-technical)

---

## 1. Swiss Editorial

**Thesis.** The grid is the design. Nothing decorative survives; hierarchy comes from position, scale, and a single accent used sparingly.

**Lineage.** Josef Müller-Brockmann, Emil Ruder, Karl Gerstner, Massimo Vignelli's NYC subway system and *Unigrid* for the National Park Service, Wim Crouwel. Contemporary: Pentagram's identity work, Bureau Borsche.

**Color.** Near-black ink on warm paper white, plus exactly one signal color — historically red. Anchors: ink `#16181A`, paper `#FAF8F4`, signal `#D6301F`. Neutrals warm-tinted. Zero gradients.

**Type.** A grotesque with real character. Söhne, Neue Haas Grotesk, Untitled Sans, Basis Grotesque (commercial); Archivo, Public Sans, Space Grotesk (open). Flush-left, ragged-right, always. Tight tracking on display (−0.03em). Two weights only.

**Shape & depth.** Radius `0`. No shadows at all — depth is conveyed by 1px rules and whitespace.

**Layout.** A visible, strict column grid (12-col, or 6-col for denser work). Content aligns to it without exception. Baseline grid if you can manage it. Asymmetric placement within a symmetric grid is the signature move.

**Motion.** Minimal. Instant state changes; nothing enters with animation.

**Good for.** Publishing, portfolios, documentation, institutional sites, anything where credibility beats warmth.

**Fails when.** Executed loosely — a Swiss layout with sloppy alignment is worse than no system. Also reads cold for consumer products that need warmth.

**Gives up.** Warmth, playfulness, decoration, and any tolerance for misalignment.

---

## 2. Editorial Print

**Thesis.** Import magazine craft to the screen: large serif display, tight leading, hairline rules, asymmetric columns, and real typographic contrast.

**Lineage.** *Bloomberg Businessweek* under Richard Turley, *The Gentlewoman*, *Apartamento*, *Wallpaper*, Pentagram editorial, *The New York Times* feature layouts.

**Color.** Paper base with one or two ink colors and a restrained accent. Anchors: paper `#F5F2EC`, ink `#1C1917`, accent `#8B3A2F` or a deep ultramarine `#1F3A6E`. Color used in *fields* — a full-bleed colored section — rather than as small highlights.

**Type.** The heart of it. A high-contrast display serif paired with a workmanlike sans for apparatus. Canela, GT Sectra, Ogg, Tiempos Headline (commercial); Fraunces (variable, with real optical axes), Newsreader, Instrument Serif, EB Garamond (open). Display sizes very large (64–120px) with tight leading (1.0–1.1) and negative tracking. Small caps labels tracked +0.1em.

**Shape & depth.** Radius `0` or `2px`. Hairline rules (0.5–1px) as the primary structural device. No shadows.

**Layout.** Asymmetric multi-column. Pull quotes, drop caps, marginalia, images that break the column. Wide outer margins.

**Motion.** Restrained; if anything, slow reveals on scroll for imagery only.

**Good for.** Content-heavy products, media, long-form, brand sites, anything with an editorial voice.

**Fails when.** Applied to dense UI — this is a reading aesthetic, not a working one. Also fails if the display serif is Playfair.

**Gives up.** Density, and a certain amount of interface efficiency.

---

## 3. Structural Brutalist

**Thesis.** Show the structure. Raw borders, exposed grid, system fonts, no ornament, high contrast. Honesty over comfort.

**Lineage.** Experimental Jetset, Dutch design tradition, early web made visible again, Bloomberg's terminal aesthetic, `bloomberg.com`'s more aggressive moments, Balenciaga's web presence.

**Color.** Black, white, and one aggressive color. Anchors: `#000000`, `#FFFFFF`, plus something loud — `#FF3B00`, `#0000EE` (the actual default link blue, used deliberately), or `#00FF41`. This is one of the few directions where pure black and white are correct, because rawness is the point.

**Type.** System font stacks used honestly, or a stark grotesque. Helvetica, Arial, or `-apple-system`. Monospace for anything structural. Big size jumps, no intermediate steps.

**Shape & depth.** Radius `0`. Borders `1–3px` solid, everywhere. No shadows, no gradients.

**Layout.** Visible grid lines. Content in bordered boxes that share edges. Dense, edge-to-edge, minimal outer margin.

**Motion.** None, or deliberately abrupt.

**Good for.** Developer tools, creative studios, art institutions, products with an oppositional stance.

**Fails when.** The audience needs reassurance. Also — brutalism is now itself a trend with its own clichés; commit to the structural logic, not just the borders.

**Gives up.** Approachability, softness, and broad consumer appeal.

---

## 4. Neo-Brutalist Playful

**Thesis.** Brutalist structure with saturated flats and hard offset shadows. Loud, friendly, and unmistakably designed.

**Lineage.** Gumroad's 2022 redesign, Figma's brand work, Memphis Group's color logic, Braun-era toy design.

**Color.** Saturated flat fields with black outlines. Anchors: `#FFDE00` yellow, `#FF6B4A` coral, `#4ADE9B` mint, `#3B5BFF` blue — but derive your own; these specific values are becoming a cliché in their own right. Black `#000` outlines and text.

**Type.** Heavy geometric or grotesque display, high weight contrast. Archivo Black, Anton, Space Grotesk Bold (open); Founders Grotesk, Aeonik (commercial).

**Shape & depth.** Radius `0` to `8px`, consistently. **Hard offset shadows** — `4px 4px 0 #000`, no blur. This is the signature.

**Layout.** Chunky blocks, obvious grid, generous padding inside heavy borders. Slight rotations on elements are on-style.

**Motion.** Snappy, physical — elements translate on hover into their own shadow.

**Good for.** Consumer products, creator tools, education, anything that wants to feel approachable and confident.

**Fails when.** Overused — this style saturated hard in 2022–2024. Needs an unusual palette to stay fresh. Also poor for dense or serious data.

**Gives up.** Subtlety, density, and any claim to institutional gravity.

---

## 5. Terminal Precision

**Thesis.** Built for people who use it all day. Density is a feature, monospace carries the data, borders replace shadows, and nothing is bigger than it needs to be.

**Lineage.** Linear, the Bloomberg Terminal, Retool, early Stripe dashboards, `htop`, Berkeley Systems-era Unix tooling.

**Color.** Dark, but **warm charcoal or true neutral — not navy**. Anchors: bg `#131313` or `#1A1917`, surface `#1E1E1E`, border `#2E2E2E`, text `#E8E6E3`, muted `#8A8580`. One accent, often a cool cyan or a sodium amber: `#4EC9B0` or `#E8A33D`. Semantic colors muted, not saturated.

**Type.** A neutral grotesque for prose, a real mono for anything numeric, tabular, or identifier-like. Berkeley Mono, Commit Mono, JetBrains Mono, IBM Plex Mono, Geist Mono. Small sizes — 13–14px body is correct here. Tabular figures mandatory.

**Shape & depth.** Radius `2–6px`, small and consistent. Depth via 1px borders and subtle surface lightening, never shadows.

**Layout.** Dense rows, tight vertical rhythm (4px base), aligned columns, keyboard-first affordances visible. Sidebar + content.

**Motion.** Fast (100–150ms) or none. Speed is the aesthetic.

**Good for.** Developer tools, dashboards, admin panels, trading and analytics, internal tooling.

**Fails when.** The audience is casual or first-time — density reads as intimidating. Also fails if the dark background drifts blue.

**Gives up.** Warmth, generosity of space, and first-time approachability.

---

## 6. Warm Analog

**Thesis.** Materials, not pixels. Off-white paper stock, muted earth tones, generous margins, nothing pure and nothing harsh.

**Lineage.** Aesop, Kinfolk, Muji, Cereal magazine, Le Labo, Japanese stationery design.

**Color.** No pure white, no pure black, low chroma throughout. Anchors: paper `#F4F1EA` or `#EDE8DE`, ink `#2A2724`, clay `#A8624A`, sage `#7C8471`, ochre `#C4954A`. Neutrals distinctly warm (OKLCH hue near 60–80).

**Type.** Humanist or transitional, never geometric. A serif for body is on-style. Freight Text, Lyon, Ideal Sans (commercial); Source Serif 4, Literata, IBM Plex Serif, Public Sans (open). Generous line-height (1.6–1.75).

**Shape & depth.** Radius `0–4px`, subtle. Depth via tonal layering — a slightly lighter surface on a slightly darker ground. Shadows, if any, are warm-tinted and very soft.

**Layout.** Wide margins, single column, unhurried vertical rhythm. Images given room.

**Motion.** Slow and soft — 400ms+, gentle easing.

**Good for.** Wellness, food, retail, hospitality, editorial, craft goods, anything premium-but-not-loud.

**Fails when.** Applied to data-dense interfaces; the generosity that makes it work wastes space users need.

**Gives up.** Density, urgency, and technical credibility.

---

## 7. Archival Institutional

**Thesis.** The register of a museum wall label or a well-made library catalog. Restrained, permanent, and respectful of dense text.

**Lineage.** MoMA and Tate identity systems, GOV.UK, the *Unigrid* NPS brochures, university presses, Yale and Princeton press book design.

**Color.** Restrained, near-monochrome with one earned accent. Anchors: paper `#F7F5F0`, ink `#1B1B19`, rule `#C9C4B8`, accent a deep ochre `#9A6B24` or oxblood `#6E2A28`.

**Type.** A transitional or old-style serif for display and body, a neutral sans for apparatus and wayfinding. Tiempos, Lyon (commercial); EB Garamond, Source Serif 4, Newsreader (open). Sans: Public Sans, Archivo.

**Shape & depth.** Radius `0`. Hairline rules to separate. No shadows.

**Layout.** Clear hierarchy, generous but not luxurious margins, dense text blocks treated as content rather than as a problem. Tables and lists are first-class.

**Motion.** Essentially none.

**Good for.** Government, education, research, archives, nonprofits, documentation, anything that must feel durable and trustworthy.

**Fails when.** The product needs energy or novelty — this style reads as deliberately unexciting, which is a feature or a bug depending on the brief.

**Gives up.** Speed, novelty, and emotional warmth.

---

## 8. Utility Dense

**Thesis.** Maximum information per screen without becoming unreadable. Every pixel of chrome is questioned.

**Lineage.** Bloomberg Terminal, airline and logistics operations software, Excel done well, Linear's list views, Superhuman.

**Color.** Light-mode-first, low-chroma, with color reserved almost entirely for state. Anchors: bg `#FCFCFB`, surface `#F4F4F2`, border `#DEDEDA`, text `#1F1F1D`, muted `#71716C`. Semantic states muted: `#2F6B4F` positive, `#9B3A2E` negative, `#8A6A1F` caution.

**Type.** A compact grotesque at small sizes with tabular numerics. 13–14px body, 11–12px labels. IBM Plex Sans, Archivo, Public Sans. Mono for IDs and numbers.

**Shape & depth.** Radius `2–4px`. Borders only. Zero shadows except for genuinely floating layers.

**Layout.** Tight 4px base grid. Table-forward. Persistent chrome (sidebar, toolbar, status bar). Minimal padding — 8–12px inside cells.

**Motion.** 100ms or nothing.

**Good for.** Operations tooling, CRMs, analytics, admin, anything used professionally for hours.

**Fails when.** Marketing surfaces need to breathe — pair it with a different register for the public-facing pages.

**Gives up.** Elegance, whitespace, and first-impression appeal.

---

## 9. Luxury Minimal

**Thesis.** Almost nothing on the screen, and what remains is perfect. Whitespace as the primary material.

**Lineage.** The Row, Celine under Phoebe Philo, Jil Sander, Rimowa, Loro Piana, high-end gallery sites.

**Color.** Near-monochrome. Anchors: `#FFFFFF` or a barely-warm `#FDFCFA`, text `#0D0D0D`, one muted neutral `#8C8880`. Accent color often entirely absent — the product imagery is the color.

**Type.** One refined face, sometimes two. Tiny tracked-out uppercase labels (10–11px, +0.15em) against very large display. Weight contrast is minimal — this style often uses a single light or regular weight throughout.

**Shape & depth.** Radius `0`. No borders, no shadows, no fills. Separation entirely through space.

**Layout.** Enormous margins. Very few elements per viewport. Full-bleed imagery alternating with near-empty text screens. Asymmetric, off-center placement.

**Motion.** Slow fades (500–800ms), nothing springy.

**Good for.** Fashion, jewelry, architecture, high-end hospitality, portfolios, premium hardware.

**Fails when.** There's a lot to communicate, or conversion matters more than mood. Requires excellent photography — without it, this is just an empty page.

**Gives up.** Information density, discoverability, and almost all affordance clarity.

---

## 10. Nordic Calm

**Thesis.** Quiet, humane, low-contrast. Muted color, soft neutrals, generous space, nothing shouting.

**Lineage.** Scandinavian interior and product design, Norm Architects, Danish public design, Spotify's early brand work, Arket.

**Color.** Desaturated and cool-to-neutral. Anchors: bg `#F2F1EE`, surface `#FFFFFF` used sparingly, text `#33342F`, muted sage `#8E9A8B`, dusty blue `#7C90A6`, soft terracotta `#B58474`. Everything low chroma.

**Type.** A humanist sans with warmth. Söhne Buch, Ideal Sans, Untitled Sans (commercial); Source Sans 3, IBM Plex Sans, Public Sans (open). Comfortable line-height (1.6), moderate sizes.

**Shape & depth.** Radius `4–12px`, soft but not bubbly. Depth via tonal layering, occasionally a very soft warm-tinted shadow.

**Layout.** Generous, calm rhythm. Single or two-column. Nothing crowded, nothing dramatic.

**Motion.** Gentle, 250–350ms, ease-out.

**Good for.** Wellness, finance-for-humans, productivity, healthcare, education, family products.

**Fails when.** It drifts into blandness — the low contrast that makes it calm can make it forgettable. Needs one memorable element (an unusual accent, a distinctive face) to have an identity.

**Gives up.** Drama, urgency, and strong brand recall.

---

## 11. Clinical Precision

**Thesis.** Sterile, legible, exact. Built for high-stakes accuracy where ambiguity is dangerous.

**Lineage.** Medical device interfaces, laboratory equipment, Braun under Dieter Rams, Swiss pharmaceutical packaging, aviation instrumentation.

**Color.** Cool, restrained, high legibility. Anchors: bg `#FBFCFC`, surface `#FFFFFF`, border `#D5DBDD`, text `#15201F`, primary a clinical teal-blue `#0F6B7A` or `#1B5E7E` (deliberately *not* Tailwind blue). Semantic colors unambiguous and tested for color-vision deficiency.

**Type.** Maximum legibility, no personality games. IBM Plex Sans (designed for this register), Public Sans, Source Sans 3. Larger-than-usual body (16–17px), tabular figures, generous label sizing.

**Shape & depth.** Radius `2–4px`. Borders for structure. No decorative depth.

**Layout.** Highly organized, labeled, grouped. Generous touch targets. Clear zones. Redundant encoding — never color alone to convey state.

**Motion.** Minimal and instant; motion can obscure state changes that matter.

**Good for.** Healthcare, lab software, safety-critical systems, compliance, insurance, scientific instruments.

**Fails when.** Warmth or brand personality is a requirement.

**Gives up.** Personality, warmth, and visual interest — deliberately.

---

## 12. Retro-Futurist HUD

**Thesis.** The imagined computer interfaces of 1975–1985. Phosphor glow, monospace, thin rules, tracked-out labels.

**Lineage.** *2001: A Space Odyssey* (Vignelli-adjacent), the Nostromo displays in *Alien*, *Blade Runner*, early Braun and Sony industrial design, oscilloscope and radar UIs.

**Color.** Dark ground with a single phosphor color. Anchors: bg `#0A0B0A` or `#101410`, phosphor amber `#FFB000`, phosphor green `#33FF66`, or CRT white `#E8F0E8`. Sometimes a single alarm red `#FF3B30`. Strictly two or three colors total.

**Type.** Monospace dominant, or a condensed technical sans for display. Departure Mono, JetBrains Mono, IBM Plex Mono (open); Berkeley Mono (commercial). Uppercase labels with heavy tracking (+0.15em). Small sizes.

**Shape & depth.** Radius `0` or `2px`. Thin rules and brackets. Scanline or subtle grain texture is on-style — the one place a background texture is defensible.

**Layout.** Bracketed panels, corner markers, aligned readouts, visible coordinates and status lines. Dense and instrument-like.

**Motion.** Terse — typewriter reveals, instant state flips, blinking cursors.

**Good for.** Developer tools with attitude, games, crypto/infra, security products, music software.

**Fails when.** Taken too far it becomes costume rather than interface. Keep the readability discipline; the aesthetic must not cost legibility.

**Gives up.** Warmth, broad accessibility, and any claim to being unassuming.

---

## 13. Naturalist Field Guide

**Thesis.** The visual language of scientific illustration and cartography: muted botanical color, precise labeling, illustration-forward.

**Lineage.** Audubon plates, Peterson field guides, USGS topographic maps, National Park Service signage, botanical illustration, Ordnance Survey.

**Color.** Muted, earthy, drawn from pigment rather than light. Anchors: paper `#F3EFE4`, ink `#22261F`, forest `#3E5641`, ochre `#B98A3C`, clay `#9C5B3F`, slate-blue `#5A7184`. Low chroma, high harmony.

**Type.** A serif for content with a condensed sans for labels — mirroring map typography. Source Serif 4, Literata (open serif); Archivo Narrow, Roboto Condensed (open condensed sans). Italic used meaningfully, as in taxonomy.

**Shape & depth.** Radius `0–2px`. Hairline rules, keys, legends. No shadows.

**Layout.** Content with margin annotations. Legends and keys as real interface elements. Layered information density like a map.

**Motion.** Minimal, considered.

**Good for.** Outdoor, environmental, agriculture, science communication, travel, education, data with a geographic dimension.

**Fails when.** Applied to fast transactional flows — the annotative density slows things down.

**Gives up.** Speed and modern-tech credibility.

---

## 14. Bauhaus Constructivist

**Thesis.** Geometry as content. Primary color fields, hard diagonals, circles and squares as structural elements rather than decoration.

**Lineage.** Herbert Bayer, László Moholy-Nagy, El Lissitzky, Alexander Rodchenko, Jan Tschichold's *Die neue Typographie*, Paul Rand's corporate work.

**Color.** A specific primary triad — but pick *your* primaries, not the RGB defaults. Anchors: a slightly orange red `#D62B1F`, an ultramarine `#1B4EA8`, a warm yellow `#F2B705`, against `#F2EFE9` and `#161616`. Flat fields, no gradients, large areas of color.

**Type.** Geometric sans, or a grotesque with geometric bones. Futura, Neue Haas Unica (commercial); Poppins is the wrong answer here despite being geometric — try Archivo, Space Grotesk, or Jost (open). Big size contrast, occasional vertical or rotated type.

**Shape & depth.** Radius `0` and `full` — squares and circles, nothing in between. Flat, no shadows.

**Layout.** Diagonal energy, asymmetric balance, large color blocks defining regions, elements overlapping deliberately.

**Motion.** Geometric — elements slide along axes, rotate, scale from a corner.

**Good for.** Culture, events, education, agencies, publishing, anything wanting graphic confidence.

**Fails when.** The content is dense or utilitarian — this is a poster aesthetic and it fights complex interfaces.

**Gives up.** Density, subtlety, and neutrality.

---

## 15. Soft Technical

**Thesis.** Technical credibility without coldness. The middle ground done deliberately rather than by default — precise structure, warm neutrals, restrained color.

**Lineage.** Stripe's documentation, Vercel's better moments, Notion, Things by Cultured Code, Apple's developer documentation.

**Color.** Warm-neutral base with a single confident accent that isn't indigo. Anchors: bg `#FCFBF9`, surface `#FFFFFF`, border `#E6E2DC`, text `#1C1A17`, muted `#6E6963`. Accent options: deep teal `#0E6F6B`, burnt orange `#C2571E`, forest `#2D5F3F`, or oxblood `#7A2E2E`.

**Type.** A clean grotesque with a mono companion for code and data. Geist, Public Sans, Archivo, IBM Plex Sans (open); Söhne, Untitled Sans (commercial). Body 15–16px, comfortable but not luxurious.

**Shape & depth.** Radius `6–8px`, consistent within class but differentiated across classes (inputs 4px, cards 8px). Borders primary; one very subtle shadow level reserved for floating layers.

**Layout.** Clear, organized, moderate density. Sidebar navigation, well-structured content, comfortable spacing on an 8px base.

**Motion.** 150–200ms, ease-out, applied to state changes only.

**Good for.** Developer tools, SaaS, documentation, B2B products — the broad default case, executed with intent.

**Fails when.** You stop making choices — this direction is *closest to the center of the distribution*, so it's the easiest one to let collapse into slop. If you pick it, the accent color, the typeface pairing, and the neutral tint have to carry the whole identity. Be strict about them.

**Gives up.** Strong differentiation — this trades distinctiveness for broad usability.

---

## Choosing well

A few heuristics for shortlisting:

- **Match the usage duration.** Products used for hours want Terminal Precision, Utility Dense, or Soft Technical. Products seen once want Editorial Print, Luxury Minimal, or Bauhaus.
- **Match the trust requirement.** High-stakes, low-novelty domains (health, finance, government) want Clinical, Archival, or Utility. Discretionary consumer products can take more risk.
- **Match the content.** Long-form text wants Editorial or Archival. Tables and numbers want Utility or Terminal. Imagery wants Luxury Minimal or Warm Analog.
- **Then offer one outlier.** Include one direction that's a slight stretch. Users often recognize what they want only when they see something they didn't expect, and the outlier is frequently what gets picked.
