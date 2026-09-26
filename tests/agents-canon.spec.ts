/**
 * Workflow kit checkpoint 2 — agents canon on disk and mirrored by installCanon.
 *
 * Red until agents/*.md ship and adapters.ts names the agents mirror.
 */
import { afterEach, describe, test, expect } from "bun:test";
import {
  existsSync,
  lstatSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  realpathSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { installAgentsCanon } from "../src/surfaces/adapters.ts";

const ROOT = join(import.meta.dir, "..");
const AGENTS = join(ROOT, "agents");
const ADAPTERS = join(ROOT, "src", "surfaces", "adapters.ts");

const KIT_AGENTS = [
  "checkpoint-planner",
  "adversarial-reviewer",
  "fixer",
  "ui-visual-reviewer",
  "ui-behavior-reviewer",
] as const;

/** Strict frontmatter parser mirroring what surface loaders accept. */
function parseFrontmatter(content: string): Record<string, string> {
  const match = /^---\n([\s\S]*?)\n---\n?/.exec(content);
  if (!match) throw new Error("no frontmatter block");
  const fields: Record<string, string> = {};
  let key: string | null = null;
  let folded = "";
  for (const line of match[1]!.split("\n")) {
    if (/^[a-zA-Z_-]+:/.test(line)) {
      if (key && folded) fields[key] = folded;
      const kv = /^([a-zA-Z_-]+):\s*(.*)$/.exec(line)!;
      key = kv[1]!;
      const rest = kv[2] ?? "";
      folded = "";
      if (rest === ">" || rest === ">-" || rest === "|" || rest === "|-") continue;
      if (rest === "") continue;
      if (!/^\s*["']/.test(rest) && /:\s/.test(rest)) {
        throw new Error(`invalid YAML scalar (unquoted ': ' in "${rest.slice(0, 60)}")`);
      }
      fields[key] = rest.replace(/^\s*["']|["']$/g, "");
      key = null;
    } else if (/^\s+\S/.test(line) && key) {
      folded += (folded ? " " : "") + line.trim();
    } else if (line.trim().length > 0) {
      throw new Error(`unparsable frontmatter line: ${line.slice(0, 60)}`);
    }
  }
  if (key && folded) fields[key] = folded;
  return fields;
}

describe("workflow kit — five agents ship with matching frontmatter", () => {
  test("each kit agent file exists and name equals the filename stem", () => {
    const problems: string[] = [];
    for (const agent of KIT_AGENTS) {
      const agentFile = join(AGENTS, `${agent}.md`);
      if (!existsSync(agentFile)) {
        problems.push(`${agent}: missing agents/${agent}.md`);
        continue;
      }
      try {
        const fields = parseFrontmatter(readFileSync(agentFile, "utf8"));
        if (fields["name"] !== agent) problems.push(`${agent}: name=${fields["name"]}`);
      } catch (error) {
        problems.push(`${agent}: ${(error as Error).message}`);
      }
    }
    expect(problems).toEqual([]);
  });

  test("installCanon source names the agents canon mirror", () => {
    const source = readFileSync(ADAPTERS, "utf8");
    expect(source).toContain(".ai-engineering/agents");
  });
});

describe("installAgentsCanon under AI_ENG_HOME", () => {
  let sandbox: string | undefined;
  let previousHome: string | undefined;

  afterEach(() => {
    if (previousHome === undefined) delete process.env["AI_ENG_HOME"];
    else process.env["AI_ENG_HOME"] = previousHome;
    if (sandbox !== undefined) rmSync(sandbox, { recursive: true, force: true });
    sandbox = undefined;
  });

  function useHome(name: string): string {
    previousHome = process.env["AI_ENG_HOME"];
    sandbox = mkdtempSync(join(tmpdir(), "ai-eng-agents-"));
    const dir = join(sandbox, name);
    mkdirSync(dir, { recursive: true });
    process.env["AI_ENG_HOME"] = dir;
    return dir;
  }

  test("canon holds the five markdown files and ~/.claude/agents is a symlink", () => {
    const base = useHome("symlink");
    // Broken link: existsSync is false, but the path is occupied — install must unlink it.
    mkdirSync(join(base, ".claude"), { recursive: true });
    symlinkSync(join(base, "gone"), join(base, ".claude", "agents"), "dir");

    const lines = installAgentsCanon();
    const canon = join(base, "agents");
    for (const agent of KIT_AGENTS) {
      expect(existsSync(join(canon, `${agent}.md`))).toBe(true);
    }
    const mirror = join(base, ".claude", "agents");
    expect(lstatSync(mirror).isSymbolicLink()).toBe(true);
    expect(realpathSync(mirror)).toBe(realpathSync(canon));
    expect(lines.some((line) => line.includes("Symlink → ~/.claude/agents"))).toBe(true);
  });

  test("real directory mirror gets a copy and does not throw", () => {
    const base = useHome("copy-dir");
    const mirror = join(base, ".claude", "agents");
    mkdirSync(mirror, { recursive: true });
    writeFileSync(join(mirror, "keep.md"), "mine\n");

    expect(() => installAgentsCanon()).not.toThrow();
    for (const agent of KIT_AGENTS) {
      expect(existsSync(join(mirror, `${agent}.md`))).toBe(true);
    }
    expect(lstatSync(mirror).isSymbolicLink()).toBe(false);
    expect(existsSync(join(mirror, "keep.md"))).toBe(true);
  });
});
