// Shared between init and update: the install entries for one surface set. One
// definition — the payload init installs is exactly the payload update re-installs.

import { existsSync } from "node:fs";
import { join } from "node:path";
import type { PlanEntry } from "../install.ts";
import { VERSION } from "../version.ts";
import { embeddedTemplate, embeddedChainBundle } from "../embed.ts";

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
  const entries: PlanEntry[] = [
    { path: ".ai-engineering/overrides.toml", ours: embeddedTemplate("overrides.toml.tpl") },
    { path: ".ai-engineering/arch.rules.json", ours: embeddedTemplate("arch.rules.json.tpl") },
    { path: ".ai-engineering/config.toml", ours: render(embeddedTemplate("config.toml.tpl"), { surfaces: surfaces.map((s) => `"${s}"`).join(", ") }) },
    ...gitHookEntries(),
  ];
  if (surfaces.includes("claude-code")) {
    entries.push({ path: ".claude/settings.json", ours: embeddedTemplate("settings.claude.json.tpl") });
    entries.push({ path: ".github/workflows/ai-eng-check.yml", ours: embeddedTemplate("ci.yml.tpl") });
  }
  if (surfaces.includes("opencode")) {
    entries.push({ path: ".opencode/plugins/ai-eng.ts", ours: embeddedTemplate("plugin.opencode.ts.tpl") });
    entries.push({ path: ".opencode/plugins/ai-eng-chain.ts", ours: embeddedChainBundle() });
  }
  if (surfaces.includes("oh-my-pi")) {
    entries.push({ path: ".agents/hooks/ai-eng.ts", ours: embeddedTemplate("plugin.omp.ts.tpl") });
    entries.push({ path: ".agents/hooks/ai-eng-chain.ts", ours: embeddedChainBundle() });
  }
  return entries;
}

/** The contract files init writes ONCE (untouchable by update). */
export function contractEntries(date: string): PlanEntry[] {
  return [
    { path: "AGENTS.md", ours: render(embeddedTemplate("AGENTS.md.tpl"), { version: VERSION, commands: detectCommands() }) },
    { path: "DECISIONS.md", ours: render(embeddedTemplate("DECISIONS.md.tpl"), { date, version: VERSION }) },
  ];
}
