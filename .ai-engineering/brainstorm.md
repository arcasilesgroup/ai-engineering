# Handshake · skill que audita y reescribe los AGENTS.md de un proyecto

Status: draft, interview in progress · 2026-09-10

## La idea en palabras llanas

(Read-back pendiente de confirmación. Texto propuesto.)

La skill que ya existe para escribir el archivo de instrucciones de un repo (AGENTS.md) aprende
la otra mitad del trabajo: entrar en un repo que ya tiene uno o varios de esos archivos,
mirarlos, decirte qué está mal y proponerte cómo dejarlos, y sólo si dices que sí, reescribirlos.
Si el repo se trabaja de una sola forma, se queda un solo archivo en la raíz. Si tiene zonas que
se trabajan distinto (paquetes con su propio test, su propio lint, sus propias reglas), se parte
la guía: el archivo de la raíz con lo común y un archivo corto por zona con sólo lo que cambia,
para que un agente sepa qué leer y qué no leer según la tarea que le toca. Por cada archivo que
se cree, se deja su espejo CLAUDE.md apuntando ahí, y si el repo ya tenía reglas de otra
herramienta que repetían lo que decía el AGENTS.md, quedan coherentes. Nada se escribe antes de
que lo apruebes.

## Por qué importa

Dos razones concretas, ambas medidas en este repo:

1. Un AGENTS.md gordo y único se carga entero en cada turno y no dice qué zona importa para la
   tarea. Un set partido dice al agente qué leer y qué no, y el archivo raíz deja de pagar el
   detalle de cada paquete.
2. Hoy nada audita un set existente: la skill sabe crear y sabe el test de forma (una toolchain
   contra varias), pero no tiene procedimiento para inspeccionar lo que ya hay, encontrar la
   duplicación padre/hijo, las líneas que el código ya dice, ni los comandos muertos.

## Para quién

El usuario que invoca la skill en un repo, propio o ajeno. El beneficiario final es el agente que
trabaja en ese repo después: menos contexto cargado y mejor ruta hacia la zona correcta.

## Qué existe hoy (hechos verificados, no recuerdos)

1. **La skill ya existe.** `skills/ai-agents-md/SKILL.md` (5.8 KB) se añadió en el commit
   `deb68d39` (2026-09-01, "feat(skills): v2 canon, marker hooks, agents.md standard, blueprint
   templates") y sigue viva. El blueprint la lista como entrada 10 del canon de 20
   (`docs/blueprint.html:892`, §11.2) y la atribuye a la convención agents.md en la tabla de
   linaje (`docs/blueprint.html:962`, §11.5). Atribución en `NOTICE.md:29`.

   Conclusión: la premisa "esto lo dijimos y no lo hiciste" es falsa para la skill en sí. Lo que
   falta es el camino de auditoría y reescritura de un set ya existente.

2. **Lo que la skill de hoy SÍ cubre**: raíz sola o raíz más anidados (test mecánico: una
   toolchain y un comando de test, archivo único; dos o más paquetes divergentes, un anidado por
   paquete con sólo el delta), las secciones que se ganan su sitio y su orden, entrevistar al
   árbol para los comandos, verificar cada comando, y el mantenimiento en sesión.

3. **Lo que la skill de hoy NO cubre** (el hueco):
   - Auditar un set que ya existe: anidados que repiten al padre, archivos desactualizados, un
     raíz gordo que pide split.
   - El procedimiento de reestructurar: qué línea se queda, cuál se mueve, cuál se borra, y cómo
     se verifica el set resultante.
   - "Dónde mirar y dónde no mirar" como criterio del reparto.

4. **El espejo CLAUDE.md es mecánico y ya está resuelto para la raíz.**
   `src/commands/init.ts:54-63` planta `CLAUDE.md` como symlink relativo (`AGENTS.md`, mismo
   directorio) y sólo si el SO rechaza el symlink escribe la línea `@AGENTS.md`. Un symlink
   relativo funciona igual en cualquier subdirectorio, así que un set anidado se espeja creando
   el mismo symlink hermano en cada carpeta. `doctor` sólo comprueba el de la raíz
   (`src/commands/doctor.ts:36-48`).

5. **Las superficies no escriben archivos de instrucciones.** `src/surfaces/surfaces.json`
   declara para cada superficie sólo settings y plugins (hooks.json, settings.json, ai-eng.ts);
   ningún adaptador escribe `.cursor/rules` ni `copilot-instructions.md`. Los importadores que
   existen de verdad son los que ya tenga el repo del usuario.

6. **El tooling sólo mira la raíz.** `src/commands/doctor.ts:26-35` comprueba el AGENTS.md de la
   raíz (≤ 80 líneas y ≥ 6 reglas, contadas con `/^\s*(?:\d+\.|-)\s+\S/gm`). Ningún archivo
   anidado se comprueba, ni la duplicación con el padre.

7. **La plantilla que planta `init`** (`templates/AGENTS.md.tpl`, 49 líneas) trae: Security, Code
   style, Build and test commands, Workflow, Architecture layers, Session hygiene, Pull requests,
   Anti-drift. El AGENTS.md de este repo es esa plantilla con los comandos rellenos (dogfooding).

8. **Este repo no necesita split.** Una sola toolchain (bun), un `package.json`, un test runner.
   Por el test de forma de la propia skill, ai-engineering es raíz sola. Partir este AGENTS.md en
   3 sería over-engineering.

9. **Cuatro references huérfanos en el canon.** `skills/ai-write/references/` tiene cinco
   archivos: `documentation-writer.md` (enlazado desde `ai-write/SKILL.md`) y cuatro que no
   enlaza nadie: `agents-md-writer.md`, `readme-writer.md`, `contributing-writer.md`,
   `security-md-writer.md`. `grep` sólo los encuentra en `src/assets.ts` (la tabla de assets
   generada). El primero duplica la doctrina de AGENTS.md que ya vive en `ai-agents-md`.

10. **Contradicción verificada entre el guard y el flujo del brainstorm.** El blueprint §21.1 y
    la skill ai-brainstorm mandan `.ai-engineering/brainstorm.md` como salida del paso 1;
    `self-protect` niega esa escritura (literales `.ai-engineering` como segmento y la ruta
    absoluta como subcadena, así que el subárbol entero queda cerrado). Comprobado ejecutando el
    guard contra esa ruta: `deny: true`. En esta sesión la escritura pasó porque el hook de la
    superficie no está armado aquí. Contradice además el comentario del propio guard y §9.3, que
    dicen que `spec.html` sólo se protege cuando su sha256 está fijado en el lock.

## Qué debe salir bien (borrador)

- Invocar la skill en un repo con un set existente produce, en primer lugar, un diagnóstico y un
  set propuesto. Sin aprobación no hay escritura.
- El set escrito tiene un dueño por archivo: el raíz con lo común, cada anidado con su delta, sin
  una línea repetida entre padre e hijo.
- Cada comando que nombra el set se ejecuta tal y como está escrito.
- Cada AGENTS.md escrito tiene su espejo coherente, y las reglas de otras herramientas que
  repetían lo que ya no está en la raíz quedan alineadas.
- El reparto se justifica por la forma del repo, no por el gusto: si el repo no tiene zonas
  divergentes, sale un archivo.

## Decisiones ya tomadas

- **Extender `ai-agents-md`, no crear skill nueva** (elegido el 2026-09-10). Una skill, dos
  caminos: crear y auditar. El canon sigue en 20; no se toca NOTICE.md, ni el blueprint
  §11.2/§11.5, ni el nombre.
- **Diagnóstico y propuesta primero, aprobación humana, y sólo entonces escribe** (elegido el
  2026-09-10).
- **Superficie de escritura: AGENTS.md más sus importadores** (elegido el 2026-09-10, con la
  aclaración del usuario): si el set se parte, cada carpeta nueva necesita su `CLAUDE.md` igual
  que la raíz, y las reglas de otras herramientas relacionadas con AGENTS.md se actualizan para
  no contradecir lo que ya no está en la raíz.
- Estándar: agents.md (https://agents.md/ y https://github.com/agentsmd/agents.md).
- Calidad: KISS, YAGNI, DRY, SOLID, TDD, Clean Code. Ni ai-slop ni over-engineering.
- La forma del canon manda: `skills/<nombre>/SKILL.md`, frontmatter de tres campos (`name` =
  carpeta, `description` con verbo de uso, `license` SPDX), inglés, sin corpus.md, sin rutas de
  máquina, sin frases de límite de tokens (gates G1 a G8 de `tests/skills.spec.ts`).

## Decisiones todavía abiertas

Cada una con la recomendación por defecto, para que el usuario sólo tenga que corregir lo que no
le encaje.

1. **Alcance del audit**: cualquier repo, gobernado por ai-eng o no. Cuando está gobernado, la
   skill aprovecha las señales que ya existen (`arch.rules.json`, `config.toml`, `doctor`); cuando
   no, se apoya sólo en el árbol. Recomendado: cualquier repo, porque la skill ya es genérica.
2. **Qué optimiza el audit**: las dos cosas con un solo criterio. Cada línea paga alquiler en cada
   turno (coste de contexto) y sólo entra si un agente la necesita para decidir dónde mirar o para
   no romper algo (navegación y no deducibilidad). El split es consecuencia, nunca objetivo.
   Recomendado.
3. **¿Toca el tooling?** Recomendado: no. `doctor` sigue comprobando sólo la raíz y el audit es
   prosa. Añadir un check de anidados es tooling nuevo para un caso que no existe todavía.
4. **El huérfano `agents-md-writer.md`** (y sus tres hermanos): recomendado borrar los cuatro, que
   no los lee nadie, y quedarse con la doctrina donde ya vive (la skill que la enlaza). Alternativa
   sin borrar nada: enlazar `agents-md-writer.md` desde `ai-agents-md` en vez de repetir su
   doctrina, y dejar los otros tres.
5. **Verificación (TDD)**: qué gate prueba que el camino de auditoría funciona. Candidato: un test
   que corra la skill sobre un repo de fixture con un set mal formado (hijo que repite al padre) y
   compruebe que el diagnóstico lo nombra. Recomendado sólo si el repo ya tiene ese tipo de
   fixture; si no, un guion desechable en la propia sesión de prueba.

## Restricciones y barandillas

- Nada de rutas de máquina en skills ni en el doc.
- La skill no escribe código del proyecto; escribe guía.
- `bun scripts/gen-assets.ts` después de tocar `skills/` o el build rompe.
- `bun test tests/skills.spec.ts` es el gate del canon.
- El AGENTS.md que se reescribe es prosa que posee el equipo: se edita, nunca se pisa sin verlo.

## Fuera de alcance

- Crear una skill nueva (descartado).
- Tocar `doctor` o cualquier otro código del binario (recomendado, pendiente de confirmar).
- Reescribir la documentación humana del repo (README, wiki): eso es de ai-write.

## Preguntas abiertas para investigación

Ninguna todavía.

## Notas de traspaso

- La skill vive en `skills/ai-agents-md/SKILL.md`; si el procedimiento se alarga, va a
  `skills/ai-agents-md/references/` y el SKILL.md lo enlaza (así lo hace ai-security).
- `templates/AGENTS.md.tpl` y el `AGENTS.md` de la raíz de este repo son el mismo texto: si cambia
  la disciplina de secciones, cambian los dos a la vez.
- Tras tocar `skills/`, `bun scripts/gen-assets.ts` y luego `bun test tests/skills.spec.ts`.
