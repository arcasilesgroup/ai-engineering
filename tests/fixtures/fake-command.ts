import { chmodSync, writeFileSync } from "node:fs";
import { join } from "node:path";

/** What the fake prints and how it exits. With `whenFirstArg`, any other first
 *  argument exits 1 and prints nothing. */
export interface FakeCommand {
  exitCode: number;
  stdout?: string;
  whenFirstArg?: string;
}

/** Writes a stand-in for a real tool into `dir`, to be found through PATH, and returns
 *  its path. A shebang script cannot run on Windows, where spawn resolves a bare
 *  `name` to `name.cmd` instead, so there the stand-in is a batch file. */
export function writeFakeCommand(dir: string, name: string, fake: FakeCommand): string {
  if (process.platform === "win32") {
    const path = join(dir, `${name}.cmd`);
    const body = [
      ...(fake.stdout === undefined ? [] : [`echo ${fake.stdout}`]),
      `exit /b ${fake.exitCode}`,
    ];
    const lines = fake.whenFirstArg === undefined
      ? ["@echo off", ...body]
      : ["@echo off", `if not "%~1"=="${fake.whenFirstArg}" exit /b 1`, ...body];
    writeFileSync(path, `${lines.join("\r\n")}\r\n`);
    return path;
  }
  const path = join(dir, name);
  const body = [
    ...(fake.stdout === undefined ? [] : [`echo "${fake.stdout}"`]),
    `exit ${fake.exitCode}`,
  ];
  const lines = fake.whenFirstArg === undefined
    ? ["#!/bin/sh", ...body]
    : ["#!/bin/sh", `if [ "$1" != "${fake.whenFirstArg}" ]; then exit 1; fi`, ...body];
  writeFileSync(path, `${lines.join("\n")}\n`);
  chmodSync(path, 0o755);
  return path;
}

/** `env` with its search path replaced. Windows names are case-insensitive: a copy of
 *  process.env there may carry `Path`, and a second `PATH` beside it leaves the child's
 *  choice between the two undefined. */
export function envWithPath(env: NodeJS.ProcessEnv, searchPath: string): NodeJS.ProcessEnv {
  const result: NodeJS.ProcessEnv = {};
  for (const [name, value] of Object.entries(env)) {
    if (name.toUpperCase() !== "PATH") result[name] = value;
  }
  result["PATH"] = searchPath;
  return result;
}
