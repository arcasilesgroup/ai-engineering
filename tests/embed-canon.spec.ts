// tests/embed-canon.spec.ts — the payload walk behind init, update and doctor.
// The binary IS the payload (blueprint 07), so the only interesting questions are
// about disagreement: a canon that is installed but not shipped, shipped but not
// installed, or complete and dirty at the same time. Everything here runs in a
// temp directory: the real canon home is never touched.

import { describe, expect, test, afterEach } from "bun:test";
import { mkdtempSync, mkdirSync, writeFileSync, existsSync, symlinkSync, rmSync, readdirSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, relative, sep } from "node:path";
import {
  embeddedUnder,
  canonSkills,
  canonExtras,
  removeStaleCanonFiles,
  canonDrift,
  materializeSkills,
  embeddedPath,
  embeddedTemplate,
  embeddedChainBundle,
  CANON_OWNERSHIP_NAME,
} from "../src/embed.ts";
import { sha256 } from "../src/install.ts";

const roots: string[] = [];
const root = join(import.meta.dir, "..");

function filesBelow(directory: string): string[] {
  if (!existsSync(directory)) return [];
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? filesBelow(path) : [path];
  });
}

function sandbox(): string {
  const dir = mkdtempSync(join(tmpdir(), "ai-eng-embed-"));
  roots.push(dir);
  return dir;
}
afterEach(() => {
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

const aSkillPath = (): string => [...canonSkills().keys()][0]!;
const skillFolder = (): string => aSkillPath().split("/")[1]!;

describe("the embedded payload", () => {
  test("every key under a prefix is normalized, so callers never see the ../ the generator writes", () => {
    const templates = embeddedUnder("templates/");
    expect(templates.size).toBeGreaterThan(0);
    for (const key of templates.keys()) {
      expect(key.startsWith("templates/")).toBe(true);
      expect(key.startsWith("..")).toBe(false);
    }
  });

  test("the generated payload embeds every skills asset and no packs or test-only eval fixtures", () => {
    const skillFiles = filesBelow(join(root, "skills")).filter((path) => !path.endsWith(`${sep}.DS_Store`));
    const sourcePaths = skillFiles.map((path) => relative(root, path).split(sep).join("/")).sort();
    const embeddedSkills = embeddedUnder("skills/");
    expect(sourcePaths.length).toBeGreaterThan(0);
    expect([...embeddedSkills.keys()].sort()).toEqual(sourcePaths);
    for (const path of sourcePaths) {
      expect(readFileSync(embeddedPath(embeddedSkills.get(path)!))).toEqual(readFileSync(join(root, path)));
    }
    expect(embeddedUnder("packs/").size).toBe(0);
  });

  test("test-only verification eval fixtures are absent from the generated payload", () => {
    expect(embeddedUnder("packs/verify-tiers/evals/").size).toBe(0);
    expect(embeddedUnder("tests/fixtures/verify-tiers/evals/").size).toBe(0);
  });

  test("verify setup guide paths resolve in the skills inventory and installed payload", () => {
    const canon = canonSkills();
    const guidePath = "skills/ai-verify/VERIFICATION-SETUP-GUIDE.md";
    const guideRef = canon.get(guidePath);
    if (guideRef === undefined) throw new Error("the skills inventory is missing the verify setup guide");
    const guide = readFileSync(embeddedPath(guideRef), "utf8");
    const sourceSkillPath = /^VERIFY=\/path\/to\/(skills\/[^\s]+)$/m.exec(guide)?.[1];
    if (sourceSkillPath === undefined) throw new Error("guide is missing the selected skill source path");
    expect(canon.has(`${sourceSkillPath}/SKILL.md`)).toBe(true);
    expect(guide).toContain('cp -R "$VERIFY" "$SKILLS/"');
    expect(guide).not.toContain("packs/");
    const references = [...guide.matchAll(/`(skills\/[^`]+)`/g)]
      .map(([, path]) => path)
      .filter((path): path is string => path !== undefined && !path.includes("<"));

    expect(references.length).toBeGreaterThan(0);
    for (const path of references) {
      const prefix = path.endsWith("/") ? path : `${path}/`;
      expect([...canon.keys()].some((asset) => asset === path || asset.startsWith(prefix))).toBe(true);
    }
  });

  test("the canon proper is the payload minus the dot-entries that are plugin payload, not skills", () => {
    const everyEmbeddedSkillPath = embeddedUnder("skills/");
    const canon = canonSkills();
    expect(canon.size).toBeGreaterThan(0);
    expect(canon.size).toBeLessThan(everyEmbeddedSkillPath.size);
    for (const key of canon.keys()) expect(key.slice("skills/".length).startsWith(".")).toBe(false);
  });

  test("a template renders its {{vars}} and an unknown name is a loud error, not an empty file", () => {
    const rendered = embeddedTemplate("AGENTS.md.tpl", { version: "9.9.9", commands: "bun test" });
    expect(rendered).toContain("9.9.9");
    expect(rendered).not.toContain("{{version}}");
    expect(() => embeddedTemplate("no-such-template.tpl")).toThrow(/template not embedded/);
  });

  test("the chain bundle ships embedded, so an in-process host never imports from src/", () => {
    const bundle = embeddedChainBundle();
    expect(bundle.length).toBeGreaterThan(1000);
    expect(bundle).toContain("export");
  });

  test("an absolute ref is its own path — round-tripping it through a URL is the Windows ENOENT", () => {
    expect(embeddedPath("/opt/ai-eng/asset.tpl")).toBe("/opt/ai-eng/asset.tpl");
    expect(embeddedPath("C:\\ai-eng\\asset.tpl")).toBe("C:\\ai-eng\\asset.tpl");
    expect(existsSync(embeddedPath("./assets.ts"))).toBe(true);
  });
});

describe("the canon sweep (§14.3 — never delete a file we did not install)", () => {
  test("a renamed asset inside a folder we ship is ours; another skill and a dot entry are not", () => {
    const home = sandbox();
    const folder = skillFolder();
    mkdirSync(join(home, "skills", folder), { recursive: true });
    writeFileSync(join(home, "skills", folder, "renamed-page.md"), "gone from the payload");
    mkdirSync(join(home, "skills", "somebody-elses-skill"), { recursive: true });
    writeFileSync(join(home, "skills", "somebody-elses-skill", "SKILL.md"), "mine");
    writeFileSync(join(home, "skills", ".DS_Store"), "noise");

    const { stale, foreign } = canonExtras(home);
    expect(stale).toEqual([`skills/${folder}/renamed-page.md`]);
    expect(foreign).toEqual(["skills/somebody-elses-skill/SKILL.md"]);
  });

  test("a symlink in the canon home is never ours to delete", () => {
    const home = sandbox();
    const folder = skillFolder();
    mkdirSync(join(home, "skills", folder), { recursive: true });
    symlinkSync("/tmp/ai-eng-not-ours", join(home, "skills", folder, "linked.md"));

    const { stale, foreign } = canonExtras(home);
    expect(stale).toEqual([]);
    expect(foreign).toContain(`skills/${folder}/linked.md`);
  });

  test("the sweep takes a stale file whose recorded hash still matches, and the folder it empties", () => {
    const home = sandbox();
    const folder = skillFolder();
    mkdirSync(join(home, "skills", folder, "old"), { recursive: true });
    writeFileSync(join(home, "skills", folder, "old", "orphan.md"), "x");
    writeFileSync(join(home, CANON_OWNERSHIP_NAME), JSON.stringify({ files: { [`skills/${folder}/old/orphan.md`]: sha256("x") } }));
    mkdirSync(join(home, "skills", "somebody-elses-skill"), { recursive: true });
    writeFileSync(join(home, "skills", "somebody-elses-skill", "SKILL.md"), "mine");

    expect(removeStaleCanonFiles(home)).toEqual({ removed: [`skills/${folder}/old/orphan.md`], kept: [] });
    expect(existsSync(join(home, "skills", folder, "old"))).toBe(false);
    expect(existsSync(join(home, "skills", "somebody-elses-skill", "SKILL.md"))).toBe(true);
  });

  test("F15: a file the user added or edited inside a shipped folder is kept: no recorded hash proves it ours", () => {
    const home = sandbox();
    const folder = skillFolder();
    mkdirSync(join(home, "skills", folder), { recursive: true });
    writeFileSync(join(home, "skills", folder, "my-notes.md"), "mine");
    writeFileSync(join(home, "skills", folder, "renamed-page.md"), "edited by hand");
    writeFileSync(join(home, CANON_OWNERSHIP_NAME), JSON.stringify({ files: { [`skills/${folder}/renamed-page.md`]: sha256("as shipped") } }));

    expect(removeStaleCanonFiles(home)).toEqual({
      removed: [],
      kept: [`skills/${folder}/my-notes.md`, `skills/${folder}/renamed-page.md`],
    });
    expect(readFileSync(join(home, "skills", folder, "my-notes.md"), "utf8")).toBe("mine");
    expect(readFileSync(join(home, "skills", folder, "renamed-page.md"), "utf8")).toBe("edited by hand");
  });

  test("a folder that still holds a shipped file is not emptied", () => {
    const home = sandbox();
    materializeSkills(join(home, "skills"));
    const folder = skillFolder();
    writeFileSync(join(home, "skills", folder, "orphan.md"), "x");
    writeFileSync(join(home, CANON_OWNERSHIP_NAME), JSON.stringify({ files: { [`skills/${folder}/orphan.md`]: sha256("x") } }));

    expect(removeStaleCanonFiles(home).removed).toEqual([`skills/${folder}/orphan.md`]);
    expect(existsSync(join(home, "skills", folder))).toBe(true);
    expect(existsSync(join(home, "skills", aSkillPath().slice("skills/".length)))).toBe(true);
  });
});

describe("workflow kit — embedded payload includes kit skill paths", () => {
  test("the orchestrator and every specialist skill are in the default skills inventory", () => {
    const skillPaths = [...canonSkills().keys()];
    expect(skillPaths.some((path) => path.startsWith("skills/ai-orchestrator/"))).toBe(true);
    expect(skillPaths.some((path) => path.startsWith("skills/ai-design-md-planner/"))).toBe(true);
  });
});

describe("drift is a measurement, not a claim", () => {
  test("a freshly materialized canon is intact: nothing missing, nothing drifted, nothing stale", () => {
    const home = sandbox();
    expect(materializeSkills(join(home, "skills"))[0]).toMatch(/^materialized \d+ assets → /);
    expect(canonDrift(home)).toEqual({ verified: canonSkills().size, drift: 0, missing: 0, stale: 0, foreign: 0 });
  });

  test("a canon can be complete and dirty at once: an edited file counts as drift, a deleted one as missing", () => {
    const home = sandbox();
    materializeSkills(join(home, "skills"));
    const edited = aSkillPath();
    writeFileSync(join(home, edited), "hand-edited\n");
    const drifted = canonDrift(home);
    expect(drifted.drift).toBe(1);
    expect(drifted.verified).toBe(canonSkills().size - 1);

    rmSync(join(home, edited));
    expect(canonDrift(home).missing).toBe(1);
  });

  test("an extra file we do not ship is counted, never silently ignored", () => {
    const home = sandbox();
    materializeSkills(join(home, "skills"));
    mkdirSync(join(home, "skills", skillFolder()), { recursive: true });
    writeFileSync(join(home, "skills", skillFolder(), "left-behind.md"), "x");
    expect(canonDrift(home).stale).toBe(1);
  });
});
