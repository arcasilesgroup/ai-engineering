# Handshake · CLI UX: alinear la superficie humana del binario con §14 del blueprint

Status: complete · 2026-09-01

## The idea in plain words

Tú ejecutas `ai-eng` en la terminal y no se parece al manual (§14 del blueprint). El
programa arranca bien (logo + marco de clack) pero a mitad de camino se sale del marco
y escupe texto plano. Además le faltan piezas que el manual ya dibujó: las preguntas
agrupadas de "boosters", el aviso de "hay versión nueva", y que `update` pregunte antes
de tocar archivos. El arreglo: cada comando se ve como su dibujo del §14, marco continuo
de arriba a abajo, y los flujos que faltan existen. Sin dependencias nuevas.

## Why this matters

El CLI es la primera impresión del producto y la parte que un humano ve en cada
invocación. El blueprint §14 lo especificó completo (mockups por verbo, seis caminos de
usuario cubiertos) pero la implementación actual se ve "feo feo feo" (palabras del
usuario): el frame se rompe a mitad de init, doctor/update no tienen banner ni resumen,
y flujos definidos (boosters, notice, merge 3-vías) no existen.

## Who it's for

El desarrollador que instala ai-eng en su máquina y en sus repos. Quien prueba el tool
y decide en los primeros 60 segundos si es serio.

## What exists today

Hechos verificados en el repo (2026-09-01):

- Blueprint: `docs/blueprint.html` §14 (líneas 1126-1476) contiene mockups completos
  de init fase 1 (14.0b), init fase 2 (14.1), doctor (14.2), update (14.3),
  upgrade (14.4), config y uninstall (14.5), seis caminos de usuario (14.5b) y el
  entry point de referencia (14.6).
- `src/branding.ts`: identidad propia (logo ASCII, teal #00D4AA, degradación
  NO_COLOR/no-TTY ya resuelta). showLogo, showBanner, okLine.
- `src/commands/init.ts`: dos fases ya implementadas (global + repo), idempotencia
  básica (re-init ofrece exit/update, no los tres caminos del mockup), sin boosters,
  confirm de git sin `initial`, checklist final con `process.stdout.write` crudo que
  rompe el frame de clack (líneas 132-144).
- `src/commands/doctor.ts`: 12 checks reales + adversarial probe; render crudo sin
  intro/outro (doctorMain 209-227). No existe el check "assets outdated"
  (binario X vs assets plantados Y) que §14.2 exige como WARN.
- `src/commands/update.ts`: re-planta y reescribe lock sin preguntar; el conflicto
  "patched by you" solo imprime una pregunta que nadie responde (update.ts:51).
  §14.3 exige: lista de qué sincronizar, diff 3-vías interactivo (merge/keep/diff),
  confirm Apply (con commit / sin commit / no), y commit final con mensaje.
- `src/commands/upgrade.ts`: delega en bun/npm correctamente; falta changelog inline
  y frame. Bug menor en upgrade.ts:39-41: la opción "print the command" imprime
  siempre el comando de bun aunque el usuario hubiera elegido npm.
- `src/commands/config.ts` y `uninstall.ts`: lógica correcta, presentación cruda;
  config no muestra hints "installed/not installed" ni la nota de thresholds.
- `src/cli.ts`: dispatch + help crudos; NO existe `maybeNotice()` (aviso de versión
  cacheado 24h con opt-out `notices = false` / AI_ENG_NO_UPDATE_NOTICES, §14.0).
  `canonVersion()` y `versionFile()` existen pero nadie hace el check al arranque.
- `src/surfaces/adapters.ts:90`: el nudge de SessionStart ya existe
  (sessionContextLines) y surfaces.json ya registra el evento.
- @clack/prompts 1.7.0 (ya dependencia): trae intro/outro, log.success/info/warn/error
  (pinta exactamente el `│ ✓ msg` del mockup), groupMultiselect (boosters agrupados
  con cabeceras no seleccionables), taskLog, spinner, confirm con `initial`. Cero
  dependencias nuevas.
- El catálogo de boosters de §14.1 (14 items en 5 grupos: Contexto, Diseño,
  Investigación, Seguridad, Diagnóstico) no existe en el código.
- package.json versión 2.0.0; los números 0.13.0/0.14.0 de los mockups quedan
  obsoletos: toda versión que la UI muestre sale de VERSION dinámicamente (2.0.0),
  nunca hardcodeada.

Bugs verificados leyendo el código (se incluyen en el alcance):

- Bug del "0 assets verified": doctor.ts:63-73 filtra lock.assets por rutas que
  contengan "skills/", pero el lock del repo no contiene skills (el canon vive en
  ~/.ai-engineering/skills y el lock guarda hooks/settings/config). Resultado:
  checked siempre 0. El check debe verificar el canon global contra los assets
  embebidos del binario (src/embed.ts), no contra el lock del repo.
- lock.version ya existe en el esquema (plant.ts:97-101): el check "assets
  outdated" del mockup §14.2 es comparar lock.version contra VERSION.
- update.ts usa require("node:crypto")/require("node:fs") inline (líneas 43, 55)
  pese a importar arriba: limpieza incluida.

## What success looks like

- Cada verbo humano se ve como su mockup de §14: frame continuo de clack de intro a
  outro, checks dentro del frame, resumen final con colores por estado.
- `ai-eng init` ofrece los boosters agrupados (imprime comandos, nunca instala).
- `ai-eng update` muestra qué va a sincronizar, resuelve conflictos con diff 3-vías
  interactivo y pregunta Apply antes de escribir.
- El aviso de versión aparece como una línea al final de init/doctor/update, cacheado
  24h, con opt-out.
- doctor incluye el WARN "assets outdated" y el conteo "verified" refleja la realidad.
- NO_COLOR y no-TTY degradan a texto plano en todos los verbos.

## Decisions already made

- La fuente de verdad visual es §14 del blueprint, no un rediseño nuevo.
- Cero dependencias nuevas: @clack/prompts 1.7.0 cubre todo.
- ai-eng imprime comandos de terceros, jamás los ejecuta (§14.1).
- El logo/teal actual (branding.ts) se mantiene; lo que cambia es el uso del frame
  clack alrededor y dentro de cada verbo.
- Idioma de la UI: inglés (cerrado con el usuario, 2026-09-01). Audiencia npm global;
  el canon de skills ya es English only; las capturas actuales están en EN.
- Alcance: presentación + gaps de §14 + mejora libre (cerrado con el usuario,
  2026-09-01). Los bugs de contenido detectados entran.
- Motor de render: capa ui.ts propia (cerrado con el usuario, 2026-09-01). Un módulo
  finito que centraliza frame, niveles de log y degradación NO_COLOR; los comandos
  lo consumen.

## Design

Idioma: inglés. Alcance: presentación + gaps de §14 + mejora libre. Motor: capa ui.ts.
Secciones:

A. src/ui.ts (~120 LOC): frame(title) con clack intro/outro; ok/warn/fail/info
   sobre log.* de clack (la espina │ se sostiene); summary(ok, warn, fail) con
   colores; showLogo sigue para --help/--version. showBanner muere si nadie lo usa.
B. init: hints de superficies mapeados de surfaces.json (tier + can.*), boosters
   con groupMultiselect (5 grupos, 14 items, src/boosters.ts nuevo, imprime
   comandos nunca ejecuta), confirm de git con initial true, re-init con los tres
   caminos (update / config / exit), checklist dentro del frame, nota bootstrap
   cuando no hay src/, "Two steps" como outro.
C. doctor: intro contextual (repo · runtime · versión), check 4 reescrito (canon
   global vs embebidos del binario), check nuevo assets-outdated (lock.version ≠
   VERSION → WARN → update), checks por ui.*, summary coloreada.
D. update: plan de sincronización calculado antes de escribir; lista "What needs
   to sync"; conflictos con opciones keep-yours (default) / take-new / show-diff;
   confirm Apply (Yes+commit / Yes / No); commit chore(ai-eng): assets → <versión>;
   caso feliz corto cuando no hay nada que sincronizar.
E. upgrade/config/uninstall: frame + changelog inline si el CHANGELOG local trae
   la sección (si no, URL); config con hints installed/not-installed y nota de
   thresholds; uninstall con el flujo exacto de §14.5 y outro final.
F. cli.ts: maybeNotice() cacheado 24h (versionFile), silencioso si falla, una
   línea al final de init/doctor/update, opt-out notices=false o env var. Verbos
   máquina intactos.

Errores: todo stderr crudo de verbos humanos pasa a log.error dentro del frame;
isCancel → cancel() de clack + exit 0; exit codes sin cambiar (2 = fallo).
Tests: unit para maybeNotice (TTL, opt-out) y para el plan de sync de update
(funciones puras); el render se verifica con corrida real en terminal (proof, no
test). Lint + typecheck + suite completa al cerrar.

## Constraints and guardrails

- AGENTS.md del repo: sin silenciar linters, sin --no-verify, green gate antes de
  "done".
- El binario es el payload: tocar src/ no requiere regenerar assets salvo que se
  toquen skills/ o templates/.
- Presupuesto de dependencias: cap de 3 (args, tab, clack) ya alcanzado.
- Los verbos de máquina (chain, git, wrap, spec) NO cambian: su stdout es contrato.
- Cada cambio de presentación debe pasar los tests existentes (adversarial + gates
  + arch) y lint/typecheck.

## Out of scope

- Cambiar la lógica de guards, receipts o la cadena de hooks.
- Los mockups de spec.html/plan.html (§22 branding de artefactos HTML): otro frente.
- Nuevas superficies o cambios en surfaces.json.
- Renombrar verbos o añadir verbos nuevos.

## Open questions for research

1. ¿Qué imprime exactamente update como "what needs to sync" cuando el diff es
   vacío (repo recién init con mismo binario)? Definir el caso feliz corto.
2. groupMultiselect: confirmar comportamiento de cabeceras no seleccionables y
   navegación con tab en ghostty antes de implementar.

## Handoff notes

- Orden sugerido: ui.ts (capa de frame) → init (boosters + frame + initial) →
  doctor (frame + check assets-outdated + fix conteo) → update (confirm + 3-way
  interactivo + commit) → upgrade/config/uninstall (frame) → maybeNotice en cli.ts.
- El blueprint §14.5b (seis caminos) es el checklist de aceptación de init.
- Tests: tests/adversarial/chain.test.ts no toca presentación; los gates de
  tests/skills.spec.ts siguen aplicando si se toca skills/ (no hace falta).
- §14.0b/14.1 mockups: los hints de superficies del mockup ("✔ core — deny +
  rewrite input/output") vienen de surfaces.json (tier + can.*): mapear, no
  hardcodear.
- Riesgo de render: taskLog vs log.* dentro de spinner; decidir en implementación
  con corrida real, el contrato es el mockup.
- src/assets.ts NO se regenera (no se toca skills/ ni templates/).
