// `ai-eng uninstall` — reverts core.hooksPath, removes ONLY its own entries, and
// keeps AGENTS.md, DECISIONS.md, spec.html, arch.rules and the skills. Deleting
// what the user edited is the worst class of bug a governance tool can have (§14.5).

import { existsSync, readFileSync, writeFileSync, unlinkSync, readdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { select, isCancel } from "@clack/prompts";
import { repoRoot } from "../env.ts";
import * as ui from "../ui.ts";
import { VERSION } from "../version.ts";

const AI_ENG_ENTRIES = ["ai-eng chain"];

export async function uninstallMain(): Promise<number> {
  const root = repoRoot();
  ui.frame(`Uninstall · ai-eng ${VERSION}`);
  if (!root) {
    ui.fail("you are not in a governed repo — nothing to remove");
    ui.end("Nothing done.");
    return 2;
  }
  ui.info("This will remove ai-eng governance from this project:");
  ui.ok("core.hooksPath reverted if a custom redirect exists");
  ui.ok("marker-managed hooks removed from .git/hooks/ (only files carrying the ai-eng marker)");
  ui.ok(".claude/settings.json — only ai-eng hook entries removed");
  ui.ok("ai-eng.lock deleted");
  ui.info("Kept (yours): AGENTS.md · DECISIONS.md · .ai-engineering/{spec,plan}.html · config.toml · overrides.toml · arch.rules.json");
  const scope = await select({
    message: "What do you want to remove?",
    options: [
      { value: "governance", label: "Governance only — hooks, lock, shims — keep contract files" },
      { value: "everything", label: "Everything — all ai-eng files, contract included" },
      { value: "cancel", label: "Cancel" },
    ],
  });
  if (isCancel(scope) || scope === "cancel") {
    ui.cancelled("Nothing removed.");
    return 0;
  }
  // Default is No: uninstall is destructive, a bare Enter must not raze the repo.
  const confirmed = await ui.confirmDefault("Confirm?", false);
  if (confirmed === false) {
    ui.cancelled("Nothing removed.");
    return 0;
  }

  // 1. core.hooksPath back to default.
  spawnSync("git", ["-C", root, "config", "--unset", "core.hooksPath"]);
  ui.ok("core.hooksPath reverted");
  // 2. Our hook entries out of the surface settings, the user's hooks stay.
  const settingsPath = join(root, ".claude", "settings.json");
  if (existsSync(settingsPath)) {
    try {
      type HookGroup = { hooks?: Array<{ command?: string }> };
      type SettingsShape = { hooks?: Record<string, HookGroup[]> };
      const settings = JSON.parse(readFileSync(settingsPath, "utf8")) as SettingsShape;
      if (settings.hooks) {
        for (const event of Object.keys(settings.hooks)) {
          const groups = settings.hooks[event] ?? [];
          const filtered = groups
            .map((group) => ({
              ...group,
              hooks: (group.hooks ?? []).filter((hook) => !AI_ENG_ENTRIES.some((entry) => (hook.command ?? "").includes(entry))),
            }))
            .filter((group) => (group.hooks ?? []).length > 0);
          if (filtered.length > 0) settings.hooks[event] = filtered;
          else delete settings.hooks[event];
        }
      }
      writeFileSync(settingsPath, `${JSON.stringify(settings, null, 2)}\n`);
      ui.ok(".claude/settings.json — only ai-eng entries removed");
    } catch {
      ui.warn(".claude/settings.json not parseable — leaving it alone (review by hand)");
    }
  }
  // 3. Our shims out of .git/hooks, identified by the marker, never by name alone.
  const hooksDir = join(root, ".git", "hooks");
  if (existsSync(hooksDir)) {
    for (const name of readdirSync(hooksDir)) {
      if (!["pre-commit", "commit-msg", "pre-push"].includes(name)) continue;
      const hookPath = join(hooksDir, name);
      const content = readFileSync(hookPath, "utf8");
      if (content.includes("ai-eng git floor shim")) unlinkSync(hookPath);
    }
  }
  ui.ok("marker-managed hooks removed (only files with the ai-eng marker)");
  const lockPath = join(root, ".ai-engineering", "ai-eng.lock");
  if (existsSync(lockPath)) unlinkSync(lockPath);
  ui.ok("lock deleted");
  if (scope === "everything") {
    const agents = join(root, "AGENTS.md");
    const decisions = join(root, "DECISIONS.md");
    const confirmedAll = await ui.confirmDefault("This deletes AGENTS.md and DECISIONS.md — your work. Sure?", false);
    if (confirmedAll) {
      if (existsSync(agents)) unlinkSync(agents);
      if (existsSync(decisions)) unlinkSync(decisions);
      rmSync(join(root, ".ai-engineering"), { recursive: true, force: true });
      ui.ok("all ai-eng files removed (your choice)");
    } else {
      ui.info("kept: AGENTS.md, DECISIONS.md, .ai-engineering/");
    }
  }
  ui.end("ai-eng is no longer active in this repo. Your contract files remain.");
  return 0;
}
