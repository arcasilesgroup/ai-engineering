// Shared between init and update: the plan entries for one surface set. One
// definition — the payload init plants is exactly the payload update re-plants.

import { existsSync } from "node:fs";
import { join } from "node:path";
import type { PlanEntry } from "../plant.ts";
import { embeddedTemplate, embeddedText } from "../embed.ts";

export const VERSION = "0.13.0";

export function repoTemplateRoot(): string {
  // src/commands → repo root is three up.
  return join(import.meta.dir, "..", "..");
}

function tpl(name: string): string {
  return embeddedTemplate(name);
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
  return "typecheck: (detecta tu lenguaje aquí) · test: (tu runner)";
}

export function planEntries(surfaces: string[]): PlanEntry[] {
  const entries: PlanEntry[] = [
    { path: ".ai-engineering/overrides.toml", ours: tpl("overrides.toml.tpl") },
    { path: ".ai-engineering/arch.rules.json", ours: tpl("arch.rules.json.tpl") },
    { path: ".ai-engineering/git/pre-commit", ours: tpl("git-pre-commit.tpl") },
    { path: ".ai-engineering/git/commit-msg", ours: tpl("git-commit-msg.tpl") },
    { path: ".ai-engineering/git/pre-push", ours: tpl("git-pre-push.tpl") },
    { path: ".ai-engineering/config.toml", ours: render(tpl("config.toml.tpl"), { surfaces: surfaces.map((s) => `"${s}"`).join(", ") }) },
  ];
  if (surfaces.includes("claude-code")) {
    entries.push({ path: ".claude/settings.json", ours: tpl("settings.claude.json.tpl") });
    entries.push({ path: ".github/workflows/ai-eng-check.yml", ours: tpl("ci.yml.tpl") });
  }
  if (surfaces.includes("opencode")) {
    entries.push({ path: ".opencode/plugins/ai-eng.ts", ours: tpl("plugin.opencode.ts.tpl") });
    entries.push({ path: ".opencode/plugins/ai-eng-chain.ts", ours: embeddedText("src-chain") });
  }
  if (surfaces.includes("oh-my-pi")) {
    entries.push({ path: ".agents/hooks/ai-eng.ts", ours: tpl("plugin.omp.ts.tpl") });
    entries.push({ path: ".agents/hooks/ai-eng-chain.ts", ours: embeddedText("src-chain") });
  }
  return entries;
}

/** The contract files init writes ONCE (untouchable by update). */
export function contractEntries(date: string): PlanEntry[] {
  return [
    { path: "AGENTS.md", ours: render(tpl("AGENTS.md.tpl"), { version: VERSION, commands: detectCommands() }) },
    { path: "DECISIONS.md", ours: render(tpl("DECISIONS.md.tpl"), { date, version: VERSION }) },
  ];
}
