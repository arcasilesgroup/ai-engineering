import { describe, expect, test } from "bun:test";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join, relative, resolve } from "node:path";

const ROOT = join(import.meta.dir, "..");
const SKILLS = join(ROOT, "skills");
const TEMPLATES = join(ROOT, "templates");
const MAIN_REFS = /refs\/heads\/main|origin\/main/;
const FEATURE_PREFIX = /feat\/(?:<[^>]+>|[\w*.-]+)/i;
const DESIGN_SLOTS = /brainstorm\.html|spec\.html|plan\.html|PRD\.html/i;

function listFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? listFiles(path) : [path];
  });
}

function listSkillDocuments(): { name: string; directory: string; file: string }[] {
  return readdirSync(SKILLS, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && !entry.name.startsWith("."))
    .map((entry) => ({
      name: entry.name,
      directory: join(SKILLS, entry.name),
      file: join(SKILLS, entry.name, "SKILL.md"),
    }))
    .filter(({ file }) => existsSync(file));
}

function parseFrontmatter(content: string): Record<string, string> {
  const match = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?/.exec(content);
  if (!match) throw new Error("no frontmatter block");

  const fields: Record<string, string> = {};
  let key: string | null = null;
  let folded = "";
  for (const line of match[1]!.split(/\r?\n/)) {
    if (/^[a-zA-Z_-]+:/.test(line)) {
      if (key && folded) fields[key] = folded;
      const field = /^([a-zA-Z_-]+):\s*(.*)$/.exec(line)!;
      key = field[1]!;
      const value = field[2] ?? "";
      folded = "";
      if (value === ">" || value === ">-" || value === "|" || value === "|-") continue;
      if (value === "") continue;
      fields[key] = value.replace(/^\s*["']|["']$/g, "");
      key = null;
    } else if (/^\s+\S/.test(line) && key) {
      folded += (folded ? " " : "") + line.trim();
    } else if (line.trim()) {
      throw new Error(`unparsable frontmatter line: ${line.slice(0, 60)}`);
    }
  }
  if (key && folded) fields[key] = folded;
  return fields;
}

function relativeMarkdownLinks(content: string): string[] {
  return [...content.matchAll(/\]\(([^)#\s]+)(?:#[^)]*)?\)/g)]
    .map((match) => match[1]!)
    .filter((link) => !/^(?:[a-z][a-z\d+.-]*:|\/|#)/i.test(link));
}

function lintSkill(
  name: string,
  content: string,
  resolvesRelativeLink: (link: string) => boolean,
): string[] {
  const problems: string[] = [];
  let fields: Record<string, string> = {};
  try {
    fields = parseFrontmatter(content);
  } catch (error) {
    problems.push(`frontmatter: ${(error as Error).message}`);
  }

  if (fields.name !== name) problems.push(`name: expected ${name}, received ${fields.name ?? "missing"}`);
  if (!fields.description?.trim()) problems.push("description: missing or empty");
  if (!markdownSection(content, "Lifecycle").trim()) problems.push("lifecycle: missing ## Lifecycle block");

  for (const link of relativeMarkdownLinks(content)) {
    let isResolved = false;
    try {
      isResolved = resolvesRelativeLink(decodeURIComponent(link.split(/[?#]/, 1)[0]!));
    } catch {
      isResolved = false;
    }
    if (!isResolved) problems.push(`link: ${link}`);
  }
  return problems;
}

function markdownSection(content: string, heading: string): string {
  const headingMatch = new RegExp(`^##\\s+${heading.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*$`, "m").exec(content);
  if (!headingMatch) return "";
  const start = headingMatch.index + headingMatch[0].length;
  const nextHeading = /^#{1,2}\s+/m.exec(content.slice(start));
  return content.slice(start, nextHeading ? start + nextHeading.index : undefined);
}

function spikePath(content: string): string {
  const start = content.indexOf("- **Spike**");
  const end = content.indexOf("- **Bounded**", start + 1);
  return start < 0 || end < 0 ? "" : content.slice(start, end);
}

function isMandatoryFeaturePrefix(line: string): boolean {
  if (!FEATURE_PREFIX.test(line)) return false;
  if (/\b(?:need not|not required|not mandatory|optional|any valid|does not have to|doesn't have to)\b/i.test(line)) {
    return false;
  }
  return (
    /\bon\s+(?:the\s+)?branch\s+`?feat\//i.test(line) ||
    /\bon\s+feat\//i.test(line) ||
    /\bwill\s+use\s+for\s+feat\//i.test(line) ||
    /\b(?:must|shall|required|mandatory|always)\b.{0,100}\bfeat\//i.test(line) ||
    /\bbranch(?:es)?\b.{0,60}\b(?:must|required|mandatory|always)\b.{0,60}\bfeat\//i.test(line)
  );
}

describe("CP11 skills lint", () => {
  test("every skills/*/SKILL.md satisfies the frontmatter, Lifecycle, and relative-link contract", () => {
    const problems = listSkillDocuments().flatMap(({ name, directory, file }) => {
      const content = readFileSync(file, "utf8");
      return lintSkill(name, content, (link) => existsSync(resolve(directory, link)))
        .map((problem) => `${name}: ${problem}`);
    });

    expect(problems).toEqual([]);
  });

  test("the lint helper detects a missing field and a broken relative link", () => {
    const fixture = [
      "---",
      "name: fixture",
      "---",
      "",
      "## Lifecycle",
      "Writes: nothing",
      "",
      "[broken](missing.md)",
    ].join("\n");

    expect(lintSkill("fixture", fixture, () => false)).toEqual([
      "description: missing or empty",
      "link: missing.md",
    ]);
  });

  test("skills, templates, and src contain no refs/heads/main or origin/main literals", () => {
    const roots = [join(ROOT, "src"), SKILLS, TEMPLATES];
    const offenders = roots
      .flatMap(listFiles)
      .filter((file) => MAIN_REFS.test(readFileSync(file, "utf8")))
      .map((file) => relative(ROOT, file));

    expect(offenders).toEqual([]);
  });

  test("skills and templates do not require a feat/ branch prefix", () => {
    const offenders = [SKILLS, TEMPLATES]
      .flatMap(listFiles)
      .flatMap((file) =>
        readFileSync(file, "utf8")
          .split(/\r?\n/)
          .filter(isMandatoryFeaturePrefix)
          .map((line) => `${relative(ROOT, file)}: ${line.trim()}`),
      );

    expect(offenders).toEqual([]);
  });

  test("the Direct rhythm has no step invoking ai-brainstorm or creating a worktree", () => {
    const orchestrator = readFileSync(join(SKILLS, "ai-orchestrator", "SKILL.md"), "utf8");
    const direct = markdownSection(orchestrator, "Direct rhythm");
    expect(direct.trim()).not.toBe("");

    const steps = direct.split(/\r?\n/).filter((line) => /^\s*(?:[-*]|\d+[.)])\s+/.test(line));
    const actions = steps.filter((line) => {
      const isExplicitlyProhibited = /\b(?:do not|don't|never|without|no)\b/i.test(line);
      if (isExplicitlyProhibited) return false;
      const invokesBrainstorm =
        /\b(?:run|invoke|call|start|launch|use)\b.{0,40}\b\/?ai-brainstorm\b/i.test(line);
      const createsWorktree =
        /\b(?:create|make|start|open|use|switch to)\b.{0,40}\bworktree\b/i.test(line) ||
        /\bworktree\s+new\b|\bclaude\s+-w\b|\/worktree\b/i.test(line);
      return invokesBrainstorm || createsWorktree;
    });

    expect(actions).toEqual([]);
  });

  test("Direct/light work bypasses the brainstorm gate across both skill contracts", () => {
    const orchestrator = readFileSync(join(SKILLS, "ai-orchestrator", "SKILL.md"), "utf8");
    const brainstorm = readFileSync(join(SKILLS, "ai-brainstorm", "SKILL.md"), "utf8");
    const direct = markdownSection(orchestrator, "Direct rhythm");
    const routing = markdownSection(brainstorm, "Routing");
    const hardGate = /<HARD-GATE>([\s\S]*?)<\/HARD-GATE>/.exec(brainstorm)?.[1] ?? "";
    const description = parseFrontmatter(brainstorm).description;

    expect(direct).toMatch(/no brainstorm/i);
    expect(description).not.toMatch(/before ANY creative work/i);
    expect(description).toMatch(/Do not use as a preflight for Direct\/light work/i);
    expect(routing).toMatch(/Direct\/light[\s\S]*without ai-brainstorm/i);
    expect(hardGate).toMatch(/only to this brainstorm flow/i);
  });

  test("the ai-brainstorm spike path writes no design slots", () => {
    const brainstorm = readFileSync(join(SKILLS, "ai-brainstorm", "SKILL.md"), "utf8");
    const paths = markdownSection(brainstorm, "Three paths (classify out loud before the first question)");
    const spike = spikePath(paths);
    const lightLane = /The path picks the lane[\s\S]*?(?=\n## )/.exec(brainstorm)?.[0] ?? "";

    expect(spike).toContain("No design doc.");
    expect(spike).toContain("output is an answer");
    expect(lightLane.replace(/\s+/g, " ")).toMatch(/on the light lane nothing is written to a slot at all/i);
    expect(brainstorm).toMatch(/Spike and light\/bounded paths write no design slots and do not invoke `ai-orchestrator`/i);
    expect(brainstorm).toMatch(/On light lanes, use the spike answer or approved in-chat design and finish at `ai-verify`/i);
    expect(spike).not.toMatch(DESIGN_SLOTS);
  });

  test("the brainstorm approval handoff matches its Lifecycle routes", () => {
    const brainstorm = readFileSync(join(SKILLS, "ai-brainstorm", "SKILL.md"), "utf8");
    const seam = markdownSection(brainstorm, "The ai-engineering seam");
    const lifecycle = markdownSection(brainstorm, "Lifecycle");
    const lifecycleNext = /^Next:\s*(.+)$/m.exec(lifecycle)?.[1] ?? "";
    const handoffRoutes = Object.fromEntries(
      [...seam.matchAll(/^\s*\|\s*(Architectural|Standard)\s*\|\s*`\/(ai-[\w-]+)`\s*\|$/gim)]
        .map(([, lane, skill]) => [lane!.toLowerCase(), skill!]),
    );
    const lifecycleRoutes = Object.fromEntries(
      [...lifecycleNext.matchAll(/(?:^|;\s*)(ai-[\w-]+)\s+on\s+the\s+(architectural|standard)\s+lane(?=;|$)/gi)]
        .map(([, skill, lane]) => [lane!.toLowerCase(), skill!]),
    );

    expect(handoffRoutes).toEqual({
      architectural: "ai-architect",
      standard: "ai-orchestrator",
    });
    expect(handoffRoutes).toEqual(lifecycleRoutes);
  });
});
