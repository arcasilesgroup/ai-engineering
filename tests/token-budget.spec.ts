import { describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { tmpdir } from "node:os";
import { delimiter, join } from "node:path";
import { pathToFileURL } from "node:url";
import { canonSkills, embeddedPath } from "../src/embed.ts";
import { envWithPath, writeFakeCommand } from "./fixtures/fake-command.ts";

const ROOT = join(import.meta.dir, "..");
const SKILLS = join(ROOT, "skills");
const TEMPLATE = join(ROOT, "templates", "AGENTS.md.tpl");
const BIN = join(ROOT, "bin", "ai-eng.js");
const BASE_ENV = { ...process.env, AI_ENG_NO_UPDATE_NOTICES: "1", NO_COLOR: "1" };
const FRONTMATTER = /^---\r?\n[\s\S]*?\r?\n---(?:\r?\n|$)/;

function frontmatterBytes(path: string): number {
  const frontmatter = FRONTMATTER.exec(readFileSync(path, "utf8"));
  if (!frontmatter) throw new Error(`missing skill frontmatter: ${path}`);
  return Buffer.byteLength(frontmatter[0], "utf8");
}

function coreFrontmatterBytes(): number {
  const skillFiles = readdirSync(SKILLS, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && existsSync(join(SKILLS, entry.name, "SKILL.md")))
    .map((entry) => join(SKILLS, entry.name, "SKILL.md"));
  if (skillFiles.length === 0) throw new Error("no core skill files found");
  return skillFiles.reduce((total, file) => total + frontmatterBytes(file), 0);
}

/** Frontmatter bytes of every skill init installs, read from the shipped payload itself. */
function installableFrontmatterBytes(): number {
  const skillFiles = [...canonSkills()].filter(([path]) => /^skills\/[^/]+\/SKILL\.md$/.test(path));
  if (skillFiles.length === 0) throw new Error("the payload ships no skills");
  return skillFiles.reduce((total, [, ref]) => total + frontmatterBytes(embeddedPath(ref)), 0);
}

function tokenLine(output: string, label: string): number {
  const match = new RegExp(`^${label}:\\s+(\\d+(?:\\.\\d+)?) tokens$`, "m").exec(output);
  if (!match) throw new Error(`missing "${label}: <count> tokens" line`);
  return Number(match[1]);
}

function runAiEng(
  args: string[],
  options: { cwd?: string; env?: NodeJS.ProcessEnv; input?: string; useSource?: boolean } = {},
): { status: number | null; stdout: string; stderr: string } {
  const result = spawnSync(process.execPath, [options.useSource ? join(ROOT, "src", "cli.ts") : BIN, ...args], {
    cwd: options.cwd ?? ROOT,
    env: options.env ?? BASE_ENV,
    input: options.input,
    encoding: "utf8",
  });
  return { status: result.status, stdout: result.stdout ?? "", stderr: result.stderr ?? "" };
}

function outputLineCount(result: { stdout: string; stderr: string }): number {
  const output = `${result.stdout}${result.stderr}`.trimEnd();
  return output.length === 0 ? 0 : output.split(/\r?\n/).length;
}

function git(args: string[], env: NodeJS.ProcessEnv): void {
  const result = spawnSync("git", args, { cwd: ROOT, env, encoding: "utf8" });
  if (result.status !== 0) throw new Error(`git ${args.join(" ")} failed: ${result.stderr}`);
}

function headIndex(): { path: string; env: NodeJS.ProcessEnv } {
  const path = join(import.meta.dir, `.token-budget-index-${randomUUID()}`);
  const env = { ...BASE_ENV, GIT_INDEX_FILE: path };
  git(["read-tree", "HEAD"], env);
  return { path, env };
}

describe("token budgets", () => {
  test("core skill frontmatter and the AGENTS template fit their byte/4 budgets", () => {
    expect(coreFrontmatterBytes() / 4).toBeLessThanOrEqual(5_000);
    expect(Buffer.byteLength(readFileSync(TEMPLATE), "utf8") / 4).toBeLessThanOrEqual(1_200);
  });

  test("every installable skill's frontmatter fits 5,000 tokens, and the core count covers each of them", () => {
    expect(installableFrontmatterBytes() / 4).toBeLessThanOrEqual(5_000);
    expect(installableFrontmatterBytes()).toBe(coreFrontmatterBytes());
  });

  test("bun run tokens prints the same actual counts", () => {
    const result = spawnSync(process.execPath, ["run", "tokens"], {
      cwd: ROOT,
      env: BASE_ENV,
      encoding: "utf8",
    });

    expect(result.status).toBe(0);
    expect(tokenLine(result.stdout ?? "", "core skill frontmatter")).toBe(coreFrontmatterBytes() / 4);
    expect(tokenLine(result.stdout ?? "", "AGENTS.md template")).toBe(Buffer.byteLength(readFileSync(TEMPLATE), "utf8") / 4);
  });

  test("chain allow and all green git hooks print no lines", () => {
    const chain = runAiEng(["chain", "PreToolUse", "--surface", "claude-code"], {
      cwd: "/",
      input: JSON.stringify({ tool_name: "Bash", tool_input: { command: "ls" }, cwd: "/" }),
    });
    expect(chain.status).toBe(0);
    expect(outputLineCount(chain)).toBe(0);

    const index = headIndex();
    const message = join(import.meta.dir, `.token-budget-message-${randomUUID()}`);
    const shimDir = mkdtempSync(join(tmpdir(), "ai-eng-token-budget-bin-"));
    // pre-push denies when no base resolves (R8); CI's detached PR checkout has no
    // origin/HEAD, so the green push runs in a repo that declares its base.
    const pushRepo = mkdtempSync(join(tmpdir(), "ai-eng-token-budget-push-"));
    try {
      // Both hooks hard-fail without gitleaks (§12.1); CI's check job has none, so the
      // green path is measured against a shim that passes for both.
      writeFakeCommand(shimDir, "gitleaks", { exitCode: 0 });
      const shimPath = `${shimDir}${delimiter}${process.env.PATH ?? ""}`;
      const preCommit = runAiEng(["git", "pre-commit"], { env: envWithPath(index.env, shimPath) });
      writeFileSync(message, "docs: verify silent hooks\n");
      const commitMsg = runAiEng(["git", "commit-msg", message]);

      const init = spawnSync("git", ["init", "-q", "-b", "feature", pushRepo], { encoding: "utf8" });
      if (init.status !== 0) throw new Error(`git init failed: ${init.stderr}`);
      mkdirSync(join(pushRepo, ".ai-engineering"));
      writeFileSync(join(pushRepo, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n\n[git]\nbase = "main"\n');
      const prePush = runAiEng(["git", "pre-push"], {
        cwd: pushRepo,
        env: envWithPath({ ...BASE_ENV, AI_ENG_PUSH_REFS: "" }, shimPath),
      });

      // One comparison per hook, so a CI failure names the hook and shows what it printed.
      for (const [hook, result] of Object.entries({ preCommit, commitMsg, prePush })) {
        expect({ hook, status: result.status, output: `${result.stdout}${result.stderr}`.trimEnd() }).toEqual({
          hook,
          status: 0,
          output: "",
        });
      }
    } finally {
      rmSync(index.path, { force: true });
      rmSync(`${index.path}.lock`, { force: true });
      rmSync(message, { force: true });
      rmSync(shimDir, { recursive: true, force: true });
      rmSync(pushRepo, { recursive: true, force: true });
    }
  });

  test("a successful commit-msg with an active override prints no lines", () => {
    const repo = mkdtempSync(join(tmpdir(), "ai-eng-token-budget-override-"));
    const configDir = join(repo, ".ai-engineering");
    const message = join(repo, "COMMIT_EDITMSG");
    mkdirSync(configDir, { recursive: true });
    writeFileSync(join(configDir, "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n');
    writeFileSync(
      join(configDir, "overrides.toml"),
      '[[guard.off]]\nname = "floor"\nreason = "freeze exception"\nuntil = "2999-01-01"\n',
    );
    writeFileSync(message, "chore: commit during freeze\n");
    try {
      const commitMsg = runAiEng(["git", "commit-msg", message], { cwd: repo, useSource: true });

      expect(commitMsg.status).toBe(0);
      expect(outputLineCount(commitMsg)).toBe(0);
      expect(readFileSync(message, "utf8")).not.toContain("Override-Reason");
    } finally {
      rmSync(repo, { recursive: true, force: true });
    }
  });

  test("chain denies retain the reason and exit contract within three lines", () => {
    const surfaces: Array<[string, number]> = [
      ["claude-code", 2],
      ["codex", 0],
      ["cursor", 0],
      ["copilot-cli", 0],
    ];
    for (const [surface, status] of surfaces) {
      const denied = runAiEng(["chain", "PreToolUse", "--surface", surface], { input: "{" });
      expect(denied.status).toBe(status);
      expect(outputLineCount(denied)).toBeLessThanOrEqual(3);
      expect(`${denied.stdout}${denied.stderr}`).toContain("hook payload could not be read");
    }

    const dialect = pathToFileURL(join(ROOT, "src", "chain", "dialect.ts")).href;
    const loopDeny = spawnSync(
      process.execPath,
      ["-e", `import { deny } from ${JSON.stringify(dialect)}; deny("loop", "loop reason retained", "claude");`],
      { cwd: ROOT, env: BASE_ENV, encoding: "utf8" },
    );
    expect(loopDeny.status).toBe(2);
    expect(outputLineCount({ stdout: loopDeny.stdout ?? "", stderr: loopDeny.stderr ?? "" })).toBeLessThanOrEqual(3);
    expect(loopDeny.stderr).toContain("loop reason retained");
  });

  test("floor denies retain the reason and exit code within three lines", () => {
    const index = headIndex();
    const whitespaceFile = join(import.meta.dir, `token-budget-whitespace-${randomUUID()}.txt`);
    const relativeWhitespaceFile = `tests/${whitespaceFile.slice(import.meta.dir.length + 1)}`;
    const message = join(import.meta.dir, `.token-budget-invalid-message-${randomUUID()}`);
    try {
      writeFileSync(whitespaceFile, "trailing whitespace \n");
      // --force: under Stryker the suite runs inside an ignored sandbox folder; the index is private.
      git(["add", "--force", "--", relativeWhitespaceFile], index.env);
      const preCommit = runAiEng(["git", "pre-commit"], { env: index.env });
      expect(preCommit.status).toBe(1);
      expect(outputLineCount(preCommit)).toBeLessThanOrEqual(3);
      expect(`${preCommit.stdout}${preCommit.stderr}`).toContain("trailing whitespace.");

      writeFileSync(message, "not a conventional message\n");
      const commitMsg = runAiEng(["git", "commit-msg", message]);
      expect(commitMsg.status).toBe(1);
      expect(outputLineCount(commitMsg)).toBeLessThanOrEqual(3);
      expect(`${commitMsg.stdout}${commitMsg.stderr}`).toContain("does not follow the Conventional Commits convention");
    } finally {
      rmSync(index.path, { force: true });
      rmSync(`${index.path}.lock`, { force: true });
      rmSync(whitespaceFile, { force: true });
      rmSync(message, { force: true });
    }
  });
});
