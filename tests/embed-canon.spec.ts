// tests/embed-canon.spec.ts — the payload walk behind init, update and doctor.
// The binary IS the payload (blueprint 07), so the only interesting questions are
// about disagreement: a canon that is installed but not shipped, shipped but not
// installed, or complete and dirty at the same time. Everything here runs in a
// temp directory: the real canon home is never touched.

import { describe, expect, test, afterEach } from "bun:test";
import { mkdtempSync, mkdirSync, writeFileSync, existsSync, symlinkSync, linkSync, rmSync, readdirSync, readFileSync, readlinkSync, realpathSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, relative, sep } from "node:path";
import {
  embeddedUnder,
  canonSkills,
  canonExtras,
  removeStaleCanonFiles,
  canonDrift,
  materializeSkills,
  materializeAgents,
  embeddedPath,
  embeddedTemplate,
  embeddedChainBundle,
  recordCanonOwnership,
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

describe("the canon sweep — a skill folder ai-eng ships is ai-eng's whole", () => {
  test("every extra inside a shipped folder is stale, edited, added by hand or left by an older release; another skill and a dot entry are not", () => {
    const home = sandbox();
    const folder = skillFolder();
    mkdirSync(join(home, "skills", folder), { recursive: true });
    writeFileSync(join(home, "skills", folder, "renamed-page.md"), "gone from the payload");
    writeFileSync(join(home, "skills", folder, "my-notes.md"), "added by hand");
    mkdirSync(join(home, "skills", "somebody-elses-skill"), { recursive: true });
    writeFileSync(join(home, "skills", "somebody-elses-skill", "SKILL.md"), "mine");
    writeFileSync(join(home, "skills", ".DS_Store"), "noise");

    const { stale, retired, foreign } = canonExtras(home);
    expect(stale).toEqual([`skills/${folder}/my-notes.md`, `skills/${folder}/renamed-page.md`]);
    expect(retired).toEqual([]);
    expect(foreign).toEqual(["skills/somebody-elses-skill"]);
  });

  test("a link inside a shipped folder goes as a link; what it points at is never touched", () => {
    const home = sandbox();
    const folder = skillFolder();
    mkdirSync(join(home, "skills", folder), { recursive: true });
    const target = join(home, "theirs.md");
    writeFileSync(target, "theirs\n");
    symlinkSync(target, join(home, "skills", folder, "linked.md"));

    expect(canonExtras(home).stale).toEqual([`skills/${folder}/linked.md`]);
    expect(removeStaleCanonFiles(home)).toEqual({ removed: [`skills/${folder}/linked.md`], refused: [] });
    expect(existsSync(join(home, "skills", folder, "linked.md"))).toBe(false);
    expect(readFileSync(target, "utf8")).toBe("theirs\n");
  });

  test("the sweep takes every stale file, with or without a record, and the folder it empties", () => {
    const home = sandbox();
    const folder = skillFolder();
    mkdirSync(join(home, "skills", folder, "old"), { recursive: true });
    writeFileSync(join(home, "skills", folder, "old", "orphan.md"), "x");
    writeFileSync(join(home, "skills", folder, "edited-page.md"), "edited by hand");
    mkdirSync(join(home, "skills", "somebody-elses-skill"), { recursive: true });
    writeFileSync(join(home, "skills", "somebody-elses-skill", "SKILL.md"), "mine");

    expect(removeStaleCanonFiles(home)).toEqual({ removed: [`skills/${folder}/edited-page.md`, `skills/${folder}/old/orphan.md`], refused: [] });
    expect(existsSync(join(home, "skills", folder, "old"))).toBe(false);
    expect(existsSync(join(home, "skills", "somebody-elses-skill", "SKILL.md"))).toBe(true);
  });

  test("a skill, agent or script an earlier ai-eng recorded and this binary no longer ships is retired and swept whole", () => {
    const home = sandbox();
    mkdirSync(join(home, "skills", "ai-retired", "references"), { recursive: true });
    writeFileSync(join(home, "skills", "ai-retired", "SKILL.md"), "old skill");
    writeFileSync(join(home, "skills", "ai-retired", "references", "added.md"), "added by hand");
    mkdirSync(join(home, "agents"), { recursive: true });
    writeFileSync(join(home, "agents", "retired-agent.md"), "old agent, edited");
    writeFileSync(join(home, "agents", "my-own-agent.md"), "mine");
    writeFileSync(join(home, CANON_OWNERSHIP_NAME), JSON.stringify({
      files: { "skills/ai-retired/SKILL.md": sha256("old skill"), "agents/retired-agent.md": sha256("old agent") },
    }));

    expect(canonExtras(home).retired).toEqual(["agents/retired-agent.md", "skills/ai-retired"]);
    expect(removeStaleCanonFiles(home)).toEqual({ removed: ["agents/retired-agent.md", "skills/ai-retired"], refused: [] });
    expect(existsSync(join(home, "skills", "ai-retired"))).toBe(false);
    expect(existsSync(join(home, "agents", "retired-agent.md"))).toBe(false);
    expect(readFileSync(join(home, "agents", "my-own-agent.md"), "utf8")).toBe("mine");
  });

  test("a retired folder goes whole, dot entries too: a .DS_Store never leaves it half-removed", () => {
    const home = sandbox();
    mkdirSync(join(home, "skills", "ai-retired", "refs"), { recursive: true });
    writeFileSync(join(home, "skills", "ai-retired", "SKILL.md"), "old skill");
    writeFileSync(join(home, "skills", "ai-retired", ".DS_Store"), "os");
    writeFileSync(join(home, "skills", "ai-retired", "refs", ".DS_Store"), "os");
    writeFileSync(join(home, CANON_OWNERSHIP_NAME), JSON.stringify({ files: { "skills/ai-retired/SKILL.md": sha256("old skill") } }));

    expect(removeStaleCanonFiles(home)).toEqual({ removed: ["skills/ai-retired"], refused: [] });
    expect(existsSync(join(home, "skills", "ai-retired"))).toBe(false);
  });

  test("a dot entry inside a shipped folder that stays is left alone", () => {
    const home = sandbox();
    const folder = skillFolder();
    mkdirSync(join(home, "skills", folder), { recursive: true });
    writeFileSync(join(home, "skills", folder, ".DS_Store"), "os");

    expect(removeStaleCanonFiles(home)).toEqual({ removed: [], refused: [] });
    expect(readFileSync(join(home, "skills", folder, ".DS_Store"), "utf8")).toBe("os");
  });

  test("the record names what is installed now, and keeps naming a retired path still on disk so the next run retries it", () => {
    const home = sandbox();
    mkdirSync(join(home, "skills", "ai-retired"), { recursive: true });
    writeFileSync(join(home, "skills", "ai-retired", "SKILL.md"), "old skill");
    writeFileSync(join(home, CANON_OWNERSHIP_NAME), JSON.stringify({ files: { "skills/ai-retired/SKILL.md": "abc", "skills/ai-gone/SKILL.md": "def" }, unproven: ["x"] }));

    expect(recordCanonOwnership(home)).toBeNull();
    const record = JSON.parse(readFileSync(join(home, CANON_OWNERSHIP_NAME), "utf8")) as { files: Record<string, string>; unproven?: unknown };
    expect(record.files["skills/ai-retired/SKILL.md"]).toBe("abc");
    expect(record.files["skills/ai-gone/SKILL.md"]).toBeUndefined();
    expect(record.unproven).toBeUndefined();
    const [agentKey] = [...embeddedUnder("agents/").keys()];
    expect(record.files[agentKey!]).toBeDefined();
  });

  test("F19: the ownership record replaces its own name: a hard-linked user file keeps its bytes, a link there is refused", () => {
    const home = sandbox();
    const recordPath = join(home, CANON_OWNERSHIP_NAME);
    const userFile = join(home, "my-notes.txt");
    writeFileSync(userFile, "MY PRECIOUS NOTES\n");
    linkSync(userFile, recordPath);

    expect(recordCanonOwnership(home)).toBeNull();
    expect(readFileSync(userFile, "utf8")).toBe("MY PRECIOUS NOTES\n");
    const [shippedPath, shippedRef] = [...canonSkills()][0]!;
    const record = JSON.parse(readFileSync(recordPath, "utf8")) as { files: Record<string, string> };
    expect(record.files[shippedPath]).toBe(sha256(readFileSync(embeddedPath(shippedRef), "utf8")));

    rmSync(recordPath);
    const elsewhere = join(home, "elsewhere.txt");
    writeFileSync(elsewhere, "theirs\n");
    symlinkSync(elsewhere, recordPath);
    expect(recordCanonOwnership(home)).toBe(
      `${recordPath} is a link, not a regular file, or not writable — ownership record not written; a skill ai-eng stops shipping will not be swept`,
    );
    expect(readlinkSync(recordPath)).toBe(elsewhere);
    expect(readFileSync(elsewhere, "utf8")).toBe("theirs\n");
    expect(readdirSync(home).filter((name) => name.endsWith(".tmp"))).toEqual([]);
  });

  test("a record with a key no installer writes is untrusted: nothing is retired, nothing of yours goes", () => {
    for (const key of ["", "agents", "skills", "skills/ai-retired", "skills/../x/y", "agents/../skills"]) {
      const home = sandbox();
      mkdirSync(join(home, "agents"), { recursive: true });
      writeFileSync(join(home, "agents", "my-own-agent.md"), "mine");
      mkdirSync(join(home, "skills", "my-own-skill"), { recursive: true });
      writeFileSync(join(home, "skills", "my-own-skill", "SKILL.md"), "mine");
      writeFileSync(join(home, CANON_OWNERSHIP_NAME), JSON.stringify({ files: { [key]: "abc", "skills/my-own-skill/SKILL.md": "def" } }));

      expect(canonExtras(home).retired).toEqual([]);
      expect(removeStaleCanonFiles(home)).toEqual({ removed: [], refused: [] });
      expect(readFileSync(join(home, "agents", "my-own-agent.md"), "utf8")).toBe("mine");
      expect(readFileSync(join(home, "skills", "my-own-skill", "SKILL.md"), "utf8")).toBe("mine");
    }
  });

  test("materialize gives a hard-linked canon file a name of its own: the other name keeps its bytes", () => {
    const home = sandbox();
    materializeSkills(join(home, "skills"));
    const [path, ref] = [...canonSkills()][0]!;
    const dotfile = join(home, "dotfiles-page.md");
    rmSync(join(home, path));
    writeFileSync(dotfile, "my edited copy\n");
    linkSync(dotfile, join(home, path));

    materializeSkills(join(home, "skills"));

    expect(readFileSync(dotfile, "utf8")).toBe("my edited copy\n");
    expect(readFileSync(join(home, path))).toEqual(readFileSync(embeddedPath(ref)));
  });

  test("a folder that still holds a shipped file is not emptied", () => {
    const home = sandbox();
    materializeSkills(join(home, "skills"));
    const folder = skillFolder();
    writeFileSync(join(home, "skills", folder, "orphan.md"), "x");

    expect(removeStaleCanonFiles(home).removed).toEqual([`skills/${folder}/orphan.md`]);
    expect(existsSync(join(home, "skills", folder))).toBe(true);
    expect(existsSync(join(home, "skills", aSkillPath().slice("skills/".length)))).toBe(true);
  });

  test("materialize rewrites a shipped file the user edited: ai-eng's bytes, always", () => {
    const home = sandbox();
    materializeSkills(join(home, "skills"));
    const [path, ref] = [...canonSkills()][0]!;
    writeFileSync(join(home, path), "hand-edited\n");

    materializeSkills(join(home, "skills"));
    expect(readFileSync(join(home, path))).toEqual(readFileSync(embeddedPath(ref)));
  });
});

describe("materialization never writes through a link (§14.3)", () => {
  const linkedLine = (paths: string[]): string =>
    `⚠ ${paths.length} path(s) where ai-eng installs are links or not its own folders or files — never written through, left as they are (the link and what it points at untouched): ${paths.join(", ")}. Move one aside to let ai-eng install there`;

  test("a linked skill file is refused, its external target keeps its bytes, and the rest of the payload still lands", () => {
    const home = sandbox();
    const external = join(home, "dotfiles", "SKILL.md");
    mkdirSync(join(home, "dotfiles"), { recursive: true });
    writeFileSync(external, "theirs\n");
    const [linkedKey] = [...canonSkills().keys()].filter((key) => key.endsWith("/SKILL.md"));
    const skillsRoot = join(home, "skills");
    const linked = join(skillsRoot, linkedKey!.slice("skills/".length));
    mkdirSync(join(linked, ".."), { recursive: true });
    symlinkSync(external, linked);

    const lines = materializeSkills(skillsRoot);

    expect(lines).toContain(linkedLine([join(realpathSync(skillsRoot), linkedKey!.slice("skills/".length))]));
    expect(readlinkSync(linked)).toBe(external);
    expect(readFileSync(external, "utf8")).toBe("theirs\n");
    for (const [key, ref] of canonSkills()) {
      if (key === linkedKey) continue;
      expect(readFileSync(join(home, key))).toEqual(readFileSync(embeddedPath(ref)));
    }
  });

  test("a linked canon root is refused and nothing is written into the folder it points at", () => {
    const home = sandbox();
    const external = join(home, "elsewhere");
    mkdirSync(external);
    const skillsRoot = join(home, "skills");
    symlinkSync(external, skillsRoot, "dir");

    expect(materializeSkills(skillsRoot)).toEqual([linkedLine([skillsRoot])]);
    expect(readlinkSync(skillsRoot)).toBe(external);
    expect(readdirSync(external)).toEqual([]);
  });

  test("a linked agent file is refused and its external target keeps its bytes", () => {
    const home = sandbox();
    const agentsRoot = join(home, "agents");
    const [agentKey] = [...embeddedUnder("agents/").keys()];
    if (agentKey === undefined) throw new Error("the payload ships no agents");
    const external = join(home, "my-agent.md");
    writeFileSync(external, "mine\n");
    mkdirSync(agentsRoot);
    const linked = join(agentsRoot, agentKey.slice("agents/".length));
    symlinkSync(external, linked);

    expect(materializeAgents(agentsRoot)).toContain(linkedLine([join(realpathSync(agentsRoot), agentKey.slice("agents/".length))]));
    expect(readlinkSync(linked)).toBe(external);
    expect(readFileSync(external, "utf8")).toBe("mine\n");
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

  test("F20: an extra file we do not ship is counted, never silently ignored — stale, with or without a record", () => {
    const home = sandbox();
    materializeSkills(join(home, "skills"));
    writeFileSync(join(home, "skills", skillFolder(), "left-behind.md"), "x");
    expect(canonDrift(home)).toMatchObject({ stale: 1 });

    writeFileSync(join(home, CANON_OWNERSHIP_NAME), JSON.stringify({ files: { "skills/ai-retired/SKILL.md": "abc" } }));
    mkdirSync(join(home, "skills", "ai-retired"));
    writeFileSync(join(home, "skills", "ai-retired", "SKILL.md"), "old");
    expect(canonDrift(home)).toMatchObject({ stale: 2, foreign: 0 });
  });
});
