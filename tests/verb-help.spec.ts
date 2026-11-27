// tests/verb-help.spec.ts — `ai-eng <verb> --help` must answer about *that* verb, and the
// global menu must say which group runs which verb.
//
// Both were false for every verb at once: cli.ts intercepted --help before dispatch, so
// `ai-eng findings --help` printed the eleven-line menu and not one flag was discoverable
// from the CLI. A unit test over the data would have stayed green while the dispatch kept
// short-circuiting, so the gate for the first is the spawned binary, verb by verb.
import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { stripVTControlCharacters } from "node:util";
import { ALL_VERBS, HUMAN_VERBS, MACHINE_VERBS, renderVerbHelp } from "../src/shared-verbs.ts";

const CLI = join(import.meta.dir, "..", "src", "cli.ts");
const MENU_HEADERS = ["For people:", "For hooks, CI and agents:"];
const MENU_FOOTER = "Run 'ai-eng <command> --help' for flags.";
const VERB_FOOTER = "Run 'ai-eng --help' for every verb.";

type Run = { status: number | null; stdout: string; stderr: string };

describe("the verb-help data answers for every verb", () => {
  test("each registered verb renders its own usage, and an unknown one renders nothing", () => {
    for (const verb of ALL_VERBS) {
      const help = renderVerbHelp(verb);
      expect(help).not.toBeNull();
      expect(help).toContain(`ai-eng ${verb} · `);
      expect(help).toContain(`usage: ai-eng ${verb}`);
    }
    expect(renderVerbHelp("recap")).toBeNull();
  });
});

describe("the spawned binary: `ai-eng <verb> --help` prints that verb's help", () => {
  let home: string;

  beforeAll(() => {
    home = mkdtempSync(join(tmpdir(), "ai-eng-verb-help-"));
  });
  afterAll(() => rmSync(home, { recursive: true, force: true }));

  function eng(args: string[]): Run {
    const run = spawnSync(process.execPath, [CLI, ...args], {
      cwd: home,
      encoding: "utf8",
      env: { ...process.env, AI_ENG_HOME: home, NO_COLOR: "1", CI: "1", AI_ENG_NO_UPDATE_NOTICES: "1" },
      input: "",
      timeout: 20_000,
    });
    return {
      status: run.status,
      stdout: stripVTControlCharacters(run.stdout ?? ""),
      stderr: stripVTControlCharacters(run.stderr ?? ""),
    };
  }

  for (const verb of ALL_VERBS) {
    test(`ai-eng ${verb} --help`, () => {
      const run = eng([verb, "--help"]);
      expect(run.status).toBe(0);
      expect(run.stdout).toContain(`usage: ai-eng ${verb}`);
      expect(run.stdout).toContain(VERB_FOOTER);
      // The whole menu here is the defect this gate exists for.
      expect(run.stdout).not.toContain("For people:");
      expect(run.stderr).toBe("");
    });
  }

  test("an unknown verb with --help still names the typo instead of burying it in the menu", () => {
    const run = eng(["chian", "--help"]);
    expect(run.status).toBe(2);
    expect(run.stderr).toContain("unknown verb: chian");
    expect(run.stderr).toContain("did you mean `ai-eng chain`?");
    expect(run.stdout).toBe("");
  });
});

describe("the global menu labels its two groups", () => {
  let home: string;

  beforeAll(() => {
    home = mkdtempSync(join(tmpdir(), "ai-eng-menu-"));
  });
  afterAll(() => rmSync(home, { recursive: true, force: true }));

  function menu(args: string[]): Run {
    const run = spawnSync(process.execPath, [CLI, ...args], {
      cwd: home,
      encoding: "utf8",
      env: { ...process.env, AI_ENG_HOME: home, NO_COLOR: "1", CI: "1", AI_ENG_NO_UPDATE_NOTICES: "1" },
      input: "",
      timeout: 20_000,
    });
    return { status: run.status, stdout: stripVTControlCharacters(run.stdout ?? ""), stderr: "" };
  }

  /** Where a verb sits in the printed menu, so "under the right header" is measured and
   *  not assumed: the line index of every verb and of every header. */
  function placement(stdout: string): Map<string, number> {
    const lines = stdout.split("\n");
    const seen = new Map<string, number>();
    // `ai-eng work` is a prefix of `ai-eng worktree`: the verb column ends where the
    // padding starts, so the match has to end on whitespace.
    const verbLine = (verb: string): RegExp => new RegExp(`^\\s*ai-eng ${verb}\\s`);
    for (const [index, line] of lines.entries()) {
      for (const header of MENU_HEADERS) if (line.trim() === header) seen.set(header, index);
      for (const verb of ALL_VERBS) if (verbLine(verb).test(line)) seen.set(verb, index);
    }
    return seen;
  }

  test("ai-eng --help prints both headers, each verb under its own, and the closing line", () => {
    const run = menu(["--help"]);
    expect(run.status).toBe(0);
    const at = placement(run.stdout);

    for (const header of MENU_HEADERS) expect(at.get(header)).toBeDefined();
    const people = at.get(MENU_HEADERS[0]!)!;
    const machine = at.get(MENU_HEADERS[1]!)!;
    expect(people).toBeLessThan(machine);

    for (const { verb } of HUMAN_VERBS) {
      expect({ verb, afterPeople: at.get(verb)! > people, beforeMachine: at.get(verb)! < machine }).toEqual({
        verb,
        afterPeople: true,
        beforeMachine: true,
      });
    }
    for (const { verb } of MACHINE_VERBS) expect({ verb, afterMachine: at.get(verb)! > machine }).toEqual({ verb, afterMachine: true });

    expect(run.stdout).toContain(MENU_FOOTER);
    // The footer is the last non-empty line: nothing prints after the next step.
    expect(run.stdout.trimEnd().split("\n").at(-1)).toBe(MENU_FOOTER);
  });

  test("bare `ai-eng` prints the same menu and exits 2, because it was not a request", () => {
    const bare = menu([]);
    const asked = menu(["--help"]);
    expect(bare.status).toBe(2);
    expect(bare.stdout).toBe(asked.stdout);
  });
});
