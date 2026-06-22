---
title: "Mintlify Documentation Portal — External Docs Site for ai-engineering"
status: draft
audience: /ai-brainstorm
branch: "TBD — minted at spec promotion (live spec slot currently held by spec-170; do not clobber)"
length_estimate: "~340 lines"
authoring_style: "Staff Principal Architect — evidence-anchored, SSOT-disciplined, fail-loud"
principles_required: [KISS, YAGNI, DRY, SDD, TDD, clean-code]
delivery_mode: "Multi-milestone single spec / hard migration where files move / Conventional Commits"
mantra: "A stranger lands on the portal, installs in 60 seconds, and understands the governed flow in five minutes. The repo stays the single source of truth; the portal is a beautiful derived view."
---

> **READ FIRST.** This brief is structured intake for `/ai-brainstorm`. It proposes building the first external documentation portal for `ai-engineering` on Mintlify. Every current-state claim cites `file:line`. No implementation begins until this brief is promoted to `spec-NNN` and approved.

---

## 1. Vision

`ai-engineering` ships 54 skills, 9 agents, 6 IDE surfaces, a governed CLI, and a constitution-grade rulebook — and its entire public-facing documentation is a 165-line README (`README.md:30`, hard-capped at 170 lines by `tests/unit/docs/test_readme_brand_contract.py:25`). Everything deeper lives in-repo for operators and agents, not for evaluating humans. A Mintlify portal gives the project a real front door: quickstart-first information architecture, generated reference pages for every skill and agent, AI-native consumption (auto `llms.txt`, per-page raw Markdown, an auto-generated MCP server at `/mcp`), and zero-ops managed hosting on a free tier that includes a custom domain and PR preview deployments. The repo remains the single source of truth per CONSTITUTION Prohibition 8; the portal is an explicitly labelled derived surface with a rebuild path.

## 2. Scope Boundary

### In scope

| Item | Reason |
|------|--------|
| New Mintlify docs root in this repo (monorepo subdirectory) with `docs.json` | Portal foundation; Mintlify supports monorepo subdirectory sync natively |
| Authored content wave 1: Get Started, Concepts, per-IDE Guides | The portal's human value; nothing comparable exists today |
| Generated reference: 54 skill pages + 9 agent pages + CLI reference | DRY §10.4 — derive from `SKILL.md` frontmatter and `cli-reference.md`, never hand-copy |
| Generator script + parity test (portal counts == registry counts) | TDD §10.5 — drift between portal and registry must fail CI |
| Mintlify GitHub App wiring, production-branch deploy, PR previews | Deployment path |
| `mint broken-links` / `mint validate` in CI (npx, no new Action) | Quality gate without tripping the repo Actions allowlist |
| `pyproject.toml` `[project.urls]` block + README Documentation link | Today no Homepage/Documentation/Repository URLs exist (`pyproject.toml:1-21`) |
| CHANGELOG entry + brand-voice compliance (no emoji, `{ai} engineering` naming) | `.ai-engineering/reference/brand-voice.md:38`, `:16` |

### Explicitly NOT in scope

| Item | Why deferred |
|------|--------------|
| Spanish (or any) localization via `navigation.languages` | Manual-translation cost; CONSTITUTION fixes docs language to English (`CONSTITUTION.md:167-171`); revisit post-launch |
| Versioned docs (`navigation.versions`) | YAGNI until two majors coexist |
| Rewriting/moving `docs/` operator runbooks into the portal | They are canonical operator references cited by CONSTITUTION/CLAUDE.md; moving them is pointer churn for zero reader value now |
| Reworking the `/ai-docs` `docs-portal` handler (external-repo push flow) | Handler assumes a separate repo (`.claude/skills/ai-docs/handlers/docs-portal.md:1-11`); in-repo portal rides the normal PR flow; handler redesign is its own follow-up |
| API/OpenAPI playground | No HTTP API exists |
| Marketing site / landing page | Portal is documentation; marketing is `/ai-marketing` territory |

## 3. Diagnostic Snapshot

Current state, evidence-cited:

1. **No portal tooling exists.** Zero hits for `mkdocs.yml`, `docusaurus.config.*`, `mint.json`, `docs.json`, sphinx `conf.py`, readthedocs config anywhere in the tree. Prior specs explicitly deferred portal work three times: `.ai-engineering/specs/archive/spec-132-cli-ux-overhaul/spec.md:70` ("No documentation portal redesign"), `spec-140-less-is-more-quality-engine/spec.md:42`, `spec-144-readme-rewrite-and-branch-cleanup-rename/spec.md:38`.
2. **README is the only public doc and is capped.** 165 lines today; `tests/unit/docs/test_readme_brand_contract.py:25` asserts `<= 170`. The stat line `54 skills · 9 agents · 6 surfaces · 1 governed flow` (`README.md:30`) is the deepest public inventory of the surface area.
3. **Deep docs exist but are repo-internal.** `docs/` holds four operator runbooks (`docs/persistence-doctrine.md:1-6`, `docs/ci-branch-protection.md:1-6`, `docs/supply-chain-control-matrix.md:1-8`, `docs/cache-cleanup-runbook.md:1-9`) plus two encrypted `.pen` design files; `.ai-engineering/reference/` holds 19 reference documents (principles, gate-policy, cli-reference, brand-voice, et al.).
4. **The framework already anticipates a portal.** `/ai-docs` declares a `docs-portal` handler gated on `documentation.external_portal.enabled` (`.claude/skills/ai-docs/SKILL.md:43`), which is asserted `False` today (`tests/unit/config/test_manifest.py:286-289`). The handler models an *external repo* push flow (`.claude/skills/ai-docs/handlers/docs-portal.md:1-11`) — not the in-repo monorepo shape this brief proposes.
5. **Skill/agent inventory is machine-assertable.** `tests/unit/config/test_manifest.py:331` pins `skills.total == 54`; `:362` pins `agents.total == 9`. A generated reference can be parity-tested against the same registry.
6. **Package metadata has no documentation URL.** `pyproject.toml:1-21` carries no `[project.urls]` block at all — PyPI shows no Homepage, Documentation, or Repository link for `ai-engineering 0.10.1` (`pyproject.toml:2-3`).
7. **CI already has a lightweight docs lane.** `docs-gate` ("Docs Floor") runs `tests/docs`, `ai-eng check`, and a secret scan when docs or code change (`.github/workflows/ci-check.yml:98-107`); `docs/**` is deliberately not path-ignored (`ci-check.yml:12-14`). New checks must respect the repo Actions allowlist (only vetted actions run; npm CLIs via `npx` are safe).
8. **Brand and language constraints are binding.** English for all docs (`CONSTITUTION.md:167-171`); no PII/operator names/machine paths in committed files including docs (`CONSTITUTION.md:74-77`); no emoji, `{ai} engineering` in prose vs `ai-engineering` for identifiers (`.ai-engineering/reference/brand-voice.md:38`, `:16`).
9. **Mintlify external facts** (full citations in §12): `docs.json` replaced `mint.json` (Feb 2025); monorepo subdirectory sync is first-class via the GitHub App; the free Starter tier includes custom domain, PR preview deployments, and 5,000 AI credits/month; an OSS Program grants 10,250 credits/month to MIT-licensed non-corporate projects; `llms.txt`/`llms-full.txt` and an MCP server at `<docs-url>/mcp` are auto-generated with zero config; CLI is `mint` on npm (`mint new`, `mint dev`, `mint broken-links`, `mint validate`, Node >= 20.17); Anthropic and Cursor docs run on Mintlify.

## 4. Architecture

**Shape: in-repo monorepo subdirectory, new top-level directory `docs-portal/`** (name final at spec time — see Open Decision D2):

```
docs-portal/
  docs.json              # navigation, theme, colors per brand-voice
  index.mdx              # landing: what ai-engineering is, stat line, CTA
  get-started/
    installation.mdx     # CodeGroup: uv / pipx / pip (mirrors README install)
    quickstart.mdx       # Steps: install -> ai-eng install -> /ai-start
    governed-flow.mdx    # the canonical chain, Mermaid
  concepts/
    constitution.mdx     # governance model, hard rules, prohibitions
    skills-and-agents.mdx
    hooks.mdx            # 11 canonical events, integrity pinning
    quality-gates.mdx    # gate-policy summary, fail-open/closed doctrine
    persistence.mdx      # three-tier files-only model (links canonical doctrine)
  guides/
    ide-setup.mdx        # Tabs: Claude Code / Copilot / Codex / Antigravity / OpenCode / Cursor
    risk-acceptance.mdx
    upgrading.mdx
  reference/
    cli.mdx              # derived from .ai-engineering/reference/cli-reference.md
    skills/              # 54 GENERATED pages (one per SKILL.md)
    agents/              # 9 GENERATED pages
    environment.mdx      # runtime tunables (AIENG_*)
  changelog.mdx          # Update components, top slice of CHANGELOG.md
  logo/  favicon.svg  snippets/
```

Module boundaries:

- **Authored pages** are new prose, written once for an external audience. They may *summarize* canonical in-repo docs and must link to them on GitHub; they never fork normative content (SSOT, Prohibition 8 — `CONSTITUTION.md:84-88` area).
- **Generated pages** (`reference/skills/`, `reference/agents/`, `reference/cli.mdx`) are derived caches: produced by a new `tools/docs_portal/generate_reference.py` reading `.claude/skills/*/SKILL.md` frontmatter (name, description, argument-hint) and `.claude/agents/ai-*.md`. Each generated file carries a `<!-- GENERATED — rebuild: python tools/docs_portal/generate_reference.py -->` header. A new test (`tests/docs/test_portal_reference_parity.py`) asserts generated page count == registry counts pinned at `tests/unit/config/test_manifest.py:331,362` and that regeneration is idempotent (no diff on clean tree).
- **Deployment** is Mintlify cloud via the GitHub App: monorepo path set to `/docs-portal`, production branch `main`, PR preview deployments on. No self-hosting exists (Mintlify is proprietary); portability is preserved because all content is MDX + `docs.json` in-repo.
- **CI**: extend the existing `docs-gate` lane (`.github/workflows/ci-check.yml:98-107`) with an `npx mint broken-links` + `npx mint validate` step (Node already provisioned on runners; no new third-party Action, so the Actions allowlist is untouched).
- **AI surface for free**: hosted portal auto-serves `/llms.txt`, `/llms-full.txt`, per-page `.md`, and an MCP server at `/mcp` — no configuration or code in this repo.

## 5. Evidence Catalog

| # | Citation | Fact |
|---|----------|------|
| 1 | `tests/unit/docs/test_readme_brand_contract.py:25` | README hard cap `<= 170` lines |
| 2 | `README.md:30` | Stat line: 54 skills, 9 agents, 6 surfaces, 1 governed flow |
| 3 | `README.md:113` | Canonical chain string asserted by brand-contract test |
| 4 | `tests/unit/config/test_manifest.py:331` | `skills.total == 54` pinned |
| 5 | `tests/unit/config/test_manifest.py:362` | `agents.total == 9` pinned |
| 6 | `tests/unit/config/test_manifest.py:286-289` | `documentation.external_portal.enabled is False` today |
| 7 | `.claude/skills/ai-docs/SKILL.md:43` | `docs-portal` handler gated on that manifest flag |
| 8 | `.claude/skills/ai-docs/handlers/docs-portal.md:1-11` | Handler models external-repo flow; skips silently when disabled |
| 9 | `pyproject.toml:1-21` | No `[project.urls]` block — no Documentation link on PyPI |
| 10 | `pyproject.toml:2-3` | `name = "ai-engineering"`, `version = "0.10.1"` |
| 11 | `.github/workflows/ci-check.yml:98-107` | `docs-gate` lightweight CI lane (tests/docs + ai-eng check + gitleaks) |
| 12 | `.github/workflows/ci-check.yml:12-14` | `docs/**` intentionally not path-ignored |
| 13 | `CONSTITUTION.md:167-171` | Docs language: English |
| 14 | `CONSTITUTION.md:74-77` | No PII / operator names / machine paths in docs |
| 15 | `.ai-engineering/reference/brand-voice.md:38` | No-emoji rule |
| 16 | `.ai-engineering/reference/brand-voice.md:16` | `{ai} engineering` prose vs `ai-engineering` identifier naming |
| 17 | `docs/persistence-doctrine.md:1-6` | Canonical operator doctrine stays in-repo (linked, not forked) |
| 18 | `.ai-engineering/solution-intent.md:233-285` | Six-layer module map — source for the architecture Mermaid page |
| 19 | `.ai-engineering/specs/archive/spec-132-cli-ux-overhaul/spec.md:70` | Portal work explicitly deferred by prior specs (precedent) |
| 20 | `CHANGELOG.md:5-6` | Keep-a-Changelog + SemVer — source format for `changelog.mdx` slice |

## 6. Roadmap

| Milestone | Deliverable | Acceptance gate |
|-----------|-------------|-----------------|
| **M0 — Scaffold** | `mint new` scaffold under `docs-portal/`; `docs.json` with theme/colors/logo per brand-voice; navigation skeleton (2 tabs: Documentation, Reference) | `npx mint dev` renders locally; `npx mint validate` clean; zero emoji; naming per brand-voice |
| **M1 — Authored content** | Get Started (3 pages), Concepts (5), Guides (3), landing `index.mdx` | `npx mint broken-links` clean; every normative claim links to canonical in-repo doc; English; no PII/machine paths |
| **M2 — Generated reference** | `tools/docs_portal/generate_reference.py`; 54 skill + 9 agent pages; `reference/cli.mdx`; `environment.mdx`; parity test | `tests/docs/test_portal_reference_parity.py` green: counts match registry, regeneration idempotent |
| **M3 — Deploy** | Mintlify GitHub App installed; monorepo path `/docs-portal`; production branch `main`; custom domain (D1); PR preview deployments verified | Portal live over HTTPS; `/llms.txt` and `/mcp` respond; preview URL appears on a test PR |
| **M4 — Integration** | `[project.urls]` (Homepage/Documentation/Repository/Changelog) in `pyproject.toml`; README Documentation link within the 170-line cap; `npx mint broken-links && npx mint validate` step in `docs-gate`; CHANGELOG entry | Full `tests/unit/docs` + `tests/docs` green locally and in CI; install-smoke unaffected; docs-gate runtime stays within budget |
| **M5 — Post-launch (deferred)** | OSS Program application (10,250 AI credits/mo); Spanish localization; versioned docs; `/ai-docs` portal-handler redesign for the in-repo shape | Separate brief/spec per item |

Estimated shape: M0-M2 are pure-repo waves suited to the canonical chain; M3 requires operator dashboard actions (GitHub App install, DNS) that the agent cannot perform — the spec must mark them as operator tasks.

## 7. Definition of Done

1. Portal live on Mintlify cloud, served over HTTPS at the chosen domain, auto-deploying from `main`.
2. Navigation contains >= 11 authored pages and exactly 54 generated skill pages + 9 generated agent pages, parity-tested against the registry.
3. `npx mint validate` and `npx mint broken-links` pass in CI on every PR touching `docs-portal/**`.
4. Regeneration is idempotent: running the generator on a clean tree produces zero diff.
5. `/llms.txt`, `/llms-full.txt`, and `/mcp` respond on the live portal.
6. PyPI page for the next release shows Documentation/Homepage/Repository links.
7. README links to the portal and remains <= 170 lines with all existing brand-contract assertions green.
8. Zero emoji, zero PII, zero machine paths anywhere under `docs-portal/` (gitleaks + docs-gate green).
9. CHANGELOG documents the portal under the release that ships it.

## 8. Quality Stamps

- **KISS §10.1** — one new directory, one config file, one generator script; no new third-party GitHub Actions; hosting fully managed.
- **YAGNI §10.2** — no versioning, no i18n, no API playground until demanded; portal handler redesign deferred.
- **DRY §10.4** — reference pages generated from `SKILL.md` frontmatter, never hand-written twice; install instructions sourced from the same commands README asserts.
- **TDD §10.5** — parity test and CI link/validate gates land in the same wave as the content they protect.
- **SDD §10.6** — this brief precedes the spec; the spec precedes any scaffold.
- **Clean Code §10.7** — brand-voice contract applied to every page.
- **Contracts honoured**: CONSTITUTION Prohibitions 5 (anonymity) and 8 (SSOT per datum); Hard Rule 4 (no machine paths); brand-voice no-emoji; Actions-allowlist constraint; README 170-line cap.

## 9. Open Decisions

| ID | Decision | Options | Lean |
|----|----------|---------|------|
| D1 | Custom domain | (a) `docs.<org-domain>`; (b) default `*.mintlify.app` subdomain at launch, domain later | (b) launch unblocked; domain is a DNS-only follow-up |
| D2 | Portal directory name | (a) `docs-portal/`; (b) `website/`; (c) reuse `docs/` as Mintlify root | (a) — reusing `docs/` collides with canonical runbooks + `.pen` binaries and churns CONSTITUTION/CLAUDE.md pointers |
| D3 | Generated-page granularity | (a) one MDX per skill (54 files); (b) grouped category pages with anchors | (a) for deep-linking and llms.txt quality; CardGroup index on top |
| D4 | Changelog strategy | (a) generated slice of CHANGELOG.md top N releases; (b) link-only to GitHub | (a) with generator support, else (b) at M1 |
| D5 | OSS Program eligibility | Program requires "not owned/primarily maintained by a for-profit company" — verify arcasilesgroup status before applying | Verify at M5; free Starter tier suffices regardless |
| D6 | `documentation.external_portal.enabled` semantics | Flag models an external-repo flow; in-repo portal arguably keeps it `false` | Keep `false`; redesign handler in M5 follow-up |
| D7 | Theme/palette | Map Arcasiles dark-IDE palette (per brand assets in `docs/design.pen`) to `docs.json` colors | Extract at M0 with operator input |

## 10. Migration

No existing portal exists, so there is no migration in the rename/delete sense. Constraints that look like migration but are not: `docs/` runbooks stay canonical and untouched (linked from the portal, never copied); `mint.json` never existed here so the `docs.json`-only world is the starting point. The only hard changes: `pyproject.toml` gains `[project.urls]` (pure addition), README swaps content within its cap (hard edit, no shim), and CI `docs-gate` gains a step (additive). If a future spec moves runbooks into the portal, that is a hard move with pointer updates per CONSTITUTION §3 — explicitly out of scope here.

## 11. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Vendor lock-in (Mintlify proprietary, no self-host) | Medium | Medium | All content is MDX + `docs.json` in-repo; MkDocs/Docusaurus fallback is a rendering swap, not a content rewrite |
| Free-tier terms change (pricing restructured as recently as 2025-2026) | Medium | Low-Medium | Same portability argument; OSS Program as headroom; no paid features load-bearing in scope |
| Generated reference drifts from registry | Medium | Medium | Parity test in `tests/docs/` fails CI on count or idempotency drift |
| README brand-contract test breaks on link edit | Medium | Low | `tests/docs` + `tests/unit/docs` run locally before push (known CI-only blind spot) |
| Actions allowlist startup_failure from a new action | Low | High | No new Actions; `npx mint` CLI inside existing job steps only |
| docs-gate runtime budget blown by `mint` install | Medium | Low | Cache npm or pin `mint` version; measure in M4 gate |
| Secret/PII leak in authored pages | Low | High | Existing gitleaks + docs-gate already scan `docs-portal/**` (docs paths not ignored) |
| Operator-dependent steps stall delivery (GitHub App, DNS) | Medium | Medium | M3 isolates operator tasks; M0-M2 deliverable without them via `mint dev` |

## 12. References

1. Mintlify docs.json settings + minimal example — https://www.mintlify.com/docs/organize/settings
2. Navigation (tabs/groups/versions/languages) — https://www.mintlify.com/docs/organize/navigation
3. GitHub App deploy + PR previews — https://www.mintlify.com/docs/deploy/github
4. Monorepo subdirectory setup — https://www.mintlify.com/docs/deploy/monorepo
5. CLI install, `mint new`/`mint dev` (Node >= 20.17) — https://www.mintlify.com/docs/installation
6. CI validation (`mint broken-links`, `mint validate`, hosted checks) — https://www.mintlify.com/docs/deploy/ci
7. Pricing (Starter $0: custom domain, previews, 5,000 AI credits/mo) — https://www.mintlify.com/pricing
8. OSS Program (10,250 AI credits/mo) — https://www.mintlify.com/oss-program
9. llms.txt / llms-full.txt auto-generation — https://www.mintlify.com/docs/ai/llmstxt
10. Auto-generated MCP server at `/mcp` — https://www.mintlify.com/docs/ai/model-context-protocol
11. MDX components catalog — https://www.mintlify.com/docs/components
12. Internationalization (manual translation, 30+ languages) — https://www.mintlify.com/docs/guides/internationalization
13. Developer-docs IA guidance — https://www.mintlify.com/docs/guides/developer-documentation
14. Customers (Anthropic, Cursor, Perplexity prior art) — https://www.mintlify.com/customers
15. mint.json -> docs.json migration rationale — https://www.mintlify.com/blog/refactoring-mint-json-into-docs-json
16. Custom domain setup — https://www.mintlify.com/docs/customize/custom-domain
17. Migration tooling (`@mintlify/scraping`, Markdown reuse) — https://www.mintlify.com/docs/migration

## 13. Glossary

- **docs.json** — Mintlify's single configuration file (theme, colors, navigation); successor of `mint.json` since February 2025.
- **Monorepo path** — Mintlify Git setting pointing the GitHub App at a subdirectory (e.g. `/docs-portal`) instead of the repo root.
- **llms.txt / llms-full.txt** — auto-generated AI-consumption indexes served at the portal root; `llms-full.txt` is the entire docs corpus in one file.
- **Portal MCP server** — Model Context Protocol endpoint auto-hosted at `<docs-url>/mcp`, exposing docs search/read tools to AI clients.
- **Derived cache** — per CONSTITUTION Prohibition 8, a generated artifact (here: reference MDX pages) explicitly labelled with its rebuild command; never hand-edited.
- **Starter tier** — Mintlify's $0 plan: hosting, custom domain, PR preview deployments, 5,000 AI credits/month.
- **docs-gate** — the existing lightweight CI lane ("Docs Floor") that runs docs tests, `ai-eng check`, and secret scanning.

## 14. Acceptance

- [ ] `docs-portal/` exists with valid `docs.json`; `npx mint validate` passes.
- [ ] >= 11 authored pages (Get Started, Concepts, Guides, landing) in English, brand-voice compliant, zero emoji.
- [ ] 54 generated skill pages + 9 generated agent pages; parity test green; regeneration idempotent.
- [ ] `npx mint broken-links` clean in CI on `docs-portal/**` changes.
- [ ] Portal live on Mintlify cloud, auto-deploying from `main`, PR previews working.
- [ ] `/llms.txt` and `/mcp` respond on the live portal.
- [ ] `pyproject.toml` `[project.urls]` block present; PyPI shows the links at next release.
- [ ] README links the portal; brand-contract test green (<= 170 lines).
- [ ] CHANGELOG entry recorded; no PII/machine paths/secrets under `docs-portal/` (docs-gate green).
- [ ] Open Decisions D1-D7 resolved or explicitly carried into the spec.
