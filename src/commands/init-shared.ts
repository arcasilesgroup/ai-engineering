// Shared between init and update: the install entries for one surface set. One
// definition — the payload init installs is exactly the payload update re-installs.

import { existsSync } from "node:fs";
import { join } from "node:path";
import type { PlanEntry } from "../install.ts";
import { VERSION } from "../version.ts";
import { embeddedTemplate, embeddedChainBundle } from "../embed.ts";
import { SURFACES, SURFACE_TIERS, type Surface } from "../surfaces/adapters.ts";

export function repoTemplateRoot(): string {
  // src/commands → repo root is three up.
  return join(import.meta.dir, "..", "..");
}

function render(template: string, vars: Record<string, string>): string {
  let out = template;
  for (const [key, value] of Object.entries(vars)) out = out.split(`{{${key}}}`).join(value);
  return out;
}

export function detectCommands(): string {
  const root = repoTemplateRoot();
  if (existsSync(join(root, "package.json"))) return "typecheck: tsc --noEmit · lint: oxlint · test: bun test · arch: bun test arch.spec.ts";
  if (existsSync(join(root, "Cargo.toml"))) return "typecheck: cargo check · lint: clippy · test: cargo test";
  if (existsSync(join(root, "go.mod"))) return "typecheck: go vet · lint: golangci-lint · test: go test";
  if (existsSync(join(root, "pyproject.toml"))) return "typecheck: mypy · lint: ruff · test: pytest";
  return "typecheck: (detect your language here) · test: (your runner)";
}

export function gitHookEntries(): PlanEntry[] {
  // Marker-managed shims land directly in .git/hooks/ — one copy, standard
  // location, no core.hooksPath redirect, no .ai-engineering/git duplicate.
  return [
    { path: ".git/hooks/pre-commit", ours: embeddedTemplate("git-pre-commit.tpl") },
    { path: ".git/hooks/commit-msg", ours: embeddedTemplate("git-commit-msg.tpl") },
    { path: ".git/hooks/pre-push", ours: embeddedTemplate("git-pre-push.tpl") },
  ];
}

export function planEntries(surfaces: string[]): PlanEntry[] {
  return [
    { path: ".ai-engineering/overrides.toml", ours: embeddedTemplate("overrides.toml.tpl") },
    { path: ".ai-engineering/arch.rules.json", ours: embeddedTemplate("arch.rules.json.tpl") },
    { path: ".ai-engineering/config.toml", ours: render(embeddedTemplate("config.toml.tpl"), { surfaces: surfaces.map((s) => `"${s}"`).join(", ") }) },
    ...gitHookEntries(),
    ...surfaces.flatMap(surfaceEntries),
  ];
}

/** The files ONE surface generates. Empty for a surface with no adapter — and by
 *  §13 a surface is declared in surfaces.json before init offers it. Only these
 *  three carry a generator today: offering the rest wrote a config.toml claim no
 *  guard satisfied (cursor/codex/copilot installed nothing, measured 2026-09-10). */
function surfaceEntries(id: string): PlanEntry[] {
  switch (id) {
    case "claude-code":
      return [
        { path: ".claude/settings.json", ours: embeddedTemplate("settings.claude.json.tpl") },
        { path: ".github/workflows/ai-eng-check.yml", ours: embeddedTemplate("ci.yml.tpl") },
      ];
    case "opencode":
      return [
        { path: ".opencode/plugins/ai-eng.ts", ours: embeddedTemplate("plugin.opencode.ts.tpl") },
        { path: ".opencode/plugins/ai-eng-chain.ts", ours: embeddedChainBundle() },
      ];
    case "oh-my-pi":
      return [
        { path: ".agents/hooks/ai-eng.ts", ours: embeddedTemplate("plugin.omp.ts.tpl") },
        { path: ".agents/hooks/ai-eng-chain.ts", ours: embeddedChainBundle() },
      ];
    case "codex":
      return [{ path: ".codex/hooks.json", ours: embeddedTemplate("settings.codex.json.tpl") }];
    case "cursor":
      return [{ path: ".cursor/hooks.json", ours: embeddedTemplate("settings.cursor.json.tpl") }];
    case "copilot":
      return [{ path: ".github/hooks/ai-eng.json", ours: embeddedTemplate("settings.copilot.json.tpl") }];
    case "pi":
      return [
        { path: ".pi/extensions/ai-eng.ts", ours: embeddedTemplate("plugin.pi.ts.tpl") },
        { path: ".pi/extensions/ai-eng-chain.ts", ours: embeddedChainBundle() },
      ];
    default:
      return [];
  }
}

/** A surface earns a place in a picker only with an adapter behind it: the
 *  declaration in surfaces.json is the plan, the generator is the proof. */
export function hasAdapter(id: string): boolean {
  return surfaceEntries(id).length > 0;
}

/** The picker's groups (init and config share them): tier header → the surfaces
 *  that can actually be scaffolded, empty tiers dropped. */
export function surfaceOptions(): Array<{ title: string; items: Surface[] }> {
  return SURFACE_TIERS.map(([tier, title]) => ({ title, items: SURFACES.filter((s) => s.tier === tier && hasAdapter(s.id)) })).filter((group) => group.items.length > 0);
}

/** The contract files init writes ONCE (untouchable by update). */
export function contractEntries(date: string): PlanEntry[] {
  return [
    { path: "AGENTS.md", ours: render(embeddedTemplate("AGENTS.md.tpl"), { version: VERSION, commands: detectCommands() }) },
    { path: "DECISIONS.md", ours: render(embeddedTemplate("DECISIONS.md.tpl"), { date, version: VERSION }) },
  ];
}
