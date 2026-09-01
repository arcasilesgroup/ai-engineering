# NOTICE.md — the ONLY truth of attribution (§11.4): author, license SPDX, source
# URL, integrated version per skill. The frontmatter of each SKILL.md carries no
# metadata block; upstreams without a license are integrated with attribution here
# while the license issue (H4) is resolved.

Format: skill — source (integrated verbatim) — author — license — URL.

| Skill | Source (integrated verbatim) | Author | License | URL |
|---|---|---|---|---|
| ai-proof | unlazy v2.1.0 (SKILL.md, references/, scripts/, templates/) | Leonxlnx | MIT | https://github.com/Leonxlnx/unlazy |
| ai-brainstorm | handshake + brainstorming (obra/superpowers, merged) + spec-document-reviewer-prompt | obra | MIT | https://github.com/obra/superpowers |
| ai-plan | wayfinder (SKILL.md, agents/, commands/) | Matt Pocock (mattpocock) | MIT | https://github.com/mattpocock/wayfinder |
| ai-goal | Loop-Engineering skills (new-feature, goal-writer, feature-batch) | Loop-Engineering authors | attributed — no license declared upstream (H4) | local source ~/Downloads/Loop-Engineering |
| ai-architect | headstart (SKILL.md, agents/, references/) | headstart authors | MIT (declared in their SKILL.md; no LICENSE file in the source) | https://github.com/headstart |
| ai-design | design-orchestrator (claude-design-skills) | claude-design-skills authors | no license — attribution (H4) | https://github.com/claude-design-skills |
| ai-verify | graph-engineering (skills 1-standalone/2-embedded/3-chain, evals, guide) | graph-engineering authors | no license — attribution (H4) | local source ~/Downloads/graph-engineering |
| ai-security | cloudflare/security-audit-skill (SKILL.md, 8 attack-class MDs, validate-findings.cjs, report-schema.json) | Cloudflare | MIT | https://github.com/cloudflare/security-audit-skill |
| ai-write | v1 original | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering |
| ai-explore | v1 original | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering |
| ai-read-docs | read-the-damn-docs (~/repos/skills) | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/skills |
| ai-rtk | rtk SKILL.md (thin layer over an external binary) | autometa / Hermes Agent | MIT | https://github.com/autometa/rtk |
| ai-debug | v1 original | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering |
| ai-note | v1 original | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering |
| ai-issue-report | v1 ai-report (renamed; the oracle did not carry ai-issue-report) | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering |
| ai-research | v1 original | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering |
| ai-visual-recap | visual-recap (~/repos/skills) | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/skills |
| ai-design-audit | installed skill (SKILL.md, scripts/audit.mjs, references/) | community | no license — attribution (H4) | local source ~/.claude/skills/ai-design-audit |
| ai-writing-behavior | writing-agent-behavior (agentbehavior) | Braintrust + Basis | Apache-2.0 | https://github.com/braintrustdata/agentbehavior |
| ai-agents-md | agents.md convention + published sample layouts | agents.md (OpenAI/Codex et al.) | MIT | https://agents.md/ · https://github.com/agentsmd/agents.md |

## Open H4 issues (upstreams without a license — contact pending)
- Loop-Engineering (ai-goal): no LICENSE, no author/URL in the tree.
- claude-design-skills/design-orchestrator (ai-design): no license in the repo.
- graph-engineering (ai-verify): no license; attribution by README title.
- ai-design-audit (locally installed skill): no known license.

Integration follows rule §11.1: source content enters verbatim; the thin layer
(SKILL.md, ≤60 lines) is the only part of ours; NOTICE.md and this table are the
queryable attribution.
