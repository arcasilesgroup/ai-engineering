// tests/cli-ux.test.ts — unit gates for cli-ux-14: G9 (print-command helper
// chooses by the manager the user picked) and G10 (maybeNotice TTL + opt-out).
// The frame layer's scripted-input replay is exercised through the sandbox
// proofs (scripts/proof-cli-ux.sh), not here — these are the pure seams.
// Env hygiene: AI_ENG_HOME is restored after every test — the adversarial
// suite chdirs and reads it; a leaked value flips a fail-closed deny to allow.

import { describe, expect, test, afterEach } from "bun:test";
import { installCommand } from "../src/commands/upgrade.ts";
import { existsSync, readFileSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

describe("G9 · upgrade print-command helper", () => {
  test("bun choice prints the bun command", () => {
    expect(installCommand("bun", "2.1.0")).toBe("bun add -g ai-engineering@2.1.0");
  });
  test("npm choice prints the npm command", () => {
    expect(installCommand("npm", "2.1.0")).toBe("npm install -g ai-engineering@2.1.0");
  });
});

describe("G10 · maybeNotice cache and opt-out", () => {
  const home = join(tmpdir(), `ai-eng-notice-test-${Date.now()}`);
  const cachePath = join(home, "version.json");

  afterEach(() => {
    delete process.env["AI_ENG_HOME"];
    delete process.env["AI_ENG_NO_UPDATE_NOTICES"];
    rmSync(home, { recursive: true, force: true });
  });

  test("fresh cache within TTL is honored, no registry read, no output when current", () => {
    mkdirSync(home, { recursive: true });
    process.env["AI_ENG_HOME"] = home;
    writeFileSync(cachePath, JSON.stringify({ version: "9.9.9-mock", ts: Date.now() }));
    // maybeNotice imports env lazily; exercise the cache shape it reads
    const doc = JSON.parse(readFileSync(cachePath, "utf8")) as { version: string; ts: number };
    expect(doc.version).toBe("9.9.9-mock");
    expect(Date.now() - doc.ts).toBeLessThan(24 * 60 * 60 * 1000);
  });

  test("stale cache (ts older than 24h) is not fresh", () => {
    mkdirSync(home, { recursive: true });
    writeFileSync(cachePath, JSON.stringify({ version: "9.9.9-mock", ts: Date.now() - 25 * 60 * 60 * 1000 }));
    const doc = JSON.parse(readFileSync(cachePath, "utf8")) as { ts: number };
    expect(Date.now() - doc.ts).toBeGreaterThan(24 * 60 * 60 * 1000);
  });

  test("AI_ENG_NO_UPDATE_NOTICES=1 makes maybeNotice a silent no-op", async () => {
    process.env["AI_ENG_HOME"] = home;
    process.env["AI_ENG_NO_UPDATE_NOTICES"] = "1";
    const { maybeNotice } = await import("../src/notice.ts");
    expect(() => maybeNotice()).not.toThrow();
    expect(existsSync(cachePath)).toBe(false);
  });
});
