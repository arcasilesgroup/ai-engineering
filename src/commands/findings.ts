// `ai-eng findings check` — read a run's review rounds, attach the evidence a program can
// check, and print one count line. It never removes a finding: the module that decides
// which signals exist says why (src/shared-findings.ts), and the verb's only write is to
// stdout. It is an instrument, not a gate, so a hit is not a failure.

import { readFileSync } from "node:fs";
import { repoRoot } from "../env.ts";
import { namedBaseTrackingRef } from "../git/context.ts";
import { runGit } from "../git/run.ts";
import {
  checkFindings,
  formatCountLine,
  parseRoundDocument,
  renderAnnotations,
  selectRound,
  type AddedLine,
  type RepoFacts,
  type RoundDocument,
  type RoundSelection,
} from "../shared-findings.ts";

const USAGE =
  "usage: ai-eng findings check <rounds.json|-> [--json] [--round <n>] [--base <rev>] [--head <rev>]";

export type FindingsFlags = { json?: boolean; round?: string; base?: string; head?: string };

function gitIn(root: string, args: string[]): string | null {
  const done = runGit(args, { cwd: root, isolated: true });
  return done.status === 0 ? done.stdout : null;
}

/** Git as the checks see it, asked once per (revision, path): one run cites the same file
 *  in several findings, and `cat-file -t` first keeps a directory or a submodule from being
 *  read as if it had lines. */
export function gitFacts(root: string): RepoFacts {
  const fileTexts = new Map<string, string | null>();
  const touchedPaths = new Map<string, ReadonlySet<string>>();
  const addedByFile = new Map<string, readonly AddedLine[]>();

  const fileAt = (revision: string, path: string): string | null => {
    const key = `${revision}\0${path}`;
    const cached = fileTexts.get(key);
    if (cached !== undefined) return cached;
    const type = gitIn(root, ["cat-file", "-t", `${revision}:${path}`]);
    const text = type !== null && type.trim() === "blob" ? gitIn(root, ["show", `${revision}:${path}`]) : null;
    fileTexts.set(key, text);
    return text;
  };

  return {
    fileAt,
    pathsTouched(base, head) {
      const key = `${base}..${head}`;
      const cached = touchedPaths.get(key);
      if (cached !== undefined) return cached;
      const named = gitIn(root, ["log", "--no-color", "--format=", "--name-only", "-z", key]) ?? "";
      const paths = new Set(named.split("\0").filter((path) => path !== ""));
      touchedPaths.set(key, paths);
      return paths;
    },
    addedLines(base, head, path) {
      const key = `${base}..${head}\0${path}`;
      const cached = addedByFile.get(key);
      if (cached !== undefined) return cached;
      const diff =
        gitIn(root, ["--literal-pathspecs", "diff", "--no-ext-diff", "--no-color", "--no-textconv", "--unified=0", `${base}..${head}`, "--", path]) ?? "";
      const lines = parseAddedLines(diff);
      addedByFile.set(key, lines);
      return lines;
    },
  };
}

/** The new side's line numbers for every `+` line of a zero-context diff. A hunk header
 *  sets the counter and remaining new-side lines, `-` lines leave them alone, and file
 *  headers outside a hunk are ignored. */
export function parseAddedLines(diff: string): AddedLine[] {
  const added: AddedLine[] = [];
  let nextLine = 0;
  let remainingNew = 0;
  for (const line of diff.split("\n")) {
    const hunk = /^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@/.exec(line);
    if (hunk !== null) {
      nextLine = Number(hunk[1]);
      remainingNew = hunk[2] === undefined ? 1 : Number(hunk[2]);
      continue;
    }
    if (remainingNew === 0) continue;
    if (line.startsWith("+")) {
      added.push({ line: nextLine, text: line.slice(1) });
      nextLine += 1;
      remainingNew -= 1;
      continue;
    }
    // Context lines advance the new side; removed lines and `\ No newline` markers do not.
    if (line.startsWith(" ")) {
      nextLine += 1;
      remainingNew -= 1;
    }
  }
  return added;
}

function fail(reason: string): number {
  process.stderr.write(`findings: ${reason}\n`);
  return 1;
}

function readSource(source: string): string {
  return source === "-" ? readFileSync(0, "utf8") : readFileSync(source, "utf8");
}

/** The revisions the round was reviewed against. The document is the first witness, the
 *  flags override it, and the checkout answers last, so a live run needs no arguments.
 *  Every revision is resolved to its commit first: a name like `HEAD~1` is not evidence,
 *  and an unresolvable one would read as "the file is not there" and annotate wrongly. */
export function resolveRevisions(root: string, document: RoundDocument, selection: RoundSelection, flags: FindingsFlags): { base: string; head: string } | string {
  const wanted = flags.head ?? selection.head ?? document.head ?? "HEAD";
  const head = gitIn(root, ["rev-parse", "--verify", "--quiet", `${wanted}^{commit}`])?.trim();
  if (head === undefined || head === "") return `cannot resolve the reviewed revision ${wanted}: pass --head <rev>`;
  let baseWanted: string | null;
  if (flags.base !== undefined) baseWanted = flags.base;
  else if (selection.base !== null) baseWanted = selection.base;
  else {
    try {
      baseWanted = trunkMergeBase(root, head);
    } catch (error) {
      return error instanceof Error ? error.message : String(error);
    }
  }
  const base = baseWanted === null ? null : gitIn(root, ["rev-parse", "--verify", "--quiet", `${baseWanted}^{commit}`])?.trim();
  if (base === undefined || base === null || base === "") {
    return baseWanted === null ? "the run base is unknown: pass --base <rev>" : `cannot resolve the base revision ${baseWanted}: pass --base <rev>`;
  }
  return { base, head };
}

function trunkMergeBase(root: string, head: string): string | null {
  const tracking = namedBaseTrackingRef(root);
  if (tracking === null) return null;
  const baseTip = tracking.commit ?? gitIn(root, ["rev-parse", "--verify", "--quiet", `refs/heads/${tracking.base}^{commit}`])?.trim() ?? null;
  if (baseTip === null || baseTip === "") return null;
  const mergeBase = gitIn(root, ["merge-base", head, baseTip]);
  return mergeBase === null ? null : mergeBase.trim();
}

function requestedRound(flags: FindingsFlags): number | undefined | string {
  if (flags.round === undefined) return undefined;
  const parsed = Number(flags.round);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : `--round wants a round number, not "${flags.round}"`;
}

export function findingsMain(args: string[], flags: FindingsFlags): number {
  if (args[0] !== "check" || args.length > 2) {
    process.stderr.write(`${USAGE}\n`);
    return 2;
  }
  const source = args[1];
  if (source === undefined) {
    process.stderr.write(`${USAGE}\n`);
    return 2;
  }
  const root = repoRoot();
  if (root === null) return fail("not inside a git repository");
  let document: RoundDocument;
  try {
    document = parseRoundDocument(readSource(source));
  } catch (error) {
    return fail(error instanceof Error ? error.message : String(error));
  }
  const round = requestedRound(flags);
  if (typeof round === "string") return fail(round);
  let selection: RoundSelection;
  try {
    selection = selectRound(document, round);
  } catch (error) {
    return fail(error instanceof Error ? error.message : String(error));
  }
  const revisions = resolveRevisions(root, document, selection, flags);
  if (typeof revisions === "string") return fail(revisions);
  const result = checkFindings(
    { findings: selection.findings, base: revisions.base, head: revisions.head, declined: selection.declined, fixedLater: selection.fixedLater },
    gitFacts(root),
  );
  if (flags.json === true) {
    const full = { round: selection.number, base: revisions.base, head: revisions.head, counts: result.counts, verdicts: result.verdicts };
    process.stdout.write(`${JSON.stringify(full, null, 2)}\n`);
    return 0;
  }
  const annotated = renderAnnotations(result);
  process.stdout.write(`${formatCountLine(result.counts)}\n`);
  if (annotated.length > 0) process.stdout.write(`${annotated.join("\n")}\n`);
  return 0; // An instrument: a hit is evidence, never a failing check.
}
