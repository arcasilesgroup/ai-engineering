// The checkpoint guard's refusal contract: every refusal names the checkpoint, the gate
// and the next step in exact words, and every allowed path answers exactly.
import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import { createHash, randomUUID } from "node:crypto";
import { spawnSync } from "node:child_process";
import {
  cpSync,
  existsSync,
  linkSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  realpathSync,
  rmSync,
  statSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { homedir } from "node:os";
import { isAbsolute, join, relative, sep } from "node:path";
import { normalise, type Payload } from "../src/payload.ts";
import { runCheckpointGuard } from "../src/guards/checkpoint.ts";

type Gate = { status: string; attempts: number; findings: string[] };
type Item = {
  id: number;
  title: string;
  goal: string;
  tasks: string[];
  files: string[];
  acceptance: string[];
  verify: string[];
  ui: null;
  status: string;
  changed_files: string[];
  gates: { behavior: Gate; ui: Gate; review: Gate };
};
type Lifecycle = {
  phase: string;
  plan_approval: string;
  app_review: string;
  base_ref: string | null;
  reviewed_base: string | null;
  reviewed_feature: string | null;
};
type Plan = {
  slug: string;
  feature: string;
  summary: string;
  lifecycle: Lifecycle;
  halted: null | { reason: string; checkpoint: number };
  assumptions: string[];
  notes: string[];
  checkpoints: Item[];
};
type Fixture = { root: string; slug: string; planPath: string; folder: string; baseSha: string; featureSha: string; transcriptPath: string };

const FOLDER = ".ai-engineering/workflow/checkpoints";
const ALLOWED = { deny: false } as const;
const SHELL_WRITE = "Checkpoint cannot pass: shell gate does not allow direct Bash writes to checkpoint JSON. Next: use Edit or Write so checkpoint gates are validated.";

let fixtureRoot = "";
let template = "";
let emptyGitConfig = "";
let fixtureIndex = 0;

function git(args: string[], cwd: string): string {
  const env: NodeJS.ProcessEnv = {
    ...process.env,
    GIT_CONFIG_GLOBAL: emptyGitConfig,
    GIT_CONFIG_SYSTEM: emptyGitConfig,
    GIT_CONFIG_NOSYSTEM: "1",
    GIT_TERMINAL_PROMPT: "0",
  };
  delete env.GIT_DIR;
  delete env.GIT_WORK_TREE;
  delete env.GIT_INDEX_FILE;
  const result = spawnSync("git", args, { cwd, env, encoding: "utf8" });
  if (result.status !== 0) throw new Error(`git ${args.join(" ")} failed: ${result.stderr}`);
  return (result.stdout ?? "").trim();
}

beforeAll(() => {
  fixtureRoot = join(import.meta.dir, `.checkpoint-contract-${process.pid}-${randomUUID()}`);
  mkdirSync(fixtureRoot);
  emptyGitConfig = join(fixtureRoot, "empty-git-config");
  writeFileSync(emptyGitConfig, "");
  template = join(fixtureRoot, "template");
  mkdirSync(join(template, ".ai-engineering"), { recursive: true });
  git(["init", "-q", "-b", "main"], template);
  git(["config", "user.name", "Checkpoint Test"], template);
  git(["config", "user.email", "checkpoint@example.invalid"], template);
  git(["config", "commit.gpgsign", "false"], template);
  writeFileSync(join(template, ".ai-engineering", "config.toml"), `[surfaces]\nenabled = ["claude-code"]\n\n[git]\nbase = "main"\n`);
  writeFileSync(join(template, "base.txt"), "base\n");
  git(["add", "."], template);
  git(["commit", "-q", "-m", "base"], template);
  git(["switch", "-q", "-c", "feat/demo"], template);
  writeFileSync(join(template, "feature.txt"), "feature\n");
  git(["add", "feature.txt"], template);
  git(["commit", "-q", "-m", "feature"], template);
});

afterAll(() => {
  if (fixtureRoot) rmSync(fixtureRoot, { recursive: true, force: true });
});

function withFixture(action: (fixture: Fixture) => void): void {
  const root = join(fixtureRoot, `repo-${fixtureIndex++}`);
  cpSync(template, root, { recursive: true });
  const folder = join(root, ...FOLDER.split("/"));
  mkdirSync(folder, { recursive: true });
  const fixture = {
    root,
    slug: "demo",
    folder,
    planPath: join(folder, "demo.json"),
    baseSha: git(["rev-parse", "refs/heads/main"], root),
    featureSha: git(["rev-parse", "refs/heads/feat/demo"], root),
    transcriptPath: join(root, "orchestrator.jsonl"),
  };
  expect(git(["symbolic-ref", "--short", "HEAD"], root)).toBe("feat/demo");
  try {
    action(fixture);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

function gate(status: string, attempts = 0): Gate {
  return { status, attempts, findings: [] };
}

function item(id: number, status: string, behavior: string, ui: string, review: string): Item {
  return {
    id,
    title: `Checkpoint ${id}`,
    goal: `Goal ${id}`,
    tasks: [],
    files: [],
    acceptance: [],
    verify: [],
    ui: null,
    status,
    changed_files: [],
    gates: { behavior: gate(behavior), ui: gate(ui), review: gate(review) },
  };
}

const done = (id: number) => item(id, "passed", "passed", "n/a", "passed");
const open = (id: number) => item(id, "pending", "pending", "n/a", "pending");

function lifecycle(phase = "implementation", overrides: Partial<Lifecycle> = {}): Lifecycle {
  return {
    phase,
    plan_approval: phase === "awaiting-plan-approval" ? "pending" : "approved",
    app_review: phase === "awaiting-app-review" ? "pending" : phase === "ready-to-merge" ? "approved" : "not-started",
    base_ref: null,
    reviewed_base: null,
    reviewed_feature: null,
    ...overrides,
  };
}

function plan(checkpoints: Item[] = [done(1), open(2), open(3)], state = lifecycle(), slug = "demo"): Plan {
  return { slug, feature: "Demo", summary: "Contract fixture", lifecycle: state, halted: null, assumptions: [], notes: [], checkpoints };
}

function reviewed(fixture: Fixture, phase: string, overrides: Partial<Lifecycle> = {}): Lifecycle {
  return lifecycle(phase, { base_ref: "refs/heads/main", reviewed_base: fixture.baseSha, reviewed_feature: fixture.featureSha, ...overrides });
}

function copy<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function save(path: string, value: Plan | string): void {
  writeFileSync(path, typeof value === "string" ? value : JSON.stringify(value));
}

function tool(tool_name: string, tool_input: Record<string, unknown>, extra: Record<string, unknown> = {}): Payload {
  return { tool_name, tool_input, ...extra };
}

function write(path: string, value: Plan | string): Payload {
  return tool("Write", { file_path: path, content: typeof value === "string" ? value : JSON.stringify(value) });
}

function bash(command: string, cwd?: string): Payload {
  return tool("Bash", { command }, cwd === undefined ? {} : { cwd });
}

function marker(id: number, stage: string, slug = "demo"): Payload {
  return tool("Agent", { prompt: `[checkpoint ${slug}#${id} ${stage}]\nDo the work.` });
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function brainstorm(fixture: Fixture, approvedOn = today()): void {
  writeFileSync(
    join(fixture.root, ".ai-engineering", "brainstorm.html"),
    `<!doctype html><html><head><meta name="ai-feature" content="${fixture.slug}"><meta name="ai-approved" content="${approvedOn}"></head><body><div class="meta"><b>complete · ${approvedOn}</b></div></body></html>`,
  );
}

function refused(reason: string) {
  return { deny: true as const, reason };
}

function link(create: () => void): boolean {
  try {
    create();
    return true;
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code ?? "";
    if (["EACCES", "EPERM", "ENOSYS", "ENOTSUP", "EOPNOTSUPP"].includes(code)) {
      console.warn(`SKIP link test: this platform cannot create links (${code})`);
      return false;
    }
    throw error;
  }
}

const run = (fixture: Fixture, payload: Payload) => runCheckpointGuard(payload, fixture.root);

describe("write gate refusals name the checkpoint, the gate and the next step", () => {
  test("checkpoint IDs must run 1, 2, 3 in the proposed plan and in the plan on disk", () => {
    withFixture((fixture) => {
      const gap = refused(`CP3 cannot pass: checkpoint schema IDs in ${fixture.planPath} must be sequential starting at 1. Next: renumber the checkpoints and retry the guarded write.`);
      expect(run(fixture, write(fixture.planPath, plan([done(1), open(3)])))).toEqual(gap);
      save(fixture.planPath, plan([done(1), open(3)]));
      expect(run(fixture, write(fixture.planPath, plan()))).toEqual(gap);
    });
  });

  test("ui and review cannot pass before the gates they depend on", () => {
    withFixture((fixture) => {
      save(fixture.planPath, plan());
      const uiFirst = refused("CP2 cannot pass: ui gate cannot pass before behavior has passed. Next: run the CP2 behavior gate.");
      const reviewFirst = refused("CP2 cannot pass: review gate cannot pass before behavior and ui have passed or ui is n/a. Next: run the CP2 behavior and ui gates.");
      const propose = (behavior: string, ui: string, review: string) =>
        run(fixture, write(fixture.planPath, plan([done(1), item(2, "pending", behavior, ui, review), open(3)])));
      expect(propose("pending", "passed", "pending")).toEqual(uiFirst);
      expect(propose("pending", "n/a", "passed")).toEqual(reviewFirst);
      expect(propose("passed", "pending", "passed")).toEqual(reviewFirst);
      expect(propose("passed", "failed", "passed")).toEqual(reviewFirst);
      expect(propose("passed", "passed", "passed")).toEqual(ALLOWED);
      expect(propose("passed", "n/a", "passed")).toEqual(ALLOWED);
    });
  });

  test("a later checkpoint cannot start or change while an earlier one is open", () => {
    withFixture((fixture) => {
      const outOfOrder = refused("CP3 cannot pass: checkpoint order cannot change while an earlier checkpoint is still open. Next: finish every earlier checkpoint first.");
      const startedBy = (gates: Partial<Record<"behavior" | "ui" | "review", Gate>>) => {
        const third = open(3);
        Object.assign(third.gates, gates);
        return plan([done(1), open(2), third]);
      };
      // A first plan: any sign that CP3 started is refused.
      expect(run(fixture, write(fixture.planPath, startedBy({ review: gate("pending", 1) })))).toEqual(outOfOrder);
      expect(run(fixture, write(fixture.planPath, startedBy({ behavior: gate("failed") })))).toEqual(outOfOrder);
      expect(run(fixture, write(fixture.planPath, startedBy({ behavior: gate("passed") })))).toEqual(outOfOrder);

      // A plan on disk where CP3 already started: CP3 may not move, CP2 may.
      const onDisk = startedBy({ behavior: gate("failed") });
      save(fixture.planPath, onDisk);
      expect(run(fixture, write(fixture.planPath, plan()))).toEqual(outOfOrder);
      const secondMoves = copy(onDisk);
      secondMoves.checkpoints[1]!.gates.behavior.status = "failed";
      expect(run(fixture, write(fixture.planPath, secondMoves))).toEqual(ALLOWED);
    });
  });

  test("a first plan must be approved for implementation against a fresh matching brainstorm", () => {
    withFixture((fixture) => {
      const brainstormPath = join(fixture.root, ".ai-engineering", "brainstorm.html");
      expect(run(fixture, write(fixture.planPath, plan()))).toEqual(refused(
        `Checkpoint demo cannot pass: plan approval cannot read the matching brainstorm (ENOENT: no such file or directory, open '${brainstormPath}'). Next: restore the approved brainstorm and retry the plan write.`,
      ));
      const stale = new Date(Date.now() - 20 * 86_400_000).toISOString().slice(0, 10);
      brainstorm(fixture, stale);
      expect(run(fixture, write(fixture.planPath, plan()))).toEqual(refused(
        "Checkpoint demo cannot pass: plan approval brainstorm approval is expired or future-dated. Next: approve the matching brainstorm within the last 14 days.",
      ));
      brainstorm(fixture);
      const notForImplementation = refused("Checkpoint demo cannot pass: plan approval a first plan must start approved for implementation with no app review. Next: approve the matching brainstorm, then write the implementation plan.");
      expect(run(fixture, write(fixture.planPath, plan(undefined, lifecycle("blocked"))))).toEqual(notForImplementation);
      expect(run(fixture, write(fixture.planPath, plan(undefined, lifecycle("awaiting-plan-approval"))))).toEqual(notForImplementation);
      const unpinned = lifecycle();
      Reflect.deleteProperty(unpinned, "reviewed_base");
      expect(run(fixture, write(fixture.planPath, plan(undefined, unpinned)))).toEqual(notForImplementation);
      expect(run(fixture, write(fixture.planPath, plan()))).toEqual(ALLOWED);
    });
  });

  test("a schema refusal names the checkpoint it found, counting past nine", () => {
    withFixture((fixture) => {
      const eleven = plan([done(1), ...Array.from({ length: 10 }, (_, index) => open(index + 2))]);
      eleven.checkpoints[10]!.gates.behavior.status = "bogus";
      expect(run(fixture, write(fixture.planPath, eleven))).toEqual(refused(
        "CP11 cannot pass: checkpoint schema checkpoint checkpoints[10].gates.behavior.status: is not supported. Next: repair the checkpoint JSON schema and retry the guarded write.",
      ));
      expect(run(fixture, write(fixture.planPath, { ...plan(), checkpoints: [] }))).toEqual(refused(
        "Checkpoint demo cannot pass: checkpoint schema checkpoint checkpoints: must be a non-empty array. Next: repair the checkpoint JSON schema and retry the guarded write.",
      ));
    });
  });

  test("an unreadable plan on disk refuses the write and names the file", () => {
    withFixture((fixture) => {
      save(fixture.planPath, JSON.stringify({ ...plan(), checkpoints: [] }));
      expect(run(fixture, write(fixture.planPath, plan()))).toEqual(refused(
        `Checkpoint demo cannot pass: checkpoint gate cannot read ${fixture.planPath} (checkpoint checkpoints: must be a non-empty array). Next: repair the checkpoint file and retry the guarded write.`,
      ));
    });
  });

  test("a repository whose Git context cannot be read refuses the plan write", () => {
    const missing = join(fixtureRoot, `missing-${randomUUID()}`);
    const result = runCheckpointGuard(write(join(missing, ...FOLDER.split("/"), "demo.json"), plan()), missing);
    expect(result?.deny).toBe(true);
    expect(result?.deny === true ? result.reason : "").toMatch(
      /^Checkpoint demo cannot pass: checkpoint gate cannot detect the repository base \(.+\)\. Next: repair the repository Git context and retry the guarded write\.$/s,
    );
  });

  test("lifecycle transitions outside the allowed set are refused with the transition named", () => {
    withFixture((fixture) => {
      const completed = plan([done(1), done(2), done(3)]);
      save(fixture.planPath, completed);
      expect(run(fixture, write(fixture.planPath, { ...completed, lifecycle: reviewed(fixture, "ready-to-merge") }))).toEqual(refused(
        "Checkpoint demo cannot pass: lifecycle gate checkpoint phase: implementation cannot transition to ready-to-merge. Next: make only an allowed lifecycle transition and retry the guarded write.",
      ));
    });
  });
});

describe("app-review gate freezes the reviewed plan", () => {
  const frozen = refused("Checkpoint demo cannot pass: app-review gate cannot change reviewed plan fields after app review begins. Next: request changes or repeat the app review for the updated plan.");

  function changeTasks(value: Plan): Plan {
    const next = copy(value);
    next.checkpoints[0]!.tasks = ["changed after review"];
    return next;
  }

  test.each([
    ["awaiting-app-review", {}],
    ["ready-to-merge", {}],
    ["blocked", { app_review: "approved" }],
    ["blocked", { app_review: "pending" }],
  ] as const)("a %s plan with app review %o cannot change its tasks", (phase, overrides) => {
    withFixture((fixture) => {
      const current = plan([done(1), done(2), done(3)], reviewed(fixture, phase, overrides));
      save(fixture.planPath, current);
      expect(run(fixture, write(fixture.planPath, changeTasks(current)))).toEqual(frozen);
    });
  });

  test("leaving review for anything but implementation still freezes the plan", () => {
    withFixture((fixture) => {
      const current = plan([done(1), done(2), done(3)], reviewed(fixture, "awaiting-app-review"));
      save(fixture.planPath, current);
      expect(run(fixture, write(fixture.planPath, { ...changeTasks(current), lifecycle: lifecycle("blocked") }))).toEqual(frozen);
    });
  });

  test("before review begins, task changes are allowed in implementation and blocked", () => {
    withFixture((fixture) => {
      const current = plan([done(1), done(2), done(3)]);
      save(fixture.planPath, current);
      expect(run(fixture, write(fixture.planPath, changeTasks(current)))).toEqual(ALLOWED);
      expect(run(fixture, write(fixture.planPath, { ...changeTasks(current), lifecycle: lifecycle("blocked") }))).toEqual(ALLOWED);
      const blocked = { ...current, lifecycle: lifecycle("blocked") };
      save(fixture.planPath, blocked);
      expect(run(fixture, write(fixture.planPath, changeTasks(blocked)))).toEqual(ALLOWED);
    });
  });

  test("runtime checkpoint and gate status may change during review", () => {
    withFixture((fixture) => {
      const current = plan([done(1), done(2), done(3)], reviewed(fixture, "awaiting-app-review"));
      save(fixture.planPath, current);
      const rerun = copy(current);
      rerun.checkpoints[0]!.status = "in_progress";
      rerun.checkpoints[0]!.gates.review.status = "failed";
      expect(run(fixture, write(fixture.planPath, rerun))).toEqual(ALLOWED);
    });
  });

  test("a stale review returning to implementation may carry plan changes", () => {
    withFixture((fixture) => {
      const current = plan([done(1), done(2), done(3)], reviewed(fixture, "awaiting-app-review"));
      git(["switch", "-q", "main"], fixture.root);
      writeFileSync(join(fixture.root, "advanced.txt"), "new base\n");
      git(["add", "advanced.txt"], fixture.root);
      git(["commit", "-q", "-m", "advance base"], fixture.root);
      git(["switch", "-q", "feat/demo"], fixture.root);
      save(fixture.planPath, current);
      expect(run(fixture, write(fixture.planPath, { ...changeTasks(current), lifecycle: lifecycle("implementation") }))).toEqual(ALLOWED);
    });
  });
});

describe("Edit and MultiEdit are checked on the file they would produce", () => {
  const pending = '"behavior":{"status":"pending","attempts":0,"findings":[]}';
  const failed = '"behavior":{"status":"failed","attempts":0,"findings":[]}';
  const cp3Moved = refused("CP3 cannot pass: checkpoint order cannot change while an earlier checkpoint is still open. Next: finish every earlier checkpoint first.");

  test("one edit changes the first match; replace_all and replaceAll change every match", () => {
    withFixture((fixture) => {
      save(fixture.planPath, plan());
      const edit = (extra: Record<string, unknown>) => run(fixture, tool("Edit", { file_path: fixture.planPath, old_string: pending, new_string: failed, ...extra }));
      expect(edit({})).toEqual(ALLOWED);
      expect(edit({ replace_all: false })).toEqual(ALLOWED);
      expect(edit({ replace_all: true })).toEqual(cp3Moved);
      expect(edit({ replaceAll: true })).toEqual(cp3Moved);
      expect(run(fixture, tool("MultiEdit", { file_path: fixture.planPath, edits: [{ old_string: pending, new_string: failed }, { oldString: '"title":"Checkpoint 2"', newString: '"title":"Second"' }] }))).toEqual(ALLOWED);
    });
  });

  test("an edit the tool cannot apply is not the guard's to decide", () => {
    withFixture((fixture) => {
      save(fixture.planPath, plan());
      const edit = (input: Record<string, unknown>) => run(fixture, tool("Edit", { file_path: fixture.planPath, ...input }));
      expect(edit({ old_string: '"absent"', new_string: '"x"' })).toBeUndefined();
      expect(edit({ old_string: "", new_string: "x" })).toBeUndefined();
      expect(edit({ old_string: pending })).toBeUndefined();
      expect(edit({ old_string: ["{"], new_string: "x" })).toBeUndefined();
      const multi = (edits: unknown) => run(fixture, tool("MultiEdit", { file_path: fixture.planPath, edits }));
      expect(multi({})).toBeUndefined();
      expect(multi([null])).toBeUndefined();
      expect(multi([{ old_string: '"absent"', new_string: "x" }, { old_string: pending, new_string: failed }])).toBeUndefined();
      expect(run(fixture, tool("Write", { file_path: fixture.planPath, content: 42 }))).toBeUndefined();
    });
  });
});

describe("writes that reach a checkpoint by another name", () => {
  const alias = (slug: string, path: string) => refused(
    `Checkpoint ${slug} cannot pass: write gate does not allow writing ${FOLDER}/${slug}.json through another path (${path}). Next: edit ${FOLDER}/${slug}.json by that path so checkpoint gates are validated.`,
  );

  test("a hard link and a new file under a linked folder name the checkpoint they reach", () => {
    withFixture((fixture) => {
      save(fixture.planPath, plan());
      const hard = join(fixture.root, "plan-hard.json");
      const plans = join(fixture.root, "plans");
      if (!link(() => {
        linkSync(fixture.planPath, hard);
        symlinkSync(fixture.folder, plans, "dir");
      })) return;
      expect(run(fixture, write(hard, plan()))).toEqual(alias("demo", hard));
      expect(run(fixture, write(join(plans, "new.json"), plan()))).toEqual(alias("new", join(plans, "new.json")));
    });
  });

  test("other files, including non-JSON files in the folder, are not the guard's business", () => {
    withFixture((fixture) => {
      save(fixture.planPath, plan());
      writeFileSync(join(fixture.folder, "notes.md"), "notes\n");
      if (!link(() => linkSync(join(fixture.folder, "notes.md"), join(fixture.root, "notes-link.md")))) return;
      expect(run(fixture, write(join(fixture.root, "notes-link.md"), "x"))).toBeUndefined();
      expect(run(fixture, write(join(fixture.root, "base.txt"), "x"))).toBeUndefined();
      expect(run(fixture, tool("Write", { file_path: 42, content: "x" }))).toBeUndefined();
      rmSync(fixture.folder, { recursive: true });
      expect(run(fixture, write(join(fixture.root, "base.txt"), "x"))).toBeUndefined();
    });
  });

  test("a link loop decides nothing and is not refused", () => {
    withFixture((fixture) => {
      const loop = join(fixture.root, "loop");
      if (!link(() => symlinkSync(loop, loop))) return;
      expect(run(fixture, write(loop, "x"))).toBeUndefined();
    });
  });

  test("a case variant of the folder or file name is the checkpoint only where the filesystem ignores case", () => {
    withFixture((fixture) => {
      const isCaseInsensitive = existsSync(join(fixture.root, ".ai-engineering", "workflow", "Checkpoints"));
      for (const variant of [join(fixture.root, ".ai-engineering", "workflow", "Checkpoints", "new.json"), join(fixture.folder, "NEW.json")]) {
        const result = run(fixture, write(variant, plan()));
        if (isCaseInsensitive) expect(result).toEqual(alias("new", variant));
        else expect(result).toBeUndefined();
      }
    });
  });

  test("a patch to a checkpoint is refused by its canonical and its linked path", () => {
    withFixture((fixture) => {
      save(fixture.planPath, plan());
      if (!link(() => symlinkSync(fixture.folder, join(fixture.root, "plans"), "dir"))) return;
      const linked = join(fixture.root, "plans", "demo.json");
      const patch = (path: string) => `*** Begin Patch\n*** Update File: ${path}\n@@\n-a\n+b\n*** End Patch`;
      expect(run(fixture, normalise({ tool_name: "apply_patch", tool_input: { input: patch(linked) } }))).toEqual(refused(
        `Checkpoint cannot pass: write gate does not accept a patch to ${linked}. Next: edit ${FOLDER}/<slug>.json with the edit or create tool so checkpoint gates are validated.`,
      ));
      expect(run(fixture, bash(`apply_patch <<'EOF'\n${patch(fixture.planPath)}\nEOF`))).toEqual(refused(
        `Checkpoint cannot pass: shell gate does not accept a patch to ${fixture.planPath}. Next: use Edit or Write so checkpoint gates are validated.`,
      ));
      expect(run(fixture, bash(`apply_patch <<'EOF'\n${patch(linked)}\nEOF`))).toEqual(refused(
        `Checkpoint cannot pass: shell gate does not accept a patch to ${linked}. Next: use Edit or Write so checkpoint gates are validated.`,
      ));
      expect(run(fixture, bash(`apply_patch <<'EOF'\n${patch("notes.md")}\nEOF`))).toBeUndefined();
    });
  });
});

describe("implementation markers", () => {
  test("each refusal names the checkpoint, the gate and the next step", () => {
    withFixture((fixture) => {
      save(fixture.planPath, plan());
      expect(run(fixture, marker(2, "deploy"))).toEqual(refused('CP2 cannot pass: checkpoint stage does not recognize "deploy". Next: use tests, implement, behavior, ui, review, or fix.'));
      expect(run(fixture, marker(9, "implement"))).toEqual(refused("CP9 cannot pass: checkpoint order does not exist in demo.json. Next: use an existing checkpoint number."));
      expect(run(fixture, marker(3, "implement"))).toEqual(refused("CP3 cannot pass: checkpoint order cannot start while an earlier checkpoint is still open. Next: finish every earlier checkpoint first."));
      expect(run(fixture, marker(1, "fix"))).toEqual(refused("CP1 cannot pass: checkpoint status has already passed. Next: reopen CP1 with a failing gate before working on it again."));
      expect(run(fixture, marker(2, "ui"))).toEqual(refused('CP2 cannot pass: ui gate needs behavior passed first (behavior is "pending"). Next: run the CP2 behavior gate.'));
      expect(run(fixture, marker(2, "implement"))).toEqual(ALLOWED);

      save(fixture.planPath, plan([done(1), item(2, "pending", "passed", "pending", "pending"), open(3)]));
      expect(run(fixture, marker(2, "review"))).toEqual(refused('CP2 cannot pass: review gate needs behavior passed and ui passed or n/a (behavior="passed", ui="pending"). Next: run the CP2 behavior and ui gates.'));
      save(fixture.planPath, plan([done(1), item(2, "pending", "passed", "passed", "pending"), open(3)]));
      expect(run(fixture, marker(2, "review"))).toEqual(ALLOWED);
    });
  });

  test("the plan must be readable, sequential and approved for implementation", () => {
    withFixture((fixture) => {
      save(fixture.planPath, JSON.stringify({ ...plan(), checkpoints: [] }));
      expect(run(fixture, marker(2, "implement"))).toEqual(refused(
        `CP2 cannot pass: checkpoint gate cannot read ${fixture.planPath} (checkpoint checkpoints: must be a non-empty array). Next: repair the checkpoint file and retry the marked task.`,
      ));
      save(fixture.planPath, plan([done(1), open(3)]));
      expect(run(fixture, marker(3, "implement"))).toEqual(refused(
        `CP3 cannot pass: checkpoint schema IDs in ${fixture.planPath} must be sequential starting at 1. Next: renumber the checkpoints and retry the guarded write.`,
      ));
      save(fixture.planPath, plan(undefined, reviewed(fixture, "awaiting-app-review")));
      expect(run(fixture, marker(2, "implement"))).toEqual(refused(
        "CP2 cannot pass: plan approval gate implementation is not authorized by the lifecycle approval. Next: approve the plan before starting checkpoint work.",
      ));
    });
  });

  test("only a text prompt can carry a marker", () => {
    withFixture((fixture) => {
      save(fixture.planPath, "{ malformed");
      expect(run(fixture, tool("Agent", { prompt: ["[checkpoint demo#2 implement]"] }))).toBeUndefined();
    });
  });
});

describe("Bash writes into the checkpoint folder", () => {
  test("a named write is refused with the Edit/Write next step", () => {
    withFixture((fixture) => {
      expect(run(fixture, bash(`printf x > ${FOLDER}/demo.json`))).toEqual(refused(SHELL_WRITE));
    });
  });

  test.each([
    ["a nested subshell", `( (cd ${FOLDER} && printf x > demo.json) )`],
    ["a quoted cd", `cd "${FOLDER}" && printf x > demo.json`],
    ["an environment assignment before cd", `PLANS=x cd ${FOLDER} && printf x > demo.json`],
    ["a cd option", `cd -P ${FOLDER} && printf x > demo.json`],
    ["sed --in-place=", `cd ${FOLDER} && sed --in-place=.bak 's/a/b/' demo.json`],
    ["cd - then a write naming the folder", "cd - && printf x > checkpoints/demo.json"],
    ["popd with nothing pushed", `cd ${FOLDER} && popd && printf x > demo.json`],
    ["truncate after cd", `cd ${FOLDER} && truncate -s 0 demo.json`],
    ["combined sed flags ending in i", `cd ${FOLDER} && sed -ni 's/a/b/' demo.json`],
    ["json.tool reading an option-named file and writing the plan after --", `python3 -m json.tool -- --sort-keys ${FOLDER}/demo.json > /dev/null`],
    ["a ~user cd, then a write naming the folder", "cd ~nobody && printf x > checkpoints/demo.json"],
    ["a dash-named interpreter", `my-python3 -m json.tool ${FOLDER}/demo.json > /dev/null`],
    ["a versioned interpreter", `python3.11 -m json.tool ${FOLDER}/demo.json > /dev/null`],
    ["python -c, not json.tool", `python3 -c json.tool ${FOLDER}/demo.json > /dev/null`],
    ["another python module", `python3 -m pickletools ${FOLDER}/demo.json > /dev/null`],
  ])("refuses %s", (_name, command) => {
    withFixture((fixture) => {
      save(fixture.planPath, plan());
      expect(run(fixture, bash(command))).toEqual(refused(SHELL_WRITE));
    });
  });

  test.each([
    ["an option that is not an operand", `cd ${FOLDER} && rm -f ../../../notes.txt`],
    ["sed without in-place", `cd ${FOLDER} && sed -n p demo.json`],
    ["grep -i", `cd ${FOLDER} && grep -i x demo.json`],
    ["cp out of the folder", `cd ${FOLDER} && cp demo.json other.json ../../../backup/`],
    ["an empty redirection target", `cd ${FOLDER} && printf x > ""`],
    ["json.tool by full interpreter path", `/usr/bin/python3 -m json.tool ${FOLDER}/demo.json > /dev/null`],
    ["json.tool under python", `python -m json.tool ${FOLDER}/demo.json > /dev/null`],
    ["json.tool after --", `python3 -m json.tool -- ${FOLDER}/demo.json > /dev/null`],
    ["a cd the guard cannot follow, then one it can", `cd "$X" && cd .ai-engineering && printf x > notes.txt`],
    ["an interpreter outside the folder", `python3 -c "print(1)"`],
    ["an interpreter after a cd the guard cannot follow", `cd "$X" && python3 -c "print(1)"`],
    ["a bare cd home", "cd && printf x > notes.txt"],
    ["a trailing separator", "echo done;"],
    ["a sed script containing -i", `cd ${FOLDER} && sed 's/a-i/b/' demo.json`],
  ])("allows %s", (_name, command) => {
    withFixture((fixture) => {
      save(fixture.planPath, plan());
      expect(run(fixture, bash(command))).toBeUndefined();
    });
  });

  test("json.tool inside the folder reads only checkpoint files", () => {
    withFixture((fixture) => {
      save(fixture.planPath, plan());
      expect(run(fixture, bash("python3 -m json.tool ../../../base.txt > /dev/null", fixture.folder))).toEqual(refused(SHELL_WRITE));
      expect(run(fixture, bash('python3 -m json.tool "$PLAN" > /dev/null', fixture.folder))).toEqual(refused(SHELL_WRITE));
      expect(run(fixture, tool("Bash", {}))).toBeUndefined();
    });
  });

  test("links, spaces and ~ paths are followed to the folder", () => {
    withFixture((fixture) => {
      save(fixture.planPath, plan());
      if (!link(() => {
        symlinkSync(fixture.folder, join(fixture.root, "plan dir"), "dir");
        symlinkSync(fixture.folder, join(fixture.root, "plans"), "dir");
      })) return;
      expect(run(fixture, bash(`cd "plan dir" && printf x > demo.json`))).toEqual(refused(SHELL_WRITE));
      expect(run(fixture, bash(`cd 'plan dir' && printf x > demo.json`))).toEqual(refused(SHELL_WRITE));
      expect(run(fixture, bash(`cd "$X" && printf x > ${join(fixture.root, "plans", "demo.json")}`))).toEqual(refused(SHELL_WRITE));
      mkdirSync(join(fixture.folder, "a~b"));
      expect(run(fixture, bash("cd plans/a~b/.. && printf x > demo.json"))).toEqual(refused(SHELL_WRITE));
      // A `~/` path exists only when the folder sits under the home directory: across Windows
      // drives `relative` answers an absolute path. The shell spells the rest with `/`.
      const fromHome = relative(homedir(), fixture.folder).split(sep).join("/");
      if (fromHome.startsWith("..") || isAbsolute(fromHome)) return;
      expect(run(fixture, bash(`cd ~/${fromHome} && printf x > demo.json`))).toEqual(refused(SHELL_WRITE));
      expect(run(fixture, bash(`cd ~ && cd ${fromHome} && printf x > demo.json`))).toEqual(refused(SHELL_WRITE));
      const linkedFromHome = relative(homedir(), join(fixture.root, "plans", "demo.json")).split(sep).join("/");
      expect(run(fixture, bash(`cd "$X" && printf x > ~/${linkedFromHome}`))).toEqual(refused(SHELL_WRITE));
    });
  });

  test("a guard that cannot decide denies", () => {
    const missing = join(fixtureRoot, `missing-${randomUUID()}`);
    const result = runCheckpointGuard(bash("echo hi"), missing);
    expect(result?.deny === true ? result.reason : "").toMatch(
      /^Checkpoint cannot pass: checkpoint gate could not decide safely \(.+\)\. Next: repair the checkpoint guard input and retry\.$/s,
    );
  });
});

describe("Stop gate", () => {
  function transcript(fixture: Fixture, text = `{"name":"Skill","input":{"skill":"ai-orchestrator"}} read ${FOLDER}/demo.json\n`): void {
    writeFileSync(fixture.transcriptPath, text);
  }

  function stop(fixture: Fixture, session: unknown = randomUUID(), extra: Record<string, unknown> = {}): Payload {
    const payload: Record<string, unknown> = { tool_name: "", tool_input: {}, hook_event_name: "Stop", _event: "Stop", session_id: session, transcript_path: fixture.transcriptPath, stop_reason: "end_turn", ...extra };
    return payload as Payload;
  }

  const midway = () => plan([done(1), item(2, "pending", "passed", "n/a", "failed"), item(3, "pending", "failed", "pending", "pending")]);

  function stopRefusal(fixture: Fixture): { deny: true; reason: string } {
    const path = join(realpathSync(fixture.root), ...FOLDER.split("/"), "demo.json");
    return refused(
      `Checkpoint cannot pass: Stop gate demo CP2 Checkpoint 2: gates not yet proven (review=failed) at ${path}; demo CP3 Checkpoint 3: gates not yet proven (behavior=failed, ui=pending, review=pending) at ${path}. Continue the checkpoint loop; if a human must take over, record halted with its reason and checkpoint. Next: continue the loop or set the top-level halted reason before stopping.`,
    );
  }

  function counterFolder(fixture: Fixture): string {
    return join(fixture.root, ".ai-engineering", "cache", "checkpoint-stop");
  }

  function counterFile(fixture: Fixture, session: string): string {
    return join(counterFolder(fixture), `${createHash("sha256").update(session).digest("hex")}.txt`);
  }

  test("the refusal lists every open gate of every started checkpoint", () => {
    withFixture((fixture) => {
      transcript(fixture);
      save(fixture.planPath, midway());
      expect(run(fixture, stop(fixture))).toEqual(stopRefusal(fixture));
      expect(run(fixture, stop(fixture, randomUUID(), { _event: undefined }))).toEqual(stopRefusal(fixture));
      expect(run(fixture, stop(fixture, randomUUID(), { hook_event_name: undefined }))).toEqual(stopRefusal(fixture));
      expect(run(fixture, stop(fixture, randomUUID(), { stop_reason: "user_interrupt" }))).toEqual(ALLOWED);
      save(fixture.planPath, { ...midway(), halted: { reason: "", checkpoint: 2 } });
      expect(run(fixture, stop(fixture))).toEqual(stopRefusal(fixture));
      save(fixture.planPath, plan([done(1), done(2), done(3)]));
      expect(run(fixture, stop(fixture))).toEqual(ALLOWED);
    });
  });

  test("only a transcript that started the orchestrator on this plan is held", () => {
    withFixture((fixture) => {
      save(fixture.planPath, midway());
      expect(run(fixture, stop(fixture, randomUUID(), { transcript_path: undefined }))).toEqual(ALLOWED);
      expect(run(fixture, stop(fixture))).toEqual(ALLOWED);
      transcript(fixture, `{"skill" : "ai-orchestrator"} ${FOLDER}/demo.json`);
      expect(run(fixture, stop(fixture))).toEqual(stopRefusal(fixture));
      transcript(fixture, `<command-name>/ai-orchestrator</command-name> ${FOLDER}/demo.json`);
      expect(run(fixture, stop(fixture))).toEqual(stopRefusal(fixture));
      transcript(fixture, `{"skill":"ai-orchestrator"} ${FOLDER}/other.json`);
      expect(run(fixture, stop(fixture))).toEqual(ALLOWED);
    });
  });

  test("plans are checked in name order, and an unreadable plan names its file", () => {
    withFixture((fixture) => {
      const root = realpathSync(fixture.root);
      transcript(fixture, `{"skill":"ai-orchestrator"} ${FOLDER}/beta.json ${FOLDER}/alpha.json`);
      for (const slug of ["beta", "alpha"]) {
        save(join(fixture.folder, `${slug}.json`), plan([done(1), item(2, "pending", "failed", "n/a", "pending")], lifecycle(), slug));
      }
      const path = (slug: string) => join(root, ...FOLDER.split("/"), `${slug}.json`);
      expect(run(fixture, stop(fixture))).toEqual(refused(
        `Checkpoint cannot pass: Stop gate alpha CP2 Checkpoint 2: gates not yet proven (behavior=failed, review=pending) at ${path("alpha")}; beta CP2 Checkpoint 2: gates not yet proven (behavior=failed, review=pending) at ${path("beta")}. Continue the checkpoint loop; if a human must take over, record halted with its reason and checkpoint. Next: continue the loop or set the top-level halted reason before stopping.`,
      ));
      save(join(fixture.folder, "alpha.json"), JSON.stringify({ ...plan(undefined, lifecycle(), "alpha"), checkpoints: [] }));
      expect(run(fixture, stop(fixture))).toEqual(refused(
        `Checkpoint alpha cannot pass: Stop gate cannot validate ${path("alpha")} (checkpoint checkpoints: must be a non-empty array). Next: repair the checkpoint JSON before ending the turn.`,
      ));
      save(join(fixture.folder, "alpha.json"), plan([done(1), open(3)], lifecycle(), "alpha"));
      expect(run(fixture, stop(fixture))).toEqual(refused(
        `CP3 cannot pass: checkpoint schema IDs in ${path("alpha")} must be sequential starting at 1. Next: renumber the checkpoints and retry the guarded write.`,
      ));
    });
  });

  test("a corrupt checkpoint cannot hold a continuing turn forever: it is counted like an open gate", () => {
    // Exit 2 on Stop makes Claude continue. A corrupt checkpoint the agent is not allowed
    // to edit would otherwise refuse every Stop; continuing, it is bounded by the counter.
    withFixture((fixture) => {
      const path = join(realpathSync(fixture.root), ...FOLDER.split("/"), "alpha.json");
      transcript(fixture, `{"skill":"ai-orchestrator"} ${FOLDER}/alpha.json`);
      save(join(fixture.folder, "alpha.json"), JSON.stringify({ ...plan(undefined, lifecycle(), "alpha"), checkpoints: [] }));
      expect(run(fixture, stop(fixture))).toEqual(refused(
        `Checkpoint alpha cannot pass: Stop gate cannot validate ${path} (checkpoint checkpoints: must be a non-empty array). Next: repair the checkpoint JSON before ending the turn.`,
      ));
      const session = randomUUID();
      for (let attempt = 0; attempt < 3; attempt++) {
        const result = run(fixture, stop(fixture, session, { stop_hook_active: true }));
        expect(result?.deny === true ? result.reason : "").toContain(`alpha: cannot validate ${path}`);
      }
      expect(run(fixture, stop(fixture, session, { stop_hook_active: true }))).toEqual(ALLOWED);
    });
  });

  test("a corrupt checkpoint does not hide another checkpoint's open gates", () => {
    withFixture((fixture) => {
      transcript(fixture, `{"skill":"ai-orchestrator"} ${FOLDER}/alpha.json ${FOLDER}/beta.json`);
      save(join(fixture.folder, "alpha.json"), JSON.stringify({ ...plan(undefined, lifecycle(), "alpha"), checkpoints: [] }));
      save(join(fixture.folder, "beta.json"), plan([done(1), item(2, "pending", "failed", "n/a", "pending")], lifecycle(), "beta"));
      const result = run(fixture, stop(fixture, randomUUID(), { stop_hook_active: true }));
      const reason = result?.deny === true ? result.reason : "";
      expect(reason).toContain("alpha: cannot validate");
      expect(reason).toContain("beta CP2 Checkpoint 2: gates not yet proven (behavior=failed, review=pending)");
    });
  });

  test("open gates are not a fault: stop_hook_active alone does not let the stop through", () => {
    withFixture((fixture) => {
      transcript(fixture);
      save(fixture.planPath, midway());
      expect(run(fixture, stop(fixture, randomUUID(), { stop_hook_active: true }))).toEqual(stopRefusal(fixture));
    });
  });

  test("no checkpoint folder allows; a folder that cannot be listed refuses", () => {
    withFixture((fixture) => {
      transcript(fixture);
      rmSync(fixture.folder, { recursive: true });
      expect(run(fixture, stop(fixture))).toEqual(ALLOWED);
      writeFileSync(fixture.folder, "not a folder");
      const result = run(fixture, stop(fixture));
      const folder = join(realpathSync(fixture.root), ...FOLDER.split("/"));
      expect(result?.deny === true ? result.reason : "").toMatch(new RegExp(
        `^Checkpoint cannot pass: Stop gate cannot list ${folder.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")} \\(ENOTDIR.*\\)\\. Next: restore access to the checkpoint directory before stopping\\.$`, "s",
      ));
    });
  });

  test("a repository that cannot be resolved refuses the Stop", () => {
    const missing = join(fixtureRoot, `missing-${randomUUID()}`);
    const result = runCheckpointGuard({ tool_name: "", tool_input: {}, hook_event_name: "Stop", _event: "Stop" }, missing);
    expect(result?.deny === true ? result.reason : "").toMatch(
      /^Checkpoint cannot pass: Stop gate cannot resolve the repository \(.+\)\. Next: return to the repository and retry the Stop event\.$/s,
    );
  });

  test("the consecutive-stop counter is one private file per session, cleared once gates close", () => {
    withFixture((fixture) => {
      transcript(fixture);
      save(fixture.planPath, midway());
      const session = `count-${randomUUID()}`;
      expect(run(fixture, stop(fixture, session))).toEqual(stopRefusal(fixture));
      const counter = counterFile(fixture, session);
      expect(readdirSync(counterFolder(fixture))).toEqual([counter.slice(counterFolder(fixture).length + 1)]);
      expect(readFileSync(counter, "utf8")).toBe("1");
      // Windows keeps no owner/group/other bits: every file reports 0o666 there.
      if (process.platform !== "win32") expect(statSync(counter).mode & 0o777).toBe(0o600);
      save(fixture.planPath, plan([done(1), done(2), done(3)]));
      expect(run(fixture, stop(fixture, session))).toEqual(ALLOWED);
      expect(readdirSync(counterFolder(fixture))).toEqual([]);
    });
  });

  test("a stored count continues; a count that is not a positive integer restarts at one", () => {
    withFixture((fixture) => {
      transcript(fixture);
      save(fixture.planPath, midway());
      mkdirSync(counterFolder(fixture), { recursive: true });
      const session = `stored-${randomUUID()}`;
      const counter = counterFile(fixture, session);
      writeFileSync(counter, "3");
      expect(run(fixture, stop(fixture, session))).toEqual(ALLOWED);
      expect(existsSync(counter)).toBe(false);
      for (const stored of ["abc", "-5", "0"]) {
        writeFileSync(counter, stored);
        expect(run(fixture, stop(fixture, session))).toEqual(stopRefusal(fixture));
        expect(readFileSync(counter, "utf8")).toBe("1");
      }
    });
  });

  test("session IDs are trimmed, and a missing or blank one shares the unknown counter", () => {
    withFixture((fixture) => {
      transcript(fixture);
      save(fixture.planPath, midway());
      for (let attempt = 0; attempt < 3; attempt += 1) expect(run(fixture, stop(fixture, " padded "))).toEqual(stopRefusal(fixture));
      expect(run(fixture, stop(fixture, "padded"))).toEqual(ALLOWED);
      for (let attempt = 0; attempt < 3; attempt += 1) expect(run(fixture, stop(fixture, "", { session_id: undefined }))).toEqual(stopRefusal(fixture));
      expect(run(fixture, stop(fixture, "   "))).toEqual(ALLOWED);
    });
  });

  test("a counter folder or file that is a link or the wrong kind refuses", () => {
    withFixture((fixture) => {
      transcript(fixture);
      save(fixture.planPath, midway());
      const root = realpathSync(fixture.root);
      const cache = join(fixture.root, ".ai-engineering", "cache");
      const persist = (detail: string) => refused(`Checkpoint cannot pass: Stop gate cannot persist the consecutive-stop limit (${detail}). Next: restore access to .ai-engineering/cache and retry.`);
      writeFileSync(cache, "file");
      expect(run(fixture, stop(fixture))).toEqual(persist(`${join(root, ".ai-engineering", "cache")} is not a real directory`));
      rmSync(cache);
      const elsewhere = join(fixture.root, "elsewhere");
      mkdirSync(elsewhere);
      if (!link(() => symlinkSync(elsewhere, cache, "dir"))) return;
      expect(run(fixture, stop(fixture))).toEqual(persist(`${join(root, ".ai-engineering", "cache")} is not a real directory`));
      rmSync(cache);

      const session = `kind-${randomUUID()}`;
      const counter = counterFile(fixture, session);
      const realCounter = join(root, relative(fixture.root, counter));
      mkdirSync(counter, { recursive: true });
      expect(run(fixture, stop(fixture, session))).toEqual(persist(`${realCounter} is not a regular file`));
      rmSync(counter, { recursive: true });
      writeFileSync(join(fixture.root, "target.txt"), "1");
      if (!link(() => symlinkSync(join(fixture.root, "target.txt"), counter))) return;
      expect(run(fixture, stop(fixture, session))).toEqual(persist(`${realCounter} is not a regular file`));
    });
  });
});

describe("dispatch", () => {
  test("no repository, or a tool the guard does not gate, decides nothing", () => {
    withFixture((fixture) => {
      save(fixture.planPath, "{ malformed");
      expect(runCheckpointGuard(write(fixture.planPath, plan()), null)).toBeUndefined();
      expect(runCheckpointGuard({ tool_name: "", tool_input: {}, hook_event_name: "Stop", _event: "Stop" }, null)).toBeUndefined();
      expect(run(fixture, tool("Read", { file_path: fixture.planPath }))).toBeUndefined();
    });
  });
});
