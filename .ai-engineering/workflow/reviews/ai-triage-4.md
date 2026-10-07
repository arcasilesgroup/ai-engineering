# Checkpoint 4 · Resolve Azure targets before reading

Goal: A deterministic resolver chooses an explicit URL's provider and scope or a unique repository remote, and returns an ambiguity that must be answered before any Azure request.

Acceptance:
- Explicit URL takes precedence over repository remotes and fixes provider/scope.
- Without a URL, only an unambiguous repository remote supplies provider/project; unresolved provider, project, team, board, or backlog asks before reading.
- Azure DevOps Services only; no active `az` defaults or persisted config scope.
- Ambiguity and unsupported targets produce zero reads; a selected explicit scope is the only scope passed to the fake adapter.

Changed files:
- `skills/ai-triage/SKILL.md`
- `skills/ai-triage/scripts/resolve-target.mjs`
- `skills/ai-triage/scripts/resolve-target.d.mts`
- `tests/triage-routing.unit.spec.ts`
- `tests/triage-routing.integration.spec.ts`

Verify:
- `bun test tests/triage-routing.unit.spec.ts`
- `bun test tests/triage-routing.integration.spec.ts`
- `bun test tests/triage-github.spec.ts`
- `bun run typecheck`
- `bun run lint`

## Round 1 review
- **F1 · P1 — `resolve-target.mjs:78-80`:** `parts.indexOf("t")` can mistake an organization, project, or team literally named `t` for the route marker. For `https://dev.azure.com/org/t/_boards/board/t/team/backlogs/Stories`, the inferred team becomes `_boards`; resolving with a supplied board/backlog can then pass the wrong team to the reader. Match `t` only in its valid route position and test marker-name collisions.
- **F2 · P2 — `resolve-target.mjs:133-165`:** A valid Azure DevOps Services SSH remote (`git@ssh.dev.azure.com:v3/org/project/repo`) is not recognized: SCP parsing is GitHub-only and the Azure URL branch accepts HTTPS only. With no explicit URL, this unique remote incorrectly asks for a provider instead of supplying provider/project. Parse the Azure SSH form strictly and cover it in a routing test.
- **VERDICT: FAIL** — explicit Azure URL scope can resolve to the wrong team; a supported Services remote form is also missed.

## Round 2 response
- **F1 fixed:** Azure team and backlog fields now come only from the anchored `_boards/board` route and its expected `t/<team>` / `backlogs/<level>` positions. A synthetic project named `t` resolves the actual route team.
- **F2 fixed:** The resolver recognizes only the Azure SSH `git@ssh.dev.azure.com:v3/<org>/<project>/<repo>` form and routes the synthetic selection through the fake reader.
- **Validation:** Unit 11/11, integration 8/8, typecheck exit 0 (warnings only in unchanged files), `git diff --check` passed.
- **VERDICT: PASS.**

## Round 2 review
- **F1 resolved:** The team marker is read only at the board route's expected position; project `t` no longer shadows it.
- **F2 resolved:** Strict Azure SSH `v3` parsing accepts the supported form and rejects malformed path/user variants.
- **No new findings:** Explicit URL host/protocol/credentials and decoded path segments are checked; conflicting/unsupported targets and Azure config/default-only inputs fail closed. The reader revalidates board/backlog and receives only the selected scope; missing board yielded zero reads in the probe. The declaration matches runtime results and typecheck passes. The trusted-PATH wording is an assumption, not an executable-identity guarantee, consistent with R9.
- **Validation:** Routing unit/integration tests: 19 pass; typecheck and lint exit 0 with warnings in unchanged files. No GitHub or Azure access.
- **VERDICT: PASS** — F1/F2 resolved; no open findings.
