import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, rmSync, symlinkSync } from "node:fs";
import { delimiter, join } from "node:path";
import { describe, expect, test } from "bun:test";
import { resolveTarget } from "../bin/ai-eng.js";

const ROOT = join(import.meta.dir, "..");
const LAUNCHER = join(ROOT, "bin", "ai-eng.js");
const VERSION = (JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8")) as { version: string }).version;

function findNode(): string {
  if (process.env.AI_ENG_TEST_NODE) return process.env.AI_ENG_TEST_NODE;

  const executable = process.platform === "win32" ? "node.exe" : "node";
  const found = (process.env.PATH ?? "")
    .split(delimiter)
    .map((directory) => join(directory, executable))
    .find((path) => existsSync(path));
  if (!found) throw new Error("Node is required to exercise the npm launcher refusal path");
  return found;
}

const NODE = findNode();

describe("resolveTarget", () => {
  test("maps the seven host shapes to package suffixes", () => {
    expect(resolveTarget("darwin", "arm64", false)).toBe("darwin-arm64");
    expect(resolveTarget("darwin", "x64", false)).toBe("darwin-x64");
    expect(resolveTarget("win32", "arm64", false)).toBe("windows-arm64");
    expect(resolveTarget("linux", "x64", false)).toBe("linux-x64");
    expect(resolveTarget("linux", "x64", true)).toBe("linux-musl-x64");
    expect(resolveTarget("linux", "arm64", true)).toBe("linux-musl-arm64");
    expect(resolveTarget("sunos", "x64", false)).toBeNull();
  });

  test("musl only applies to linux", () => {
    expect(resolveTarget("darwin", "arm64", true)).toBe("darwin-arm64");
    expect(resolveTarget("win32", "x64", true)).toBe("windows-x64");
  });
});

test("the npm executable declares Bun as its shebang runtime", () => {
  const launcher = readFileSync(LAUNCHER, "utf8");
  expect(launcher.slice(0, launcher.indexOf("\n"))).toBe("#!/usr/bin/env bun");
});

test("the executable reports the exact version when Bun runs without Node on PATH", () => {
  if (process.platform === "win32") {
    const done = spawnSync(process.execPath, [LAUNCHER, "--version"], {
      encoding: "utf8",
      env: { ...process.env, PATH: "" },
    });
    expect({ status: done.status ?? 1, stdout: done.stdout ?? "", stderr: done.stderr ?? "" }).toEqual({
      status: 0,
      stdout: `ai-eng ${VERSION}\n`,
      stderr: "",
    });
    return;
  }

  const bunOnlyPath = join(ROOT, `.launcher-bun-only-${process.pid}`);
  mkdirSync(bunOnlyPath);
  try {
    symlinkSync(process.execPath, join(bunOnlyPath, "bun"));
    const done = spawnSync(LAUNCHER, ["--version"], {
      encoding: "utf8",
      env: { ...process.env, PATH: bunOnlyPath },
    });
    expect({ status: done.status ?? 1, stdout: done.stdout ?? "", stderr: done.stderr ?? "" }).toEqual({
      status: 0,
      stdout: `ai-eng ${VERSION}\n`,
      stderr: "",
    });
  } finally {
    rmSync(bunOnlyPath, { recursive: true, force: true });
  }
});

test("the npm Node entry reports the exact version through Bun", () => {
  const done = spawnSync(NODE, [LAUNCHER, "--version"], {
    encoding: "utf8",
    env: { ...process.env },
  });
  expect({ status: done.status ?? 1, stdout: done.stdout ?? "", stderr: done.stderr ?? "" }).toEqual({
    status: 0,
    stdout: `ai-eng ${VERSION}\n`,
    stderr: "",
  });
});

test("the npm Node entry refuses clearly when Bun is absent", () => {
  const done = spawnSync(NODE, [LAUNCHER, "--version"], {
    encoding: "utf8",
    env: { ...process.env, PATH: "" },
  });
  expect({ status: done.status ?? 1, stdout: done.stdout ?? "", stderr: done.stderr ?? "" }).toEqual({
    status: 1,
    stdout: "",
    stderr: "ai-eng: no bun runtime on PATH to run the source.\n  install bun: https://bun.com\n",
  });
});
