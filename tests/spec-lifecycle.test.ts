// The milestone lifecycle, tested against real repositories rather than described:
// a slot that is opened and closed, a contract edited after approval, a conditional
// node that fired and left nothing, an artifact orphaned by a milestone that never
// opened a contract, and a gc that finally collects — but only what git already holds.
import { test, expect, beforeAll, beforeEach, afterAll } from "bun:test";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { summarizeReceipts } from "../src/receipts.ts";
import { normalizeSpec } from "../src/spec/index.ts";

const cli = join(import.meta.dir, "..", "src", "cli.ts");
let sandbox: string;
let engHome: string;
let repo: string;

function eng(args: string[]): { status: number; output: string } {
  const r = spawnSync(process.execPath, [cli, ...args], {
    cwd: repo,
    encoding: "utf8",
    env: { ...process.env, AI_ENG_HOME: engHome, NO_COLOR: "1", CI: "1", AI_ENG_NO_UPDATE_NOTICES: "1" },
    input: "",
  });
  return { status: r.status ?? 0, output: `${r.stdout ?? ""}${r.stderr ?? ""}` };
}

/** A commit dated in the past, because gc judges age by the last commit, not the mtime. */
function commitAsOf(date: string, message: string): void {
  spawnSync("git", ["add", "-A"], { cwd: repo, stdio: "ignore" });
  spawnSync("git", ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", message], {
    cwd: repo,
    stdio: "ignore",
    env: { ...process.env, GIT_AUTHOR_DATE: date, GIT_COMMITTER_DATE: date },
  });
}

function writeLock(fields: { spec_sha256?: string; base_sha?: string }): void {
  const lines = ['version = "2.0.0"', ""];
  if (fields.spec_sha256) lines.push(`spec_sha256 = "${fields.spec_sha256}"`, "");
  if (fields.base_sha) lines.push(`base_sha = "${fields.base_sha}"`, "");
  lines.push("[assets]");
  writeFileSync(join(repo, ".ai-engineering", "ai-eng.lock"), `${lines.join("\n")}\n`);
}

const GATES = `# Gates: fixture

- [ ] G1: the one thing
  CHECK: true
  EVIDENCE: pending
`;

/** Writes a contract and returns the sha256 `spec approve` would pin: the normalised
 *  form, so a fixture whose EVIDENCE is already filled is not mistaken for an edit. */
function writeContract(gates: string): string {
  const spec = `<!DOCTYPE html><html><body><pre id="gates">
${gates}</pre></body></html>
`;
  writeFileSync(join(repo, ".ai-engineering", "spec.html"), spec);
  return createHash("sha256").update(normalizeSpec(spec)).digest("hex");
}

beforeAll(() => {
  sandbox = mkdtempSync(join(tmpdir(), "ai-eng-cycle-"));
  engHome = join(sandbox, "home");
  repo = join(sandbox, "repo");
  mkdirSync(join(engHome, "skills", "ai-design"), { recursive: true });
  mkdirSync(join(repo, ".ai-engineering"), { recursive: true });
  // A canon that declares one conditional node: touching a stylesheet fires it.
  writeFileSync(
    join(engHome, "skills", "ai-design", "SKILL.md"),
    [
      "# ai-design",
      "",
      "## Lifecycle",
      "",
      "Lane: full",
      "Trigger: ui",
      "Trigger when: **/*.css",
      "Writes: .ai-engineering/design/audits/NNN-{name}.html",
      "Read by: the human",
      "Dies: when cited",
      "Next: none",
      "",
    ].join("\n"),
  );
  spawnSync("git", ["init", "-q"], { cwd: repo });
  writeFileSync(
    join(repo, ".ai-engineering", "config.toml"),
    '[gc]\nmax_files = 25\nolder_than = "30d"\nkeep_runs = 2\nreceipts_ttl = "30d"\n',
  );
  // A base commit: base_sha is a commit, so a repo without one has no milestone base.
  spawnSync("git", ["add", "-A"], { cwd: repo, stdio: "ignore" });
  spawnSync("git", ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init"], { cwd: repo, stdio: "ignore" });
});

beforeEach(() => {
  for (const name of ["spec.html", "plan.html", "brainstorm.md", "recap.html", "ai-eng.lock"]) {
    rmSync(join(repo, ".ai-engineering", name), { force: true });
  }
});

afterAll(() => {
  rmSync(sandbox, { recursive: true, force: true });
});

test("spec open records the base commit the conditional nodes are judged against", () => {
  const head = spawnSync("git", ["rev-parse", "HEAD"], { cwd: repo, encoding: "utf8" }).stdout.trim();
  const opened = eng(["spec", "open", "fixture"]);
  expect(opened.status).toBe(0);
  const lock = readFileSync(join(repo, ".ai-engineering", "ai-eng.lock"), "utf8");
  expect(lock).toContain(`base_sha = "${head}"`);
  expect(existsSync(join(repo, ".ai-engineering", "plan.html"))).toBe(true);
});

test("spec close refuses a pending gate, a reasonless ABANDON and a post-approval edit", () => {
  writeContract(GATES);
  writeLock({ spec_sha256: "0".repeat(64) });
  const edited = eng(["spec", "close"]);
  expect(edited.status).toBe(2);
  expect(edited.output).toContain("changed after approval");

  const sha = writeContract(GATES);
  writeLock({ spec_sha256: sha });
  const pending = eng(["spec", "close"]);
  expect(pending.status).toBe(2);
  expect(pending.output).toContain("without evidence or ABANDON");
  expect(existsSync(join(repo, ".ai-engineering", "spec.html"))).toBe(true);

  const sha2 = writeContract(`${GATES}ABANDON: G1 short\n`);
  writeLock({ spec_sha256: sha2 });
  const reasonless = eng(["spec", "close"]);
  expect(reasonless.status).toBe(2);
  expect(reasonless.output).toContain("carries no reason");
});

test("spec close refuses when a fired trigger left no artifact", () => {
  writeFileSync(join(repo, "app.css"), "body { color: red; }\n");
  const sha = writeContract(`${GATES.replace("pending", "ran: true")}`);
  const head = spawnSync("git", ["rev-parse", "HEAD"], { cwd: repo, encoding: "utf8" }).stdout.trim();
  writeLock({ spec_sha256: sha, base_sha: head });
  const refused = eng(["spec", "close"]);
  expect(refused.status).toBe(2);
  expect(refused.output).toContain('trigger "ui" fired on app.css');

  // The honest exit: name the trigger and say why it did not run.
  mkdirSync(join(repo, ".ai-engineering", "design", "audits"), { recursive: true });
  writeFileSync(join(repo, ".ai-engineering", "design", "audits", "001-x.html"), "<html></html>\n");
  const satisfied = eng(["spec", "close"]);
  expect(satisfied.status).toBe(0);
  expect(satisfied.output).toContain("contract closed");
});

test("spec run's own bookkeeping does not invalidate the approved pin", () => {
  const pristine = writeContract(GATES);
  writeLock({ spec_sha256: pristine });
  // What `ai-eng spec run` writes back into that same file: a ticked box, the receipt.
  writeContract(GATES.replace("- [ ] G1", "- [x] G1").replace("EVIDENCE: pending", "EVIDENCE: exit 0"));
  const closed = eng(["spec", "close"]);
  expect(closed.status).toBe(0);
  expect(closed.output).toContain("contract closed");
});

test("doctor warns on an orphan brainstorm with no live contract", () => {
  writeFileSync(join(repo, ".ai-engineering", "brainstorm.md"), "# Handshake\n");
  const orphaned = eng(["doctor"]);
  expect(orphaned.output).toContain("orphan brainstorm.md");
  rmSync(join(repo, ".ai-engineering", "brainstorm.md"), { force: true });
  const clean = eng(["doctor"]);
  expect(clean.output).toContain("clean slot");
});

test("gc deletes only what is old, uncited and already committed — and keeps the last security runs", () => {
  const research = join(repo, ".ai-engineering", "research");
  mkdirSync(research, { recursive: true });
  writeFileSync(join(research, "001-old.html"), "<html>old</html>\n");
  writeFileSync(join(research, "002-cited.html"), "<html>cited</html>\n");
  // D-001 must not confer immunity on research/001-old.html: a bare number in a
  // decision title is not a citation, or every third artifact is immortal.
  writeFileSync(
    join(repo, "DECISIONS.md"),
    "## D-001 · something unrelated\n\n## D-2\nSee research/002-cited.html for the rate limits.\n",
  );
  commitAsOf("2020-01-01T00:00:00", "chore: old artifacts");

  for (const run of ["run-1", "run-2", "run-3", "run-4"]) {
    mkdirSync(join(repo, ".ai-engineering", "security", run), { recursive: true });
    writeFileSync(join(repo, ".ai-engineering", "security", run, "findings.json"), "{}\n");
  }
  commitAsOf("2020-01-02T00:00:00", "chore: old security runs");

  // Written after the last commit, so git holds no copy and gc must leave it alone.
  writeFileSync(join(research, "003-uncommitted.html"), "<html>never committed</html>\n");

  const collected = eng(["doctor", "--gc"]);
  expect(collected.status).toBe(0);
  expect(existsSync(join(research, "001-old.html"))).toBe(false);
  expect(existsSync(join(research, "002-cited.html"))).toBe(true);
  expect(existsSync(join(research, "003-uncommitted.html"))).toBe(true);
  expect(existsSync(join(repo, ".ai-engineering", "security", "run-1"))).toBe(false);
  expect(existsSync(join(repo, ".ai-engineering", "security", "run-4"))).toBe(true);
});

test("gc does not count its own summary as a receipt", () => {
  const receipts = join(repo, ".ai-engineering", "receipts");
  mkdirSync(receipts, { recursive: true });
  writeFileSync(
    join(receipts, "2026-01-01T00-00-00-000Z-PreToolUse-aaaa.json"),
    JSON.stringify({ operation_id: "aaaa", event: "PreToolUse", surface: "claude-code", outcome: "allow", latency_ms: 3 }),
  );
  const once = summarizeReceipts(receipts);
  writeFileSync(join(receipts, "summary.json"), JSON.stringify(once));
  expect(summarizeReceipts(receipts).total).toBe(once.total);
});

test("update does not invalidate the approved pin", () => {
  // The lock is rebuilt on every update, and the two contract fields are not the
  // installer's to drop: doing so erased an approval, so `spec run` refused a
  // contract a human had approved and the milestone could never close — measured in
  // CI, where update runs before spec run.
  const pristine = writeContract(GATES);
  writeLock({ spec_sha256: pristine, base_sha: "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef" });
  // The gate runs and writes its verdict, which normalises back to the pinned hash.
  writeContract(GATES.replace("- [ ] G1", "- [x] G1").replace("EVIDENCE: pending", "EVIDENCE: exit 0"));
  const updated = eng(["update", "--yes"]);
  expect(updated.status, updated.output).toBe(0);
  const after = readFileSync(join(repo, ".ai-engineering", "ai-eng.lock"), "utf8");
  expect(after).toContain(pristine);
  expect(after).toContain("deadbeefdeadbeefdeadbeefdeadbeefdeadbeef");
  expect(eng(["spec", "close"]).status).toBe(0);
});
