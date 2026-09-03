// `ai-eng uninstall` — two scopes, stated plainly (user feedback 2026-09-01 #6,
// sharpened 2026-09-02): "This project" sweeps EVERY file the lock declares
// ai-eng's (hooks, settings entries, adapters, CI workflow, config, lock) and
// prunes the dirs that end up empty — nothing that depends on ai-eng is left
// behind. "Everything" ALSO removes the machine side (~/.ai-engineering: the
// global skill canon and mirrors). Deleting what the user edited is the worst
// class of bug a governance tool can have: edited files are kept and named,
// contract files survive "This project", and "Everything" asks twice.

import { spawnSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync, unlinkSync, readdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { SURFACES } from "../surfaces/adapters.ts";
import { repoRoot, home, enabledSurfaces } from "../env.ts";
import { parseLock, sha256 } from "../install.ts";
import { hashFile } from "../skills-lint.ts";
import { planEntries } from "./init-shared.ts";
import { select, isCancel } from "@clack/prompts";
import * as ui from "../ui.ts";
import { VERSION } from "../version.ts";
import { scriptedInput } from "../ui.ts";

const AI_ENG_ENTRIES = ["ai-eng chain"];

/** Our hook entries out of a surface settings file; the user's hooks stay.
 *  Unparseable → left alone with a warn: never rewrite what you cannot read. */
function stripAiEngHooks(absolute: string, rel: string, removed: ui.Row[]): void {
  try {
    type HookGroup = { hooks?: Array<{ command?: string }> };
    type SettingsShape = { hooks?: Record<string, HookGroup[]>; $comment?: string };
    const settings = JSON.parse(readFileSync(absolute, "utf8")) as SettingsShape;
    delete settings.$comment; // ours too: the template's banner
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
    if (Object.keys(settings.hooks ?? {}).length === 0) {
      delete settings.hooks;
      writeFileSync(absolute, `${JSON.stringify(settings, null, 2)}\n`);
      if (Object.keys(settings).length === 0) {
        unlinkSync(absolute);
        removed.push({ mark: "ok", text: `${rel} removed`, dim: "it held only ai-eng entries" });
        return;
      }
    } else {
      writeFileSync(absolute, `${JSON.stringify(settings, null, 2)}\n`);
    }
    removed.push({ mark: "ok", text: `${rel}: removed the ai-eng hook entries, kept yours` });
  } catch {
    removed.push({ mark: "warn", text: `${rel} not parseable — leaving it alone (review by hand)` });
  }
}

/** Remove a directory only when it is empty — ai-eng created it, the sweep
 *  emptied it, and an empty scaffold is noise. */
function pruneIfEmpty(dir: string): boolean {
  try {
    if (readdirSync(dir).length === 0) {
      rmSync(dir, { recursive: true, force: true });
      return true;
    }
  } catch {
    /* absent or unreadable: nothing to prune */
  }
  return false;
}

export async function uninstallMain(): Promise<number> {
  const input = scriptedInput();
  ui.frame(`Uninstall · ai-eng ${VERSION}`);
  const root = repoRoot();
  if (!root) {
    ui.fail("you are not in a governed repo — nothing of this project to remove");
    ui.end("Nothing done.");
    return 2;
  }
  ui.section("Two scopes", [
    { mark: "info", text: "This project", dim: "sweeps every file the lock says ai-eng owns: hooks, settings entries, adapters, CI workflow, config, lock. Keeps AGENTS.md, DECISIONS.md, spec/plan." },
    { mark: "warn", text: "Everything", dim: `the project side ABOVE, plus the machine side: deletes ${home()} (global skills, mirrors, caches). Asks twice.` },
  ]);
  const scope = await select({
    message: "What do you want to remove?",
    options: [
      { value: "project", label: "This project only — every file the lock says ai-eng owns" },
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
  // The lock is the ownership register; when it is gone (a half-finished
  // uninstall, a hand-deletion), the binary's own planEntries list is the
  // fallback — same paths, hashes recomputed from the payload it installs.
  // Never a hardcoded subset, never a file it did not install.
  const removed: ui.Row[] = [];
  spawnSync("git", ["-C", root, "config", "--unset", "core.hooksPath"]);
  removed.push({ mark: "ok", text: "git: core.hooksPath reverted to default" });
  const lockPath = join(root, ".ai-engineering", "ai-eng.lock");
  const hasLock = existsSync(lockPath);
  let assets: Record<string, string> = hasLock ? parseLock(readFileSync(lockPath, "utf8")).assets : {};
  if (Object.keys(assets).length === 0) {
    assets = Object.fromEntries(
      planEntries(enabledSurfaces()).map((entry) => [entry.path, sha256(entry.ours)]),
    );
    removed.push({ mark: "muted", text: "no lock — swept by the binary's own file list" });
  }
  const owned = Object.keys(assets);
  const settingsByPath = new Map<string, string>();
  for (const surface of SURFACES) if (typeof surface.settingsFile === "string") settingsByPath.set(surface.settingsFile, surface.label);
  for (const rel of owned) {
    const absolute = join(root, rel);
    if (!existsSync(absolute)) continue;
    if (settingsByPath.has(rel)) {
      // Unedited: the whole file is ai-eng's template — it goes. Edited: the
      // user's keys stay, only our hook entries come out.
      if (hashFile(absolute) === assets[rel]) {
        unlinkSync(absolute);
        removed.push({ mark: "ok", text: `${rel} removed`, dim: "still the template ai-eng installed" });
      } else {
        stripAiEngHooks(absolute, rel, removed);
      }
      continue;
    }
    // Git shims are judged by their marker (the only test that survives a
    // user re-chmod); everything else by the lock's hash: delete only what
    // still matches what we installed — an edited file is yours now, kept and named.
    if (rel.startsWith(".git/hooks/")) {
      if (readFileSync(absolute, "utf8").includes("ai-eng git floor shim")) {
        unlinkSync(absolute);
        removed.push({ mark: "ok", text: `${rel} removed`, dim: "marker-matched — never by name alone" });
      } else {
        removed.push({ mark: "warn", text: `${rel} kept`, dim: "no ai-eng marker: it is yours now" });
      }
      continue;
    }
    if (hashFile(absolute) === assets[rel]) {
      unlinkSync(absolute);
      removed.push({ mark: "ok", text: `${rel} removed` });
    } else {
      removed.push({ mark: "warn", text: `${rel} kept`, dim: "you edited it after install — it is yours now" });
    }
  }
  if (hasLock) {
    unlinkSync(lockPath);
    removed.push({ mark: "ok", text: "ai-eng.lock deleted", dim: `${owned.length} owned files swept` });
  } else {
    removed.push({ mark: "muted", text: `${owned.length} owned files swept` });
  }
  // Dirs ai-eng created are pruned only when the sweep left them empty.
  for (const dir of [".ai-engineering", ".claude", ".cursor", ".codex", ".copilot", ".opencode/plugins", ".agents/hooks", ".github/workflows"]) {
    if (pruneIfEmpty(join(root, dir))) removed.push({ mark: "muted", text: `${dir}/ removed (empty)` });
  }
  for (const dir of [".opencode", ".agents", ".github"]) {
    if (pruneIfEmpty(join(root, dir))) removed.push({ mark: "muted", text: `${dir}/ removed (empty)` });
  }
  // Rendered as one block: what went, at a glance.
  ui.section("Removed", removed);
  if (scope === "everything") {
    const extra: ui.Row[] = [];
    const agents = join(root, "AGENTS.md");
    const decisions = join(root, "DECISIONS.md");
    const confirmedAll = await ui.confirmDefault("Delete this project's AGENTS.md, DECISIONS.md and .ai-engineering/ too? They hold your work.", false, input as never);
    if (confirmedAll) {
      if (existsSync(agents)) unlinkSync(agents);
      if (existsSync(decisions)) unlinkSync(decisions);
      const claude = join(root, "CLAUDE.md");
      if (existsSync(claude)) unlinkSync(claude);
      rmSync(join(root, ".ai-engineering"), { recursive: true, force: true });
      extra.push({ mark: "warn", text: "project contract files removed (your choice)", dim: "AGENTS.md · DECISIONS.md · CLAUDE.md · .ai-engineering/" });
    } else {
      extra.push({ mark: "ok", text: "kept: AGENTS.md, DECISIONS.md, .ai-engineering/" });
    }
    // The machine side: the global canon this binary installed.
    const machineDir = home();
    const confirmedMachine = await ui.confirmDefault(`Delete the machine side ${machineDir} (global skills, mirrors)?`, false, input as never);
    if (confirmedMachine) {
      rmSync(machineDir, { recursive: true, force: true });
      extra.push({ mark: "warn", text: `${machineDir} deleted`, dim: "global skills and mirrors removed" });
    } else {
      extra.push({ mark: "ok", text: `kept: ${machineDir}`, dim: "global skills stay installed" });
    }
    ui.section("Everything scope — the extra sweep", extra);
  }
  ui.end(scope === "everything" ? "ai-eng removed from this machine as far as you chose. Your work survives unless you said otherwise." : "ai-eng is no longer active in this repo. Your contract files remain.");
  return 0;
}
