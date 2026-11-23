// tests/findings-check.spec.ts — every signal from both sides: the finding it must
// annotate, and the look-alike it must leave alone. An annotation that hides a real
// finding is the failure this file exists to prevent, so the "stays clean" rows matter as
// much as the others. Facts are stubbed from maps, so no test needs a git history.
//
// The fixture `rounds-hardening.json` keeps real ids, files, lines and revisions from this
// repository's own pull requests, with each description cut at its first sentence.

import { afterAll, describe, expect, test } from "bun:test";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { gitFacts, parseAddedLines, resolveRevisions, findingsMain } from "../src/commands/findings.ts";
import { runGit } from "../src/git/run.ts";
import {
  absenceTokens,
  checkFindings,
  formatCountLine,
  lineCount,
  parseRoundDocument,
  renderAnnotations,
  selectRound,
  type CheckInput,
  type Finding,
  type RepoFacts,
} from "../src/shared-findings.ts";

const FIXTURES = join(import.meta.dir, "fixtures", "findings");
const HEAD = "b35f722fba2a49f8f9ea2c086ae6c85f5d98ec1a";
const BASE = "ffc1584fa6c9369b91d15701dd003ed2a0f61cb1";
const readFixture = () => parseRoundDocument(readFileSync(join(FIXTURES, "rounds-hardening.json"), "utf8"));

/** A repository cut down to what a check can ask: one revision's text per path, the paths
 *  a branch named, and the added lines of one file (numbered from 1 in the order given). */
type Repo = {
  files?: Record<string, string>;
  touched?: string[];
  added?: Record<string, string[]>;
};

function stubFacts(repo: Repo): RepoFacts {
  return {
    fileAt: (revision, path) => repo.files?.[`${revision}:${path}`] ?? null,
    pathsTouched: () => new Set(repo.touched ?? []),
    addedLines: (_base, _head, path) => (repo.added?.[path] ?? []).map((text, index) => ({ line: index + 1, text })),
  };
}

/** A file with `lines` numbered lines, for the "line past the end" rows. */
const textOfLines = (lines: number): string => Array.from({ length: lines }, (_, index) => `line ${index + 1}`).join("\n") + "\n";

const finding = (over: Partial<Finding> & Pick<Finding, "id">): Finding => ({
  severity: "warning",
  file: "src/guards/shell.ts",
  description: "a finding with no unusual wording",
  ...over,
});

const input = (findings: Finding[], over: Partial<CheckInput> = {}): CheckInput => ({
  findings,
  base: BASE,
  head: HEAD,
  declined: new Set<string>(),
  ...over,
});

/** The signals attached to one finding, by id. */
function signalsFor(findings: Finding[], facts: RepoFacts, over: Partial<CheckInput> = {}): Record<string, string[]> {
  const report = checkFindings(input(findings, over), facts);
  return Object.fromEntries(report.verdicts.map((verdict) => [verdict.finding.id, verdict.hits.map((hit) => hit.signal)]));
}

const emptyRepo: Repo = { files: { [`${HEAD}:src/guards/shell.ts`]: textOfLines(900), [`${BASE}:src/guards/shell.ts`]: textOfLines(900) } };
const UPSTREAM_IMPORT = 'import { commandIndex, expandedSegments, inlineShellPrograms, normalizeRedirects, quotedSpanEnd, rawShellWords, shellWords, stripRedirectWords } from "./shell.ts";';

describe("phantom-location", () => {
  // Row shape: [reason, finding, repository, must annotate]
  const rows: [string, Finding, Repo, boolean][] = [
    [
      "a path that never existed in either revision",
      finding({ id: "phantom-path", file: "src/guards/nope.ts", line: 12 }),
      emptyRepo,
      true,
    ],
    [
      "a line past the end of a file that does exist",
      finding({ id: "phantom-line", file: "src/guards/shell.ts", line: 99999 }),
      emptyRepo,
      true,
    ],
    [
      "a path a commit in the branch added and then deleted: the agy lockout finding, which was real",
      finding({ id: "agy-machine-carrier-fail-closed-lockout", severity: "warning", file: "templates/settings.agy.json.tpl", line: 3 }),
      { ...emptyRepo, touched: ["templates/settings.agy.json.tpl"] },
      false,
    ],
    [
      "a path outside the diff that exists at head: the agy-normalise-bypasses shape",
      finding({ id: "agy-normalise-bypasses", file: "src/payload.ts", line: 287 }),
      { ...emptyRepo, files: { ...emptyRepo.files, [`${HEAD}:src/payload.ts`]: textOfLines(400), [`${BASE}:src/payload.ts`]: textOfLines(400) } },
      false,
    ],
    [
      "a finding that names no line, on a file that exists",
      finding({ id: "no-line", file: "src/payload.ts" }),
      { ...emptyRepo, files: { ...emptyRepo.files, [`${HEAD}:src/payload.ts`]: textOfLines(10), [`${BASE}:src/payload.ts`]: textOfLines(10) } },
      false,
    ],
    [
      "a finding that names no file at all: a claim about nothing is not a claim",
      finding({ id: "no-file", file: "  ", line: 12 }),
      emptyRepo,
      false,
    ],
  ];
  for (const [reason, caseFinding, repo, annotates] of rows) {
    test(`${annotates ? "annotates" : "leaves alone"}: ${reason}`, () => {
      expect(signalsFor([caseFinding], stubFacts(repo))[caseFinding.id]).toEqual(annotates ? ["phantom-location"] : []);
    });
  }
});

describe("absence-contradicted", () => {
  const BASE_IMPORT = 'import { commandIndex, expandedSegments, shellWords } from "./shell.ts";';
  // policy.ts exists at both revisions, so only the absence claim can fire here.
  const withPolicy: Repo = { ...emptyRepo, files: { ...emptyRepo.files, [`${HEAD}:src/guards/policy.ts`]: textOfLines(400), [`${BASE}:src/guards/policy.ts`]: textOfLines(400) } };
  const withImport: Repo = {
    ...withPolicy,
    added: { "src/guards/policy.ts": [BASE_IMPORT, UPSTREAM_IMPORT] },
  };
  const rows: [string, Finding, Repo, boolean][] = [
    [
      "`does not import` the token, and the import is on an added line of the cited file",
      finding({ id: "absence-before", file: "src/guards/policy.ts", description: "policy.ts does not import `quotedSpanEnd`, so the span it reports is wrong." }),
      withImport,
      true,
    ],
    [
      "`is not exported` the token, and the export is on an added line of the cited file",
      finding({ id: "absence-after", file: "src/guards/policy.ts", description: "`quotedSpanEnd` is not exported from src/guards/shell.ts any more." }),
      withImport,
      true,
    ],
    [
      "free-form absence wording: nothing to match, and no program can check it",
      finding({ id: "absence-free-form", file: "src/guards/policy.ts", description: "`foo` does not handle null." }),
      withImport,
      false,
    ],
    [
      "a token under three characters is not a code name to match on",
      finding({ id: "absence-short", file: "src/guards/policy.ts", description: "policy does not import `qs`." }),
      withImport,
      false,
    ],
    [
      "the token is on a removed line, which the new side does not carry",
      finding({ id: "absence-removed", file: "src/guards/policy.ts", description: "policy.ts does not import `quotedSpanEnd`." }),
      { ...withPolicy, added: { "src/guards/policy.ts": [BASE_IMPORT] } },
      false,
    ],
    [
      "the token was added in a different file, not the one the finding cites",
      finding({ id: "absence-other-file", file: "src/guards/policy.ts", description: "policy.ts does not import `quotedSpanEnd`." }),
      { ...withPolicy, added: { "src/guards/shell.ts": [UPSTREAM_IMPORT], "src/guards/policy.ts": [BASE_IMPORT] } },
      false,
    ],
    [
      "one of two claimed tokens is missing from the added lines: the claim is not contradicted",
      finding({ id: "absence-partial", file: "src/guards/policy.ts", description: "policy.ts does not import `quotedSpanEnd` or `unresolvedHelper`." }),
      withImport,
      false,
    ],
    [
      "an Oxford-comma list whose final token is missing is not contradicted",
      finding({
        id: "absence-oxford-partial",
        file: "src/guards/policy.ts",
        description: "policy.ts does not import `quotedSpanEnd`, `shellWords`, or `unresolvedHelper`.",
      }),
      withImport,
      false,
    ],
    [
      "an Oxford-comma list where every token is on an added line is contradicted",
      finding({
        id: "absence-oxford-all",
        file: "src/guards/policy.ts",
        description: "policy.ts does not import `quotedSpanEnd`, `shellWords`, or `rawShellWords`.",
      }),
      withImport,
      true,
    ],
  ];
  for (const [reason, caseFinding, repo, annotates] of rows) {
    test(`${annotates ? "annotates" : "leaves alone"}: ${reason}`, () => {
      expect(signalsFor([caseFinding], stubFacts(repo))[caseFinding.id]).toEqual(annotates ? ["absence-contradicted"] : []);
    });
  }

  test("both templates and every token are read from one description", () => {
    expect(absenceTokens("`a1` is missing and it never calls `b2`.")).toEqual(["a1", "b2"]);
  });

  test("Oxford-comma lists keep every token and repeated tokens are deduplicated in first-seen order", () => {
    expect(absenceTokens("does not import `first`, `second`, or `third`, and `second` is missing.")).toEqual([
      "first",
      "second",
      "third",
    ]);
    expect(absenceTokens("does not import `alpha`, `beta`, and `gamma`.")).toEqual(["alpha", "beta", "gamma"]);
  });

  test("a token mentioned twice is one hit, not two, with no duplicate evidence clause", () => {
    const twice = finding({ id: "mentions-twice", file: "src/guards/policy.ts", description: "policy.ts does not import `quotedSpanEnd`, and `quotedSpanEnd` is not exported." });
    const report = checkFindings(input([twice]), stubFacts(withImport));
    expect(report.verdicts[0]!.hits).toHaveLength(1);
    expect(report.verdicts[0]!.hits[0]!.evidence).toBe("`quotedSpanEnd` is on the added line src/guards/policy.ts:2");
    expect(report.counts.signals["absence-contradicted"]).toEqual({ annotated: 1, fixedLater: 0 });
  });
});

describe("already-decided", () => {
  test("annotates: the same id a user selection declined earlier", () => {
    const declined = new Set(["injection-review-arms-have-no-reader"]);
    expect(signalsFor([finding({ id: "injection-review-arms-have-no-reader" })], stubFacts(emptyRepo), { declined })["injection-review-arms-have-no-reader"]).toEqual([
      "already-decided",
    ]);
  });

  test("leaves alone: an id that differs only in case is a different id", () => {
    const declined = new Set(["Injection-Review-Arms"]);
    expect(signalsFor([finding({ id: "injection-review-arms" })], stubFacts(emptyRepo), { declined })["injection-review-arms"]).toEqual([]);
  });

  test("leaves alone: nothing declined means nothing decided", () => {
    expect(signalsFor([finding({ id: "fresh" })], stubFacts(emptyRepo))["fresh"]).toEqual([]);
  });
});

describe("annotate-only across severities and wording", () => {
  const errorFinding = finding({ id: "compound-scope-resolved-before-pipe-or-background", severity: "error", file: "src/guards/nope.ts", line: 3 });
  const securityFinding = finding({ id: "assignment-expansion-bypass", file: "src/guards/nope.ts", line: 3 });
  const cleanErrorFinding = finding({ id: "real-error", severity: "error", file: "src/guards/shell.ts", line: 12 });

  test("an error finding that matches a signal is annotated, rendered, visible, and counted for precision", () => {
    const report = checkFindings(input([errorFinding], { fixedLater: new Set([errorFinding.id]) }), stubFacts(emptyRepo));
    expect(report.verdicts[0]!.finding.id).toBe(errorFinding.id);
    expect(report.verdicts[0]!.hits.map((hit) => hit.signal)).toEqual(["phantom-location"]);
    expect(report.counts).toMatchObject({ findings: 1, annotated: 1, clean: 0, fixedLater: 1 });
    expect(report.counts.signals["phantom-location"]).toEqual({ annotated: 1, fixedLater: 1 });
    expect(renderAnnotations(report)[0]).toBe("phantom-location  src/guards/nope.ts:3  compound-scope-resolved-before-pipe-or-background (error)");
  });

  test("a security-worded finding that matches a signal is annotated, rendered, and counted", () => {
    const report = checkFindings(input([securityFinding]), stubFacts(emptyRepo));
    expect(report.verdicts[0]!.hits.map((hit) => hit.signal)).toEqual(["phantom-location"]);
    expect(report.counts).toMatchObject({ findings: 1, annotated: 1, clean: 0, fixedLater: 0 });
    expect(renderAnnotations(report)[0]).toBe("phantom-location  src/guards/nope.ts:3  assignment-expansion-bypass (warning)");
  });

  test("an error finding that matches no signal stays clean and unannotated", () => {
    const report = checkFindings(input([cleanErrorFinding]), stubFacts(emptyRepo));
    expect(report.verdicts[0]!.hits).toEqual([]);
    expect(report.counts).toMatchObject({ findings: 1, annotated: 0, clean: 1, fixedLater: 0 });
    expect(renderAnnotations(report)).toEqual([]);
  });
});

describe("the counters", () => {
  const doubleHit = finding({ id: "both-signals", file: "src/guards/nope.ts", line: 3 });
  const clean = finding({ id: "clean", file: "src/guards/shell.ts", line: 171 });
  const errorHit = finding({ id: "tamper-check", severity: "error", file: "src/guards/nope.ts", line: 3 });

  test("annotated and clean add up to every finding", () => {
    const report = checkFindings(input([doubleHit, clean, errorHit], { declined: new Set(["both-signals"]) }), stubFacts(emptyRepo));
    const { counts } = report;
    expect(counts.findings).toBe(3);
    expect(counts.annotated + counts.clean).toBe(counts.findings);
    expect(counts).toMatchObject({ annotated: 2, clean: 1 });
  });

  test("a finding with two signals counts once per signal, not twice in `annotated`", () => {
    const report = checkFindings(input([doubleHit], { declined: new Set(["both-signals"]) }), stubFacts(emptyRepo));
    expect(report.verdicts[0]!.hits.map((hit) => hit.signal)).toEqual(["phantom-location", "already-decided"]);
    expect(report.counts.annotated).toBe(1);
    expect(report.counts.signals["phantom-location"]).toEqual({ annotated: 1, fixedLater: 0 });
    expect(report.counts.signals["already-decided"]).toEqual({ annotated: 1, fixedLater: 0 });
  });

  test("an annotated finding selected for fixing is counted once, on every signal it carries", () => {
    const report = checkFindings(input([doubleHit], { declined: new Set(["both-signals"]), fixedLater: new Set(["both-signals"]) }), stubFacts(emptyRepo));
    expect(report.counts.fixedLater).toBe(1);
    expect(report.counts.signals["phantom-location"].fixedLater).toBe(1);
    expect(report.counts.signals["already-decided"].fixedLater).toBe(1);
  });

  test("the count line names every signal and counts a fixed finding once", () => {
    const report = checkFindings(input([doubleHit, clean], { declined: new Set(["both-signals"]), fixedLater: new Set(["both-signals"]) }), stubFacts(emptyRepo));
    expect(formatCountLine(report.counts)).toBe(
      "findings 2 · annotated 1 (phantom-location 1, absence-contradicted 0, already-decided 1) · clean 1 · fixed later 1 of 1 (phantom-location 1, absence-contradicted 0, already-decided 1)",
    );
  });

  test("nothing is ever removed: every finding has a verdict", () => {
    const findings = [doubleHit, clean, errorHit];
    const report = checkFindings(input(findings, { declined: new Set(["both-signals"]) }), stubFacts(emptyRepo));
    expect(report.verdicts.map((verdict) => verdict.finding.id)).toEqual(findings.map((entry) => entry.id));
  });
});

describe("the rounds document", () => {
  const fixture = readFixture();

  test("reads the captured array shape and keeps every review round", () => {
    expect(fixture.rounds.map((round) => round.number)).toEqual([1, 2, 3]);
    expect(fixture.rounds[2]!.findings).toHaveLength(7);
  });

  test("round 2 sees the id round 1 declined, and selections from round 2 and round 3", () => {
    const selection = selectRound(fixture, 2);
    expect([...selection.declined]).toEqual(["injection-review-arms-have-no-reader"]);
    expect(selection.fixedLater.has("compound-scope-resolved-before-pipe-or-background")).toBe(true);
    expect(selection.fixedLater.has("injection-review-arms-have-no-reader")).toBe(true);
    expect(selection.head).toBe("b8ca51b8f22b208c2d4cae9746384dcd6a07fa53");
  });

  test("the default last round counts its own selection in fixedLater, and an unselected finding stays 0", () => {
    const last = selectRound(fixture);
    expect(last.number).toBe(3);
    expect(last.fixedLater.has("injection-review-arms-have-no-reader")).toBe(true);

    const liveDocument = parseRoundDocument(
      JSON.stringify([
        { round: 1, selection_source: "user", selected_finding_ids: [], findings: [finding({ id: "kept-declined" })] },
        { round: 2, selection_source: "user", selected_finding_ids: [], findings: [finding({ id: "kept-declined" })] },
      ]),
    );
    const live = selectRound(liveDocument);
    expect(live.fixedLater.has("kept-declined")).toBe(false);
    const liveReport = checkFindings({ ...live, base: BASE, head: HEAD }, stubFacts(emptyRepo));
    expect(liveReport.counts).toMatchObject({ findings: 1, annotated: 1, clean: 0, fixedLater: 0 });
  });

  test("a finding fixed in the reviewed round's own selection is counted even when it never recurs in a later round", () => {
    const resolved = finding({ id: "fixed-in-round-2", file: "src/guards/nope.ts", line: 3 });
    const document = parseRoundDocument(
      JSON.stringify([
        { round: 1, selection_source: "user", selected_finding_ids: [], findings: [] },
        { round: 2, selection_source: "user", selected_finding_ids: ["fixed-in-round-2"], findings: [resolved] },
        { round: 3, selection_source: "user", selected_finding_ids: [], findings: [] },
      ]),
    );
    const selection = selectRound(document, 2);
    expect(selection.fixedLater.has("fixed-in-round-2")).toBe(true);
    const report = checkFindings({ ...selection, base: BASE, head: HEAD }, stubFacts(emptyRepo));
    expect(report.counts).toMatchObject({ findings: 1, annotated: 1, clean: 0, fixedLater: 1 });
  });

  test("a later user round that selects a previously declined id clears the decline", () => {
    const document = parseRoundDocument(
      JSON.stringify([
        { round: 1, selection_source: "user", selected_finding_ids: [], findings: [finding({ id: "incomplete-fix" })] },
        { round: 2, selection_source: "user", selected_finding_ids: ["incomplete-fix"], findings: [finding({ id: "incomplete-fix" })] },
        { round: 3, selection_source: "user", selected_finding_ids: [], findings: [finding({ id: "incomplete-fix" })] },
      ]),
    );
    expect([...selectRound(document, 2).declined]).toEqual(["incomplete-fix"]);
    expect([...selectRound(document, 3).declined]).toEqual([]);
  });

  test("a non-user round neither declines nor clears a decline: only the person decides", () => {
    const autoClearsNothing = parseRoundDocument(
      JSON.stringify([
        { round: 1, selection_source: "user", selected_finding_ids: [], findings: [finding({ id: "declined-twice" })] },
        { round: 2, selection_source: "auto", selected_finding_ids: ["declined-twice"], findings: [finding({ id: "declined-twice" })] },
        { round: 3, selection_source: "user", selected_finding_ids: [], findings: [finding({ id: "declined-twice" })] },
      ]),
    );
    expect([...selectRound(autoClearsNothing, 3).declined]).toEqual(["declined-twice"]);

    const autoDeclinesNothing = parseRoundDocument(
      JSON.stringify([
        { round: 1, selection_source: "auto", selected_finding_ids: [], findings: [finding({ id: "auto-omitted" })] },
        { round: 2, selection_source: "user", selected_finding_ids: [], findings: [finding({ id: "auto-omitted" })] },
      ]),
    );
    expect([...selectRound(autoDeclinesNothing, 2).declined]).toEqual([]);
  });

  test("fileless findings are never dropped, can match already-decided, and render cleanly", () => {
    const roundsDoc = parseRoundDocument(
      JSON.stringify([
        {
          round: 1,
          selection_source: "user",
          selected_finding_ids: [],
          findings: [
            { id: "missing-file-key", severity: "warning", description: "PR-wide missing changelog" },
            { id: "null-file-key", severity: "info", file: null, line: 12, description: "PR-wide metadata note" },
          ],
        },
        {
          round: 2,
          selection_source: "user",
          selected_finding_ids: [],
          findings: [
            { id: "missing-file-key", severity: "warning", description: "PR-wide missing changelog" },
            { id: "null-file-key", severity: "info", file: null, line: 12, description: "PR-wide metadata note" },
            { id: "blank-file-fresh", severity: "warning", file: "   ", description: "fresh PR-wide note" },
          ],
        },
      ]),
    );
    const selection = selectRound(roundsDoc, 2);
    expect(selection.findings.map((item) => item.id)).toEqual(["missing-file-key", "null-file-key", "blank-file-fresh"]);
    const report = checkFindings({ ...selection, base: BASE, head: HEAD }, stubFacts(emptyRepo));
    expect(report.counts).toMatchObject({ findings: 3, annotated: 2, clean: 1, fixedLater: 0 });
    expect(report.verdicts.map((verdict) => [verdict.finding.id, verdict.hits.map((hit) => hit.signal)])).toEqual([
      ["missing-file-key", ["already-decided"]],
      ["null-file-key", ["already-decided"]],
      ["blank-file-fresh", []],
    ]);
    const rendered = renderAnnotations(report);
    expect(rendered[0]).toBe("already-decided  missing-file-key (warning)");
    expect(rendered[3]).toBe("already-decided  null-file-key (info)");

    const bareDoc = parseRoundDocument(
      JSON.stringify({ findings: [{ id: "bare-fileless", severity: "warning", description: "no file field" }] }),
    );
    expect(selectRound(bareDoc).findings).toEqual([
      { id: "bare-fileless", severity: "warning", file: "", description: "no file field" },
    ]);
  });

  test("reads the live `{rounds:[…]}` shape and the bare `{findings:[…]}` shape", () => {
    const live = parseRoundDocument(JSON.stringify({ run_id: "r", rounds: [{ round: 1, findings: [finding({ id: "live" })] }] }));
    expect(live.rounds[0]!.findings[0]!.id).toBe("live");
    const bare = parseRoundDocument(JSON.stringify({ findings: [finding({ id: "bare" })] }));
    expect(selectRound(bare).declined.size).toBe(0);
    expect(selectRound(bare).findings[0]!.id).toBe("bare");
  });

  test("reads the captured `findings_json` string shape", () => {
    const captured = parseRoundDocument(
      JSON.stringify([{ round: 1, step_name: "review", findings_json: JSON.stringify({ findings: [finding({ id: "stored" })] }) }]),
    );
    expect(captured.rounds[0]!.findings[0]!.id).toBe("stored");
  });

  test("reads a selection the capture stored as JSON text, not as an array", () => {
    // The eval capture holds the database column: one string. Read as a string, every id of
    // every earlier round looked declined and the check annotated the whole run.
    const document = parseRoundDocument(
      JSON.stringify([
        { round: 1, selection_source: "user", selected_finding_ids: '["kept"]', findings: [finding({ id: "kept" }), finding({ id: "dropped" })] },
        { round: 2, selection_source: "user", selected_finding_ids: "[]", findings: [finding({ id: "kept" }), finding({ id: "dropped" })] },
      ]),
    );
    expect([...selectRound(document, 2).declined]).toEqual(["dropped"]);
  });

  test("another step's rounds are not review findings", () => {
    const document = parseRoundDocument(JSON.stringify([{ round: 1, step_name: "review" }, { round: 2, step_name: "rebase" }]));
    expect(document.rounds.map((round) => round.number)).toEqual([1]);
  });

  test("an unreadable document says what it wanted", () => {
    expect(() => parseRoundDocument("not json")).toThrow(/not JSON/);
    expect(() => parseRoundDocument("{}")).toThrow(/neither rounds nor findings/);
  });

  test("a round the document does not have is named with the ones it does", () => {
    expect(() => selectRound(fixture, 9)).toThrow(/round 9 is not in the document; its review rounds are 1, 2, 3/);
  });
});

describe("the fixture, annotated end to end", () => {
  const fixture = readFixture();
  const facts = stubFacts({
    files: {
      [`${HEAD}:src/guards/shell.ts`]: textOfLines(900),
      [`${HEAD}:src/guards/injection.ts`]: textOfLines(320),
      [`${HEAD}:src/guards/no-verify.ts`]: textOfLines(400),
    },
  });

  test("round 3 keeps every finding, annotates the declined one, and counts its round-3 selection as fixedLater", () => {
    const selection = selectRound(fixture, 3);
    const report = checkFindings({ ...selection, base: BASE, head: selection.head ?? HEAD }, facts);
    expect(report.counts).toMatchObject({ findings: 7, annotated: 1, clean: 6, fixedLater: 1 });
    expect(report.counts.signals["already-decided"]).toEqual({ annotated: 1, fixedLater: 1 });
    expect(renderAnnotations(report)[0]).toBe("already-decided  src/guards/injection.ts:279  injection-review-arms-have-no-reader (info)");
  });

  test("a declined warning is annotated, counted, and measured against the fix that followed", () => {
    const declinedWarning = finding({ id: "matrix-doc-contradictions", file: "src/guards/shell.ts", line: 171 });
    const document = parseRoundDocument(
      JSON.stringify([
        { round: 1, selection_source: "user", selected_finding_ids: [], reviewed_head_sha: HEAD, findings: [declinedWarning] },
        { round: 2, selection_source: "user", selected_finding_ids: [], reviewed_head_sha: HEAD, findings: [declinedWarning] },
        {
          round: 3,
          selection_source: "user",
          selected_finding_ids: ["matrix-doc-contradictions"],
          reviewed_head_sha: HEAD,
          findings: [declinedWarning],
        },
      ]),
    );
    const selection = selectRound(document, 2);
    const report = checkFindings({ ...selection, base: BASE, head: selection.head ?? HEAD }, facts);
    expect(report.counts).toMatchObject({ findings: 1, annotated: 1, clean: 0, fixedLater: 1 });
    expect(formatCountLine(report.counts)).toBe(
      "findings 1 · annotated 1 (phantom-location 0, absence-contradicted 0, already-decided 1) · clean 0 · fixed later 1 of 1 (phantom-location 0, absence-contradicted 0, already-decided 1)",
    );
    expect(renderAnnotations(report)[0]).toContain("already-decided  src/guards/shell.ts:171  matrix-doc-contradictions (warning)");
  });
});

describe("the git facts", () => {
  const scratch = mkdtempSync(join(tmpdir(), "ai-eng-findings-"));
  const git = (args: string[]): void => {
    const done = runGit(args, { cwd: scratch });
    if (done.status !== 0) throw new Error(`${args.join(" ")}: ${done.stderr}`);
  };
  writeFileSync(join(scratch, "kept.ts"), "one\ntwo\nthree\n");
  writeFileSync(join(scratch, "gone.ts"), "old\n");
  mkdirSync(join(scratch, "src"));
  writeFileSync(join(scratch, "src", "nested.ts"), "nested\n");
  git(["init", "-q", "-b", "main"]);
  git(["add", "."]);
  git(["-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "base"]);
  const base = runGit(["rev-parse", "HEAD"], { cwd: scratch }).stdout.trim();
  writeFileSync(join(scratch, "kept.ts"), "one\ntwo\nthree\nimport { quotedSpanEnd } from './shell.ts';\n");
  rmSync(join(scratch, "gone.ts"));
  git(["add", "-A"]);
  git(["-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "change"]);
  const head = runGit(["rev-parse", "HEAD"], { cwd: scratch }).stdout.trim();
  const facts = gitFacts(scratch);
  afterAll(() => rmSync(scratch, { recursive: true, force: true }));

  test("a file's text at a revision, and null for the path that is not there", () => {
    expect(facts.fileAt(head, "kept.ts")).toContain("quotedSpanEnd");
    expect(facts.fileAt(base, "kept.ts")).not.toContain("quotedSpanEnd");
    expect(facts.fileAt(head, "gone.ts")).toBeNull();
  });

  test("the paths the branch named include a deleted file", () => {
    expect(facts.pathsTouched(base, head).has("gone.ts")).toBe(true);
    expect(facts.pathsTouched(base, head).has("kept.ts")).toBe(true);
  });

  test("the added lines carry the new side's line numbers and no removed line", () => {
    expect(facts.addedLines(base, head, "kept.ts")).toEqual([{ line: 4, text: "import { quotedSpanEnd } from './shell.ts';" }]);
  });

  test("a directory is not a file with lines", () => {
    expect(facts.fileAt(head, "src")).toBeNull();
  });

  test("gitFacts ignores external diff tools, forced color, and ambient GIT_DIR", () => {
    const configured = mkdtempSync(join(tmpdir(), "ai-eng-findings-cfg-"));
    const run = (args: string[]): void => {
      const done = runGit(args, { cwd: configured, isolated: true });
      if (done.status !== 0) throw new Error(`${args.join(" ")}: ${done.stderr}`);
    };
    const prevGitDir = process.env.GIT_DIR;
    try {
      writeFileSync(join(configured, "a.ts"), "one\n");
      run(["init", "-q", "-b", "main"]);
      run(["add", "."]);
      run(["-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "base"]);
      const cfgBase = runGit(["rev-parse", "HEAD"], { cwd: configured, isolated: true }).stdout.trim();
      writeFileSync(join(configured, "a.ts"), "one\nexport const sentinel = true;\n");
      run(["add", "."]);
      run(["-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "change"]);
      const cfgHead = runGit(["rev-parse", "HEAD"], { cwd: configured, isolated: true }).stdout.trim();
      run(["config", "diff.external", "echo EXTERNAL_DIFF"]);
      run(["config", "color.ui", "always"]);

      process.env.GIT_DIR = join(scratch, ".git");
      const isolatedFacts = gitFacts(configured);
      expect(isolatedFacts.addedLines(cfgBase, cfgHead, "a.ts")).toEqual([{ line: 2, text: "export const sentinel = true;" }]);
      expect(isolatedFacts.pathsTouched(cfgBase, cfgHead).has("a.ts")).toBe(true);
    } finally {
      if (prevGitDir === undefined) delete process.env.GIT_DIR;
      else process.env.GIT_DIR = prevGitDir;
      rmSync(configured, { recursive: true, force: true });
    }
  });

  test("gitFacts treats bracketed route paths literally and keeps non-ASCII paths unquoted", () => {
    const special = mkdtempSync(join(tmpdir(), "ai-eng-findings-paths-"));
    const run = (args: string[]): string => {
      const done = runGit(args, { cwd: special, isolated: true });
      if (done.status !== 0) throw new Error(`${args.join(" ")}: ${done.stderr}`);
      return done.stdout.trim();
    };
    const commit = (message: string, extra: string[] = []): void => {
      run(["-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", message, ...extra]);
    };
    try {
      mkdirSync(join(special, "src", "routes", "[id]"), { recursive: true });
      mkdirSync(join(special, "src", "routes", "i"), { recursive: true });
      mkdirSync(join(special, "src", "routes", "[unchanged]"), { recursive: true });
      mkdirSync(join(special, "src", "routes", "u"), { recursive: true });
      mkdirSync(join(special, "docs"), { recursive: true });
      writeFileSync(join(special, "src", "routes", "[id]", "page.ts"), "base\n");
      writeFileSync(join(special, "src", "routes", "i", "page.ts"), "base\n");
      writeFileSync(join(special, "src", "routes", "[unchanged]", "page.ts"), "base\n");
      writeFileSync(join(special, "src", "routes", "u", "page.ts"), "base\n");
      writeFileSync(join(special, "docs", "resumen-ñ.md"), "inicio\n");
      run(["init", "-q", "-b", "main"]);
      run(["add", "."]);
      commit("base");
      const specialBase = run(["rev-parse", "HEAD"]);

      writeFileSync(join(special, "src", "routes", "[id]", "page.ts"), "base\nexport const fromBracketRoute = true;\n");
      writeFileSync(join(special, "src", "routes", "i", "page.ts"), "base\nexport const fromSibling = true;\n");
      writeFileSync(join(special, "src", "routes", "u", "page.ts"), "base\nexport const fromOtherSibling = true;\n");
      writeFileSync(join(special, "docs", "diseño.md"), "borrador\n");
      writeFileSync(join(special, "docs", "resumen-ñ.md"), "inicio\nnuevo\n");
      run(["add", "."]);
      commit("add special paths");

      commit("empty commit", ["--allow-empty"]);

      rmSync(join(special, "docs", "diseño.md"));
      run(["add", "-A"]);
      commit("remove non-ascii path");
      const specialHead = run(["rev-parse", "HEAD"]);

      const specialFacts = gitFacts(special);
      expect(specialFacts.addedLines(specialBase, specialHead, "src/routes/[id]/page.ts")).toEqual([
        { line: 2, text: "export const fromBracketRoute = true;" },
      ]);
      expect(specialFacts.addedLines(specialBase, specialHead, "src/routes/[unchanged]/page.ts")).toEqual([]);
      expect(specialFacts.fileAt(specialHead, "src/routes/[id]/page.ts")).toContain("fromBracketRoute");
      expect(specialFacts.pathsTouched(specialBase, specialHead).has("src/routes/[id]/page.ts")).toBe(true);
      expect(specialFacts.pathsTouched(specialBase, specialHead).has("docs/diseño.md")).toBe(true);
      expect(specialFacts.addedLines(specialBase, specialHead, "docs/resumen-ñ.md")).toEqual([{ line: 2, text: "nuevo" }]);
      expect(specialFacts.fileAt(specialHead, "docs/resumen-ñ.md")).toContain("nuevo");
    } finally {
      rmSync(special, { recursive: true, force: true });
    }
  });
});

describe("resolveRevisions", () => {
  const initRepo = (): { dir: string; git: (args: string[]) => string } => {
    const dir = mkdtempSync(join(tmpdir(), "ai-eng-findings-rev-"));
    const git = (args: string[]): string => {
      const done = runGit(args, { cwd: dir, isolated: true });
      if (done.status !== 0) throw new Error(`${args.join(" ")}: ${done.stderr}`);
      return done.stdout.trim();
    };
    return { dir, git };
  };

  const emptySelection = () => {
    const document = parseRoundDocument(JSON.stringify({ findings: [] }));
    return { document, selection: selectRound(document) };
  };

  test("resolves merge-base from [git] base in config.toml even without a remote", () => {
    const { dir, git } = initRepo();
    try {
      git(["init", "-q", "-b", "trunk"]);
      writeFileSync(join(dir, "f.ts"), "base\n");
      mkdirSync(join(dir, ".ai-engineering"), { recursive: true });
      writeFileSync(join(dir, ".ai-engineering", "config.toml"), '[git]\nbase = "trunk"\n');
      git(["add", "."]);
      git(["-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "base"]);
      const baseSha = git(["rev-parse", "HEAD"]);
      git(["checkout", "-qb", "fm/feature"]);
      writeFileSync(join(dir, "f.ts"), "base\nfeature\n");
      git(["add", "."]);
      git(["-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "feat"]);
      const headSha = git(["rev-parse", "HEAD"]);

      const { document, selection } = emptySelection();
      expect(resolveRevisions(dir, document, selection, {})).toEqual({ base: baseSha, head: headSha });
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("resolves merge-base from a non-origin remote HEAD without a local base branch", () => {
    const { dir, git } = initRepo();
    try {
      git(["init", "-q", "-b", "develop"]);
      writeFileSync(join(dir, "f.ts"), "base\n");
      git(["add", "."]);
      git(["-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "base"]);
      const baseSha = git(["rev-parse", "HEAD"]);
      git(["checkout", "-qb", "fm/feature"]);
      writeFileSync(join(dir, "f.ts"), "base\nfeature\n");
      git(["add", "."]);
      git(["-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "feat"]);
      const headSha = git(["rev-parse", "HEAD"]);
      git(["remote", "add", "upstream", "https://example.invalid/repo.git"]);
      git(["update-ref", "refs/remotes/upstream/develop", baseSha]);
      git(["update-ref", "refs/remotes/upstream/fm/feature", headSha]);
      git(["symbolic-ref", "refs/remotes/upstream/HEAD", "refs/remotes/upstream/develop"]);
      git(["branch", "--set-upstream-to=upstream/fm/feature"]);
      git(["branch", "-D", "develop"]);

      const { document, selection } = emptySelection();
      expect(resolveRevisions(dir, document, selection, {})).toEqual({ base: baseSha, head: headSha });
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("does not fall back to @{upstream} when no configured or remote-HEAD base exists", () => {
    const { dir, git } = initRepo();
    try {
      git(["init", "-q", "-b", "main"]);
      writeFileSync(join(dir, "f.ts"), "base\n");
      git(["add", "."]);
      git(["-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "base"]);
      git(["checkout", "-qb", "fm/pushed"]);
      writeFileSync(join(dir, "f.ts"), "base\nfeature\n");
      git(["add", "."]);
      git(["-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "feat"]);
      const headSha = git(["rev-parse", "HEAD"]);
      git(["remote", "add", "origin", "https://example.invalid/repo.git"]);
      git(["update-ref", "refs/remotes/origin/fm/pushed", headSha]);
      git(["branch", "--set-upstream-to=origin/fm/pushed"]);

      const { document, selection } = emptySelection();
      expect(resolveRevisions(dir, document, selection, {})).toBe("the run base is unknown: pass --base <rev>");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});

describe("parseAddedLines", () => {
  test("hunk headers set the new-side counter and removed lines do not advance it", () => {
    const diff = [
      "diff --git a/x.ts b/x.ts",
      "--- a/x.ts",
      "+++ b/x.ts",
      "@@ -10,2 +10,3 @@",
      "-removed",
      "+first",
      " context",
      "+second",
      "\\ No newline at end of file",
      "@@ -40 +41,0 @@",
      "-only-removed",
    ].join("\n");
    expect(parseAddedLines(diff)).toEqual([
      { line: 10, text: "first" },
      { line: 12, text: "second" },
    ]);
  });

  test("an added line starting with `++ ` inside a hunk is kept and advances line numbers, while headers outside a hunk are ignored", () => {
    const diff = [
      "diff --git a/x.ts b/x.ts",
      "--- a/x.ts",
      "+++ b/x.ts",
      "@@ -1,0 +1,2 @@",
      "+++ count",
      "+after",
      "diff --git a/y.ts b/y.ts",
      "--- a/y.ts",
      "+++ b/y.ts",
      "@@ -0,0 +1 @@",
      "+only-one",
      "+++ b/trailing-header.ts",
    ].join("\n");
    expect(parseAddedLines(diff)).toEqual([
      { line: 1, text: "++ count" },
      { line: 2, text: "after" },
      { line: 1, text: "only-one" },
    ]);
  });

  test("a file header is not an added line", () => {
    expect(parseAddedLines("+++ b/x.ts")).toEqual([]);
  });
});

describe("lineCount", () => {
  test("a trailing newline ends the last line instead of starting a new one", () => {
    expect(lineCount("one\ntwo\n")).toBe(2);
    expect(lineCount("one\ntwo")).toBe(2);
    expect(lineCount("")).toBe(0);
  });
});

describe("the verb", () => {
  test("a missing subcommand is usage, not a failure", () => {
    expect(findingsMain([], {})).toBe(2);
  });

  test("input it cannot read exits 1 with a reason, because the count line would be a lie", () => {
    expect(findingsMain(["check", join(tmpdir(), "ai-eng-findings-does-not-exist.json")], {})).toBe(1);
  });

  test("a round that is not a round number is refused before any git runs", () => {
    expect(findingsMain(["check", join(FIXTURES, "rounds-hardening.json")], { round: "three" })).toBe(1);
  });
});
