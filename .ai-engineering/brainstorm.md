# Handshake · mutation testing en ai-engineering

Status: completo · pendiente de tu revisión · 2026-09-15
Clasificación declarada: **architectural** (tier de CI nuevo, toolchain nuevo, contrato de merge
que cambia, informe que otros leen). Si el usuario la corrige, se corrige aquí.
Ubicación: este documento es el slot `.ai-engineering/brainstorm.md`, uno de los cuatro
artefactos del hito: la sesión lo escribe, `spec close` lo barre y `doctor` avisa si sobrevive
sin contrato vivo.

## La idea en palabras simples

Quieres una prueba que revise si los tests existentes sirven de algo. La máquina coge el código
de los guards y le hace una trampa pequeña a propósito: cambia un `>=` por un `>`, borra un
nombre de una lista de comandos prohibidos, pone `true` donde había `false`. Después corre los
tests. Si los tests se dan cuenta y se ponen rojos, ese test vale. Si se quedan verdes con el
código saboteado, hay un agujero que nadie sabía que existía. Eso es mutación.

Lo que se quiere: que corra de noche, solo sobre el código que decide si una orden peligrosa se
bloquea, que no alargue la CI de cada push, y que si alguien deja un guard sin cubrir el PR no
pase.

## Por qué importa

Un guard que nadie prueba es un guard apagado, y ese es el fallo que este repositorio existe
para rechazar. La suite actual mide que el comportamiento sea correcto; no mide si los tests
que escribimos serían capaces de notar que un guard cambió. La mutación es la única medida
que responde a esa pregunta.

## Hechos verificados hoy (medidos, no supuestos)

- Suite completa: `bun test` = 449 tests, 31 ficheros, 33,13 s de pared. Medido hoy en el M1 Pro
  de este workstation. Al cerrar este documento la suite son 454 tests, por los cinco que se
  añadieron al guard de self-protect; el núcleo mutado no cambió.
- `src/` = 6.269 LOC de TypeScript. Reparto: `commands/` 1.931, `guards/` 647, `chain/` 561,
  `surfaces/` 560, `spec/` 426, `floor/` 385, `wrap/` 243, el resto en ficheros de raíz.
- `tests/` = 8.546 LOC.
- Hoy NO existe Stryker: sin `stryker.conf.*`, sin `tests/mutation/`, sin dependencia en
  `package.json` y sin ningún workflow con `schedule:`.
- `.github/workflows/check.yml:100-102` dice, textual: el job `guards-adversarial` **no** es
  mutation testing, "generating mutants is its own milestone (§17.1)".
- `docs/blueprint.html` §17.1 ya diseña el tier: StrykerJS + TypeScript checker, scope
  incremental sobre ficheros cambiados desde la última corrida verde, nightly con cap de
  10 min, caché de mutantes keyeada por sha256 del original, y la regla de PR "ningún mutante
  **nuevo** superviviente en los ficheros que toqué". El propio §17.1 declara "no corre hoy".
- `DECISIONS.md` D-016 registra que `docs/recap.html` se escribió contra el árbol porque el plan
  prometía un "mutation-testing job" que ningún fichero implementaba. Ese es el precedente a no
  repetir: el contrato se escribe contra lo que corre, no contra lo que se diseñó.
- `.ai-engineering/research/001-cicd-gate-audit.html` ya marcó la promesa de mutación como
  "falso" y propuso como criterio reconciliar el blueprint o poner el ejecutor.

### Toolchain disponible (comprobado contra el registry hoy)

- `@hughescr/stryker-bun-runner` · Apache-2.0 · latest 1.4.0 (publicado 2026-09-15), 1.3.8
  (2026-07-17), 1.3.7 (2026-07-15). Es el único runner de Bun con cobertura por test.
  - Exige Bun ≥ 1.3.7 (aquí se pina `bun@1.4.2`, cumple) y `@stryker-mutator/core` ^9
    (el latest de core es 10.0.0 desde 2026-08-14, así que la ventana es la 9.x).
  - Corre con `--concurrency=1`: los tests se ejecutan **en serie** para poder correlacionar
    cobertura y test. Cada mutante levanta un proceso `bun test` nuevo. En el dry run hace
    eager-import de cada módulo mutado.
  - Consecuencia directa: el techo de tiempo no lo pone el número de mutantes solo, lo pone
    `mutantes × (arranque de proceso + tests que cubren ese mutante)`.
- `stryker-mutator-bun-runner` (menoncello) 0.4.0, única versión, publicada 2025-07-07: parada
  desde entonces. No es candidata.
- `bunfig.toml`: `[test] coverage = false`, `[install] exact = true`,
  `minimumReleaseAge = 604800`. Ese mínimo de 7 días es una restricción dura del repo: la 1.4.0
  de hoy no sería instalable hasta la semana que viene; la 1.3.8 sí.

## Para quién es

Para quien mantiene este repositorio. El tier mide si los tests de `ai-engineering` serían
capaces de notar que un guard dejó de denegar. No entra en lo que `ai-eng` instala en los
proyectos cliente: nada de `templates/ci.yml.tpl`, ni `planEntries`, ni canon, ni `doctor`.
Decidido en la entrevista del 2026-09-15.

## Qué existe hoy

Ver "Hechos verificados hoy". No hay tier de mutación ejecutándose, ni ejecutor, ni caché.

## Decisiones ya tomadas (el planner no las reabre)

- El tier de mutación **no** corre en cada push. La mutación es nightly o a demanda, nunca
  parte del PR rápido. (blueprint §17.1)
- Si el tier no cabe en su presupuesto, se recorta el scope; no se abandona ni se deja en el
  repo sin que nadie lo ejecute. (blueprint §17.1, la regla que lo sostiene)
- La suite adversarial (`tests/adversarial/`, 21 payloads) es el oráculo de comportamiento de
  los guards. La mutación no la reemplaza. (check.yml:100-102)

## Decisiones de la entrevista (todas cerradas)

1. ~~**Alcance del cambio**~~ **CERRADA**: solo este repositorio. No toca `templates/`, ni
   `planEntries`, ni el canon, ni `doctor`.
2. ~~**Qué se muta**~~ **CERRADA**: el núcleo de gobernanza, `src/guards/` + `src/chain/` +
   `src/floor/` = 1.593 LOC. Fuera `commands/`, `surfaces/`, `spec/` y `wrap/`.
3. ~~**Con qué**~~ **CERRADA**: `@stryker-mutator/core` 9.6.1 + `@hughescr/stryker-bun-runner`
   1.3.8, todo pineado exacto en `devDependencies`. No viajan al cliente ni al binario: `files`
   en `package.json` no incluye `node_modules`, así que el radio de daño es CI y máquinas de
   maintainers. El `@stryker-mutator/typescript-checker` que §17.1 pide **no entra**: ver
   "Fuera de alcance".
4. ~~**Cuándo corre**~~ **CERRADA**: nightly por `schedule` más `workflow_dispatch`, y un job de
   PR condicionado por paths (`src/guards`, `src/chain`, `src/floor`), con el mismo patrón que
   ya usa `guards-adversarial` en `check.yml:104-113`. La mutación nunca entra en cada push.
5. ~~**Qué hacemos con los mutantes estáticos**~~ **CERRADA**: se ignoran (`ignoreStatic: true`).
   Son 223 de 1.927 (12%) y Stryker calcula que se llevan el 81% del tiempo, porque no se pueden
   atribuir a un test y obligan a correr la suite entera para cada uno. Se dejan fuera.
   - **Coste aceptado, escrito para que no se olvide**: los estáticos son el código de módulo,
     es decir `WRITERS`, `REDIRECT`, `SEPARATORS` y `RELATIVE_PATH` en `src/guards/self-protect.ts`,
     más las tablas de guards del chain. Mutar una denylist es el caso más valioso que existe
     aquí: "borrar `rm` de la lista de verbos que escriben" es exactamente el bug que este
     repositorio existe para no tener.
   - **Por qué es una decisión defendible y no un recorte a ciegas**: las denylists no se quedan
     sin oráculo. Los 21 payloads de `tests/adversarial/` son el oráculo de comportamiento de
     los guards (check.yml:100-102 lo dice), y un guard que deja de denegar `rm -rf .git/hooks`
     pone ese suite en rojo hoy mismo. Lo que aporta la mutación es cubrir lo que el oráculo no
     cubre, y eso vive en el código con lógica, no en las constantes.
   - Si algún día se quiere cerrar ese hueco sin pagar un arranque de suite por mutante, la
     palanca está en recortar el conjunto de tests de la campaña. El plan lo mediría antes.
6. ~~**Qué pasa al pasarse**~~ **CERRADA**: el gate es `thresholds.break` con el score medido,
   más un `timeout-minutes` en el job como techo duro. Si el techo salta, el job es rojo sin
   informe: eso también es la señal de que hay que recortar el scope, que es lo que §17.1 manda.
7. ~~**Gate de PR**~~ **CERRADA**: **bloquea el merge**. Un PR que toca la gobernanza y baja el
   score no pasa. La tensión que §17.1 dejaba abierta se resuelve así: el job de PR existe, pero
   condicionado por paths, así que la mutación sigue sin entrar en el push rápido.
8. ~~**Dónde vive la caché**~~ **CERRADA**: la caché incremental de Stryker, en `actions/cache`
   con `restore-keys` por prefijo. **Medida**: fría 7:27, caliente 35 s (1.703 de 1.927
   resultados reutilizados), y **34 s con un fichero tocado**, que es el caso del PR.
9. ~~**Quién lee el resultado**~~ **CERRADA**: nadie desde `ai-eng`. El informe se sube como
   artefacto de Actions y el color del job es la señal. No hay receipt y `doctor` no lo mira:
   esto es un gate de CI, no una superficie de gobernanza.

## Qué cuenta como éxito

- Existe `.github/workflows/mutation.yml`: un job nocturno por `schedule` más `workflow_dispatch`,
  y un job de PR que solo se dispara cuando el diff toca `src/guards`, `src/chain` o `src/floor`.
- La campaña sobre el núcleo termina dentro de su presupuesto, y ese presupuesto es un número
  medido, no una estimación.
- Un PR que toca la gobernanza y deja un guard sin cubrir se pone rojo, y el informe nombra los
  mutantes supervivientes uno por uno.
- `bun test` / el job `check` de cada push no cambia de duración: 33 s de suite hoy, 33 s después.
- `docs/blueprint.html` §17.1 y `docs/recap.html` dejan de describir un tier que no existe, o
  describen el que existe. D-016 no permite que un claim mienta sobre el árbol.

## Restricciones y barandillas

- Sin secretos, sin rutas absolutas de máquina, sin `|| true` que convierta un fallo en verde.
- Todo pinneado: el repo instala con `exact = true` y no adopta nada publicado hace menos de
  7 días. Esa regla hoy deja fuera la 1.4.0 del plugin y obliga a la 1.3.8.
- Un check que no puede correr es un FAIL, nunca silencio (blueprint §09.3).
- El job de PR no puede pagar la campaña entera en cada push, y por eso corre condicionado por
  paths y sobre la caché incremental. Nunca en un PR que no toque `src/guards`, `src/chain` o
  `src/floor`.
- Nada de `--no-verify`, nada de silenciar un linter.
- Los mutantes pueden hacer que el propio guard del repo deniegue dentro de sus propios tests
  (medido: un run hijo salió con `exit=2` y el `[ai-eng] no-verify:` por stderr). Es ruido
  esperado de mutar un repositorio que se gobierna a sí mismo, no un fallo del tier.

## Fuera de alcance

- **El tier como producto.** No entra en `templates/ci.yml.tpl`, ni en `planEntries`, ni en el
  canon, ni en `doctor`.
- **Mutar `commands/`, `surfaces/`, `spec/` ni `wrap/`.** Decidido en la entrevista.
- **El TypeScript checker que pide §17.1.** No puede entrar mientras el repo instale
  `typescript@7`, porque las APIs que usa (`parseConfigFileTextToJson`,
  `createEmitAndSemanticDiagnosticsBuilderProgram`, `sys`, `formatDiagnostics`) no existen en
  esa versión, aunque su peer diga `>=3.6`. Entra el día que se resuelva la versión de
  TypeScript, y con él la reducción de mutantes que §17.1 le atribuye.
- **Ficheros de baseline y scripts que comparen informes.** El gate es `thresholds.break`, una
  línea de configuración.
- **Receipts y `doctor`.** El tier es un gate de CI, no una superficie de gobernanza.

## Preguntas abiertas para research

1. ~~¿`ignorePatterns` deja un fichero de test fuera del sandbox sin romper el descubrimiento
   automático?~~ **RESPONDIDA**: sí, y verificado. `ignorePatterns:
   ["tests/generated-payload.test.ts"]` con descubrimiento automático intacto pasa el dry run
   en 34 s. La lista blanca de `bun.testFiles` que usó el spike queda descartada: 29 ficheros
   mantenidos a mano se pudren en silencio y un test nuevo quedaría fuera sin que nadie lo note.
2. ~~¿Cuál es el score real del núcleo?~~ **RESPONDIDA**: 59,21% (65,73% contando cobertura),
   1.007 muertos, 526 supervivientes, 169 sin cobertura, 2 timeouts, 0 errores. Reproducida al
   byte en dos corridas limpias. Con caché incremental el mismo árbol da 58,51%.
3. **¿Cuánto tarda de verdad en un runner de CI?** Los 8,2 minutos medidos aquí son de un M1 Pro;
   en `ubuntu-latest` hay que esperar más, y el rango 12-20 minutos es una extrapolación, no una
   medida. Importa porque decide si el cap de §17.1 se reescribe o el scope se recorta. Se
   responde con la primera corrida real del job, y ese número es el que fija `thresholds.break`.

## Lo que el tier ya encontró antes de existir

La primera campaña limpia es, en sí misma, el primer informe del tier, y dice algo incómodo:

- `guards/self-protect.ts`: **46,84%**, 125 supervivientes de 251.
- `guards/no-verify.ts`: **34,78%**, 77 de 125.
- `chain/mod.ts`: **34,59%**, 106 de 261.
- `guards/` entero: 49,62%. `chain/` entero: 54,49%. `floor/`: 75,51%.

La suite adversarial mata aproximadamente la mitad de los mutantes de los guards. El código que
decide si una orden peligrosa se bloquea está medio cubierto, y ningún tier lo estaba diciendo.
Esto no es un defecto del tier: es el tier funcionando, y es la razón por la que merece existir.

## Diseño

### Forma: un tier fuera del camino crítico

Nada de esto toca `src/`. El PR rápido de `check.yml` no cambia ni un segundo.

```
package.json                     2 devDeps pineadas exactas + script "mutation"
stryker.conf.mjs                 config única, nueva, en la raíz
.github/workflows/mutation.yml   job nocturno + job de PR condicionado por paths
CHANGELOG.md + .changeset/       el repo publica con changesets
docs/blueprint.html §17.1        reconciliar: hoy describe un tier que no existe
docs/recap.html                  lo mismo
```

### La config, entera, para que no haya que redescubrirla

```js
// stryker.conf.mjs — cada ajuste raro tiene su razón medida, y esta es la config real.
export default {
  // El plugin NO está en el scope @stryker-mutator/*, así que el glob por defecto de
  // Stryker nunca lo encuentra. Su README omite esta línea.
  plugins: ["@hughescr/stryker-bun-runner"],
  testRunner: "bun",
  coverageAnalysis: "perTest",
  mutate: ["src/guards/**/*.ts", "src/chain/**/*.ts", "src/floor/**/*.ts"],
  concurrency: 4,
  // 223 de 1.927 mutantes son estáticos y se llevan el 81% del tiempo. Fuera.
  ignoreStatic: true,
  inPlace: false,
  // El default es `true` y expande a **/*.{js,ts,jsx,tsx,html,vue,mjs,mts,cts,cjs} sobre
  // TODO el proyecto (core: config/file-matcher.js:14): reescribía skills/**/*.ts dentro
  // del sandbox y rompía el test de las copias .embed. `bun test` nunca comprueba tipos.
  disableTypeChecks: false,
  // TSConfigPreprocessor llama ts.parseConfigFileTextToJson, que TS 7 eliminó. Su único
  // consumidor es sandbox/ts-config-preprocessor.js:36, con guarda en :42, así que una
  // ruta que no es un fichero del proyecto lo salta.
  tsconfigFile: ".stryker/absent.json",
  // Este fichero reconstruye el bundle con `bun build` y compara bytes: dentro del sandbox
  // src/ está instrumentado y no puede coincidir jamás. No importa src/, así que tampoco
  // puede matar un mutante. Fuera por patrón, con descubrimiento automático intacto.
  ignorePatterns: ["tests/generated-payload.test.ts"],
  // La caché que hace barato el job de PR: 35 s en caliente, 34 s con un fichero tocado.
  incremental: true,
  incrementalFile: "reports/stryker-incremental.json",
  reporters: ["clear-text", "json"],
  jsonReporter: { fileName: "reports/mutation.json" },
  thresholds: { high: 80, low: 60, break: VER_MAS_ABAJO },
  tempDirName: ".stryker-tmp",
  bun: { timeout: 30000 },
};
```

### El gate, sin fichero de baseline

`thresholds: { break: <el score medido> }`. Una línea de configuración, no un script que
compare informes ni un fichero de línea base que alguien tenga que regenerar.

**Ojo con de dónde sale el número**, porque hay dos y no coinciden: una corrida limpia sin
caché dio **59,21%**, y la corrida con `incremental: true` (la que correrá en CI) dio
**58,51%**. Doce mutantes cambian de estado entre los dos modos. El número tiene que salir de
una corrida con la misma config que va a usar CI, y el más fiable es el de la primera corrida
real del job: fijarlo desde aquí sería congelar una medida de otra máquina.

Por qué un número basta: un superviviente nuevo baja el score. El informe `clear-text` nombra
los supervivientes, así que el rojo dice exactamente qué falta. El día que alguien suba el
score, sube el número; nunca hace falta bajarlo.

Límite honesto, escrito para que no sorprenda a nadie: el gate detecta **bajadas**. No impide
que los 526 supervivientes de hoy sigan ahí, y eso es exactamente lo que §17.1 pide ("ningún
mutante nuevo superviviente") y no otra cosa.

### El job de PR

Se dispara solo cuando el diff toca `src/guards`, `src/chain` o `src/floor`, con el mismo
patrón por paths que ya usa `guards-adversarial` en `check.yml:104-113`. Corre la campaña
completa y no solo los ficheros cambiados, porque el umbral de score es global: correr un
subconjunto haría que `self-protect.ts`, que está en el 46,84%, fallara el umbral por ser él
mismo. Lo que lo hace barato no es recortar el scope, es la caché: 34 s con un fichero tocado.

### Presupuesto: lo que cuesta y lo que se puede recortar

Medido en este portátil, `concurrency: 4`, `ignoreStatic: true`:

| | dry run | campaña | total | score | muertos |
|---|---|---|---|---|---|
| suite auto-descubierta (29 ficheros) | 38 s | 7:31 | **8,2 min** | 59,21% | 1.007 |
| 8 ficheros elegidos a mano | 11 s | 1:51 | **2,0 min** | 54,05% | 919 |
| la misma campaña con caché caliente | 34 s | 35 s | **~1,2 min** | 58,51% | 995 |

El recorte a mano es cuatro veces más rápido y por eso tienta, pero pierde **88 mutantes que la
suite completa sí mata** y deja 130 más sin cobertura. Y la lista que lo consigue hay que
mantenerla a mano: un test nuevo en `tests/` quedaría fuera de la campaña sin que nadie lo note,
que es exactamente el modo de fallo que este repositorio rechaza en todas partes.

Recomendación: **suite completa**. El tier corre de noche, nadie está esperando, y perder el 9%
de las muertes para ahorrar seis minutos es el cambio equivocado. El recorte queda documentado
como la palanca que existe si algún día el tier no cabe.

En un runner de CI, más lento por núcleo que este portátil, los 8,2 minutos se van
previsiblemente a 12-20. Eso deja el cap de 10 minutos de §17.1 fuera de alcance tal cual, y hay
que decirlo en la documentación en vez de fingir que cabe.

### Riesgo conocido: el dry run puede fallar de forma espuria

Observado **una vez en siete** dry runs con la configuración final: Stryker reportó como fallido
`tests/adversarial/chain.test.ts > adversarial · no-verify > control · ordinary commit passes`,
un test que pasa solo (`bun test tests/adversarial/chain.test.ts` → 45 pass, 0 fail) y que pasó
en los tres intentos de reproducción consecutivos con la máquina libre.

La corrida que falló coincidió con carga alta en la máquina. El README del plugin documenta
exactamente ese modo: truncado del stream del inspector bajo contención de CPU, y recomienda
reintentar con menos carga o menos workers.

Por qué importa: un dry run que falla espuriamente pone el PR en rojo sin motivo, y un gate que
a veces miente es un gate que la gente aprende a saltar. El plan debe medir la tasa de fallo en
CI antes de confiar en él como puerta de merge; si aparece, bajar `concurrency` es la palanca
documentada.

### Manejo de errores

- Nada de `|| true`. Un check que no corre es rojo, nunca silencio.
- `timeout-minutes` en el job como techo duro, aparte del presupuesto esperado.
- El dry run es la puerta: si un test falla dentro del sandbox instrumentado, Stryker aborta sin
  escribir informe y el job es rojo con el nombre del test. Ese modo de fallo se comió tres
  intentos del spike, así que queda documentado en la propia config.
- Un mutante puede hacer que el guard del propio repositorio deniegue dentro de sus propios
  tests. Es ruido esperado de mutar un repositorio que se gobierna a sí mismo, no un fallo.

### Verificación antes de mergear

- El tier no lleva tests unitarios propios: su verificación es que corra y escriba el informe.
- Lo que sí hay que comprobar: que `bun test` siga verde y en 33 s, que `check.yml` no cambie de
  duración, y que una campaña con la misma config reproduzca el score del que salió el
  `break` (59,21 sin caché, 58,51 con ella).

## Notas de handoff

- Salida de este brainstorm: este fichero, `.ai-engineering/brainstorm.md`. Muere en la
  aprobación del contrato, cuando `/ai-plan` lo convierta en el contrato y el plan, y
  `spec close` lo barra del árbol.
- Orden sugerido para el plan:
  1. Las 2 devDependencies pineadas exactas y el script `mutation` en `package.json`.
  2. `stryker.conf.mjs` con los cinco ajustes que el spike demostró obligatorios (`plugins`,
     `ignoreStatic`, `disableTypeChecks: false`, `tsconfigFile` ausente, `ignorePatterns`) y la
     caché incremental. El `break` se fija con el número de la primera corrida real del job.
  3. `.github/workflows/mutation.yml`: job nocturno con `schedule` + `workflow_dispatch`, job de
     PR por paths, `actions/cache` con `restore-keys`, el informe como artefacto.
  4. Reconciliar `docs/blueprint.html` §17.1 y `docs/recap.html`, más CHANGELOG y changeset.
- Ficheros que el plan toca: `package.json`, `stryker.conf.mjs` (nuevo),
  `.github/workflows/mutation.yml` (nuevo), `CHANGELOG.md` + `.changeset/`,
  `docs/blueprint.html`, `docs/recap.html`. Nada en `src/`.
- El spike ya está borrado: era un `git worktree` en `/tmp/ai-eng-mutation-spike` y dejó de
  existir al cerrar este documento. Lo que sobrevive de él es la config de arriba y los números
  medidos aquí, así que no hace falta reconstruirlo.
- Si alguien vuelve a medir, dos reglas aprendidas a golpes: **nunca dos campañas en el mismo
  directorio** (la segunda cuenta como muertos los procesos que la primera rompió), y
  **el dry run puede fallar de forma espuria bajo carga**, así que una medida se repite antes
  de creerla.

## Spike de medición (completado, 2026-09-15)

Corrió en `/tmp/ai-eng-mutation-spike`, un worktree aislado ya borrado. M1 Pro de 8 núcleos,
`concurrency: 4` para parecerse a un runner de CI.

**Punto ciego del worktree, para no comparar mal**: estaba en `HEAD`, así que no incluía los
ficheros sin commitear del árbol de trabajo (`tests/security-findings.spec.ts`, 5 tests, más
cambios en las skills de seguridad). De ahí que el dry run diga 442 tests y no 449. Los números
de mutantes y de tiempo corresponden al núcleo de gobernanza, que esos ficheros no tocan, así
que no cambian; el recuento de tests sí.

Medido:

- 11 ficheros instrumentados de `guards/` + `chain/` + `floor/` → **1.927 mutantes**, de los que
  223 son estáticos y 1.704 dinámicos. La estimación optimista de 400-700 era corta por un
  factor de tres.
- Dry run (la suite entera menos un fichero): **442 tests en 38 s**.
- Campaña con `ignoreStatic: true`, `concurrency: 4`, en un M1 Pro de 8 núcleos:
  **7 minutos 53 segundos**. Reproducido en una segunda corrida sin contaminar (7:34). Total del
  tier: **~8,5 minutos**. En un runner de CI, que por núcleo es más lento que este portátil,
  hay que esperar bastante más: el cap de 10 minutos de §17.1 no se sostiene tal cual.

### Resultado de la primera corrida (el baseline del gate)

| | score | supervivientes |
|---|---|---|
| **Todo el núcleo** | **59,21%** (65,73% contando cobertura) | **526** |
| `guards/` | 49,62% | 258 |
| `guards/self-protect.ts` | 46,84% | 125 de 251 |
| `guards/no-verify.ts` | 34,78% | 77 de 125 |
| `chain/` | 54,49% | 157 |
| `chain/mod.ts` | 34,59% | 106 de 261 |
| `floor/` | 75,51% | 111 |

**Conclusión incómoda y valiosa**: la suite adversarial mata aproximadamente la mitad de los
mutantes de los guards. `self-protect.ts` y `no-verify.ts`, que son el corazón del gobierno de
este repositorio, están en el 46,84% y el 34,78%. Eso es exactamente lo que la mutación existe
para decir, y ningún otro tier lo estaba diciendo.

### Una medición que salió mal, y por qué se cuenta

La primera corrida que terminó dio 86,44% y 1 minuto 21 segundos. Era **basura**: otra corrida
arrancó encima y un `rm -rf .stryker-tmp` destruyó su sandbox en vuelo, así que Stryker contó
como muertos 1.472 mutantes que en realidad eran procesos rotos (1,87 tests por mutante frente a
los 6,48 reales). Se detecta porque el número de tests por mutante no cuadra con el
planificador. La corrida limpia, repetida dos veces, da 6,48 y 6,52 tests por mutante y 7:53 y
7:34 de duración. **Nunca medir el tier con dos campañas compitiendo en el mismo directorio.**

### Cuatro bloqueos reales, ninguno documentado por el plugin

1. **El plugin no se autodescubre.** Stryker resuelve plugins desde el glob
   `@stryker-mutator/*`, y `@hughescr/stryker-bun-runner` no está en ese scope. Sin
   `plugins: ["@hughescr/stryker-bun-runner"]` el `bun: {...}` del README es "unknown config
   option" y el runner no existe. El README no lo menciona.

2. **Stryker no arranca con `typescript@7`.** `TSConfigPreprocessor` llama
   `ts.parseConfigFileTextToJson` (`core/dist/src/sandbox/ts-config-preprocessor.js:46`), y TS
   7.0.2 no expone **ninguna** API del compilador: `parseConfigFileTextToJson`, `createProgram`,
   `sys`, `formatDiagnostics` y `createWatchProgram` son todas `undefined`. El repo declara
   `"typescript": "latest"`, que hoy resuelve a 7.0.2. Subir a Stryker 10.0.0 no arregla nada:
   hace la misma llamada (`ts-config-preprocessor.js:46` en la 10 también).
   - El único consumidor de la opción `tsconfigFile` es ese preprocesador (`:36`), y tiene
     guarda `if (tsconfigFile)` (`:42`). Apuntarla a un fichero que no existe en el proyecto lo
     salta sin consecuencias para el resto.
   - **Consecuencia mayor**: `@stryker-mutator/typescript-checker` usa las mismas APIs y declara
     peer `typescript: >=3.6`. Ese peer miente para 7.x: **el checker que pide §17.1 no puede
     correr en este repo tal y como está**, y con él se va la reducción de mutantes que §17.1 le
     atribuye.

3. **`disableTypeChecks` por defecto reescribe el proyecto entero.** Su default es `true`, que
   expande a `**/*.{js,ts,jsx,tsx,html,vue,mjs,mts,cts,cjs}` sobre todos los ficheros del
   proyecto (`core/dist/src/config/file-matcher.js:14`). En el sandbox eso tocó
   `skills/**/*.ts`, y el test de `tests/generated-payload.test.ts` que compara las copias
   `.embed` byte a byte falló. `disableTypeChecks: false` lo evita, y aquí es seguro porque
   `bun test` nunca comprueba tipos.
   - Acotarlo a `{src/guards,src/chain,src/floor}/**/*.ts` **no** sirve: `scripts/chain-entry.ts`
     empaqueta `src/chain/**`, así que quitarle los tipos a esos ficheros cambia el bundle.

4. **La instrumentación es incompatible con un test de este repositorio.**
   `tests/generated-payload.test.ts` reconstruye el bundle con `bun build scripts/chain-entry.ts`
   y lo compara byte a byte con el commiteado. Dentro del sandbox, `src/chain/mod.ts` pasa de
   291 a 552 líneas por los `stryNS_*` / `stryCov_*` que inyecta el instrumenter, así que el
   bundle reconstruido no puede coincidir jamás. No es un ajuste que falte: la instrumentación
   es el mecanismo de Stryker.
   - Excluir ese fichero de la corrida es la salida, y es segura: no importa `src/` en absoluto
     (solo `bun:test`, `node:child_process` y `node:fs`), así que no puede matar un mutante.
   - La primera versión de esta exclusión fue una lista blanca de 29 ficheros con
     `bun.testFiles`, y era la parte fea del diseño: se pudre en silencio. La sustituye
     `ignorePatterns`, verificado con el descubrimiento automático intacto.
   - Ojo con `inPlace: true` como atajo: no salta el problema (el test mide también dentro del
     árbol real), y además deja el árbol de trabajo instrumentado durante la corrida.

---

# MAP — tier de mutación

Escrito por `ai-plan` el 2026-09-15, sobre este handshake y la review de arquitectura de la misma
fecha. El mapa vive aquí y no en `.wayfinder/`: un mapa fuera del slot no lo barre `spec close`,
no lo audita `doctor` y nada lo protege.

## Destination

El núcleo de gobernanza tiene un gate de mutación que corre de verdad — de noche y en el PR que lo
toca — y su rojo significa exactamente lo que dice el contrato: nombra los supervivientes y no
puede ponerse verde por un job que se saltó, una caché rancia o un número mal puesto.

## Open questions

<!-- Vacía: las ocho preguntas están resueltas en `## Answers`. La niebla que queda no es pregunta
     todavía. -->

## Not yet specified

<!-- Niebla: dentro del destino, pero todavía no se puede formular como pregunta. -->

- El texto exacto de §17.1 después de la reconciliación: depende del número medido en CI, que aún
  no existe. Se escribe con el número, no antes.
- Qué se hace con los 526 supervivientes de hoy, más allá de nombrarlos en el informe: el tier los
  mide, pero nadie ha decidido si este milestone también decide cuáles se atacan primero.
- Si hace falta un modo de ejecución congelado (sin caché / con caché) para que el número del
  nightly y el del PR sean comparables. La investigación dice que la caché no altera el veredicto
  (no cambia qué mutantes mueren, solo cuáles se reejecutan), así que probablemente no — pero no
  está medido en CI.

## Out of scope

<!-- Añadir cualquiera de estas empeora el resultado. Un revisor no debe premiarlas. -->

1. **El tier como producto** — `templates/ci.yml.tpl`, `planEntries`, el canon, `doctor`. Lo que se
   compra aquí es la salud de este repositorio, no una superficie que `ai-eng` planta.
2. **Mutar `commands/`, `surfaces/`, `spec/` ni `wrap/`** — decidido en la entrevista del
   2026-09-15; fuera del núcleo de gobernanza.
3. **El `typescript-checker` de §17.1** — no puede correr mientras este repo instale
   `typescript@7`; entra el día que se resuelva esa versión, con su milestone.
4. **Ficheros de baseline y scripts que comparen informes** — la respuesta 1 elige el umbral, que
   no necesita baseline. Un comparador de informes sería una segunda fuente de verdad.
5. **Receipts y `doctor`** — el tier es un gate de CI, no una superficie de gobernanza.
6. **Un badge de mutación en el README o un dashboard público** — convertiría el score en un claim
   de marketing y le daría al repo una razón para subir el número en vez de bajar los
   supervivientes. D-016, en la dirección contraria.

## Answers

### 1 · ¿Qué significa el rojo del job de PR?

**Answer:** El score del núcleo no puede bajar. Se implementa con una línea de configuración
(`thresholds.break`) y §17.1 se reescribe a esa frase: el umbral es un score mínimo, no un
comparador de supervivientes.

**Why:** Es el mecanismo que ya está en la config y no necesita ni artefacto de baseline ni script
de comparación. La regla literal de §17.1 ("ningún mutante nuevo superviviente") exige guardar el
informe de la corrida verde anterior y compararlo, con el coste de un baseline que puede envejecer
o no existir en la primera corrida. Hueco aceptado y escrito: un PR que añade código matado por
encima de la media puede sumar supervivientes y seguir verde, porque el score es una razón, no un
conjunto.

**Check:** Con el umbral por encima del score medido, el job sale con código ≠ 0.
**Judged by:** run it
**Reference:** —

**Check:** Con el umbral por debajo del score medido, la misma campaña sale con código 0.
**Judged by:** run it
**Reference:** —

### 2 · ¿El 85% es el `break` del gate o el objetivo declarado?

**Answer:** `break = 85` desde ya. Bandas coherentes en la misma config: `high: 90`, `low: 85`,
`break: 85`.

**Why:** Decisión explícita del usuario, tomada con el coste sobre la mesa: el score medido del
núcleo es 59,21% (1.007 matados de 1.704), así que el gate nace rojo y lo estará en cada PR que
toque `src/guards`, `src/chain` o `src/floor`, y en cada nightly, hasta que el núcleo llegue a 85.
Es un trinquete deliberado: la luz roja es el forcing function, no un fallo del tier. Dos
consecuencias que la implementación debe respetar: (a) §17.1 tiene que decir "rojo esperado hasta
el 85", o el próximo lector creerá que el gate está roto; (b) el camino para subir el score no pasa
por el gate — un PR que solo toca `tests/` no dispara el job, porque el filtro es por paths de
`src/`, así que matar supervivientes se hace escribiendo tests, no editando guards.

**Check:** El job es rojo con el score medido de hoy (por debajo de 85) y su informe nombra los
supervivientes uno por uno.
**Judged by:** run it
**Reference:** —

**Check:** El job es verde, sin tocar la campaña, cuando el umbral se baja por debajo del score
que el informe ya tiene.
**Judged by:** run it
**Reference:** —

### 3 · ¿El milestone arregla también `guards-adversarial`?

**Answer:** Sí, en el mismo PR. El diff por paths se arregla una vez y sirve a los dos jobs: el
nuevo y el que hoy no corre.

**Why:** El patrón que el plan copia es un no-op medido, no una sospecha: en 9 de 9 corridas de PR
el job imprimió `fatal: bad revision 'origin/main...HEAD'` y cayó al `else` con
`governance untouched — oracle skipped` (`.github/workflows/check.yml:116-117`). El checkout no
fija `fetch-depth`, y la profundidad 1 no deja `origin/main` como ref. Los otros dos jobs que
necesitan historia sí lo fijan (`check.yml:72`, `:148`). Arreglar solo el job nuevo deja dos
verdades para el mismo mecanismo y deja el oráculo adversarial — el contrato de comportamiento de
los guards — sin ejecutarse en ningún PR.

**Check:** En un PR que toca `src/guards/`, el log del job `guards-adversarial` contiene una línea
`… pass, 0 fail` de `bun test tests/adversarial/` y **no** contiene la cadena `oracle skipped`; y
un PR que no toca esos paths sigue imprimiendo `oracle skipped`.
**Judged by:** run it
**Reference:** —

### 4 · ¿Con qué concurrencia arranca el gate?

**Answer:** `concurrency: 2`, una sola config para el nightly y el PR.

**Why:** El spike midió 4 workers en un M1 Pro de 8 núcleos; el runner es `ubuntu-latest` con
4 vCPU y 16 GB (docs de GitHub, observadas hoy). El README del plugin documenta el truncado del
stream del inspector precisamente bajo contención de CPU, que es el modo de fallo que ya se
observó aquí (1 dry run espurio de 7). Los minutos son gratis e ilimitados en repo público, así
que bajar la concurrencia solo cuesta tiempo de reloj.

**Check:** La campaña del job termina y escribe `reports/mutation.json`, y su log no contiene la
cadena `dry run data-completeness check failed`.
**Judged by:** run it
**Reference:** —

### 5 · ¿El cap de 10 minutos de §17.1?

**Answer:** §17.1 se reescribe con el número medido en la primera corrida real del job, y ese mismo
número pasa a ser el `timeout-minutes` del job. El techo duro es el timeout, no una estimación.

**Why:** 8,2 minutos medidos en un portátil mejor que el runner no caben en 10 minutos de CI; el
propio handshake lo admite y la conclusión es que §17.1 describe hoy un tier que no existe — que
es exactamente lo que D-016 prohíbe. La edición de §17.1 la hace una persona: el guard del repo no
deja que un agente lea ese fichero (bloqueó la lectura durante la review de arquitectura).

**Check:** §17.1 nombra el número medido y el job lleva ese mismo número en `timeout-minutes`;
ninguno de los dos dice ya `10 min`.
**Judged by:** run it
**Reference:** —

### 6 · ¿El runner de Bun reporta ficheros y localizaciones de test? (research)

**Answer:** Sí. El plugin rellena `fileName` + `startPosition` en cada test del dry run ya en la
1.3.8 que se va a instalar; Stryker identifica un test por `fichero@línea:columna\nnombre` y solo
reutiliza un mutante Killed si su test matador sale `same` en el diff. Un test editado invalida el
kill cacheado de los mutantes que cubre. Sin acción extra.

**Why:** Es el tier "Full" de la tabla de Stryker, que no tiene fila de Bun y por eso había que ir
a la fuente: `src/bun-test-runner.ts:744-782` (tag 1.3.8) construye `fileName` desde
`normalizeTestFilePath(testInfo.url)` y `startPosition` desde `testInfo.line`, y los cuelga de cada
test Success/Failed/Skipped que devuelve en `{status: Complete, tests, mutantCoverage}`.
`incremental-differ.ts:591-601` compone la clave con esos dos campos y `:394-437` reutiliza solo
cuando el test matador está `same`. En `main` (1.4.0) el comportamiento es idéntico. Puntos ciegos
que quedan y son de Stryker, no del plugin: cambios en ficheros auxiliares que no son tests ni
fuentes mutadas, y el camino de fallback sin inspector.

**Check:** Con caché caliente, editar **solo** un test que mata un mutante conocido y volver a
correr hace que la corrida imprima `Tests: 1 files changed` y reejecute ese mutante (el informe lo
vuelve a atribuir a un test recién corrido), en vez de reutilizar su kill anterior.
**Judged by:** run it
**Reference:** —

### 7 · ¿Cómo se invoca Stryker en CI? (research)

**Answer:** `bunx stryker run`. El binario de `@stryker-mutator/core@9.6.1` declara
`#!/usr/bin/env node` y `bunx` respeta shebangs, así que Stryker corre bajo Node — que es lo que el
plugin exige. La imagen `ubuntu-24.04` (20260907.300.1) trae Node 22.23.2, que cumple
`engines.node >= 20`.

**Why:** El README del plugin parece contradecirse ("Stryker itself runs on Node", con ejemplo
`bunx stryker run`); la contradicción se resuelve a favor del ejemplo porque `bin.stryker` →
`bin/stryker.js` lleva shebang de node y la documentación de Bun dice que `bunx` lo respeta por
defecto. No hace falta `npx` ni instalar Node aparte.

**Check:** El step imprime `node -v` con una versión ≥ 20 y la misma corrida completa el dry run y
escribe `reports/mutation.json`.
**Judged by:** run it
**Reference:** —

### 8 · ¿Qué corre en un PR de fork?

**Answer:** Nada especial: la plataforma ya aísla la caché. Un PR —de fork o no— puede restaurar la
caché de la rama base, y lo que guarda queda en su propio merge ref, invisible para `main` y para
otros PRs. Lo único que hay que cubrir es el arranque en frío, y eso lo cubre el timeout del job.

**Why:** El aislamiento por rama que iba a construir con una clave por ref ya lo da GitHub, así que
la clave se queda en `stryker-incremental-${{ hashFiles('bun.lock') }}` con
`restore-keys: stryker-incremental-`. Las cachés son inmutables: la primera escritura de una clave
gana y las demás no fallan el job. La búsqueda por prefijo devuelve la más reciente, primero la
rama actual y luego la de por defecto.

**Check:** Una segunda corrida del mismo job sobre el mismo árbol imprime una línea
`Result: N of M mutant result(s)` con N ≥ 1; la primera sobre caché vacía imprime 0.
**Judged by:** run it
**Reference:** —
