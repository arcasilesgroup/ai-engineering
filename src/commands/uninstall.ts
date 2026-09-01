// `ai-eng uninstall` — two scopes, stated plainly (user feedback 2026-09-01 #6):
// "This project" removes only what this repo carries (hooks, settings entries,
// lock). "Everything" ALSO removes the machine side (~/.ai-engineering: the
// global skill canon and mirrors). Deleting what the user edited is the worst
// class of bug a governance tool can have, so contract files survive "This
// project" and "Everything" asks twice before it deletes them.

import { existsSync, readFileSync, writeFileSync, unlinkSync, readdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { select, isCancel } from "@clack/prompts";
import { repoRoot, home } from "../env.ts";
import * as ui from "../ui.ts";
import { VERSION } from "../version.ts";
import { scriptedInput } from "../ui.ts";

const AI_ENG_ENTRIES = ["ai-eng chain"];

export async function uninstallMain(): Promise<number> {
  const input = scriptedInput();
  ui.frame(`Uninstall · ai-eng ${VERSION}`);
  const root = repoRoot();
  if (!root) {
    ui.fail("you are not in a governed repo — nothing of this project to remove");
    ui.end("Nothing done.");
    return 2;
  }
  ui.info("Two scopes:");
  ui.info(`  This project — removes what THIS repo carries: git hooks, surface settings entries, ai-eng.lock. Keeps AGENTS.md, DECISIONS.md, spec/plan.`);
  ui.info(`  Everything  — the project side ABOVE, plus the machine side: deletes ${home()} (global skills, mirrors, caches). Asks twice.`);
  const scope = await select({
    message: "What do you want to remove?",
    options: [
      { value: "project", label: "This project only — hooks, settings entries, lock" },
      { value: "everything", label: `Everything — this project AND ${home()} (global skills)` },
      { value: "cancel", label: "Cancel — remove nothing" },
    ],
    input: input as never,
  });
  if (isCancel(scope) || scope === "cancel") {
    ui.cancelled("Nothing removed.");
    return 0;
  }
  // Default is No: uninstall is destructive, a bare Enter must not raze the repo.
  const confirmed = await ui.confirmDefault("Confirm?", false, input as never);
  if (confirmed === false) {
    ui.cancelled("Nothing removed.");
    return 0;
  }

  // ── project side ──────────────────────────────────────────────
  // 1. core.hooksPath back to default.
  spawnSync("git", ["-C", root, "config", "--unset", "core.hooksPath"]);
  ui.ok("git: core.hooksPath reverted to default");
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
      ui.ok(".claude/settings.json: removed the ai-eng hook entries, kept yours");
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
  ui.ok(".git/hooks: removed the three ai-eng shims (marker-matched)");
  const lockPath = join(root, ".ai-engineering", "ai-eng.lock");
  if (existsSync(lockPath)) unlinkSync(lockPath);
  ui.ok("ai-eng.lock deleted");

  if (scope === "everything") {
    const agents = join(root, "AGENTS.md");
    const decisions = join(root, "DECISIONS.md");
    const confirmedAll = await ui.confirmDefault("Delete this project's AGENTS.md, DECISIONS.md and .ai-engineering/ too? They hold your work.", false, input as never);
    if (confirmedAll) {
      if (existsSync(agents)) unlinkSync(agents);
      if (existsSync(decisions)) unlinkSync(decisions);
      rmSync(join(root, ".ai-engineering"), { recursive: true, force: true });
      ui.ok("project contract files removed (your choice)");
    } else {
      ui.info("kept: AGENTS.md, DECISIONS.md, .ai-engineering/");
    }
    // The machine side: the global canon this binary installed.
    const machineDir = home();
    const confirmedMachine = await ui.confirmDefault(`Delete the machine side ${machineDir} (global skills, mirrors)?`, false, input as never);
    if (confirmedMachine) {
      rmSync(machineDir, { recursive: true, force: true });
      ui.ok(`${machineDir} deleted — global skills and mirrors removed`);
    } else {
      ui.info(`kept: ${machineDir} (global skills stay installed)`);
    }
  }
  ui.end(scope === "everything" ? "ai-eng removed from this machine as far as you chose. Your work survives unless you said otherwise." : "ai-eng is no longer active in this repo. Your contract files remain.");
  return 0;
}
