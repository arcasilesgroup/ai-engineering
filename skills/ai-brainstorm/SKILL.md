---
name: ai-brainstorm
description: Úsalo cuando el usuario trae una idea difusa que hay que fijar antes de investigar o planear — "handshake", "alineemos esta idea", "te explico mi visión" — y el output debe quedar capturado en un doc autocontenido que un agente investigador y uno planificador puedan ejecutar sin preguntar nada.
license: MIT
---

# ai-brainstorm — interrogación hasta entendimiento compartido (handshake)

Una pregunta a la vez hasta poder explicar la idea entera en lenguaje de 3.º de primaria, y el resultado en un doc autocontenido, listo para el investigador y el planificador. No construye, no investiga, no planea: el handshake termina en el doc.

- Protocolo completo: escucha, draft en disco, interrogación, read-back, early exit → [handshake-SKILL.md](handshake-SKILL.md)

Fuente: handshake por obra — https://obra.sh (MIT; obra/superpowers attributed by URL).

Lo que añade ai-engineering (la costura):

1. Salida fijada a `.ai-engineering/brainstorm.md` (transitorio: muere al aprobarse el contrato PARADA 1).
2. Los gaps alimentan a ai-plan (ficheros, no chat).
3. Deber de grounding §11.6: ninguna cita de archivo/API sin haberla abierto en sesión (ai-explore/ai-read-docs).
