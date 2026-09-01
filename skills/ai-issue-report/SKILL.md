---
name: ai-issue-report
description: Úsalo cuando algo pasó y el equipo necesita un reporte técnico estructurado — issue o incidente reproducible — con pasos de reproducción, campos cerrados, escaneo de rutas de máquina y secretos, y los bytes exactos con su SHA-256 antes de que nadie confirme nada. Not for un fallo de tu propio código sin diagnosticar (/ai-debug) ni para una vulnerabilidad con ruta pública: disclosure privado.
license: Apache-2.0
---

# ai-issue-report

Reporte de un issue o incidente reproducible como payload gobernado: campos allow-list,
escaneos, borrador local gitignored y los bytes exactos con su digest a la vista antes de
que cualquiera confirme nada. El envío es separado y manual; esto no manda nada solo.

## Lo que trae la fuente

- Método completo: reproducir primero, `--kind security` nunca se vuelve público (imprime la ruta privada y se niega a la otra), los cuatro campos en tus palabras sin pegar logs ni diffs, leer la negación (`ACCEPTANCE_MACHINE_PATH_*`, `ACCEPTANCE_PII_*`, `ACCEPTANCE_GITLEAKS_SECRET`), verificar bytes + SHA-256, envío con frase que lleva el digest → [ai-report-SKILL.md](ai-report-SKILL.md)
- Corpus de ruteo: qué frases llegan aquí y qué se rechaza (sin diagnóstico → /ai-debug, hallazgo interno → /ai-note, decisión → /ai-spec, PR → /ai-ship; «attach the log» y «just send it» se niegan por diseño del payload) → [corpus.md](corpus.md)
- Estilo del write-up: una idea por frase, un significado por palabra, nada que el entorno ya diga repetido → [references/documentation-writer.md](references/documentation-writer.md)

Fuente: ai-engineering v1, skill `ai-report` (propio), Apache-2.0 — integrado aquí como
método de ai-issue-report sin una línea reescrita.

## Lo que añade ai-engineering (la costura):

1. Salida: `.ai-engineering/reports/NNN-{slug}.html` — post-mortem legible sin contexto de
   sesión; la numeración NNN no se reescribe.
2. Inmune mientras DECISIONS.md lo cite; sin cita, caduca a gc (§21.3) — la historia no se
   reescribe.
