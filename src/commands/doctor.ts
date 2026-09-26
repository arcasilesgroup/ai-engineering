// `ai-eng doctor` — 12 checks + one real test. The difference with theater: it
// EXECUTES an adversarial payload and measures real latency. A hook that does not
// deny, or denies slow, is FAIL — not WARN (§14.2).
import { canonDrift } from "../embed.ts";
import { existsSync, readFileSync, readdirSync, lstatSync, statSync, unlinkSync, writeFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { repoRoot, loadConfig, home, governanceGap, enabledSurfaces, receiptsDir } from "../env.ts";
import { mergeDaily, pruneDenyLedger, summarizeReceipts, type DailyPoint, type DenyLedger, type ReceiptSummary } from "../receipts.ts";
import { parseLock, sha256 } from "../install.ts";
import { SURFACES, machineCarrier, repoCarrier, carrierFiles, carrierPath, readMachineState } from "../surfaces/adapters.ts";
import { unmetTriggers } from "../spec/triggers.ts";
import { VERSION, compareVersions } from "../version.ts";
import { runChain } from "../chain/mod.ts";
import { readOverrides, overrideDaysLeft } from "../chain/dialect.ts";
import { checkpointGateReportLines } from "./checkpoint-gate-report.ts";
import * as ui from "../ui.ts";

export type CheckResult = { readonly name: string; readonly status: "ok" | "warn" | "fail"; readonly detail: string };

const CEILING_MS = 50;


function checkAgents(root: string | null): CheckResult {
  // 1. AGENTS.md present, rule-bearing, under the context ceiling.
  const agentsPath = root ? join(root, "AGENTS.md") : null;
  if (!agentsPath || !existsSync(agentsPath)) return { name: "AGENTS.md", status: "fail", detail: "missing — the contract was never installed" };
  const content = readFileSync(agentsPath, "utf8");
  const rules = (content.match(/^[ \t]*(?:\d+\.|-)[ \t]+\S/gm) ?? []).length;
  const lines = content.split("\n").length;
  return { name: "AGENTS.md", status: lines <= 120 && rules >= 6 ? "ok" : "warn", detail: `${rules} rules · ${lines} lines${lines > 120 ? " (over the context ceiling)" : ""}` };
}

function checkConfig(gap: string | null, surfaces: string[]): CheckResult {
  // 3. config.toml — this IS the gate. Absent, corrupt and declared are three
  //    different states, and "I could not read it" must never read as ok: the chain
  //    treats an unreadable file as an undeclared repo, so a green here would be a
  //    lie about the exact file the policy hangs on (F2).
  const detail = gap === null
    ? `governed · surfaces: ${surfaces.length > 0 ? surfaces.join(", ") : "none declared"}`
    : ({
        "no-config": "absent — the gate reads this file; without it this repo is not governed",
        "corrupt-config": "unparseable — the chain treats this repo as ungoverned; fix the TOML or re-run ai-eng init",
        "no-surfaces": "no [surfaces] enabled list — the gate needs the declaration, not just the file",
      } as Record<string, string>)[gap] ?? "no repository above this directory";
  return { name: "config.toml", status: gap === null ? "ok" : "fail", detail };
}

async function checkMirrors(root: string | null): Promise<CheckResult | null> {
  // 3b. Skill mirrors: the canon only reaches IDEs through them. A mirror dir
  //    missing its links is the P0-1 failure mode (silent ENOENT in installCanon).
  if (!root) return null;
  const { mirrorTargets } = await import("../surfaces/adapters.ts");
  const mirrors = mirrorTargets();
  let mirrorOK = 0;
  let mirrorBroken = 0;
  for (const target of mirrors) {
    if (!existsSync(target.dir)) {
      mirrorBroken += 1;
      continue;
    }
    const links = readdirSync(target.dir, { withFileTypes: true }).filter((e) => e.isSymbolicLink());
    if (links.length > 0) mirrorOK += 1;
    else mirrorBroken += 1;
  }
  return {
    name: "mirrors",
    status: mirrorBroken === 0 ? "ok" : "warn",
    detail: mirrorBroken === 0 ? `${mirrorOK}/${mirrors.length} mirrors carry linked skills` : `${mirrorBroken}/${mirrors.length} mirrors empty or missing → ai-eng init --global`,
  };
}

function checkCanon(): CheckResult {
  // 4. Canon: the machine's ~/.ai-engineering/skills must byte-match the binary's
  //    embedded payload. The repo lock never contains skills (it lists hooks,
  //    settings, config), so filtering the lock by skills/ counts 0 forever.
  //    Same predicate as materializeSkills: the dot-entries (chain bundle) are
  //    payload, not canon, so they are neither verified nor counted.
  const canon = canonDrift(home());
  const canonTotal = canon.verified + canon.drift + canon.missing;
  // A canon can be complete and dirty at once: an orphan is invisible to a payload
  // walk, so without the extras walk a renamed asset sits in every install while
  // this line reads 101/101. `foreign` is reported and never counted against
  // health — it is somebody's, and we do not delete it.
  const canonBits = [`${canon.verified}/${canonTotal} files verified`, `${canon.drift} drift`, `${canon.missing} missing`];
  if (canon.stale > 0) canonBits.push(`${canon.stale} stale (ai-eng update sweeps what we shipped)`);
  if (canon.foreign > 0) canonBits.push(`${canon.foreign} not ours (left alone)`);
  return { name: "canon", status: canon.drift === 0 && canon.missing === 0 && canon.stale === 0 ? "ok" : "warn", detail: canonBits.join(" · ") };
}

function checkAssets(root: string | null): CheckResult | null {
  // 4b. Assets outdated: the installed lock records which binary version installed
  //    it. Binary newer than lock → the repo runs stale hooks (§14.2: distinct
  //    from "a newer binary exists" — only update fixes this one).
  const lockPath = root ? join(root, ".ai-engineering", "ai-eng.lock") : null;
  if (!lockPath || !existsSync(lockPath)) {
    // Silent absence lets a half-uninstalled repo hide: no lock is a state, not a
    // non-event — say so.
    if (!root) return null;
    return { name: "assets", status: "warn", detail: "no ai-eng.lock — governance files were never (re)installed: run ai-eng init" };
  }
  const lockVersion = String(parseLock(readFileSync(lockPath, "utf8")).version || "");
  let detail: string;
  if (!lockVersion) detail = "lock has no version — run ai-eng update";
  else if (lockVersion === VERSION) detail = `installed by ${VERSION}`;
  else detail = `binary ${VERSION} · files installed by ${lockVersion} → ai-eng update`;
  return { name: "assets", status: lockVersion === VERSION ? "ok" : "warn", detail };
}

function checkGitFloor(root: string | null): CheckResult | null {
  // 5. git floor: marker-managed shims in .git/hooks/ + gitleaks present.
  if (!root) return null;
  const hooksDir = join(root, ".git", "hooks");
  const floorHooks = ["pre-commit", "commit-msg", "pre-push"];
  const wired = floorHooks.every((name) => {
    const p = join(hooksDir, name);
    return existsSync(p) && readFileSync(p, "utf8").includes("ai-eng git floor shim");
  });
  const gitleaks = spawnSync("gitleaks", ["version"], { encoding: "utf8" });
  const gitleaksLine = gitleaks.status === 0 ? "present" : "MISSING (HARD FAIL)";
  const detail = wired ? `marker hooks in .git/hooks/ · gitleaks ${gitleaksLine}` : "marker hooks missing from .git/hooks/ — run ai-eng init";
  let status: CheckResult["status"];
  if (wired && gitleaks.status === 0) status = "ok";
  else if (wired) status = "warn";
  else status = "fail";
  return { name: "git floor", status, detail };
}

function checkChainTest(gap: string | null): CheckResult {
  // 6. THE REAL TEST: adversarial payload must deny, under the latency ceiling.
  //    In a repo that never declared itself the allow IS the answer: the gate is
  //    open by design there, so calling it a broken chain would be a false alarm in
  //    every repo that has not run init — and a WARN a reader learns to ignore.
  const t0 = Date.now();
  const outcome = runChain(
    { tool_name: "Bash", tool_input: { command: "git commit -n -m x" }, tool_use_id: `doctor-${t0}`, session_id: `doctor-${t0}` },
    "PreToolUse",
    { inProcess: true },
  );
  const ms = Date.now() - t0;
  let status: CheckResult["status"];
  let detail: string;
  if (gap !== null) {
    status = "warn";
    detail = `not governed (${gap}) — the chain applies no policy here, so an allow is the gate working`;
  } else if (outcome.action === "deny") {
    status = ms <= CEILING_MS ? "ok" : "warn";
    detail = `adversarial payload (git commit -n) → DENY in ${ms}ms`;
  } else {
    status = "fail";
    detail = `adversarial payload NOT denied (${outcome.action}) in ${ms}ms`;
  }
  return { name: "chain test", status, detail };
}

/** The deviation rule (R1): the last 7 days of denies over 3x the preceding 7. Both
 *  windows are 7 days, so comparing sums is comparing daily means; 3x is fixed in
 *  code — a knob needs a band to calibrate against and there is one.
 *  The series comes from the RAW receipts (their 30-day TTL always covers the
 *  14-day window), never from summary.json: the aggregate is attacker-writable
 *  inside the repo like every local file, and a forged or deleted baseline is how
 *  run-1's audit found the WARN silenced while the line printed ok. A young repo
 *  (no runs at all in the prior week) has no baseline and stays SILENT — that is
 *  the honest absence of history, not a forgery.
 *  todo: names the dominant guard of the whole live window, not of the spike
 *  week per day — upgrade only if it ever misnames a real one. */
function denySpike(dir: string | null): { last7: number; prior7: number; guard: string } | null {
  if (!dir) return null;
  const live = summarizeReceipts(dir);
  const day = (offset: number) => new Date(Date.now() - offset * 86_400_000).toISOString().slice(0, 10);
  let last7 = 0;
  let prior7 = 0;
  let priorRuns = 0;
  for (let i = 0; i < 7; i += 1) last7 += live.daily[day(i)]?.denies ?? 0;
  for (let i = 7; i < 14; i += 1) {
    prior7 += live.daily[day(i)]?.denies ?? 0;
    priorRuns += live.daily[day(i)]?.runs ?? 0;
  }
  if (priorRuns === 0) return null; // no baseline in the raw trail: silent, not forgeable-by-absence
  // A storm, not a blip: the rule needs 3+ denies over the band. Without the floor,
  // doctor's own chain-test deny would out-shout a quiet prior week (1 vs 0) and the
  // row would WARN on every repo the human touches.
  if (last7 < 3 || last7 <= 3 * prior7) return null;
  const top = Object.entries(live.per_guard).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "chain";
  return { last7, prior7, guard: top };
}

function checkReceipts(root?: string | null): CheckResult {
  // 7. receipts aggregate vs budget — four numbers plus the top denier, the
  // ledger's repeats and the 7-day deviation, all on the same line.
  const dir = receiptsDir(root);
  const summary = summarizeReceipts(dir ?? undefined);
  let detail = `${summary.total} runs · ${summary.denies} denies · p50 ${summary.p50}ms · p95 ${summary.p95}ms (ceiling ${CEILING_MS})`;
  if (summary.denies > 0) {
    const topOf = (m: Record<string, number>) => Object.entries(m).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "-";
    detail += ` · top ${topOf(summary.per_guard)}/${topOf(summary.per_tool)}`;
  }
  let repeats = 0;
  try {
    const ledger = JSON.parse(readFileSync(join(dir!, "denies.json"), "utf8")) as DenyLedger;
    // Forged shapes (string n, NaN, object) coerce to 0, never NaN — the repeats
    // count a human reads cannot be made to vanish or inflate by writing the file
    // (audit run-1 F2b).
    repeats = Object.values(ledger).reduce((sum, e) => {
      const n = typeof e?.n === "number" && Number.isFinite(e.n) ? Math.floor(e.n) : 0;
      return sum + Math.max(0, n - 1);
    }, 0);
  } catch {
    /* no ledger yet */
  }
  if (repeats > 0) detail += ` · repeats ${repeats}`;
  const spike = denySpike(dir);
  if (spike) detail += ` · spike ${spike.last7} vs ${spike.prior7} the week before (${spike.guard})`;
  return { name: "receipts", status: summary.p95 <= CEILING_MS && spike === null ? "ok" : "warn", detail };
}

function checkOverrides(root: string | null): CheckResult {
  // 8. overrides: active → permanent WARN until they expire (§12.1); expired → the
  //    guard is live again but the entry is still dead config, so it is named with
  //    the fix. §14.2 shows the days left; §14.5b wants the action, not just the fact.
  const overrides = readOverrides(root);
  const now = Date.now();
  const described = overrides.map((entry) => {
    const days = overrideDaysLeft(entry, now);
    let label: string;
    if (days === null) label = "no expiry — add an until";
    else if (days === 0) label = "expires today";
    else label = `expires in ${days}d`;
    return { entry, days, label };
  });
  const rows = described
    .filter((d) => d.days === null || d.days >= 0)
    .map((d) => `${d.entry.name} — ${d.entry.reason.slice(0, 40)} (${d.label})`);
  const stale = described
    .filter((d) => d.days !== null && d.days < 0)
    .map((d) => `${d.entry.name} — expired ${String(d.entry.until).slice(0, 10)} → remove it from .ai-engineering/overrides.toml`);
  const detail = described.length === 0 ? "none active" : [...rows, ...stale].join(" · ");
  return { name: "overrides", status: described.length === 0 ? "ok" : "warn", detail };
}

/** A source tree is `src/` at the root, or `<package>/src/` one level down
 *  (`kit/src`, `web/src`). An empty `src/` still counts: the check is "code can
 *  live here", and the existing doctor pin is that directory's presence. */
function hasSourceTree(root: string): boolean {
  if (existsSync(join(root, "src"))) return true;
  let names: string[] = [];
  try {
    names = readdirSync(root);
  } catch {
    return false;
  }
  for (const name of names) {
    if (name.startsWith(".") || name === "node_modules") continue;
    if (existsSync(join(root, name, "src"))) return true;
  }
  return false;
}

function checkArch(root: string | null): CheckResult {
  // 9. arch bootstrap vs active. The rules file is what makes the check a check: a path
  //    that is only joined is never null, so a repo with src/ and no arch.rules.json
  //    would report "ok · active" — the false green this project exists to refuse.
  const archPath = root ? join(root, ".ai-engineering", "arch.rules.json") : null;
  const hasRules = archPath !== null && existsSync(archPath);
  if (!hasRules) return { name: "arch", status: "warn", detail: "no arch.rules.json — nothing enforces the layer rules" };
  if (!root || !hasSourceTree(root)) return { name: "arch", status: "warn", detail: "bootstrap mode — src/ empty" };
  const atRoot = existsSync(join(root, "src"));
  return { name: "arch", status: "ok", detail: atRoot ? "active — src/ present" : "active — source outside src/" };
}

function checkSpecSlot(root: string | null): CheckResult {
  // 10. milestone slots: a live contract, and the artifacts a dead one leaves behind.
  //     A milestone that never opened a contract has no live contract to close, so its
  //     brainstorm.html would stay immortal and doctor would call the slot clean (§21.2) —
  //     which is why orphans are reported.
  const specPath = root ? join(root, ".ai-engineering", "spec.html") : null;
  const hasContract = specPath !== null && existsSync(specPath);
  if (hasContract) {
    const lockPath = join(root ?? "", ".ai-engineering", "ai-eng.lock");
    const pinned = existsSync(lockPath) ? Boolean(parseLock(readFileSync(lockPath, "utf8")).spec_sha256) : false;
    // A pre-rename brainstorm.md under a live contract is stale slot material: the
    // slot is brainstorm.html since the artifact design landed (§21.2). Name it so
    // the session deletes or migrates it instead of leaving it immortal.
    const legacy = root && existsSync(join(root, ".ai-engineering", "brainstorm.md"));
    if (pinned && legacy) return { name: "spec slot", status: "warn", detail: "contract approved (sha256 in lock) · legacy brainstorm.md present — migrate to brainstorm.html or delete it" };
    return { name: "spec slot", status: pinned ? "ok" : "warn", detail: pinned ? "contract approved (sha256 in lock)" : "live spec.html WITHOUT approval — STOP 1 pending or zombie contract" };
  }
  const orphans = root
    ? ["brainstorm.html", "recap.html"].filter((name) => existsSync(join(root, ".ai-engineering", name)))
    : [];
  if (orphans.length === 0) return { name: "spec slot", status: "ok", detail: "clean slot: 0 zombie contracts" };
  return { name: "spec slot", status: "warn", detail: `orphan ${orphans.join(" + ")} with no live contract — the milestone it belongs to is closed: delete it (git keeps the history)` };
}

function checkResearchCache(root: string | null): CheckResult {
  const cacheDir = root ? join(root, ".ai-engineering", "research-cache") : null;
  if (!cacheDir || !existsSync(cacheDir)) return { name: "research cache", status: "ok", detail: "no cache directory (created on first research run)" };
  const files = readdirSync(cacheDir).filter((f) => f.endsWith(".md"));
  if (files.length === 0) return { name: "research cache", status: "ok", detail: "empty cache" };
  const now = Date.now();
  const stale: string[] = [];
  const fresh: string[] = [];
  for (const file of files) {
    const filePath = join(cacheDir, file);
    try {
      const ageMs = now - statSync(filePath).mtimeMs;
      const ageDays = Math.floor(ageMs / 86_400_000);
      if (ageDays > 30) stale.push(`${file} (${ageDays}d)`);
      else fresh.push(file);
    } catch {
      fresh.push(file);
    }
  }
  const lines: string[] = [`${files.length} files`];
  if (stale.length > 0) lines.push(`${stale.length} stale (>30d): ${stale.join(", ")}`);
  if (fresh.length > 0) lines.push(`${fresh.length} fresh`);
  return { name: "research cache", status: stale.length > 0 ? "warn" : "ok", detail: lines.join(" · ") };
}

async function checkTriggers(root: string | null): Promise<CheckResult | null> {
  // 10b. conditional nodes: a trigger that fired and left no artifact. This is the
  //      "if it touches UI" sentence made checkable (§20.1).
  const specPath = root ? join(root, ".ai-engineering", "spec.html") : null;
  const hasContract = specPath !== null && existsSync(specPath);
  if (!hasContract || !root) return null;
  const lock = parseLock(readFileSync(join(root, ".ai-engineering", "ai-eng.lock"), "utf8"));
  if (!lock.base_sha) return { name: "triggers", status: "warn", detail: "no base_sha in the lock — this milestone cannot judge its conditional nodes; reopen it with ai-eng spec open" };
  const spec = readFileSync(join(root, ".ai-engineering", "spec.html"), "utf8");
  const abandoned = new Set([...spec.matchAll(/^ABANDON:\s*(\S+)/gm)].map((m) => m[1]!));
  const unmet = unmetTriggers(root, lock.base_sha, abandoned);
  if (unmet.length === 0) return { name: "triggers", status: "ok", detail: "no fired trigger is missing its artifact" };
  return { name: "triggers", status: "warn", detail: unmet.map((entry) => `${entry.id} fired on ${entry.sample} → ${entry.skill} left no artifact`).join(" · ") };
}

function checkSurfaces(root: string | null, surfaces: string[]): CheckResult[] {
  // 11. surfaces: two questions that must never share one line.
  //     (a) the MACHINE carrier — is it where that host actually reads, and is it the
  //         one this binary ships? Existence is not the question: the OMP carrier sat
  //         in `.agents/hooks/` for a year, absent from nothing and read by nobody.
  //     (b) the REPO declaration — for the two hosts whose readers live in the
  //         checkout, is their carrier in the repo?
  const rows: CheckResult[] = [];
  for (const id of surfaces) {
    const surface = SURFACES.find((s) => s.id === id);
    if (!surface) continue;
    const machine = machineCarrier(surface);
    const repo = repoCarrier(surface);
    const files = carrierFiles(id, "machine");
    const parts: string[] = [];
    let status: CheckResult["status"] = "ok";
    if (machine && files) {
      const absolute = carrierPath(machine);
      if (!existsSync(absolute)) {
        status = surface.tier === "core" ? "fail" : "warn";
        parts.push(`machine carrier ~/${machine.path} missing → ai-eng update`);
      } else if (machine.kind === "module") {
        // A missing chain bundle beside a current entry is drift, not a crash: the
        // half-installed module host is exactly the state this check exists to report,
        // and a health check that throws on it reports nothing at all (§14.2).
        const chainPath = machine.chain === undefined ? null : carrierPath(machine, machine.chain);
        const chainDrift =
          chainPath !== null && files.chain !== null && (!existsSync(chainPath) || readFileSync(chainPath, "utf8") !== files.chain);
        const drift = readFileSync(absolute, "utf8") !== files.main || chainDrift;
        if (drift) status = "warn";
        parts.push(drift ? `machine carrier ~/${machine.path} is NOT the one this binary ships → ai-eng update` : `machine carrier ~/${machine.path} matches the binary`);
      } else {
        const ours = readFileSync(absolute, "utf8").includes("ai-eng chain");
        if (!ours) status = "warn";
        parts.push(ours ? `machine carrier ~/${machine.path} carries the ai-eng entries` : `machine carrier ~/${machine.path} has no ai-eng entries → ai-eng update`);
      }
    }
    if (repo) {
      const present = root !== null && existsSync(join(root, repo.path));
      if (!present) {
        if (status !== "fail" && surface.tier !== "best-effort") status = "fail";
        else if (status === "ok" && surface.tier === "best-effort") status = "warn";
      }
      parts.push(present ? `repo carrier ${repo.path} present` : `repo carrier ${repo.path} missing → ai-eng update`);
    }
    if (parts.length === 0) parts.push("no carrier: guard wiring is not implemented for this host");
    // The row's own caveat, from one place: the surface's measured `note` field,
    // not a substring guess by the row printer.
    if (surface.note !== undefined) parts.push(surface.note);
    rows.push({ name: `surface ${id}`, status, detail: parts.join(" · ") });
  }
  return rows;
}

function checkMachineState(surfaces: string[]): CheckResult | null {
  // 11b. the machine STATE — the third question, and the one no file answers: which
  //      binary wrote the carriers, and whether this one is older than that record. A
  //      downgrade is not cosmetic: the carrier is the new binary's, the chain it calls
  //      would be the old one, and the old one has no gate — so the policy would fall
  //      back onto repos that never asked for it (F7).
  const state = readMachineState();
  if (Object.keys(state.carriers).length === 0) return null;
  const downgrade = state.version !== "" && state.version !== VERSION && compareVersions(state.version, VERSION) > 0;
  const changed = surfaces.filter((id) => {
    const files = carrierFiles(id, "machine");
    const recorded = state.carriers[id];
    return files !== null && recorded !== undefined && recorded !== sha256(files.main);
  });
  let status: CheckResult["status"];
  let detail: string;
  if (downgrade) {
    status = "warn";
    detail = `carriers were written by ${state.version} and this binary is ${VERSION} — a DOWNGRADE: they would call an older chain that has no gate → install ${state.version} again, or update with it`;
  } else if (changed.length > 0) {
    status = "warn";
    detail = `carrier definition changed since ${state.version}: ${changed.join(", ")}${changed.includes("codex") ? " — Codex re-asks for trust in /hooks after any byte change" : " → ai-eng update"}`;
  } else {
    status = "ok";
    detail = `carriers written by ${VERSION} · definitions unchanged`;
  }
  return { name: "machine state", status, detail };
}

function checkBehaviors(root: string | null): CheckResult {
  // 12. behaviors lint (§21.5) — same frontmatter rules as skills.
  const behaviorsDir = root ? join(root, ".agents", "behaviors") : null;
  if (behaviorsDir && existsSync(behaviorsDir)) {
    const bad: string[] = [];
    for (const entry of readdirSync(behaviorsDir)) {
      const behavior = join(behaviorsDir, entry, "BEHAVIOR.md");
      if (!existsSync(behavior)) continue;
      const lint = lintBehavior(readFileSync(behavior, "utf8"), entry);
      if (lint) bad.push(`${entry}: ${lint}`);
    }
    return { name: "behaviors", status: bad.length === 0 ? "ok" : "fail", detail: bad.length === 0 ? "frontmatter ok" : bad.join(" · ") };
  }
  return { name: "behaviors", status: "ok", detail: "no behaviors declared" };
}

async function runChecks(cwd = process.cwd()): Promise<{ results: CheckResult[]; fail: boolean }> {
  const root = repoRoot(cwd);
  const gap = governanceGap(root);
  const surfaces = gap === null ? enabledSurfaces() : [];
  const results: CheckResult[] = [checkAgents(root), checkConfig(gap, surfaces)];
  const mirrors = await checkMirrors(root);
  if (mirrors) results.push(mirrors);
  results.push(checkCanon());
  const assets = checkAssets(root);
  if (assets) results.push(assets);
  const floor = checkGitFloor(root);
  if (floor) results.push(floor);
  results.push(checkChainTest(gap));
  results.push(checkReceipts(root));
  results.push(checkOverrides(root));
  results.push(checkArch(root));
  results.push(checkSpecSlot(root));
  results.push(checkResearchCache(root));
  const triggers = await checkTriggers(root);
  if (triggers) results.push(triggers);
  results.push(...checkSurfaces(root, surfaces));
  results.push({ name: "checkpoint gate", status: "ok", detail: checkpointGateReportLines(SURFACES, Object.fromEntries(SURFACES.flatMap((s) => { const files = carrierFiles(s.id, "machine") ?? carrierFiles(s.id, "repo"); return files ? [[s.id, files.main] as const] : []; }))).join(" · ") });
  const state = checkMachineState(surfaces);
  if (state) results.push(state);
  results.push(checkBehaviors(root));
  return { results, fail: results.some((r) => r.status === "fail") };
}

/** The files whose citation protects an artifact from gc. spec.html, plan.html and
 *  brainstorm.html die at close, so immunity they granted would die with them (§21.3). */
const PERMANENT_GOVERNORS = ["DECISIONS.md", "NOTICE", join(".ai-engineering", "arch.rules.json")];

/** Cited by a working file that outlives the milestone — the only immunity there is.
 *  The citation is the artifact's own name, or its number qualified by its folder
 *  (`research/014`): a bare `014` also matches `D-014`, and immunity handed out by a
 *  decision *number* would protect artifacts nobody ever referenced. */
function citedByGovernor(root: string, folder: string, name: string): boolean {
  const nnn = /^(\d{3})/.exec(name)?.[1];
  const qualified = nnn ? `${folder}/${nnn}` : null;
  for (const governor of PERMANENT_GOVERNORS) {
    const path = join(root, governor);
    if (!existsSync(path)) continue;
    const text = readFileSync(path, "utf8");
    if (text.includes(name)) return true;
    if (qualified !== null && text.includes(qualified)) return true;
  }
  return false;
}

/** Deleting from the tree is only safe when git already holds the file: the history IS
 *  the archive, and a file nobody committed has no history to fall back on. */
function trackedByGit(root: string, path: string): boolean {
  return spawnSync("git", ["-C", root, "ls-files", "--error-unmatch", "--", path], { stdio: "ignore" }).status === 0;
}

/** Age in days from the last commit that touched the path — an mtime is a checkout, not a date. */
function committedAgeDays(root: string, path: string): number | null {
  const out = spawnSync("git", ["-C", root, "log", "-1", "--format=%ct", "--", path], { encoding: "utf8" });
  const seconds = Number(out.stdout.trim());
  return out.status === 0 && Number.isFinite(seconds) && seconds > 0 ? (Date.now() / 1000 - seconds) / 86_400 : null;
}

/** `doctor --gc` — execute what the audit proposes, in one commit (§21.3). */
/** Merge the live summary with any prior summary.json and write it back. */
function mergeAndWriteSummary(receipts: string, summary: ReceiptSummary): void {
  let prior: { daily?: Record<string, DailyPoint> } | null = null;
  try {
    prior = JSON.parse(readFileSync(join(receipts, "summary.json"), "utf8")) as { daily?: Record<string, DailyPoint> };
  } catch {
    /* no prior summary, or a torn one: the live window starts the series */
  }
  const merged = { ...summary, daily: mergeDaily(prior?.daily, summary.daily), gc: new Date().toISOString() };
  writeFileSync(join(receipts, "summary.json"), JSON.stringify(merged));
}

function gcReceipts(receipts: string, ttlDays: number): string[] {
  // Receipts: aggregate, then delete. They carry no citation to respect — their
  // permanent half is the Receipt-Id trailer on the commit. Two files are the gc's
  // own memory, not its trash: summary.json (the series) and denies.json (the
  // ledger). The mtime sweep skips both — leaving summary.json to age out was
  // eating the only long-term memory on the second quiet month — and each is
  // pruned by its own contents instead: the series by day-age, the ledger by
  // last_seen and count.
  const lines: string[] = [];
  if (!existsSync(receipts)) return lines;
  const summary = summarizeReceipts(receipts);
  const cut = Date.now() - ttlDays * 86_400_000;
  // Files only: a planted DIRECTORY named like a receipt (`mkdir bomb.json`) made
  // unlinkSync throw EISDIR/EPERM before the summary write, bricking the gc on
  // every future run and freezing the spike baseline at the forged state
  // (audit run-1 F4). A directory in the receipts folder is not a receipt.
  const stale = readdirSync(receipts)
    .filter((name) => name !== "summary.json" && name !== "denies.json" && lstatSync(join(receipts, name)).isFile())
    .map((name) => ({ name, ts: statMtime(join(receipts, name)) }))
    .filter((entry) => entry.ts < cut);
  for (const entry of stale) unlinkSync(join(receipts, entry.name));
  if (stale.length > 0) {
    mergeAndWriteSummary(receipts, summary);
    lines.push(`✓ receipts: ${stale.length} aggregated into summary.json and deleted (ttl ${ttlDays}d)`);
  }
  const ledger = join(receipts, "denies.json");
  if (existsSync(ledger)) pruneDenyLedger(ledger);
  return lines;
}

/** Should this entry be collected (deleted) during gc? Returns "immune" if cited
 *  by a governor, "collect" if old enough and tracked by git, "skip" otherwise. */
function collectVerdict(root: string, folder: string, dir: string, name: string, olderDays: number): "immune" | "collect" | "skip" {
  if (citedByGovernor(root, folder, name)) return "immune";
  const age = committedAgeDays(root, join(dir, name));
  if (age === null || age < olderDays || !trackedByGit(root, join(dir, name))) return "skip";
  return "collect";
}

function gcFolder(root: string, folder: string, maxFiles: number, olderDays: number): string[] {
  // The NNN folders: cited is immune, young is left alone, and only what git already
  // holds is ever deleted — the tree is the cache of the living, git is the archive.
  const lines: string[] = [];
  const dir = join(root, ".ai-engineering", folder);
  if (!existsSync(dir)) return lines;
  const entries = readdirSync(dir).filter((name) => name !== "summary.json");
  const collected: string[] = [];
  let immune = 0;
  for (const name of entries) {
    const verdict = collectVerdict(root, folder, dir, name, olderDays);
    if (verdict === "immune") { immune += 1; continue; }
    if (verdict === "skip") continue;
    unlinkSync(join(dir, name));
    collected.push(`${folder}/${name}`);
  }
  if (collected.length > 0) lines.push(`✓ ${folder}/: archived ${collected.length} in git and deleted (${collected.join(", ")})`);
  if (immune > 0) lines.push(`  ${folder}/: ${immune} cited by a permanent governor — immune`);
  const remaining = readdirSync(dir).length;
  if (remaining > maxFiles) lines.push(`⚠ ${folder}/: ${remaining} > max_files=${maxFiles} — review before the next pass`);
  return lines;
}

/** Should this security run be pruned during gc? True if not cited by a governor,
 *  old enough, and already tracked by git. */
function shouldPruneRun(root: string, security: string, run: string, olderDays: number): boolean {
  if (citedByGovernor(root, "security", run)) return false;
  const age = committedAgeDays(root, join(security, run));
  if (age === null || age < olderDays || !trackedByGit(root, join(security, run))) return false;
  return true;
}

function gcSecurity(root: string, security: string, olderDays: number, keepRuns: number): string[] {
  // Security runs: the newest keep_runs are always live; beyond that the same rule.
  const lines: string[] = [];
  if (!existsSync(security)) return lines;
  const runs = readdirSync(security)
    .filter((name) => name.startsWith("run-"))
    .sort((a, b) => a.localeCompare(b, "en"));
  const beyond = runs.slice(0, Math.max(0, runs.length - keepRuns));
  const collected: string[] = [];
  for (const run of beyond) {
    if (!shouldPruneRun(root, security, run, olderDays)) continue;
    rmSync(join(security, run), { recursive: true, force: true });
    collected.push(`security/${run}`);
  }
  if (collected.length > 0) lines.push(`✓ security/: archived ${collected.length} in git and deleted (keeping the last ${keepRuns})`);
  else if (runs.length > keepRuns) lines.push(`  security/: ${runs.length} runs, keeping the last ${keepRuns}`);
  return lines;
}

function gcResearchCache(root: string, olderDays: number): string[] {
  const cacheDir = join(root, ".ai-engineering", "research-cache");
  if (!existsSync(cacheDir)) return [];
  const files = readdirSync(cacheDir).filter((f) => f.endsWith(".md"));
  const now = Date.now();
  const deleted: string[] = [];
  for (const file of files) {
    const filePath = join(cacheDir, file);
    try {
      const ageMs = now - statSync(filePath).mtimeMs;
      const ageDays = Math.floor(ageMs / 86_400_000);
      if (ageDays > olderDays) {
        unlinkSync(filePath);
        deleted.push(`${file} (${ageDays}d)`);
      }
    } catch {
      /* skip */
    }
  }
  if (deleted.length > 0) return [`✓ research-cache/: pruned ${deleted.length} stale entries: ${deleted.join(", ")}`];
  return [];
}

function gc(cwd = process.cwd()): string[] {
  const root = repoRoot(cwd);
  const lines: string[] = [];
  if (!root) return ["no repo: nothing to collect"];
  const config = loadConfig();
  const gcConfig = config["gc"] ?? {};
  const maxFiles = Number(gcConfig["max_files"] ?? 25);
  const ttlDays = Number(String(gcConfig["receipts_ttl"] ?? "30d").replace("d", ""));
  const olderDays = Number(String(gcConfig["older_than"] ?? "90d").replace("d", ""));
  const keepRuns = Number(gcConfig["keep_runs"] ?? 5);
  lines.push(...gcReceipts(join(root, ".ai-engineering", "receipts"), ttlDays));
  for (const folder of ["research", "reports", join("design", "audits")]) {
    lines.push(...gcFolder(root, folder, maxFiles, olderDays));
  }
  lines.push(...gcResearchCache(root, olderDays));
  lines.push(...gcSecurity(root, join(root, ".ai-engineering", "security"), olderDays, keepRuns));
  if (lines.length === 0) lines.push("✓ gc: nothing to collect");
  return lines;
}

function statMtime(path: string): number {
  try {
    return lstatSync(path).mtimeMs;
  } catch {
    return 0;
  }
}

function lintBehavior(content: string, folder: string): string | null {
  const match = /^---\n([\s\S]*?)\n---/.exec(content);
  if (!match) return "no frontmatter";
  const body = match[1] ?? "";
  const name = /^name:\s*(.+)$/m.exec(body)?.[1]?.trim();
  if (name !== folder) return `name=${name} ≠ folder ${folder}`;
  const description = /^description:\s*(.+)$/m.exec(body)?.[1]?.trim() ?? "";
  if (description.length === 0 || description.length > 1024) return "description empty or >1024";
  return null;
}

export async function doctorMain(flags: { gc?: boolean; cwd?: string }): Promise<number> {
  if (flags.gc) {
    for (const line of gc()) process.stdout.write(`${line}\n`);
    return 0;
  }
  const root = repoRoot(flags.cwd) ?? flags.cwd ?? process.cwd();
  const { results, fail } = await runChecks(flags.cwd);
  const runtime = `bun ${typeof Bun !== "undefined" ? Bun.version : "?"}`;
  ui.frame(`Health check · ${root.split("/").pop()} · ${runtime} · ai-eng ${VERSION}`);
  // One block per status — the eye scans three ideas, not twelve lines
  // (the ✓/▲/✗ families of §14.2).
  const toRow = (r: CheckResult): ui.Row => ({ mark: r.status, text: `${r.name} · ${r.detail}` });
  const oks = results.filter((r) => r.status === "ok");
  const warns = results.filter((r) => r.status === "warn");
  const fails = results.filter((r) => r.status === "fail");
  if (fails.length > 0) ui.section("FAIL — the chain is broken here", fails.map(toRow));
  if (warns.length > 0) ui.section("Attention", warns.map(toRow), "not fatal — decide with the detail");
  ui.section("Checks passed", oks.map(toRow));
  ui.summary(oks.length, warns.length, fails.length);
  ui.end(fail ? "FAIL present — fix before trusting the chain." : "Chain verified. Next: keep working.");
  return fail ? 2 : 0;
}
