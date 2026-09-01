# Judging the output

Severity is a guess about impact, not a verdict. Every finding still has to be argued against the code, and roughly a third of a first run is usually the audit misreading a decision.

## The shapes that look like defects and are not

**A whole-pixel leading or line-height.** `line-height: 19px` on 12.5px type reports as an outlier against a rung of `1.55`. A pill with `border-radius: 999px` is clamped to half its own height, so a fractional box puts every arc-to-straight join mid-pixel and the ring renders as a cut band. Whole pixels there are the fix, not the drift. Look for a comment; if there is none, the value still has to earn one.

**A connector read as a divider.** The stroke inventory cannot tell a rule that separates from a rail that joins. A timeline spine, a thread down a comment chain and a bracket around a group are Gestalt *continuity* — they build one object out of several. A hairline between two blocks is the thing to delete.

**A decorative rule under something already identified.** An underline beneath text that is already coloured, already a link and already underlined by role carries no information on its own. It fails a 3:1 reading and no one depends on finding it. Keep it, and write down that the exception is deliberate.

**An emoji reported at 1.0:1.** A colour glyph paints its own colours and ignores `color`. The audit skips runs that are only pictographs; a pictograph inside a sentence still gets measured against the sentence's ink, which is right.

**Bleed past the viewport.** A portrait that runs off the right edge is usually the design. It is filed as a note so it can be dismissed once. What matters is whether the *document* scrolls sideways, which is a separate, high finding.

**A heading level skipped by a visually hidden landmark.** Structure is read from the DOM, not from what is painted, so an `sr-only` `h2` counts. If a jump still reports, it is real.

**An italic tracking a hundredth wider than its paragraph.** A synthesised oblique closes its right sidebearing; opening it back is an optical correction every type designer makes. Bare inline tags are excluded for this reason — if one still reports, it has a class, which makes it a role.

## The shapes that are almost always real

**Two containers in one row starting to read at different heights.** Bottom-anchored content (`justify-content: flex-end`) agrees the bottoms of a row and lets the tops fall wherever the copy leaves them. The eye scans a row across, so the line that matters is the first one.

**An absolutely positioned label over a flow label.** It does not push anything, so it simply paints on top when the container gets narrow. Nothing catches it because nothing looks at the narrow case.

**A proximity ratio under 1.** The gutter between two cards being smaller than the largest break inside one means the space is saying "these two belong together" about the wrong pair. Derive the gutter from the interior rather than picking it: it has to beat the largest gap inside the thing it separates, and 1.5× is a defensible floor.

**Text over a photograph.** The only contrast case a token system cannot predict. The ground is whatever the image happens to be at that point, and it changes with the crop, the width and the art direction.

**An inset that does not follow its type.** When a component's loud variant sets 56% more type in the same padding as its quiet one, the biggest thing on the page is proportionally the tightest. Take the base ratio — inset ÷ largest title — and apply it.

## Two things worth checking before you believe any run

**The server.** Point at the built output on a port you own. A stale daemon holding the port answers instead, and the audit measures a build from three commits ago with total confidence. `curl` one route and one asset before trusting a number.

**Scroll-linked effects.** Parallax, scroll-driven animations and reveals gated on an observer all depend on where the page is when it is measured. The audit walks the page to fire them and returns to the top; anything whose appearance depends on scroll position is measured in one state, not all of them.
