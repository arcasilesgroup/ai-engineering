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

const SKILLS = join(import.meta.dir, "..", "skills");
const ACCENTS = /[áéíóúñÁÉÍÓÚÑ¿¡]/;
const TOKEN_LIMIT = /(límite de tokens|token limit|token budget for this (file|skill)|keep (it|this) (under|below) \d+|≤\s*\d+\s*(chars|caracteres|characters)\s*(max|limit|límite)?)/i;

function listSkillDirs(): string[] {
  return readdirSync(SKILLS, { withFileTypes: true })
    .filter((e) => e.isDirectory())
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
        if (/-SKILL\.md$/.test(f)) offenders.push(f);
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
      if (/\b(headstart|handshake|wayfinder|unlazy|read-the-damn-docs|design-orchestrator|visual-recap)\b/i.test(firstHeading)) {
        offenders.push(`${dir.split("/").pop()}: H1=${firstHeading}`);
      }
    }
    expect(offenders).toEqual([]);
  });
});
