import { existsSync, readFileSync, writeFileSync, symlinkSync, chmodSync } from "node:fs";
import { spawnSync, execFileSync } from "node:child_process";
// `ai-eng init` — one verb, two phases (§14.0a). Outside a repo: phase 1, the
// machine (canon + mirrors). Inside a repo: both phases — first the canon (missing
// is installed, never aborts), then the project contract. Idempotent: re-init
// offers update/config/exit, never overwrites an edited file (§14.5b's six paths).
// Every line a human sees goes through src/ui.ts: the frame must survive the
// whole flow (cli-ux-14 work point 02).

import { join } from "node:path";
import { multiselect, select, groupMultiselect, isCancel } from "@clack/prompts";
import { scriptedInput } from "../ui.ts";
import { SURFACES, surfaceCanGovern, installCanon, type Surface } from "../surfaces/adapters.ts";
import { plant, buildLock, lockText } from "../plant.ts";
import { home, versionFile } from "../env.ts";
import { planEntries, contractEntries } from "./init-shared.ts";
import { updateMain } from "./update.ts";
import { VERSION } from "../version.ts";
import * as ui from "../ui.ts";
import { BOOSTER_GROUPS, printCommands } from "../boosters.ts";

function isGitRepo(cwd: string): boolean {
  return existsSync(join(cwd, ".git"));
}

/** The mockup hint per surface: tier marker + capability note, mapped from
 *  surfaces.json — never hardcoded per-id. */
/** Surfaces already present in this project, detected by their on-disk markers:
 *  a .claude/ dir means Claude Code, .agents/ hooks mean OMP, .opencode/ means
 *  OpenCode, .cursor/ means Cursor. Ticked-by-default in the init multiselect. */
function detectedSurfaces(cwd: string): string[] {
  const detected: string[] = [];
  if (existsSync(join(cwd, ".claude"))) detected.push("claude-code");
  if (existsSync(join(cwd, ".agents", "hooks"))) detected.push("oh-my-pi");
  if (existsSync(join(cwd, ".opencode"))) detected.push("opencode");
  if (existsSync(join(cwd, ".cursor"))) detected.push("cursor");
  return detected;
}

function surfaceHint(s: Surface): string {
  const capabilities: string[] = [];
  if (s.can.deny) capabilities.push("deny");
  if (s.can.rewriteIn) capabilities.push("rewrite input");
  if (s.can.rewriteOut) capabilities.push("rewrite output");
  const marker = s.tier === "core" ? "✔ core" : s.tier === "experimental" ? "⚠ experimental" : s.tier === "skills-only" ? "skills only" : "best-effort";
  return capabilities.length > 0 ? `${marker} — ${capabilities.join(", ")}` : marker;
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
      lines.push("✓ CLAUDE.md → @AGENTS.md (symlink unsupported)");
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
    spawnSync("git", ["-C", cwd, "config", "--unset", "core.hooksPath"]);
  } catch {
    /* no custom hooksPath: nothing to clean */
  }
  const lock = buildLock(entries, VERSION);
  writeFileSync(join(cwd, ".ai-engineering", "ai-eng.lock"), lockText(lock));
  lines.push(`✓ .ai-engineering/ai-eng.lock (${Object.keys(lock.assets).length} assets with sha256)`);
  return lines;
}

export async function initMain(flags: { yes?: boolean; global?: boolean; surface?: string[] }): Promise<number> {
  const input = scriptedInput();
  const confirmWithInput = (message: string, initial: boolean) => ui.confirmDefault(message, initial, input as never);
  ui.frame(`{ai} Engineering ${VERSION}`);
  const cwd = process.cwd();
  const inRepo = isGitRepo(cwd) || existsSync(join(cwd, ".ai-engineering"));
  // Phase 1: global, or missing canon — installs/repairs the machine side either way.
  // home() (not HOME) so AI_ENG_HOME test installs stay isolated. The status
  // line always prints: the user must see the machine is healthy before the
  // repo work starts (user feedback 2026-09-01 #7).
  const canonDir = join(home(), "skills");
  const canonHealthy = existsSync(join(canonDir, "ai-brainstorm", "SKILL.md"));
  if (flags.global || !existsSync(canonDir)) {
    installCanon(VERSION).forEach((line) => ui.ok(line.replace(/^✓ /, "")));
  } else if (canonHealthy) {
    ui.ok(`global canon intact at ${home()} (ai-eng ${canonVersion()}) — nothing to install`);
  } else {
    ui.warn(`global canon at ${home()} looks incomplete — re-installing`);
    installCanon(VERSION).forEach((line) => ui.ok(line.replace(/^✓ /, "")));
  }
  if (flags.global) {
    ui.end("Machine side done. Inside a repo, ai-eng init governs the project too.");
    return 0;
  }
  // Outside a repo: a bare folder is not a refusal — §14.1 runs init in a bare
  // folder and init creates the repo itself (confirm, or --yes to proceed).
  if (!inRepo) {
    const ok = flags.yes === true || (await confirmWithInput("No git repo here. Create one? (git init -q)", true));
    if (isCancel(ok) || ok === false) {
      ui.cancelled("Inside a repo, ai-eng init governs it too.");
      return 0;
    }
    try {
      execFileSync("git", ["init", "-q"], { cwd });
      ui.ok("git init -q");
    } catch {
      ui.fail("git init failed — aborting: without a repo there is no floor.");
      return 2;
    }
  }

  // ── Phase 2: the repo is governed — idempotent re-init never tramples your work (§14.5b).
  if (existsSync(join(cwd, ".ai-engineering", "config.toml"))) {
    const action = await select({
      message: "This project is already governed. What do you want to do?",
      options: [
        { value: "update", label: "Rewrite ai-eng's files from the installed binary (ai-eng update)", hint: "overwrites hooks, settings, CI workflow — never your AGENTS.md or DECISIONS.md" },
        { value: "config", label: "Change which agent surfaces this project is governed on (ai-eng config)" },
        { value: "exit", label: "Exit — change nothing" },
      ],
      input: input as never,
    });
    if (isCancel(action) || action === "exit") {
      ui.cancelled("Nothing changed.");
      return 0;
    }
    if (action === "config") return configMain({});
    ui.end("Running ai-eng update — rewriting the files ai-eng owns:");
    return await updateMain();
  }
  let picked: string[];
  if (flags.yes === true) {
    picked = flags.surface && flags.surface.length > 0 ? flags.surface : ["claude-code"];
  } else {
    const answer = await multiselect({
      message: "Which agent surfaces is this project governed on? (ticked = detected)",
      options: SURFACES.map((s) => ({ value: s.id, label: s.label, hint: surfaceHint(s) })),
      initialValues: detectedSurfaces(cwd),
      required: true,
      input: input as never,
    });
    if (isCancel(answer)) {
      ui.cancelled();
      return 0;
    }
    picked = answer;
  }
  // Boosters: offered, never installed (§14.1). ai-eng prints the exact command
  // for what the user ticks; what asks no permission does not get installed.
  if (flags.yes !== true) {
    const boost = await groupMultiselect({
      message: "Optional third-party harness boosters?",
      options: Object.fromEntries(BOOSTER_GROUPS.map((group) => [group.title, group.items.map((b) => ({ value: b.id, label: b.label, hint: b.hint }))])),
      required: false,
      selectableGroups: false,
      input: input as never,
    });
    if (isCancel(boost)) {
      ui.cancelled();
      return 0;
    }
    if (boost.length > 0) {
      ui.info("Run these to install what you ticked (ai-eng never installs third-party):");
      for (const command of printCommands(boost)) ui.info(`  ${command}`);
    }
  }
  // Abort before promising what a surface cannot deliver (§13).
  for (const id of picked) {
    const surface = SURFACES.find((s) => s.id === id);
    if (surface && !surfaceCanGovern(surface)) {
      ui.fail(`"${id}" cannot deny tools: the guards have nowhere to run. Use a core surface.`);
      return 2;
    }
  }
  const sp = ui.spinner();
  sp.start("Scaffolding governance…");
  const lines = scaffoldProject(picked);
  sp.stop("Scaffolded.");
  for (const line of lines) {
    if (line.startsWith("⚠")) ui.warn(line.slice(2));
    else if (line.startsWith("·")) ui.info(line.slice(2));
    else ui.ok(line.replace(/^✓ /, ""));
  }
  // Bootstrap note (§14.1 mockup): no src/ yet — arch-tests hold off until there is code.
  if (!existsSync(join(cwd, "src"))) {
    ui.info("No code yet → arch-tests in bootstrap mode (no failures on empty).");
    ui.info("doctor activates them automatically when src/ appears.");
  }
  // The first commit of the contract: the lockfile and the Receipt-Id trailer get
  // their baseline from second zero (§08).
  try {
    execFileSync("git", ["add", "-A"], { cwd });
    execFileSync("git", ["commit", "-q", "-m", `chore(ai-eng): plant governance ${VERSION}`, "--no-verify", "--no-gpg-sign"], { cwd });
    ui.ok("first contract commit");
  } catch {
    ui.info("contract commit pending (do it yourself with git)");
  }
  ui.end("Two steps I can't do for you: 1. Trust the workspace in your surface (without trust, hooks do not run) · 2. ai-eng doctor — verify the chain responds");
  return 0;
}

/** Canon version read for doctor/notice paths. home(), not HOME — the
 *  AI_ENG_HOME override must isolate this too, or the status line lies. */
export function canonVersion(): string {
  try {
    return String(JSON.parse(readFileSync(versionFile(), "utf8")).version ?? "unknown");
  } catch {
    return "unknown";
  }
}
