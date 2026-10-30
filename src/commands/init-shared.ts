// Shared between init and update: the install entries for one surface set. One
// definition — the payload init installs is exactly the payload update re-installs.

import { existsSync } from "node:fs";
import { join } from "node:path";
import type { PlanEntry } from "../install.ts";
import { VERSION } from "../version.ts";
import { embeddedTemplate } from "../embed.ts";
import { SURFACES, repoCarrier, carrierFiles, type Surface } from "../surfaces/adapters.ts";

export function repoTemplateRoot(): string {
  // src/commands → repo root is three up.
  return join(import.meta.dir, "..", "..");
}

/** One line for a file we were asked to merge into and could not. The file is left
 *  exactly as it was — and the line says what that costs, because a surface whose
 *  settings file could not be merged has no hooks behind it (§13). */
export function refuseLine(refused: { path: string; reason: string }): string {
  if (refused.reason === "identity-bound-settings-mutation-unavailable") {
    return `⚠ ${refused.path} — safe machine-settings replacement/removal is unavailable on this platform; left untouched`;
  }
  if (refused.reason === "machine-state-identity-unverified") {
    return `⚠ ${refused.path} — machine state is linked, changed, or shared with another path; left untouched`;
  }
  if (refused.reason === "settings-changed-after-validation") {
    return `⚠ ${refused.path} — settings changed during validation; left untouched`;
  }
  if (refused.reason === "settings-unreadable") {
    return `⚠ ${refused.path} — unreadable, a dangling link, not a regular file, or changing while read; left untouched`;
  }
  if (refused.reason === "machine-state-busy") {
    return `⚠ ${refused.path} — held by another ai-eng run, one on another host, or one this run cannot prove has stopped; machine state left untouched. If no ai-eng run is using this home, delete ${refused.path} and run again`;
  }
  if (refused.reason === "machine-state-lock-stale") {
    return `⚠ ${refused.path} — left by an ai-eng run that is no longer running; the next ai-eng update reclaims it`;
  }
  if (refused.reason === "machine-state-stranded") {
    return `⚠ machine.json is missing; an interrupted ai-eng run left its previous contents at ${refused.path} — move the right copy back to machine.json by hand; machine state left untouched`;
  }
  if (refused.reason === "machine-state-copy-kept") {
    return `⚠ ${refused.path} — an earlier copy of machine.json left by an interrupted ai-eng run; kept beside the current one — compare them and delete the one you do not need`;
  }
  if (refused.reason === "machine-state-unreadable") {
    return `⚠ ${refused.path} — machine state cannot be read or is not valid JSON; left untouched`;
  }
  if (refused.reason === "machine-state-kept-aside") {
    return `⚠ machine.json changed while this run was replacing it; its previous contents are kept at ${refused.path} — move them back by hand`;
  }
  if (refused.reason === "carrier-path-unwritable") {
    return `⚠ ${refused.path} — a link, a directory, or a file this installer cannot write is there; the carrier was not written`;
  }
  if (refused.reason === "carrier-edited") {
    return `⚠ ${refused.path} — changed since ai-eng wrote it; kept`;
  }
  if (refused.reason === "removal-refused") {
    return `⚠ ${refused.path} — still exactly ai-eng's, but it could not be removed (changed meanwhile, or a read-only, locked or busy folder); kept. Make the folder writable, then run again`;
  }
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

/** Commands for the tree being governed. The default is this framework's own
 *  checkout, which is what the unit seam asserts. `init` passes the target cwd:
 *  a Python project must not inherit this repo's bun/oxlint line. */
export function detectCommands(root: string = repoTemplateRoot()): string {
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
    {
      path: ".ai-engineering/config.toml",
      ours: embeddedTemplate("config.toml.tpl", {
        surfaces: surfaces.map((s) => `"${s}"`).join(", "),
      }),
    },
    // The merge gate belongs to the project, not to one editor: it hung off the
    // claude-code case, so choosing OpenCode/OMP/Codex/Cursor/Copilot CLI/Pi installed
    // guards and adapters with no workflow at all, and nothing said so (§17).
    { path: ".github/workflows/ai-eng-check.yml", ours: embeddedTemplate("ci.yml.tpl") },
    ...gitHookEntries(),
    ...surfaces.flatMap(surfaceEntries),
  ];
}

/** The files ONE surface generates INSIDE the repo: only the carriers whose readers
 *  live in the checkout (Cursor cloud). The other hosts read
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

/** The question init and config ask. Options sit on the next lines, with no tier headers. */
export const SURFACE_PICK_MESSAGE = "Which agent surfaces is this project governed on?";

/** The flat picker options shared by init and config. */
export function surfaceOptions(): Surface[] {
  return SURFACES.filter((surface) => hasAdapter(surface.id));
}

/** The contract files init writes ONCE (untouchable by update). The .gitignore rides
 *  with them: a project that already owns one keeps it (`install()` reports it as
 *  "yours, untouched"), and uninstall's project sweep never takes it back. */
export function contractEntries(date: string, root: string = repoTemplateRoot()): PlanEntry[] {
  return [
    { path: "AGENTS.md", ours: render(embeddedTemplate("AGENTS.md.tpl"), { version: VERSION, commands: detectCommands(root) }) },
    { path: "DECISIONS.md", ours: render(embeddedTemplate("DECISIONS.md.tpl"), { date, version: VERSION }) },
    { path: ".gitignore", ours: embeddedTemplate("gitignore.tpl") },
  ];
}
