// The payload has one source of truth: the files git tracks under skills/, agents/ and
// templates/. The binary carries those folders as they are (`bun build --compile --asset`,
// scripts/build.ts) and src/embed.ts reads them back by path, so there is no generated
// registry or copy to fall out of step. The one build artifact, the chain bundle, lives in
// the ignored generated/ folder and is rebuilt by every compile, test run and pack.

import { expect, test } from "bun:test";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { embeddedChainBundle, embeddedUnder } from "../src/embed.ts";

const root = join(import.meta.dir, "..");
const git = (args: string[]): string => execFileSync("git", args, { cwd: root, encoding: "utf8" });

test("the payload is exactly the tracked files under skills/, agents/ and templates/", () => {
  const tracked = git(["ls-files", "skills", "agents", "templates"]).split("\n").filter(Boolean).sort();
  const shipped = [...embeddedUnder("").keys()].filter((key) => !key.startsWith("generated/")).sort();
  // Empty-test protection: a moved folder must fail loudly, not pass vacuously.
  expect(tracked.length).toBeGreaterThan(100);
  expect(shipped).toEqual(tracked);
});

test("nothing generated is committed, and generated/ is ignored", () => {
  expect(git(["ls-files", "generated", "src/assets.ts", "scripts/.embed", "skills/.chain-bundle"]).trim()).toBe("");
  expect(git(["check-ignore", "generated/chain/ai-eng-chain.ts"]).trim()).toBe("generated/chain/ai-eng-chain.ts");
});

test("the bundle script prints nothing on success: as prepack, its stdout lands inside `npm pack --json`", () => {
  expect(execFileSync(process.execPath, ["scripts/chain-bundle.ts"], { cwd: root, encoding: "utf8" })).toBe("");
});

test("the chain bundle is the current src/chain, self-contained", () => {
  const bundle = embeddedChainBundle();
  expect(bundle).toContain("export");
  expect(bundle).not.toMatch(/from\s+["']\.\.?\//); // a relative import dies in a foreign repo
  expect(bundle).toBe(readFileSync(join(root, "generated", "chain", "ai-eng-chain.ts"), "utf8"));
});
