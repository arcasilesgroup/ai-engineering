import { existsSync, readFileSync, writeFileSync, symlinkSync, chmodSync } from "node:fs";
import { spawnSync, execFileSync } from "node:child_process";
// `ai-eng init` — one verb, two phases (§14.0a). Outside a repo: phase 1, the
// machine (canon + mirrors). Inside a repo: both phases — first the canon (missing
// is installed, never aborts), then the project contract. Idempotent: re-init
// offers update/config/exit, never overwrites an edited file (§14.5b's six paths).
// Every line a human sees goes through src/ui.ts: the frame must survive the
// whole flow (cli-ux-14 work point 02).

import { join } from "node:path";
import { select, groupMultiselect, isCancel } from "@clack/prompts";
import { scriptedInput } from "../ui.ts";
import { SURFACES, surfaceCanGovern, installCanon, installMachineCarriers, machineCarrier, rememberTemplateDir, type Surface } from "../surfaces/adapters.ts";
import { installTemplateDir } from "../floor/template.ts";
import { install, buildLock, lockText, parseLock } from "../install.ts";
import { canonDrift } from "../embed.ts";
import { home } from "../env.ts";
import { planEntries, contractEntries, hasAdapter, surfaceOptions, refuseLine } from "./init-shared.ts";
import { configMain } from "./config.ts";
import { updateMain } from "./update.ts";
import { VERSION } from "../version.ts";
import * as ui from "../ui.ts";

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

/** What the tier header cannot say, in plain words: the delta from the
 *  group's promise. A core surface with full guards gets no hint — the
 *  header already said it. */
export function surfaceHint(s: Surface): string {
  const delta: string[] = [];
  if (s.can.deny === "throw") delta.push("blocks by throwing");
  else if (s.can.deny === "host-only") delta.push("the host denies through its own permissions; no hook for us to run");
  else if (s.can.deny !== true) delta.push("can't block tool calls");
  if (s.can.rewriteOut === false) delta.push("can't rewrite output");
  else if (typeof s.can.rewriteOut === "string") delta.push("rewrites output wholesale");
  // The caveat is the row's own, because a group header cannot state a fact two rows do not
  // share — and because a promise that disagrees with its measurement may not do it quietly.
  if (s.note !== undefined) delta.push(s.note);
  return delta.join(" · ");
}

function scaffoldProject(surfaces: string[]): string[] {
  const cwd = process.cwd();
  const lines: string[] = [];
  // Contract files: written ONCE. install() skips anything the user already has.
  const contractReport = install(cwd, contractEntries(new Date().toISOString().slice(0, 10)));
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
  const report = install(cwd, entries);
  for (const written of report.written) lines.push(`✓ ${written}`);
  for (const conflict of report.conflicts) lines.push(`⚠ ${conflict} — edited by you: 3-way diff required, not touched`);
  for (const refused of report.refused) lines.push(refuseLine(refused));
  // Hook shims must be executable or git silently ignores them.
  for (const shim of ["pre-commit", "commit-msg", "pre-push"]) {
    const shimPath = join(cwd, ".git", "hooks", shim);
    if (existsSync(shimPath)) chmodSync(shimPath, 0o755);
  }
  lines.push("✓ git floor → .git/hooks/{pre-commit,commit-msg,pre-push} (marker-managed)");
  // core.hooksPath is NOT redirected: the hooks live in their standard location.
  // The shims live in .git/hooks, which git only reads while `core.hooksPath` is unset —
  // so a repo that points it somewhere else (husky, pre-commit) would carry our floor and
  // never run it. Deleting that setting for the user is not ours to do: it is named, with
  // the one line that fixes it, and a value we set ourselves in an older release is
  // cleaned up because it IS ours.
  const hooksPath = spawnSync("git", ["-C", cwd, "config", "--get", "core.hooksPath"], { encoding: "utf8" });
  const hooksPathValue = (hooksPath.stdout ?? "").trim();
  if (hooksPathValue.length > 0) {
    if (hooksPathValue.includes("ai-eng")) {
      spawnSync("git", ["-C", cwd, "config", "--unset", "core.hooksPath"]);
      lines.push(`✓ git core.hooksPath (${hooksPathValue}) unset — it pointed at ai-eng's own floor`);
    } else {
      lines.push(`⚠ core.hooksPath is yours (${hooksPathValue}): git will not read .git/hooks, so the ai-eng floor does not run. Keep it and call \`ai-eng git pre-commit\` from your hook, or unset it.`);
    }
  }
  // A repo that already carries a contract keeps its pin: re-init is not a way to
  // un-approve a milestone (same reason as update.ts).
  const lockPath = join(cwd, ".ai-engineering", "ai-eng.lock");
  const carried = existsSync(lockPath) ? parseLock(readFileSync(lockPath, "utf8")) : null;
  const lock = buildLock(entries, VERSION, { spec_sha256: carried?.spec_sha256, base_sha: carried?.base_sha });
  writeFileSync(join(cwd, ".ai-engineering", "ai-eng.lock"), lockText(lock));
  lines.push(`✓ .ai-engineering/ai-eng.lock (${Object.keys(lock.assets).length} assets with sha256)`);
  return lines;
}

export async function initMain(flags: { yes?: boolean; global?: boolean; surface?: string[] }): Promise<number> {
  const input = scriptedInput();
  const confirmWithInput = (message: string, initial: boolean) => ui.confirmDefault(message, initial, input as never);
  ui.frame(`{ai} Engineering ${VERSION}`);
  const cwd = process.cwd();
  const inRepo = existsSync(join(cwd, ".git")) || existsSync(join(cwd, ".ai-engineering"));
  // Phase 1: global, or missing canon — installs/repairs the machine side either way.
  // home() (not HOME) so AI_ENG_HOME test installs stay isolated. The status
  // line always prints: the user must see the machine is healthy before the
  // repo work starts.
  const canonDir = join(home(), "skills");
  // Health is proven, not guessed: every canon file byte-compared to this
  // binary's payload — the same predicate doctor proves. Existence probes and
  // version.json are not enough: a canon reads "global canon intact · nothing to
  // install" with 34 skills deleted, because notice.ts caches the REGISTRY
  // version in the very version.json that installCanon wrote the INSTALLED
  // version into.
  const canon = canonDrift(home());
  const canonHealthy = canon.drift === 0 && canon.missing === 0 && canon.stale === 0;
  // Did a machine-side write get agreed in this run? The canon install asks once (§14.5b)
  // and the carriers ride with the same answer — a second question for the same "write
  // outside the repo" would be noise, and silence would be a write nobody agreed to.
  const machineAgreed = flags.global === true || flags.yes === true || !canonHealthy;
  if (flags.global || !canonHealthy) {
    const reinstalling: boolean = existsSync(canonDir) && !canonHealthy;
    // §14.5b path 2: a repo on a machine that never had the canon. Writing all of
    // ~/.ai-engineering is not what "govern this repo" asked for, so it is OFFERED
    // ("one yes, two phases done") and a no ends the verb with the machine
    // untouched. Repair of a canon that IS there stays silent: that half is already
    // ours, and update repairs it without a question too. --global is the explicit
    // ask; --yes is the zero-prompt CI path.
    if (!flags.global && inRepo && !reinstalling && flags.yes !== true) {
      const ok = await confirmWithInput(`No global canon at ${canonDir} — install it now and I continue with the repo?`, true);
      if (isCancel(ok) || ok === false) {
        ui.cancelled("Nothing installed. The machine side alone: ai-eng init --global");
        return 0;
      }
    }
    const canonLines = installCanon(VERSION).map((line): ui.Row => ({ mark: "ok", text: line.replace(/^✓ /, "") }));
    ui.section(
      reinstalling ? "global canon outdated or incomplete — re-installing" : "global canon (the machine side)",
      canonLines,
      reinstalling ? `${canon.drift} drifted · ${canon.missing} missing${canon.stale > 0 ? ` · ${canon.stale} stale` : ""}` : home(),
    );
  } else {
    ui.section("global canon intact", [{ mark: "ok", text: `${home()} · ai-eng ${VERSION}`, dim: "nothing to install" }]);
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
    // --yes resolves the hand-off question: rewrite ours, never yours. Without
    // it, a non-TTY stdin cancels the select and init exits having installed
    // nothing — the recovery path for a half-uninstalled repo has to exist
    // even unattended: "no lock, run init" is a deadlock.
    const action = flags.yes === true ? "update" : await select({
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
    // One frame, one story: updateMain() continues inside it — its frame()
    // call becomes the chapter line, and the version context rides with it.
    return await updateMain({ yes: flags.yes === true });
  }
  let picked: string[];
  if (flags.yes === true) {
    picked = flags.surface && flags.surface.length > 0 ? flags.surface : ["claude-code"];
  } else {
    // Grouped by tier, not a flat wall of seven: the header carries the
    // capability class, the hint only the delta. Tab jumps between groups.
    // Only surfaces with an adapter appear — the rest would be a config.toml
    // claim with nothing to enforce it (§13).
    const answer = await groupMultiselect({
      message: "Which agent surfaces is this project governed on? (ticked = detected)",
      options: Object.fromEntries(surfaceOptions().map((group) => [group.title, group.items.map((s) => ({ value: s.id, label: s.label, hint: surfaceHint(s) }))])),
      initialValues: detectedSurfaces(cwd),
      required: true,
      selectableGroups: false,
      input: input as never,
    });
    if (isCancel(answer)) {
      ui.cancelled();
      return 0;
    }
    picked = answer;
  }
  // Abort before promising what a surface cannot deliver (§13): one that cannot deny
  // has nowhere for the guards to run, and one with no adapter would be declared in
  // config.toml with nothing to enforce it.
  for (const id of picked) {
    const surface = SURFACES.find((s) => s.id === id);
    if (!surface) continue;
    if (!surfaceCanGovern(surface)) {
      ui.fail(`"${id}" cannot deny tools: the guards have nowhere to run. Use a core surface.`);
      return 2;
    }
    if (!hasAdapter(id)) {
      ui.fail(`"${id}" has no adapter in this release — nothing would enforce its guards.`);
      return 2;
    }
  }
  const sp = ui.spinner();
  sp.start("Scaffolding governance…");
  const lines = scaffoldProject(picked);
  sp.stop();
  // The machine side of the declared surfaces: five of the seven hosts read their
  // carrier from the user's home, so that is where it goes — once per machine, not once
  // per repo (§13.2). Writing outside the repo is ASKED for (§14.5b); --yes is the
  // zero-prompt path, and a canon that was just installed under the same permission
  // already answered it.
  const machineScoped = picked.filter((id) => {
    const surface = SURFACES.find((s) => s.id === id);
    return surface !== undefined && machineCarrier(surface) !== null;
  });
  if (machineScoped.length > 0) {
    const agreed =
      machineAgreed ||
      flags.yes === true ||
      (await confirmWithInput(`${machineScoped.join(", ")} read their hooks from your home — write the machine carriers there?`, true)) === true;
    if (!agreed) {
      lines.push("⚠ machine carriers not written — those surfaces will run without guards until you re-run init");
    } else {
      const report = installMachineCarriers(machineScoped);
      for (const path of report.written) lines.push(`✓ ${path} — machine carrier`);
      for (const path of report.untouched) lines.push(`· ${path} — machine carrier already current`);
      for (const refused of report.refused) lines.push(refuseLine(refused));
    }
  }
  // The git floor's second life, and it is the REPO's floor, not the carriers': a repo
  // whose surfaces all read from the checkout still deserves clones born with the shims,
  // instead of a CI step rebuilding them after the fact (§13.2). It rides the same
  // machine-side permission as everything else that writes outside the repo.
  if (machineAgreed || (await confirmWithInput("Write the git floor into your global init.templateDir, so new clones are born with it?", true)) === true) {
    const template = installTemplateDir();
    if (template.status !== "failed") {
      rememberTemplateDir(template.previous, template.ours);
      lines.push(`✓ ${template.line}`);
    } else {
      lines.push(`⚠ ${template.line}`);
    }
  }
  // next step — each idea one block, the dim tail carries the why.
  const contract = lines.filter((l) => l.includes("(contract)") || l.startsWith("·") || l.includes("CLAUDE.md"));
  const machine = lines.filter((l) => !contract.includes(l));
  const toRow = (line: string): ui.Row =>
    line.startsWith("⚠")
      ? { mark: "warn", text: line.slice(2) }
      : line.startsWith("·")
        ? { mark: "muted", text: line.slice(2) }
        : { mark: "ok", text: line.replace(/^✓ /, "") };
  if (contract.length > 0) ui.section("Your contract files", contract.map(toRow), "yours to edit — ai-eng never rewrites them");
  ui.section("Scaffolded", machine.map(toRow), `${picked.length} surface${picked.length === 1 ? "" : "s"}: ${picked.join(", ")}`);
  // Bootstrap note (§14.1 mockup): no src/ yet — arch-tests hold off until there is code.
  if (!existsSync(join(cwd, "src"))) {
    ui.section("Bootstrap mode", [
      { mark: "muted", text: "No code yet → arch-tests hold off (no failures on empty)." },
      { mark: "sub", text: "doctor activates them automatically when src/ appears." },
    ]);
  }
  // The first commit of the contract: the lockfile and the Receipt-Id trailer get
  // their baseline from second zero (§08).
  let commitLine = "contract commit pending (do it yourself with git)";
  try {
    execFileSync("git", ["add", "-A"], { cwd });
    execFileSync("git", ["commit", "-q", "-m", `chore(ai-eng): install governance ${VERSION}`, "--no-verify", "--no-gpg-sign"], { cwd });
    commitLine = `chore(ai-eng): install governance ${VERSION}`;
  } catch {
    /* nothing staged or git refused — the pending note stands */
  }
  ui.section("Governance installed", [{ mark: "ok", text: `commit: ${commitLine}`, dim: "git revert is the rollback" }]);
  ui.end("Two steps I can't do for you: 1. Trust the workspace in your surface (without trust, hooks do not run) · 2. ai-eng doctor — verify the chain responds");
  return 0;
}
