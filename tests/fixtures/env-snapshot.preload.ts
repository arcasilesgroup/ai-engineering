// Preloaded into a child `bun test` by tests/test-hygiene.spec.ts. A root-level
// afterEach runs after every file-level afterEach, so each line it appends shows the
// process exactly as the suite under test left it for the next suite.

import { afterEach } from "bun:test";
import { appendFileSync } from "node:fs";

const WATCHED = ["AI_ENG_HOME", "PI_CODING_AGENT_DIR", "GIT_CONFIG_GLOBAL"] as const;
// Captured once at load: a suite that deletes or rewrites the variable must not move
// the place this probe reports to.
const reportFile = process.env["HYGIENE_REPORT"];

function snapshot(): { env: Record<string, string | null>; cwd: string } {
  const env: Record<string, string | null> = {};
  for (const name of WATCHED) env[name] = name in process.env ? (process.env[name] ?? null) : null;
  return { env, cwd: process.cwd() };
}

if (reportFile) {
  appendFileSync(reportFile, `${JSON.stringify({ phase: "before", ...snapshot() })}\n`);
  afterEach(() => {
    appendFileSync(reportFile, `${JSON.stringify({ phase: "after-test", ...snapshot() })}\n`);
  });
}
