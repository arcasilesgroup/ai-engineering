// `ai-eng spec run|open|approve|close` and the conditional-node evaluator, driven
// in-process against a real repository: the sha256 pinned at approval is what makes a
// contract executable, a gate that cannot run is red, a fired trigger that left no
// artifact blocks the close. The trigger reader decides all of that from the canon's
// own `## Lifecycle` blocks — never from a list in the source.
import { test, expect, beforeEach, afterEach } from "bun:test";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { normalizeSpec, specApprove, specClose, specMain, specOpen, specRun } from "../src/spec/index.ts";
import {
  artifactExists,
  artifactPattern,
  blockFields,
  canonSkillsDir,
  changedFiles,
  lifecycleBlock,
  readTriggers,
  unmetTriggers,
} from "../src/spec/triggers.ts";

let sandbox: string;
let engHome: string;
let repo: string;
let cwd: string;

const specPath = (): string => join(repo, ".ai-engineering", "spec.html");
const lockPath = (): string => join(repo, ".ai-engineering", "ai-eng.lock");
const receiptsPath = (): string => join(repo, ".ai-engineering", "receipts");

function git(args: string[]): { status: number; out: string } {
  const run = spawnSync("git", args, { cwd: repo, encoding: "utf8" });
  return { status: run.status ?? 1, out: `${run.stdout ?? ""}${run.stderr ?? ""}` };
}

/** A conventional message on purpose: the repo is governed, and the git floor judges
 *  commit messages through the globally installed shims. */
function commitAll(message: string): string {
  git(["add", "-A"]);
  git(["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", message]);
  return git(["rev-parse", "HEAD"]).out.trim();
}

/** The verbs write to process.stdout/stderr directly; bun's console holds its own
 *  stream, so patching these two is enough to read back what a verb said. */
function capture(fn: () => number): { code: number; out: string } {
  const chunks: string[] = [];
  const realOut = process.stdout.write.bind(process.stdout);
  const realErr = process.stderr.write.bind(process.stderr);
  const sink = (chunk: unknown): boolean => {
    chunks.push(typeof chunk === "string" ? chunk : String(chunk));
    return true;
  };
  process.stdout.write = sink as typeof process.stdout.write;
  process.stderr.write = sink as typeof process.stderr.write;
  try {
    return { code: fn(), out: chunks.join("") };
  } finally {
    process.stdout.write = realOut;
    process.stderr.write = realErr;
  }
}

const contract = (gates: string): string => `<!DOCTYPE html>\n<html><body>\n<pre id="gates">\n${gates}</pre>\n</body></html>\n`;

/** Writes a contract and returns the sha256 `spec approve` would pin: the normalised
 *  form, so a fixture whose EVIDENCE is already filled is not mistaken for an edit. */
function writeSpec(spec: string): string {
  writeFileSync(specPath(), spec);
  return createHash("sha256").update(normalizeSpec(spec)).digest("hex");
}

function writeLock(fields: { spec_sha256?: string; base_sha?: string }): void {
  const lines = ['version = "2.0.0"', ""];
  if (fields.spec_sha256) lines.push(`spec_sha256 = "${fields.spec_sha256}"`, "");
  if (fields.base_sha) lines.push(`base_sha = "${fields.base_sha}"`, "");
  lines.push("[assets]");
  writeFileSync(lockPath(), `${lines.join("\n")}\n`);
}

function writeSkill(name: string, body: string): void {
  mkdirSync(join(engHome, "skills", name), { recursive: true });
  writeFileSync(join(engHome, "skills", name, "SKILL.md"), body);
}

function specRunReceipts(): Array<Record<string, unknown>> {
  const dir = receiptsPath();
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter((name) => name.includes("spec-run"))
    .map((name) => JSON.parse(readFileSync(join(dir, name), "utf8")) as Record<string, unknown>);
}

const PENDING_GATES = '# Gates: fixture\n\n- [ ] G1: the one thing\n  CHECK: echo "g1 ran"\n  EVIDENCE: pending\n';
const EVIDENCED_GATES = PENDING_GATES.replace("EVIDENCE: pending", "EVIDENCE: exit 0");

/** One conditional node, as the canon declares it: touching a stylesheet fires it. */
const UI_SKILL = [
  "# ai-design",
  "",
  "## Lifecycle",
  "",
  "Lane: full",
  "Trigger: ui",
  "Trigger kind: path",
  "Trigger when: **/*.css",
  "Trigger excludes: docs/**",
  "Writes: .ai-engineering/design/audits/NNN-{name}.html",
  "Read by: the human",
  "Dies: when cited",
  "Next: none",
  "",
].join("\n");

/** A judgment condition: the planner honours it, no machine may. */
const JUDGMENT_SKILL = [
  "# ai-architect",
  "",
  "## Lifecycle",
  "",
  "Lane: full",
  "Trigger: arch-change",
  "Trigger kind: judgment",
  "Trigger when: **/*.css",
  "Writes: .ai-engineering/arch.rules.json",
  "",
].join("\n");

beforeEach(() => {
  cwd = process.cwd();
  sandbox = mkdtempSync(join(tmpdir(), "ai-eng-spec-command-"));
  engHome = join(sandbox, "home");
  repo = join(sandbox, "repo");
  mkdirSync(join(engHome, "skills"), { recursive: true });
  mkdirSync(join(repo, ".ai-engineering"), { recursive: true });
  writeFileSync(join(repo, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n');
  // Own the global git config for this fixture. After `ai-eng update` (and in CI
  // after the check job installs the floor), the developer's init.templateDir
  // points at hook shims that need `ai-eng` + gitleaks on PATH — without this,
  // `git init` inherits those shims and every commit in the fixture fails,
  // which is exactly how G20 went red after update while the earlier `bun test`
  // step stayed green.
  process.env["GIT_CONFIG_GLOBAL"] = join(sandbox, "gitconfig");
  writeFileSync(process.env["GIT_CONFIG_GLOBAL"], "");
  spawnSync("git", ["init", "-q"], { cwd: repo, stdio: "ignore" });
  process.env["AI_ENG_HOME"] = engHome;
  process.chdir(repo);
});

afterEach(() => {
  process.chdir(cwd);
  delete process.env["AI_ENG_HOME"];
  delete process.env["GIT_CONFIG_GLOBAL"];
  rmSync(sandbox, { recursive: true, force: true });
});

test("specMain refuses an unknown verb with usage", () => {
  const usage = capture(() => specMain(["stop"]));
  expect(usage.code).toBe(2);
  expect(usage.out).toBe("usage: ai-eng spec run|open|approve|close\n");
});

test("spec open writes the contract pair, records the base commit and refuses a second slot", () => {
  const head = commitAll("chore: fixture base");
  const opened = capture(() => specMain(["open", "rate limits"]));
  expect(opened.code).toBe(0);
  expect(opened.out).toContain('✓ slot opened: spec.html + plan.html for "rate limits"');
  expect(opened.out).toContain(`  base ${head.slice(0, 12)} recorded — fired triggers are judged against it`);
  expect(opened.out).toContain("  STOP 1: a human approves the contract → pin its sha256 with: ai-eng spec approve");

  const spec = readFileSync(specPath(), "utf8");
  expect(spec).toContain("<title>spec.html — WHAT · rate limits</title>");
  expect(readFileSync(join(repo, ".ai-engineering", "plan.html"), "utf8")).toContain("<title>plan.html — HOW · rate limits</title>");
  expect(readFileSync(lockPath(), "utf8")).toContain(`base_sha = "${head}"`);

  const again = capture(() => specMain(["open", "another milestone"]));
  expect(again.code).toBe(2);
  expect(again.out).toContain("spec open: a live contract already exists (spec.html)");
  expect(readFileSync(specPath(), "utf8")).toBe(spec);
});

test("spec open without a commit records no base and invents no lock", () => {
  const opened = capture(() => specMain(["open"]));
  expect(opened.code).toBe(0);
  expect(opened.out).toContain('for "unnamed-milestone"');
  expect(opened.out).not.toContain("fired triggers are judged against it");
  expect(existsSync(lockPath())).toBe(false);
});

test("every spec verb refuses outside a governed repo", () => {
  process.chdir(sandbox);
  const run = capture(() => specRun());
  expect(run.code).toBe(2);
  expect(run.out).toContain("spec run: you are not in a governed repo.");
  const open = capture(() => specOpen("M1"));
  expect(open.code).toBe(2);
  expect(open.out).toContain("spec open: you are not in a governed repo.");
  expect(capture(() => specApprove()).code).toBe(2);
  expect(capture(() => specClose()).code).toBe(2);

  // A repo that has a root but never declared its surfaces is not governed either.
  process.chdir(repo);
  rmSync(join(repo, ".ai-engineering", "config.toml"));
  const undeclared = capture(() => specMain(["run"]));
  expect(undeclared.code).toBe(2);
  expect(undeclared.out).toContain("you are not in a governed repo.");
});

test("spec approve pins the normalised sha256 of the contract", () => {
  const nothing = capture(() => specApprove());
  expect(nothing.code).toBe(2);
  expect(nothing.out).toContain("spec approve: no spec.html to approve.");

  const sha = writeSpec(contract(PENDING_GATES));
  const approved = capture(() => specMain(["approve"]));
  expect(approved.code).toBe(0);
  expect(approved.out).toContain(`✓ STOP 1: spec sha256 pinned in ai-eng.lock (${sha.slice(0, 12)}…)`);
  expect(readFileSync(lockPath(), "utf8")).toContain(`spec_sha256 = "${sha}"`);
});

test("spec run refuses a contract nobody approved", () => {
  const noContract = capture(() => specRun());
  expect(noContract.code).toBe(2);
  expect(noContract.out).toContain("spec run: no spec.html in .ai-engineering/ — no live contract.");

  writeSpec(contract(PENDING_GATES));
  const noLock = capture(() => specRun());
  expect(noLock.code).toBe(2);
  expect(noLock.out).toContain("spec run: spec.html is not approved (sha256 missing or different in ai-eng.lock)");

  writeLock({ base_sha: "0".repeat(40) }); // a lock that carries no pin
  expect(capture(() => specRun()).code).toBe(2);

  writeLock({ spec_sha256: "0".repeat(64) }); // a pin for a different contract
  expect(capture(() => specRun()).code).toBe(2);

  expect(specRunReceipts()).toEqual([]); // nothing ran, so nothing was recorded
});

test("spec run refuses a contract with nothing to verify", () => {
  writeLock({ spec_sha256: writeSpec(contract("# Gates: fixture\n")) });
  const empty = capture(() => specRun());
  expect(empty.code).toBe(2);
  expect(empty.out).toContain("spec run: no gates found in spec.html — a contract with nothing to verify is not a contract.");
  expect(specRunReceipts()).toEqual([]);
});

test("spec run executes the approved gates, ticks the boxes and records a receipt", () => {
  writeLock({ spec_sha256: writeSpec(contract(PENDING_GATES)) });
  const ran = capture(() => specMain(["run"]));
  expect(ran.code).toBe(0);

  const after = readFileSync(specPath(), "utf8");
  expect(after).toContain("- [x] G1: the one thing");
  expect(after).toContain("EVIDENCE: g1 ran");

  const receipts = specRunReceipts();
  expect(receipts).toHaveLength(1);
  expect(receipts[0]!["event"]).toBe("spec-run");
  expect(receipts[0]!["surface"]).toBe("ci");
  expect(receipts[0]!["outcome"]).toBe("allow");
  expect(typeof receipts[0]!["latency_ms"]).toBe("number");
});

test("spec run turns a gate whose check cannot run red", () => {
  const broken = '# Gates: fixture\n\n- [ ] G1: the one thing\n  CHECK: no-such-command-ai-eng --version\n  EVIDENCE: pending\n';
  writeLock({ spec_sha256: writeSpec(contract(broken)) });
  const ran = capture(() => specRun());
  expect(ran.code).toBe(1);
  expect(ran.out).toMatch(/spec run: FAILURE \(receipt [0-9a-f]{8}\) — a check that does not run is not green, it is red\./);

  const after = readFileSync(specPath(), "utf8");
  expect(after).toContain("- [ ] G1: the one thing"); // never ticked by a failing gate
  expect(specRunReceipts()[0]!["outcome"]).toBe("deny");
});

test("spec close refuses a contract edited after approval", () => {
  writeLock({ spec_sha256: writeSpec(contract(EVIDENCED_GATES)) });
  writeFileSync(specPath(), contract(EVIDENCED_GATES.replace("the one thing", "the other thing")));
  const refused = capture(() => specClose());
  expect(refused.code).toBe(2);
  expect(refused.out).toContain("spec close: spec.html changed after approval (sha256 differs from the lock)");
  expect(existsSync(specPath())).toBe(true);
});

test("spec close refuses a gate without evidence or ABANDON", () => {
  writeLock({ spec_sha256: writeSpec(contract(PENDING_GATES)) });
  const refused = capture(() => specClose());
  expect(refused.code).toBe(2);
  expect(refused.out).toContain("spec close: 1 gate(s) without evidence or ABANDON (G1)");
  expect(existsSync(specPath())).toBe(true);
});

test("spec close refuses an ABANDON that carries no reason", () => {
  writeLock({ spec_sha256: writeSpec(contract(`${PENDING_GATES}ABANDON: G1 too short\n`)) });
  const refused = capture(() => specClose());
  expect(refused.code).toBe(2);
  expect(refused.out).toContain("spec close: ABANDON: G1 carries no reason — an honest exit says what it is exiting.");
  expect(existsSync(specPath())).toBe(true);
});

test("spec close refuses a contract with nothing to verify", () => {
  writeLock({ spec_sha256: writeSpec(contract("# Gates: fixture\n")) });
  const refused = capture(() => specClose());
  expect(refused.code).toBe(2);
  expect(refused.out).toContain("spec close: no gates found in spec.html — a contract with nothing to verify is not a contract.");
  expect(existsSync(specPath())).toBe(true);
});

test("spec close accepts an honest ABANDON, prints it and frees the slot", () => {
  commitAll("chore: fixture base");
  const reason = "the check needs a network the CI does not have";
  writeLock({ spec_sha256: writeSpec(contract(`${PENDING_GATES}ABANDON: G1 ${reason}\n`)), base_sha: git(["rev-parse", "HEAD"]).out.trim() });
  writeFileSync(join(repo, ".ai-engineering", "brainstorm.html"), "# Handshake\n");
  writeFileSync(join(repo, ".ai-engineering", "recap.html"), "<html></html>\n");

  const closed = capture(() => specClose());
  expect(closed.code).toBe(0);
  expect(closed.out).toContain(`  ABANDON: G1 — ${reason}`);
  expect(closed.out).toContain("✓ contract closed: 1 gate(s) verified, spec/plan/brainstorm/recap dead from the tree");

  for (const name of ["spec.html", "plan.html", "brainstorm.html", "recap.html"]) {
    expect(existsSync(join(repo, ".ai-engineering", name))).toBe(false);
  }
  const lock = readFileSync(lockPath(), "utf8");
  expect(lock).not.toContain("spec_sha256");
  expect(lock).not.toContain("base_sha");
  expect(lock).toContain("[assets]");
});

test("spec close with no lock closes on the artifact's own evidence", () => {
  writeSpec(contract(EVIDENCED_GATES));
  const closed = capture(() => specClose());
  expect(closed.code).toBe(0);
  expect(closed.out).toContain("✓ contract closed: 1 gate(s) verified");
  expect(existsSync(lockPath())).toBe(false); // nothing to clean, nothing invented
});

test("spec close refuses with no live contract", () => {
  const refused = capture(() => specClose());
  expect(refused.code).toBe(2);
  expect(refused.out).toContain("spec close: no live contract.");
});

test("spec close refuses a fired trigger that left no artifact, and accepts its ABANDON", () => {
  writeSkill("ai-design", UI_SKILL);
  const head = commitAll("chore: fixture base");
  writeFileSync(join(repo, "app.css"), "body { color: red; }\n");
  writeLock({ spec_sha256: writeSpec(contract(EVIDENCED_GATES)), base_sha: head });

  const refused = capture(() => specClose());
  expect(refused.code).toBe(2);
  expect(refused.out).toContain('trigger "ui" fired on app.css and ai-design left no artifact — run it, or declare ABANDON: ui <reason>.');

  const reason = "the audit waits for the design pass";
  writeLock({ spec_sha256: writeSpec(contract(`${EVIDENCED_GATES}ABANDON: ui ${reason}\n`)), base_sha: head });
  const closed = capture(() => specClose());
  expect(closed.code).toBe(0);
  expect(closed.out).toContain(`  ABANDON: ui — ${reason}`);
  expect(existsSync(specPath())).toBe(false);
});

test("normalizeSpec folds the run's bookkeeping away and keeps the contract itself", () => {
  const raw = '# Gates: x\n\n- [x] G1: the one thing\n  CHECK: echo ok\n  EVIDENCE: exit 0\n';
  expect(normalizeSpec(raw)).toBe('# Gates: x\n\n- [ ] G1: the one thing\n  CHECK: echo ok\n  EVIDENCE: pending\n');
  expect(normalizeSpec(normalizeSpec(raw))).toBe(normalizeSpec(raw));
  expect(normalizeSpec(raw.replace("- [x]", "- [X]"))).toBe(normalizeSpec(raw));
  expect(normalizeSpec(raw.replace("echo ok", "echo different"))).not.toBe(normalizeSpec(raw));
});

test("canonSkillsDir prefers the installed canon and falls back to this repo's skills/", () => {
  expect(canonSkillsDir()).toBe(join(engHome, "skills"));
  rmSync(join(engHome, "skills"), { recursive: true, force: true });
  const fallback = canonSkillsDir();
  expect(fallback).toBe(join(import.meta.dir, "..", "skills"));
  expect(existsSync(join(fallback!, "ai-proof", "SKILL.md"))).toBe(true);
});

test("lifecycleBlock and blockFields read a node's own condition out of its SKILL.md", () => {
  const markdown = [
    "# ai-design",
    "",
    "## Lifecycle",
    "",
    "Trigger: ui",
    "Trigger: second-value",
    "Trigger when: **/*.css",
    "Writes: a.html, b.html",
    "",
    "## Next",
    "",
    "Trigger: not-this-one",
    "",
  ].join("\n");
  const block = lifecycleBlock(markdown);
  expect(block).toContain("Trigger: ui");
  expect(block).not.toContain("not-this-one");

  const fields = blockFields(block!);
  expect(fields["Trigger"]).toBe("ui"); // the first occurrence is the contract
  expect(fields["Trigger when"]).toBe("**/*.css");
  expect(fields["Lane"]).toBeUndefined();
  expect(blockFields("trigger: lowercase is prose\n\n## H\n").Trigger).toBeUndefined();

  expect(lifecycleBlock("# ai-note\n\n## What it writes\n")).toBeNull();
  expect(lifecycleBlock("### Lifecycle\n\nTrigger: ui\n")).toBeNull();
});

test("readTriggers reads every conditional node out of the canon", () => {
  const canon = join(sandbox, "canon");
  const skill = (name: string, body: string): void => {
    mkdirSync(join(canon, name), { recursive: true });
    writeFileSync(join(canon, name, "SKILL.md"), body);
  };
  skill(
    "ai-alpha",
    [
      "# ai-alpha",
      "",
      "## Lifecycle",
      "",
      "Trigger: alpha",
      "Trigger when: src/a.ts, src/b.ts",
      "Trigger excludes: src/b.ts",
      "Writes: out/a.html, out/b.html",
      "",
    ].join("\n"),
  );
  skill("ai-beta", ["# ai-beta", "", "## Lifecycle", "", "Trigger: beta", "Trigger kind: judgment", "Trigger when: the human says so", ""].join("\n"));
  skill("ai-gamma", "# ai-gamma\n\n## Lifecycle\n\nLane: full\n");
  skill("ai-delta", "# ai-delta\n\n## Anything\n\nTrigger: delta\nTrigger when: src/*.ts\n");
  skill("ai-none", "# ai-none\n\n## Lifecycle\n\nTrigger: none\nTrigger when: src/*.ts\n");
  skill("ai-nowhen", "# ai-nowhen\n\n## Lifecycle\n\nTrigger: nowhen\n");
  skill("other-one", "# other\n\n## Lifecycle\n\nTrigger: other\nTrigger when: src/*.ts\n");
  mkdirSync(join(canon, "ai-nofile"), { recursive: true });

  const triggers = readTriggers(canon);
  expect(triggers.map((trigger) => trigger.id)).toEqual(["alpha", "beta"]);
  expect(triggers[0]).toEqual({
    id: "alpha",
    skill: "ai-alpha",
    kind: "path", // no `Trigger kind:` means a path condition
    globs: ["src/a.ts", "src/b.ts"],
    excludes: ["src/b.ts"],
    writes: "out/a.html", // the first path: the second is generated from it
  });
  expect(triggers[1]!.kind).toBe("judgment");
  expect(readTriggers(null)).toEqual([]);
});

test("changedFiles lists what the milestone touched and refuses a bogus base", () => {
  const head = commitAll("chore: fixture base");
  writeFileSync(join(repo, "tracked.txt"), "one\n");
  commitAll("feat: add a tracked file");
  writeFileSync(join(repo, "tracked.txt"), "two\n");
  writeFileSync(join(repo, "untracked.txt"), "new\n");

  const changed = changedFiles(repo, head);
  expect(changed).toContain("tracked.txt"); // committed since the base
  expect(changed).toContain("untracked.txt"); // worktree, never committed
  expect(changed).not.toContain(".ai-engineering/config.toml"); // untouched since the base

  expect(changedFiles(repo, "not-a-commit")).toEqual([]);
  expect(changedFiles(repo, "--name-only")).toEqual([]); // a base_sha is a revision, never an option
});

test("artifactPattern wildcards only the generated segments", () => {
  expect(artifactPattern(".ai-engineering/security/run-N/findings.json")).toBe(".ai-engineering/security/*/findings.json");
  expect(artifactPattern(".ai-engineering/research/NNN-{name}.html")).toBe(".ai-engineering/research/*");
  expect(artifactPattern("a/N/b")).toBe("a/*/b");
  expect(artifactPattern(".ai-engineering/design/audits/001-x.html")).toBe(".ai-engineering/design/audits/001-x.html");
  expect(artifactPattern("DECISIONS.md")).toBe("DECISIONS.md");
});

test("artifactExists trusts a file and refuses a promise", () => {
  expect(artifactExists(repo, "")).toBe(true); // a node that writes nothing cannot leave evidence
  expect(artifactExists(repo, "nothing — it is a lens, not an author")).toBe(true);

  writeFileSync(join(repo, "AGENTS.md"), "# agents\n");
  expect(artifactExists(repo, "AGENTS.md")).toBe(true);
  expect(artifactExists(repo, "CLAUDE.md")).toBe(false);

  const run = join(repo, ".ai-engineering", "security", "run-1");
  mkdirSync(run, { recursive: true });
  expect(artifactExists(repo, ".ai-engineering/security/run-N/findings.json")).toBe(false); // the folder is a promise
  writeFileSync(join(run, "findings.json"), "{}\n");
  expect(artifactExists(repo, ".ai-engineering/security/run-N/findings.json")).toBe(true);
  expect(artifactExists(repo, ".ai-engineering/security/run-N/REPORT.md")).toBe(false);

  const gc = join(repo, ".ai-engineering", "security", "run-2");
  mkdirSync(gc, { recursive: true });
  writeFileSync(join(gc, "summary.json"), "{}\n");
  expect(artifactExists(repo, ".ai-engineering/security/run-N/summary.json")).toBe(false); // gc's own ledger

  expect(artifactExists(join(sandbox, "gone"), ".ai-engineering/design/audits/NNN-{name}.html")).toBe(false); // a root that cannot be scanned is not proof
});

test("unmetTriggers reports a fired path condition that left nothing, and honours the excludes", () => {
  writeSkill("ai-design", UI_SKILL);
  writeSkill("ai-architect", JUDGMENT_SKILL);
  writeSkill("ai-broken", "# ai-broken\n\n## Lifecycle\n\nTrigger: broken\nTrigger when: [\nWrites: .ai-engineering/broken/NNN-{n}.html\n");
  const head = commitAll("chore: fixture base");

  expect(unmetTriggers(repo, head, new Set())).toEqual([]); // nothing touched yet

  mkdirSync(join(repo, "docs"), { recursive: true });
  writeFileSync(join(repo, "docs/guide.css"), "body{}\n");
  expect(unmetTriggers(repo, head, new Set())).toEqual([]); // docs/** is excluded, and `[` is silent

  writeFileSync(join(repo, "app.css"), "body{}\n");
  const unmet = unmetTriggers(repo, head, new Set());
  expect(unmet).toEqual([{ id: "ui", skill: "ai-design", sample: "app.css" }]); // a judgment node is the planner's

  expect(unmetTriggers(repo, head, new Set(["ui"]))).toEqual([]); // declared ABANDON
  expect(unmetTriggers(repo, "not-a-commit", new Set())).toEqual([]); // no readable base, no verdicts

  mkdirSync(join(repo, ".ai-engineering", "design", "audits"), { recursive: true });
  writeFileSync(join(repo, ".ai-engineering", "design", "audits", "001-x.html"), "<html></html>\n");
  expect(unmetTriggers(repo, head, new Set())).toEqual([]); // a file is proof
});
