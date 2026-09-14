// Shared between init and update: the install entries for one surface set. One
// definition — the payload init installs is exactly the payload update re-installs.

import { existsSync } from "node:fs";
import { join } from "node:path";
import type { PlanEntry } from "../install.ts";
import { VERSION } from "../version.ts";
import { embeddedTemplate } from "../embed.ts";
import { SURFACES, SURFACE_TIERS, repoCarrier, carrierFiles, type Surface } from "../surfaces/adapters.ts";

export function repoTemplateRoot(): string {
  // src/commands → repo root is three up.
  return join(import.meta.dir, "..", "..");
}

/** One line for a file we were asked to merge into and could not. The file is left
 *  exactly as it was — and the line says what that costs, because a surface whose
 *  settings file could not be merged has no hooks behind it (§13). */
export function refuseLine(refused: { path: string; reason: string }): string {
  const why =
    refused.reason === "not-json"
      ? "not valid JSON"
      : refused.reason === "reformat"
        ? "laid out in a style this installer would have to reformat (tabs, CRLF, a compact one-liner)"
        : "not a JSON object";
  return `⚠ ${refused.path} — ${why}: left exactly as it is, so this surface runs without guards until you move it aside or reformat it`;
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
    // The merge gate belongs to the project, not to one editor: it hung off the
    // claude-code case, so choosing OpenCode/OMP/Codex/Cursor/Copilot/Pi installed
    // guards and adapters with no workflow at all, and nothing said so (§17).
    { path: ".github/workflows/ai-eng-check.yml", ours: embeddedTemplate("ci.yml.tpl") },
    ...gitHookEntries(),
    ...surfaces.flatMap(surfaceEntries),
  ];
}

/** The files ONE surface generates INSIDE the repo: only the carriers whose readers
 *  live in the checkout (Cursor cloud, VS Code Copilot Chat). The other five hosts read
 *  from the user's home, and `installMachineCarriers()` writes those once per machine —
 *  a repo that still carried them would be carrying a hook file nobody reads (§13.2).
 *
 *  A settings carrier is `merge: true`: it can be a file the user already owns, so ours
 *  go in by marker and the file is never written whole (§03). */
function surfaceEntries(id: string): PlanEntry[] {
  const surface = SURFACES.find((s) => s.id === id);
  const placement = surface ? repoCarrier(surface) : null;
  const files = carrierFiles(id, "repo");
  if (!placement || !files) return [];
  const entries: PlanEntry[] = [{ path: placement.path, ours: files.main, merge: placement.kind === "settings" }];
  if (placement.chain && files.chain) entries.push({ path: placement.chain, ours: files.chain });
  return entries;
}

/** A surface earns a place in a picker only with an adapter behind it: the
 *  declaration in surfaces.json is the plan, the generator is the proof. */
export function hasAdapter(id: string): boolean {
  return carrierFiles(id, "repo") !== null;
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
