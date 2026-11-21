// git add copies files into the repository's own index: the paths it names are read, not
// written. A design file called tokens.json, staged, is a workspace write; writing a
// sensitive path for real still needs system write.

import { describe, expect, test } from "bun:test";
import { classifyRequiredMode, modeAllows, DEFAULT_MODE } from "../src/guards/policy.ts";

const repo = "/repo";
const allowed = (command: string): boolean => modeAllows(DEFAULT_MODE, classifyRequiredMode(command, repo));

describe("policy — git add stages, it does not write the files it names", () => {
  test("staging a file whose name says token, secret or credential is allowed by the default mode", () => {
    expect(allowed("git add brand/tokens.json")).toBe(true);
    expect(allowed("git add -- ./brand/tokens.json")).toBe(true);
    expect(allowed("git add docs/secrets-handling.md src/credential-store.ts")).toBe(true);
    expect(allowed("/usr/bin/git add brand/tokens.json")).toBe(true);
  });

  test("staging still costs a workspace write", () => {
    const required = Number.parseInt(classifyRequiredMode("git add brand/tokens.json", repo), 8);
    expect(required & 0o2).toBe(0o2);
  });

  test("a real write to a sensitive path is still a system write the default mode refuses", () => {
    expect(allowed("cp brand/tokens.json ~/.ssh/token")).toBe(false);
    expect(allowed("echo x > deploy-token.txt")).toBe(false);
    expect(allowed("rm .env")).toBe(false);
  });
});
