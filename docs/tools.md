# Guía rápida de comandos
Esta es la chuleta para instalar, entender y ejecutar este repositorio sin tener que leer el código.
> Ejecuta todo desde la raíz. Usa `uv run ai-eng` para el código local; si instalaste la herramienta, puedes escribir solo `ai-eng`.
## 1. Preparación
Necesitas **Python 3.11+**, `uv` y `just`; `just security`/`just check` también necesitan `gitleaks` y `trivy`. En macOS: `brew install uv just gitleaks trivy`.

```bash
uv sync                    # prepara el entorno local
uv tool install --editable .  # opcional: deja `ai-eng` disponible en el PATH
uv run ai-eng --help       # muestra la CLI del proyecto
just --list                # muestra las tareas de desarrollo
```
> Ruta habitual: prepara una vez con `uv sync` → trabaja con `just changed` → antes del PR ejecuta `just check` y `just mutate`.
## 2. Cómo funciona
`ai-eng` instala o escribe la configuración y el registro; `hooks/chain.py` recibe las acciones del agente y llama a los guardas; los hooks de Git protegen commits y pushes; CI ejecuta las mismas recetas de `just` que tú ejecutas localmente.
## 3. Todos los comandos `ai-eng`
| Comando | Para qué sirve |
|---|---|
| `uv run ai-eng init [--global] [--no-global] [--project [RUTA]] [--no-project] [--harness IDS] [--overwrite ARCHIVOS\|all] [--dry-run] [-y]` | Configura la máquina y, si lo eliges, el repositorio. Escribe `.github/workflows/check.yml` y un `justfile` con los comandos de los stacks que encuentre. Empieza con `--dry-run`; no instala binarios ni hace commits. |
| `uv run ai-eng doctor [--ci] [--paths] [--fix]` | Ejecuta el diagnóstico de salud. `--ci` omite lo que un runner no puede comprobar; `--paths` enseña dónde vive cada clase de archivo; `--fix` ejecuta solo las curas que los propios fallos declaran y vuelve a comprobar. |
| `uv run ai-eng update [--to VERSION] [--force]` | Migra el pin del proyecto de forma interactiva. `--force` **solo informa** qué se descartaría; nunca sobrescribe cambios locales. |
| `uv run ai-eng spec new SLUG [--ref owner/repo#45]` | Crea `specs/NNN-slug/spec.md`; `--ref` solo anota el work item en el frontmatter y no rellena nada. |
| `uv run ai-eng spec list [--all]` · `uv run ai-eng spec show ID` | Lista especificaciones o muestra una; `--all` incluye las reemplazadas. |
| `uv run ai-eng decide "DECISIÓN" [--why "MOTIVO"] [--adr] [--supersede NNNN]` · `uv run ai-eng decide --list` | Guarda una decisión en la spec más nueva o crea/lista un ADR en `docs/adr/`. |
| `uv run ai-eng accept --finding ID --expires AAAA-MM-DD --by PERSONA --justification TEXTO [--severity NIVEL] [--follow-up TEXTO] [--spec ID]` · `uv run ai-eng accept --expired` | Registra un riesgo con dueño y caducidad, o lista los ya caducados. Las cuatro primeras son obligatorias: una aceptación sin nombre y sin razón no es una aceptación. |
| `uv run ai-eng audit [verify\|replay] [--anchors] [--session ID] [--anchor]` | Verifica o reproduce la cadena de auditoría. `--anchors` coteja Git; `--anchor` es para el hook `commit-msg`. |
| `uv run ai-eng digest [--weeks N]` | Resume sesiones, bloqueos, bypasses, errores y cobertura del periodo; marca el resumen como leído. |
| `uv run ai-eng plan --skip "MOTIVO" [--guard design_gate\|loop_guard]` | Con confirmación humana, concede **un** bypass durante 15 minutos y lo registra. No funciona sin terminal interactiva. |
| `uv run ai-eng uninstall [--project] [-y]` | Quita lo instalado según el recibo. Conserva siempre `specs/`, `CONSTITUTION.md`, `AGENTS.md`, `docs/adr/` y el registro externo. |
| `uv run ai-eng --version` · `uv run ai-eng <comando> --help` | Muestra la versión o todas las opciones reales de un comando. |

## 4. Todas las recetas `just`
| Receta | Qué ejecuta y cuándo usarla |
|---|---|
| `just build` | Construye el wheel y el paquete fuente con `uv build`. |
| `just lint` | Ejecuta Ruff: reglas de código y comprobación de formato. |
| `just test` | Ejecuta toda la suite de Pytest. Para un archivo: `uv run --with pytest==9.1.1 pytest -q tests/test_doctor.py`. |
| `just security` | Busca secretos con Gitleaks, analiza reglas con Semgrep y revisa vulnerabilidades/licencias/configuración con Trivy. |
| `just cover` | Mide cobertura de ramas sobre paquete, hooks y suite adversarial; exige al menos 80 %. |
| `just mutate [RUTA ...]` | Introduce defectos deliberados y falla si los tests no los detectan. Sin ruta recorre todo; suele ser la tarea más lenta. |
| `just changed` | Atajo local: lint y tests completos, más mutación solo de lo cambiado. **No sustituye** al gate completo. |
| `just counts` | Imprime pruebas verificables de cuántos archivos formateó Ruff y cuántos tests recogió Pytest. |
| `just stats` | Muestra métricas del repositorio; es un informe, no un gate. Usa `uv run python tests/stats.py --json` para JSON. |
| `just check` | Gate local/CI: `build + lint + test + cover + security + counts`. No incluye `just mutate`, que es un gate separado. |

## 5. Scripts directos y automatismos
| Ejecución | Uso |
|---|---|
| `uv run python tests/adversarial/run.py` | Lanza todos los ataques y un caso limpio que no debe bloquearse. |
| `uv run python tests/mutation.py [-k RUTA]` | Mitad de mutación específica de los guardas; normalmente usa `just mutate`. |
| `uv run python tests/anti_theatre.py LOG [RAÍZ] [nombres,separados]` | CI: confirma que un log demuestra que los gates realmente corrieron. |
| `uv run python tests/stats.py [--json]` | Genera el informe de gobierno, calidad y seguridad. |
| `SONAR_TOKEN=... uv run python tests/quality_gate.py [project-key]` | CI: compara el Quality Gate real de SonarCloud con `policy/quality-gate.toml`. |
| `uv run python migrations/0.13..1.0/unvendor.py [RAÍZ] [HOME]` | Migración interna desde 0.13; normalmente la llama `ai-eng update`, no una persona. |

| Automático | Qué hace |
|---|---|
| `git-hooks/` | `pre-commit` busca secretos; `commit-msg` valida el asunto y añade el ancla; `pre-push` bloquea ramas protegidas, secretos salientes y riesgos caducados. |
| `hooks/chain.py` | Despacha `self_protect`, `no_verify_guard`, `injection_guard`, `loop_guard`, `design_gate`, `autoformat` y `session`; no se ejecutan a mano. |
| `hooks/_emit.py`, `_otlp.py`, `_wrap.py` | Mantienen el registro, exportan OTLP y definen el comportamiento fail-closed/fail-open; son auxiliares internos. |
| `tests/test_*.py` · `surfaces/opencode.ts` | Pytest recoge los tests y OpenCode carga su plugin. |
| `.agents/skills/ai-*` | El agente invoca `ai-debug`, `ai-explore`, `ai-note`, `ai-plan`, `ai-research`, `ai-review`, `ai-ship` y `ai-spec`; no son comandos del shell. |
| `.github/workflows/` | GitHub ejecuta check, ataques, mutación, mypy, Sonar, Snyk, instalación multiplataforma y publicación; localmente usa las recetas anteriores. |
