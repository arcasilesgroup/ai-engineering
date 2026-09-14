# MAP — gobernanza global de ai-engineering (carriers en la maquina)

## Destination

Los hooks de ai-engineering viven en la maquina, escritos una vez por superficie, y un repo participa
declarandose en `.ai-engineering/config.toml`. Un repo que no se declara no recibe politica de ai-eng, ni de agentes
ni de git. Dos excepciones, por lectores que solo existen en el repo: Cursor y Copilot.

## Open questions

1. [x] Que significa "global": el carrier o la politica — grilling
2. [x] Donde vive el carrier de cada superficie — research
3. [x] El floor de git: templateDir, core.hooksPath o quieto — grilling
4. [x] Alcance: entra el allow de Cursor, entra la deuda destapada — grilling
5. [x] Codex: aceptar el coste de re-aprobar en /hooks, o dejarlo sin carrier — grilling
6. [x] La puerta exige `config.toml` parseable, no existente — grilling
7. [x] Como se escribe un carrier sobre un fichero que el usuario ya posee — grilling
8. [x] Que version manda en el hot path y como se detecta un downgrade — grilling

## Not yet specified

- Si los hosts in-process de OMP, OpenCode y Pi invocan `chain()` con cwd igual a la raiz del workspace. Todo el
  diseno asume que si; nadie lo ha medido. Se resuelve con un probe durante la construccion.
- Que pasa con un equipo donde solo una persona tiene ai-eng instalado en la maquina: el repo esta declarado y el
  companero no tiene carrier. Es una decision de producto, no tecnica, y hoy no esta tomada.

## Out of scope

- Nivel Managed/Enterprise que no se pueda desactivar: en Claude Code y Cursor lo despliega un admin por MDM o
  dashboard, y ai-engineering no tiene ni quiere esa infraestructura. Anadirlo empeora el resultado.
- Distribucion de hooks por cloud para equipos (Team hooks de Cursor): misma razon.
- Carrier de usuario para Cursor: su cloud solo lee el repo, ya medido, y su precedencia pone al usuario el ultimo.
- Emulacion del rewrite de salida en Cursor, y un dialecto nuevo por host.
- El split `copilot` / `copilot-cloud` y generalizar `loopEvidence` a `can.evidence` (`research/003` los deja para
  su propio trabajo).
- Mover a la maquina el estado del contrato (receipts, spec, research): eso se queda en el repo, es del repo.

## Answers

### Que significa "global"

**Answer:** el carrier, no la politica. El hook se escribe una vez en la maquina por superficie; un repo participa
declarandose en `.ai-engineering/config.toml`, y `chain` gana una puerta explicita: sin ese fichero, allow y exit 0.
El lock sigue pinchando canon y contrato.

**Why:** el radio de explosion esta medido. En un repo con solo `.git`, `ai-eng chain PreToolUse` ya deniega
`git commit -n` (exit 2) y `ai-eng git commit-msg` ya falla (exit 1). Llevar los hooks a la maquina sin puerta seria
imponer la politica en repos ajenos, incluidos clones de otros equipos.

**Check:** en un repo temporal sin `.ai-engineering/`, el payload adversarial sale allow, exit 0 y cero stdout; en un
repo gobernado sale deny, exit 2.
**Judged by:** run it
**Reference:** —

### Donde vive el carrier de cada superficie

**Answer:** en la ruta que su host lee de verdad. Maquina: Claude Code `~/.claude/settings.json`; OpenCode
`~/.config/opencode/plugins/`; OMP `~/.omp/agent/hooks/pre/`; Codex `~/.codex/hooks.json`; Pi
`~/.pi/agent/extensions/`. Repo: Cursor `.cursor/hooks.json` y Copilot `.github/hooks/ai-eng.json`, y ademas
Copilot CLI en `~/.copilot/hooks/ai-eng.json`.

**Why:** cada host tiene su ambito y su prioridad documentada (Claude Code user scope aplica a todos los proyectos;
Codex carga hooks de usuario incluso con el proyecto no confiado; Cursor cloud y VS Code Copilot Chat solo leen el
repo). Hay un bug vivo de por medio: ai-engineering escribe el carrier de OMP en `.agents/hooks/`, y OMP lee
`.omp/hooks/pre/`. El provider `agents` de OMP existe para skills, no para hooks.

**Check:** cada ruta se prueba cargando de verdad en su host antes de declararla; y la tabla del registro coincide con
la raiz documentada por el vendor, con fuente y fecha.
**Judged by:** run it
**Reference:** `research/004`

### El floor de git

**Answer:** `init.templateDir` en la config global de git, con los mismos shims marker-managed, y la misma puerta en
`ai-eng git <hook>`. `core.hooksPath` global queda descartado.

**Why:** `templateDir` hace que cada clone nazca con el floor sin cambiar el sitio ni el contrato (los shims siguen en
`.git/hooks`), asi que el barrido de `uninstall` y la convivencia con husky siguen valiendo. `core.hooksPath` global
tiene dos problemas medidos: al ponerlo, `.git/hooks` deja de leerse, y un `hooksPath` local (husky, pre-commit) gana
al global y deja el repo sin gobernanza en silencio.

**Check:** un clone nuevo nace con los tres shims; un `init.templateDir` que ya existia no se pisa; `uninstall` lo
restaura.
**Judged by:** run it
**Reference:** —

### Alcance

**Answer:** entra el arreglo del allow de Cursor y entra la deuda destapada por el inventario (cache de veredictos,
`protectedPaths`, `specOpen`). Fuera: el split `copilot`/`copilot-cloud` y `can.evidence`.

**Why:** Cursor conserva su carrier en el repo, y hoy bloquea todo en allow porque `chainMain` sale con `exit 0` sin
escribir nada mientras su plantilla declara `failClosed: true`. Dejar eso dentro seria enviar un carrier roto. La
deuda entra porque el plan toca los mismos archivos y dejarla seria escribir sobre una base que ya miente.

**Check:** una llamada permitida con `--surface cursor` emite `{"permission":"allow"}` en stdout y sale 0.
**Judged by:** run it
**Reference:** `research/003`

### Codex y el trust por hash

**Answer:** se conserva el carrier y se acepta que un cambio de bytes obliga a re-aprobar en `/hooks`. El carrier se
escribe solo cuando cambia, y cuando cambia se dice con una linea de accion.

**Why:** el trust de Codex es por hash normalizado de la definicion y se invalida con el fichero. La alternativa
(no dar carrier a Codex) dejaria la superficie declarada y sin nadie detras, que es el fallo que §13 prohibe. El
coste es humano y por release, no por ejecucion.

**Check:** dos `update` seguidos sobre el mismo binario dejan el sha256 del carrier intacto; cuando cambia, `doctor`
nombra `/hooks`.
**Judged by:** run it
**Reference:** —

### La puerta exige `config.toml` parseable

**Answer:** gobernado significa `config.toml` existente, parseable y con la seccion de superficies. `doctor` distingue
ausente de corrupto.

**Why:** `loadConfig()` devuelve `{}` ante un TOML ilegible y `enabledSurfaces()` cae a `["claude-code"]`, asi que un
fichero de cero bytes contaria como gobernado con valores por defecto: la politica mas estricta aplicada por el
fichero mas vacio.

**Check:** con `config.toml` de cero bytes el chain no aplica politica, y `doctor` da WARN de corrupto, no ok.
**Judged by:** run it
**Reference:** —

### Como se escribe sobre un fichero que el usuario ya posee

**Answer:** merge por marcador desde la primera escritura, con las entradas ajenas intactas byte a byte. Un fichero
ajeno que no sea JSON valido no se toca: se dice y se sigue.

**Why:** `install()` protege las actualizaciones con diff de 3 vias, pero la primera instalacion escribe la plantilla
entera, y `~/.claude/settings.json` puede tener hooks, permisos y env del usuario. Es el test de mas riesgo del plan y
el unico sitio donde el merge deja de ser nuestro.

**Check:** un `settings.json` con un hook propio sobrevive byte a byte a init, update y uninstall.
**Judged by:** run it
**Reference:** —

### Version y downgrade

**Answer:** el hot path es el binario de la maquina; el estado de maquina registra que version escribio los carriers,
y `doctor` avisa cuando el binario es mas viejo que ese registro.

**Why:** los carriers de maquina son del binario que los escribio. Un downgrade dejaria un hook nuevo llamando a un
`chain` sin puerta, y la politica volveria a caer en repos ajenos sin que nadie lo pidiera.

**Check:** con un estado de maquina de version superior al binario, `doctor` da WARN con la linea de accion.
**Judged by:** run it
**Reference:** —
