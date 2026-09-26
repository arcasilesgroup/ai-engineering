// `ai-eng spec open|approve|close` — the slot verbs.
// open: claims the slot and records the commit the milestone starts from, which is
// what gives the conditional nodes a diff to judge. close: verifies every gate has
// evidence or an honest ABANDON, checks the contract was not edited after approval,
// refuses when a fired trigger left no artifact, archives to git and frees the slot
// (§21.2). The feature cycle does not execute spec.html; checkpoints do that work.

import { existsSync, readFileSync, writeFileSync, unlinkSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { repoRoot, isGoverned } from "../env.ts";
import { embeddedTemplate } from "../embed.ts";
import { parseLock, lockText } from "../install.ts";
import { unmetTriggers } from "./triggers.ts";
import { VERSION } from "../version.ts";

/** The four artifacts of a milestone. `spec open` scaffolds two, `spec close` sweeps
 *  all four — the guard's fence leaves them to the session, so this verb is their
 *  only consumer. */
const SLOT_FILES = ["spec.html", "plan.html", "brainstorm.html", "recap.html"] as const;

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
 *  with an indented EVIDENCE line. Markup no spec.html contains: a `<div class="gate">`
 *  regex matches zero gates and never refuses. */
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

/** The contract the human approved is the WHAT, not the bookkeeping. Ticked boxes
 *  and EVIDENCE lines land in the same file whose sha256 was pinned at approval.
 *  Comparing raw bytes meant recording evidence broke that approval. Both fields
 *  are normalised away, so an edit to a check or a requirement still breaks the pin
 *  and a recorded receipt does not — and a spec pinned over its pristine form stays
 *  valid, because a pristine contract and its normalised form are the same bytes. */
export function normalizeSpec(spec: string): string {
  return spec.replace(/^- \[[xX]\]/gm, "- [ ]").replace(/^(\s+EVIDENCE:\s*).*$/gm, "$1pending");
}

function sha256(text: string): string {
  return createHash("sha256").update(text).digest("hex");
}

/** `spec open <milestone>` — claim the slot; refuse when a live contract exists (§21.2). */
export function specOpen(milestone: string): number {
  const root = repoRoot();
  if (root === null || !isGoverned(root)) {
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
  if (root === null || !isGoverned(root)) return 2;
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
  process.stdout.write(`✓ STOP 1: spec sha256 pinned in ai-eng.lock (${sha.slice(0, 12)}…) — the contract is pinned and self-protect now blocks its edits.\n`);
  return 0;
}

/** `spec close` — the only exit: receipts or ABANDON per gate, no post-approval edits,
 *  no fired trigger left without an artifact. Then archive, delete, free the slot (§21.2). */
export function specClose(): number {
  const root = repoRoot();
  if (root === null || !isGoverned(root)) return 2;
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
      `spec close: ${unmet.length} gate(s) without evidence or ABANDON (${ids}) — write the evidence, or declare ABANDON: <gate> <reason>.`,
    );
  }
  if (abandoned.size > 0) {
    for (const entry of declared) process.stdout.write(`  ABANDON: ${entry.id} — ${entry.reason}\n`);
  }

  // A conditional node that fired and left nothing is the "if it touches UI" sentence
  // made enforceable.
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
  if (sub === "run") {
    process.stderr.write("spec run: retired. The feature cycle is ai-research, ai-brainstorm, ai-orchestrator. spec open, approve and close remain.\n");
    return 2;
  }
  if (sub === "open") {
    const milestone = args.slice(1).join(" ") || "unnamed-milestone";
    return specOpen(milestone);
  }
  if (sub === "approve") return specApprove();
  if (sub === "close") return specClose();
  process.stderr.write("usage: ai-eng spec open|approve|close\n");
  return 2;
}
