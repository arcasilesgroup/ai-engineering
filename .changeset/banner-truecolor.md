---
"ai-engineering": patch
---

`ai-eng` crashed on startup under Bun 1.3.x: the banner frame painted the brand hex `#00ED64` through `styleText` (node:util), whose runtime validation accepts only named formats — strict runtimes threw `ERR_INVALID_ARG_VALUE` on the first render, and lenient ones (Bun 1.4, Node ≥ 24.1) silently dropped the colour, so the banner shipped unpainted there. The banner now emits the truecolor SGR sequence for the declared hex itself, degrading to plain text under `NO_COLOR` or a non-TTY stdout — the same rule the rest of the frame follows. `BANNER_META` keeps its named format through `styleText`.
