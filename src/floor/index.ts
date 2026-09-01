// The git floor: what the 3-line shims call. Independent of every agent surface —
// this runs even for a person committing from Vim (§13.2). gitleaks missing is HARD
// FAIL, never silent degradation.

import { execFileSync, spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { repoRoot } from "../env.ts";

type FloorResult = { ok: boolean; lines: string[] };

function git(args: string[], cwd: string): { code: number; out: string } {
  const done = spawnSync("git", args, { cwd, encoding: "utf8" });
  return { code: done.status ?? 1, out: `${done.stdout ?? ""}${done.stderr ?? ""}` };
}

/** pre-commit: diff --check · gitleaks --staged · DECISIONS.md if >10 files or new dep. */
export function preCommit(cwd = repoRoot() ?? process.cwd()): FloorResult {
  const lines: string[] = [];
  const check = git(["diff", "--cached", "--check"], cwd);
  if (check.code !== 0) {
    lines.push("diff --check encontró problemas de whitespace:");
    lines.push(check.out.trim());
    return { ok: false, lines };
  }
  const leaks = stageSecrets(cwd);
  if (!leaks.ok) return { ok: false, lines: [...lines, ...leaks.lines] };
  lines.push(...leaks.lines);
  const decisions = decisionsBlock(cwd);
  if (!decisions.ok) return { ok: false, lines: [...lines, ...decisions.lines] };
  if (decisions.lines.length > 0) lines.push(...decisions.lines);
  return { ok: true, lines };
}

function whichGitleaks(): string | null {
  for (const candidate of ["/opt/homebrew/bin/gitleaks", "/usr/local/bin/gitleaks", "/usr/bin/gitleaks"]) {
    if (existsSync(candidate)) return candidate;
  }
  const probe = spawnSync("gitleaks", ["version"], { encoding: "utf8" });
  return probe.status === 0 ? "gitleaks" : null;
}

/** >10 files touched or a dependency changed → a DECISIONS.md block is required. */
function decisionsBlock(cwd: string): FloorResult {
  const nameOnly = git(["diff", "--cached", "--name-only"], cwd).out.trim();
  const files = nameOnly ? nameOnly.split("\n").filter((f) => f.length > 0) : [];
  const dependencyTouched = files.some((f) => /^(package\.json|Cargo\.toml|go\.mod|pyproject\.toml|Gemfile|composer\.json|pom\.xml|Package\.swift|.*\.csproj)$/.test(f));
  if (files.length <= 10 && !dependencyTouched) return { ok: true, lines: [] };
  const decisionsPath = join(cwd, "DECISIONS.md");
  if (!existsSync(decisionsPath)) {
    return { ok: false, lines: [`este commit toca ${files.length} archivos${dependencyTouched ? " (o una dependencia)" : ""} y exige un bloque en DECISIONS.md (§9.2) — no existe.`] };
  }
  const content = readFileSync(decisionsPath, "utf8");
  const blocks = content.split(/^## /m).length - 1;
  if (blocks === 0) {
    return { ok: false, lines: ["DECISIONS.md existe pero no lleva ningún bloque ## D-NNN — añade uno (≤6 líneas) o reduce el commit."] };
  }
  return { ok: true, lines: [] };
}

function stageSecrets(cwd: string): FloorResult {
  const gitleaks = whichGitleaks();
  if (!gitleaks) {
    return {
      ok: false,
      lines: ["gitleaks no está instalado — HARD FAIL, no degradación silenciosa (§12.1).", "Instálalo: brew install gitleaks"],
    };
  }
  // v1's proven invocation: `gitleaks dir` — `git --staged` in 8.30 scans 0 commits
  // on a fresh HEAD and silently passes. We scan the files actually staged.
  const staged = git(["diff", "--cached", "--name-only", "--diff-filter=ACM"], cwd).out
    .split("\n")
    .map((f) => f.trim())
    .filter((f) => f.length > 0);
  if (staged.length === 0) return { ok: true, lines: [] };
  const present = staged.filter((f) => existsSync(join(cwd, f)));
  if (present.length === 0) return { ok: true, lines: [] };
  try {
    const args = ["dir", "--redact", "--no-banner", "--exit-code", "1", ...present];
    execFileSync(gitleaks, args, { cwd, stdio: "pipe" });
    return { ok: true, lines: [] };
  } catch (error) {
    const e = error as { stdout?: unknown; stderr?: unknown; message?: string };
    const asText = (v: unknown): string => (Buffer.isBuffer(v) ? v.toString() : typeof v === "string" ? v : "");
    const out = `${asText(e.stdout)}\n${asText(e.stderr)}`.trim() || (e.message ?? "");
    const findings = out
      .split("\n")
      .filter((l) => l.startsWith("File:") || l.startsWith("RuleID:") || l.startsWith("Finding:"))
      .slice(0, 10)
      .join("\n");
    return { ok: false, lines: ["gitleaks: secreto en lo staged → BLOQUEADO.", findings || out.slice(0, 800)] };
  }
}
/** commit-msg: convention + Receipt-Id trailer + override reason when active. */
export function commitMsg(msgFile: string, receiptId: string, overrideReason: string | null): FloorResult {
  const lines: string[] = [];
  let content: string;
  try {
    content = readFileSync(msgFile, "utf8");
  } catch {
    return { ok: false, lines: ["commit-msg: no puedo leer el mensaje del commit."] };
  }
  const first = content.split("\n")[0] ?? "";
  if (!/^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9._/-]+\))?!?: \S/.test(first)) {
    return {
      ok: false,
      lines: [`el mensaje no sigue la convención Conventional Commits: "${first.slice(0, 72)}"`, "Formato: tipo(ámbito): descripción"],
    };
  }
  if (!content.includes("Receipt-Id:")) {
    content = `${content.trimEnd()}\n\nReceipt-Id: ${receiptId}\n`;
    if (overrideReason) content = `${content.trimEnd()}\nOverride-Reason: ${overrideReason}\n`;
    const { writeFileSync } = require("node:fs") as typeof import("node:fs");
    writeFileSync(msgFile, content);
    if (overrideReason) lines.push(`override activo viaja en el commit: ${overrideReason.slice(0, 80)}`);
  }
  return { ok: true, lines };
}

/** pre-push: gitleaks over the whole unpushed surface + expiry of dated overrides. */
export function prePush(cwd = repoRoot() ?? process.cwd()): FloorResult {
  const lines: string[] = [];
  const gitleaks = whichGitleaks();
  if (!gitleaks) {
    return { ok: false, lines: ["gitleaks no está instalado — HARD FAIL (§12.1). brew install gitleaks"] };
  }
  try {
    execFileSync(gitleaks, ["git", "--redact", "-v"], { cwd, stdio: "pipe" });
  } catch (error) {
    const out = (error as { stdout?: string }).stdout ?? "";
    return { ok: false, lines: ["gitleaks en pre-push: secreto en el histórico no pusheado → BLOQUEADO.", out.toString().slice(0, 2000)] };
  }
  return { ok: true, lines };
}
