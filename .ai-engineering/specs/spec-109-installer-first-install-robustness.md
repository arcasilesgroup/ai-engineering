---
spec: spec-109
title: Installer First-Install Robustness — Pipeline Non-Critical Phases + Render-Before-Exit + Auto-Remediation + Live Progress UI
status: approved
effort: large
refs:
  - .ai-engineering/specs/_history.md
  - src/ai_engineering/installer/phases/pipeline.py
  - src/ai_engineering/cli_commands/core.py
  - src/ai_engineering/installer/ui.py
  - .ai-engineering/contexts/cli-ux.md
---

# Spec 109 — Installer First-Install Robustness

## Summary

`ai-eng install` no es robusto en proyectos nuevos: requiere correr 3 comandos (`install` → `doctor` → `doctor --fix`) para llegar a un estado verde. Cuatro defectos confirmados en `installer/phases/pipeline.py:202-203`, `cli_commands/core.py:381-383`, y `installer/phases/__init__.py:32-39`: (1) el `PipelineRunner.run()` rompe (`break`) cuando cualquier fase falla verify, así que un único tool roto en `ToolsPhase` mata el resto del pipeline y `HooksPhase` jamás corre — los hooks no se escriben, `install-state.json` no recibe `hook_hash:*`, y el siguiente `ai-eng doctor` reporta `hooks-integrity FAIL: hook verification failed: commit-msg, pre-commit, pre-push` aunque `HooksPhase` no tenga dependencia funcional con `ToolsPhase` en tiempo de instalación; (2) `cli_commands/core.py:382` imprime `"Tool installation failed; see warnings above. Run 'ai-eng doctor' to retry."` y luego hace `raise typer.Exit(80)` antes de la línea `if not is_json_mode(): _render_pipeline_steps(summary)` (línea 405-406), por lo que el usuario ve la frase "see warnings above" sin ningún warning visible — diagnóstico imposible sin leer el código; (3) la fase doctor.fix corrige automáticamente las mismas fallas (instala tool faltante via `TOOL_REGISTRY[name].install()`, reinstala hooks via `install_hooks(force=True)`), pero el usuario debe invocarla manualmente — la remediación no está enlazada al install pipeline; (4) durante `with spinner("Installing governance framework..."):` el usuario ve un spinner indeterminado que oculta qué tool/fase se está ejecutando, sin feedback granular del progreso. spec-109 cierra los 4 defectos: introduce semantics `phase.critical: bool` en `PhaseProtocol` (default True, preserva contrato existente) con `ToolsPhase.critical = False`; `PipelineRunner.run` continúa pasando fases non-critical fallidas; `cli_commands/core.py` hace render BEFORE Exit; nuevo helper `installer/auto_remediate.py` invoca el subset fixable de `doctor.phases.tools.fix + doctor.phases.hooks.fix` post-pipeline cuando hay verdicts non-critical fallados; reemplaza el spinner único por `step_progress(total=N_phases, ...)` con sub-tracker por tool. Beneficio medible: `ai-eng install` en `/tmp/probando` produce `ai-eng doctor PASS` sin intervención manual; usuario ve cada paso en tiempo real ("[5/6] Installing tool: gitleaks via uv tool"); fallas surface con detail line + remediation hint ANTES del exit.

## Goals

- G-1: `PhaseProtocol` añade property `critical: bool` (default True). `ToolsPhase.critical = False`. `HooksPhase.critical = True` (default). Verificable por `tests/unit/installer/test_pipeline.py::test_phase_critical_default_true` y `test_tools_phase_marked_non_critical`.
- G-2: `PipelineRunner.run` continúa al siguiente phase cuando un phase non-critical falla (verdict.passed = False). `summary.failed_phase` se setea SOLO si la fase fallada es critical. `summary.non_critical_failures: list[str]` (nuevo) acumula los non-critical fallados. Verificable por `tests/unit/installer/test_pipeline.py::test_continues_past_non_critical_failure` y `test_critical_failure_still_breaks`.
- G-3: `cli_commands/core.py` install path renderiza `_render_pipeline_steps(summary)` ANTES de cualquier `raise typer.Exit`. La línea `error("Tool installation failed; ...")` se mueve al final, después de que el usuario haya visto los warnings. Verificable por `tests/unit/test_cli_install_non_interactive.py::test_render_steps_before_exit_on_tool_failure` con captura de stderr buffer.
- G-4: Nuevo módulo `installer/auto_remediate.py` exporta `auto_remediate_after_install(root, summary) -> AutoRemediateReport`. Reusa `doctor.phases.tools.fix` y `doctor.phases.hooks.fix` directamente (no duplica logic). Invocado desde `cli_commands/core.py` SOLO cuando `summary.non_critical_failures` is non-empty. Verificable por `tests/integration/test_install_auto_remediate.py` (5 escenarios: tool faltante → fixed; hooks rotos → fixed; ambos → ambos fixed; non-fixable → reported as manual; doctor fix raises → install reports remediation_failed).
- G-5: Live progress UI: `cli_commands/core.py` reemplaza `with spinner("Installing governance framework..."):` por `with step_progress(total=len(PHASE_ORDER), description="Installing ai-engineering") as tracker:` que reporta `tracker.step("Phase X: ...")` antes de cada fase. `ToolsPhase` recibe un `progress_callback: Callable[[str], None] | None` que llama a `tracker.step("Installing tool: <name>")` por cada tool. Verificable por `tests/unit/test_install_progress.py` con mock de Status object capturando update calls.
- G-6: `cli_commands/core.py` exit-code logic: SOLO exit non-zero cuando hay critical failures O non-critical failures que auto-remediate no pudo arreglar. Tools-only failures que auto-remediate fixea → exit 0 + warning summary. Verificable por `tests/integration/test_install_exit_codes.py::test_tool_failure_remediated_exits_zero`.
- G-7: Pre-install detection banner (`render_detection`) añade qualifier `(PATH check; install may use different mechanism)` debajo de `Tools:` line — clarifica que ✓ != "install will succeed". Verificable por `tests/unit/test_render_detection.py::test_includes_path_check_qualifier`.
- G-8: `_render_pipeline_steps` añade segunda pasada que muestra remediation actions per phase fallado: "→ Auto-fix: installed gitleaks (tools mechanism)". Verificable por `tests/unit/test_render_pipeline_steps.py::test_renders_auto_remediate_actions`.
- G-9: 0 secrets, 0 vulnerabilities, 0 lint errors introducidos; pre-existing failures unchanged.
- G-10: Coverage ≥80% on new modules (`installer/auto_remediate.py`, modificaciones a `pipeline.py`).

## Non-Goals

- NG-1: Modificar el contract del `phase.execute → PhaseResult`. Sólo añadimos `critical` property; el shape de PhaseResult no cambia.
- NG-2: Auto-remediation de fases CRITICAL fallidas (e.g., GovernancePhase). Si governance falla, instalación queda rota y usuario debe diagnosticar manualmente. Auto-remediate cubre SOLO tools + hooks (los dos casos confirmados como fixable).
- NG-3: Cambiar el shape del JSON envelope de `--non-interactive` install. Auto-remediation results se añaden como nuevo campo additivo `auto_remediation: {applied: [...], failed: [...]}`. Existing fields untouched.
- NG-4: Modificar PHASE_ORDER. El orden permanece (DETECT, GOVERNANCE, IDE_CONFIG, STATE, TOOLS, HOOKS). Sólo cambia la criticality de TOOLS, no su posición.
- NG-5: Suprimir `branch-policy WARN` o `detection-current WARN` o `stack-drift WARN` de doctor en fresh install. Esos warnings son válidos como signals; mejorar su wording queda fuera de scope (defer a spec separado).
- NG-6: Migración del banner `[BREAKING] spec-101` ya emitido. Banner sigue saliendo igual (state.breaking_banner_seen flag preservado).
- NG-7: Cambiar la mecánica de `--force`. Force flag sigue bypassing idempotence; auto-remediate corre independientemente de force.
- NG-8: Animaciones complejas en progress UI. Usamos el `step_progress` existente con Status spinner — zero new dependencies.
- NG-9: PR creation in this spec. Branch consolidation final post spec-109 done.

## Decisions

### D-109-01: `critical: bool` en PhaseProtocol con default True

`PhaseProtocol` recibe nueva property `critical: bool` (default True) — preserva el comportamiento actual del pipeline (toda fase es crítica). `ToolsPhase` opta por `critical = False` explícitamente. Default True en lugar de default False fuerza al autor de cada fase a decidir conscientemente si su fase es non-critical, evitando que un nuevo phase silenciosamente degrade la robustez del pipeline.

**Rationale**: Una fase non-critical es un caso especial (sólo TOOLS hoy) que requiere justificación; el default conservador previene regresiones.

### D-109-02: Pipeline continúa post non-critical failure; critical failure rompe

`PipelineRunner.run` cambia su loop a:

```python
for phase in self._phases:
    plan = phase.plan(context)
    summary.plans.append(plan)
    if dry_run:
        summary.completed_phases.append(phase.name)
        continue
    result = phase.execute(plan, context)
    summary.results.append(result)
    verdict = phase.verify(result, context)
    summary.verdicts.append(verdict)
    if not verdict.passed:
        if getattr(phase, "critical", True):
            summary.failed_phase = phase.name
            break
        summary.non_critical_failures.append(phase.name)
        summary.completed_phases.append(phase.name)
        continue
    summary.completed_phases.append(phase.name)
```

`PipelineSummary` recibe nuevo campo `non_critical_failures: list[str] = field(default_factory=list)`.

**Rationale**: Mínima diff respecto al runner actual; preserva semantics del exit-on-critical (compatibilidad). Los completed_phases incluyen fases non-critical fallidas (porque "completaron" su intento), pero non_critical_failures permite diferenciarlas en reporting.

### D-109-03: ToolsPhase es non-critical, HooksPhase es critical

`ToolsPhase.critical = False`: una falla de instalación de tool es recuperable (auto-remediate via doctor's mechanism), y la falla NO impide que hooks se escriban (hook scripts no requieren tool durante install — sólo durante ejecución del hook que es runtime, post-install).

`HooksPhase.critical = True`: una falla de hooks (e.g., `.git/hooks/` no existe, no es git repo) es bloqueante porque el proyecto no podrá enforcer gates.

**Rationale**: El criterio de criticality es "sin esta fase exitosa, ¿puede el usuario continuar productivamente?". Tools = sí (auto-remediate o degraded gates). Hooks = no.

### D-109-04: Render pipeline steps ANTES del Exit

Mover `if not is_json_mode(): _render_pipeline_steps(summary)` desde la línea 405-406 a una posición ANTES del block `if tools_verdict is not None and not tools_verdict.passed: raise Exit(80)`. Adicionalmente, `_render_pipeline_steps` recibe `summary` con info de auto-remediation para mostrar segunda pasada.

**Rationale**: Bug obvio. La frase "see warnings above" obliga al usuario a ver los warnings — el código actual los oculta detrás del Exit. Fix de costo cero.

### D-109-05: Auto-remediate sólo TOOLS + HOOKS, en orden, post-pipeline

`auto_remediate_after_install(root, summary)` corre cuando `summary.non_critical_failures` is non-empty. Itera sobre los phases fallados y llama a:

- TOOLS: `doctor.phases.tools.fix(ctx, [check for check in tools.check(ctx) if check.status == FAIL], dry_run=False)`
- HOOKS: `doctor.phases.hooks.fix(ctx, [check for check in hooks.check(ctx) if check.status == FAIL], dry_run=False)`

Resultados se agregan a `AutoRemediateReport(fixed: list[str], failed: list[str], errors: list[str])`. Si remediate falla con excepción, captura y registra en errors.

**Rationale**: Reuso 100% del code path de doctor.fix — zero duplicación. Si doctor.fix funciona en ese caso, install lo aprovecha. Si no funciona, auto-remediate falla limpio y reporta.

### D-109-06: Exit code: 0 cuando auto-remediate cubre TODOS los non-critical failures; 80 si cualquier survived

```python
critical_failed = summary.failed_phase is not None
non_critical_unfixed = (
    bool(summary.non_critical_failures)
    and bool(remediate_report.failed)
)
if critical_failed:
    raise typer.Exit(EXIT_TOOLS_FAILED)
if non_critical_unfixed:
    raise typer.Exit(EXIT_TOOLS_FAILED)
# else: exit 0 (success or success-after-remediate)
```

**Rationale**: Honesty principle — el exit code refleja la realidad. Un tool failure que se auto-arregló no debería forzar al usuario a leer un error rojo; un tool failure que sobrevive sí. CI environments siguen viendo exit 80 cuando hay un problema real.

### D-109-07: `step_progress` reemplaza `spinner` en install path

`cli_commands/core.py` install path:

```python
with step_progress(total=len(PHASE_ORDER), description="Installing ai-engineering framework") as tracker:
    for phase_name in PHASE_ORDER:
        tracker.step(f"Phase {i+1}/{N}: {phase_label(phase_name)}")
        # phase runs (via install_with_pipeline; tracker passed in via context)
```

Pero `install_with_pipeline` actualmente abstrae el loop de phases. Decision: añadir `progress_callback: Callable[[str], None] | None = None` a `install_with_pipeline` y `PipelineRunner.run`; el runner llama `progress_callback(f"Phase {i+1}/{N}: {phase.name}")` antes de cada `phase.execute`.

`ToolsPhase.execute` adicionalmente llama `progress_callback(f"  Installing tool: {tool.name}")` en el loop de tools (sub-progress dentro de la fase).

**Rationale**: El usuario quiere ver QUÉ está pasando. Multi-step progress es estándar en CLI UX (`cli-ux.md` lo lista como reference). Cero new dependencies (`step_progress` ya existe en `cli_progress.py`).

### D-109-08: Banner pre-install añade qualifier "(PATH check)"

`installer/ui.py::render_detection` cambia:

```python
_console.print(f"  Tools (PATH):  {' | '.join(tool_lines)}")
_console.print(f"  [muted](Pipeline may install via uv tool / package manager regardless of PATH state.)[/]")
```

**Rationale**: Honesty. ✓ gitleaks en PATH NO garantiza que el install pipeline tendrá éxito (mecanismo distinto). El usuario merece saber qué significa el ✓.

## Risks

### R-109-01: Auto-remediate masks real install bugs in CI

**Risk**: Un bug genuino en TOOL_REGISTRY[name].install() podría auto-remediar exitosamente en post-pipeline (ya que el flow es idéntico), enmascarando que el primer intento falló. CI pipelines podrían dejar pasar regressions.

**Mitigation**: `--no-auto-remediate` flag (additive, default off — auto-remediate ON by default for human users). CI workflows que quieran detectar el primer-intento failure setean `--no-auto-remediate` en su `ai-eng install` step. JSON envelope reporta `auto_remediation.applied: [...]` siempre, así que CI puede assertar `len(applied) == 0` para failure-on-first-attempt detection.

### R-109-02: PipelineRunner contract change rompe consumidores externos

**Risk**: Un consumidor externo del `PipelineSummary` (ej. plugin de terceros) que dependa de `summary.failed_phase` para detectar cualquier fallo se rompería al introducir `non_critical_failures`.

**Mitigation**: `failed_phase` semantics se preservan (sigue marcando crítico); nuevo campo es additivo. Schema de `PipelineSummary.to_dict()` (si existe) extiende sin remover campos. CHANGELOG entry documenta el additive change.

### R-109-03: Live progress UI agrega ruido en CI no-TTY

**Risk**: `step_progress` ya skip-en non-TTY (chequea `console.is_terminal`), pero el `progress_callback` que pasamos al runner se llama de todos modos — overhead innecesario en CI.

**Mitigation**: Cuando `_should_show_progress() == False`, `step_progress` yields un `StepTracker(total, status=None)` cuyo `step()` es no-op. Ningún side effect en CI. Verificable por `tests/unit/test_install_progress.py::test_no_op_in_non_tty`.

### R-109-04: Auto-remediate puede agregar minutos al install si fix() es lento

**Risk**: `doctor.phases.tools.fix` llama mecanismos de instalación reales (uv tool install) que pueden tardar — agregamos esos seconds al wall time del install.

**Mitigation**: Auto-remediate sólo corre cuando `non_critical_failures` is non-empty. En el happy path (tools instalados correctamente) NO se invoca. El extra time sólo se paga cuando el usuario YA está en un mal estado, donde la alternativa es ejecutar `doctor --fix` manual igualmente.

## References

- `installer/phases/pipeline.py:202-203` — Pipeline break-on-failure (root cause #1)
- `cli_commands/core.py:381-383` — Exit before render (root cause #2)
- `cli_commands/core.py:405-406` — `_render_pipeline_steps(summary)` after Exit (unreachable on tool failure)
- `installer/phases/tools.py:700-708` — `ToolsPhase.verify` returns `passed=False` if any tool failed
- `doctor/phases/hooks.py:309-336` — Existing fix path proves auto-remediate is feasible
- `doctor/phases/tools.py:516-533` — Existing tool re-install via `run_verify` + registry
- `cli_progress.py` — `step_progress` already exists; reuse not new
- `.ai-engineering/contexts/cli-ux.md` — CLI UX conventions (color, progress, dual-output)

## Open Questions

None at spec-approval time. Implementation will surface micro-decisions (e.g., exact wording of progress messages) which the build agent resolves inline per CLI UX context.
