// tests/pipeline-commit-routes.spec.ts — the commit subjects this repository's validation
// pipeline stamps, held to the same rule the git floor asks a person.
//
// The pipeline writes its own commits and can assign a subject after the commit already
// exists, so several of its routes never run the `commit-msg` hook (see docs/git-floor.md).
// `prePush` re-asks the rule at the door every route does cross; tests/floor-gates.spec.ts
// proves that catch. This file proves the other half: the subjects the pipeline is
// configured to stamp pass the floor, and a pipeline route whose subject template this file
// does not know how to render fails the suite instead of slipping through unjudged.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { commitMsg, subjectProblem } from "../src/floor/index.ts";

const ROOT = join(import.meta.dir, "..");
const PIPELINE_CONFIG = join(ROOT, ".no-mistakes.yaml");

/** The steps `no-mistakes axi run --help` lists for one pipeline. Each one can stamp its
 *  own fix commits, so each one names a subject this repository has to accept. */
const PIPELINE_STEPS = ["intent", "rebase", "review", "test", "document", "lint", "push", "pr", "ci"] as const;

type PipelineRoute = {
  /** Dotted key, as the pipeline reads it from `.no-mistakes.yaml`. */
  key: string;
  /** What the pipeline stamps when the repository pins nothing. */
  pipelineDefault: string;
  /** Sample values for the placeholders this route's template supports. */
  samples: Record<string, string>;
  /** Whether this repository turns the route on at all. */
  isActive: (config: Record<string, unknown>) => boolean;
  /** One route per subject: the fix template is rendered per step, the rest once. */
  isPerStep: boolean;
};

const PIPELINE_ROUTES: PipelineRoute[] = [
  {
    key: "commit.fix_message",
    pipelineDefault: "no-mistakes({{.Step}}): {{.Summary}}",
    samples: { Step: "review", Summary: "count the findings" },
    isActive: () => true,
    isPerStep: true,
  },
  {
    key: "test.evidence.commit_message",
    pipelineDefault: "no-mistakes: evidence for {{.Branch}} (run {{.RunID}})",
    samples: { Branch: "fm/example", RunID: "01M84H2Y4395R8PP1894PFCE0M" },
    isActive: (config) => isRecord(objectAt(config, ["test", "evidence"])) && objectAt(config, ["test", "evidence"])?.store_in_repo === true,
    isPerStep: false,
  },
];

const KNOWN_KEYS = new Set(PIPELINE_ROUTES.map((route) => route.key));

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function objectAt(config: unknown, path: string[]): Record<string, unknown> | undefined {
  let cursor: unknown = config;
  for (const name of path) {
    if (!isRecord(cursor)) return undefined;
    cursor = cursor[name];
  }
  return isRecord(cursor) ? cursor : undefined;
}

/** Every commit-subject template the pipeline config declares, as `dotted.key -> template`.
 *  An unknown key is collected too: a route nobody rendered is a route nobody judged. */
function declaredSubjectTemplates(config: unknown, prefix: string[] = []): Array<{ key: string; template: string }> {
  if (!isRecord(config)) return [];
  return Object.entries(config).flatMap(([name, value]) => {
    const path = [...prefix, name];
    if (isRecord(value)) return declaredSubjectTemplates(value, path);
    return /message/i.test(name) && typeof value === "string" ? [{ key: path.join("."), template: value }] : [];
  });
}

function parsePipelineConfig(text: string): Record<string, unknown> {
  const parsed = Bun.YAML.parse(text);
  if (!isRecord(parsed)) throw new Error(".no-mistakes.yaml does not parse to a table");
  return parsed;
}

function render(template: string, values: Record<string, string>): string {
  return template.replace(/\{\{\.(\w+)\}\}/g, (_placeholder, name: string) => values[name] ?? `{{.${name}}}`);
}

/** The subject the pipeline stamps for one route, per step when the route is stepped. */
function renderedSubjects(route: PipelineRoute, template: string): string[] {
  if (!route.isPerStep) return [render(template, route.samples)];
  return PIPELINE_STEPS.map((step) => render(template, { ...route.samples, Step: step }));
}

describe("CP26 pipeline commit routes", () => {
  const repositoryConfig = parsePipelineConfig(readFileSync(PIPELINE_CONFIG, "utf8"));
  const declared = declaredSubjectTemplates(repositoryConfig);

  test("the pipeline config declares no commit-subject route this suite cannot render", () => {
    const unrouted = declared.map((route) => route.key).filter((key) => !KNOWN_KEYS.has(key));
    expect(unrouted).toEqual([]);
  });

  test("every route this repository turns on renders a subject the commit-msg hook accepts", () => {
    const active = PIPELINE_ROUTES.filter((route) => route.isActive(repositoryConfig));
    // The pin the pipeline reads for its fix commits is the one this repository declares;
    // dropping it falls back to the pipeline default, which this test then has to reject.
    expect(active.map((route) => route.key)).toContain("commit.fix_message");
    const accepted: string[] = [];
    for (const route of active) {
      const pinned = declared.find((candidate) => candidate.key === route.key)?.template;
      for (const subject of renderedSubjects(route, pinned ?? route.pipelineDefault)) {
        expect({ subject, problem: subjectProblem(subject) }).toEqual({ subject, problem: null });
        accepted.push(subject);
      }
    }
    expect(accepted.length).toBe(PIPELINE_STEPS.length);
    // One subject per step: a step that quietly reused another's would hide a route.
    expect(new Set(accepted).size).toBe(PIPELINE_STEPS.length);
  });

  test("a rendered subject also survives the real hook, trailer included", () => {
    const pinned = declared.find((route) => route.key === "commit.fix_message")?.template;
    const step = "review";
    const subject = render(pinned ?? "no-mistakes({{.Step}}): {{.Summary}}", { Step: step, Summary: "count the findings" });
    const directory = mkdtempSync(join(tmpdir(), "ai-eng-route-subject-"));
    try {
      const messageFile = join(directory, "COMMIT_EDITMSG");
      writeFileSync(messageFile, `${subject}\n\nWhy it changed.\n`);
      expect(commitMsg(messageFile, "0123abcd")).toEqual({ ok: true, lines: [] });
      expect(readFileSync(messageFile, "utf8")).toBe(`${subject}\n\nWhy it changed.\n\nReceipt-Id: 0123abcd\n`);
    } finally {
      rmSync(directory, { recursive: true, force: true });
    }
  });

  test("an unknown subject template and the pipeline default are both reported, not skipped", () => {
    const unknown = declaredSubjectTemplates({ commit: { fix_message: "chore({{.Step}}): {{.Summary}}", publish_message: "no-mistakes: {{.Summary}}" } });
    expect(unknown.map((route) => route.key)).toEqual(["commit.fix_message", "commit.publish_message"]);
    expect(unknown.map((route) => route.key).filter((key) => !KNOWN_KEYS.has(key))).toEqual(["commit.publish_message"]);
    // With no pin at all the pipeline's own default is what lands: the rejected type.
    expect(subjectProblem(render("no-mistakes({{.Step}}): {{.Summary}}", { Step: "review", Summary: "count the findings" }))).toBe(
      'the message does not follow the Conventional Commits convention: "no-mistakes(review): count the findings"',
    );
  });
});
