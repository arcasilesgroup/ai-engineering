// tests/self-protect-readers.spec.ts — running or reading a governed file is not writing
// it. A shipped skill script is there to be run, a static server only reads, and a quoted
// glob names only its own text; every write into a governed path stays denied.

import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { machineBase } from "../src/env.ts";
import { runSelfProtect } from "../src/guards/self-protect.ts";

const HOME_BEFORE = process.env.AI_ENG_HOME;
let repo = "";
let skills = "";

beforeAll(() => {
  process.env.AI_ENG_HOME = mkdtempSync(join(tmpdir(), "ai-eng-readers-home-"));
  repo = join(mkdtempSync(join(tmpdir(), "ai-eng-readers-")), "repo");
  mkdirSync(join(repo, ".ai-engineering", "workflow", "checkpoints"), { recursive: true });
  spawnSync("git", ["init", "-q", "--template=", repo]);
  writeFileSync(join(repo, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n');
  writeFileSync(join(repo, ".gitleaksrc.toml"), "");
  // A pinned spec makes .ai-engineering/spec.html governed.
  writeFileSync(join(repo, ".ai-engineering", "ai-eng.lock"), `spec_sha256 = "${"a".repeat(64)}"\n`);
  writeFileSync(join(repo, ".ai-engineering", "spec.html"), "<html></html>\n");
  skills = join(machineBase(), ".claude", "skills");
});

afterAll(() => {
  rmSync(join(repo, ".."), { recursive: true, force: true });
  rmSync(process.env.AI_ENG_HOME!, { recursive: true, force: true });
  if (HOME_BEFORE === undefined) delete process.env.AI_ENG_HOME;
  else process.env.AI_ENG_HOME = HOME_BEFORE;
});

const verdict = (command: string) => runSelfProtect({ tool_name: "Bash", tool_input: { command }, cwd: repo }, repo);

describe("self-protect — an interpreter may run a governed script", () => {
  test("the script operand of node, bun, deno and python is a run, not a write", () => {
    for (const command of [
      `node ${skills}/ai-audit-design/scripts/audit.mjs --routes / --widths 320 390`,
      `bun ${skills}/archify/bin/archify.mjs finalize out.html`,
      `deno run --allow-read ${skills}/x/mod.ts`,
      `python3 -u "${skills}/x/run.py" report.txt`,
    ]) {
      expect(verdict(command), command).toBeUndefined();
    }
  });

  test("inline code, a governed path past the script, and a write into a governed path stay denied", () => {
    for (const command of [
      `node -e "require('fs').writeFileSync('${skills}/x/a.mjs', '')"`,
      `node -p "require('fs').rmSync('${skills}/x')"`,
      `python3 -c "open('${skills}/x/a.py', 'w')"`,
      `node build.mjs ${skills}/x/a.mjs`,
      `node ${skills}/x/a.mjs ${skills}/x/b.mjs`,
      `node ${skills}/x/a.mjs > ${skills}/x/b.mjs`,
      `node ${skills}/x/a.mjs > .ai-engineering/config.toml`,
    ]) {
      expect(verdict(command)?.deny, command).toBe(true);
    }
  });
});

describe("self-protect — a quoted glob names only its own text", () => {
  test("a quoted glob handed to a program that does not write files is not expanded", () => {
    for (const command of [
      'impeccable hooks ignore-value side-tab "*" --file "**/brainstorm.html" --local',
      "impeccable hooks ignore-value side-tab '*' --file '.ai-engineering/*.html' --local",
    ]) {
      expect(verdict(command), command).toBeUndefined();
    }
  });

  test("an unquoted glob, and a quoted one handed to a tree writer, are still expanded", () => {
    for (const command of [
      "impeccable hooks ignore-value side-tab * --local",
      "impeccable --file .ai-engineering/*.html --local",
      'impeccable --file ".ai-engineering/"*.html --local',
      "git rm '.ai-engineering/*.toml'",
      "rm -f '.ai-engineering/*.toml'",
    ]) {
      expect(verdict(command)?.deny, command).toBe(true);
    }
  });
});
