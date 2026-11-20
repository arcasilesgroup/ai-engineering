// tests/self-protect-recorders.spec.ts — an agent may record governance files, never write
// them. `ai-eng update` writes the lock and the carriers; the agent that ran it can stage
// and commit them (an agentic update of every repo needs no human step), while every
// command that changes their bytes stays denied.

import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { runSelfProtect } from "../src/guards/self-protect.ts";

let repo = "";

beforeAll(() => {
  repo = join(mkdtempSync(join(tmpdir(), "ai-eng-recorders-")), "repo");
  mkdirSync(join(repo, ".ai-engineering"), { recursive: true });
  spawnSync("git", ["init", "-q", "--template=", repo]);
  writeFileSync(join(repo, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n');
  writeFileSync(join(repo, ".ai-engineering", "ai-eng.lock"), 'version = "3.0.8"\n\n[assets]\n');
});

afterAll(() => {
  rmSync(join(repo, ".."), { recursive: true, force: true });
});

const verdict = (command: string) => runSelfProtect({ tool_name: "Bash", tool_input: { command } }, repo);

describe("self-protect — recording a governance file is allowed, writing it is not", () => {
  test("git add and git commit may name the lock and the config", () => {
    for (const command of [
      "git add .ai-engineering/ai-eng.lock",
      "git add -- .ai-engineering/ai-eng.lock .ai-engineering/config.toml",
      'git commit -m "chore(ai-eng): update to 3.0.9" -- .ai-engineering/ai-eng.lock',
      "git -C . add .ai-engineering/ai-eng.lock && git commit -m chore",
    ]) {
      expect(verdict(command), command).toBeUndefined();
    }
  });

  test("every command that changes the bytes stays denied", () => {
    for (const command of [
      "git checkout HEAD~1 -- .ai-engineering/ai-eng.lock",
      "git restore .ai-engineering/ai-eng.lock",
      "git rm .ai-engineering/ai-eng.lock",
      "echo forged > .ai-engineering/ai-eng.lock",
      "cp /tmp/x .ai-engineering/ai-eng.lock",
    ]) {
      expect(verdict(command)?.deny, command).toBe(true);
    }
  });
});
