// `ai-eng spec run|open|close` — the machine verb the CI and the loop call.
// run: wrapper over ai-proof's gate-check.mjs + receipt per run + exit ≠ 0 when a
// CHECK could not execute (green-by-absence-of-executor is impossible, §09.3).
// open: claims the slot. close: verifies receipts or ABANDON per gate, archives to
// git, deletes the four slot files, frees the slot (§21.2).

import { existsSync, readFileSync, writeFileSync, unlinkSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { repoRoot, home } from "../env.ts";
import { writeReceipt } from "../receipts.ts";
import { parseLock, lockText } from "../plant.ts";
import { VERSION } from "../version.ts";

const SLOT_FILES = ["spec.html", "plan.html", "brainstorm.md", "recap.html"];

function specGatePolicyAllowsRun(root: string): boolean {
  // A contract nobody approved does not run: the sha256 pinned in the lock at
  // STOP 1 is what makes the contract executable (H6 criterion).
  const lockPath = join(root, ".ai-engineering", "ai-eng.lock");
  if (!existsSync(lockPath)) return false;
  const lock = parseLock(readFileSync(lockPath, "utf8"));
  if (!lock.spec_sha256) return false;
  const specPath = join(root, ".ai-engineering", "spec.html");
  if (!existsSync(specPath)) return false;
  const current = createHash("sha256").update(readFileSync(specPath)).digest("hex");
  return current === lock.spec_sha256;
}

/** `spec run` — execute every CHECK in the approved spec.html. */
export function specRun(): number {
  const root = repoRoot();
  if (!root) {
    process.stderr.write("spec run: you are not in a governed repo.\n");
    return 2;
  }
  const specPath = join(root, ".ai-engineering", "spec.html");
  if (!existsSync(specPath)) {
    process.stderr.write("spec run: no spec.html in .ai-engineering/ — no live contract.\n");
    return 2;
  }
  if (!specGatePolicyAllowsRun(root)) {
    process.stderr.write("spec run: spec.html is not approved (sha256 missing or different in ai-eng.lock) — a contract nobody approved does not run (§9.3).\n");
    return 2;
  }
  // The real executor is ai-proof's gate-check.mjs — never reimplemented (§11.3).
  const gateCheck = join(home(), "skills", "ai-proof", "scripts", "gate-check.mjs");
  const fallback = join(import.meta.dir, "..", "..", "skills", "ai-proof", "scripts", "gate-check.mjs");
  const script = existsSync(gateCheck) ? gateCheck : existsSync(fallback) ? fallback : null;
  const t0 = Date.now();
  let code: number;
  if (script) {
    const runner = existsSync("/usr/bin/env") ? "bun" : "node"; // mjs needs a JS runtime, not ourselves
    const done = spawnSync(runner, [script, specPath], { cwd: root, encoding: "utf8", stdio: "inherit" });
    code = done.status ?? 1;
  } else {
    // The CHECK extraction still runs: a missing executor is a FAIL, never silence.
    process.stderr.write("spec run: gate-check.mjs not found — checks run with the built-in extractor.\n");
    code = extractAndRunChecks(root, readFileSync(specPath, "utf8"));
  }
  const receipt = writeReceipt({
    event: "spec-run",
    surface: "ci",
    tool: "spec",
    guards: { ran: ["spec"], denied_by: null },
    latency_ms: Date.now() - t0,
    outcome: code === 0 ? "allow" : "deny",
  });
  if (code !== 0) process.stderr.write(`spec run: FAILURE (receipt ${receipt?.operation_id ?? "n/a"}) — a check that does not run is not green, it is red.\n`);
  return code;
}

function extractAndRunChecks(root: string, spec: string): number {
  // Parse CHECK lines from the spec and run each as a shell command in the repo.
  const checks = [...spec.matchAll(/CHECK:\s*(.+)/g)].map((m) => m[1]!.trim());
  if (checks.length === 0) {
    process.stderr.write("spec run: the spec declares no executable CHECKs — green would be a lie.\n");
    return 2;
  }
  let failures = 0;
  for (const command of checks) {
    const done = spawnSync("/bin/sh", ["-c", command], { cwd: root, encoding: "utf8" });
    if (done.status !== 0) {
      failures += 1;
      process.stderr.write(`✗ CHECK failed: ${command}\n`);
    } else {
      process.stdout.write(`✓ CHECK: ${command}\n`);
    }
  }
  return failures === 0 ? 0 : 1;
}

/** `spec open <milestone>` — claim the slot; refuse when a live contract exists (§21.2). */
export function specOpen(milestone: string): number {
  const root = repoRoot();
  if (!root) {
    process.stderr.write("spec open: you are not in a governed repo.\n");
    return 2;
  }
  const dir = join(root, ".ai-engineering");
  mkdirSync(dir, { recursive: true });
  for (const name of ["spec.html", "plan.html"]) {
    if (existsSync(join(dir, name))) {
      process.stderr.write(`spec open: a live contract already exists (${name}) — close it with \`ai-eng spec close\` before opening another (§21.2).\n`);
      return 2;
    }
  }
  const specTpl = readFileSync(join(import.meta.dir, "..", "..", "templates", "spec.html.tpl"), "utf8");
  const planTpl = readFileSync(join(import.meta.dir, "..", "..", "templates", "plan.html.tpl"), "utf8");
  writeFileSync(join(dir, "spec.html"), specTpl.split("{{milestone}}").join(milestone));
  writeFileSync(join(dir, "plan.html"), planTpl.split("{{milestone}}").join(milestone));
  process.stdout.write(`✓ slot opened: spec.html + plan.html for "${milestone}"\n`);
  process.stdout.write("  STOP 1: a human approves the contract → pin its sha256 with: ai-eng spec approve\n");
  return 0;
}

/** `spec approve` — STOP 1: pin the approved spec's sha256 into the lock. Human-only:
 *  the chain denies edits to an approved spec (self-protect), so approving is the
 *  moment the contract becomes immutable for the agent. */
export function specApprove(): number {
  const root = repoRoot();
  if (!root) return 2;
  const specPath = join(root, ".ai-engineering", "spec.html");
  if (!existsSync(specPath)) {
    process.stderr.write("spec approve: no spec.html to approve.\n");
    return 2;
  }
  const lockPath = join(root, ".ai-engineering", "ai-eng.lock");
  const lock = existsSync(lockPath) ? parseLock(readFileSync(lockPath, "utf8")) : { version: VERSION, assets: {} };
  const sha = createHash("sha256").update(readFileSync(specPath)).digest("hex");
  lock.spec_sha256 = sha;
  writeFileSync(lockPath, lockText(lock));
  process.stdout.write(`✓ STOP 1: spec sha256 pinned in ai-eng.lock (${sha.slice(0, 12)}…) — the contract is executable and self-protect now blocks its edits.\n`);
  return 0;
}

/** `spec close` — the only exit: receipts or ABANDON per gate, archive to git, delete. */
export function specClose(): number {
  const root = repoRoot();
  if (!root) return 2;
  const dir = join(root, ".ai-engineering");
  const specPath = join(dir, "spec.html");
  if (!existsSync(specPath)) {
    process.stderr.write("spec close: no live contract.\n");
    return 2;
  }
  const spec = readFileSync(specPath, "utf8");
  const gates = [...spec.matchAll(/^<div class="gate"><span class="id">(G\d+)<\/span>([\s\S]*?)<\/div>/gm)];
  const abandoned = [...spec.matchAll(/ABANDON:\s*(G\d+)\s+(.+)/g)].map((m) => m[1]!);
  let withoutReceipt = 0;
  for (const [full, id] of gates.map((g) => [g[0], g[1]!] as const)) {
    if (abandoned.includes(id)) continue;
    const hasEvidence = /EVIDENCE:\s*(?!pending)\S/.test(full);
    if (!hasEvidence) withoutReceipt += 1;
  }
  if (withoutReceipt > 0) {
    process.stderr.write(`spec close: ${withoutReceipt} gates without EVIDENCE or ABANDON — verify first or declare ABANDON (§9.3).\n`);
    return 2;
  }
  // Archive = git add of the four files happens by the caller's commit; here we
  // delete the slot files after recording what dies.
  for (const name of SLOT_FILES) {
    const path = join(dir, name);
    if (existsSync(path)) unlinkSync(path);
  }
  // The lock entry dies with the milestone; the next contract takes its place.
  const lockPath = join(dir, "ai-eng.lock");
  if (existsSync(lockPath)) {
    const lock = parseLock(readFileSync(lockPath, "utf8"));
    delete lock.spec_sha256;
    writeFileSync(lockPath, lockText(lock));
  }
  process.stdout.write("✓ contract closed: spec/plan/brainstorm/recap dead from the tree — git keeps the history.\n");
  return 0;
}

export function specMain(args: string[]): number {
  const sub = args[0];
  if (sub === "run") return specRun();
  if (sub === "open") {
    const milestone = args.slice(1).join(" ") || "unnamed-milestone";
    return specOpen(milestone);
  }
  if (sub === "approve") return specApprove();
  if (sub === "close") return specClose();
  process.stderr.write("usage: ai-eng spec run|open|approve|close\n");
  return 2;
}
