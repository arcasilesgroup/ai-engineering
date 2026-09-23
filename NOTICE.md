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
| ai-goal | Loop-Engineering skills (new-feature, goal-writer, feature-batch) | Loop-Engineering authors | attributed — no license declared upstream (H4) | local source |
| ai-architect | headstart (SKILL.md, agents/, references/) | headstart authors | MIT (declared in their SKILL.md; no LICENSE file in the source) | https://github.com/headstart |
| ai-design | design-orchestrator (claude-design-skills) | claude-design-skills authors | no license — attribution (H4) | https://github.com/claude-design-skills |
| ai-verify | graph-engineering (skills 1-standalone/2-embedded/3-chain, evals, guide) | graph-engineering authors | no license — attribution (H4) | local source |
| ai-security | cloudflare/security-audit-skill (SKILL.md, 8 attack-class MDs, validate-findings.cjs, report-schema.json) | Cloudflare | MIT | https://github.com/cloudflare/security-audit-skill |
| ai-write | original | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering |
| ai-explore | original | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering |
| ai-read-docs | read-the-damn-docs | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/skills |
| ai-debug | original | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering |
| ai-note | original | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering |
| ai-issue-report | original | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering |
| ai-research | original | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering |
| ai-visual-recap | visual-recap | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/skills |
| ai-audit-design | installed skill (SKILL.md, scripts/audit.mjs, references/) | community | no license — attribution (H4) | installed locally |
| ai-writing-behavior | writing-agent-behavior (agentbehavior) | Braintrust + Basis | Apache-2.0 | https://github.com/braintrustdata/agentbehavior |
| ai-agents-md | agents.md convention + published sample layouts | agents.md (OpenAI/Codex et al.) | MIT | https://agents.md/ · https://github.com/agentsmd/agents.md |
| ai-stress-test | original | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering |

## The brand (§22)

The visual identity is neither a skill nor bundled content: it is a palette.
`brand/tokens.json` copies the colour families **verbatim** from
[LeafyGreen UI](https://github.com/mongodb/leafygreen-ui/blob/main/packages/palette/src/palette.ts)
(`packages/palette/src/palette.ts`) — © MongoDB, Inc., Apache-2.0.

What is adopted is the visual grammar: the palette, the type treatment, the geometry and
the component shapes. The identity is not. No MongoDB logo, wordmark, leaf glyph or
stylized name appears anywhere in this repository, and none may be added — those are
trademarks and Apache-2.0 §7 grants no rights to them. MongoDB's own typefaces (Euclid
Circular A, MongoDB Value Serif) are commercial and are not shipped; Archivo stands in
for them, and that substitution is named in the landing site's `DESIGN.md` rather than
left for a reader to discover.

## Open H4 issues (upstreams without a license — contact pending)
- Loop-Engineering (ai-goal): no LICENSE, no author/URL in the tree.
- claude-design-skills/design-orchestrator (ai-design): no license in the repo.
- graph-engineering (ai-verify): no license; attribution by README title.
- ai-audit-design (locally installed skill): no known license.

Integration follows one rule: upstream content enters verbatim, the skill is
authored for the canon on top of it, and NOTICE.md plus this table are the
queryable attribution. Lineage is maintenance information — it never appears in
a skill's name or path.
