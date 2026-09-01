# NOTICE.md — the ONLY truth of attribution (§11.4): author, license SPDX, source
# URL, integrated version per skill. The frontmatter of each SKILL.md carries no
# metadata block; upstreams without a license are integrated with attribution here
# while the license issue (H4) is resolved.

Format: skill — author — license — source — pinned version (sha256 in ai-eng.lock).

| Skill | Fuente (íntegra) | Autor | Licencia | URL |
|---|---|---|---|---|
| ai-proof | unlazy v2.1.0 (SKILL.md, references/, scripts/, templates/) | Leonxlnx | MIT | https://github.com/Leonxlnx/unlazy |
| ai-brainstorm | handshake SKILL.md | handshake authors; obra/superpowers patterns attributed by URL | MIT | https://github.com/obra/superpowers |
| ai-plan | wayfinder (SKILL.md, agents/, commands/) | Matt Pocock (mattpocock) | MIT | https://github.com/mattpocock/wayfinder |
| ai-goal | Loop-Engineering skills (new-feature, goal-writer, feature-batch) | Loop-Engineering authors | attributed — sin licencia declarada en la fuente (H4) | fuente local ~/Downloads/Loop-Engineering |
| ai-architect | headstart (SKILL.md, agents/, references/) | headstart authors | MIT (declarado en su SKILL.md; sin archivo LICENSE en la fuente) | https://github.com/headstart |
| ai-design | design-orchestrator (claude-design-skills) | claude-design-skills authors | sin licencia — atribución (H4) | https://github.com/claude-design-skills |
| ai-verify | graph-engineering (skills 1-standalone/2-embedded/3-chain, evals, guide) | graph-engineering authors | sin licencia — atribución (H4) | fuente local ~/Downloads/graph-engineering |
| ai-security | cloudflare/security-audit-skill (SKILL.md, 8 attack-class MDs, validate-findings.cjs, report-schema.json) | Cloudflare | MIT | https://github.com/cloudflare/security-audit-skill |
| ai-write | v1 propio | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering |
| ai-explore | v1 propio | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering |
| ai-read-docs | read-the-damn-docs (~/repos/skills) | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/skills |
| ai-rtk | rtk SKILL.md (capa fina sobre binario externo) | autometa / Hermes Agent | MIT | https://github.com/autometa/rtk |
| ai-debug | v1 propio | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering |
| ai-note | v1 propio | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering |
| ai-issue-report | v1 ai-report (renombrado; el oracle no traía ai-issue-report) | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering |
| ai-research | v1 propio | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering |
| ai-visual-recap | visual-recap (~/repos/skills) | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/skills |
| ai-design-audit | skill instalado (SKILL.md, scripts/audit.mjs, references/) | comunidad | sin licencia — atribución (H4) | fuente local ~/.claude/skills/ai-design-audit |
| ai-writing-behavior | writing-agent-behavior (agentbehavior) | Braintrust + Basis | Apache-2.0 | https://github.com/braintrustdata/agentbehavior |

## Issues H4 abiertos (upstreams sin licencia — contacto pendiente)
- Loop-Engineering (ai-goal): sin LICENSE ni author/URL en el árbol.
- claude-design-skills/design-orchestrator (ai-design): sin licencia en el repo.
- graph-engineering (ai-verify): sin licencia; atribución por título del README.
- ai-design-audit (skill instalado local): sin licencia conocida.

La integración sigue la regla §11.1: el contenido fuente entra íntegro; la capa fina
(SKILL.md, ≤60 líneas) es la única parte nuestra; NOTICE.md y esta tabla son la
atribución consultable.
