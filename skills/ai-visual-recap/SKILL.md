---
name: ai-visual-recap
description: Úsalo al cerrar un hito — "recap this PR", "resume el cambio para review" — para convertir el diff de la rama, commit o PR en un recap visual interactivo con diffs anotados, diagramas, mapas de archivos, resúmenes de API/schema y estados de UI, antes del review línea a línea.
license: Apache-2.0
---

# ai-visual-recap — el cambio convertido en mapa (visual-recap)

Resume un diff, rama, commit o PR cuando el trabajo ya existe: ayuda al reviewer a entender la forma del cambio antes de sumergirse en el diff crudo. Recap MDX optimizado para humanos con componentes propios.

- Método completo: modos (hosted/local), qué publica, cuándo usarlo → [visual-recap-SKILL.md](visual-recap-SKILL.md)
- Modo local-files y privacidad → [references/local-files.md](references/local-files.md)
- Calidad del wireframe HTML → [references/wireframe.md](references/wireframe.md)
- Conexión y publicación → [references/connection.md](references/connection.md)

Fuente: /visual-recap de BuilderIO — https://github.com/BuilderIO/agent-native/ (Apache-2.0; agent-native.com).

Lo que añade ai-engineering (la costura):

1. Nombre canónico.
2. Gatillo: se corre al CERRAR el hito (paso 12), no a demanda.
3. Salida: `.ai-engineering/recap.html`; `ai-eng spec close` lo archiva a git y lo borra del árbol.
