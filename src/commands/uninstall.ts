// `ai-eng uninstall` — reverts core.hooksPath, removes ONLY its own entries, and
// keeps AGENTS.md, DECISIONS.md, spec.html, arch.rules and the skills. Deleting
// what the user edited is the worst class of bug a governance tool can have (§14.5).

import { existsSync, readFileSync, writeFileSync, unlinkSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { confirm, select, isCancel } from "@clack/prompts";
import { repoRoot } from "../env.ts";

const AI_ENG_ENTRIES = ["ai-eng chain"];

export async function uninstallMain(): Promise<number> {
  const root = repoRoot();
  if (!root) {
    process.stderr.write("uninstall: no estás en un repo gobernado.\n");
    return 2;
  }
  process.stdout.write("This will remove ai-eng governance from this project:\n\n");
  process.stdout.write("✓ core.hooksPath reverted if a custom redirect exists\n");
  process.stdout.write("✓ marker-managed hooks removed from .git/hooks/ (only files carrying the ai-eng marker)\n");
  process.stdout.write("✓ .claude/settings.json — only ai-eng hook entries removed\n");
  process.stdout.write("✓ ai-eng.lock deleted\n\n");
  process.stdout.write("Kept (yours): AGENTS.md · DECISIONS.md · .ai-engineering/{spec,plan}.html · config.toml · overrides.toml · arch.rules.json\n\n");
  const scope = await select({
    message: "What do you want to remove?",
    options: [
      { value: "governance", label: "Governance only — hooks, lock, shims — keep contract files" },
      { value: "everything", label: "Everything — all ai-eng files, contract included" },
      { value: "cancel", label: "Cancel" },
    ],
  });
  if (isCancel(scope) || scope === "cancel") return 0;
  const confirmed = await confirm({ message: "Confirm?" });
  if (isCancel(confirmed) || confirmed === false) return 0;

  const lines: string[] = [];
  // 1. core.hooksPath back to default.
  spawnSync("git", ["-C", root, "config", "--unset", "core.hooksPath"]);
  lines.push("✓ core.hooksPath reverted");
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
      lines.push("✓ .claude/settings.json — solo entradas ai-eng eliminadas");
    } catch {
      lines.push("⚠ .claude/settings.json no parseable — no lo toco (revísalo a mano)");
    }
  }
  const hooksDir = join(root, ".git", "hooks");
  if (existsSync(hooksDir)) {
    for (const name of readdirSync(hooksDir)) {
      if (!["pre-commit", "commit-msg", "pre-push"].includes(name)) continue;
      const hookPath = join(hooksDir, name);
      const content = readFileSync(hookPath, "utf8");
      if (content.includes("ai-eng git floor shim")) unlinkSync(hookPath);
    }
  }
  lines.push("✓ marker-managed hooks removed (only files with the ai-eng marker)");
  const lockPath = join(root, ".ai-engineering", "ai-eng.lock");
  if (existsSync(lockPath)) unlinkSync(lockPath);
  lines.push("✓ lock deleted");
  if (scope === "everything") {
    const agents = join(root, "AGENTS.md");
    const decisions = join(root, "DECISIONS.md");
    const confirmedAll = await confirm({ message: "Esto borra AGENTS.md y DECISIONS.md — tu trabajo. ¿Seguro?" });
    if (confirmedAll === true) {
      if (existsSync(agents)) unlinkSync(agents);
      if (existsSync(decisions)) unlinkSync(decisions);
      rmSync(join(root, ".ai-engineering"), { recursive: true, force: true });
      lines.push("✓ todo lo de ai-eng eliminado (elección tuya)");
    } else {
      lines.push("· conservado: AGENTS.md, DECISIONS.md, .ai-engineering/");
    }
  }
  for (const line of lines) process.stdout.write(`${line}\n`);
  process.stdout.write("\nai-eng is no longer active in this repo. Your contract files remain.\n");
  return 0;
}
