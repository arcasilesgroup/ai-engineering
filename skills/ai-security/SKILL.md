---
name: ai-security
description: Úsalo cuando el hito declara un audit de seguridad, cuando necesitas validar findings adversarialmente, o trigger for "security review" — audit de 6 fases con validación adversarial: el que valida jamás es el que encontró.
license: MIT
---

# Security audit (Cloudflare), gobernado por ai-engineering

El método es de **cloudflare/security-audit-skill** (MIT, ~3.2k★), palabra por palabra — no lo hemos reescrito:

- Pipeline de 6 fases: recon → hunt paralelo por clases de ataque → **validación adversarial**
  → report → findings.json → verificación independiente → [cloudflare-security-audit-SKILL.md](cloudflare-security-audit-SKILL.md)
- Las 8 familias de ataque, una referencia por familia → [AI-AND-LLM.md](AI-AND-LLM.md) ·
  [ATTACK-CLASSES.md](ATTACK-CLASSES.md) · [CLIENT-SIDE.md](CLIENT-SIDE.md) ·
  [HUNTING.md](HUNTING.md) · [MEMORY-SAFETY-AND-BINARY.md](MEMORY-SAFETY-AND-BINARY.md) ·
  [RECONNAISSANCE.md](RECONNAISSANCE.md) · [VALIDATION-AND-REPORTING.md](VALIDATION-AND-REPORTING.md) ·
  [WEB-PROTOCOL-AND-AUTH.md](WEB-PROTOCOL-AND-AUTH.md)
- El validador ejecutable de findings y su schema → [validate-findings.cjs](validate-findings.cjs) ·
  [report-schema.json](report-schema.json)

## Lo que añade ai-engineering (la costura)

1. La salida se fija en `.ai-engineering/security/run-N/` — `findings.json` validado contra
   report-schema.json + `REPORT.md`. Los últimos `keep_runs` (config.toml) permanecen vivos:
   el ledger de conocidos del run N lee a los anteriores.
2. Cuando el hito incluye un audit, sus fases se expresan como gates de `spec.html`:
   «findings validados contra schema» y «cero HIGH abiertos» son CHECKs ejecutables de
   `ai-eng spec run` — no lectura de cortesía.
3. El principio sin concesiones del fuente es también el de ai-proof (§9.3): solo reportas
   lo que puedes explotar. Sin exploit demostrable no hay finding.
4. Quién verifica: el tier `verify` del pin (§09.4); quién juzga las conclusiones: `decide`.
   El que valida no es el que encontró — la validación adversarial es innegociable.
