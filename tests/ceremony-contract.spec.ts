// tests/ceremony-contract.spec.ts — the build-by-checkpoints ceremony is only as real
// as the pieces it names. ai-orchestrator and every skill it hands work to cite other
// skills, agents, scripts and templates by name; an installed machine has only what
// init materializes from the embedded canon. This reads the skill text at test time,
// follows each skill ai-orchestrator invokes one level deep, and fails on any citation
// that is missing from the repository or from what init would install. Nothing is
// listed by hand: delete a piece, or stop embedding it, and this goes red (LEARNINGS R7).
//
// One level, not the transitive closure: the ceremony is the orchestrator plus the
// skills it hands a phase to. Following those skills' own references walks into
// general-purpose skills (ai-read-docs, ai-verify) whose prose names third-party files
// and frameworks, which is noise for a contract about this ceremony. The skills the
// level-one skills name are still checked to exist and ship; only their text is not read.
import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, normalize } from "node:path";
import { embeddedTemplate, materializeAgents, materializeScripts, materializeSkills } from "../src/embed.ts";

const REPO = join(import.meta.dir, "..");
const ENTRY_SKILL = "ai-orchestrator";

/** Names that look like skills but are the binary itself (`ai-eng`), owned by package.json. */
const BINARY_NAMES = new Set(Object.keys((JSON.parse(readFileSync(join(REPO, "package.json"), "utf8")) as { bin?: Record<string, string> }).bin ?? {}));

type ScriptCitation = { from: string; token: string };
type Citations = { skills: Set<string>; agents: Set<string>; scripts: ScriptCitation[]; templates: Set<string>; metaNames: Set<string> };

/** What init would install, materialized from the embedded payload the same way installCanon does. */
type Canon = { skillsDir: string; agentsDir: string; scriptsDir: string; template: (name: string) => string | null };

const SKILL_NAME = String.raw`ai-[a-z0-9]+(?:-[a-z0-9]+)*`;
const KEBAB = String.raw`[a-z][a-z0-9]*(?:-[a-z0-9]+)*`;

function isSkillName(name: string): boolean {
  return new RegExp(`^${SKILL_NAME}$`).test(name) && !BINARY_NAMES.has(name);
}

/** Every piece one SKILL.md cites. A skill is a `/ai-x` invocation, an exact `ai-x` code
 *  span, or a path into another skill folder — unless the text declares that name as an
 *  HTML meta field (`<meta name="ai-approved">`), which is an artifact field, not a skill. An agent is what the text launches: `--agent x`,
 *  "the `x` agent", or the code spans right after start/run/launch/resume — unless the
 *  text defines that name as a platform role ("**`research` agent** means …"), which
 *  the host supplies and no agents/*.md file does. A script is a
 *  path with a script extension, in a code span or with a directory, outside src/ and
 *  tests/ (a bare "Next.js" in prose is a framework, not a file). A template is an explicit
 *  templates/*.tpl path, or a `.ai-engineering/<name>.html` design artifact, which init
 *  can only write from its `<name>.html.tpl`. */
function citationsIn(text: string, from: string): Citations {
  const skills = new Set<string>();
  const agents = new Set<string>();
  const templates = new Set<string>();
  const scripts: ScriptCitation[] = [];
  const metaNames = new Set([...text.matchAll(/name="([\w-]+)"/g)].map((match) => match[1] ?? ""));
  const skillPatterns = [
    new RegExp(String.raw`(?<![\w/.-])/(${SKILL_NAME})\b`, "g"),
    new RegExp("`(" + SKILL_NAME + ")`", "g"),
    new RegExp(String.raw`(?:\.\./|skills/)(${SKILL_NAME})/`, "g"),
  ];
  for (const pattern of skillPatterns) {
    for (const match of text.matchAll(pattern)) {
      const name = match[1] ?? "";
      if (isSkillName(name)) skills.add(name);
    }
  }
  const agentNames: string[] = [];
  for (const match of text.matchAll(new RegExp(String.raw`--agent\s+(${KEBAB})`, "g"))) agentNames.push(match[1] ?? "");
  for (const match of text.matchAll(new RegExp("`(" + KEBAB + ")`\\s+agent\\b", "g"))) agentNames.push(match[1] ?? "");
  const launched = new RegExp(String.raw`\b(?:start|run|launch|resume)\s+(?:the\s+)?((?:` + "`" + KEBAB + "`" + String.raw`(?:\s*,\s*|\s+and\s+)?)+)`, "gi");
  for (const match of text.matchAll(launched)) {
    for (const span of (match[1] ?? "").matchAll(new RegExp("`(" + KEBAB + ")`", "g"))) agentNames.push(span[1] ?? "");
  }
  const platformRoles = new Set([...text.matchAll(new RegExp("`(" + KEBAB + ")`(?:\\s+agent)?\\**\\s+means\\b", "g"))].map((match) => match[1] ?? ""));
  for (const name of agentNames) {
    if (name !== "" && !platformRoles.has(name) && !new RegExp(`^${SKILL_NAME}$`).test(name)) agents.add(name);
  }
  for (const match of text.matchAll(/(?<![\w/.:-])((?:[\w.-]+\/)*[\w-]+\.(?:py|sh|mjs|cjs|js|ts))\b/g)) {
    const token = match[1] ?? "";
    const isInCodeSpan = text[(match.index ?? 0) - 1] === "`";
    if (/^(?:src|tests)\//.test(token) || !(token.includes("/") || isInCodeSpan)) continue;
    scripts.push({ from, token });
  }
  for (const match of text.matchAll(/templates\/([\w.-]+\.tpl)\b/g)) templates.add(match[1] ?? "");
  for (const match of text.matchAll(/\.ai-engineering\/([\w-]+\.html)\b/g)) templates.add(`${match[1] ?? ""}.tpl`);
  return { skills, agents, scripts, templates, metaNames };
}

/** Every citation in the entry skill and in each SKILL.md it invokes directly. */
function ceremonyCitations(root: string, entry: string): Citations & { read: string[] } {
  const all: Citations = { skills: new Set([entry]), agents: new Set(), scripts: [], templates: new Set(), metaNames: new Set() };
  const read: string[] = [];
  const absorb = (skill: string): Citations | null => {
    const skillFile = join(root, "skills", skill, "SKILL.md");
    if (read.includes(skill) || !existsSync(skillFile)) return null;
    read.push(skill);
    const found = citationsIn(readFileSync(skillFile, "utf8"), skill);
    for (const name of found.skills) all.skills.add(name);
    for (const name of found.agents) all.agents.add(name);
    for (const name of found.templates) all.templates.add(name);
    for (const name of found.metaNames) all.metaNames.add(name);
    all.scripts.push(...found.scripts);
    return found;
  };
  const invoked = absorb(entry)?.skills ?? new Set<string>();
  for (const skill of invoked) absorb(skill);
  for (const name of all.metaNames) all.skills.delete(name);
  return { ...all, read };
}

/** A script path resolves inside the citing skill first, then from the repository root. */
function resolveScript(root: string, citation: ScriptCitation): string | null {
  const candidates = [normalize(join("skills", citation.from, citation.token)), normalize(citation.token)];
  return candidates.find((candidate) => !candidate.startsWith("..") && existsSync(join(root, candidate))) ?? null;
}

/** One line per cited piece that the repository or the installed canon lacks. */
function ceremonyGaps(root: string, entry: string, canon: Canon): string[] {
  const cited = ceremonyCitations(root, entry);
  const gaps: string[] = [];
  for (const skill of cited.skills) {
    if (!existsSync(join(root, "skills", skill, "SKILL.md"))) gaps.push(`skill ${skill}: no skills/${skill}/SKILL.md`);
    else if (!existsSync(join(canon.skillsDir, skill, "SKILL.md"))) gaps.push(`skill ${skill}: not installed by init`);
  }
  for (const agent of cited.agents) {
    if (!existsSync(join(root, "agents", `${agent}.md`))) gaps.push(`agent ${agent}: no agents/${agent}.md`);
    else if (!existsSync(join(canon.agentsDir, `${agent}.md`))) gaps.push(`agent ${agent}: not installed by init`);
  }
  for (const citation of cited.scripts) {
    const resolved = resolveScript(root, citation);
    if (resolved === null) {
      gaps.push(`script ${citation.token} (cited by ${citation.from}): not in the repository`);
      continue;
    }
    const [area, ...rest] = resolved.split("/");
    const installedDir = area === "skills" ? canon.skillsDir : area === "scripts" ? canon.scriptsDir : null;
    if (installedDir === null || !existsSync(join(installedDir, ...rest))) gaps.push(`script ${resolved}: not installed by init`);
  }
  for (const name of cited.templates) {
    const repoTemplate = join(root, "templates", name);
    if (!existsSync(repoTemplate)) gaps.push(`template ${name}: no templates/${name}`);
    else if (canon.template(name) !== readFileSync(repoTemplate, "utf8")) gaps.push(`template ${name}: not embedded as shipped`);
  }
  return gaps;
}

let canonRoot: string;
let canon: Canon;

beforeAll(() => {
  canonRoot = mkdtempSync(join(tmpdir(), "ai-eng-ceremony-canon-"));
  canon = {
    skillsDir: join(canonRoot, "skills"),
    agentsDir: join(canonRoot, "agents"),
    scriptsDir: join(canonRoot, "scripts"),
    template: (name) => {
      try {
        return embeddedTemplate(name);
      } catch {
        return null;
      }
    },
  };
  materializeSkills(canon.skillsDir);
  materializeAgents(canon.agentsDir);
  materializeScripts(canon.scriptsDir);
});

afterAll(() => rmSync(canonRoot, { recursive: true, force: true }));

describe("ceremony contract — every piece ai-orchestrator cites exists and ships", () => {
  test("the extraction finds the ceremony, not an empty set", () => {
    const cited = ceremonyCitations(REPO, ENTRY_SKILL);
    expect(cited.skills.size).toBeGreaterThanOrEqual(5);
    expect(cited.agents.size).toBeGreaterThanOrEqual(3);
    expect(cited.scripts.length).toBeGreaterThanOrEqual(1);
    expect(cited.templates.size).toBeGreaterThanOrEqual(3);
    // Known pieces of the ceremony, as a floor on the extractor — not the list under test.
    expect([...cited.skills]).toEqual(expect.arrayContaining(["ai-adversarial-loop", "ai-test-planner", "ai-review-ui"]));
    expect([...cited.agents]).toEqual(expect.arrayContaining(["checkpoint-planner", "adversarial-reviewer", "fixer"]));
    expect(cited.scripts.map((citation) => citation.token)).toContain("scripts/checkpoint-gate.py");
  });

  test("every cited skill, agent, script and template is in the repository and in the installed canon", () => {
    expect(ceremonyGaps(REPO, ENTRY_SKILL, canon)).toEqual([]);
  });

  test("a skill citing pieces that do not exist, or are not embedded, fails the contract", () => {
    const fixtureRoot = mkdtempSync(join(tmpdir(), "ai-eng-ceremony-fixture-"));
    try {
      const write = (path: string, body: string): void => {
        mkdirSync(dirname(join(fixtureRoot, path)), { recursive: true });
        writeFileSync(join(fixtureRoot, path), body);
      };
      write(
        "skills/ai-fixture/SKILL.md",
        [
          "Run `/ai-ghost-skill` first, then start `ghost-reviewer`.",
          "Launch `stray-planner` and `ghost-fixer` in parallel.",
          "The hook (`scripts/ghost-gate.py`) blocks the call; write `.ai-engineering/ghost.html`.",
          "Start from `templates/stray.md.tpl`.",
        ].join("\n"),
      );
      // In the fixture repository but never embedded: only the canon check can catch these.
      write("agents/stray-planner.md", "# stray\n");
      write("templates/stray.md.tpl", "stray\n");
      expect(ceremonyGaps(fixtureRoot, "ai-fixture", canon).sort()).toEqual(
        [
          "skill ai-ghost-skill: no skills/ai-ghost-skill/SKILL.md",
          "skill ai-fixture: not installed by init",
          "agent ghost-reviewer: no agents/ghost-reviewer.md",
          "agent stray-planner: not installed by init",
          "agent ghost-fixer: no agents/ghost-fixer.md",
          "script scripts/ghost-gate.py (cited by ai-fixture): not in the repository",
          "template ghost.html.tpl: no templates/ghost.html.tpl",
          "template stray.md.tpl: not embedded as shipped",
        ].sort(),
      );
    } finally {
      rmSync(fixtureRoot, { recursive: true, force: true });
    }
  });
});
