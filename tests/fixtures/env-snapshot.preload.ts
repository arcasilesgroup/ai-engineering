// Preloaded into a child `bun test` by tests/test-hygiene.spec.ts. Bun evaluates a preload
// once per test file and runs its root afterAll after the file's own afterAll, so each
// suite appends two lines: the process as the suite found it, and as it left it for the
// next one. Bun.main names the suite.

import { afterAll } from "bun:test";
import { appendFileSync } from "node:fs";
import { SANDBOX_VARS } from "./sandbox-env.ts";

// Captured once at load: a suite that deletes or rewrites the variable must not move
// the place this probe reports to.
const reportFile = process.env["HYGIENE_REPORT"];

function snapshot(): { suite: string; env: Record<string, string | null>; cwd: string } {
  const env: Record<string, string | null> = {};
  for (const name of SANDBOX_VARS) env[name] = name in process.env ? (process.env[name] ?? null) : null;
  return { suite: Bun.main, env, cwd: process.cwd() };
}

if (reportFile) {
  appendFileSync(reportFile, `${JSON.stringify({ phase: "before", ...snapshot() })}\n`);
  afterAll(() => {
    appendFileSync(reportFile, `${JSON.stringify({ phase: "after-suite", ...snapshot() })}\n`);
  });
}
