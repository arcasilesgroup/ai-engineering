# Handshake · Gobernanza por observabilidad (research 001)

Status: grilled · 2026-09-21 · enfoque A aprobado por el humano

## The idea in plain words

Read-back aprobado, tal cual se validó:

> En este repo un robot hace el trabajo y unos guardias lo vigilan: cada vez que el robot quiere
> tocar algo, un guardia dice sí o no, y anotan la respuesta en un papelito. Un mes después,
> alguien tritura los papelitos y solo salva 4 números: cuántos hubo y cuántos fueron "no". Así
> que nadie se acuerda de nada.
>
> Queremos tres cambios chicos:
> 1. Al triturar, salvar mejor el resumen: qué guardia dijo no, a qué herramienta, en qué día. Y
>    si un día los "no" se disparan comparados con lo normal, el revisor (`doctor`) avisa con un
>    WARN.
> 2. Un cuadernito de "no" que sobrevive a la trituradora. Cuando un guardia dice "no" otra vez,
>    el cuadernito se consulta y el aviso le dice al robot: "esta llamada exacta ya fue negada N
>    veces antes". No cambia ninguna decisión; solo informa. Así, un atacante que reintenta lo
>    mismo desde otra sesión por fin se ve.
> 3. Cuando un texto truque las letras para esconder una mala palabra y el filtro lo pierda,
>    anotar ese casi-fallo en el resumen diario. Solo visible, nunca un "no" nuevo.
>
> Y como todo esto es ceremony nueva, el blueprint se corrige para decir la verdad ("no hacemos
> un sistema de observabilidad; sí agregamos señal dentro de la limpieza que ya existía") y
> queda escrito: si en 90 días el cuadernito no cazó ni un repeat y no saltó ningún WARN, esta
> capa se borra.

## Why this matters

OWASP Top 10 for Agentic Applications 2026 nombra dos primeros principios: least agency y strong
observability. El framework tiene la primera mitad casi completa y la segunda es un contador. La
cita de OWASP: "Least agency without observability is blind risk reduction". (research/001 §02)

## Who it's for

El humano que corre `ai-eng doctor` en el repo gobernado (deja de ver 4 números y ve qué niega su
máquina) y el agente que lee el mensaje del deny (ve que su reintento exacto ya fue negado). La
visibilidad entre máquinas o entre gente sigue fuera de alcance: el trail es machine-local.

## What exists today

Verificado esta sesión contra el árbol actual (no solo contra el research):

- `summarizeReceipts()` → `src/receipts.ts:41-86`: exactamente `{ total, denies, p50, p95 }`.
- `doctor --gc` (`gcReceipts`) → `src/commands/doctor.ts:421-437`: escribe solo ese resumen plano
  en `summary.json` y borra los receipts crudos tras el TTL (30 d).
- La línea de doctor que muestra los números → `src/commands/doctor.ts:187-191` (check 7).
- El `Receipt` ya trae `surface`, `tool`, `guards.ran`, `guards.denied_by`, `outcome`, `ts` →
  `src/receipts.ts:10-20`. Los sensores existen; el gc tira el detalle.
- `denyOutcome()` → `src/chain/mod.ts:237-261` es el único embudo de todos los denegados
  (guard-deny, cached-deny y fail-closed de payload ilegible pasan por él) y ya tiene `fp` en
  mano antes de llamar (`src/chain/mod.ts:148,165,180`). El mensaje humano sale por ahí.
- Presión actual medida (research 001, contada con jq): 3 663 receipts, 103 denies (~3%).
- Postura declarada hoy: blueprint §10 "Sin observabilidad propia... solo receipts locales".

Cuatro correcciones a la lectura del research 001, encontradas al abrir el código esta sesión:

1. **El research subestimó su propio hecho 1.** No solo el payload ilegible pierde la herramienta:
   `denyOutcome` pone `tool: "unknown"` duro en TODOS los denies (`src/chain/mod.ts:250`), cuando
   `runChain` sí tiene el `tool` real en esa pila (`:147`). Los 103 denies del repo dicen hoy
   `tool:"unknown"`. El `per_tool` de R1 no existe sin arreglar esto primero (~3 líneas: pasar el
   tool por parámetro; el camino del payload ilegible conserva "unknown" como cubo propio).
2. **El fold-miss literal es indectable como está escrito.** `fold` (`src/guards/injection.ts:38-40`)
   es NFKD + borrar no-ASCII. Si el texto crudo toca un patrón (que es ASCII puro), sus caracteres
   ASCII sobreviven al fold intactos → el folded SIEMPRE toca lo que toca el raw. El caso que se
   quiere ver (homoglifos cirílicos) no matchea en NINGUNO de los dos; verlo exige una tabla
   confusables (Unicode ICU), no 6 líneas. Se cierra en Design §6: cae del alcance.
3. **R2 no puede usar `fingerprint()` tal como la escribe el research.** `fingerprint`
   (`src/chain/payload.ts:90-98`) incluye `session_id` y `tool_use_id`: es la clave de dedup de
   UNA llamada física. La misma llamada reintentada desde otra sesión produce un fp distinto, así
   que el ledger nunca vería count > 0 y R2 no detectaría nada. La clave correcta ya existe:
   `loopExact(payload)` (`payload.ts:105-107`, sha256 de tool + input completo, sin sesión), que
   es exactamente "esta llamada exacta".
4. Detalle de gc visto en `gcReceipts`: `summary.json` se **sobrescribe** en cada pase
   (`doctor.ts:433`), no se acumula. La serie diaria que pide la señal 2 exige merge con el
   archivo existente, no overwrite.

## What success looks like

Dos señales, ambas observables sin herramientas nuevas (cerrado por el humano):

1. **En vivo (R2):** la próxima vez que un agente reintenta una llamada ya-negada desde otra
   sesión, el mensaje humano dice "esta llamada exacta fue negada N veces antes" sin que nadie
   abra un archivo. (Clave: `loopExact`, no `fingerprint`; corrección 3.)
2. **En reposo (R1):** `ai-eng doctor` deja de ser 4 números: responde qué niega esta máquina
   (por guard / herramienta / superficie, serie diaria) y suelta un WARN cuando los denies se
   disparan sobre la banda histórica, nombrando el guard que más manda en el pico. (Regla única
   sobre la serie global, no por guard: con ~1 deny/día las bandas por guard son ruido; si un
   día el ruido de un guard se ahoga en el volumen de otro, se sube a serie por guard.)

Un criterio sin el otro deja la mitad del hueco: la frase sin agregados no da línea base; los
agregados sin frase no llegan al momento en que alguien actúa.

## Design (enfoque A, aprobado)

1. **`denyOutcome` (`src/chain/mod.ts:237-261`)**: la firma gana `tool` y `loopKey` (el
   fail-closed de payload ilegible, `:143`, no tiene ninguno de los dos: conserva `"unknown"`
   como cubo propio y no escribe ledger; no hay clave que anotar). En el camino de deny,
   `loopExact(payload)` → mapa `fp → {n, last_seen}` en `receipts/denies.json`, escrito con
   try/catch "state must never break the chain" (patrón `loop.ts:42-50`). Con `n ≥ 2` el
   `reason` gana la cláusula "· esta llamada exacta fue negada N veces antes". Veredicto
   intacto; cero cómputo nuevo en allows.
2. **`summarizeReceipts` + gc**: el summary añade `per_guard` (por `denied_by`), `per_tool`,
   `per_surface` y serie diaria `{runs, denies}`. `gcReceipts` hace **merge** de la serie por
   día (overwrite por clave de día; la ventana cruda manda) en lugar del overwrite total de
   hoy, y poda días > 90d.
3. **Podas en el gc existente**: `denies.json` pierde entradas con `last_seen` > 90d y se
   acota a 500 por recencia. Las dos exclusiones obligatorias: `summarizeReceipts` exceptúa
   también `denies.json` (hoy solo exceptúa `summary.json`, `receipts.ts:69`), y `gcReceipts`
   se lo salta en la barrida por mtime (`doctor.ts:427-431`) o se comería el ledger.
4. **Doctor check 7 (`doctor.ts:187-191`)**: imprime lo de hoy + denies por guard/tool +
   repeats del ledger; WARN si los denies de los últimos 7 días superan 3× la media diaria de
   los 7 previos (3x fijo en código), nombrando el guard mayoritario. Sin serie previa
   (primera corrida de gc), la regla no dispara.
5. **Blueprint §10**: el renglón se enmienda ("no construimos un sistema de observabilidad;
   sí agregamos señal dentro del gc que ya existe") y la señal de muerte de 90 días queda
   escrita en el spec. Ambos son entregables del contrato.
6. **Fold-miss: fuera** (corrección 2: indetectable sin tabla confusables; el proxy barato
   dispara con contenido español legítimo). El read-back prometía "tres cambios chicos"; el
   tercero se cayó al abrir el código, y esta es la cuenta, no un olvido.

## Decisions already made

- Alcance: **R1 + R2 dentro; R3 fuera.** El alias OTLP espera a que alguien envíe receipts a un
  dashboard real; el schema queda en `urn:ai-eng:receipt:2`.
- Postura blueprint §10: **se enmienda el texto** para que diga "no construimos un sistema de
  observabilidad (ni servicio, ni dashboard, ni dependencias de runtime); sí agregamos señal
  dentro del gc que ya existe". La enmienda del renglón es entregable del contrato, no una
  navegación silenciosa.
- Señal de muerte pre-comprometida (estilo §10.2): **90 días sin repeats y sin desviaciones → la
  capa se retira.** Vive escrita en el spec.
- Retención del ledger R2: **acotado + caduco**, podado en el gc que ya corre. Entradas con
  `last_seen` > 90 días fuera; techo fijo de 500 entradas por recencia. Es un ledger de
  campana, no un archivo forense.
- Umbral del WARN de desviación: **fijo 3x sobre la media previa, sin knob** en config.toml.
  Subirlo a config solo si alguien lo pide con datos en la mano.
- Sin nuevas piezas que frenen: nada de los rejections del research 001 §05 entra (SDK OTel,
  monitor LLM, verbo `ai-eng observe`). Doctor sigue siendo la única superficie de lectura.
- El ceiling de 50 ms del chain no se toca: todo cómputo agregado va en el pase gc; en el hot
  path solo escrituras pequeñas fuera del veredicto.
- Cambios que anotan pero nunca cambian un veredicto (R2) son seguros por diseño frente al
  self-protect.
- KISS / YAGNI / DRY / SOLID / Clean Code como criterio duro (orden explícito del humano): nada
  de knobs, abstracciones o archivos "por si acaso". Cada pieza se justifica por una de las dos
  señales de éxito o se cae.

## Decisions still open

(ninguna; todas cerradas arriba y en Design)

## Constraints and guardrails

- Cero dependencias de runtime (pin de diseño).
- Receipts gitignored: el trail es machine-local por ahora.
- Los archivos que la cadena escribe deben sobrevivir a su propio gc y al de doctor.
- Un JSON suelto en el directorio de receipts NO es inocuo: `summarizeReceipts` lo contaría como
  receipt (`src/receipts.ts:65-69` solo exceptúa `summary.json`) y `gcReceipts` lo borraría por
  mtime (`doctor.ts:427-431`). Cualquier archivo nuevo de este contrato necesita explícitamente
  las dos exclusiones.

## Out of scope

- R3 (shim OTLP / alias de schema OTel): fuera hasta que alguien envíe receipts a un dashboard real.
- Los tres rejections del research 001 §05: SDK de OTel como dependencia, monitor LLM de
  alineación en hot path, verbo nuevo `ai-eng observe` / dashboard / servidor de métricas.
- Ningún umbral configurable nuevo en config.toml.
- Cambios a los guards existentes (veredictos), al loop por sesión, o al ceiling de 50 ms.
- Compartir receipts entre máquinas o gente (el trail sigue machine-local y gitignored).
- Tablas confusables / detección Unicode de homoglifos.

## Open questions for research

(ninguna; el research 001 ya cerró el lado externo y sus números fueron verificados contra el árbol)

## Handoff notes

- El diseño aprobado (arriba) va a `/ai-plan`: las dos señales de éxito son los checks del
  contrato; la enmienda del blueprint §10 y la señal de muerte de 90 días son entregables
  escritos.
- Archivos tocados previstos: `src/receipts.ts` (summary enriquecido), `src/commands/doctor.ts`
  (check 7 + gcReceipts), `src/chain/mod.ts` (denyOutcome: threading de tool + cláusula de
  repeat + ledger write).
- Tests: `bun test`; el scope de mutación `stryker.conf.mjs:17` cubre `src/guards/**`; R1/R2
  necesitan tests que maten mutantes (el repeat clause, el poda del ledger, el skip del nuevo
  archivo en summarize/gc), no que pasen.
- Trampa conocida a cubrir en el plan: la corrida de gc con receipts viejos debe dejar
  `denies.json` viva y podada, no borrada.
