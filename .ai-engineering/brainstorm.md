# Handshake · gobernanza global de ai-engineering

Status: draft, lectura en voz alta PASADA · diseno v1 en revision · 2026-09-14

## The idea in plain words

(borrador, sin confirmar · se fija cuando pase la lectura en voz alta)

Hoy, para que un repo quede gobernado hay que escribir de 8 a 10 archivos DENTRO del repo: un archivo de
hooks por superficie elegida, mas tres shims en `.git/hooks`. Quieres que eso viva en la maquina, escrito una
vez por superficie, y que el repo solo declare "yo estoy gobernado, y en estas superficies" en
`.ai-engineering/config.toml`. Asi `ai-eng init` deja de sembrar archivos de hook en el repo, `ai-eng update`
actualiza la maquina, `ai-eng uninstall` la limpia, y el resto del ciclo de vida (doctor, lock, receipts, spec)
sigue significando lo mismo. La pregunta que decide el diseno es si "global" quiere decir solo DONDE vive el
hook, o tambien que el hook gobierne repos que nunca ejecutaron `init`.

## Why this matters

- Hoy cada repo gobernado arrastra 8 a 10 archivos de carrier que nadie revisa y que envejecen con el repo, no
  con el binario.
- El floor de git nace ausente en cada clone (`.github/workflows/check.yml:43` existe justamente para
  reconstruirlo despues del hecho). Es el sintoma de que el carrier esta en el sitio equivocado.
- ai-eng ya tiene dos modelos mentales a la vez: el canon, los espejos y los comandos de OpenCode son de
  maquina (`src/surfaces/adapters.ts:72-107`) y un hook de Copilot CLI tambien lo es
  (`src/surfaces/adapters.ts:118-123`), mientras todo lo demas es por repo. Un solo modelo es menos que dos.
- El coste real de equivocarse esta medido: los guards deniegan en repos que nunca se gobernaron
  (`research/004 §02`: `ai-eng chain PreToolUse` deniega `git commit -n` en un repo vacio, exit 2, y tambien
  fuera de todo repo).

## Who it's for

TODO (confirmar): soydachi como autor del framework, y despues cualquiera que instale ai-eng en una maquina y
no quiera tocar siete configs por repo. Falta decidir si el usuario objetivo es tambien equipos que comparten
repos (donde el carrier por repo viaja en el clone y el de maquina no).

## What exists today

Hechos verificados en esta sesion, con la ruta abierta:

- **Lado maquina, ya existe**: `~/.ai-engineering/skills` + espejos `~/.claude/skills`, `~/.agents/skills`,
  `~/.config/opencode/skill`, mas `~/.config/opencode/commands` (`src/surfaces/adapters.ts:72-107`). Entra por
  `installCanon(version, { machineHooks })` (`src/surfaces/adapters.ts:85`), que hoy solo escribe hook de
  maquina en un caso: Copilot CLI, y solo con `--global` (`:118-123`). `init --global` es la unica ruta que
  escribe fuera del repo (`:81-85`, comentario explicito).
- **Lado repo, lo que se escribe hoy**: `planEntries()` (`src/commands/init-shared.ts:42-52`) escribe
  `.ai-engineering/overrides.toml`, `arch.rules.json`, `config.toml`, `.github/workflows/ai-eng-check.yml`,
  los tres shims de git (`gitHookEntries()`, `:31-40`) y, por superficie (`surfaceEntries()`, `:59-83`):
  `.claude/settings.json` (claude-code), `.opencode/plugins/ai-eng{,-chain}.ts`, `.agents/hooks/ai-eng{,-chain}.ts`,
  `.codex/hooks.json`, `.cursor/hooks.json`, `.github/hooks/ai-eng.json`, `.pi/extensions/ai-eng{,-chain}.ts`.
  Pi y OpenCode y OMP llevan ademas el bundle del chain embebido.
- **Quien lee esas rutas**: `doctor` chequeo 5 "git floor" (`src/commands/doctor.ts:112-122`) y chequeo 11
  "surface \<id\>: settings present" (`:200-233`), que hoy resuelve `surface.settingsFile ?? surface.pluginFile`
  contra la raiz del repo. `uninstall` scope proyecto barre lo que declara el lock (`src/commands/uninstall.ts:1-14`),
  y scope "Everything" llama `removeMachineArtifacts()` y borra `~/.ai-engineering` (`:204-211`).
- **Quien decide la politica**: `config.toml` declara las superficies, `enabledSurfaces()` las lee
  (`src/env.ts:77-90`) y, cuando no hay repo o no hay config, devuelve `["claude-code"]` por defecto.
- **`chain` no pregunta si el repo esta gobernado**: resuelve la raiz (`src/chain/mod.ts:103`, `src/env.ts:27`)
  y los guards deciden. Medido en `research/004 §02`.
- **El lock** pincha los assets del repo por sha256 mas `spec_sha256` y `skills_min` (`src/install.ts`).
- **No existe** `~/.ai-engineering/projects.json` (el blueprint §14.0a lo promete; no aparece en `src/`).
- **No existe** ningun hook `SessionStart` (blueprint §14.0a:1138 lo disena como hook de maquina; no aparece
  en `src/`).

Investigacion ya pagada, en el repo: `research/003` (promocion de Cursor, Codex y Copilot a core; el allow de
Cursor roto; Copilot CLI solo dispara a nivel usuario) y `research/004` (donde vive cada hook por superficie,
y la medicion de que los guards no estan acotados al repo).

## What success looks like

(Pendiente de tu si en la lectura en voz alta.)

1. Un repo gobernado contiene 2 archivos de carrier (Cursor y Copilot, por sus lectores de cloud) y sigue denegando
   `git commit -n`.
2. Un repo SIN `config.toml` no recibe politica de ai-eng: `ai-eng chain PreToolUse` con el payload adversarial sale
   allow, y `ai-eng git commit-msg` sale 0, aunque el carrier exista en la maquina.
3. `ai-eng doctor` distingue dos cosas que hoy mezcla: "el carrier de maquina esta y coincide con el binario" y "el
   repo esta declarado y su lock cuadra". Ningun chequeo lee rutas de hook dentro del repo salvo las dos de Cursor y
   Copilot.
4. `ai-eng uninstall` scope proyecto no toca la maquina, y scope "Everything" deja la maquina como estaba: sin hooks
   huerfanos, sin `init.templateDir` colgando, y sin haber pisado un templateDir que ya existiera.
5. Re-ejecutar `init` en un repo ya gobernado no duplica, no reinstala y no pide permiso otra vez por el carrier que
   ya esta.
6. En un repo con `cursor` declarado, una llamada permitida pasa (hoy bloquea todo): el envelope de allow sale en el
   dialecto del host.

## Decisions already made

- `init` pregunta antes de instalar el canon cuando estas dentro de un repo y la maquina no lo tiene
  (commit de ayer, `src/commands/init.ts:112-124`). Es el precedente de tono: instalar fuera del repo se pide.
- Solo `--global` escribe fuera del repo hoy (`src/surfaces/adapters.ts:81-85`). Este plan probablemente
  invierte esa regla, y hay que decirlo en voz alta cuando se invierta.
- El floor de git vive en `.git/hooks` y `core.hooksPath` se desactiva a proposito (`src/commands/init.ts:74-80`).
- Un hook de maquina debe fallar ABIERTO si el binario no esta en PATH (`tests/surfaces.test.ts:224`).
- DECIDIDO hoy: "global" significa DONDE VIVE EL CARRIER, no ampliar la politica. El hook se escribe una vez en la
  maquina por superficie, y `chain` gana una puerta explicita: repo sin `.ai-engineering/config.toml` → allow,
  exit 0. El repo sigue siendo el que se declara gobernado y el lock sigue pinchando canon y contrato.
- DECIDIDO hoy: el carrier vive donde cada host lo lee de verdad. Cursor (`.cursor/hooks.json`) y Copilot
  (`.github/hooks/ai-eng.json`) conservan copia en el repo porque sus cloud agents y VS Code Copilot Chat solo leen
  archivos del repo (`src/surfaces/adapters.ts:109-117`, medido en `research/003`). Claude Code, OpenCode, Oh My Pi,
  Codex y Pi se van a la maquina. Un repo gobernado pasa de 7 archivos de carrier a 2.
- DECIDIDO hoy: el floor de git usa `init.templateDir` (mismos shims marker-managed, mismo sitio), y va en la ultima
  fase del plan. Tres condiciones: (a) nunca pisar un `init.templateDir` que ya exista, se copian nuestros shims
  dentro del del usuario; (b) la puerta de repo gobernado tambien en `ai-eng git <hook>`; (c) fail-closed solo en
  repo gobernado, sin `config.toml` el shim sale 0. `core.hooksPath` global queda descartado: un `hooksPath` local
  (husky, pre-commit) gana al global y deja el repo sin gobernanza en silencio.

## Decisions still open

1. CERRADA: carrier global, politica declarada por repo (puerta en `chain`).
2. CERRADA: el carrier vive donde el host lo lee. Maquina: Claude Code, OpenCode, Oh My Pi, Codex, Pi.
   Repo: Cursor (`.cursor/hooks.json`, cloud agents solo leen hooks de proyecto) y Copilot
   (`.github/hooks/ai-eng.json`, VS Code Copilot Chat y el cloud agent solo leen el repo; su CLI lee
   `~/.copilot/hooks/ai-eng.json`, que pasa a escribirse siempre y no solo con `--global`). Dos archivos de
   carrier por repo gobernado.
3. CERRADA: floor de git con `init.templateDir` y sus tres condiciones, en la ultima fase.
4. Version (default recomendado, pendiente de confirmar): el hot path es siempre el binario de la maquina, el lock
   sigue pinchando canon y contrato, y `doctor` avisa cuando el binario es mas nuevo que el lock.
5. Trust por superficie (default recomendado): documentar el coste en `doctor` y no intentar saltarlo. Codex: una
   revision por hash en `/hooks`, una vez por hook. Pi y OMP: con carrier global se ahorran el trust de proyecto.
   Cursor cloud: fuera de cobertura, dicho con esas palabras.
6. `config.toml` (default recomendado): intacto, sigue siendo la declaracion por repo y la fuente de
   `enabledSurfaces()`.
7. CERRADA: el alcance incluye el arreglo del allow de Cursor. Fuera: el split `copilot` / `copilot-cloud` y
   generalizar `loopEvidence` a `can.evidence` (`research/003` los deja para su propio trabajo).
8. Instalacion del carrier de maquina (default recomendado): en `init --global`, que ya disena un multiselect de
   superficies en §14.0b, y ademas cuando un repo declara una superficie que aun no tiene carrier, dentro del mismo
   paso "machine side" que ya pide permiso.

## Constraints and guardrails

- §13: no prometer lo que una superficie no puede cumplir; una superficie sin adapter no se ofrece.
- Coexistencia con husky y con `pre-commit` (un `core.hooksPath` local gana al global).
- Sin secretos ni rutas absolutas de maquina en archivos versionados.
- Todo lo que un humano ve pasa por `src/ui.ts`; los verbos de maquina (`chain`, `git`, `wrap`, `spec`) no.
- El canon de skills no cambia de sitio: ya es de maquina.

## Out of scope

- Emulacion del rewrite de salida en Cursor (gap del vendor, `research/003`).
- Un dialecto nuevo por host.
- Usar `--dangerously-bypass-hook-trust` de Codex como ruta de instalacion (`research/003`).
- Bundlear el chain para los hosts que hacen shell-out.

## Open questions for research

0. Niebla que sigue abierta y no cabe en ningun gate (venia de un mapa que estaba fuera del slot, y el slot es
   este): (a) si los hosts in-process de OMP, OpenCode y Pi llaman `chain()` con cwd igual a la raiz del
   workspace, que todo el diseno de puerta por cwd asume; (b) que pasa con un equipo donde solo una persona tiene
   el carrier en su maquina: el repo esta declarado y el companero no tiene nada. La primera se resuelve con un
   probe dentro del paso 4 del plan; la segunda es una decision de producto que nadie ha tomado todavia.

1. Claude Code ejecuta hooks de user scope en un workspace NO confiado? En `research/004 §05` quedo
   `[unsourced]`. Importa porque decide si el carrier global ahorra el paso de trust o solo lo mueve.
2. Cursor cloud tiene hoy alguna ruta de maquina para hooks? `research/004` dice que solo dispara hooks de
   proyecto. Importa porque decide si la copia por repo sobrevive como caso obligatorio.
3. Cual es la ruta exacta de descubrimiento de hooks (no de extensiones) en OMP y en Pi a nivel usuario?
   Importa para escribir el carrier en el sitio que el host lee de verdad.
4. Codex: como se comporta `codex exec` con un hook de usuario (el issue #26383 habla de hooks de repo).
   Importa porque Codex es la superficie experimental y queremos una verdad medida, no documentada.

## Handoff notes

- Orden sugerido para el planner: (a) puerta de repo gobernado en `chain`; (b) carrier de maquina por
  superficie y retirada de los carriers del repo; (c) `doctor` y `uninstall` al nuevo contrato; (d) floor de
  git como decision aparte.
- Archivos que este trabajo toca: `src/chain/mod.ts`, `src/env.ts`, `src/surfaces/adapters.ts`,
  `src/commands/{init,init-shared,update,uninstall,doctor,config}.ts`, `src/install.ts`, plantillas de
  `templates/`, `scripts/proof-cli-ux.sh`, `tests/adversarial/init-recovery.test.ts`,
  `tests/surfaces.test.ts`, y las secciones §13, §14.0a y §14.5b del blueprint.
- Evidencia ya pagada que este plan debe citar en vez de repetir: `research/003` y `research/004`.


## Diseno (borrador v1, en revision)

Marcado `[evidencia]` lo que ya esta verificado en esta sesion, `[pendiente: <agente>]` lo que depende de los cuatro
cortes que estan corriendo (CarrierCallSites, ComparablePlacement, TrustFacts, ModelAdversary).

### A. La puerta de repo gobernado

- Un solo predicado nuevo, en `src/env.ts` junto a `repoRoot()`: `isGoverned(root)` = `root !== null` y existe
  `join(root, ".ai-engineering", "config.toml")`. `[evidencia]` (misma condicion que ya usa `init.ts:156` y `env.ts:27`).
- `runChain` (`src/chain/mod.ts:103`) la consulta **antes** de normalizar el payload y antes de escribir receipts:
  sin repo gobernado devuelve `{action:"allow"}` sin tocar disco. El limite fail-closed del payload sigue existiendo,
  pero solo donde hay algo que proteger. `[evidencia]` del bug que esto arregla: `writeReceipt` y el cache de veredictos
  escriben bajo la raiz del repo (`src/chain/mod.ts:129-135`).
- `ai-eng git <hook>` (`src/floor/*`) consulta lo mismo: sin `config.toml` sale 0 y en silencio. Hoy medido sale 1.
- La puerta NO se duplica en cada guard: se pone donde todos los caminos pasan (stdio, in-process y git floor).

### B. Carriers de maquina

- Tabla nueva en `src/surfaces/adapters.ts` (o en `surfaces.json`): para cada id, la ruta de nivel usuario donde su host
  lee de verdad, y si el carrier es de maquina o de repo. Maquina: claude-code `~/.claude/settings.json`, opencode
  `~/.config/opencode/plugins/ai-eng{,-chain}.ts`, oh-my-pi `~/.omp/agent/extensions/ai-eng{,-chain}.ts` (ruta exacta
  `[pendiente: TrustFacts]`), codex `~/.codex/hooks.json`, pi `~/.pi/agent/extensions/ai-eng{,-chain}.ts`, copilot CLI
  `~/.copilot/hooks/ai-eng.json`. Repo: cursor `.cursor/hooks.json`, copilot `.github/hooks/ai-eng.json`. `[evidencia: research/004 §01]`
- **Regla dura: nunca reescribir entero un fichero de la maquina que el usuario ya posee.** `~/.claude/settings.json` y
  `~/.codex/hooks.json` pueden tener hooks, permisos y env propios. Se mezclan SOLO nuestras entradas, marcadas por
  `command` que contiene `ai-eng chain`; si el fichero no es JSON valido o no es escribible, `init` lo dice y no toca
  nada. `uninstall` quita exactamente esas entradas y deja el resto byte a byte.
- Los hosts in-process (OMP, OpenCode, Pi) se llevan el bundle del chain igual que hoy, pero en su carpeta de usuario.
- Quien escribe: `installCanon` (fase maquina de `init --global` y de `update`), no `planEntries`.

### C. init, update, doctor y uninstall al contrato nuevo

- `init` fase 2 deja en el repo: contrato, `overrides.toml`, `arch.rules.json`, `config.toml`, workflow CI, los tres
  shims de git, y solo los dos carriers de repo (cursor y copilot). Los otros cinco se escriben en el paso "machine
  side", bajo el mismo permiso que ya pide el canon. `[evidencia]` de lo que hay hoy: `init-shared.ts:42-83`.
- `update` refresca las dos mitades: carriers de maquina (mezcla) y assets del repo (3-way, como hoy).
- `doctor` parte el chequeo 11 en dos: "carrier de maquina \<superficie\>" (existe, mezcla intacta, y para in-process el
  bundle coincide con el binario) y "repo declara \<superficie\>" (config.toml lo lista, y si es cursor o copilot su
  carrier de repo esta). El chequeo 5 (git floor) suma: `init.templateDir` presente y nuestro. `[evidencia]` de los
  chequeos actuales: `doctor.ts:112-122`, `:200-233`.
- `uninstall` scope proyecto: barre carriers de repo, shims y contrato. Scope Everything: quita nuestras entradas de los
  ficheros de maquina, restaura `init.templateDir` al valor que tenia (o lo deja sin poner si no estaba), y borra el
  canon. El estado que hay que restaurar se guarda en un fichero de maquina (candidato: `~/.ai-engineering/machine.json`,
  que ademas resuelve el `projects.json` que el blueprint promete y no existe). `[pendiente: ModelAdversary]` sobre orden
  de borrado y huerfanos.

### D. Floor de git (ultima fase)

- `git config --global --get init.templateDir`: vacio → se pone el nuestro y se recuerda; apuntando a una carpeta del
  usuario → se copian nuestros tres shims dentro de la suya, marker-managed, sin tocar su setting; apuntando a la
  nuestra → se asegura que los shims estan.
- El shim deja de ser "falla cerrado siempre": sin `.ai-engineering/config.toml` sale 0 (no es asunto nuestro), con
  `config.toml` y sin `ai-eng` en PATH sale 1 (un repo gobernado no puede pasar en silencio). La misma regla vive en el
  binario (`ai-eng git <hook>`), y el diseno dice por que se acepta esa duplicacion: el shim decide "¿molesto al
  binario?", el verbo decide "¿que dice la politica?". `[pendiente: ModelAdversary]` sobre divergencia entre los dos.
- `core.hooksPath` global queda descartado con la razon escrita: un `hooksPath` local (husky, pre-commit) gana al global
  y deja el repo sin gobernanza en silencio. `[evidencia: research/004 §04]`

### E. El allow de Cursor

- Una rama en el camino de allow: cuando el dialecto exige envelope explicito, se emite el mismo shape que ya sabe
  construir `allowRewrite()` sin el `updated_input`. Predicado en `src/chain/dialect.ts` junto a `deny` y `allowRewrite`,
  con el comentario que nombra la medicion; si aparece un segundo host que lo necesite, pasa a `surfaces.json` como
  capacidad. `[evidencia]` `dialect.ts:67-78`, `chain/mod.ts:247-263`, `templates/settings.cursor.json.tpl:3`.
- Codex documenta que silencio con exit 0 es exito, Claude y Pi usan exit 2 para bloquear: no se les manda envelope.

### F. Pruebas (cada decision con su gate)

1. Puerta: en un repo temporal sin `.ai-engineering/`, payload adversarial → allow, exit 0, cero stdout; en repo
   gobernado → deny, exit 2.
2. Floor: repo sin `config.toml` → `ai-eng git commit-msg` exit 0; repo gobernado sin binario → exit 1.
3. Allow de Cursor: llamada permitida con `--surface cursor` → stdout con `{"permission":"allow"}`, exit 0 (el
   experimento del research 003 convertido en test).
4. Merge de maquina: un `~/.claude/settings.json` con hooks propios sobrevive a init, update y uninstall, byte a byte
   en lo que no es nuestro. Es el test de mas riesgo del plan.
5. Round trip de uninstall: estado de maquina antes y despues identico (incluido `init.templateDir`).
6. `doctor`: carrier presente sin `config.toml` dice "no gobernado"; `config.toml` sin carrier dice la linea de accion.
7. `scripts/proof-cli-ux.sh`: extender con el camino global (init escribe carriers de maquina, el repo queda con 2,
   uninstall Everything los limpia).

### G. Riesgos abiertos

- Trust invalidado por `update` (Codex re-revisa cada vez que reescribimos su hooks.json) `[pendiente: TrustFacts]`.
- Ficheros de maquina compartidos con el usuario (dotfiles, symlinks, JSON con comentarios) `[pendiente: ModelAdversary]`.
- Version skew: un binario de maquina para N repos con locks distintos `[pendiente: ModelAdversary]`.
- Conflicto usuario vs repo en hosts que mezclan ambitos `[pendiente: ComparablePlacement]`.
- Sitios que hoy escriben bajo la raiz del repo y que la puerta deja sin cubrir `[pendiente: CarrierCallSites]`.


## Comparables externos (evidencia, corte ComparablePlacement)

Nota de higiene: el informe del agente arrastra un desliz de contexto y a veces llama "OMP" al proyecto que
estamos disenando. La evidencia y las URLs valen; su framing no se cita.

### Como resuelven el conflicto usuario vs repo (patron observado)

| Patron | Quien lo hace | Que nos dice |
|---|---|---|
| Los hooks se UNEN entre ambitos, la config se reemplaza | Claude Code, Codex, Cursor | Un hook de maquina no lo apaga un hooks.json de repo. La puerta de ai-eng decide, no el host. |
| Precedencia escalonada explicita | Cursor (Enterprise > Team > Project > User), Claude (Managed > CLI > Local > Project > User) | El nivel de maquina es un nivel mas, y en los dos casos el nivel admin es el unico no desactivable. |
| Guard por defecto: no instalo en repo si hay politica de maquina | pre-commit (`--allow-global-hooks`, PR #2994), lefthook (PR #1292/#1371) | Existe precedente de que el repo NO pise la politica de maquina sin permiso explicito. |
| Override del usuario que no contamina el repo | lefthook `lefthook-local.yml`, Claude `.claude/settings.local.json` | ai-engineering ya tiene el equivalente: `overrides.toml` (hoy solo para guards, podria ser la escotilla "en este repo no"). |
| Delta sobre lo global, no reemplazo | Pi (`autoload: false`), OpenCode (deepmerge local gana) | El proyecto extiende la maquina; no la sustituye. Es exactamente nuestro modelo declarado. |
| Kill switch por entorno | husky (`HUSKY=0`), git (`core.hooksPath=/dev/null`) | Precedente para una variable que apague el subsistema entero sin tocar ficheros. |
| Trust por hash se invalida al cambiar el fichero | Codex (PR #20321: `trusted_hash` en `config.toml`, hook cambiado → re-review) | RIESGO NUEVO Y CONCRETO: si `ai-eng update` reescribe `~/.codex/hooks.json`, el usuario tiene que volver a revisarlo en `/hooks`. A confirmar por TrustFacts. |

### Tres cosas que NO se pueden copiar tal cual

1. **El nivel Managed/Enterprise no existe aqui**: en Claude Code y Cursor lo distribuye un admin (MDM, dashboard,
   consola). ai-engineering no tiene ni quiere esa infraestructura, asi que "politica que no se puede desactivar" no
   es una opcion, y el modelo declarado (config.toml) es el sustituto honesto.
2. **Los formatos de merge difieren por host**: JSON plano que reemplaza capas (Claude, Codex, Cursor) frente a YAML
   con deep-merge de objetos y reemplazo de arrays (OMP). Nuestro merge por marcador tiene que ser nuestro, no
   importado de ninguno.
3. **Codex y Cursor ya tienen un bug o una ambiguedad en el merge**: en Cursor hay reporte de que `updated_input`
   resuelve al reves de la precedencia escrita. No escribimos carrier de usuario para Cursor, asi que hoy no nos toca;
   si algun dia se anade, hay que medirlo, no documentarlo.


## Hechos cerrados (corte TrustFacts) y sus correcciones al diseno

### 1. Claude Code: user scope NO pasa por el trust del workspace

Un hook en `~/.claude/settings.json` se ejecuta aunque el workspace no este confiado; el dialogo de trust gatea los
hooks de **project scope** (`.claude/settings.json` del repo) en sesiones interactivas, y en headless/SDK no hay
dialogo. Evidencia: issue anthropics/claude-code #13288 y #83502 (respuesta de maintainer, 2026-08-16).
**Correccion al diseno**: el carrier de maquina de Claude no gana un paso de trust, y la linea final de `init`
("Trust the workspace in your surface: without trust, hooks do not run") pasa a ser **por superficie**: verdadera
para Cursor y Copilot (cuyo carrier vive en el repo), falsa para Claude Code con carrier de usuario. Ademas refuerza
que la puerta de repo gobernado es imprescindible: un hook de user scope corre en todo.

### 2. Codex: el trust se invalida cuando el fichero cambia

El trust es por hash normalizado de la definicion (evento + matcher), persistido en `config.toml`; un fichero que
cambia invalida la aprobacion y el hook se salta en silencio hasta que el humano lo revisa en `/hooks`. Hay dos
puertas separadas: folder trust y hook-definition trust. Evidencia: PR openai/codex #20321 (merged 2026-05-05),
issues #37362 y #35306.
**Correccion al diseno**: `update` no puede reescribir `~/.codex/hooks.json` "porque si". Se escribe solo cuando los
bytes cambian (el instalador ya hace no-op si coincide), y cuando cambian **se dice**: linea de accion "Codex: revisa
/hooks", y `doctor` reporta el estado de trust como desconocido o pendiente, nunca como verde. Un carrier que se
reescribe en cada release obliga a un humano a re-aprobar en cada release: eso es coste del diseno, no del usuario.

### 3. OMP y Pi: donde viven de verdad los hooks de usuario

- **OMP** descubrimiento nativo: `<cwd>/.omp/hooks/pre|post/*.{ts,js}` en proyecto, `<agentDir>/hooks/pre|post/*.{ts,js}`
  en usuario (perfil y `PI_CODING_AGENT_DIR` aware), sin recursion. Extensiones: `~/.omp/agent/extensions/`.
  Evidencia local: `omp://hooks.md:10,55`, `omp://extension-loading.md`, y el arbol real de esta maquina
  (`~/.omp/agent/extensions/herdr-omp-agent-state.ts` existe y se descubre).
- **Pi** no tiene hooks nativos de usuario: solo extensiones (`~/.pi/agent/extensions/*.ts`), o el paquete de
  terceros `pi-yaml-hooks` (`~/.pi/agent/hook/hooks.yaml`). Evidencia: pi.dev/docs/latest/extensions y
  pi.dev/packages/pi-yaml-hooks.
**Correccion al diseno**: el carrier de maquina de OMP es un hook en `~/.omp/agent/hooks/pre/ai-eng.ts` (+ el bundle
del chain al lado); el de Pi es una extension en `~/.pi/agent/extensions/`, no un hook.

### 4. Cursor cloud: confirmado por el vendor

Los cloud agents de Cursor **no** ejecutan hooks de usuario ("cloud VMs don't have access to your local home
directory") y si ejecutan los de proyecto (`cursor.com/docs/cloud-agent`). Nuestra decision de dejarle su carrier en
el repo queda respaldada por documentacion del vendor, no por inferencia.

### 5. HALLAZGO NUEVO Y SERIO: el carrier de OMP que ai-engineering ya envia no se carga

ai-engineering escribe `.agents/hooks/ai-eng.ts` y `surfaces.json` lo declara como `pluginFile` de oh-my-pi, y el
chequeo 11 de `doctor` verifica su existencia. Pero OMP no lee `.agents/hooks/`:
`omp://hooks.md` da `<cwd>/.omp/hooks/pre/*.ts` como ejemplo de descubrimiento, `omp://extension-loading.md` dice que
el descubrimiento nativo es `.omp`, y el `agents` provider de OMP existe para **skills** (`.agent[s]/skills`, canonico y
con sus propios toggles, `omp://skills.md:116`), no para hooks. Esa asimetria explica por que los espejos de skills a
`.agents/skills` si funcionan mientras el carrier de hooks puede no cargar nunca.
**Estado**: `[verificar antes de construir]`, y el veredicto es de una sola comprobacion (una sesion de OMP en un repo
con el carrier y un `git commit -n`; si no hay deny ni receipt, el carrier esta muerto). Cae de lleno en la regla §13
del repo: una existencia no es una prueba, y `doctor` hoy da verde sobre un carrier que puede no cargar.
**Consecuencia para el plan**: cada carrier, de maquina o de repo, lleva su **prueba de descubrimiento** propia antes
de darse por bueno. No se construye sobre una ruta que no se ha visto cargar.


## Ataque al modelo (corte ModelAdversary)

### Ya esta en el plan (no son hallazgos nuevos, son el trabajo que este plan existe para hacer)
- F1 la puerta no existe hoy (`src/chain/mod.ts:103-159` corre todos los guards sin mirar governance): es la pieza A.
- F5/F10 `init.templateDir` ni se escribe ni se restaura hoy (`grep templateDir src/` = 0): es la pieza D.
- F6 el floor de git tampoco tiene puerta (`src/floor/entry.ts:28-34`): es la pieza D, y esta medido.
- F4 el trust de Codex se invalida al reescribir: mitigado en la seccion de hechos (escribir solo si cambian los bytes).

### Hallazgos que SI cambian el diseno
- **F2 (bloqueante): la puerta no puede ser "existe el fichero".** `loadConfig()` devuelve `{}` ante un TOML ilegible
  (`src/env.ts:69-74`) y `enabledSurfaces()` cae a `["claude-code"]` (`:80-97`), asi que un `config.toml` de cero bytes
  seria "gobernado con valores por defecto". Regla nueva: la puerta exige config.toml **parseable y con la seccion de
  superficies**, y `doctor` distingue ausente de corrupto (hoy el chequeo 3 solo usa `existsSync`, `:53-57`).
- **F3 (importante): ninguna primera escritura es total si el fichero ya existe.** `install()` protege con diff de 3
  vias las actualizaciones, pero en la primera instalacion escribe la plantilla entera (`src/install.ts:24-33`), y la
  plantilla de Claude solo tiene nuestros hooks (`templates/settings.claude.json.tpl`). En el repo eso ya duele; en
  `~/.claude/settings.json` es inaceptable. Regla nueva: **merge por marcador desde la primera escritura, en repo y en
  maquina**, con el contenido ajeno intacto byte a byte.
- **F7 (importante, riesgo nuevo): un downgrade del binario reintroduce el fail-closed en repos ajenos.** Los carriers
  de maquina son del binario nuevo; si el usuario baja de version, el hook ejecuta un `chain` sin puerta y deniega en
  todos los repos. Regla nueva: el estado de maquina (`~/.ai-engineering/machine.json`) registra **que version escribio
  los carriers**, y `doctor` avisa cuando el binario es MAS VIEJO que ese registro, con linea de accion. Es el mismo
  fichero que resuelve el `projects.json` que el blueprint promete y no existe.
- **F8 (menor): `init` desconfigura `core.hooksPath` sin preguntar** (`src/commands/init.ts:76-80`). Si un usuario lo
  tiene puesto por su empresa, hoy se lo borramos en silencio. Regla nueva: registrar y avisar, o restaurar en uninstall.
- **F9 (menor): superficie declarada sin carrier en la maquina** debe tener linea de accion en `doctor`, no solo WARN
  generico.

### Ataques que NO entraron (se dejan escritos para no repetirlos)
- Divergencia shim contra binario: el shim de git es un trampolin de 3 lineas (`templates/git-pre-commit.tpl:6`) y la
  logica vive en el binario. No hay segundo camino de codigo, asi que la duplicacion que yo temia no existe.
- "Fail-open = cualquiera desactiva ai-eng borrando config.toml": `config.toml` esta versionado y self-protect bloquea
  escrituras a `.ai-engineering/`. El borrado manual es el precio documentado de la puerta, no un agujero.
- JSON con comentarios, Windows sin `jq`, symlinks en dotfiles: ai-eng escribe con `writeFileSync` desde plantilla y no
  parsea el fichero ajeno, asi que ninguno de los tres aplica **hoy**. Aplica en cuanto metamos merge por marcador: el
  parseo del fichero ajeno pasa a ser nuestro problema y ahi vuelven los tres.

### Sospechas sin verificar que merecen un probe (no un parrafo)
1. Hooks de Copilot a nivel repo en versiones posteriores a 1.0.83 (la referencia publicada ahora dice que si
   funcionan). Se re-prueba por release.
2. Semantica de salida vacia en el Cursor IDE frente a `cursor-agent` (el allow de la pieza E se midio en el CLI).
3. Los hooks de user scope de Claude Code en workspace no confiado quedaron cerrados por TrustFacts (issue #83502).


## Inventario de sitios (corte CarrierCallSites)

`repoRoot()` (`src/env.ts:24-31`) **no es una puerta de gobernanza**: cuenta cualquier ancestro con `.git`. Hoy
existen al menos tres definiciones distintas de "gobernado" (`repoRoot()` con upward walk, `init.ts:96` cwd-only,
`config.ts:21` carrier-existente), y ~40 simbolos consumen la primera.

### Reglas nuevas que salen del inventario

- **R1 · una sola puerta.** Todo sitio que hoy reimplementa "gobernado" como `repoRoot() !== null` pasa a consultar
  `isGoverned()`. La lista del inventario: `src/env.ts:27`, `src/commands/config.ts:21`, `src/commands/init.ts:96` y
  `:156`, `src/commands/update.ts:62`, `src/commands/uninstall.ts:80`, `src/floor/entry.ts:12`,
  `src/spec/index.ts:88,140,173,193`, `src/chain/mod.ts:126` (el dedup depende de la puerta), `src/guards/self-protect.ts:50`,
  `src/receipts.ts:24`, `src/guards/no-verify.ts:54`.
- **R2 · un repo que no pidio gobernanza no recibe ni un byte.** Hoy `writeReceipt()` crea
  `<repo>/.ai-engineering/receipts/` en un repo ajeno con solo `.git` (`src/receipts.ts:32`), y `specOpen` crea el
  carrier entero (`src/spec/index.ts:144-145`). Con la puerta, lo primero se apaga; lo segundo necesita decision
  propia.
- **R3 · el cache de veredictos nunca ha funcionado.** `rememberVerdict` escribe `<root>/cache/verdicts/<session>.json`
  sin `mkdir` y con `catch` silencioso (`src/chain/mod.ts:83-98`, `:126-127`); la ruta esta fuera del carrier y del
  `.gitignore`. Dos salidas: arreglarlo (mkdir + sanear `session_id`, que hoy entra crudo en la ruta y permite
  traversal) o borrarlo. Es deuda previa, no de este plan, pero el plan la toca.
- **R4 · `protectedPaths(null)` desprotege HOME** (`src/guards/self-protect.ts:50` contra `:79-83`): fuera de un repo,
  el canon y sus espejos no estan en la lista, y ademas usa `homedir()` crudo en vez de `home()`, asi que en tests
  protege una ruta distinta de la que se escribe.
- **R5 · `init` y `repoRoot()` tienen que usar el mismo paseo hacia arriba** (`init.ts:96` mira solo el cwd, y en un
  subdirectorio crea un carrier anidado que despues gana al del padre).
- **R6 · mover el carrier obliga a migrar.** El bundle del chain duplica `repoRoot`/`receiptsDir`/`cacheFile`
  (`skills/.chain-bundle/ai-eng-chain.ts`) y cada repo gobernado lleva su copia: el plan necesita regenerar assets y
  una linea de `doctor` que mande a `update`, porque hoy `chainDiffers` detecta el drift pero no hay migracion del
  carrier.
- **R7 · CI es una maquina mas.** `templates/ci.yml.tpl` y `.github/workflows/check.yml:55-63` ejecutan el contrato
  contra el checkout: en el modelo nuevo el runner hace `update --yes` (instala canon y carriers de maquina) y lee el
  contrato del repo. No hace falta carrier por repo en CI; hace falta que la linea este escrita.

### El floor de git no es el carrier, pero viaja con el

`gitHookEntries()` vive en `init-shared.ts:34-38` y aparece en el lock, en los chmods de `update:166-169`, en los
markers de `uninstall:153-160`, en el chequeo 5 de `doctor:118` y en los literales de self-protect:66. Mover "el
carrier" moviendo solo `.ai-engineering/` partiria la instalacion en dos raices; por eso la pieza D es una fase
propia y no un detalle de la B.

### Sospechas que el inventario deja abiertas

- `[unsourced]` si los hosts in-process llaman `chain()` con cwd igual a la raiz del workspace en las tres
  superficies. Todo el diseno de puerta-por-cwd lo asume y nadie lo ha probado.
- `[unsourced]` la nota "best-effort: cloud FS, receipts may not survive" de Copilot (`surfaces.json`) afirma
  comportamiento sin medicion; si fuera cierta, parte del argumento de su carrier en repo ya estaria muerto.
