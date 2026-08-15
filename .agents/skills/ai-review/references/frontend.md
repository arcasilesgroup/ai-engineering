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
