// `ai-eng spec run|open|approve|close` — the machine verb the CI and the loop call.
// run: wrapper over ai-proof's gate-check.mjs + receipt per run + exit ≠ 0 when a
// CHECK could not execute (green-by-absence-of-executor is impossible, §09.3).
// open: claims the slot and records the commit the milestone starts from, which is
// what gives the conditional nodes a diff to judge. close: verifies every gate has
// evidence or an honest ABANDON, checks the contract was not edited after approval,
// refuses when a fired trigger left no artifact, archives to git and frees the slot
// (§21.2).

import { existsSync, readFileSync, writeFileSync, unlinkSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { repoRoot, home } from "../env.ts";
import { writeReceipt } from "../receipts.ts";
import { embeddedTemplate } from "../embed.ts";
import { parseLock, lockText } from "../install.ts";
import { unmetTriggers } from "./triggers.ts";
import { VERSION } from "../version.ts";

const SLOT_FILES = ["spec.html", "plan.html", "brainstorm.md", "recap.html"];
/** An ABANDON with less than this much reason is a checkbox, not an honest exit. */
const MIN_ABANDON_REASON = 12;

/** The commit the milestone starts from — the base every conditional node is judged against. */
function gitHead(root: string): string | null {
  const head = spawnSync("git", ["-C", root, "rev-parse", "HEAD"], { encoding: "utf8" });
  const sha = head.stdout.trim();
  return head.status === 0 && /^[0-9a-f]{40}$/.test(sha) ? sha : null;
}

type GateLine = { id: string; evidence: string | null };

/** The gates as the artifact really writes them: `- [ ] G4: ...` inside `<pre id="gates">`
 *  with an indented EVIDENCE line. The old regex looked for `<div class="gate">`, markup no
 *  spec.html has ever contained — so the check ran against zero gates and never refused. */
function parseGates(spec: string): GateLine[] {
  const block = /<pre id="gates">([\s\S]*?)<\/pre>/.exec(spec)?.[1] ?? spec;
  const gates: GateLine[] = [];
  for (const line of block.split("\n")) {
    const gate = /^- \[[ xX]\] (G\d+):/.exec(line);
    if (gate) {
      gates.push({ id: gate[1]!, evidence: null });
      continue;
    }
    const evidence = /^\s+EVIDENCE:\s*(.*)$/.exec(line);
    const current = gates[gates.length - 1];
    if (evidence && current && current.evidence === null) current.evidence = evidence[1]!.trim();
  }
  return gates;
}

/** Every `ABANDON: <id> <reason>` in the artifact, by id. The id is a gate or a trigger. */
function abandons(spec: string): Array<{ id: string; reason: string }> {
  return [...spec.matchAll(/^ABANDON:\s*(\S+)[ \t]*(.*)$/gm)].map((m) => ({ id: m[1]!, reason: (m[2] ?? "").trim() }));
}

/** The contract the human approved is the WHAT, not the bookkeeping: `ai-eng spec run`
 *  ticks the boxes and fills the EVIDENCE lines in the very file whose sha256 was
 *  pinned at approval. Comparing raw bytes meant the act of running the gates broke
 *  the authorisation that allowed the run. Both fields are normalised away, so an
 *  edit to a check or a requirement still breaks the pin and a recorded receipt does
 *  not — and a spec pinned before this change stays valid, because a pristine
 *  contract and its normalised form are the same bytes. */
export function normalizeSpec(spec: string): string {
  return spec.replace(/^- \[[xX]\]/gm, "- [ ]").replace(/^(\s+EVIDENCE:\s*).*$/gm, "$1pending");
}

function sha256(text: string): string {
  return createHash("sha256").update(text).digest("hex");
}

function specGatePolicyAllowsRun(root: string): boolean {
  // A contract nobody approved does not run: the sha256 pinned in the lock at
  // STOP 1 is what makes the contract executable (H6 criterion).
  const lockPath = join(root, ".ai-engineering", "ai-eng.lock");
  if (!existsSync(lockPath)) return false;
  const lock = parseLock(readFileSync(lockPath, "utf8"));
  if (!lock.spec_sha256) return false;
  const specPath = join(root, ".ai-engineering", "spec.html");
  if (!existsSync(specPath)) return false;
  return sha256(normalizeSpec(readFileSync(specPath, "utf8"))) === lock.spec_sha256;
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
  if (!script) {
    // A check that cannot run is red, never green by absence of executor (§09.3).
    process.stderr.write("spec run: gate-check.mjs not found (canon missing) — run ai-eng init, then retry.\n");
    return 2;
  }
  const runner = existsSync("/usr/bin/env") ? "bun" : "node"; // mjs needs a JS runtime, not ourselves
  const done = spawnSync(runner, [script, specPath], { cwd: root, encoding: "utf8", stdio: "inherit" });
  const code = done.status ?? 1;
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
  writeFileSync(join(dir, "spec.html"), embeddedTemplate("spec.html.tpl", { milestone }));
  writeFileSync(join(dir, "plan.html"), embeddedTemplate("plan.html.tpl", { milestone }));
  // The milestone's base: the conditional nodes judge `git diff --name-only <base>`
  // against it, and nothing else records where the work began.
  const base = gitHead(root);
  const lockPath = join(dir, "ai-eng.lock");
  if (base) {
    const lock = existsSync(lockPath) ? parseLock(readFileSync(lockPath, "utf8")) : { version: VERSION, assets: {} };
    lock.base_sha = base;
    writeFileSync(lockPath, lockText(lock));
  }
  process.stdout.write(`✓ slot opened: spec.html + plan.html for "${milestone}"\n`);
  if (base) process.stdout.write(`  base ${base.slice(0, 12)} recorded — fired triggers are judged against it\n`);
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
  const sha = sha256(normalizeSpec(readFileSync(specPath, "utf8")));
  lock.spec_sha256 = sha;
  writeFileSync(lockPath, lockText(lock));
  process.stdout.write(`✓ STOP 1: spec sha256 pinned in ai-eng.lock (${sha.slice(0, 12)}…) — the contract is executable and self-protect now blocks its edits.\n`);
  return 0;
}

/** `spec close` — the only exit: receipts or ABANDON per gate, no post-approval edits,
 *  no fired trigger left without an artifact. Then archive, delete, free the slot (§21.2). */
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
  const lockPath = join(dir, "ai-eng.lock");
  const lock = existsSync(lockPath) ? parseLock(readFileSync(lockPath, "utf8")) : { version: VERSION, assets: {} };
  const problems: string[] = [];

  // The contract the human approved is the one that closes: an edited spec is a
  // different contract, however small the edit.
  if (lock.spec_sha256 && sha256(normalizeSpec(spec)) !== lock.spec_sha256) {
    problems.push(
      "spec close: spec.html changed after approval (sha256 differs from the lock) — restore it from git, or reopen with ai-eng spec open and approve again.",
    );
  }

  const declared = abandons(spec);
  const abandoned = new Set(declared.map((entry) => entry.id));
  for (const entry of declared) {
    if (entry.reason.length < MIN_ABANDON_REASON) {
      problems.push(`spec close: ABANDON: ${entry.id} carries no reason — an honest exit says what it is exiting.`);
    }
  }

  const gates = parseGates(spec);
  if (gates.length === 0) {
    problems.push("spec close: no gates found in spec.html — a contract with nothing to verify is not a contract.");
  }
  const unmet = gates.filter((gate) => {
    if (abandoned.has(gate.id)) return false;
    const evidence = gate.evidence?.trim() ?? "";
    return evidence.length === 0 || /^pending$/i.test(evidence);
  });
  if (unmet.length > 0) {
    const ids = unmet.map((gate) => gate.id).join(", ");
    problems.push(
      `spec close: ${unmet.length} gate(s) without evidence or ABANDON (${ids}) — run ai-eng spec run, or declare ABANDON: <gate> <reason>.`,
    );
  }
  if (abandoned.size > 0) {
    for (const entry of declared) process.stdout.write(`  ABANDON: ${entry.id} — ${entry.reason}\n`);
  }

  // A conditional node that fired and left nothing is the "if it touches UI" sentence
  // that used to be unenforceable.
  if (lock.base_sha && gates.length > 0) {
    for (const unmetTrigger of unmetTriggers(root, lock.base_sha, abandoned)) {
      problems.push(
        `spec close: trigger "${unmetTrigger.id}" fired on ${unmetTrigger.sample} and ${unmetTrigger.skill} left no artifact — run it, or declare ABANDON: ${unmetTrigger.id} <reason>.`,
      );
    }
  }

  if (problems.length > 0) {
    for (const problem of problems) process.stderr.write(`${problem}\n`);
    return 2;
  }

  // Archive = git add of the four files happens by the caller's commit; here we
  // delete the slot files after recording what dies.
  for (const name of SLOT_FILES) {
    const path = join(dir, name);
    if (existsSync(path)) unlinkSync(path);
  }
  // The lock entries die with the milestone; the next contract takes their place.
  if (existsSync(lockPath)) {
    const clean = parseLock(readFileSync(lockPath, "utf8"));
    delete clean.spec_sha256;
    delete clean.base_sha;
    writeFileSync(lockPath, lockText(clean));
  }
  process.stdout.write(
    `✓ contract closed: ${gates.length} gate(s) verified, spec/plan/brainstorm/recap dead from the tree — git keeps the history.\n`,
  );
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
