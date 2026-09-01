// `ai-eng update` — re-plant this repo's assets from the installed binary. ZERO
// network: the payload leaves the binary the user already installed (§14.3). What
// is the user's (AGENTS.md, DECISIONS.md, spec/plan, arch.rules) is never touched.
// cli-ux-14 work point 04: compute the sync plan first, show it, resolve conflicts
// with the human (keep-yours default), confirm Apply, then write — never the
// reverse. Human-facing lines go through src/ui.ts.

import { existsSync, readFileSync, writeFileSync, chmodSync } from "node:fs";
import { join } from "node:path";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import { select, confirm, isCancel } from "@clack/prompts";
import { plant, buildLock, lockText, parseLock } from "../plant.ts";
import type { PlanEntry } from "../plant.ts";
import { repoRoot, loadConfig } from "../env.ts";
import { planEntries } from "./init-shared.ts";
import { VERSION } from "../version.ts";
import * as ui from "../ui.ts";

type SyncPlan = {
  current: string[]; // byte-identical to what this binary plants
  updates: string[]; // previous version of ours on disk → safe update
  fresh: string[]; // not on disk yet
  conflicts: string[]; // user-edited AND ours changed since their plant
};

/** Pure: what would change, before anything is written. The lock's recorded
 *  hashes tell previous-ours apart from the user's edits. */
export function syncPlan(entries: PlanEntry[], root: string, previousAssets: Record<string, string>): SyncPlan {
  const plan: SyncPlan = { current: [], updates: [], fresh: [], conflicts: [] };
  for (const entry of entries) {
    if (entry.mode === "symlink") continue;
    const absolute = join(root, entry.path);
    if (!existsSync(absolute)) {
      plan.fresh.push(entry.path);
      continue;
    }
    const currentHash = createHash("sha256").update(readFileSync(absolute)).digest("hex");
    if (currentHash === createHash("sha256").update(entry.ours).digest("hex")) {
      plan.current.push(entry.path);
      continue;
    }
    const recorded = previousAssets[entry.path];
    if (!recorded) {
      plan.current.push(entry.path); // we never planted it: the user's own
      continue;
    }
    if (currentHash === recorded) {
      plan.updates.push(entry.path); // exact previous version: safe update
      continue;
    }
    plan.conflicts.push(entry.path);
  }
  return plan;
}

export async function updateMain(): Promise<number> {
  const root = repoRoot();
  if (!root) {
    process.stderr.write("update: you are not in a governed repo.\n");
    return 2;
  }
  const lockPath = join(root, ".ai-engineering", "ai-eng.lock");
  if (!existsSync(lockPath)) {
    process.stderr.write("update: no ai-eng.lock — run ai-eng init first.\n");
    return 2;
  }
  const previous = parseLock(readFileSync(lockPath, "utf8"));
  const config = loadConfig();
  const surfaces = (config["surfaces"]?.["enabled"] as unknown as string[] | undefined) ?? ["claude-code"];
  const entries: PlanEntry[] = planEntries(Array.isArray(surfaces) ? surfaces : ["claude-code"]);
  const plan = syncPlan(entries, root, previous.assets);
  const pending = [...plan.updates, ...plan.fresh];

  ui.frame(`ai-eng ${VERSION} · assets planted by ${previous.version || "unknown"}`);
  if (pending.length === 0 && plan.conflicts.length === 0) {
    ui.ok(`all ${plan.current.length} assets current — nothing to sync`);
    ui.end(`Next: ai-eng doctor — verify the chain responds`);
    return 0;
  }
  ui.info("What needs to sync:");
  for (const path of plan.updates) ui.ok(`${path} — new version from binary ${VERSION}`);
  for (const path of plan.fresh) ui.ok(`${path} — new asset`);
  for (const path of plan.current) ui.info(`${path} (already current or yours)`);
  for (const path of plan.conflicts) ui.warn(`${path} — patched by you`);

  // Conflict resolution BEFORE any write: keep-yours is the default — deleting
  // what the user edited is the worst class of bug a governance tool can have.
  const resolutions = new Map<string, "keep" | "take">();
  for (const path of plan.conflicts) {
    const choice = select({
      message: `${path} — you patched it, the binary changed it. What wins?`,
      options: [
        { value: "keep", label: "Keep mine" },
        { value: "take", label: "Take the new version (mine is in git history)" },
      ],
    });
    if (isCancel(choice)) {
      ui.cancelled("Nothing written.");
      return 0;
    }
    resolutions.set(path, choice === "take" ? "take" : "keep");
  }
  const apply = await confirm({ message: `Apply? (${pending.length} write${pending.length === 1 ? "" : "s"}, ${plan.conflicts.length} conflict${plan.conflicts.length === 1 ? "" : "s"})`, initialValue: true });
  if (isCancel(apply) || apply === false) {
    ui.cancelled("Nothing written.");
    return 0;
  }

  // Writes: keep-yours means plant() must not touch the conflict — filter it
  // out of the entries it sees; take-new means the conflict is planted as-is.
  const writable = entries.filter((entry) => resolutions.get(entry.path ?? entry) !== "keep");
  const report = plant(root, writable, (path) => {
    const hash = previous.assets[path];
    return hash ? `sha256:${hash}` : null;
  });
  for (const [path, resolution] of resolutions) {
    if (resolution === "keep") ui.info(`${path} — kept yours`);
  }
  // Freshly written git shims must stay executable or git silently ignores
  // them (measured at init; update re-plants the same paths).
  for (const shim of ["pre-commit", "commit-msg", "pre-push"]) {
    const shimPath = join(root, ".git", "hooks", shim);
    if (existsSync(shimPath)) chmodSync(shimPath, 0o755);
  }
  ui.ok(`${report.written.length} assets synced · ${resolutions.size} conflict${resolutions.size === 1 ? "" : "s"} resolved · 0 files of yours touched otherwise`);
  const lock = buildLock(entries, VERSION);
  writeFileSync(lockPath, lockText(lock));
  ui.ok(`ai-eng.lock rewritten (${Object.keys(lock.assets).length} assets)`);
  // The update lands as a commit: git revert is the rollback (§14.3).
  try {
    spawnSync("git", ["-C", root, "add", "-A"]);
    const committed = spawnSync("git", ["-C", root, "commit", "-q", "-m", `chore(ai-eng): assets → ${VERSION}`, "--no-verify", "--no-gpg-sign"]);
    if (committed.status === 0) ui.ok(`commit: chore(ai-eng): assets → ${VERSION}`);
    else ui.info("commit skipped — nothing staged or git refused (your call to commit by hand)");
  } catch {
    ui.info("commit skipped — do it by hand with git");
  }
  ui.end(`Next: ai-eng doctor — verify the chain still works with the new hooks`);
  return 0;
}
