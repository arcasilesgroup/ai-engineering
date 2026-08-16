# Frontend

Loads only when the diff touches markup, styles or a component. It judges what is there; it
does not redesign it and does not repair it — that is `/ai-design` and `/ai-build`.

- Semantics before ARIA: a button that is a `div` needs four attributes to behave like the
  element it should have been.
- Keyboard: every interactive thing reachable, in an order that matches the visual one, with
  a focus state somebody can see against the real background.
- States: empty, loading, error, partial, too-long, too-many. A component with one state is
  a component that has only been seen with the developer's own data.
- Contrast measured over what is actually behind the text — a gradient, an image, a
  translucent panel — and not over the token's nominal colour.
- Reflow at 320 CSS pixels and at 200% zoom, with no horizontal scroll and nothing clipped.
- Text that grows: the longest realistic string, not the shortest, and a translation that is
  forty per cent longer than the English.
- Errors say what to do next, in the place the mistake was made.
- AA is the floor. Anything claimed above it names the criterion and its evidence.

## The definition of done, item by item

Written out because "accessible" is a word and this is a list. Each item is a thing somebody
either ran or looked at, and an item with neither beside it is not done.

- Name, role, value and state readable for every control, including the ones built out of
  `div`s.
- A dialog returns focus to whatever opened it, and the page behind it is inert while it is
  open.
- Touch targets are at least 24 by 24 CSS pixels, or spaced so the next one is not hit.
- A pointer action can be cancelled: pressing down and moving away does not fire it.
- Anything that needs a drag has a way that does not, on the same screen.
- Orientation is not locked unless the content genuinely only works one way.
- 400% zoom, and the content reflows rather than clipping or scrolling in two directions.
- Forced-colours mode keeps every boundary and every state distinguishable.
- Paste works in password and one-time-code fields; blocking it is an accessibility fault.
- Announcements reach a screen reader when something changes without a page load.
- Nothing flashes more than three times a second.
- Audio and video carry an alternative: captions, a transcript, or a described track.
- Motion respects the reduced-motion preference, which is judged by the motion lens beside
  this one.
