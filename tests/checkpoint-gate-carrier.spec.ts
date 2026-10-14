/**
 * Workflow kit checkpoint 3 — denying carriers name checkpoint-gate beside chain.
 *
 * Red until every denying-surface carrier template that already runs the chain
 * also names checkpoint-gate, without replacing the chain itself. Zed has no
 * carrier; this suite must not require a Zed template.
 */
import { describe, test, expect } from "bun:test";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

const ROOT = join(import.meta.dir, "..");
const TEMPLATES = join(ROOT, "templates");
const SURFACES = join(ROOT, "src", "surfaces", "surfaces.json");

/** Carrier templates for surfaces that can deny a tool call (not Zed host-only). */
const DENYING_CARRIER_TEMPLATES = [
  "settings.claude.json.tpl",
  "settings.cursor.json.tpl",
  "settings.codex.json.tpl",
  "settings.copilot.json.tpl",
  "settings.copilot.cli.json.tpl",
  "plugin.opencode.ts.tpl",
  "plugin.omp.ts.tpl",
  "plugin.pi.ts.tpl",
] as const;

function runsChain(content: string): boolean {
  return /ai-eng chain/.test(content) || /\bchain\s*\(/.test(content);
}

function namesCheckpointGate(content: string): boolean {
  return (
    /checkpoint-gate/.test(content) ||
    /skills\/ai-orchestrator\/checkpoint-gate\.py/.test(content)
  );
}

function denyingCarrierTemplatesOnDisk(): string[] {
  return DENYING_CARRIER_TEMPLATES.filter((name) => existsSync(join(TEMPLATES, name)));
}

describe("workflow kit — checkpoint-gate beside chain on deny carriers", () => {
  test("every denying-surface carrier that runs the chain also names checkpoint-gate", () => {
    const problems: string[] = [];
    for (const name of denyingCarrierTemplatesOnDisk()) {
      const content = readFileSync(join(TEMPLATES, name), "utf8");
      if (!runsChain(content)) continue;
      if (!namesCheckpointGate(content)) {
        problems.push(`${name}: runs chain but missing checkpoint-gate`);
      }
    }
    expect(problems).toEqual([]);
  });

  test("those same templates still keep the chain (gate does not replace it)", () => {
    const problems: string[] = [];
    for (const name of denyingCarrierTemplatesOnDisk()) {
      const content = readFileSync(join(TEMPLATES, name), "utf8");
      if (!runsChain(content)) continue;
      if (!namesCheckpointGate(content)) {
        problems.push(`${name}: checkpoint-gate not registered beside chain yet`);
        continue;
      }
      if (!runsChain(content)) {
        problems.push(`${name}: checkpoint-gate present but chain removed`);
      }
    }
    expect(problems).toEqual([]);
  });

  test("Zed has no carrier template; suite does not require one", () => {
    const zedTemplates = readdirSync(TEMPLATES).filter((name) => /zed/i.test(name));
    expect(zedTemplates).toEqual([]);

    const catalog = JSON.parse(readFileSync(SURFACES, "utf8")) as {
      surfaces: Array<{ id: string; carriers: unknown[]; can: { deny: unknown } }>;
    };
    const zed = catalog.surfaces.find((surface) => surface.id === "zed");
    expect(zed).toBeDefined();
    expect(zed!.carriers).toEqual([]);
    expect(zed!.can.deny).toBe("host-only");
    expect(DENYING_CARRIER_TEMPLATES.some((name) => /zed/i.test(name))).toBe(false);
  });

  test("every carrier that runs the gate guards the script's existence", () => {
    // A carrier invokes python3 on a path that lives in the machine canon. When the
    // canon is gone the script is absent, and python exits 2 — which the host reads
    // as a denial (Copilot: "Denied by preToolUse hook: hook exited with code 2"),
    // bricking every tool call. The in-process plugins already treat a missing script
    // as "no gate"; the shell carriers must say so too.
    const GUARD = /\[\s*-f\s+\\?"\$HOME\/\.ai-engineering\/scripts\/checkpoint-gate\.py\\?"\s*\]\s*\|\|\s*exit 0/;
    const problems: string[] = [];
    for (const name of denyingCarrierTemplatesOnDisk()) {
      const content = readFileSync(join(TEMPLATES, name), "utf8");
      if (!/python3/.test(content) || !/checkpoint-gate\.py/.test(content)) continue;
      // Shell carriers guard with a test on the path; the in-process plugins guard
      // with existsSync before spawn. Either way the missing script is no denial.
      if (GUARD.test(content) || /existsSync\(script\)/.test(content)) continue;
      problems.push(`${name}: invokes checkpoint-gate.py without a file guard`);
    }
    expect(problems).toEqual([]);
  });
});
