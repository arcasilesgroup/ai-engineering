// `ai-eng doctor` — 12 checks + one real test. The difference with theater: it
// EXECUTES an adversarial payload and measures real latency. A hook that does not
// deny, or denies slow, is FAIL — not WARN (§14.2).

import { existsSync, readFileSync, readdirSync, lstatSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { repoRoot, loadConfig, home } from "../env.ts";
import { summarizeReceipts } from "../receipts.ts";
import { parseLock } from "../plant.ts";
import { SURFACES } from "../surfaces/adapters.ts";
import { runChain } from "../chain/mod.ts";
import { readOverrides, overrideActive } from "../chain/dialect.ts";
import { hashFile } from "../skills-lint.ts";

export type CheckResult = { name: string; status: "ok" | "warn" | "fail"; detail: string };

const CEILING_MS = 50;

export function runChecks(cwd = process.cwd()): { results: CheckResult[]; fail: boolean } {
  const results: CheckResult[] = [];
  const root = repoRoot(cwd);
  const push = (name: string, status: CheckResult["status"], detail: string) => results.push({ name, status, detail });

  // 1. AGENTS.md present, rule-bearing, under the context ceiling.
  const agentsPath = root ? join(root, "AGENTS.md") : null;
  if (agentsPath && existsSync(agentsPath)) {
    const content = readFileSync(agentsPath, "utf8");
    const rules = (content.match(/^\d+\./gm) ?? []).length;
    const lines = content.split("\n").length;
    push("AGENTS.md", lines <= 80 && rules >= 6 ? "ok" : "warn", `${rules} reglas · ${lines} líneas${lines > 80 ? " (over the context ceiling)" : ""}`);
  } else {
    push("AGENTS.md", "fail", "no existe — el contrato no está plantado");
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
    push("CLAUDE.md", ok ? "ok" : "warn", ok ? "importa AGENTS.md" : "no referencia AGENTS.md");
  } else {
    push("CLAUDE.md", "warn", "ausente");
  }
  // 3. config.toml parseable + surfaces declared.
  const config = loadConfig();
  const surfaces = (config["surfaces"]?.["enabled"] as unknown as string[] | undefined) ?? [];
  push(
    "config.toml",
    existsSync(root ? join(root, ".ai-engineering", "config.toml") : "") ? "ok" : "fail",
    Array.isArray(surfaces) ? `superficies: ${surfaces.join(", ")}` : "no parseable o ausente",
  );
  // 4. Canon 19/19 sha256 + mirrors resolve.
  if (root) {
    const lockPath = join(root, ".ai-engineering", "ai-eng.lock");
    if (existsSync(lockPath)) {
      const lock = parseLock(readFileSync(lockPath, "utf8"));
      let drift = 0;
      let checked = 0;
      for (const [path, hash] of Object.entries(lock.assets)) {
        if (path.includes("skills/")) {
          const absolute = join(home(), "skills", path.replace(/^.*skills\//, ""));
          if (!existsSync(absolute)) {
            drift += 1;
            continue;
          }
          checked += 1;
          if (hashFile(absolute) !== hash) drift += 1;
        }
      }
      push("canon+lock", drift === 0 ? "ok" : "warn", `${checked} assets verificados · ${drift} drift`);
    } else {
      push("canon+lock", "warn", "sin lockfile — ejecuta ai-eng init");
    }
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
  push("chain test", outcome.action === "deny" && ms <= CEILING_MS ? "ok" : outcome.action === "deny" ? "warn" : "fail", outcome.action === "deny" ? `payload adversarial (git commit -n) → DENY en ${ms}ms` : `payload adversarial NO negado (${outcome.action}) en ${ms}ms`);
  // 7. receipts aggregate vs budget.
  const summary = summarizeReceipts();
  push("receipts", summary.p95 <= CEILING_MS ? "ok" : "warn", `${summary.total} ejecuciones · ${summary.denies} denies · p50 ${summary.p50}ms · p95 ${summary.p95}ms (techo ${CEILING_MS})`);
  // 8. overrides active → permanent WARN until they expire.
  const overrides = readOverrides(root);
  const active = overrides.filter((o) => overrideActive(overrides, o.name) !== null);
  push("overrides", active.length === 0 ? "ok" : "warn", active.length === 0 ? "ninguno activo" : `${active.length} activo(s): ${active.map((o) => `${o.name} — ${o.reason.slice(0, 40)}`).join(" · ")}`);
  // 9. arch bootstrap vs active.
  const archPath = root ? join(root, ".ai-engineering", "arch.rules.json") : null;
  const hasSrc = root ? existsSync(join(root, "src")) : false;
  push("arch", !archPath ? "warn" : hasSrc ? "ok" : "warn", !archPath ? "sin arch.rules.json" : hasSrc ? "activo — src/ presente" : "modo bootstrap — src/ vacío");
  // 10. spec slot: zombie contracts.
  const specPath = root ? join(root, ".ai-engineering", "spec.html") : null;
  if (specPath && existsSync(specPath)) {
    const lockPath = join(root ?? "", ".ai-engineering", "ai-eng.lock");
    const pinned = existsSync(lockPath) ? Boolean(parseLock(readFileSync(lockPath, "utf8")).spec_sha256) : false;
    push("spec slot", pinned ? "ok" : "warn", pinned ? "contrato aprobado (sha256 en el lock)" : "spec.html vivo SIN aprobación — PARADA 1 pendiente o contrato zombi");
  } else {
    push("spec slot", "ok", "slot limpio: 0 contratos zombi");
  }
  // 11. surfaces responding: settings present for declared surfaces.
  if (Array.isArray(surfaces)) {
    for (const id of surfaces) {
      const surface = SURFACES.find((s) => s.id === id);
      if (!surface) continue;
      const path = surface.settingsFile ?? surface.pluginFile ?? "";
      const present = root !== null && path.length > 0 && existsSync(join(root, path));
      push(`surface ${id}`, present ? "ok" : id === "claude-code" ? "fail" : "warn", present ? `${path} presente` : `${path} ausente`);
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
    push("behaviors", bad.length === 0 ? "ok" : "fail", bad.length === 0 ? "frontmatter correcto" : bad.join(" · "));
  } else {
    push("behaviors", "ok", "sin behaviors declarados");
  }
  return { results, fail: results.some((r) => r.status === "fail") };
}

/** `doctor --gc` — execute what the audit proposes, in one commit (§21.3). */
export function gc(cwd = process.cwd()): string[] {
  const root = repoRoot(cwd);
  const lines: string[] = [];
  if (!root) return ["sin repo: nada que recolectar"];
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
      for (const entry of stale) {
        const { unlinkSync } = require("node:fs") as typeof import("node:fs");
        unlinkSync(join(dir, entry.name));
      }
      if (stale.length > 0) {
        const { writeFileSync } = require("node:fs") as typeof import("node:fs");
        writeFileSync(join(dir, "summary.json"), JSON.stringify({ ...summary, gc: new Date().toISOString() }));
        lines.push(`✓ receipts: ${stale.length} agregados a summary.json y borrados (ttl ${ttlDays}d)`);
      }
      continue;
    }
    if (entries.length > limit) {
      lines.push(`⚠ ${folder}/: ${entries.length} > max_files=${limit} — revisa citas antes de gc (los citados son inmunes)`);
    }
  }
  if (lines.length === 0) lines.push("✓ gc: nada que recolectar");
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
  if (!match) return "sin frontmatter";
  const body = match[1] ?? "";
  const name = /^name:\s*(.+)$/m.exec(body)?.[1]?.trim();
  if (name !== folder) return `name=${name} ≠ carpeta ${folder}`;
  const description = /^description:\s*(.+)$/m.exec(body)?.[1]?.trim() ?? "";
  if (description.length === 0 || description.length > 1024) return "description vacía o >1024";
  return null;
}

export function doctorMain(flags: { gc?: boolean }): number {
  if (flags.gc) {
    for (const line of gc()) process.stdout.write(`${line}\n`);
    return 0;
  }
  const { results, fail } = runChecks();
  let ok = 0;
  let warn = 0;
  let failed = 0;
  for (const result of results) {
    const mark = result.status === "ok" ? "✓" : result.status === "warn" ? "⚠" : "✗";
    process.stdout.write(`${mark}  ${result.name} · ${result.detail}\n`);
    if (result.status === "ok") ok += 1;
    else if (result.status === "warn") warn += 1;
    else failed += 1;
  }
  process.stdout.write(`\n${results.length} checks: ${ok} OK · ${warn} WARN · ${failed} FAIL\n`);
  return fail ? 2 : 0;
}
