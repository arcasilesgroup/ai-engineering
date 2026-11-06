# NOTICE.md — the ONLY truth of attribution (§11.4): author, license SPDX, source
# URL, integrated version per skill. The frontmatter of each SKILL.md carries no
# metadata block; upstreams without a license are integrated with attribution here
# while the license issue (H4) is resolved.

Format: skill — source (integrated verbatim) — author — license — URL — redistribution.

| Skill | Source (integrated verbatim) | Author | License | URL | Redistribution |
|---|---|---|---|---|---|
| ai-brainstorm | handshake + brainstorming (obra/superpowers, merged) + spec-document-reviewer-prompt | obra | MIT | https://github.com/obra/superpowers | verified |
| ai-architect | headstart (SKILL.md, agents/, references/) | headstart authors | MIT (declared in their SKILL.md; no LICENSE file in the source) | https://github.com/headstart | unresolved (declared upstream https://github.com/headstart does not resolve to this content) |
| ai-verify | graph-engineering (skills 1-standalone/2-embedded/3-chain, evals, guide) | graph-engineering authors | no license — attribution (H4) | local source | unresolved (H4: no upstream license) |
| ai-security | cloudflare/security-audit-skill (SKILL.md, 8 attack-class MDs, validate-findings.cjs, report-schema.json) | Cloudflare | MIT | https://github.com/cloudflare/security-audit-skill | verified |
| ai-write | original; `references/voice.md` adapted from i-have-adhd | ai-engineering; voice: ayghri (i-have-adhd) | Apache-2.0; voice MIT | https://github.com/arcasilesgroup/ai-engineering · voice: https://github.com/ayghri/i-have-adhd | verified |
| ai-explore | original | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering | verified |
| ai-read-docs | read-the-damn-docs | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering/tree/main/skills/ai-read-docs | verified |
| ai-debug | original | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering | verified |
| ai-note | original | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering | verified |
| ai-issue-report | original | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering | verified |
| ai-research | original | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering | verified |
| ai-visual-recap | visual-recap | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering/tree/main/skills/ai-visual-recap | verified |
| ai-audit-design | installed skill (SKILL.md, scripts/audit.mjs, references/) | community | no license — attribution (H4) | installed locally | unresolved (H4: no upstream license) |
| ai-writing-behavior | writing-agent-behavior (agentbehavior) | Braintrust + Basis | Apache-2.0 | https://github.com/braintrustdata/agentbehavior | verified |
| ai-agents-md | agents.md convention + published sample layouts | agents.md (OpenAI/Codex et al.) | MIT | https://agents.md/ · https://github.com/agentsmd/agents.md | verified |
| ai-stress-test | original | ai-engineering | Apache-2.0 | https://github.com/arcasilesgroup/ai-engineering | verified |
| src/guards/spoken-secret.ts | spoken-secret classifier ported from agit-secret-guard (supplied locally) | agit-secret-guard authors | unknown (H4) | supplied locally | unresolved (H4: license unknown) |

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

## Open H4 issues (redistribution rights unresolved — contact pending)
- graph-engineering (ai-verify): no license; attribution by README title.
- ai-audit-design (locally installed skill): no known license.
- headstart (ai-architect): the declared upstream https://github.com/headstart does not
  resolve to this content, so its declared MIT license cannot be confirmed.
- agit-secret-guard (the spoken-secret classifier in `src/guards/spoken-secret.ts`):
  supplied locally; license unknown.

Publication is refused while any row above reads `unresolved`: `scripts/release-policy.ts` names each one, and the release workflow stops before anything is built or published.

Integration follows one rule: upstream content enters verbatim, the skill is
authored for the canon on top of it, and NOTICE.md plus this table are the
queryable attribution. Lineage is maintenance information — it never appears in
a skill's name or path.
