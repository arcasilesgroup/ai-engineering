// `ai-eng doctor` — 12 checks + one real test. The difference with theater: it
// EXECUTES an adversarial payload and measures real latency. A hook that does not
// deny, or denies slow, is FAIL — not WARN (§14.2).
import { canonDrift, embeddedChainBundle } from "../embed.ts";
import { existsSync, readFileSync, readdirSync, lstatSync, unlinkSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { repoRoot, loadConfig, home } from "../env.ts";
import { summarizeReceipts } from "../receipts.ts";
import { parseLock } from "../install.ts";
import { SURFACES } from "../surfaces/adapters.ts";
import { VERSION } from "../version.ts";
import { runChain } from "../chain/mod.ts";
import { readOverrides, overrideDaysLeft } from "../chain/dialect.ts";
import * as ui from "../ui.ts";

export type CheckResult = { readonly name: string; readonly status: "ok" | "warn" | "fail"; readonly detail: string };

const CEILING_MS = 50;

async function runChecks(cwd = process.cwd()): Promise<{ results: CheckResult[]; fail: boolean }> {
  const results: CheckResult[] = [];
  const root = repoRoot(cwd);
  const push = (name: string, status: CheckResult["status"], detail: string) => results.push({ name, status, detail });

  // 1. AGENTS.md present, rule-bearing, under the context ceiling.
  const agentsPath = root ? join(root, "AGENTS.md") : null;
  if (agentsPath && existsSync(agentsPath)) {
    const content = readFileSync(agentsPath, "utf8");
    const rules = (content.match(/^\s*(?:\d+\.|-)\s+\S/gm) ?? []).length;
    const lines = content.split("\n").length;
    push("AGENTS.md", lines <= 80 && rules >= 6 ? "ok" : "warn", `${rules} rules · ${lines} lines${lines > 80 ? " (over the context ceiling)" : ""}`);
  } else {
    push("AGENTS.md", "fail", "missing — the contract was never installed");
  }
  // 2. CLAUDE.md imports AGENTS.md or is a symlink.
  const claudePath = root ? join(root, "CLAUDE.md") : null;
  if (claudePath && existsSync(claudePath)) {
    let ok = false;
    try {
      ok = lstatSync(claudePath).isSymbolicLink() || readFileSync(claudePath, "utf8").includes("@AGENTS.md");
    } catch {
      ok = false;
    }
    push("CLAUDE.md", ok ? "ok" : "warn", ok ? "imports AGENTS.md" : "does not reference AGENTS.md");
  } else {
    push("CLAUDE.md", "warn", "absent");
  }
  // 3. config.toml parseable + surfaces declared.
  const config = loadConfig();
  const surfaces = (config["surfaces"]?.["enabled"] as unknown as string[] | undefined) ?? [];
  push(
    "config.toml",
    existsSync(root ? join(root, ".ai-engineering", "config.toml") : "") ? "ok" : "fail",
    Array.isArray(surfaces) ? `surfaces: ${surfaces.join(", ")}` : "not parseable or missing",
  );
  // 3b. Skill mirrors: the canon only reaches IDEs through them. A mirror dir
  //    missing its links is the P0-1 failure mode (silent ENOENT in installCanon).
  if (root) {
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
    push(
      "mirrors",
      mirrorBroken === 0 ? "ok" : "warn",
      mirrorBroken === 0 ? `${mirrorOK}/${mirrors.length} mirrors carry linked skills` : `${mirrorBroken}/${mirrors.length} mirrors empty or missing → ai-eng init --global`,
    );
  }
  // 4. Canon: the machine's ~/.ai-engineering/skills must byte-match the binary's
  //    embedded payload. The repo lock never contains skills (it lists hooks,
  //    settings, config) — the old filter-by-skills/ check counted 0 forever.
  //    Same predicate as materializeSkills: the dot-entries (chain bundle) are
  //    payload, not canon, so they are neither verified nor counted.
  const canon = canonDrift(home());
  const canonTotal = canon.verified + canon.drift + canon.missing;
  push(
    "canon",
    canon.drift === 0 && canon.missing === 0 ? "ok" : "warn",
    `${canon.verified}/${canonTotal} files verified · ${canon.drift} drift · ${canon.missing} missing`,
  );
  // 4b. Assets outdated: the installed lock records which binary version installed
  //    it. Binary newer than lock → the repo runs stale hooks (§14.2: distinct
  //    from "a newer binary exists" — only update fixes this one).
  const lockPath = root ? join(root, ".ai-engineering", "ai-eng.lock") : null;
  if (lockPath && existsSync(lockPath)) {
    const lockVersion = String(parseLock(readFileSync(lockPath, "utf8")).version || "");
    const detail = !lockVersion
      ? "lock has no version — run ai-eng update"
      : lockVersion === VERSION
        ? `installed by ${VERSION}`
        : `binary ${VERSION} · files installed by ${lockVersion} → ai-eng update`;
    push("assets", lockVersion === VERSION ? "ok" : "warn", detail);
  } else if (root) {
    // Silent absence was how the half-uninstalled repo hid: no lock is a state,
    // not a non-event — say so (tests2, 2026-09-03).
    push("assets", "warn", "no ai-eng.lock — governance files were never (re)installed: run ai-eng init");
  }
  // 5. git floor: marker-managed shims in .git/hooks/ + gitleaks present.
  if (root) {
    const hooksDir = join(root, ".git", "hooks");
    const floorHooks = ["pre-commit", "commit-msg", "pre-push"];
    const wired = floorHooks.every((name) => {
      const p = join(hooksDir, name);
      return existsSync(p) && readFileSync(p, "utf8").includes("ai-eng git floor shim");
    });
    const gitleaks = spawnSync("gitleaks", ["version"], { encoding: "utf8" });
    push("git floor", wired && gitleaks.status === 0 ? "ok" : wired ? "warn" : "fail", wired ? `marker hooks in .git/hooks/ · gitleaks ${gitleaks.status === 0 ? "present" : "MISSING (HARD FAIL)"}` : "marker hooks missing from .git/hooks/ — run ai-eng init");
  }
  // 6. THE REAL TEST: adversarial payload must deny, under the latency ceiling.
  const t0 = Date.now();
  const outcome = runChain(
    { tool_name: "Bash", tool_input: { command: "git commit -n -m x" }, tool_use_id: `doctor-${t0}`, session_id: `doctor-${t0}` },
    "PreToolUse",
    { inProcess: true, stateDir: join(home(), "doctor") },
  );
  const ms = Date.now() - t0;
  push("chain test", outcome.action === "deny" && ms <= CEILING_MS ? "ok" : outcome.action === "deny" ? "warn" : "fail", outcome.action === "deny" ? `adversarial payload (git commit -n) → DENY in ${ms}ms` : `adversarial payload NOT denied (${outcome.action}) in ${ms}ms`);
  // 7. receipts aggregate vs budget.
  const summary = summarizeReceipts();
  push("receipts", summary.p95 <= CEILING_MS ? "ok" : "warn", `${summary.total} runs · ${summary.denies} denies · p50 ${summary.p50}ms · p95 ${summary.p95}ms (ceiling ${CEILING_MS})`);
  // 8. overrides: active → permanent WARN until they expire (§12.1); expired → the
  //    guard is live again but the entry is still dead config, so it is named with
  //    the fix. §14.2 shows the days left; §14.5b wants the action, not just the fact.
  const overrides = readOverrides(root);
  const now = Date.now();
  const described = overrides.map((entry) => {
    const days = overrideDaysLeft(entry, now);
    const label = days === null ? "no expiry — add an until" : days === 0 ? "expires today" : `expires in ${days}d`;
    return { entry, days, label };
  });
  const rows = described
    .filter((d) => d.days === null || d.days >= 0)
    .map((d) => `${d.entry.name} — ${d.entry.reason.slice(0, 40)} (${d.label})`);
  const stale = described
    .filter((d) => d.days !== null && d.days < 0)
    .map((d) => `${d.entry.name} — expired ${String(d.entry.until).slice(0, 10)} → remove it from .ai-engineering/overrides.toml`);
  push(
    "overrides",
    described.length === 0 ? "ok" : "warn",
    described.length === 0 ? "none active" : [...rows, ...stale].join(" · "),
  );
  // 9. arch bootstrap vs active.
  const archPath = root ? join(root, ".ai-engineering", "arch.rules.json") : null;
  const hasSrc = root ? existsSync(join(root, "src")) : false;
  push("arch", !archPath ? "warn" : hasSrc ? "ok" : "warn", !archPath ? "no arch.rules.json" : hasSrc ? "active — src/ present" : "bootstrap mode — src/ empty");
  // 10. spec slot: zombie contracts.
  const specPath = root ? join(root, ".ai-engineering", "spec.html") : null;
  if (specPath && existsSync(specPath)) {
    const lockPath = join(root ?? "", ".ai-engineering", "ai-eng.lock");
    const pinned = existsSync(lockPath) ? Boolean(parseLock(readFileSync(lockPath, "utf8")).spec_sha256) : false;
    push("spec slot", pinned ? "ok" : "warn", pinned ? "contract approved (sha256 in lock)" : "live spec.html WITHOUT approval — STOP 1 pending or zombie contract");
  } else {
    push("spec slot", "ok", "clean slot: 0 zombie contracts");
  }
  // 11. surfaces responding: settings present for declared surfaces — and, where the
  //     surface runs the guard in-process, the planted chain is the one THIS binary
  //     ships. Existence is not the question: a half-written or hand-patched bundle
  //     passes every probe and denies nothing. §14.3 asks the human the patch
  //     question; bytes answer it, so an edited bundle is a WARN with the action,
  //     never a silent pass (measured 2026-09-10: doctor read a stale guard as green).
  if (Array.isArray(surfaces)) {
    const shipped = embeddedChainBundle();
    for (const id of surfaces) {
      const surface = SURFACES.find((s) => s.id === id);
      if (!surface) continue;
      const path = surface.settingsFile ?? surface.pluginFile ?? "";
      const present = root !== null && path.length > 0 && existsSync(join(root, path));
      const chainRel = surface.chainFile ?? "";
      const chainAbs = root !== null && chainRel.length > 0 ? join(root, chainRel) : null;
      let chainDiffers = false;
      if (chainAbs !== null && existsSync(chainAbs)) {
        try {
          chainDiffers = readFileSync(chainAbs, "utf8") !== shipped;
        } catch {
          chainDiffers = true; // unreadable is not the same as matching
        }
      }
      let status: CheckResult["status"] = "ok";
      if (!present) status = id === "claude-code" ? "fail" : "warn";
      else if (chainDiffers) status = "warn";
      const detail = !present
        ? `${path} missing`
        : chainDiffers
          ? `${path} present · ${chainRel} is NOT the chain this binary ships → ai-eng update (if you patched it yourself, update offers the diff — it never overwrites in silence)`
          : `${path} present${chainRel.length > 0 ? ` · in-process chain matches the binary` : ""}`;
      push(`surface ${id}`, status, detail);
    }
  }
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
    push("behaviors", bad.length === 0 ? "ok" : "fail", bad.length === 0 ? "frontmatter ok" : bad.join(" · "));
  } else {
    push("behaviors", "ok", "no behaviors declared");
  }
  return { results, fail: results.some((r) => r.status === "fail") };
}

/** `doctor --gc` — execute what the audit proposes, in one commit (§21.3). */
function gc(cwd = process.cwd()): string[] {
  const root = repoRoot(cwd);
  const lines: string[] = [];
  if (!root) return ["no repo: nothing to collect"];
  const config = loadConfig();
  const maxFiles = Number(config["gc"]?.["max_files"] ?? 25);
  const ttlDays = Number(String(config["gc"]?.["receipts_ttl"] ?? "30d").replace("d", ""));
  const folders: Array<[string, number]> = [
    ["research", maxFiles],
    ["reports", maxFiles],
    ["design/audits", maxFiles],
    ["receipts", ttlDays],
  ];
  const cut = Date.now() - ttlDays * 86_400_000;
  for (const [folder, limit] of folders) {
    const dir = join(root, ".ai-engineering", folder);
    if (!existsSync(dir)) continue;
    const entries = readdirSync(dir).sort();
    if (folder === "receipts") {
      // Aggregate then delete: counts per month, p50/p95, denies per guard → summary.json.
      const summary = summarizeReceipts(dir);
      const stale = entries
        .map((name) => ({ name, ts: statMtime(join(dir, name)) }))
        .filter((e) => e.ts < cut);
      for (const entry of stale) unlinkSync(join(dir, entry.name));
      if (stale.length > 0) {
        writeFileSync(join(dir, "summary.json"), JSON.stringify({ ...summary, gc: new Date().toISOString() }));
        lines.push(`✓ receipts: ${stale.length} aggregated into summary.json and deleted (ttl ${ttlDays}d)`);
      }
      continue;
    }
    if (entries.length > limit) {
      lines.push(`⚠ ${folder}/: ${entries.length} > max_files=${limit} — review citations before gc (cited items are immune)`);
    }
  }
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
  const toRow = (r: CheckResult): ui.Row => ({ mark: r.status === "ok" ? "ok" : r.status === "warn" ? "warn" : "fail", text: `${r.name} · ${r.detail}` });
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
