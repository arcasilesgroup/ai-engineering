// Uninstall's git-template restore, observed through the global config file git
// actually reads: under a sandboxed machine home (AI_ENG_HOME) the global config is
// that home's own `gitconfig`, and without one it is the user's ~/.gitconfig. HOME
// and AI_ENG_HOME point at different scratch files here, so reading the wrong one
// shows up as the wrong answer — and never touches a real config.
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { restoreTemplateDir } from "../src/floor/template.ts";
import { floor } from "../src/floor/entry.ts";
import { prePush } from "../src/floor/index.ts";
import { compileGitleaksShim, useGitleaksShim } from "./fixtures/gitleaks-shim.ts";

const GLOBAL = "GIT_CONFIG_" + "GLOBAL";
const SAVED = ["HOME", "AI_ENG_HOME", GLOBAL, "XDG_CONFIG_HOME", "GIT_CONFIG_NOSYSTEM"] as const;
let before: Record<string, string | undefined>;
let scratch: string;
let cwdBefore: string;
let userHome: string;
let machineHome: string;

beforeEach(() => {
  before = Object.fromEntries(SAVED.map((name) => [name, process.env[name]]));
  cwdBefore = process.cwd();
  scratch = mkdtempSync(join(tmpdir(), "ai-eng-floor-template-"));
  userHome = join(scratch, "user");
  machineHome = join(scratch, "machine");
  mkdirSync(userHome);
  mkdirSync(machineHome);
  // An ungoverned cwd: AI_ENG_HOME is honoured only outside the repo that would supply it.
  process.chdir(scratch);
  process.env.HOME = userHome;
  process.env.XDG_CONFIG_HOME = join(userHome, ".config");
  process.env.GIT_CONFIG_NOSYSTEM = "1";
  delete process.env[GLOBAL];
});
afterEach(() => {
  process.chdir(cwdBefore);
  for (const name of SAVED) {
    if (before[name] === undefined) delete process.env[name];
    else process.env[name] = before[name];
  }
  rmSync(scratch, { recursive: true, force: true });
});

const setTemplate = (file: string, value: string): void => {
  const done = spawnSync("git", ["config", "--file", file, "init.templateDir", value], { encoding: "utf8" });
  expect(done.status).toBe(0);
};
const templateIn = (file: string): string | null => {
  if (!existsSync(file)) return null;
  const done = spawnSync("git", ["config", "--file", file, "--get", "init.templateDir"], { encoding: "utf8" });
  return done.status === 0 ? done.stdout.trim() : null;
};

describe("restoreTemplateDir reads the global config of the home it runs under", () => {
  test("a sandboxed machine home reads and restores its own gitconfig, never the user's", () => {
    process.env.AI_ENG_HOME = machineHome;
    const sandboxed = join(machineHome, "gitconfig");
    const users = join(userHome, ".gitconfig");
    const previous = join(scratch, "previous");
    const ours = join(scratch, "ours");
    mkdirSync(join(ours, "hooks"), { recursive: true });
    setTemplate(sandboxed, ours);
    setTemplate(users, join(scratch, "users-own"));

    expect(restoreTemplateDir(previous, ours)).toBe(`git init.templateDir restored to ${previous}`);
    expect(templateIn(sandboxed)).toBe(previous);
    expect(templateIn(users)).toBe(join(scratch, "users-own"));
    expect(existsSync(ours)).toBe(false);
  });

  test("without a machine home it is the user's own global config", () => {
    delete process.env.AI_ENG_HOME;
    const users = join(userHome, ".gitconfig");
    const theirs = join(scratch, "theirs");
    setTemplate(users, theirs);
    expect(restoreTemplateDir(null, null)).toBe("git init.templateDir unset (it was unset before)");
    expect(templateIn(users)).toBeNull();
  });

  test("an empty setting is no setting", () => {
    process.env.AI_ENG_HOME = machineHome;
    const sandboxed = join(machineHome, "gitconfig");
    setTemplate(sandboxed, "");
    expect(restoreTemplateDir(null, null)).toBe("git init.templateDir was not set — nothing to restore");
    expect(readFileSync(sandboxed, "utf8")).toContain("templateDir = \n");
  });

  test("a joined directory left with no hooks loses its empty hooks folder", () => {
    process.env.AI_ENG_HOME = machineHome;
    const theirs = join(scratch, "theirs");
    mkdirSync(join(theirs, "hooks"), { recursive: true });
    writeFileSync(join(theirs, "hooks", "pre-push"), "#!/bin/sh\n# ai-eng git floor shim\n");
    writeFileSync(join(theirs, "keep.txt"), "theirs\n");
    setTemplate(join(machineHome, "gitconfig"), theirs);
    expect(restoreTemplateDir(theirs, null)).toBe(`git init.templateDir kept yours (${theirs}) · 1 ai-eng shim(s) removed from it`);
    expect(existsSync(join(theirs, "hooks"))).toBe(false);
    expect(readFileSync(join(theirs, "keep.txt"), "utf8")).toBe("theirs\n");
  });
});

describe("pre-push through the hook entry", () => {
  let shimDir = "";
  let repo = "";
  const pathBefore = process.env.PATH ?? "";
  const refsBefore = process.env.AI_ENG_PUSH_REFS;
  const homeBefore = process.env.AI_ENG_HOME;

  beforeAll(() => {
    shimDir = compileGitleaksShim();
  });
  afterAll(() => {
    rmSync(shimDir, { recursive: true, force: true });
  });
  beforeEach(() => {
    process.env.AI_ENG_HOME = machineHome;
    repo = join(scratch, "repo");
    mkdirSync(join(repo, ".ai-engineering"), { recursive: true });
    const git = (...args: string[]) => expect(spawnSync("git", args, { cwd: repo, encoding: "utf8" }).status).toBe(0);
    git("init", "-q", "-b", "feature");
    writeFileSync(join(repo, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n\n[git]\nbase = "main"\n');
    process.chdir(repo);
  });
  afterEach(() => {
    process.env.PATH = pathBefore;
    if (refsBefore === undefined) delete process.env.AI_ENG_PUSH_REFS;
    else process.env.AI_ENG_PUSH_REFS = refsBefore;
    if (homeBefore === undefined) delete process.env.AI_ENG_HOME;
    else process.env.AI_ENG_HOME = homeBefore;
  });

  async function hookStderr(scanOut: string): Promise<{ code: number; stderr: string }> {
    useGitleaksShim(shimDir, { mode: "strict", scanExit: 1, scanOut }, pathBefore);
    process.env.AI_ENG_PUSH_REFS = "";
    const chunks: string[] = [];
    const original = process.stderr.write.bind(process.stderr);
    process.stderr.write = ((chunk: unknown) => {
      chunks.push(String(chunk));
      return true;
    }) as typeof process.stderr.write;
    try {
      return { code: await floor("pre-push"), stderr: chunks.join("") };
    } finally {
      process.stderr.write = original;
    }
  }

  const BLOCKED = "gitleaks in pre-push: secret in the unpushed history → BLOCKED.";

  test("a long report keeps two lines and folds the rest, line endings normalised and trailing blanks dropped", async () => {
    expect(await hookStderr("one\r\ntwo\rthree\n\nfour\n\n\n")).toEqual({ code: 1, stderr: `${BLOCKED}\none\ntwo | three |  | four\n` });
  });

  test("a short report prints as it is", async () => {
    expect(await hookStderr("only")).toEqual({ code: 1, stderr: `${BLOCKED}\nonly\n` });
  });

  test("a push to the base is refused however the ref line is spaced", () => {
    process.env.AI_ENG_PUSH_REFS = `  refs/heads/feature  ${"1".repeat(40)}   refs/heads/main\t${"0".repeat(40)}\n`;
    expect(prePush(repo)).toEqual({ ok: false, lines: ["direct push to detected base refs/heads/main is not allowed — open a PR instead."] });
  });
});
