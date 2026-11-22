import { existsSync, readFileSync, writeFileSync, chmodSync } from "node:fs";
import { spawnSync, execFileSync } from "node:child_process";
import { PassThrough } from "node:stream";
// `ai-eng init` — one verb, two phases. Outside a repo: phase 1, the
// machine (canon + mirrors). Inside a repo: both phases — first the canon (missing
// is installed, never aborts), then the project contract. Idempotent: re-init
// offers update/config/exit, never overwrites an edited file.
// A first init that meets a foreign AGENTS.md names it and asks before replacing it.
// Every line a human sees goes through src/ui.ts: the frame must survive the
// whole flow (cli-ux-14 work point 02).

import { basename, join } from "node:path";
import { select, multiselect, isCancel } from "@clack/prompts";
import { scriptedInput } from "../ui.ts";
import { installCanon } from "../surfaces/canon-install.ts";
import { installMachineCarriers } from "../surfaces/carriers-install.ts";
import { SURFACES, surfaceCanGovern, machineCarrier, retireNpmPowerShellShim } from "../surfaces/adapters.ts";
import { install, buildLock, lockText, parseLock, type PlanEntry } from "../install.ts";
import { canonDrift, type CanonDrift } from "../embed.ts";
import { canonicalSurfaceId, home, isCiProvider, CI_PROVIDERS, type CiProvider } from "../env.ts";
import { planEntries, contractEntries, hasAdapter, installLineRow, SURFACE_PICK_MESSAGE, surfaceOptions, refuseLine, refuseText, AZURE_PORTAL_STEPS, CI_PICK_MESSAGE, ciOptions, isLegacyHooksPath } from "./init-shared.ts";
import { configMain } from "./config.ts";
import { updateMain } from "./update.ts";
import { retiredPaths, sweepRetiredAssets } from "./uninstall.ts";
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

type InitFlags = { yes?: boolean; global?: boolean; surface?: string[]; ci?: string };

/** Where the origin remote is hosted — a suggestion for the CI question, never a
 *  decision: a GitHub repository can build on Azure Pipelines and the other way round. */
function detectedCiProvider(cwd: string): CiProvider {
  const origin = spawnSync("git", ["-C", cwd, "remote", "get-url", "origin"], { encoding: "utf8" });
  const url = (origin.stdout ?? "").trim();
  return /dev\.azure\.com|visualstudio\.com/.test(url) ? "azure-pipelines" : "github-actions";
}

/** The canon's drift in one line — the counts that matter, and only the ones that are
 *  non-zero beyond the first two. Nested template literals read as arithmetic. */
function canonSummary(canon: { drift: number; missing: number; stale: number }): string {
  const parts = [`${canon.drift} drifted`, `${canon.missing} missing`];
  if (canon.stale > 0) parts.push(`${canon.stale} stale`);
  return parts.join(" · ");
}


function scaffoldProject(surfaces: string[], ci: CiProvider, contract: PlanEntry[]): ScaffoldRows {
  const cwd = process.cwd();
  const rows: ui.Row[] = [];
  const contractRows: ui.Row[] = [];
  // Contract files: written ONCE. The AGENTS.md question is already resolved where the
  // prompt lives (scaffoldAndCarriers), so what reaches install() here is exactly what
  // may be written: a kept file was filtered out, a replaced one was written above.
  const contractReport = install(cwd, contract);
  for (const written of contractReport.written) contractRows.push(ui.fileRow("installed", written, "contract"));
  for (const untouched of contractReport.yours) contractRows.push(ui.fileRow("unchanged", untouched, "contract · yours, untouched"));
  // A repo that already carries a lock (config.toml gone, so init runs instead of update) keeps
  // what it records as ai-eng's: an edited recorded file is rewritten, never handed over.
  const lockPath = join(cwd, ".ai-engineering", "ai-eng.lock");
  const carried = existsSync(lockPath) ? parseLock(readFileSync(lockPath, "utf8")) : null;
  const recordedHash = (path: string): string | null => {
    const hash = carried?.assets[path];
    return hash ? `sha256:${hash}` : null;
  };
  const entries = planEntries(surfaces, ci);
  const report = install(cwd, entries, recordedHash);
  for (const written of report.written) rows.push(ui.fileRow("installed", written));
  for (const path of report.yours) rows.push(ui.fileRow("unchanged", path, "already here and not written by ai-eng: yours, untouched"));
  for (const refused of report.refused) rows.push({ mark: "warn", text: refuseText(refused) });
  // What the carried lock records and this run does not write goes, by update's rule: a re-init
  // that dropped it from the ledger unswept would leave a file no later run can see.
  const retiredRows: ui.Row[] = [];
  const carriedAssets = carried?.assets ?? {};
  const retiredKept = sweepRetiredAssets(cwd, retiredPaths(carriedAssets, entries), carriedAssets, retiredRows);
  rows.push(...retiredRows);
  // Hook shims must be executable or git silently ignores them.
  for (const shim of ["pre-commit", "commit-msg", "pre-push"]) {
    const shimPath = join(cwd, ".git", "hooks", shim);
    if (existsSync(shimPath)) chmodSync(shimPath, 0o755);
  }
  rows.push({ mark: "ok", text: "git floor → .git/hooks/{pre-commit,commit-msg,pre-push}", dim: "marker-managed" });
  // core.hooksPath is NOT redirected: the hooks live in their standard location.
  // The shims live in .git/hooks, which git only reads while `core.hooksPath` is unset —
  // so a repo that points it somewhere else (husky, pre-commit) would carry our floor and
  // never run it. Deleting that setting for the user is not ours to do: it is named, with
  // the one line that fixes it, and a value we set ourselves in an older release is
  // cleaned up because it IS ours. `--local` so an environment or global value is not
  // mistaken for this repo's. A path that merely contains "ai-eng" is still the user's.
  const hooksPath = spawnSync("git", ["-C", cwd, "config", "--local", "--get", "core.hooksPath"], { encoding: "utf8" });
  const hooksPathValue = (hooksPath.stdout ?? "").trim();
  if (hooksPathValue.length > 0) {
    if (isLegacyHooksPath(hooksPathValue)) {
      spawnSync("git", ["-C", cwd, "config", "--local", "--unset", "core.hooksPath"]);
      rows.push(ui.fileRow("updated", "core.hooksPath", `unset — was ${hooksPathValue}`));
    } else {
      rows.push({ mark: "warn", text: `core.hooksPath is yours (${hooksPathValue}): git will not read .git/hooks, so the ai-eng floor does not run. Keep it and call \`ai-eng git pre-commit\` from your hook, or unset it.` });
    }
  }
  // The lock is the ownership ledger: it claims only what ai-eng wrote or already matched.
  // A file of the project's left untouched must stay the project's on every later update.
  // A carried contract keeps its pin: re-init is not a way to un-approve a milestone.
  const refused = new Set(report.refused.map((entry) => entry.path));
  const notOurs = new Set([...report.yours, ...refused]);
  const lock = buildLock(entries.filter((entry) => !notOurs.has(entry.path)), VERSION, { spec_sha256: carried?.spec_sha256, base_sha: carried?.base_sha });
  // A recorded file this run could not write is still ai-eng's (same as update.ts): it keeps
  // its previous entry, so the next update retries it and uninstall knows it.
  for (const entry of entries) {
    const recorded = carried?.assets[entry.path];
    if (entry.merge !== true && refused.has(entry.path) && recorded !== undefined) lock.assets[entry.path] = recorded;
  }
  for (const [path, recorded] of Object.entries(carriedAssets)) {
    if (retiredKept.includes(path)) lock.assets[path] = recorded;
  }
  writeFileSync(lockPath, lockText(lock));
  rows.push(ui.fileRow("installed", ".ai-engineering/ai-eng.lock", `${Object.keys(lock.assets).length} assets with sha256`));
  return { contract: contractRows, files: rows };
}

/** The local confirm closure — one shared prompt helper threaded into the machine/repo steps. */
type ConfirmInput = (message: string, initial: boolean) => Promise<boolean>;

/** Phase 1 machine side: install/repair the global canon, or report it healthy. An exit
 *  code ends the verb (`--global` is done); null carries on with the repo. */
function resolveMachineSide(flags: InitFlags): number | null {
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
  installCanonOrReport(flags, canonDir, canon, canonHealthy);
  if (flags.global) {
    ui.end("Next: ai-eng init inside a repo.");
    return 0;
  }
  return null;
}

/** Install or report the global canon, one section either way. Never asked (D-012): a repo
 *  is not governed without the canon, and update and config write it without a question. */
function installCanonOrReport(flags: InitFlags, canonDir: string, canon: CanonDrift, canonHealthy: boolean): void {
  if (flags.global || !canonHealthy) {
    const reinstalling: boolean = existsSync(canonDir) && !canonHealthy;
    const canonLines = installCanon(VERSION).map((line) => installLineRow(line));
    if (reinstalling) {
      ui.section("global canon outdated or incomplete — re-installing", canonLines, canonSummary(canon));
    } else {
      ui.section("global canon (the machine side)", canonLines, home());
    }
  } else {
    ui.section("global canon intact", [{ mark: "ok", text: `${home()} · ai-eng ${VERSION}`, dim: "nothing to install" }]);
  }
}

/** Outside a repo: init creates the repo itself (confirm, or --yes to proceed). */
async function ensureRepo(
  flags: InitFlags,
  inRepo: boolean,
  cwd: string,
  confirmWithInput: ConfirmInput,
): Promise<number | null> {
  // Outside a repo: a bare folder is not a refusal — init runs in a bare
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
  return null;
}

/** Phase 2 re-init hand-off: already-governed repo routes to update/config/exit. */
async function reinitHandoff(
  flags: InitFlags,
  cwd: string,
  input: NodeJS.ReadStream | PassThrough,
): Promise<number | null> {
  // ── Phase 2: the repo is governed — idempotent re-init never tramples your work.
  if (existsSync(join(cwd, ".ai-engineering", "config.toml"))) {
    // --yes resolves the hand-off question: rewrite ours, never yours. Without
    // it, a non-TTY stdin cancels the select and init exits having installed
    // nothing — the recovery path for a half-uninstalled repo has to exist
    // even unattended: "no lock, run init" is a deadlock.
    const action = flags.yes === true ? "update" : await select({
      message: "This project is already governed. What do you want to do?",
      options: [
        { value: "update", label: "Update ai-eng's files" },
        { value: "config", label: "Change settings (agent surfaces, CI)" },
        { value: "exit", label: "Exit" },
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
    return await updateMain({ yes: flags.yes === true, binary: false });
  }
  return null;
}

/** Pick which surfaces govern this project. Detected hosts start ticked; --yes and --surface skip the prompt. */
async function pickSurfaces(
  flags: InitFlags,
  cwd: string,
  input: NodeJS.ReadStream | PassThrough,
): Promise<number | string[]> {
  let picked: string[];
  if (flags.yes === true) {
    picked = flags.surface && flags.surface.length > 0 ? flags.surface : ["claude-code"];
  } else {
    const answer = await multiselect({
      message: SURFACE_PICK_MESSAGE,
      options: surfaceOptions().map((s) => ({ value: s.id, label: s.label })),
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
  return picked.map(canonicalSurfaceId);
}

/** Pick where the merge gate runs. The origin remote preselects; --ci and --yes skip the prompt. */
async function pickCi(flags: InitFlags, cwd: string, input: NodeJS.ReadStream | PassThrough): Promise<number | CiProvider> {
  if (flags.ci !== undefined) {
    if (isCiProvider(flags.ci)) return flags.ci;
    ui.fail(`--ci "${flags.ci}" is not a CI provider: use ${CI_PROVIDERS.join(", ")}.`);
    return 2;
  }
  const detected = detectedCiProvider(cwd);
  if (flags.yes === true) return detected;
  const answer = await select({
    message: CI_PICK_MESSAGE,
    options: ciOptions(),
    initialValue: detected,
    input: input as never,
  });
  if (isCancel(answer)) {
    ui.cancelled();
    return 0;
  }
  return answer;
}

/** Refuse a surface this release cannot actually enforce, before any promise is printed. */
function validateSurfaces(picked: string[]): number | null {
  // Abort before promising what a surface cannot deliver: one that cannot deny
  // has nowhere for the guards to run, and one with no adapter would be declared in
  // config.toml with nothing to enforce it.
  for (const id of picked) {
    const surface = SURFACES.find((s) => s.id === id);
    // An unknown surface id is refused here, not declared: the declaration is what the
    // gate reads, so a typo like `--surface claud-code` in config.toml would be a repo
    // calling itself governed on a surface that does not exist — with no carrier behind
    // it, governed by nothing.
    if (!surface) {
      ui.fail(`"${id}" is not a surface this release knows — nothing would enforce its guards.`);
      return 2;
    }
    if (!surfaceCanGovern(surface)) {
      ui.fail(`"${id}" cannot deny tools: the guards have nowhere to run. Use a core surface.`);
      return 2;
    }
    if (!hasAdapter(id)) {
      ui.fail(`"${id}" has no adapter in this release — nothing would enforce its guards.`);
      return 2;
    }
  }
  return null;
}

/** Scaffold the repo, then write the carriers the picked surfaces read from the home. */
async function scaffoldAndCarriers(
  flags: InitFlags,
  picked: string[],
  ci: CiProvider,
  confirmWithInput: ConfirmInput,
): Promise<ScaffoldRows> {
  const cwd = process.cwd();
  // An AGENTS.md this project already had is named and asked about before anything is
  // written: default, --yes and cancel keep it byte for byte; only a human yes replaces
  // it. install() would keep it either way ("we never installed it: it is the user's"),
  // so the decision is resolved here, before the installer runs.
  let contract = contractEntries(new Date().toISOString().slice(0, 10), cwd);
  const agents = contract.find((entry) => entry.path === "AGENTS.md");
  const agentsPath = join(cwd, "AGENTS.md");
  let replacedExisting = false;
  let keptExisting = false;
  if (agents !== undefined && existsSync(agentsPath) && readFileSync(agentsPath, "utf8") !== agents.ours) {
    let overwrite = false;
    if (flags.yes !== true) {
      const lsFiles = spawnSync("git", ["-C", cwd, "ls-files", "--", "AGENTS.md"], { encoding: "utf8" });
      const untrackedHint = lsFiles.status === 0 && (lsFiles.stdout ?? "").trim() === "" ? " Not in git: overwriting loses it for good." : "";
      overwrite = await confirmWithInput(`AGENTS.md already exists in this project.${untrackedHint} Overwrite it with the ai-engineering contract file?`, false);
    }
    contract = contract.filter((entry) => entry.path !== "AGENTS.md");
    if (overwrite) {
      writeFileSync(agentsPath, agents.ours);
      replacedExisting = true;
    } else {
      keptExisting = true;
    }
  }
  const sp = ui.spinner();
  sp.start("Scaffolding");
  const rows = scaffoldProject(picked, ci, contract);
  if (replacedExisting) rows.contract.unshift(ui.fileRow("updated", "AGENTS.md", "contract — replaced the file that was there"));
  if (keptExisting) rows.contract.unshift(ui.fileRow("unchanged", "AGENTS.md", "contract · yours, untouched"));
  sp.stop();
  installCarriers(picked, rows.files);
  return rows;
}

/** Write the machine carriers for the surfaces that read their hooks from the user's home. */
function installCarriers(picked: string[], rows: ui.Row[]): void {
  // Five of the seven hosts read their carrier from the user's home, so that is where it
  // goes — once per machine, not once per repo. Never asked (D-012): a surface
  // without its carrier runs with no guards at all, which is not what `init` was for, and
  // the merge keeps every setting of the person's own.
  const machineScoped = picked.filter((id) => {
    const surface = SURFACES.find((s) => s.id === id);
    return surface !== undefined && machineCarrier(surface) !== null;
  });
  // Every init, whatever the surfaces: Cursor's repo-only hook is the one that needs it most.
  const retiredShim = retireNpmPowerShellShim();
  if (retiredShim !== null) rows.push(installLineRow(retiredShim));
  if (machineScoped.length === 0) return;
  const report = installMachineCarriers(machineScoped);
  for (const path of report.written) rows.push(ui.fileRow("installed", path, "machine carrier"));
  for (const path of report.retired) rows.push(ui.fileRow("removed", path, "OpenCode loads every file in its plugin folder"));
  for (const path of report.untouched) rows.push(ui.fileRow("unchanged", path, "machine carrier already current"));
  for (const refused of report.refused) rows.push(installLineRow(refuseLine(refused)));
}

/** The contract files and everything else, kept apart where they are written — never
 *  sorted afterwards by reading the words of a row. */
type ScaffoldRows = { contract: ui.Row[]; files: ui.Row[] };

/** Print the contract section, then the scaffold. */
function renderSections(picked: string[], ci: CiProvider, rows: ScaffoldRows): void {
  if (rows.contract.length > 0) ui.section("Your contract files", rows.contract, "yours to edit — ai-eng never rewrites them");
  const plural = picked.length === 1 ? "" : "s";
  ui.section("Scaffolded", rows.files, `${picked.length} surface${plural}: ${picked.join(", ")} · CI: ${ci}`);
  ui.section("Layer rules", [
    { mark: "muted", text: "Choosing layers is judgement: run /ai-refresh-project once there is code." },
    { mark: "sub", text: "It proposes rules for your language's own tool; you review and apply them." },
  ]);
}

/** Resolve every pre-scaffold step in one place — machine side, repo, re-init handoff,
 *  surface pick, and validation. Returns either an exit code (early-return) or the
 *  resolved values the scaffold phase needs. */
async function resolvePhase(
  flags: InitFlags,
  cwd: string,
  inRepo: boolean,
  input: NodeJS.ReadStream | PassThrough,
  confirmWithInput: ConfirmInput,
): Promise<number | { picked: string[]; ci: CiProvider }> {
  const machineExit = resolveMachineSide(flags);
  if (machineExit !== null) return machineExit;
  const repoCode = await ensureRepo(flags, inRepo, cwd, confirmWithInput);
  if (repoCode !== null) return repoCode;
  const handoff = await reinitHandoff(flags, cwd, input);
  if (handoff !== null) return handoff;
  const pickedResult = await pickSurfaces(flags, cwd, input);
  if (typeof pickedResult === "number") return pickedResult;
  const invalid = validateSurfaces(pickedResult);
  if (invalid !== null) return invalid;
  const ci = await pickCi(flags, cwd, input);
  if (typeof ci === "number") return ci;
  return { picked: pickedResult, ci };
}

export async function initMain(flags: InitFlags): Promise<number> {
  const input = scriptedInput();
  const confirmWithInput: ConfirmInput = (message, initial) => ui.confirmDefault(message, initial, input as never);
  const cwd = process.cwd();
  const inRepo = existsSync(join(cwd, ".git")) || existsSync(join(cwd, ".ai-engineering"));
  const subject = flags.global && !inRepo ? "this machine" : inRepo ? basename(cwd) : "this folder";
  ui.frame(ui.frameTitle("init", subject, VERSION));
  const resolved = await resolvePhase(flags, cwd, inRepo, input, confirmWithInput);
  if (typeof resolved === "number") return resolved;
  const lines = await scaffoldAndCarriers(flags, resolved.picked, resolved.ci, confirmWithInput);
  renderSections(resolved.picked, resolved.ci, lines);
  ui.section("Installed", [
    { mark: "warn", text: "Trust this workspace in your editor, or the hooks do not run." },
    { mark: "ok", text: "Nothing committed." },
  ]);
  if (resolved.ci === "azure-pipelines") ui.section("Azure DevOps — two steps in the portal", AZURE_PORTAL_STEPS);
  ui.end("Next: ai-eng doctor");
  return 0;
}
