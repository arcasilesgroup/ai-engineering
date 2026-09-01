---
name: ai-rtk
description: Úsalo cuando vayas a correr comandos de shell con salida larga — tests, builds, git, búsquedas, logs de docker/kubectl, CLI de nubes — para routearlos por rtk y leer −60–90% menos tokens de output; también para instalar o configurar rtk, verificar qué reescribe con rtk rewrite, o reportar ahorros con rtk gain.
license: MIT
---

# ai-rtk

rtk es un proxy CLI que filtra y comprime la salida de un comando antes de que llegue al
modelo: `rtk cargo test` corre la misma suite y devuelve solo fallos, `rtk git push`
devuelve `ok main` en vez de quince líneas de progreso. No cambia lo que un comando hace —
solo cuánto de su output lees.

## Lo que trae la fuente

- Método completo de ruteo: cuándo prefijar y qué NUNCA prefijar (builtins, mutaciones de ficheros, pipes, intérpretes, control de flujo), `rtk rewrite` como única verdad de qué se reescribe, lectura de ficheros por niveles con `rtk read -l`, bypass con `rtk proxy`, configuración, `rtk gain`/`rtk discover`, y las trampas verificadas → [rtk-SKILL.md](rtk-SKILL.md)
- Referencia por comando con reducción y qué cambia en cada uno (git, forges, cargo, jest/vitest/tsc, pytest/ruff, go, rspec, php, jvm/dotnet, docker/kubectl, terraform/pulumi, aws/gcloud/psql, linters y wrappers genéricos `rtk test`/`rtk err`/`rtk summary`), telemetría y casos no cubiertos → [references/commands.md](references/commands.md)

Fuente: rtk (autometa / Hermes Agent), MIT — https://github.com/rtk-ai/rtk ·
flags y comportamiento verificados contra el binario v0.45.0.

## Lo que añade ai-engineering (la costura):

1. rtk es binario ajeno: ai-eng lo OFRECE en init — imprime `brew install rtk · rtk init`
   (con la versión pinneada y la licencia) y el humano lo corre. Nunca se ejecuta desde
   ai-eng y nunca se bundlea; el hook de reescritura se planta por superficie.
2. La capa fina routea comandos de shell por rtk: −60–90% tokens de output. Al bajar el
   coste de leer la salida, baja el coste de verificar.
