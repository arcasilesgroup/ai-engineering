// `ai-eng update` — re-install this repo's assets from the installed binary. ZERO
// network: the payload leaves the binary the user already installed (§14.3). What
// is the user's (AGENTS.md, DECISIONS.md, spec/plan, arch.rules) is never touched.
// It refreshes BOTH halves ai-eng installed: the machine side (the global canon and
// its mirrors) and this repo's assets. cli-ux-14 work point 04: compute the sync
// plan first, show it, resolve conflicts with the human (keep-yours default),
// confirm Apply, then write — never the reverse. Human-facing lines go through
// src/ui.ts.

import { existsSync, readFileSync, writeFileSync, chmodSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { select, confirm, isCancel } from "@clack/prompts";
import { install, buildLock, lockText, parseLock, sha256 } from "../install.ts";
import type { PlanEntry } from "../install.ts";
import { repoRoot, enabledSurfaces, home } from "../env.ts";
import { canonDrift } from "../embed.ts";
import { installCanon } from "../surfaces/adapters.ts";
import { planEntries } from "./init-shared.ts";
import { VERSION } from "../version.ts";
import * as ui from "../ui.ts";
import { scriptedInput } from "../ui.ts";

export type SyncPlan = {
  current: string[]; // byte-identical to what this binary installs
  updates: string[]; // previous version of ours on disk → safe update
  fresh: string[]; // not on disk yet
  conflicts: string[]; // user-edited AND ours changed since their install
  verbatim: string[]; // subset of current that byte-matches ours — provably ours
};
export function syncPlan(entries: PlanEntry[], root: string, previousAssets: Record<string, string>): SyncPlan {
  const plan: SyncPlan = { current: [], updates: [], fresh: [], conflicts: [], verbatim: [] };
  for (const entry of entries) {
    const absolute = join(root, entry.path);
    if (!existsSync(absolute)) {
      plan.fresh.push(entry.path);
      continue;
    }
    const currentHash = sha256(readFileSync(absolute, "utf8"));
    if (currentHash === sha256(entry.ours)) {
      plan.current.push(entry.path);
      plan.verbatim.push(entry.path);
      continue;
    }
    const recorded = previousAssets[entry.path];
    if (!recorded) {
      plan.current.push(entry.path); // we never installed it: the user's own
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

export async function updateMain(opts: { yes?: boolean } = {}): Promise<number> {
  const input = scriptedInput();
  const root = repoRoot();
  if (!root) {
    process.stderr.write("update: you are not in a governed repo.\n");
    return 2;
  }
  const lockPath = join(root, ".ai-engineering", "ai-eng.lock");
  // A missing lock is a recoverable state, not an abort: `uninstall` (project
  // scope) deletes the lock but keeps config.toml, and init then hands off here
  // — "no lock, run init" was a deadlock (measured tests2 2026-09-03). Empty
  // previous assets = nothing recorded as ours: absent files install fresh, any
  // file on disk is treated as the user's, and the lock is rebuilt at the end.
  const previous = existsSync(lockPath) ? parseLock(readFileSync(lockPath, "utf8")) : { version: "", assets: {} };
  const surfaces = enabledSurfaces();
  const entries: PlanEntry[] = planEntries(surfaces);
  const plan = syncPlan(entries, root, previous.assets);
  const pending = [...plan.updates, ...plan.fresh];

  // The frame states the repo's state in plain words: "unknown" was a fallback lying
  // about a recoverable state, and the old internal verb never reached a user anyway.
  const origin = !existsSync(lockPath)
    ? "no ai-eng.lock here yet: ai-eng will create its files fresh"
    : previous.version
      ? `previous install by ai-eng ${previous.version}`
      : "previous install by an older ai-eng";
  ui.frame(`ai-eng ${VERSION} · ${origin}`);
  // The machine side travels with the repo side. The canon is what a surface
  // actually reads, and it drifts the moment the binary ships different skills —
  // twenty stale skills reported as "all assets current" was the gap, and
  // repairing it by hand meant knowing that `init --global` does it (measured
  // 2026-09-11). Same predicate init and doctor use: health is a measurement.
  const canon = canonDrift(home());
  const canonHealthy = canon.drift === 0 && canon.missing === 0 && canon.stale === 0;
  if (!canonHealthy) {
    const rows = installCanon(VERSION).map((line): ui.Row => ({ mark: "ok", text: line.replace(/^✓ /, "") }));
    const why = [`${canon.drift} drifted`, `${canon.missing} missing`, ...(canon.stale > 0 ? [`${canon.stale} stale`] : [])].join(" · ");
    ui.section("global canon outdated or incomplete — re-installing", rows, why);
  }
  if (pending.length === 0 && plan.conflicts.length === 0) {
    ui.ok(canonHealthy ? `all ${plan.current.length} assets current — nothing to sync` : "repo assets current — the machine side was the work");
    ui.end(`Next: ai-eng doctor — verify the chain responds`);
    return 0;
  }
  // Concept blocks, not line-spam (§14.3 mockup): one block per idea. And a
  // question only appears when there is a real decision left to make:
  // sync-plan when files change, ONE conflict decision, Apply only when
  // something will actually be written.
  if (pending.length > 0) {
    const rows: ui.Row[] = [
      ...plan.updates.map((path): ui.Row => ({ mark: "ok", text: path, dim: `new version from binary ${VERSION}` })),
      ...plan.fresh.map((path): ui.Row => ({ mark: "ok", text: path, dim: "new asset" })),
    ];
    if (plan.current.length > 0) {
      rows.push({ mark: "sub", text: ui.pathList(plan.current) }, { mark: "muted", text: `${plan.current.length} already current or yours — untouched` });
    }
    ui.section("What needs to sync", rows, `${pending.length} update${pending.length === 1 ? "" : "s"}`);
  }

  // Conflict resolution BEFORE any write: ONE decision for the whole set —
  // the same question N times is noise, and keep-yours is the default:
  // deleting what the user edited is the worst class of bug a governance
  // tool can have. The file list rides inside the question itself.
  let takeAll = false;
  if (plan.conflicts.length > 0) {
    // --yes resolves conservatively: keep-yours. Unattended recovery may install
    // what is absent but never overwrites what the human edited.
    const choice = opts.yes === true ? "keep" : await select({
      message: `${plan.conflicts.length === 1 ? "A file" : `${plan.conflicts.length} files`} patched by you also changed in binary ${VERSION}. What wins?\n${ui.pathList(plan.conflicts)}`,
      options: [
        { value: "keep", label: "Keep mine everywhere", hint: "your patches stay; the new version is one git revert away" },
        { value: "take", label: "Take the new version everywhere", hint: "your edits survive in git history" },
      ],
      input: input as never,
    });
    if (isCancel(choice)) {
      ui.cancelled("Nothing written.");
      return 0;
    }
    takeAll = choice === "take";
  }
  const takeCount = takeAll ? plan.conflicts.length : 0;
  const writeCount = pending.length + takeCount;
  if (writeCount === 0) {
    // Keep-mine everywhere with nothing else pending: the repo is already
    // exactly as you left it. Say so and close — no lock rewrite, no commit.
    ui.section("Kept", [{ mark: "info", text: "your patches stay", dim: ui.pathList(plan.conflicts) }, { mark: "muted", text: "nothing written — the repo is exactly as you left it" }]);
    ui.end("Next: ai-eng doctor — verify the chain responds");
    return 0;
  }
  const apply = opts.yes === true ? true : await confirm({ message: `Apply? ${writeCount} write${writeCount === 1 ? "" : "s"}${plan.conflicts.length > 0 && takeCount === 0 ? " · your patches stay untouched" : ""}`, initialValue: true, input: input as never });
  if (isCancel(apply) || apply === false) {
    ui.cancelled("Nothing written.");
    return 0;
  }
  // Writes: keep-yours means install() must not touch the conflict at all — the
  // entry comes out of the plan AND out of the lock (a kept file is the user's;
  // recording our hash for it would make the NEXT update overwrite their edit in
  // silence). take means install() writes ours over the edit: that is the force
  // channel — only a human decision reaches it.
  const take = () => takeAll;
  const writable = takeAll ? entries : entries.filter((entry) => !plan.conflicts.includes(entry.path));
  const report = install(root, writable, (path) => {
    const hash = previous.assets[path];
    return hash ? `sha256:${hash}` : null;
  }, take);
  // Freshly written git shims must stay executable or git silently ignores them.
  for (const shim of ["pre-commit", "commit-msg", "pre-push"]) {
    const shimPath = join(root, ".git", "hooks", shim);
    if (existsSync(shimPath)) chmodSync(shimPath, 0o755);
  }
  const keptPaths = takeAll ? [] : plan.conflicts;
  const keptCount = keptPaths.length;
  const resultRows: ui.Row[] = [
    { mark: "ok", text: `${report.written.length} asset${report.written.length === 1 ? "" : "s"} synced`, dim: "sha256 recorded in ai-eng.lock" },
    ...(keptCount > 0 ? [{ mark: "info", text: "kept yours", dim: keptPaths.join("  ·  ") } satisfies ui.Row] : []),
  ];
  ui.section("Synced", resultRows, `${plan.conflicts.length} conflict${plan.conflicts.length === 1 ? "" : "s"} resolved · 0 files of yours touched otherwise`);
  // The lock is the ownership ledger: it may only claim files this run actually
  // made ours — written now, taken over by explicit human resolution, or
  // already byte-identical to ours (verbatim). "current" also holds files
  // install() calls untouched/user's (the no-lock recovery state): recording
  // those made the next update report a false conflict and uninstall strip a
  // file the binary never owned (measured 2026-09-03).
  const oursNow = new Set([...report.written, ...plan.verbatim]);
  const lock = buildLock(
    entries.filter((entry) => (takeAll || !plan.conflicts.includes(entry.path)) && oursNow.has(entry.path)),
    VERSION,
    { spec_sha256: previous.spec_sha256, base_sha: previous.base_sha },
  );
  writeFileSync(lockPath, lockText(lock));
  let commitLine = "commit skipped — nothing staged or git refused (your call to commit by hand)";
  try {
    spawnSync("git", ["-C", root, "add", "-A"]);
    const committed = spawnSync("git", ["-C", root, "commit", "-q", "-m", `chore(ai-eng): assets → ${VERSION}`, "--no-verify", "--no-gpg-sign"]);
    if (committed.status === 0) commitLine = `chore(ai-eng): assets → ${VERSION} · git revert is the rollback`;
  } catch {
    /* git absent or refused — the hand-commit note above stands */
  }
  ui.section("Recorded", [{ mark: "ok", text: `ai-eng.lock · ${Object.keys(lock.assets).length} assets with sha256` }, { mark: "ok", text: `commit: ${commitLine}` }]);
  ui.end(`Next: ai-eng doctor — verify the chain still works with the new hooks`);
  return 0;
}
