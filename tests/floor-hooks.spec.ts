// tests/floor-hooks.spec.ts — the git floor, driven through its public surface.
//
// The floor is what the 3-line shims exec into, and it runs for a person committing
// from Vim as much as for an agent (§13.2). What a hook decides is only observable
// three ways: the `{ ok, lines }` it returns, the files it writes (a receipt, the
// amended commit message), and the exit code `floor()` hands back to git. Every test
// below asserts one of those three — never an internal, never "did not throw".
//
// No network, no real repo, no real home: throwaway `git init` repos in mkdtemp(), a
// sandboxed AI_ENG_HOME, and a `gitleaks` shim on PATH whose exit code and output are
// the only thing that varies (the real gitleaks is not a dependency of this suite).

import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, spyOn, test } from "bun:test";
import { execFileSync, spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { commitMsg, preCommit, prePush } from "../src/floor/index.ts";
import { floor } from "../src/floor/entry.ts";

const SECRET = "AKIAIOSFODNN7EXAMPLE";
const roots: string[] = [];
const HOME_BEFORE = process.env.AI_ENG_HOME;
const PATH_BEFORE = process.env.PATH ?? "";
const CWD_BEFORE = process.cwd();

beforeAll(() => {
  process.env.AI_ENG_HOME = mkdtempSync(join(tmpdir(), "ai-eng-floor-home-"));
});
afterAll(() => {
  if (HOME_BEFORE === undefined) delete process.env.AI_ENG_HOME;
  else process.env.AI_ENG_HOME = HOME_BEFORE;
});
beforeEach(() => {
  process.env.PATH = PATH_BEFORE;
});
afterEach(() => {
  process.chdir(CWD_BEFORE);
  process.env.PATH = PATH_BEFORE;
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

/** A throwaway repo. `governed` writes the declaration `.ai-engineering/config.toml`
 *  — the only thing that makes the floor judge a commit at all (§A). */
function tempRepo(governed: boolean): string {
  const dir = tempDir(governed ? "ai-eng-floor-repo-" : "ai-eng-floor-foreign-");
  run("git", dir, ["init", "-q"]);
  run("git", dir, ["config", "user.email", "floor@example.com"]);
  run("git", dir, ["config", "user.name", "floor test"]);
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

/** A `gitleaks` stand-in: `version` is what the floor probes for, and the scan finds
 *  the marker token only when the scanned surface actually carries it. Both outcomes
 *  come from this shim's exit code and output, so the suite runs with or without the
 *  real binary installed. */
function installGitleaksShim(): string {
  const dir = tempDir("ai-eng-floor-bin-");
  const shim = join(dir, "gitleaks");
  writeFileSync(
    shim,
    [
      "#!/bin/sh",
      'if [ "$1" = "version" ]; then echo "8.18.0"; exit 0; fi',
      'target="."',
      'for arg in "$@"; do if [ -d "$arg" ]; then target="$arg"; fi; done',
      "hit=$(grep -rIl 'AKIA[0-9A-Z][0-9A-Z]*' \"$target\" 2>/dev/null | head -n 1)",
      'if [ -n "$hit" ]; then',
      '  echo "Finding:     AWS access token"',
      '  echo "File:        $hit"',
      '  echo "RuleID:      aws-access-token"',
      "  exit 1",
      "fi",
      "exit 0",
      "",
    ].join("\n"),
  );
  execFileSync("chmod", ["0755", shim]);
  process.env.PATH = `${dir}:${PATH_BEFORE}`;
  return dir;
}

/** A PATH with git and nothing else — how "gitleaks is not installed" is proved
 *  without depending on what this machine happens to have in /opt/homebrew. */
function pathWithoutGitleaks(): void {
  const dir = tempDir("ai-eng-floor-gitonly-");
  symlinkSync(execFileSync("which", ["git"], { encoding: "utf8" }).trim(), join(dir, "git"));
  process.env.PATH = dir;
}

function captureStderr(): { text: () => string; restore: () => void } {
  const chunks: string[] = [];
  const spy = spyOn(process.stderr, "write").mockImplementation(((chunk: string) => {
    chunks.push(String(chunk));
    return true;
  }) as never);
  return { text: () => chunks.join(""), restore: () => spy.mockRestore() };
}

describe("preCommit — diff --check, then the staged-secret scan, then DECISIONS.md", () => {
  test("refuses a staged trailing-whitespace diff and names the file", () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    stage(repo, { "note.txt": "line with trailing spaces   \n" });

    const result = preCommit(repo);

    expect(result.ok).toBe(false);
    expect(result.lines[0]).toBe("diff --check found whitespace problems:");
    expect(result.lines[1]).toContain("note.txt");
    expect(result.lines[1]).toContain("trailing whitespace.");
  });

  test("refuses a staged leftover conflict marker", () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    stage(repo, { "conflict.txt": "a\n<<<<<<< HEAD\nb\n=======\nc\n>>>>>>> other\n" });

    const result = preCommit(repo);

    expect(result.ok).toBe(false);
    expect(result.lines[1]).toContain("leftover conflict marker");
  });

  test("passes a clean commit once the staged blobs scan clean", () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    stage(repo, { "clean.txt": "nothing to see here\n" });

    expect(preCommit(repo)).toEqual({ ok: true, lines: [] });
  });

  test("passes an empty index — nothing staged, nothing to judge", () => {
    const repo = tempRepo(true);
    installGitleaksShim();

    expect(preCommit(repo)).toEqual({ ok: true, lines: [] });
  });

  test("refuses a staged secret and reports the finding, not the scratch path", () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    stage(repo, { "config.env": `AWS_ACCESS_KEY_ID=${SECRET}\n` });

    const result = preCommit(repo);

    expect(result.ok).toBe(false);
    expect(result.lines[0]).toBe("gitleaks: secret in the staged files → BLOCKED.");
    expect(result.lines[1]).toContain("RuleID:");
    expect(result.lines[1]).toContain("aws-access-token");
    expect(result.lines[1]).toContain("<staged>");
  });

  test("HARD FAILS when gitleaks is not on PATH — never silent degradation (§12.1)", () => {
    const repo = tempRepo(true);
    stage(repo, { "clean.txt": "clean\n" });
    pathWithoutGitleaks();

    const result = preCommit(repo);

    expect(result.ok).toBe(false);
    expect(result.lines).toContain("gitleaks is not installed — HARD FAIL, never silent degradation (§12.1).");
    expect(result.lines).toContain("Install it: brew install gitleaks");
  });

  test("requires a DECISIONS.md block when the commit is wider than 10 files", () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    const many: Record<string, string> = {};
    for (let i = 1; i <= 11; i += 1) many[`file-${i}.txt`] = `content ${i}\n`;
    stage(repo, many);

    const result = preCommit(repo);

    expect(result.ok).toBe(false);
    expect(result.lines[0]).toContain("this commit touches 11 files");
    expect(result.lines[0]).toContain("requires a DECISIONS.md block (§9.2) — none exists.");
  });

  test("requires a DECISIONS.md block when a dependency is staged, even alone", () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    stage(repo, { "package.json": '{ "name": "fixture" }\n' });

    const result = preCommit(repo);

    expect(result.ok).toBe(false);
    expect(result.lines[0]).toContain("this commit touches 1 files (or a dependency)");
  });

  test("refuses a DECISIONS.md that carries no D-block", () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    stage(repo, { "package.json": '{ "name": "fixture" }\n', "DECISIONS.md": "# Decisions\n\nnothing to see here\n" });

    const result = preCommit(repo);

    expect(result.ok).toBe(false);
    expect(result.lines[0]).toBe("DECISIONS.md exists but carries no ## D-NNN block — add one (≤6 lines) or shrink the commit.");
  });

  test("accepts a wide commit that carries a DECISIONS.md block", () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    stage(repo, { "package.json": '{ "name": "fixture" }\n', "DECISIONS.md": "# Decisions\n\n## D-001 keep it boring\n" });

    expect(preCommit(repo)).toEqual({ ok: true, lines: [] });
  });
});

describe("commitMsg — the convention, the Receipt-Id trailer, the override reason", () => {
  test("refuses a message that breaks Conventional Commits", () => {
    const msg = write(tempDir("ai-eng-floor-msg-"), "COMMIT_EDITMSG", "just some words\n");

    const result = commitMsg(msg, "abc12345", null);

    expect(result.ok).toBe(false);
    expect(result.lines[0]).toBe('the message does not follow the Conventional Commits convention: "just some words"');
    expect(result.lines[1]).toBe("Format: type(scope): description");
    expect(readFileSync(msg, "utf8")).toBe("just some words\n");
  });

  test("accepts a conventional message and appends the Receipt-Id trailer", () => {
    const msg = write(tempDir("ai-eng-floor-msg-"), "COMMIT_EDITMSG", "feat(floor): block staged secrets\n\nThe body.\n");

    const result = commitMsg(msg, "7f3a0000", null);

    expect(result.ok).toBe(true);
    expect(readFileSync(msg, "utf8")).toBe("feat(floor): block staged secrets\n\nThe body.\n\nReceipt-Id: 7f3a0000\n");
  });

  test("leaves an already-trailered message byte-identical", () => {
    const before = "fix: keep the trailer\n\nReceipt-Id: deadbeef\n";
    const msg = write(tempDir("ai-eng-floor-msg-"), "COMMIT_EDITMSG", before);

    const result = commitMsg(msg, "newvalue", null);

    expect(result.ok).toBe(true);
    expect(result.lines).toEqual([]);
    expect(readFileSync(msg, "utf8")).toBe(before);
  });

  test("travels the active override reason in the commit", () => {
    const msg = write(tempDir("ai-eng-floor-msg-"), "COMMIT_EDITMSG", "chore: land it\n");

    const result = commitMsg(msg, "abc12345", "hotfix under a declared override");

    expect(result.ok).toBe(true);
    expect(readFileSync(msg, "utf8")).toBe("chore: land it\n\nReceipt-Id: abc12345\nOverride-Reason: hotfix under a declared override\n");
    expect(result.lines).toContain("active override travels in the commit: hotfix under a declared override");
  });

  test("refuses a message file it cannot read", () => {
    const result = commitMsg(join(tempDir("ai-eng-floor-msg-"), "absent"), "abc12345", null);

    expect(result.ok).toBe(false);
    expect(result.lines).toEqual(["commit-msg: cannot read the commit message."]);
  });
});

describe("prePush — the whole unpushed surface, and dated overrides", () => {
  test("passes a surface with nothing to leak", () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    write(repo, "app.ts", "export const name = 'clean';\n");

    expect(prePush(repo)).toEqual({ ok: true, lines: [] });
  });

  test("blocks the push when the surface carries a secret", () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    write(repo, "leak.env", `AWS_ACCESS_KEY_ID=${SECRET}\n`);

    const result = prePush(repo);

    expect(result.ok).toBe(false);
    expect(result.lines[0]).toBe("gitleaks in pre-push: secret in the unpushed history → BLOCKED.");
    expect(result.lines[1]).toContain("RuleID:");
    expect(result.lines[1]).toContain("aws-access-token");
  });

  test("HARD FAILS when gitleaks is not on PATH", () => {
    const repo = tempRepo(true);
    pathWithoutGitleaks();

    const result = prePush(repo);

    expect(result.ok).toBe(false);
    expect(result.lines).toEqual(["gitleaks is not installed — HARD FAIL (§12.1). brew install gitleaks"]);
  });

  test("an expired dated override leaves the gate live again (§09.1)", () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    write(repo, ".ai-engineering/overrides.toml", '[[guard.off]]\nname = "floor"\nreason = "pushed under duress"\nuntil = "2020-01-01"\n');
    write(repo, "leak.env", `AWS_ACCESS_KEY_ID=${SECRET}\n`);

    expect(prePush(repo).ok).toBe(false);
  });
});

describe("floor — the dispatcher the shims exec into", () => {
  test("pre-commit: allow runs to exit 0 and leave an allow receipt behind", async () => {
    const repo = tempRepo(true);
    installGitleaksShim();
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
    const receipts = readdirSync(join(repo, ".ai-engineering", "receipts")).filter((n) => n.includes("git-pre-commit"));
    expect(receipts).toHaveLength(1);
    const receipt = JSON.parse(readFileSync(join(repo, ".ai-engineering", "receipts", receipts[0]!), "utf8")) as {
      event: string;
      outcome: string;
      guards: { ran: string[]; denied_by: string | null };
    };
    expect(receipt.event).toBe("git-pre-commit");
    expect(receipt.outcome).toBe("allow");
    expect(receipt.guards).toEqual({ ran: ["floor"], denied_by: null });
  });

  test("pre-commit: a refusing hook returns non-zero and writes a deny receipt", async () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    stage(repo, { "note.txt": "trailing spaces   \n" });
    process.chdir(repo);
    const err = captureStderr();
    let code: number;
    try {
      code = await floor("pre-commit");
    } finally {
      err.restore();
    }

    expect(code).toBe(1);
    expect(err.text()).toContain("diff --check found whitespace problems:");
    expect(err.text()).toContain("[git floor] pre-commit: BLOCKED — what the hooks would say is what needs fixing.");
    const receipts = readdirSync(join(repo, ".ai-engineering", "receipts")).filter((n) => n.includes("git-pre-commit"));
    const receipt = JSON.parse(readFileSync(join(repo, ".ai-engineering", "receipts", receipts[0]!), "utf8")) as {
      outcome: string;
      guards: { denied_by: string | null };
    };
    expect(receipt.outcome).toBe("deny");
    expect(receipt.guards.denied_by).toBe("floor");
  });

  test("commit-msg: a conventional message exits 0 and the file carries the Receipt-Id", async () => {
    const repo = tempRepo(true);
    process.chdir(repo);
    const msg = write(repo, "COMMIT_EDITMSG", "docs: explain the floor\n");
    const err = captureStderr();
    let code: number;
    try {
      code = await floor("commit-msg", msg);
    } finally {
      err.restore();
    }

    expect(code).toBe(0);
    expect(readFileSync(msg, "utf8")).toMatch(/^docs: explain the floor\n\nReceipt-Id: [0-9a-f]{8}\n$/);
  });

  test("commit-msg: a message that breaks the convention exits 1", async () => {
    const repo = tempRepo(true);
    process.chdir(repo);
    const msg = write(repo, "COMMIT_EDITMSG", "did some stuff\n");
    const err = captureStderr();
    let code: number;
    try {
      code = await floor("commit-msg", msg);
    } finally {
      err.restore();
    }

    expect(code).toBe(1);
    expect(err.text()).toContain("does not follow the Conventional Commits convention");
    expect(readFileSync(msg, "utf8")).toBe("did some stuff\n");
  });

  test("commit-msg: called without a message file it answers with usage and exit 2", async () => {
    const repo = tempRepo(true);
    process.chdir(repo);
    const err = captureStderr();
    let code: number;
    try {
      code = await floor("commit-msg");
    } finally {
      err.restore();
    }

    expect(code).toBe(2);
    expect(err.text()).toBe("usage: ai-eng git commit-msg <msgfile>\n");
  });

  test("commit-msg: a live dated override travels as an Override-Reason trailer", async () => {
    const repo = tempRepo(true);
    write(repo, ".ai-engineering/overrides.toml", '[[guard.off]]\nname = "floor"\nreason = "sealed build window"\nuntil = "2999-01-01"\n');
    process.chdir(repo);
    const msg = write(repo, "COMMIT_EDITMSG", "chore: land during the freeze\n");
    const err = captureStderr();
    let code: number;
    try {
      code = await floor("commit-msg", msg);
    } finally {
      err.restore();
    }

    expect(code).toBe(0);
    expect(err.text()).toContain("active override travels in the commit: sealed build window");
    expect(readFileSync(msg, "utf8")).toContain("Override-Reason: sealed build window");
  });

  test("commit-msg: an expired dated override no longer travels (§09.1)", async () => {
    const repo = tempRepo(true);
    write(repo, ".ai-engineering/overrides.toml", '[[guard.off]]\nname = "floor"\nreason = "sealed build window"\nuntil = "2020-01-01"\n');
    process.chdir(repo);
    const msg = write(repo, "COMMIT_EDITMSG", "chore: land after the freeze\n");
    const err = captureStderr();
    let code: number;
    try {
      code = await floor("commit-msg", msg);
    } finally {
      err.restore();
    }

    expect(code).toBe(0);
    expect(err.text()).not.toContain("active override");
    const content = readFileSync(msg, "utf8");
    expect(content).not.toContain("Override-Reason");
    expect(content).toMatch(/Receipt-Id: [0-9a-f]{8}\n$/);
  });

  test("pre-push: exit 0 on a clean surface, exit 1 when it leaks", async () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    write(repo, "app.ts", "export const name = 'clean';\n");
    process.chdir(repo);
    const err = captureStderr();
    try {
      expect(await floor("pre-push")).toBe(0);
      write(repo, "leak.env", `AWS_ACCESS_KEY_ID=${SECRET}\n`);
      expect(await floor("pre-push")).toBe(1);
    } finally {
      err.restore();
    }
    expect(err.text()).toContain("secret in the unpushed history → BLOCKED.");
  });

  test("an unknown hook is answered with the usage line and exit 2", async () => {
    const repo = tempRepo(true);
    process.chdir(repo);
    const err = captureStderr();
    let code: number;
    try {
      code = await floor("post-rewrite");
    } finally {
      err.restore();
    }

    expect(code).toBe(2);
    expect(err.text()).toBe("usage: ai-eng git pre-commit|commit-msg|pre-push\n");
  });

  test("a repo that never declared itself passes in silence and writes nothing (G5)", async () => {
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
});
