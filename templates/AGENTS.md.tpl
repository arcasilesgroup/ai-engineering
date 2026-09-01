# AGENTS.md — governed by {ai} Engineering ({{version}})

## Seguridad
3. Never `--no-verify`. Never silence a linter (noqa, @ts-ignore, nosec).
8. No secrets, no personal data, no machine paths in files.

## Calidad
9. Explain it so someone who doesn't code can follow along.
10. KISS, YAGNI, DRY, SOLID, TDD, Clean Code.

## Flujo
6. Green gate before «hecho». Show the output.
12. A decision that always comes out the same is code, not a prompt.

## Status (convención en todo task list)
🟢 done (con prueba pegada) · 🟡 pending (nómbralo) · 🔴 blocked on user

## Capas (las editas tú; el arch-test las lee desde .ai-engineering/arch.rules.json)
Hoy: feature-based (src/features/**, src/shared/**)

## Comandos (los que doctor detectó para este lenguaje)
{{commands}}

## Sesión (economía de contexto)
/clear entre tareas · /compact antes de parar, no después · batch prompting · /usage si el contexto se infla

## Anti-deriva
This list contains only what the agent CANNOT deduce from the project. Si una regla se vuelve obvia
leyendo el código, se borra de aquí.
