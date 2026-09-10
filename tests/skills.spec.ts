/**
 * Skill canon gates (§11) — every rule is binary; a red here is a red canon.
 *
 * G1  one SKILL.md per skill; zero legacy `*-SKILL.md`.
 * G2  every SKILL.md frontmatter parses (the Zed loader is the oracle):
 *     `---` block, name = folder, folded `>-` description, license SPDX,
 *     no `: ` inside unquoted single-line scalars.
 * G3  zero corpus.md.
 * G4  zero machine paths and no install-path claims; skills are named, never pathed.
 * G5  zero token/length-limit statements.
 * G6  English only (accent-regex over prose; attribution URLs exempt).
 * G7  link integrity inside each skill folder.
 */
import { describe, test, expect } from "bun:test";
import { readdirSync, readFileSync, existsSync, statSync } from "node:fs";
import { join } from "node:path";
import { lifecycleBlock, blockFields, readTriggers } from "../src/spec/triggers.ts";

const SKILLS = join(import.meta.dir, "..", "skills");
const ACCENTS = /[áéíóúñÁÉÍÓÚÑ¿¡]/;
const TOKEN_LIMIT = /(límite de tokens|token limit|token budget for this (file|skill)|keep (it|this) (under|below) \d+\s*(chars|caracteres|characters|tokens)|≤\s*\d+\s*(chars|caracteres|characters)\s*(max|limit|límite)?)/i;
const MACHINE_PATH = /(\/Users\/|\/private\/tmp\/|\/tmp\/ai-eng-home-test|~\/\.agents\/skills)/;

function listSkillDirs(): string[] {
  return readdirSync(SKILLS, { withFileTypes: true })
    .filter((e) => e.isDirectory() && !e.name.startsWith("."))
    .map((e) => join(SKILLS, e.name));
}

function walk(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (statSync(full).isDirectory()) out.push(...walk(full));
    else out.push(full);
  }
  return out;
}

/** Strict frontmatter parser mirroring what surface loaders (Zed) accept. */
function parseFrontmatter(content: string): { fields: Record<string, string>; body: string } {
  const m = /^---\n([\s\S]*?)\n---\n?/.exec(content);
  if (!m) throw new Error("no frontmatter block");
  const fields: Record<string, string> = {};
  let key: string | null = null;
  let folded = "";
  for (const line of m[1]!.split("\n")) {
    if (/^[a-zA-Z_-]+:/.test(line)) {
      if (key && folded) fields[key] = folded;
      const kv = /^([a-zA-Z_-]+):\s*(.*)$/.exec(line)!;
      key = kv[1]!;
      const rest = kv[2] ?? "";
      folded = "";
      if (rest === ">" || rest === ">-" || rest === "|" || rest === "|-") continue;
      if (rest === "") continue;
      // single-line scalar: quoted is always safe; bare must not contain ': '
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
  return { fields, body: content.slice(m[0]!.length) };
}

const SPDX = ["MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "0BSD", "Unlicense", "CC0-1.0", "LicenseRef-Attributed"];

describe("G1 — one SKILL.md per skill", () => {
  test("no legacy *-SKILL.md files anywhere in skills/", () => {
    const offenders: string[] = [];
    for (const dir of listSkillDirs()) {
      for (const f of walk(dir)) {
        if (f.endsWith('-SKILL.md')) offenders.push(f);
      }
    }
    expect(offenders).toEqual([]);
  });

  test("every skill folder has a SKILL.md at its root", () => {
    const missing = listSkillDirs().filter((d) => !existsSync(join(d, "SKILL.md")));
    expect(missing).toEqual([]);
  });
});

describe("G2 — frontmatter parses like Zed loads it", () => {
  test("every SKILL.md: name = folder, license SPDX, folded description", () => {
    const problems: string[] = [];
    for (const dir of listSkillDirs()) {
      const skill = dir.split("/").pop()!;
      const content = readFileSync(join(dir, "SKILL.md"), "utf8");
      try {
        const { fields } = parseFrontmatter(content);
        if (fields["name"] !== skill) problems.push(`${skill}: name=${fields["name"]}`);
        if (!SPDX.includes(fields["license"] ?? "")) problems.push(`${skill}: license=${fields["license"]}`);
        if (!fields["description"] || fields["description"].length < 40) problems.push(`${skill}: description too short`);
      } catch (e) {
        problems.push(`${skill}: ${(e as Error).message}`);
      }
    }
    expect(problems).toEqual([]);
  });
});

describe("G3 — corpus.md is dead", () => {
  test("zero corpus.md files in skills/", () => {
    const offenders = listSkillDirs().flatMap((d) => walk(d)).filter((f) => f.endsWith("corpus.md"));
    expect(offenders).toEqual([]);
  });
  test("no SKILL.md still links a corpus.md", () => {
    const offenders: string[] = [];
    for (const dir of listSkillDirs()) {
      const content = readFileSync(join(dir, "SKILL.md"), "utf8");
      if (/corpus\.md/.test(content)) offenders.push(dir);
    }
    expect(offenders).toEqual([]);
  });
});

describe("G4 — skills are named, never pathed", () => {
  test("no machine paths in any skill markdown", () => {
    const offenders: string[] = [];
    for (const dir of listSkillDirs()) {
      for (const f of walk(dir)) {
        if (!f.endsWith(".md")) continue;
        const content = readFileSync(f, "utf8");
        if (MACHINE_PATH.test(content)) offenders.push(f);
      }
    }
    expect(offenders).toEqual([]);
  });
});

describe("G5 — no token/length-limit statements", () => {
  test("zero limit language in skill markdown", () => {
    const offenders: string[] = [];
    for (const dir of listSkillDirs()) {
      for (const f of walk(dir)) {
        if (!f.endsWith(".md")) continue;
        const content = readFileSync(f, "utf8");
        if (TOKEN_LIMIT.test(content)) offenders.push(f);
      }
    }
    expect(offenders).toEqual([]);
  });
});

describe("G6 — the canon is English", () => {
  test("no accented-Spanish prose in SKILL.md", () => {
    const offenders: string[] = [];
    for (const dir of listSkillDirs()) {
      const { body } = parseFrontmatter(readFileSync(join(dir, "SKILL.md"), "utf8"));
      const hits = body.split("\n").filter((l) => ACCENTS.test(l));
      if (hits.length > 0) offenders.push(`${dir}: ${hits[0]!.slice(0, 80)}`);
    }
    expect(offenders).toEqual([]);
  });
  test("no accented-Spanish prose in reference markdown", () => {
    const offenders: string[] = [];
    for (const dir of listSkillDirs()) {
      for (const f of walk(dir)) {
        const rel = f.slice(dir.length + 1);
        if (!f.endsWith(".md")) continue;
        if (rel === "SKILL.md") continue;
        const content = readFileSync(f, "utf8");
        const hits = content.split("\n").filter((l) => ACCENTS.test(l));
        if (hits.length > 2) offenders.push(`${rel}: ${hits.length} accented lines`);
      }
    }
    expect(offenders).toEqual([]);
  });
});

describe("G7 — links inside each skill resolve", () => {
  test("every relative md/script link in SKILL.md points at an existing file", () => {
    const broken: string[] = [];
    for (const dir of listSkillDirs()) {
      const content = readFileSync(join(dir, "SKILL.md"), "utf8");
      const links = [...content.matchAll(/\]\(([^)#\s]+)\)/g)].map((m) => m[1]!);
      for (const link of links) {
        if (/^[a-z]+:\/\//.test(link) || link.startsWith("/")) continue;
        if (!existsSync(join(dir, link))) broken.push(`${dir.split("/").pop()}: ${link}`);
      }
    }
    expect(broken).toEqual([]);
  });
});

describe("G8 — official names only", () => {
  test("no legacy upstream name in name: field or H1", () => {
    const offenders: string[] = [];
    for (const dir of listSkillDirs()) {
      const content = readFileSync(join(dir, "SKILL.md"), "utf8");
      const firstHeading = /^#\s+(.+)$/m.exec(content)?.[1] ?? "";
      if (/(^|[^-\w])(headstart|handshake|wayfinder|unlazy|read-the-damn-docs|design-orchestrator)([^-\w]|$)/i.test(firstHeading)) {
        offenders.push(`${dir.split("/").pop()}: H1=${firstHeading}`);
      }
    }
    expect(offenders).toEqual([]);
  });
});

// ── G9-G14 · the graph ────────────────────────────────────────────────────────
// Every skill declares its own node in a `## Lifecycle` block, so the graph is the
// union of those blocks and there is no central map to fall out of sync (§20.1).
// The parser is the same one the runtime uses: a second implementation would be a
// second truth.

const LANES = ["light", "standard", "full", "any"];
const TRIGGER_IDS = ["ui", "security", "open-questions", "arch-change", "public-interface"];
/** Declared by every node; the rest of the vocabulary belongs to specific kinds of node. */
const REQUIRED_KEYS = ["Lane", "Writes", "Read by", "Dies", "Next"];
/** The four slot files are shared by design — several nodes write into one milestone
 *  slot (states, evidence), so ownership is exclusive for everything BUT these. */
const SLOTS = ["spec.html", "plan.html", "brainstorm.md", "recap.html"];

function skillName(dir: string): string {
  return dir.split("/").pop()!;
}

function lifecycleFields(dir: string): Record<string, string> {
  const block = lifecycleBlock(readFileSync(join(dir, "SKILL.md"), "utf8"));
  return block ? blockFields(block) : {};
}

describe("G9 — every skill declares its node", () => {
  test("the Lifecycle block carries Lane, Writes, Read by, Dies and Next", () => {
    const problems: string[] = [];
    for (const dir of listSkillDirs()) {
      const fields = lifecycleFields(dir);
      if (Object.keys(fields).length === 0) {
        problems.push(`${skillName(dir)}: no ## Lifecycle block`);
        continue;
      }
      for (const key of REQUIRED_KEYS) {
        if (!fields[key] || fields[key]!.length === 0) problems.push(`${skillName(dir)}: ${key} missing`);
      }
    }
    expect(problems).toEqual([]);
  });
});

describe("G10 — the graph is closed and ends", () => {
  test("Next names real skills, every artifact has one owner, and a terminal node exists", () => {
    const problems: string[] = [];
    const names = new Set(listSkillDirs().map(skillName));
    const owners = new Map<string, string>();
    let terminals = 0;
    for (const dir of listSkillDirs()) {
      const skill = skillName(dir);
      const fields = lifecycleFields(dir);
      const next = fields["Next"];
      if (!next) continue;
      if (next.startsWith("none")) terminals += 1;
      for (const mentioned of next.matchAll(/\bai-[a-z-]+/g)) {
        if (!names.has(mentioned[0])) problems.push(`${skill}: Next names ${mentioned[0]}, which is not a skill`);
      }
      const written = (fields["Writes"] ?? "").split(",")[0]!.trim();
      if (written.length === 0 || written.startsWith("nothing")) continue;
      if (SLOTS.some((slot) => written.endsWith(slot))) continue;
      const previous = owners.get(written);
      if (previous) problems.push(`${written}: owned by ${previous} and by ${skill}`);
      owners.set(written, skill);
    }
    if (terminals === 0) problems.push("no terminal node: the chain never ends");
    expect(problems).toEqual([]);
  });
});

describe("G11 — lanes and triggers come from a closed vocabulary", () => {
  test("every lane is light, standard, full or any; every trigger id is known and has a condition", () => {
    const problems: string[] = [];
    for (const dir of listSkillDirs()) {
      const skill = skillName(dir);
      const fields = lifecycleFields(dir);
      const lanes = (fields["Lane"] ?? "").split(",").map((lane) => lane.trim()).filter((lane) => lane.length > 0);
      if (lanes.length === 0) problems.push(`${skill}: no lane`);
      for (const lane of lanes) if (!LANES.includes(lane)) problems.push(`${skill}: unknown lane "${lane}"`);
      const trigger = fields["Trigger"];
      const kind = fields["Trigger kind"];
      if (trigger && !TRIGGER_IDS.includes(trigger)) problems.push(`${skill}: unknown trigger "${trigger}"`);
      if (trigger && !fields["Trigger when"]) problems.push(`${skill}: trigger "${trigger}" with no condition`);
      if (!trigger && fields["Trigger when"]) problems.push(`${skill}: a condition with no trigger id`);
      if (trigger && kind !== "path" && kind !== "judgment") {
        problems.push(`${skill}: trigger "${trigger}" declares no kind (path or judgment)`);
      }
      if (!trigger && kind) problems.push(`${skill}: a trigger kind with no trigger id`);
      if (trigger && kind === "path") {
        const globs = (fields["Trigger when"] ?? "").split(",").map((glob) => glob.trim()).filter((glob) => glob.length > 0);
        if (globs.length === 0 || globs.some((glob) => !glob.includes("*") && !glob.includes("/"))) {
          problems.push(`${skill}: a path trigger needs globs, not a sentence`);
        }
      }
    }
    expect(problems).toEqual([]);
  });
});

describe("G12 — the human speaks words", () => {
  test("every stop declares its words, what it confirms and the command the agent runs", () => {
    const problems: string[] = [];
    const declared = new Map<string, string>();
    for (const dir of listSkillDirs()) {
      const skill = skillName(dir);
      const fields = lifecycleFields(dir);
      const stop = fields["Stop"];
      if (!stop) continue;
      const previous = declared.get(stop);
      if (previous) problems.push(`stop "${stop}" declared by ${previous} and by ${skill}`);
      declared.set(stop, skill);
      if (!fields["Stop words"]) problems.push(`${stop}: no words the human can say`);
      if (!fields["Stop confirms"]) problems.push(`${stop}: nothing named as confirmed`);
      if (!(fields["Stop runs"] ?? "").includes("ai-eng spec")) problems.push(`${stop}: runs no command`);
    }
    for (const required of ["approve", "close"]) {
      if (!declared.has(required)) problems.push(`no "${required}" stop declared anywhere in the canon`);
    }
    expect(problems).toEqual([]);
  });
});

describe("G13 — the lane is named where the classification happens", () => {
  test("ai-brainstorm routes all three lanes: plan, verify, and research or architect", () => {
    const next = lifecycleFields(join(SKILLS, "ai-brainstorm"))["Next"] ?? "";
    expect(next).toMatch(/\bai-plan\b/);
    expect(next).toMatch(/\bai-verify\b/);
    expect(/\bai-research\b/.test(next) || /\bai-architect\b/.test(next)).toBe(true);
  });
});

describe("G14 — every condition reaches the planner", () => {
  test("each trigger id in the canon is named in ai-plan", () => {
    const plan = readFileSync(join(SKILLS, "ai-plan", "SKILL.md"), "utf8");
    const ids = [...new Set(readTriggers(SKILLS).map((trigger) => trigger.id))];
    expect(ids.length).toBeGreaterThan(0);
    expect(ids.filter((id) => !plan.includes(id))).toEqual([]);
  });
});
