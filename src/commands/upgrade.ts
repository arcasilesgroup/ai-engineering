// `ai-eng upgrade` — deliberately boring (§14.4): show the changelog, confirm, and
// delegate the install to bun/npm. Ten lines of spawn. Reimplementing download +
// integrity + self-substitution is inventing npm with less testing.

import { spawnSync } from "node:child_process";
import { select, isCancel } from "@clack/prompts";
import { VERSION } from "../version.ts";

function registryLatest(): string | null {
  const bun = spawnSync("bun", ["pm", "view", "ai-engineering", "version"], { encoding: "utf8" });
  if (bun.status === 0 && bun.stdout) return bun.stdout.trim().split("\n").pop() ?? null;
  const npm = spawnSync("npm", ["view", "ai-engineering", "version"], { encoding: "utf8" });
  if (npm.status === 0 && npm.stdout) return npm.stdout.trim().split("\n").pop() ?? null;
  return null; // offline or error → silence, never a failure
}

export async function upgradeMain(): Promise<number> {
  const latest = registryLatest();
  if (!latest) {
    process.stdout.write("upgrade: could not read the registry version (offline?) — silence, never a failure.\n");
    return 0;
  }
  if (latest === VERSION) {
    process.stdout.write(`ai-eng ${VERSION} — already the latest.\n`);
    return 0;
  }
  process.stdout.write(`ai-eng · installed ${VERSION} · latest ${latest}\n`);
  process.stdout.write("CHANGELOG: https://github.com/arcasilesgroup/ai-engineering/blob/main/CHANGELOG.md\n");
  const how = await select({
    message: "How do you want to update?",
    options: [
      { value: "bun", label: `bun add -g ai-engineering@${latest}` },
      { value: "npm", label: `npm install -g ai-engineering@${latest}` },
      { value: "print", label: "Just print the command, I'll run it myself" },
    ],
  });
  if (isCancel(how)) return 0;
  const command = how === "bun" ? ["add", "-g", `ai-engineering@${latest}`] : ["install", "-g", `ai-engineering@${latest}`];
  if (how === "print") {
    process.stdout.write(`${how === "print" ? `bun add -g ai-engineering@${latest}` : ""}\n`);
    return 0;
  }
  const manager = how === "bun" ? "bun" : "npm";
  const done = spawnSync(manager, command, { stdio: "inherit" });
  if (done.status !== 0) return done.status ?? 1;
  const verify = spawnSync("ai-eng", ["--version"], { encoding: "utf8" });
  process.stdout.write(`✓ ai-eng ${verify.stdout?.trim() ?? latest} · trust is signed by the registry, not by ai-eng\n`);
  process.stdout.write("⚠ if this repo still runs assets from the previous version → ai-eng update\n");
  return 0;
}
