/**
 * Workflow kit checkpoint 5 — checkpoint guard runs in the chain, without Python.
 */
import { describe, test, expect } from "bun:test";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { embeddedUnder } from "../src/embed.ts";
import { mergeSharedText } from "../src/install.ts";

const ROOT = join(import.meta.dir, "..");
const TEMPLATES = join(ROOT, "templates");
const SURFACES = join(ROOT, "src", "surfaces", "surfaces.json");

function runsChain(content: string): boolean {
  return /ai-eng chain/.test(content) || /\bchain\s*\(/.test(content);
}

function carrierTemplatesOnDisk(): string[] {
  return readdirSync(TEMPLATES).filter((name) => /^(?:settings|plugin)\..+\.tpl$/.test(name));
}

describe("workflow kit — TypeScript checkpoint guard in chain carriers", () => {
  test("every carrier template keeps the chain", () => {
    const problems: string[] = [];
    for (const name of carrierTemplatesOnDisk()) {
      const content = readFileSync(join(TEMPLATES, name), "utf8");
      if (!runsChain(content)) problems.push(`${name}: missing chain`);
    }
    expect(problems).toEqual([]);
  });

  test("no carrier template calls python3", () => {
    const problems: string[] = [];
    for (const name of carrierTemplatesOnDisk()) {
      const content = readFileSync(join(TEMPLATES, name), "utf8");
      if (/python3/.test(content)) problems.push(`${name}: calls python3`);
    }
    expect(problems).toEqual([]);
  });

  test("Zed has no carrier template; suite does not require one", () => {
    expect(carrierTemplatesOnDisk().filter((name) => /zed/i.test(name))).toEqual([]);

    const catalog = JSON.parse(readFileSync(SURFACES, "utf8")) as {
      surfaces: Array<{ id: string; carriers: unknown[]; can: { deny: unknown } }>;
    };
    const zed = catalog.surfaces.find((surface) => surface.id === "zed");
    expect(zed).toBeDefined();
    expect(zed!.carriers).toEqual([]);
    expect(zed!.can.deny).toBe("host-only");
  });

  test("the Python checkpoint script and its test are removed", () => {
    expect(existsSync(join(ROOT, "scripts", "checkpoint-gate.py"))).toBe(false);
    expect(existsSync(join(ROOT, "tests", "test_checkpoint_gate.py"))).toBe(false);
  });

  test("generated assets no longer materialize the Python checkpoint script", () => {
    expect(embeddedUnder("scripts/").has("scripts/checkpoint-gate.py")).toBe(false);
  });

  test("the repository Copilot hook keeps the chain without a Python checkpoint hook", () => {
    const config = JSON.parse(readFileSync(join(ROOT, ".github", "hooks", "ai-eng.json"), "utf8")) as {
      hooks: { preToolUse: Array<{ command: string }> };
    };
    const commands = config.hooks.preToolUse.map((hook) => hook.command);
    expect(commands.some((command) => /ai-eng chain PreToolUse/.test(command))).toBe(true);
    expect(commands.some((command) => /python3/.test(command))).toBe(false);
  });

  test("update retires an old Python checkpoint entry and preserves the user's hook", () => {
    const current = `${JSON.stringify({
      hooks: [
        { command: 'python3 "$HOME/.ai-engineering/scripts/checkpoint-gate.py" --surface cursor' },
        { command: "my-own-hook" },
      ],
    }, null, 2)}\n`;
    const ours = `${JSON.stringify({
      hooks: [{ command: "ai-eng chain PreToolUse --surface cursor" }],
    }, null, 2)}\n`;
    const merged = mergeSharedText(current, ours);

    expect(merged).toHaveProperty("text");
    if (!("text" in merged)) return;
    expect(JSON.parse(merged.text)).toEqual({
      hooks: [
        { command: "my-own-hook" },
        { command: "ai-eng chain PreToolUse --surface cursor" },
      ],
    });
  });
});
