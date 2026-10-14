/**
 * Skill canon gates (§11) — every rule is binary; a red here is a red canon.
 *
 * G1  one SKILL.md per skill; zero `*-SKILL.md` companions.
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
import { lifecycleBlock, blockFields } from "../src/spec/triggers.ts";

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
  test("no *-SKILL.md files anywhere in skills/", () => {
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
        // The kit's style catalog spells proper names (Müller, László). That is not Spanish prose.
        if (rel === "references/style-directions.md") continue;
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
  test("no upstream alias in the name: field or H1", () => {
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
const SLOTS = ["spec.html", "plan.html", "brainstorm.html", "recap.html"];

function skillName(dir: string): string {
  return dir.split("/").pop()!;
}

function lifecycleFields(dir: string): Record<string, string> {
  const block = lifecycleBlock(readFileSync(join(dir, "SKILL.md"), "utf8"));
  return block ? blockFields(block) : {};
}

function markdownSection(content: string, heading: string): string {
  const start = content.indexOf(heading);
  if (start < 0) return "";
  const bodyStart = start + heading.length;
  const nextHeading = /^#{1,3} /m.exec(content.slice(bodyStart));
  return content.slice(bodyStart, nextHeading ? bodyStart + nextHeading.index : undefined);
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
      if (!(fields["Stop runs"] ?? "").trim()) problems.push(`${stop}: runs no command`);
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
    expect(next).toMatch(/\bai-orchestrator\b/);
    expect(next).toMatch(/\bai-verify\b/);
    expect(/\bai-research\b/.test(next) || /\bai-architect\b/.test(next)).toBe(true);
  });
});

describe("G14 — every condition reaches the planner", () => {
  test("no skill still names ai-plan or ai-goal as the feature path", () => {
    const offenders: string[] = [];
    for (const dir of listSkillDirs()) {
      const text = readFileSync(join(dir, "SKILL.md"), "utf8");
      if (/\bai-plan\b|\bai-goal\b/.test(text)) offenders.push(skillName(dir));
    }
    expect(offenders).toEqual([]);
  });
});

// ── Workflow kit · checkpoint 1 ───────────────────────────────────────────────
const WORKFLOW_KIT_SKILLS = [
  "ai-orchestrator",
  "ai-test-planner",
  "ai-prototype",
  "ai-review-ui",
  "ai-adversarial-loop",
  "ai-design-md-planner",
] as const;

const KIT_FORBIDDEN_PATH =
  /CLAUDE\.md|docs\/checkpoints|docs\/PRD\.md|docs\/LEARNINGS\.md|docs\/FILEMAP\.md|docs\/PERMISSIONS\.md|docs\/CHANGELOG\.md/;

describe("workflow kit — six skills ship with valid frontmatter", () => {
  test("U1: each kit skill has SKILL.md with name = folder, license SPDX, folded description", () => {
    const problems: string[] = [];
    for (const skill of WORKFLOW_KIT_SKILLS) {
      const skillFile = join(SKILLS, skill, "SKILL.md");
      if (!existsSync(skillFile)) {
        problems.push(`${skill}: missing SKILL.md`);
        continue;
      }
      try {
        const { fields } = parseFrontmatter(readFileSync(skillFile, "utf8"));
        if (fields["name"] !== skill) problems.push(`${skill}: name=${fields["name"]}`);
        if (!SPDX.includes(fields["license"] ?? "")) problems.push(`${skill}: license=${fields["license"]}`);
        if (!fields["description"] || fields["description"].length < 40) {
          problems.push(`${skill}: description too short`);
        }
      } catch (error) {
        problems.push(`${skill}: ${(error as Error).message}`);
      }
    }
    expect(problems).toEqual([]);
  });

  test("U2: kit skill trees contain no CLAUDE.md or docs/checkpoints|PRD|LEARNINGS|FILEMAP|PERMISSIONS|CHANGELOG path strings", () => {
    const offenders: string[] = [];
    for (const skill of WORKFLOW_KIT_SKILLS) {
      const dir = join(SKILLS, skill);
      if (!existsSync(dir)) {
        offenders.push(`${skill}: skill directory missing`);
        continue;
      }
      for (const file of walk(dir)) {
        const content = readFileSync(file, "utf8");
        if (KIT_FORBIDDEN_PATH.test(content)) offenders.push(file.slice(SKILLS.length + 1));
      }
    }
    expect(offenders).toEqual([]);
  });
});

describe("workflow kit — visual recap is opt-in", () => {
  test("the orchestrator never requires or automatically invokes a recap", () => {
    const orchestratorSkill = readFileSync(join(SKILLS, "ai-orchestrator", "SKILL.md"), "utf8");
    const recapSkill = readFileSync(join(SKILLS, "ai-visual-recap", "SKILL.md"), "utf8");
    const agents = readFileSync(join(SKILLS, "..", "AGENTS.md"), "utf8");
    const agentsTemplate = readFileSync(join(SKILLS, "..", "templates", "AGENTS.md.tpl"), "utf8");
    const prd = readFileSync(join(SKILLS, "..", ".ai-engineering", "PRD.html"), "utf8");
    const blueprint = readFileSync(join(SKILLS, "..", "docs", "blueprint.html"), "utf8");

    const phase3 = markdownSection(orchestratorSkill, "## Phase 3: Wrap-up");
    const appReview = markdownSection(orchestratorSkill, "## Phase 4: Human stop 2, app review");
    const approval = appReview.split("- **Approve:**")[1]?.split("- **Stop here:**")[0] ?? "";
    expect(appReview).toContain("Never invoke `ai-visual-recap` automatically");
    expect(appReview).toContain("Only when the user explicitly invokes `/ai-visual-recap` themselves");
    const rebase = phase3.indexOf("Run `git rebase refs/heads/main`");
    const behaviorGates = phase3.indexOf("rerun affected behavior checks");
    const uiGates = phase3.indexOf("rerun affected UI checks");
    const reviewGate = phase3.indexOf("rerun the affected review gate");
    const appReviewHandoff = phase3.indexOf("Only then proceed to Phase 4");
    expect(rebase).toBeGreaterThanOrEqual(0);
    expect(behaviorGates).toBeGreaterThan(rebase);
    expect(uiGates).toBeGreaterThan(behaviorGates);
    expect(reviewGate).toBeGreaterThan(uiGates);
    expect(appReviewHandoff).toBeGreaterThan(reviewGate);
    const approved = approval.indexOf("lifecycle.app_review: approved");
    const readyToMerge = approval.indexOf("lifecycle.phase: ready-to-merge", approved);
    const mergeCommand = approval.indexOf("ai-eng worktree merge <slug>", readyToMerge);
    expect(approval).toContain("retain the exact full `lifecycle.reviewed_main`");
    expect(approved).toBeGreaterThanOrEqual(0);
    expect(readyToMerge).toBeGreaterThan(approved);
    expect(mergeCommand).toBeGreaterThan(readyToMerge);
    expect(approval).toContain("compare-and-swap transaction");
    expect(appReview).toContain("Never write lifecycle phase `complete`.");
    expect(appReview).toContain("its absence must not delay approval, merge, or worktree removal");
    expect(appReview).not.toContain(
      "follow the repository-owned procedure at `skills/ai-visual-recap/SKILL.md`",
    );
    expect(recapSkill).toContain("manually invoked by the user");
    expect(agents).toContain("optional and never required for merge");
    expect(agentsTemplate).toContain("optional and never required for merge");
    expect(prd).toContain("optional and never required for merge");
    expect(blueprint).toContain("nunca es requisito para merge ni limpieza");
    expect(orchestratorSkill).toContain(
      "Next: none — Phase 4 closes after app review approval; recap is optional and user-invoked.",
    );
    expect(recapSkill).toContain("Start with `templates/recap.html.tpl`");
    expect(recapSkill).toContain("`.ai-engineering/recap.html`");
  });
});

describe("worktree lifecycle — skill preflight contract (checkpoint 3)", () => {
  test("U12: brainstorm and orchestrator use the same read-only local worktree listing before work", () => {
    const cases = [
      {
        skill: "ai-brainstorm",
        heading: "### 0. Check what already exists",
      },
      {
        skill: "ai-orchestrator",
        heading: "## Phase 0: Preflight",
      },
    ];
    const commands: string[] = [];

    for (const { skill, heading } of cases) {
      const text = readFileSync(join(SKILLS, skill, "SKILL.md"), "utf8");
      const preflight = markdownSection(text, heading);
      const command = /`(ai-eng worktree list)`/.exec(preflight)?.[1] ?? "";

      expect(preflight).toMatch(/read.only/i);
      expect(preflight).toMatch(/\blocal\b/i);
      commands.push(command);
    }

    expect(commands).toEqual(["ai-eng worktree list", "ai-eng worktree list"]);
  });

  test("U16: preflights stay local, avoid remote sync and sibling merges, and keep plans in the feature worktree", () => {
    const preflights = [
      { skill: "ai-brainstorm", heading: "### 0. Check what already exists" },
      { skill: "ai-orchestrator", heading: "## Phase 0: Preflight" },
    ];

    for (const { skill, heading } of preflights) {
      const text = readFileSync(join(SKILLS, skill, "SKILL.md"), "utf8");
      const preflight = markdownSection(text, heading);
      expect(preflight).toMatch(/\bcurrent clone\b|\blocal\b/i);
      expect(preflight).toMatch(/(?:never|do not|no)[\s\S]{0,100}(?:fetch|remote sync|sync remote)/i);
      expect(preflight).toMatch(
        /(?:never|do not)[\s\S]{0,100}(?:merge[\s\S]{0,100}unapproved sibling|unapproved sibling[\s\S]{0,100}merge)/i,
      );
    }

    const orchestrator = readFileSync(join(SKILLS, "ai-orchestrator", "SKILL.md"), "utf8");
    const phase1 = markdownSection(orchestrator, "## Phase 1: Plan");
    expect(phase1).toMatch(/(?:write|create)[\s\S]{0,120}checkpoint[\s\S]{0,120}feature worktree/i);
    expect(phase1).toMatch(/(?:plan|checkpoint)[\s\S]{0,160}(?:primary checkout|primary tree)|(?:primary checkout|primary tree)[\s\S]{0,160}(?:plan|checkpoint)/i);
    expect(phase1).toMatch(/(?:never|do not)[\s\S]{0,100}(?:primary checkout|primary tree)/i);
    expect(phase1).toMatch(/(?:never|do not)[\s\S]{0,100}cop(?:y|ied|ying)[\s\S]{0,100}(?:checkpoint|plan|between worktrees|between trees)/i);
  });

  test("U16b: both preflights surface lifecycle approvals and ask the human before continuing", () => {
    const preflights = [
      { skill: "ai-brainstorm", heading: "### 0. Check what already exists" },
      { skill: "ai-orchestrator", heading: "## Phase 0: Preflight" },
    ];

    for (const { skill, heading } of preflights) {
      const text = readFileSync(join(SKILLS, skill, "SKILL.md"), "utf8");
      const preflight = markdownSection(text, heading)
        .replace(/[`*]/g, "")
        .replace(/\s+/g, " ")
        .toLowerCase();
      const listing = preflight.indexOf("ai-eng worktree list");
      expect(listing).toBeGreaterThanOrEqual(0);
      expect(preflight).toMatch(/before deciding whether work may continue/);

      const planPhase = preflight.indexOf("awaiting-plan-approval", listing);
      const planPending = preflight.indexOf("plan_approval: pending", planPhase);
      const appReviewPhase = preflight.indexOf("awaiting-app-review", planPending);
      const appReviewPending = preflight.indexOf("app_review: pending", appReviewPhase);
      const mergeReady = preflight.indexOf("ready-to-merge", appReviewPending);
      const mergeApproved = preflight.indexOf("app_review: approved", mergeReady);
      const planDecision = preflight.indexOf("ask the human to approve, edit, or stop", mergeApproved);
      const appReviewDecision = preflight.indexOf(
        "ask the human to approve, request changes, or stop here",
        planDecision,
      );
      const mergeDecision = preflight.indexOf(
        "ask whether to continue the merge before any merge action",
        appReviewDecision,
      );
      const continueWork = preflight.indexOf(
        skill === "ai-brainstorm"
          ? "a listed worktree with the same slug means resume that feature"
          : "resume it using its exact git-listed path",
        mergeDecision,
      );

      expect(planPhase).toBeGreaterThan(listing);
      expect(planPending).toBeGreaterThan(planPhase);
      expect(appReviewPhase).toBeGreaterThan(planPending);
      expect(appReviewPending).toBeGreaterThan(appReviewPhase);
      expect(mergeReady).toBeGreaterThan(appReviewPending);
      expect(mergeApproved).toBeGreaterThan(mergeReady);
      expect(planDecision).toBeGreaterThan(mergeApproved);
      expect(appReviewDecision).toBeGreaterThan(planDecision);
      expect(mergeDecision).toBeGreaterThan(appReviewDecision);
      expect(continueWork).toBeGreaterThan(mergeDecision);
      expect(preflight).toMatch(/do not reduce these to a generic pending-approval label/);
      expect(preflight).toMatch(/unknown lifecycle state is not approval/);
      if (skill === "ai-orchestrator") {
        const newBranch = preflight.indexOf("only when no matching slug is listed", continueWork);
        const create = preflight.indexOf("ai-eng worktree new", newBranch);
        expect(newBranch).toBeGreaterThan(mergeDecision);
        expect(create).toBeGreaterThan(newBranch);
      }
    }
  });

  test("U24-U27: Phase 3 pins reviewed SHAs before app review and Phase 4 commits approval before CLI merge", () => {
    const orchestrator = readFileSync(join(SKILLS, "ai-orchestrator", "SKILL.md"), "utf8");
    const phase3 = markdownSection(orchestrator, "## Phase 3: Wrap-up")
      .replace(/[`*]/g, "")
      .replace(/\s+/g, " ")
      .toLowerCase();
    const phase4 = markdownSection(orchestrator, "## Phase 4: Human stop 2, app review");
    const approval = phase4.split("- **Approve:**")[1]?.split("- **Stop here:**")[0] ?? "";
    const normalized = approval.replace(/[`*]/g, "").replace(/\s+/g, " ").toLowerCase();
    const mainTip = phase3.indexOf("git rev-parse refs/heads/main");
    const featureTip = phase3.indexOf("git rev-parse refs/heads/feat/<slug>", mainTip);
    const recordReviewedMain = phase3.indexOf("lifecycle.reviewed_main", mainTip);
    const recordReviewedFeature = phase3.indexOf("lifecycle.reviewed_feature", featureTip);
    const awaitingReview = phase3.indexOf("lifecycle.phase to awaiting-app-review", recordReviewedFeature);
    const pendingReview = phase3.indexOf("lifecycle.app_review to pending", awaitingReview);
    const reviewCommit = phase3.indexOf("checkpoint-only commit", pendingReview);
    const approveAppReview = normalized.indexOf("app_review: approved");
    const readyToMerge = normalized.indexOf("phase: ready-to-merge", approveAppReview);
    const approvalCommit = normalized.indexOf("checkpoint-only commit", readyToMerge);
    const mergeCommand = normalized.indexOf("ai-eng worktree merge <slug>", readyToMerge);
    const artifactCommit = phase3.indexOf("commit those artifacts");
    const recordedApprovalSha = normalized.indexOf("reviewed_feature_sha=");

    expect(mainTip).toBeGreaterThanOrEqual(0);
    expect(artifactCommit).toBeGreaterThanOrEqual(0);
    expect(featureTip).toBeGreaterThan(artifactCommit);
    expect(featureTip).toBeGreaterThan(mainTip);
    expect(recordReviewedMain).toBeGreaterThan(mainTip);
    expect(recordReviewedFeature).toBeGreaterThan(featureTip);
    expect(phase3).toMatch(/reviewed_feature[\s\S]{0,120}(?:exact|full) (?:commit )?(?:id|sha)/);
    expect(awaitingReview).toBeGreaterThan(recordReviewedFeature);
    expect(pendingReview).toBeGreaterThan(awaitingReview);
    expect(reviewCommit).toBeGreaterThan(pendingReview);
    expect(approveAppReview).toBeGreaterThanOrEqual(0);
    expect(recordedApprovalSha).toBeGreaterThanOrEqual(0);
    expect(approveAppReview).toBeGreaterThan(recordedApprovalSha);
    expect(readyToMerge).toBeGreaterThan(approveAppReview);
    expect(approvalCommit).toBeGreaterThan(readyToMerge);
    expect(mergeCommand).toBeGreaterThan(approvalCommit);
    expect(normalized).toMatch(/retain the exact (?:full )?lifecycle\.reviewed_main/);
    expect(normalized).toMatch(/retain the exact (?:full )?lifecycle\.reviewed_feature/);
    expect(normalized).toMatch(/reviewed_main/);
    expect(normalized).toMatch(/no custom lock/);
    expect(normalized).toMatch(/preserve the feature worktree/);
    expect(normalized).toMatch(/rerun (?:phase 3|sync)[\s\S]{0,100}(?:gates|review)/);
    expect(normalized).not.toMatch(/\bgit merge\b|\bgit update-ref\b|\bgit worktree rm\b/);
    expect(normalized).not.toContain("phase: complete");
    expect(normalized).not.toContain("commit those artifacts");
  });

  test("U17: Phase 1 initializes lifecycle approval in the selected feature worktree", () => {
    const orchestrator = readFileSync(join(SKILLS, "ai-orchestrator", "SKILL.md"), "utf8");
    const phase1 = markdownSection(orchestrator, "## Phase 1: Plan")
      .replace(/\s+/g, " ")
      .toLowerCase();

    expect(phase1).toContain("selected feature worktree");
    expect(phase1).toContain(".ai-engineering/workflow/checkpoints/<slug>.json");
    expect(phase1).toMatch(/lifecycle[\s\S]{0,100}awaiting-plan-approval/);
    expect(phase1).toMatch(/plan_approval: pending/);
    expect(phase1).toMatch(/app_review: not-started/);
    expect(phase1).toMatch(/reviewed_main: null/);
    expect(phase1).toMatch(/never create a checkpoint plan in the primary checkout or copy any plan between worktrees/);
  });

  test("U20-U22: Phase 3 syncs only a clean feature worktree and fails closed", () => {
    const orchestrator = readFileSync(join(SKILLS, "ai-orchestrator", "SKILL.md"), "utf8");
    const phase3 = markdownSection(orchestrator, "## Phase 3: Wrap-up");
    const normalized = phase3.replace(/[`*_]/g, "").replace(/\s+/g, " ").toLowerCase();
    const dirtyCheck = normalized.indexOf("git status --porcelain --untracked-files=all");
    const localRebase = normalized.indexOf("git rebase refs/heads/main");
    const clearConflict = normalized.indexOf("a clear conflict");
    const afterSync = normalized.indexOf("after a clean rebase or clear resolution", clearConflict);
    const behaviorRerun = normalized.indexOf("rerun affected behavior checks", afterSync);
    const uiRerun = normalized.indexOf("rerun affected ui checks only when the checkpoint has a ui gate", behaviorRerun);
    const reviewRerun = normalized.indexOf("rerun the affected review gate", uiRerun);
    const unclearConflict = normalized.indexOf("if either side's intent is unclear");
    const abortConflict = normalized.indexOf("git rebase --abort first", unclearConflict);
    const verifyConflictRestoration = normalized.indexOf("verify that the original feature branch", abortConflict);
    const blockAfterConflictRestoration = normalized.indexOf(
      "only after abort and restoration are verified, write lifecycle phase: blocked",
      verifyConflictRestoration,
    );
    const failedCheck = normalized.indexOf("on any failed check");
    const abortFailedCheck = normalized.indexOf("abort an active rebase first", failedCheck);
    const verifyFailedCheckRestoration = normalized.indexOf(
      "verify the original branch, feature commit, tree id and clean worktree as in step 3",
      abortFailedCheck,
    );
    const blockAfterFailedCheckRestoration = normalized.indexOf(
      "only after restoration is verified, write lifecycle phase: blocked",
      verifyFailedCheckRestoration,
    );

    expect(dirtyCheck).toBeGreaterThanOrEqual(0);
    expect(localRebase).toBeGreaterThan(dirtyCheck);
    expect(clearConflict).toBeGreaterThanOrEqual(0);
    expect(afterSync).toBeGreaterThan(clearConflict);
    expect(behaviorRerun).toBeGreaterThan(afterSync);
    expect(uiRerun).toBeGreaterThan(behaviorRerun);
    expect(reviewRerun).toBeGreaterThan(uiRerun);
    expect(abortConflict).toBeGreaterThan(unclearConflict);
    expect(verifyConflictRestoration).toBeGreaterThan(abortConflict);
    expect(blockAfterConflictRestoration).toBeGreaterThan(verifyConflictRestoration);
    expect(abortFailedCheck).toBeGreaterThan(failedCheck);
    expect(verifyFailedCheckRestoration).toBeGreaterThan(abortFailedCheck);
    expect(blockAfterFailedCheckRestoration).toBeGreaterThan(verifyFailedCheckRestoration);
    expect(normalized).not.toMatch(/git rebase main\b/);
    expect(phase3).toMatch(/(?:never|do not)[\s\S]{0,120}(?:fetch|remote sync)/i);
    expect(phase3).toMatch(
      /(?:never|do not)[\s\S]{0,120}(?:merge[\s\S]{0,100}unapproved sibling|unapproved sibling[\s\S]{0,100}merge)/i,
    );
    expect(phase3).toMatch(/clear conflict[\s\S]{0,160}resolve[\s\S]{0,120}feature worktree/i);
    expect(phase3).toMatch(/ui checks only when the checkpoint has a ui gate/i);
    expect(phase3).toMatch(/without writing lifecycle state or claiming clean preservation/i);
    expect(phase3).toMatch(/without changing checkpoint state or claiming clean preservation/i);
    expect(phase3).toMatch(/(?:unclear|ambiguous)[\s\S]{0,100}conflict[\s\S]{0,160}(?:git rebase --abort|abort)/i);
    expect(phase3).toMatch(/(?:failed|failing)[\s\S]{0,100}check[\s\S]{0,180}(?:restore|reset|abort)/i);
    expect(phase3).toMatch(/blocked/i);
  });
});
