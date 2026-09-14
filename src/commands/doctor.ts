// `ai-eng doctor` — 12 checks + one real test. The difference with theater: it
// EXECUTES an adversarial payload and measures real latency. A hook that does not
// deny, or denies slow, is FAIL — not WARN (§14.2).
import { canonDrift } from "../embed.ts";
import { existsSync, readFileSync, readdirSync, lstatSync, unlinkSync, writeFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { repoRoot, loadConfig, home, governanceGap, enabledSurfaces } from "../env.ts";
import { summarizeReceipts } from "../receipts.ts";
import { parseLock, sha256 } from "../install.ts";
import { SURFACES, machineCarrier, repoCarrier, carrierFiles, carrierPath, readMachineState } from "../surfaces/adapters.ts";
import { unmetTriggers } from "../spec/triggers.ts";
import { VERSION } from "../version.ts";
import { runChain } from "../chain/mod.ts";
import { readOverrides, overrideDaysLeft } from "../chain/dialect.ts";
import * as ui from "../ui.ts";

export type CheckResult = { readonly name: string; readonly status: "ok" | "warn" | "fail"; readonly detail: string };

const CEILING_MS = 50;

/** Numeric segment compare: "2.10.0" is newer than "2.9.0", which a string compare gets
 *  wrong in exactly the release where it matters. */
function compareVersions(a: string, b: string): number {
  const left = a.split(".").map((part) => Number.parseInt(part, 10) || 0);
  const right = b.split(".").map((part) => Number.parseInt(part, 10) || 0);
  for (let i = 0; i < Math.max(left.length, right.length); i += 1) {
    const diff = (left[i] ?? 0) - (right[i] ?? 0);
    if (diff !== 0) return diff;
  }
  return 0;
}

function checkAgents(root: string | null): CheckResult {
  // 1. AGENTS.md present, rule-bearing, under the context ceiling.
  const agentsPath = root ? join(root, "AGENTS.md") : null;
  if (!agentsPath || !existsSync(agentsPath)) return { name: "AGENTS.md", status: "fail", detail: "missing — the contract was never installed" };
  const content = readFileSync(agentsPath, "utf8");
  const rules = (content.match(/^[ \t]*(?:\d+\.|-)[ \t]+\S/gm) ?? []).length;
  const lines = content.split("\n").length;
  return { name: "AGENTS.md", status: lines <= 80 && rules >= 6 ? "ok" : "warn", detail: `${rules} rules · ${lines} lines${lines > 80 ? " (over the context ceiling)" : ""}` };
}

function checkClaude(root: string | null): CheckResult {
  // 2. CLAUDE.md imports AGENTS.md or is a symlink.
  const claudePath = root ? join(root, "CLAUDE.md") : null;
  if (!claudePath || !existsSync(claudePath)) return { name: "CLAUDE.md", status: "warn", detail: "absent" };
  let ok = false;
  try {
    ok = lstatSync(claudePath).isSymbolicLink() || readFileSync(claudePath, "utf8").includes("@AGENTS.md");
  } catch {
    ok = false;
  }
  return { name: "CLAUDE.md", status: ok ? "ok" : "warn", detail: ok ? "imports AGENTS.md" : "does not reference AGENTS.md" };
}

function checkConfig(gap: string | null, surfaces: string[]): CheckResult {
  // 3. config.toml — this IS the gate. Absent, corrupt and declared are three
  //    different states, and "I could not read it" must never read as ok: the chain
  //    treats an unreadable file as an undeclared repo, so a green here would be a
  //    lie about the exact file the policy hangs on (F2).
  let detail: string;
  if (gap === null) {
    detail = `governed · surfaces: ${surfaces.length > 0 ? surfaces.join(", ") : "none declared"}`;
  } else if (gap === "no-config") {
    detail = "absent — the gate reads this file; without it this repo is not governed";
  } else if (gap === "corrupt-config") {
    detail = "unparseable — the chain treats this repo as ungoverned; fix the TOML or re-run ai-eng init";
  } else if (gap === "no-surfaces") {
    detail = "no [surfaces] enabled list — the gate needs the declaration, not just the file";
  } else {
    detail = "no repository above this directory";
  }
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
  } else if (outcome.action === "deny" && ms <= CEILING_MS) {
    status = "ok";
    detail = `adversarial payload (git commit -n) → DENY in ${ms}ms`;
  } else if (outcome.action === "deny") {
    status = "warn";
    detail = `adversarial payload (git commit -n) → DENY in ${ms}ms`;
  } else {
    status = "fail";
    detail = `adversarial payload NOT denied (${outcome.action}) in ${ms}ms`;
  }
  return { name: "chain test", status, detail };
}

function checkReceipts(): CheckResult {
  // 7. receipts aggregate vs budget.
  const summary = summarizeReceipts();
  return { name: "receipts", status: summary.p95 <= CEILING_MS ? "ok" : "warn", detail: `${summary.total} runs · ${summary.denies} denies · p50 ${summary.p50}ms · p95 ${summary.p95}ms (ceiling ${CEILING_MS})` };
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

function checkArch(root: string | null): CheckResult {
  // 9. arch bootstrap vs active. The rules file is what makes the check a check: a path
  //    that is only joined is never null, so a repo with src/ and no arch.rules.json used
  //    to report "ok · active" — the false green this project exists to refuse.
  const archPath = root ? join(root, ".ai-engineering", "arch.rules.json") : null;
  const hasRules = archPath !== null && existsSync(archPath);
  const hasSrc = root ? existsSync(join(root, "src")) : false;
  if (!hasRules) return { name: "arch", status: "warn", detail: "no arch.rules.json — nothing enforces the layer rules" };
  return { name: "arch", status: hasSrc ? "ok" : "warn", detail: hasSrc ? "active — src/ present" : "bootstrap mode — src/ empty" };
}

function checkSpecSlot(root: string | null): CheckResult {
  // 10. milestone slots: a live contract, and the artifacts a dead one leaves behind.
  //     A milestone that never opened a contract could never be closed either, so its
  //     brainstorm.md was immortal and doctor called the slot clean (§21.2).
  const specPath = root ? join(root, ".ai-engineering", "spec.html") : null;
  const hasContract = specPath !== null && existsSync(specPath);
  if (hasContract) {
    const lockPath = join(root ?? "", ".ai-engineering", "ai-eng.lock");
    const pinned = existsSync(lockPath) ? Boolean(parseLock(readFileSync(lockPath, "utf8")).spec_sha256) : false;
    return { name: "spec slot", status: pinned ? "ok" : "warn", detail: pinned ? "contract approved (sha256 in lock)" : "live spec.html WITHOUT approval — STOP 1 pending or zombie contract" };
  }
  const orphans = root
    ? ["brainstorm.md", "recap.html"].filter((name) => existsSync(join(root, ".ai-engineering", name)))
    : [];
  if (orphans.length === 0) return { name: "spec slot", status: "ok", detail: "clean slot: 0 zombie contracts" };
  return { name: "spec slot", status: "warn", detail: `orphan ${orphans.join(" + ")} with no live contract — the milestone it belongs to is closed: delete it (git keeps the history)` };
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
        if (status === "fail") status = "fail";
        else if (surface.tier === "best-effort") status = "warn";
        else status = "fail";
      }
      parts.push(present ? `repo carrier ${repo.path} present` : `repo carrier ${repo.path} missing → ai-eng update`);
    }
    if (parts.length === 0) parts.push("no carrier: guard wiring is not implemented for this host");
    // The row's own caveat, from one place: doctor no longer guesses it from a substring.
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
  const results: CheckResult[] = [checkAgents(root), checkClaude(root), checkConfig(gap, surfaces)];
  const mirrors = await checkMirrors(root);
  if (mirrors) results.push(mirrors);
  results.push(checkCanon());
  const assets = checkAssets(root);
  if (assets) results.push(assets);
  const floor = checkGitFloor(root);
  if (floor) results.push(floor);
  results.push(checkChainTest(gap));
  results.push(checkReceipts());
  results.push(checkOverrides(root));
  results.push(checkArch(root));
  results.push(checkSpecSlot(root));
  const triggers = await checkTriggers(root);
  if (triggers) results.push(triggers);
  results.push(...checkSurfaces(root, surfaces));
  const state = checkMachineState(surfaces);
  if (state) results.push(state);
  results.push(checkBehaviors(root));
  return { results, fail: results.some((r) => r.status === "fail") };
}

/** The files whose citation protects an artifact from gc. spec.html, plan.html and
 *  brainstorm.md die at close, so immunity they granted would die with them (§21.3). */
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
function gcReceipts(receipts: string, ttlDays: number): string[] {
  // Receipts: aggregate, then delete. They carry no citation to respect — their
  // permanent half is the Receipt-Id trailer on the commit.
  const lines: string[] = [];
  if (!existsSync(receipts)) return lines;
  const summary = summarizeReceipts(receipts);
  const cut = Date.now() - ttlDays * 86_400_000;
  const stale = readdirSync(receipts)
    .map((name) => ({ name, ts: statMtime(join(receipts, name)) }))
    .filter((entry) => entry.ts < cut);
  for (const entry of stale) unlinkSync(join(receipts, entry.name));
  if (stale.length > 0) {
    writeFileSync(join(receipts, "summary.json"), JSON.stringify({ ...summary, gc: new Date().toISOString() }));
    lines.push(`✓ receipts: ${stale.length} aggregated into summary.json and deleted (ttl ${ttlDays}d)`);
  }
  return lines;
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
    const path = join(dir, name);
    if (citedByGovernor(root, folder, name)) {
      immune += 1;
      continue;
    }
    const age = committedAgeDays(root, path);
    if (age === null || age < olderDays || !trackedByGit(root, path)) continue;
    unlinkSync(path);
    collected.push(`${folder}/${name}`);
  }
  if (collected.length > 0) lines.push(`✓ ${folder}/: archived ${collected.length} in git and deleted (${collected.join(", ")})`);
  if (immune > 0) lines.push(`  ${folder}/: ${immune} cited by a permanent governor — immune`);
  const remaining = readdirSync(dir).length;
  if (remaining > maxFiles) lines.push(`⚠ ${folder}/: ${remaining} > max_files=${maxFiles} — review before the next pass`);
  return lines;
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
    const path = join(security, run);
    if (citedByGovernor(root, "security", run)) continue;
    const age = committedAgeDays(root, path);
    if (age === null || age < olderDays || !trackedByGit(root, path)) continue;
    rmSync(path, { recursive: true, force: true });
    collected.push(`security/${run}`);
  }
  if (collected.length > 0) lines.push(`✓ security/: archived ${collected.length} in git and deleted (keeping the last ${keepRuns})`);
  else if (runs.length > keepRuns) lines.push(`  security/: ${runs.length} runs, keeping the last ${keepRuns}`);
  return lines;
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

export async function doctorMain(flags: { gc?: boolean }): Promise<number> {
  if (flags.gc) {
    for (const line of gc()) process.stdout.write(`${line}\n`);
    return 0;
  }
  const root = repoRoot() ?? process.cwd();
  const { results, fail } = await runChecks();
  const runtime = `bun ${typeof Bun !== "undefined" ? Bun.version : "?"}`;
  ui.frame(`Health check · ${root.split("/").pop()} · ${runtime} · ai-eng ${VERSION}`);
  // One block per status — the eye scans three ideas, not twelve lines
  // (the ✓/▲/✗ families of §14.2).
  const markOf = (status: CheckResult["status"]): "ok" | "warn" | "fail" => {
    if (status === "ok") return "ok";
    if (status === "warn") return "warn";
    return "fail";
  };
  const toRow = (r: CheckResult): ui.Row => ({ mark: markOf(r.status), text: `${r.name} · ${r.detail}` });
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
