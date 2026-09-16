// tests/floor-gates.spec.ts — mutation-tier gates for src/floor/index.ts,
// src/floor/template.ts and src/floor/entry.ts.
//
// Same fixtures discipline as floor-hooks.spec.ts: throwaway git repos in
// mkdtemp, a sandboxed AI_ENG_HOME per file, and a gitleaks shim on PATH.
// This file's shim is ARGV-STRICT: it exits 42 unless the floor passes the
// exact argument contract the shim contract fixes (probe `version`, staged
// scan `dir --redact --no-banner --exit-code 1 <dir>`, push scan
// `git --redact -v`). A mutant that drops or reorders an argument fails the
// shim's argv check and is killed by the run that must succeed.
//
// Every conditional in scope gets a control for BOTH branches: the allow
// branch (clean run, exact empty result) and the deny branch (exact lines).
// Scratch hygiene is asserted per test: the floor's ai-eng-staged-* dir in
// tmpdir must be gone after every preCommit call that materialised blobs.

import { afterAll, afterEach, beforeAll, describe, expect, test } from "bun:test";
import { execFileSync, spawnSync } from "node:child_process";
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { commitMsg, preCommit, prePush } from "../src/floor/index.ts";
import { currentTemplateDir, installTemplateDir, restoreTemplateDir, SHIMS } from "../src/floor/template.ts";
import { floor } from "../src/floor/entry.ts";

const SECRET = "AKIAIOSFODNN7EXAMPLE";
const roots: string[] = [];
const HOME_BEFORE = process.env.AI_ENG_HOME;
const PATH_BEFORE = process.env.PATH ?? "";
const CWD_BEFORE = process.cwd();
const GIT_CONFIG_GLOBAL_BEFORE = process.env.GIT_CONFIG_GLOBAL;

beforeAll(() => {
  process.env.AI_ENG_HOME = mkdtempSync(join(tmpdir(), "ai-eng-floor-gates-home-"));
});
afterAll(() => {
  if (HOME_BEFORE === undefined) delete process.env.AI_ENG_HOME;
  else process.env.AI_ENG_HOME = HOME_BEFORE;
});
afterEach(() => {
  process.chdir(CWD_BEFORE);
  process.env.PATH = PATH_BEFORE;
  if (GIT_CONFIG_GLOBAL_BEFORE === undefined) delete process.env.GIT_CONFIG_GLOBAL;
  else process.env.GIT_CONFIG_GLOBAL = GIT_CONFIG_GLOBAL_BEFORE;
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

function tempDir(prefix: string): string {
  const dir = mkdtempSync(join(tmpdir(), prefix));
  roots.push(dir);
  return dir;
}

function run(bin: string, cwd: string, args: string[]): { status: number; stdout: string; stderr: string } {
  const done = spawnSync(bin, args, { cwd, encoding: "utf8" });
  if (done.status !== 0 && bin === "git") throw new Error(`git ${args.join(" ")} failed: ${done.stderr}`);
  return { status: done.status ?? 1, stdout: done.stdout ?? "", stderr: done.stderr ?? "" };
}

function tempRepo(governed: boolean): string {
  const dir = tempDir(governed ? "ai-eng-gates-repo-" : "ai-eng-gates-foreign-");
  run("git", dir, ["init", "-q"]);
  run("git", dir, ["config", "user.email", "gates@example.com"]);
  run("git", dir, ["config", "user.name", "gates test"]);
  run("git", dir, ["config", "commit.gpgsign", "false"]);
  if (governed) {
    mkdirSync(join(dir, ".ai-engineering"), { recursive: true });
    writeFileSync(join(dir, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n');
  }
  return dir;
}

function write(root: string, name: string, content: string): string {
  const path = join(root, name);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content);
  return path;
}

function stage(root: string, files: Record<string, string>): void {
  for (const [name, content] of Object.entries(files)) write(root, name, content);
  run("git", root, ["add", ...Object.keys(files)]);
}

/** Path with git symlinked and nothing else: proves the "gitleaks missing" HARD FAIL. */
function pathWithoutGitleaks(): void {
  const dir = tempDir("ai-eng-gates-gitonly-");
  symlinkSync(execFileSync("which", ["git"], { encoding: "utf8" }).trim(), join(dir, "git"));
  process.env.PATH = dir;
}

function captureStderr(): { text: () => string; restore: () => void } {
  const chunks: string[] = [];
  const orig = process.stderr.write.bind(process.stderr);
  process.stderr.write = ((chunk: unknown) => {
    chunks.push(String(chunk));
    return true;
  }) as typeof process.stderr.write;
  return { text: () => chunks.join(""), restore: () => (process.stderr.write = orig) };
}

/** Count the floor's scratch dirs in tmpdir before/after — the finally-block's hygiene. */
function stagedScratchCount(): number {
  return readdirSync(tmpdir()).filter((n) => n.startsWith("ai-eng-staged-")).length;
}

/** The argv-strict gitleaks shim. The floor's argument contract, executable:
 *  `version` probe and the two scan shapes must arrive byte-exact or the shim
 *  exits 42 with BADECHO on stderr (so an unexpected run is visible in lines). */
function installStrictShim(opts: { scanExit: number; scanOut?: string; versionExit?: number }): string {
  const dir = tempDir("ai-eng-gates-bin-");
  const shim = join(dir, "gitleaks");
  const out = JSON.stringify(opts.scanOut ?? "");
  writeFileSync(
    shim,
    [
      "#!/bin/sh",
      'if [ "$1" = "version" ]; then',
      `  echo "8.18.0"; exit ${opts.versionExit ?? 0};`,
      "fi",
      'if [ "$1" = "dir" ] && [ "$2" = "--redact" ] && [ "$3" = "--no-banner" ] && [ "$4" = "--exit-code" ] && [ "$5" = "1" ] && [ -d "$6" ]; then',
      `  printf '%b' ${out}; exit ${opts.scanExit};`,
      "fi",
      'if [ "$1" = "git" ] && [ "$2" = "--redact" ] && [ "$3" = "-v" ]; then',
      `  printf '%b' ${out}; exit ${opts.scanExit};`,
      "fi",
      'echo "BADECHO: $*" >&2; exit 42;',
      "",
    ].join("\n"),
  );
  execFileSync("chmod", ["0755", shim]);
  process.env.PATH = `${dir}:${PATH_BEFORE}`;
  return dir;
}

/** A config-setter sandbox: installTemplateDir under a GIT_CONFIG_GLOBAL we own. */
function gitConfigSandbox(): string {
  const dir = tempDir("ai-eng-gates-gitcfg-");
  process.env.GIT_CONFIG_GLOBAL = join(dir, "gitconfig");
  return dir;
}

function stagedBlobErrorOut(): string {
  // What the catch path in stageSecrets parses: File:/RuleID:/Finding: lines.
  return [
    "Finding:     AWS access token",
    "Decoy: this line never survives the filter",
    "File:        config.env",
    "RuleID:      aws-access-token",
    "",
  ].join("\n");
}

describe("floor gates — git() plumbing and the diff --check branch", () => {
  test("a git failure outside any repository surfaces git's stderr bytes verbatim, trimmed", () => {
    const nowhere = tempDir("ai-eng-gates-nowhere-");
    const result = preCommit(nowhere);
    const done = spawnSync("git", ["diff", "--cached", "--check"], { cwd: nowhere, encoding: "utf8" });
    expect(done.status).not.toBe(0);
    expect(result.ok).toBe(false);
    expect(result.lines[0]).toBe("diff --check found whitespace problems:");
    expect(result.lines[1]).toBe((done.stderr ?? "").trim());
    expect(result.lines[1]!.length).toBeGreaterThan(0);
  });

  test("a clean small commit in a governed repo returns ok with exactly no lines", () => {
    const repo = tempRepo(true);
    installStrictShim({ scanExit: 0 });
    stage(repo, { "clean.txt": "clean\n" });
    expect(preCommit(repo)).toEqual({ ok: true, lines: [] });
  });
});

describe("floor gates — whichGitleaks missing is a HARD FAIL", () => {
  test("preCommit without gitleaks refuses with the install hint, prePush likewise", () => {
    const repo = tempRepo(true);
    stage(repo, { "clean.txt": "clean\n" });
    pathWithoutGitleaks();
    const commit = preCommit(repo);
    expect(commit.ok).toBe(false);
    expect(commit.lines[0]).toContain("gitleaks is not installed");
    expect(commit.lines[1]).toBe("Install it: brew install gitleaks");
    const push = prePush(repo);
    expect(push.ok).toBe(false);
    expect(push.lines[0]).toBe("gitleaks is not installed — HARD FAIL (§12.1). brew install gitleaks");
  });
});

describe("floor gates — the DECISIONS.md threshold and the dependency regex", () => {
  test("exactly ten files with no dependency passes clean", () => {
    const repo = tempRepo(true);
    installStrictShim({ scanExit: 0 });
    const many: Record<string, string> = {};
    for (let i = 1; i <= 10; i += 1) many[`file-${i}.txt`] = `content ${i}\n`;
    stage(repo, many);
    expect(preCommit(repo)).toEqual({ ok: true, lines: [] });
  });

  test("eleven files trigger the DECISIONS requirement and count exactly eleven", () => {
    const repo = tempRepo(true);
    installStrictShim({ scanExit: 0 });
    const many: Record<string, string> = {};
    for (let i = 1; i <= 11; i += 1) many[`file-${i}.txt`] = `content ${i}\n`;
    stage(repo, many);
    const result = preCommit(repo);
    expect(result.ok).toBe(false);
    expect(result.lines[0]).toBe(
      "this commit touches 11 files and requires a DECISIONS.md block (§9.2) — none exists.",
    );
  });

  test("the dependency names are anchored: lookalikes and suffixes are not dependencies", () => {
    const repo = tempRepo(true);
    installStrictShim({ scanExit: 0 });
    stage(repo, { "not-package.json": "x\n", "x/Cargo.toml.orig": "x\n", "ab.csproj2": "x\n" });
    expect(preCommit(repo)).toEqual({ ok: true, lines: [] });
  });

  test("ab.csproj IS a dependency (the .* wildcard needs more than one char)", () => {
    const repo = tempRepo(true);
    installStrictShim({ scanExit: 0 });
    stage(repo, { "ab.csproj": "x\n" });
    const result = preCommit(repo);
    expect(result.ok).toBe(false);
    expect(result.lines[0]).toBe(
      "this commit touches 1 files (or a dependency) and requires a DECISIONS.md block (§9.2) — none exists.",
    );
  });

  test("a wide commit with a real D-block passes and never mentions a dependency", () => {
    const repo = tempRepo(true);
    installStrictShim({ scanExit: 0 });
    const many: Record<string, string> = {};
    for (let i = 1; i <= 12; i += 1) many[`file-${i}.txt`] = `content ${i}\n`;
    many["DECISIONS.md"] = "# Decisions\n\n## D-001 wide is fine\n";
    stage(repo, many);
    const result = preCommit(repo);
    expect(result.ok).toBe(true);
    expect(result.lines).toEqual([]);
    expect(result.lines.join("\n")).not.toContain("or a dependency");
  });

  test("a DECISIONS.md whose block header is not at line start counts as no block", () => {
    const repo = tempRepo(true);
    installStrictShim({ scanExit: 0 });
    stage(repo, {
      "package.json": '{ "name": "fixture" }\n',
      "DECISIONS.md": "# Decisions\n\nsee ## D-001 inline for context\n",
    });
    const result = preCommit(repo);
    expect(result.ok).toBe(false);
    expect(result.lines[0]).toBe(
      "DECISIONS.md exists but carries no ## D-NNN block — add one (≤6 lines) or shrink the commit.",
    );
  });
});

describe("floor gates — the staged-secret scan contract", () => {
  test("the scan must arrive as `dir --redact --no-banner --exit-code 1 <dir>` and pass when it exits 0", () => {
    const repo = tempRepo(true);
    installStrictShim({ scanExit: 0 });
    stage(repo, { "clean.txt": "clean\n" });
    const before = stagedScratchCount();
    const result = preCommit(repo);
    expect(result).toEqual({ ok: true, lines: [] });
    expect(stagedScratchCount()).toBe(before);
  });

  test("a scan exit 42 (bad argv from a mutant) or exit 1 both block with the contract text", () => {
    for (const code of [42, 1]) {
      const repo = tempRepo(true);
      installStrictShim({ scanExit: code, scanOut: stagedBlobErrorOut() });
      stage(repo, { "config.env": `AWS_ACCESS_KEY_ID=${SECRET}\n` });
      const before = stagedScratchCount();
      const result = preCommit(repo);
      expect(result.ok).toBe(false);
      expect(result.lines[0]).toBe("gitleaks: secret in the staged files → BLOCKED.");
      expect(stagedScratchCount()).toBe(before);
    }
  });

  test("the finding filter keeps File:/RuleID:/Finding: lines, joins with newlines, and keeps the first ten only", () => {
    const repo = tempRepo(true);
    installStrictShim({ scanExit: 1, scanOut: stagedBlobErrorOut() });
    stage(repo, { "config.env": `AWS_ACCESS_KEY_ID=${SECRET}\n` });
    const result = preCommit(repo);
    expect(result.lines[1]).toContain("File:");
    expect(result.lines[1]).toContain("RuleID:");
    expect(result.lines[1]).toContain("Finding:");
    expect(result.lines[1]).toContain("aws-access-token");
    expect(result.lines[1]).not.toContain("Decoy:");
    expect(result.lines[1]).toMatch(/Finding:[^\n]*\nFile:/);
    expect(result.lines[1]).not.toContain("ai-eng-gates");
  });

  test("more than ten finding lines are truncated to ten", () => {
    const repo = tempRepo(true);
    const noise: string[] = [];
    for (let i = 0; i < 14; i += 1) noise.push(`RuleID:      rule-${i}`);
    installStrictShim({ scanExit: 1, scanOut: [...noise, "Decoy: tail"].join("\n") });
    stage(repo, { "config.env": `AWS_ACCESS_KEY_ID=${SECRET}\n` });
    const result = preCommit(repo);
    expect(result.lines[1]).toContain("rule-9");
    expect(result.lines[1]).not.toContain("rule-10");
    expect(result.lines[1]).not.toContain("Decoy:");
  });

  test("a path that looks like the scratch dir is named <staged>, never the real temp path", () => {
    const repo = tempRepo(true);
    installStrictShim({ scanExit: 1, scanOut: "File: /var/should-never-appear/config.env\nRuleID: aws-access-token\n" });
    stage(repo, { "config.env": `AWS_ACCESS_KEY_ID=${SECRET}\n` });
    const result = preCommit(repo);
    expect(result.lines[1]).not.toContain(tmpdir());
    expect(result.lines[1]).toContain("File:");
  });

  test("an unreadable staged file still leaves no scratch behind and a clean index still passes", () => {
    const repo = tempRepo(true);
    installStrictShim({ scanExit: 0 });
    // Empty index: no scratch is even created.
    const empty = preCommit(repo);
    expect(empty).toEqual({ ok: true, lines: [] });
    // One staged file the shim clears: scratch created and removed.
    stage(repo, { "one.txt": "one\n" });
    const before = stagedScratchCount();
    expect(preCommit(repo)).toEqual({ ok: true, lines: [] });
    expect(stagedScratchCount()).toBe(before);
  });

  test("a pre-push scan must arrive as `git --redact -v`, truncated to 2000 chars on failure", () => {
    const repo = tempRepo(true);
    installStrictShim({ scanExit: 0 });
    write(repo, "app.ts", "clean\n");
    expect(prePush(repo)).toEqual({ ok: true, lines: [] });

    const long = "x".repeat(3000);
    installStrictShim({ scanExit: 1, scanOut: long });
    const result = prePush(repo);
    expect(result.ok).toBe(false);
    expect(result.lines[0]).toBe("gitleaks in pre-push: secret in the unpushed history → BLOCKED.");
    expect(result.lines[1]!.length).toBe(2000);
    expect(result.lines[1]).toBe(long.slice(0, 2000));
  });
});

describe("floor gates — commitMsg contract corners", () => {
  test("a conventional word inside the first line is not a conventional message", () => {
    const msg = write(tempDir("ai-eng-gates-msg-"), "COMMIT_EDITMSG", "this mentions feat: but is not it\n");
    const result = commitMsg(msg, "abc12345", null);
    expect(result.ok).toBe(false);
    expect(result.lines[0]).toBe(
      'the message does not follow the Conventional Commits convention: "this mentions feat: but is not it"',
    );
    expect(readFileSync(msg, "utf8")).toBe("this mentions feat: but is not it\n");
  });

  test("a first line longer than 72 chars is reported truncated to 72", () => {
    const long = `${"a".repeat(80)}: tail`;
    const msg = write(tempDir("ai-eng-gates-msg-"), "COMMIT_EDITMSG", `${long}\n`);
    const result = commitMsg(msg, "abc12345", null);
    expect(result.ok).toBe(false);
    expect(result.lines[0]).toBe(
      `the message does not follow the Conventional Commits convention: "${long.slice(0, 72)}"`,
    );
  });

  test("an override reason longer than 80 chars travels truncated to 80", () => {
    const reason = `r${"e".repeat(99)}`;
    const msg = write(tempDir("ai-eng-gates-msg-"), "COMMIT_EDITMSG", "chore: land it\n");
    const result = commitMsg(msg, "abc12345", reason);
    expect(result.ok).toBe(true);
    expect(result.lines).toEqual([`active override travels in the commit: ${reason.slice(0, 80)}`]);
    expect(readFileSync(msg, "utf8")).toBe(
      `chore: land it\n\nReceipt-Id: abc12345\nOverride-Reason: ${reason}\n`,
    );
  });

  test("an already-trailered message is not rewritten — prove it with a read-only file", () => {
    const before = "fix: keep the trailer\n\nReceipt-Id: deadbeef\n";
    const msg = write(tempDir("ai-eng-gates-msg-"), "COMMIT_EDITMSG", before);
    chmodSync(msg, 0o444);
    try {
      const result = commitMsg(msg, "newvalue", null);
      expect(result.ok).toBe(true);
      expect(result.lines).toEqual([]);
      expect(readFileSync(msg, "utf8")).toBe(before);
    } finally {
      chmodSync(msg, 0o644);
    }
  });
});

describe("floor gates — the git template dir", () => {
  test("currentTemplateDir is null for a config that cannot be read and for an empty value", () => {
    process.env.GIT_CONFIG_GLOBAL = join(tempDir("ai-eng-gates-gitcfg-"), "absent-gitconfig");
    expect(currentTemplateDir()).toBeNull();
    const empty = tempDir("ai-eng-gates-gitcfg-");
    process.env.GIT_CONFIG_GLOBAL = join(empty, "gitconfig");
    writeFileSync(process.env.GIT_CONFIG_GLOBAL, "[init]\n\ttemplateDir =\n");
    expect(currentTemplateDir()).toBeNull();
  });

  test("install into a fresh sandbox: created, shims on disk, and a second run is already current", () => {
    gitConfigSandbox();
    const first = installTemplateDir();
    expect(first.status).toBe("created");
    expect(first.previous).toBeNull();
    expect(first.ours).not.toBeNull();
    expect(first.line).toContain("git init.templateDir → ");
    const dir = first.ours!;
    for (const name of SHIMS) {
      const body = readFileSync(join(dir, "hooks", name), "utf8");
      expect(body).toContain("ai-eng git floor shim");
    }
    const second = installTemplateDir();
    expect(second.status).toBe("current");
    expect(second.line).toContain("our shims already current");
  });

  test("install joined into a user-owned template dir never overwrites a foreign hook", () => {
    const user = tempDir("ai-eng-gates-usertpl-");
    mkdirSync(join(user, "hooks"), { recursive: true });
    writeFileSync(join(user, "hooks", "pre-commit"), "#!/bin/sh\necho mine\n");
    const cfg = gitConfigSandbox();
    writeFileSync(join(cfg, "gitconfig"), `[init]\n\ttemplateDir = ${user}\n`);
    const report = installTemplateDir();
    expect(report.status).toBe("joined");
    expect(report.previous).toBe(user);
    expect(report.ours).toBeNull();
    expect(report.line).toBe(
      `git init.templateDir keeps your ${user} · our three shims written inside it`,
    );
    expect(readFileSync(join(user, "hooks", "pre-commit"), "utf8")).toBe("#!/bin/sh\necho mine\n");
    for (const name of ["commit-msg", "pre-push"] as const) {
      expect(readFileSync(join(user, "hooks", name), "utf8")).toContain("ai-eng git floor shim");
    }
  });

  test("restore: joined dir keeps the user's hook and loses only our marked shims", () => {
    const user = tempDir("ai-eng-gates-usertpl-");
    mkdirSync(join(user, "hooks"), { recursive: true });
    writeFileSync(join(user, "hooks", "pre-commit"), "#!/bin/sh\necho mine\n");
    const cfg = gitConfigSandbox();
    writeFileSync(join(cfg, "gitconfig"), `[init]\n\ttemplateDir = ${user}\n`);
    installTemplateDir();
    // The machine's shim count in their dir: two of ours written next to their one.
    expect(existsSync(join(user, "hooks", "commit-msg"))).toBe(true);
    const line = restoreTemplateDir(user, null);
    expect(line).toBe(
      `git init.templateDir kept yours (${user}) · 2 ai-eng shim(s) removed from it`,
    );
    expect(readFileSync(join(user, "hooks", "pre-commit"), "utf8")).toBe("#!/bin/sh\necho mine\n");
    expect(existsSync(join(user, "hooks", "commit-msg"))).toBe(false);
    expect(existsSync(join(user, "hooks", "pre-push"))).toBe(false);
    expect(existsSync(join(user, "hooks"))).toBe(true);
  });

  test("restore: a created dir is deleted and the setting goes back to unset", () => {
    const cfg = gitConfigSandbox();
    const first = installTemplateDir();
    expect(first.ours).not.toBeNull();
    const ours = first.ours!;
    const line = restoreTemplateDir(first.previous, first.ours);
    expect(line).toBe("git init.templateDir unset (it was unset before)");
    expect(existsSync(ours)).toBe(false);
    expect(currentTemplateDir()).toBeNull();
    expect(existsSync(join(cfg, "gitconfig"))).toBe(true);
  });

  test("restore: the setting the user moved meanwhile is reported and left alone", () => {
    const cfg = gitConfigSandbox();
    const first = installTemplateDir();
    const moved = tempDir("ai-eng-gates-moved-");
    writeFileSync(join(cfg, "gitconfig"), `[init]\n\ttemplateDir = ${moved}\n`);
    const line = restoreTemplateDir(first.previous, first.ours);
    expect(line).toBe(
      `git init.templateDir is now ${moved} — left as it is (it is not the one this install set)`,
    );
    expect(existsSync(first.ours!)).toBe(true);
  });
});

describe("floor gates — the entry dispatcher", () => {
  test("outside any repository floor exits 0 in silence — no stderr, no receipt dir", async () => {
    const nowhere = tempDir("ai-eng-gates-nowhere-");
    process.chdir(nowhere);
    const err = captureStderr();
    let code: number;
    try {
      code = await floor("pre-commit");
    } finally {
      err.restore();
    }
    expect(code).toBe(0);
    expect(err.text()).toBe("");
    expect(existsSync(join(nowhere, ".ai-engineering"))).toBe(false);
  });

  test("a governed pre-commit allow receipt carries surface git, tool pre-commit, sane latency", async () => {
    const repo = tempRepo(true);
    installStrictShim({ scanExit: 0 });
    stage(repo, { "clean.txt": "clean\n" });
    process.chdir(repo);
    const err = captureStderr();
    let code: number;
    try {
      code = await floor("pre-commit");
    } finally {
      err.restore();
    }
    expect(code).toBe(0);
    const receipts = readdirSync(join(repo, ".ai-engineering", "receipts")).filter((n) =>
      n.includes("git-pre-commit"),
    );
    expect(receipts).toHaveLength(1);
    const receipt = JSON.parse(readFileSync(join(repo, ".ai-engineering", "receipts", receipts[0]!), "utf8")) as {
      surface: string;
      tool: string;
      latency_ms: number;
    };
    expect(receipt.surface).toBe("git");
    expect(receipt.tool).toBe("pre-commit");
    expect(receipt.latency_ms).toBeGreaterThanOrEqual(0);
    expect(receipt.latency_ms).toBeLessThan(10_000);
    expect(err.text()).toMatch(/^\[git floor\] pre-commit ✓ \(\d+ms · \d+ receipts\)\n$/);
    expect(Number(err.text().match(/✓ \((\d+)ms/)?.[1])).toBeLessThan(10_000);
  });

  test("a foreign repo (root but not governed) also passes in silence", async () => {
    const repo = tempRepo(false);
    stage(repo, { "note.txt": "trailing spaces   \n" });
    process.chdir(repo);
    const err = captureStderr();
    let code: number;
    try {
      code = await floor("pre-commit");
    } finally {
      err.restore();
    }
    expect(code).toBe(0);
    expect(err.text()).toBe("");
    expect(existsSync(join(repo, ".ai-engineering"))).toBe(false);
  });

  test("a clean pre-commit whose receipt cannot be written still exits 0 and prints no ✓", async () => {
    const repo = tempRepo(true);
    installStrictShim({ scanExit: 0 });
    stage(repo, { "clean.txt": "clean\n" });
    // A receipts PATH that is a file: mkdirSync throws, writeReceipt returns
    // null, and the allow branch must skip the ✓ line — receiptless is not an
    // invitation to celebrate.
    mkdirSync(join(repo, ".ai-engineering"), { recursive: true });
    writeFileSync(join(repo, ".ai-engineering", "receipts"), "not a directory\n");
    process.chdir(repo);
    const err = captureStderr();
    let code: number;
    try {
      code = await floor("pre-commit");
    } finally {
      err.restore();
    }
    expect(code).toBe(0);
    expect(err.text()).toBe("");
  });

  test("the commit-msg Receipt-Id is a hash of the timestamp, not of the empty string", async () => {
    const repo = tempRepo(true);
    process.chdir(repo);
    const msg = write(repo, "COMMIT_EDITMSG", "chore: id check\n");
    const err = captureStderr();
    let code: number;
    try {
      code = await floor("commit-msg", msg);
    } finally {
      err.restore();
    }
    expect(code).toBe(0);
    const id = readFileSync(msg, "utf8").match(/Receipt-Id: ([0-9a-f]{8})\n/)?.[1];
    expect(id).toBeDefined();
    expect(id).not.toBe("e3b0c442"); // sha256("") first 8 hex — the killed mutant's constant
  });
});
