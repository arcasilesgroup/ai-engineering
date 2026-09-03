// `ai-eng upgrade` — deliberately boring (§14.4): show the changelog, confirm, and
// delegate the install to bun/npm. Ten lines of spawn. Reimplementing download +
// integrity + self-substitution is inventing npm with less testing.
// cli-ux-14 work point 05: frame, inline changelog when the local CHANGELOG.md
// carries the target section (else URL), and the print-command helper chooses by
// the manager the user actually picked (regression: it always printed bun).

import { existsSync, readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { select, isCancel } from "@clack/prompts";
import { join } from "node:path";
import { VERSION } from "../version.ts";
import * as ui from "../ui.ts";

function registryLatest(): string | null {
  const bun = spawnSync("bun", ["pm", "view", "ai-engineering", "version"], { encoding: "utf8" });
  if (bun.status === 0 && bun.stdout) return bun.stdout.trim().split("\n").pop() ?? null;
  const npm = spawnSync("npm", ["view", "ai-engineering", "version"], { encoding: "utf8" });
  if (npm.status === 0 && npm.stdout) return npm.stdout.trim().split("\n").pop() ?? null;
  return null; // offline or error → silence, never a failure
}

/** The install command for a manager, in one place — the G9 seam. */
export function installCommand(manager: "bun" | "npm", version: string): string {
  return manager === "bun" ? `bun add -g ai-engineering@${version}` : `npm install -g ai-engineering@${version}`;
}

/** Inline changelog section for a version when the local CHANGELOG.md has it. */
export function changelogSection(root: string, version: string): string | null {
  const path = join(root, "CHANGELOG.md");
  if (!existsSync(path)) return null;
  const text = readFileSync(path, "utf8");
  const match = new RegExp(`^## ${version.replace(/\./g, "\\.")}[^\n]*\n([\\s\\S]*?)(?=\\n## |$)`, "m").exec(text);
  return match ? match[1]?.trim() ?? null : null;
}

export async function upgradeMain(): Promise<number> {
  const latest = registryLatest();
  if (!latest) {
    ui.frame(`ai-eng ${VERSION}`);
    ui.info("could not read the registry version (offline?) — silence, never a failure");
    ui.end("Nothing done.");
    return 0;
  }
  if (latest === VERSION) {
    ui.frame(`ai-eng ${VERSION}`);
    ui.ok("already the latest");
    ui.end("Nothing to upgrade.");
    return 0;
  }
  ui.frame(`ai-eng · installed ${VERSION} · latest ${latest}`);
  const section = changelogSection(process.cwd(), latest);
  if (section) {
    ui.section(`What's new in ${latest}`, section.split("\n").slice(0, 12).map((line): ui.Row => ({ mark: "muted", text: line.replace(/^### /, "").replace(/^- /, "· ") })));
  } else {
    ui.section(`What's new in ${latest}`, [{ mark: "muted", text: "CHANGELOG: https://github.com/arcasilesgroup/ai-engineering/blob/main/CHANGELOG.md" }]);
  }
  const how = await select({
    message: "How do you want to update?",
    options: [
      { value: "bun", label: installCommand("bun", latest), hint: "registry, checksum, substitution — by bun" },
      { value: "npm", label: installCommand("npm", latest), hint: "registry, checksum, substitution — by npm" },
      { value: "print", label: "Just print the command, I'll run it myself" },
    ],
  });
  if (isCancel(how)) {
    ui.cancelled("Nothing done — upgrade proposes, the human disposes.");
    return 0;
  }
  if (how === "print") {
    ui.end(`Run: ${installCommand("bun", latest)} (or the npm equivalent)`);
    return 0;
  }
  const manager = how === "bun" ? "bun" : "npm";
  const done = spawnSync(manager, [manager === "bun" ? "add" : "install", "-g", `ai-engineering@${latest}`], { stdio: "inherit" });
  if (done.status !== 0) return done.status ?? 1;
  ui.section("Upgraded", [{ mark: "ok", text: `ai-eng ${verify.stdout?.trim() ?? latest}`, dim: "trust is signed by the registry, not by ai-eng" }]);
  ui.end("if this repo still runs assets from the previous version → ai-eng update");
  return 0;
}
