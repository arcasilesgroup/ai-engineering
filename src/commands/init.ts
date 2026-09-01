import { existsSync, readFileSync, writeFileSync, symlinkSync, chmodSync } from "node:fs";
import { spawnSync, execFileSync } from "node:child_process";
// `ai-eng init` — one verb, two phases (§14.0a). Outside a repo: phase 1, the
// machine (canon + mirrors). Inside a repo: both phases — first the canon (missing
// is installed, never aborts), then the project contract. Idempotent: re-init
// offers update, never overwrites an edited file (§14.5b's six paths).

import { join } from "node:path";
import { multiselect, select, spinner, note, isCancel, confirm } from "@clack/prompts";
import { SURFACES, surfaceCanGovern, installCanon } from "../surfaces/adapters.ts";
import { plant, buildLock, lockText } from "../plant.ts";
import { home } from "../env.ts";
import { updateMain } from "./update.ts";
import { planEntries, contractEntries } from "./init-shared.ts";
import { showLogo } from "../branding.ts";
import { VERSION } from "../version.ts";

function isGitRepo(cwd: string): boolean {
  return existsSync(join(cwd, ".git"));
}

function scaffoldProject(surfaces: string[]): string[] {
  const cwd = process.cwd();
  const lines: string[] = [];
  // Contract files: written ONCE. plant() skips anything the user already has.
  const contractReport = plant(cwd, contractEntries(new Date().toISOString().slice(0, 10)));
  for (const written of contractReport.written) lines.push(`✓ ${written} (contract)`);
  for (const untouched of contractReport.untouched) lines.push(`· ${untouched} — yours, untouched`);
  // CLAUDE.md: symlink to AGENTS.md where the OS allows, one-line import where not.
  const claudePath = join(cwd, "CLAUDE.md");
  if (!existsSync(claudePath)) {
    try {
      symlinkSync("AGENTS.md", claudePath);
      lines.push("✓ CLAUDE.md → symlink to AGENTS.md");
    } catch {
      writeFileSync(claudePath, "@AGENTS.md\n");
      lines.push("✓ CLAUDE.md → one-line @AGENTS.md (FS refused the symlink)");
    }
  }
  const entries = planEntries(surfaces);
  const report = plant(cwd, entries);
  for (const written of report.written) lines.push(`✓ ${written}`);
  for (const conflict of report.conflicts) lines.push(`⚠ ${conflict} — edited by you: 3-way diff required, not touched`);
  // Hook shims must be executable or git silently ignores them (measured).
  for (const shim of ["pre-commit", "commit-msg", "pre-push"]) {
    const shimPath = join(cwd, ".git", "hooks", shim);
    if (existsSync(shimPath)) chmodSync(shimPath, 0o755);
  }
  lines.push("✓ git floor → .git/hooks/{pre-commit,commit-msg,pre-push} (marker-managed)");
  // core.hooksPath is NOT redirected: the hooks live in their standard location.
  try {
    const wired = spawnSync("git", ["-C", cwd, "config", "core.hooksPath"], { encoding: "utf8" });
    if ((wired.stdout ?? "").trim() !== "") {
      execFileSync("git", ["-C", cwd, "config", "--unset", "core.hooksPath"], { cwd });
      lines.push("✓ core.hooksPath custom redirect removed (hooks now standard .git/hooks/)");
    }
  } catch {
    /* no custom hooksPath: nothing to clean */
  }
  const lock = buildLock(entries, VERSION);
  writeFileSync(join(cwd, ".ai-engineering", "ai-eng.lock"), lockText(lock));
  lines.push(`✓ .ai-engineering/ai-eng.lock (${Object.keys(lock.assets).length} assets with sha256)`);
  return lines;
}

export async function initMain(flags: { yes?: boolean; global?: boolean; surface?: string[] }): Promise<number> {
  showLogo(VERSION);
  const cwd = process.cwd();
  const inRepo = isGitRepo(cwd) || existsSync(join(cwd, ".ai-engineering"));
  // Phase 1: global, or missing canon — installs/repairs the machine side either way.
  // home() (not HOME) so AI_ENG_HOME test installs stay isolated.
  const canonDir = join(home(), "skills");
  if (flags.global || !existsSync(canonDir)) {
    installCanon(VERSION).forEach((line) => process.stdout.write(`${line}\n`));
  }
  // Outside a repo: a bare folder is not a refusal — §14.1 runs init in a bare
  // folder and init creates the repo itself (confirm, or --yes to proceed).
  if (!inRepo) {
    const ok = flags.yes === true || (await confirm({ message: "No git repo here. Create one? (git init -q)" }));
    if (isCancel(ok) || ok === false) {
      note("Inside a repo, ai-eng init governs it too.", "next");
      return 0;
    }
    try {
      execFileSync("git", ["init", "-q"], { cwd });
      process.stdout.write("✓ git init -q\n");
    } catch {
      process.stderr.write("git init failed — aborting: without a repo there is no floor.\n");
      return 2;
    }
  }
  // ── Phase 2: the repo is governed — idempotent re-init never tramples your work (§14.5b).
  if (existsSync(join(cwd, ".ai-engineering", "config.toml"))) {
    const action = await select({
      message: "This repo is already governed.",
      options: [
        { value: "exit", label: "Exit" },
        { value: "update", label: "Re-plant assets (update)" },
      ],
    });
    if (isCancel(action) || action === "exit") return 0;
    return updateMain();
  }
  let picked: string[];
  if (flags.yes === true) {
    picked = flags.surface && flags.surface.length > 0 ? flags.surface : ["claude-code"];
  } else {
    const answer = await multiselect({
      message: "Which agent surfaces do you use?",
      options: SURFACES.map((s) => ({
        value: s.id,
        label: s.label,
        hint: s.tier === "core" ? "✔ core" : s.tier === "experimental" ? "⚠ experimental" : s.tier === "skills-only" ? "skills only" : "best-effort",
      })),
      required: true,
    });
    if (isCancel(answer)) return 0;
    picked = answer;
  }
  // Abort before promising what a surface cannot deliver (§13).
  for (const id of picked) {
    const surface = SURFACES.find((s) => s.id === id);
    if (surface && !surfaceCanGovern(surface)) {
      process.stderr.write(`"${id}" cannot deny tools: the guards have nowhere to run. Use a core surface.\n`);
      return 2;
    }
  }
  const sp = spinner();
  sp.start("Scaffolding governance…");
  const lines = scaffoldProject(picked);
  sp.stop("Scaffolded.");
  for (const line of lines) process.stdout.write(`${line}\n`);
  // The first commit of the contract: the lockfile and the Receipt-Id trailer get
  // their baseline from second zero (§08).
  try {
    execFileSync("git", ["add", "-A"], { cwd });
    execFileSync("git", ["commit", "-q", "-m", `chore(ai-eng): plant governance ${VERSION}`, "--no-verify", "--no-gpg-sign"], { cwd });
    process.stdout.write("✓ first contract commit\n");
  } catch {
    process.stdout.write("· contract commit pending (do it yourself with git)\n");
  }
  process.stdout.write("\nTwo steps I can't do for you:\n");
  process.stdout.write("  1. Trust the workspace in your surface (without trust, hooks do not run)\n");
  process.stdout.write("  2. ai-eng doctor — verify the chain responds\n");
  return 0;
}

/** Canon version read for doctor/notice paths. */
export function canonVersion(): string {
  try {
    const path = join(process.env.HOME ?? "", ".ai-engineering", "version.json");
    return String(JSON.parse(readFileSync(path, "utf8")).version ?? "unknown");
  } catch {
    return "unknown";
  }
}
