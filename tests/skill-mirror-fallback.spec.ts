// The Windows portability of the skill mirrors (Bloque 1, item 3): when the OS refuses
// symlinks — a stock Windows laptop without developer mode refuses `dir` symlinks — the
// mirrors fall back to a junction and then to a verified copy, so `init --global` still
// leaves every mirror usable; and the removal side sweeps ai-eng's copies while keeping
// the user's own folders, judged by the only proof there is: byte equality with the canon.

import { afterEach, beforeAll, describe, expect, spyOn, test } from "bun:test";
import * as fs from "node:fs";
import { existsSync, lstatSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { installCanon, mirrorTargets } from "../src/surfaces/canon-install.ts";
import { removeMachineArtifacts } from "../src/surfaces/carriers-install.ts";
import { VERSION } from "../src/version.ts";

let sandbox: string;
const OWNED_ENV = ["AI_ENG_HOME", "PI_CODING_AGENT_DIR", "GIT_CONFIG_GLOBAL"] as const;
let inherited: Record<string, string | undefined> = {};

beforeAll(() => {
  sandbox = mkdtempSync(join(tmpdir(), "ai-eng-mirror-fallback-"));
  inherited = Object.fromEntries(OWNED_ENV.map((key) => [key, process.env[key]]));
});

afterEach(() => {
  for (const key of OWNED_ENV) {
    const value = inherited[key];
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
});

afterEach(() => {
  rmSync(sandbox, { recursive: true, force: true });
  sandbox = mkdtempSync(join(tmpdir(), "ai-eng-mirror-fallback-"));
});

/** The no-links-at-all refusal: a stock Windows laptop without developer mode refuses
 *  `dir` symlinks, and an OS (or policy) that refuses links refuses `junction` too —
 *  so the chain ends at the verified copy on every platform, deterministically. */
function refuseDirSymlinks(): () => void {
  const original = fs.symlinkSync.bind(fs);
  const spy = spyOn(fs, "symlinkSync").mockImplementation((...args: unknown[]) => {
    if (args[2] === "dir" || args[2] === "junction") {
      const error = new Error("operation not permitted") as NodeJS.ErrnoException;
      error.code = "EPERM";
      throw error;
    }
    return (original as (...callArgs: unknown[]) => unknown)(...args);
  });
  return () => spy.mockRestore();
}

function useHome(name: string): string {
  const dir = join(sandbox, name);
  mkdirSync(join(dir, "skills"), { recursive: true });
  process.env["AI_ENG_HOME"] = dir;
  process.env["GIT_CONFIG_GLOBAL"] = join(dir, "gitconfig");
  delete process.env["PI_CODING_AGENT_DIR"];
  return dir;
}

function canonSkillNames(base: string): string[] {
  return readdirSync(join(base, "skills"), { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && !entry.name.startsWith("."))
    .map((entry) => entry.name)
    .sort();
}

function write(path: string, content: string): void {
  mkdirSync(join(path, ".."), { recursive: true });
  writeFileSync(path, content);
}

describe("skill mirrors without symlinks", () => {
  test("when the OS refuses skill symlinks, every mirror gets a verified copy and stays usable", () => {
    const base = useHome("copy-install");
    // A real directory of the user's under a canon skill's name is never replaced.
    write(join(base, ".claude", "skills", "ai-debug", "SKILL.md"), "mine\n");

    const refuse = refuseDirSymlinks();
    let lines: string[];
    try {
      lines = installCanon(VERSION);
    } finally {
      refuse();
    }

    const skills = canonSkillNames(base);
    expect(skills.length).toBeGreaterThan(0);
    const targets = mirrorTargets();
    for (const [index, target] of targets.entries()) {
      const expectedCopies = index === 0 ? skills.length - 1 : skills.length;
      expect(lines).toContain(`✓ Copy → ${target.label} (${expectedCopies} skills)`);
      for (const name of skills) {
        if (index === 0 && name === "ai-debug") continue;
        const entry = lstatSync(join(target.dir, name));
        expect(entry.isSymbolicLink()).toBe(false);
        expect(entry.isDirectory()).toBe(true);
        // Usable: the mirror holds exactly the canon's bytes.
        expect(readFileSync(join(target.dir, name, "SKILL.md"), "utf8")).toBe(readFileSync(join(base, "skills", name, "SKILL.md"), "utf8"));
      }
    }
    expect(readFileSync(join(base, ".claude", "skills", "ai-debug", "SKILL.md"), "utf8")).toBe("mine\n");
  });

  test("the removal sweeps ai-eng's verified copies and keeps the user's own and edited folders", () => {
    const base = useHome("copy-removal");
    write(join(base, ".claude", "skills", "my-own-skill", "SKILL.md"), "mine\n");

    const refuse = refuseDirSymlinks();
    try {
      installCanon(VERSION);
    } finally {
      refuse();
    }
    // A copy edited after the install can no longer be proven ai-eng's, so it stays.
    const edited = join(base, ".agents", "skills", "ai-debug");
    writeFileSync(join(edited, "SKILL.md"), "edited by hand\n");

    removeMachineArtifacts();

    for (const name of canonSkillNames(base)) {
      if (name === "ai-debug") continue;
      for (const target of mirrorTargets()) {
        expect(existsSync(join(target.dir, name))).toBe(false);
      }
    }
    expect(readFileSync(join(base, ".claude", "skills", "my-own-skill", "SKILL.md"), "utf8")).toBe("mine\n");
    expect(readFileSync(join(edited, "SKILL.md"), "utf8")).toBe("edited by hand\n");
  });
});
