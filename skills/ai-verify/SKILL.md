---
name: ai-verify
description: Úsalo cuando hay que verificar trabajo — "verify the feature", "did we build what was asked", "review this diff", "is it ready to commit" — eligiendo el tier correcto de verificación (standalone, embedded o chain) y produciendo veredictos con evidencia, no impresiones.
license: LicenseRef-Attributed
---

# ai-verify — verificación en tres tiers (Graph Engineering)

Tres formas de verificar según quién dispara: skills que corras a propósito, skills que se disparan solas a mitad de flujo, y una cadena de lanes de review. El router de la cadena decide qué lanes corren por la evidencia del diff, nunca por el tamaño.

Tier 1 — standalone (lo corres a propósito):

- Veredicto por requisito contra lo que se pidió de verdad → [tiers/1-standalone/verify-feature/SKILL.md](tiers/1-standalone/verify-feature/SKILL.md)
- Extrae los requisitos de la conversación a claims numerados y falsables → [tiers/1-standalone/spec-extract/SKILL.md](tiers/1-standalone/spec-extract/SKILL.md)

Tier 2 — embedded (dispara solo, a mitad de workflow):

- Verificación browser del feature terminado + blast radius de las rutas que dependen del cambio → [tiers/2-embedded/feature-verify/SKILL.md](tiers/2-embedded/feature-verify/SKILL.md), con [blast_radius.py](tiers/2-embedded/feature-verify/scripts/blast_radius.py), [setup_harness.sh](tiers/2-embedded/feature-verify/scripts/setup_harness.sh) y [references/](tiers/2-embedded/feature-verify/references/)
- Segunda opinión de un Claude fresco que no ve tu razonamiento → [tiers/2-embedded/second-opinion/SKILL.md](tiers/2-embedded/second-opinion/SKILL.md)

Tier 3 — chain (lanes de review por evidencia):

- Router que elige lanes, estima coste y ejecuta → [tiers/3-chain/review-router/SKILL.md](tiers/3-chain/review-router/SKILL.md)
- Lanes: [code-audit](tiers/3-chain/code-audit/SKILL.md) · [security-audit](tiers/3-chain/security-audit/SKILL.md) · [a11y-audit](tiers/3-chain/a11y-audit/SKILL.md) · [perf-audit](tiers/3-chain/perf-audit/SKILL.md) · [design-check](tiers/3-chain/design-check/SKILL.md) · [build-check](tiers/3-chain/build-check/SKILL.md)
- Fusión de todas las lanes en un informe deduplicado → [full-review](tiers/3-chain/full-review/SKILL.md); convenciones de scope y diff → [CONVENTIONS.md](tiers/3-chain/_support/review/CONVENTIONS.md)

Guía de setup y router de entrada → [VERIFICATION-SETUP-GUIDE.md](VERIFICATION-SETUP-GUIDE.md). Evals (plantar bugs reales y puntuar al revisor) → [evals/README.md](evals/README.md): [plant.py](evals/scripts/plant.py), [score.py](evals/scripts/score.py), [bug-catalog.md](evals/bug-catalog.md), pack de ejemplo [answer-key.json](evals/packs/example-node-web/answer-key.json).

Fuente: Graph Engineering — Verification Skills (skills del vídeo, generalizadas a cualquier stack; attributed, sin licencia — issue H4; sin repo público declarado en la fuente).

Lo que añade ai-engineering (la costura):

1. El router elige tier por la taxonomía de la fuente.
2. El juez usa tier `decide`; los checks binarios, `verify`.
3. Los evals (plant.py/score.py) corren en CI del repo de ai-eng, no en el proyecto del usuario.
4. Salidas: veredictos → EVIDENCE de spec.html + receipt.
