# Handshake · El grafo del ciclo: un router para que humano y agente decidan el camino

Status: complete · 2026-09-10 · arquitectónico (clasificación ratificada por el humano)

> Este slot lo ocupaba el handshake de la skill que audita AGENTS.md — hito cerrado y mergeado sin contrato, así que su documento nunca murió: es el zombi que motivó este hito. Recuperable en git: `git show f2e5ee19:.ai-engineering/brainstorm.md`.

## La idea en palabras llanas

Hoy ai-engineering tiene veinte skills y una maquinaria de gobierno que funciona, pero el orden en que se usan solo existe escrito en el blueprint. Cada skill conoce a quién no llamar y casi ninguno sabe a quién llamar después, así que el camino se improvisa: se hace la idea y se salta directo a construir, o se abre un contrato y nadie lo cierra. Queremos que el encadenado esté **declarado por cada skill** y que el agente lo siga solo: al terminar cualquiera de ellas, deja dicho cuál es su sucesor y con qué condición, así que el hilo no se corta nunca y tú no tienes que conocer el mapa ni llamar a nada. El carril (una pregunta suelta, un cambio acotado o algo que reestructura) lo nombra quien ya lo clasifica hoy, el brainstorm, junto con la ruta que ese carril implica y las condiciones exactas que añaden nodos. Y los documentos que el ciclo produce — brainstorm, spec, plan, research, audit, recap — por fin tienen quién los escribe, quién los lee y cuándo mueren, con un portero que lo comprueba antes de dejar cerrar el hito.

## Por qué importa

Medido en este repo, no supuesto:

- `brainstorm.md` lleva vivo desde un hito cerrado. `ai-eng doctor` dice `clean slot: 0 zombie contracts` porque solo mira `spec.html` y el lock: el hito nunca abrió contrato, así que `spec close` (el único que borra el slot) no podía correr.
- `spec close` presume de exigir "receipt por gate o ABANDON" y busca `<div class="gate">`, markup que ningún `spec.html` de la historia ha tenido: cero coincidencias, cero negativas. Se ha cerrado siempre sin comprobar nada.
- `recap.html` no aparece ni una vez en el historial: el paso 12 nunca corrió y nada lo notó.
- Veinte skills, cuatro aristas hacia adelante. El AGENTS.md que plantamos no menciona el ciclo, así que un agente nuevo no puede saber que existía un paso 2.
- `ai-goal` afirma que "el goal nativo de la superficie" corre el bucle. Pi no trae plan mode ni sub-agentes y aun así lo tratamos como superficie core; nadie lo comprueba porque "loop nativo" no es una capacidad declarada.

## Quién es el usuario

El que teclea: quiere poder elegir rápido o exhaustivo sin perder gobernanza. Y el agente: necesita descubrir el orden sin que se lo cuenten en cada sesión.

## Qué existe hoy (verificado)

- `ai-eng spec open|approve|close` en `src/spec/index.ts:74,100,116`; sha256 en `ai-eng.lock` que self-protect vuelve inmutable; `SLOT_FILES` en `src/spec/index.ts:17`.
- `doctor --gc` en `src/commands/doctor.ts:217`; `[gc]` con cuatro claves, dos usadas.
- Canon G1-G8 en `tests/skills.spec.ts`; `ai-design` es el único router del canon, y rutea diseño, no el ciclo.

## Qué éxito significa

Un hito que se abre con `spec open`, se aprueba, corre, cierra con `spec close` — y que al cerrar no deja ni un documento huérfano; y un agente que, leyendo solo el AGENTS.md plantado y el router, sabe qué toca sin preguntar.

## Decisiones ya tomadas

- **Nada de router ni hub.** Descartado `ai-route`: el grafo es la unión de los veinte bloques `## Lifecycle`, una sola fuente, sin mapa central que mantener sincronizado ni estado duplicado (`plan.html` ya lleva el 🟢/🟡 por paso). El encadenado vive en el `Next:` de cada skill.
- **Tres carriles** (light / standard / full) con ratchet de un solo sentido: se sube, no se baja en silencio.
- **Alcance del primer hito: el grafo entero** — bloques de ciclo de vida + gates de canon, triggers mecánicos, registrador civil (doctor + gc), fallback de ai-goal y los drifts del blueprint.
- Los triggers de UI/seguridad/research/architect/write son globs declarados **por el nodo que los posee**, y se evalúan contra el diff desde el commit base del hito.
- `spec open` registra ese commit base en el lock.
- **El hilo no depende de que el humano se acuerde del mapa.** Cada skill cierra con un `Next:` (su sucesor y la condición que lo elige): el agente anuncia el siguiente nodo solo. El carril lo nombra `ai-brainstorm` al aprobar, junto con la ruta que implica.
- **El humano habla en palabras; el agente corre el binario.** Las paradas se declaran como palabras ("apruebo", "ok", "adelante", "cierra", "listo") mapeadas al comando que ejecuta el agente por debajo, y cada parada declara además `Confirms:` — qué está aprobando el humano. Aprobar sigue siendo solo humano: la palabra es la puerta, el comando es el lápiz, y una palabra que responde a otra frase no es una aprobación.
- **Auditoría adversarial antes de aprobar** (agente `adversary` sobre nan/mimo-v2.5, tres ataques independientes: diagnóstico, diseño y gates). Cinco hallazgos aceptados y ya dentro del contrato: (1) la regla `Confirms:` contra la auto-ratificación de un "ok"; (2) `spec close` re-verifica el sha256 aprobado y rechaza un ABANDON sin razón; (3) gc no puede contar su propio `summary.json` como receipt en la corrida siguiente — `summarizeReceipts` lee todo `.json` de la carpeta; (4) la inmunidad solo la dan gobernantes permanentes, porque spec/plan/brainstorm mueren al cerrar; (5) dos gates gameables: G13 pasaba con la palabra "facilitator" en cualquier contexto y G15 se satisfacía borrando un comentario — ahora la primera exige sección y la segunda exige que la lista de opciones del template iguale el registro de superficies.

## Decisiones aún abiertas

- **Qué superficies son `native`.** Pi es `none` (verificado: sin plan mode ni sub-agentes). El resto entra como `unverified` hasta que alguien lo mida con un receipt; ninguna se promociona por optimismo.
- **Si `[budget]` acaba siendo un medidor.** Hoy es contrato que el agente honra en cada frontera de paso; el binario no mide tokens.

## Restricciones y barandillas

- Nada de verbos CLI nuevos: `base_sha` vive en el lock y la evaluación de triggers dentro de `spec close` y `doctor`, que ya existen.
- El carril light es legal, no un atajo: es lo que `ai-brainstorm` ya manda para spike y bounded. Lo que cambia es que el artefacto igual muere.
- `ai-design` conserva su router interno de skills de diseño; el hito lo encadena la cadena de `Next:`.

## Fuera de alcance

- Detección en runtime del goal nativo por superficie (probe). La capacidad se declara y se verifica con receipt.
- Reescribir el orden de §20.1 entero: se le añaden los carriles, no se sustituye.

## Preguntas abiertas para investigación

Ninguna bloqueante. Referencia externa consultada para la forma del grafo: GraSP (arXiv:2604.17870), TROVE (arXiv:2609.05019), SkillRouter (arXiv:2603.22455).

## Notas de traspaso

Para el planner: el contrato vive en `.ai-engineering/spec.html` + `plan.html` de este mismo hito. Los puntos 01-08 del spec son el orden de trabajo; el paso 3 de plan.html (tests de canon) es el que convierte el grafo en algo que puede fallar.
