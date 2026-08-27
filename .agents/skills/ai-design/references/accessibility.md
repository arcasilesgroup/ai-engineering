# Accessibility — the honesty floor for designed surfaces (spec 038 / B-038-1/2)

Cargada solo cuando corre un verify pass (economía de contexto, spec 033). Un diseño que
el framework produce cumple el piso de accesibilidad o sale con `not-covered: <razón>`;
nunca un pass silencioso.

## Los cuatro básicos

1. **Contraste** — ≥ WCAG 2.2 AA sobre el fondo real (ya lo mide el verify de ai-design
   paso 7; no sobre CSS declarado).
2. **Teclado** — todo elemento interactivo es alcanzable y operable solo con teclado.
3. **Focus visible** — el foco es siempre visible al navegar por teclado.
4. **Reduced motion** — `prefers-reduced-motion` respetado (lo delega la lente de motion
   de ai-review; el diseño no añade movimiento que lo ignore).

## La regla

Un verify pass que nombre los cuatro básicos pasa. Un verify pass que **deliberadamente no
puede** cumplir uno o más sale `not-covered: <razón>` — la salida honesta, registrada,
nunca un pass silencioso ni un stall. Un verify pass que no nombre los básicos ni un
`not-covered` es rechazado por `contract._accessibility_problems` (silent pass refused).

## Misma disciplina, dos superficies

- `NOT COVERED` (verifier frío, spec 030): una lane que no corrió.
- `not-covered` (diseño, spec 038): una superficie que no puede cumplir el piso.
La misma honestidad, dos sitios; la grafía queda ligada en este reference y se unifica en
una constante solo cuando una segunda superficie lo necesite.

## Landmarks y más allá (medida por necesidad, no hoy)

Landmarks, etiquetas de screen-reader, orden de tabulación: se añaden al piso solo cuando
una superficie las necesite; el piso actual es el mínimo funcional (contraste, teclado,
focus, reduced-motion).

## Insumos de diseño (spec 037 roadmap filas 6/16)

Las skills de diseño (apple-design, hallmark, high-end-visual-design, emil-design-eng, y
las del roadmap) son insumos que esta skill de diseño puede cargar; nunca skills del
framework. Este reference es el piso que cualquiera de ellas debe respetar.