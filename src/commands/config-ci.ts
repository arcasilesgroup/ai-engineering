// The CI half of `ai-eng config`: [ci].provider rewritten in place, then the gate
// swapped — the new provider's file written, the old one's taken back by the same
// ownership rules update and uninstall use. The rest of config.toml is the user's.

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { PassThrough } from "node:stream";
import { isCancel, select } from "@clack/prompts";
import { install, lockText, parseLock, sha256, type Lock, type PlanEntry } from "../install.ts";
import { CI_PROVIDERS, ciProvider, isCiProvider, type CiProvider } from "../env.ts";
import { AZURE_PORTAL_STEPS, CI_PICK_MESSAGE, ciEntries, ciOptions, installLineRow, refuseLine } from "./init-shared.ts";
import { sweepRetiredAssets } from "./uninstall.ts";
import * as ui from "../ui.ts";

/** The CI picker, preselected on what the repo declares. Null when cancelled. */
export async function pickCi(input: NodeJS.ReadStream | PassThrough, root: string): Promise<CiProvider | null> {
  const current = ciProvider(root);
  const answer = await select({
    message: CI_PICK_MESSAGE,
    options: ciOptions(),
    initialValue: typeof current === "string" ? current : "github-actions",
    input: input as never,
  });
  return isCancel(answer) ? null : answer;
}

/** `--ci <value>`: refuse what names no provider, before anything is written. */
export function changeCiFromFlag(root: string, value: string): number {
  if (isCiProvider(value)) return changeCi(root, value);
  ui.fail(`--ci "${value}" is not a CI provider: use ${CI_PROVIDERS.join(", ")}.`);
  ui.end("Nothing changed.");
  return 2;
}

export function changeCi(root: string, next: CiProvider): number {
  if (ciProvider(root) === next) {
    ui.section("CI unchanged", [{ mark: "muted", text: next }]);
    ui.end("Nothing changed.");
    return 0;
  }
  const configPath = join(root, ".ai-engineering", "config.toml");
  const rewritten = withCiProvider(readFileSync(configPath, "utf8"), next);
  if (rewritten === null) {
    ui.fail(".ai-engineering/config.toml is laid out in a way this command cannot rewrite without changing more than [ci].provider.");
    ui.info(`Edit it by hand: under [ci], set provider = "${next}", then run ai-eng update`);
    ui.end("Nothing changed.");
    return 2;
  }
  writeFileSync(configPath, rewritten);
  ui.section("CI changed", swapGate(root, next), `provider: ${next}`);
  if (next === "azure-pipelines") ui.section("Azure DevOps — two steps in the portal", AZURE_PORTAL_STEPS);
  ui.end("Next: review the diff, then commit it.");
  return 0;
}

/** config.toml with [ci].provider set, or null when the edit would change anything else.
 *  Judged by meaning, like the surfaces rewrite: the result must parse and differ from
 *  the original in that one key — so an unusual layout is refused, never mangled. */
export function withCiProvider(raw: string, next: CiProvider): string | null {
  const assignment = `provider = "${next}"`;
  const lines = raw.split("\n");
  const header = lines.findIndex((line) => /^\s*\[ci\]\s*(#.*)?\r?$/.test(line));
  let rewritten: string;
  if (header === -1) {
    // A repo governed before the choice existed: its config has no [ci] table yet.
    const base = raw === "" || raw.endsWith("\n") ? raw : `${raw}\n`;
    rewritten = `${base}\n[ci]\n${assignment}\n`;
  } else {
    const tableEnd = lines.findIndex((line, index) => index > header && /^\s*\[/.test(line));
    const last = tableEnd === -1 ? lines.length : tableEnd;
    const key = lines.findIndex((line, index) => index > header && index < last && /^\s*provider\s*=/.test(line));
    if (key === -1) lines.splice(header + 1, 0, assignment);
    else lines[key] = lines[key]!.replace(/^(\s*provider\s*=\s*)"[^"]*"/, `$1"${next}"`);
    rewritten = lines.join("\n");
  }
  try {
    const before = Bun.TOML.parse(raw) as Record<string, unknown>;
    const after = Bun.TOML.parse(rewritten) as Record<string, unknown>;
    const tableBefore = before["ci"];
    const ci = typeof tableBefore === "object" && tableBefore !== null && !Array.isArray(tableBefore) ? tableBefore : {};
    return Bun.deepEquals(after, { ...before, ci: { ...ci, provider: next } }) ? rewritten : null;
  } catch {
    return null;
  }
}

/** Write the new gate, take back every other provider's gate ai-eng wrote, and move the
 *  lock with them so uninstall and update see the same ownership. */
function swapGate(root: string, next: CiProvider): ui.Row[] {
  const rows: ui.Row[] = [];
  const lockPath = join(root, ".ai-engineering", "ai-eng.lock");
  const lock: Lock | null = existsSync(lockPath) ? parseLock(readFileSync(lockPath, "utf8")) : null;
  const entries = ciEntries(next);
  const report = install(root, entries, (path) => {
    const recorded = lock?.assets[path];
    return recorded ? `sha256:${recorded}` : null;
  });
  for (const path of report.written) rows.push({ mark: "ok", text: `${path} written` });
  for (const path of report.untouched) rows.push({ mark: "muted", text: `${path} already current` });
  for (const path of report.yours) rows.push({ mark: "warn", text: `${path} kept`, dim: "already here and not written by ai-eng — yours; no ai-eng gate was written" });
  for (const refused of report.refused) rows.push(installLineRow(refuseLine(refused)));

  const others: PlanEntry[] = CI_PROVIDERS.filter((provider) => provider !== next).flatMap(ciEntries);
  // Without a lock, only bytes identical to ai-eng's say a file is ai-eng's.
  const assets = lock?.assets ?? Object.fromEntries(others.map((entry) => [entry.path, sha256(entry.ours)]));
  const retiring = others.map((entry) => entry.path).filter((path) => {
    if (assets[path] === undefined) return false;
    if (lock !== null) return true;
    const absolute = join(root, path);
    return existsSync(absolute) && sha256(readFileSync(absolute, "utf8")) === assets[path];
  });
  const kept = sweepRetiredAssets(root, retiring, assets, rows);

  if (lock !== null) {
    for (const path of retiring) if (!kept.includes(path)) delete lock.assets[path];
    const notOurs = new Set([...report.yours, ...report.refused.map((refused) => refused.path)]);
    for (const entry of entries) if (!notOurs.has(entry.path)) lock.assets[entry.path] = sha256(entry.ours);
    writeFileSync(lockPath, lockText(lock));
  }
  return rows;
}
