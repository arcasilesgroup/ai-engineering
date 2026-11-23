// src/shared-findings.ts — the review-finding filter, shrunk to its honest form:
// annotate and count, never drop.
//
// Why it does not drop: the replay over 120 real review findings from this pipeline found
// no class that is provably false on its own. "The file is not in the diff" matched 3
// findings and all 3 were real, one of them an `error`. Hiding a real finding costs more
// than reading a stale one, so every check here attaches its evidence to the finding and
// increments a counter, and the finding still reaches the reader. A check earns a drop
// switch only after 30 or more hits at 100 % measured precision; `fixedLater` is the
// counter that measures it, because a hit the operator later fixed counts against it.
//
// The absence check is a mechanism adapted from karajan-code's `absence-claims`; no code
// was taken (AGPL-3.0).

/** One finding as the review step records it. `severity` stays a string on purpose so
 *  an unknown value is preserved rather than normalised by accident. */
export type Finding = {
  id: string;
  severity: string;
  file: string;
  line?: number;
  description: string;
};

/** The signals this module can attach. Each names a claim a program can check. */
export type Signal = "phantom-location" | "absence-contradicted" | "already-decided";

/** Table order: the order the plan words them, and the order the count line prints them. */
export const SIGNALS: readonly Signal[] = ["phantom-location", "absence-contradicted", "already-decided"];

/** What a check found: the signal, and the evidence that fired it. */
export type Hit = { signal: Signal; evidence: string };

/** One added line of a file: the line number the new side gives it. */
export type AddedLine = { line: number; text: string };

/** What the checks may ask of the repository, and nothing else. Pure callers stub this,
 *  so a check is testable without a git history. */
export type RepoFacts = {
  /** The file's text at that revision, or null when the path is not there. */
  fileAt(revision: string, path: string): string | null;
  /** Every path any commit in `base..head` names. */
  pathsTouched(base: string, head: string): ReadonlySet<string>;
  /** Every added line of one file, with the line number the new side gives it. */
  addedLines(base: string, head: string, path: string): readonly AddedLine[];
};

export type Verdict = {
  finding: Finding;
  hits: Hit[];
  /** Selected for fixing in this round or a later one — the measured outcome, not an assumption. */
  isFixedLater: boolean;
};

/** Per signal: how many findings carried it, and how many of those were selected for fixing. */
export type SignalTally = { annotated: number; fixedLater: number };

export type Counts = {
  findings: number;
  /** Findings with at least one hit. */
  annotated: number;
  /** Findings with no hit: the review's ordinary output. */
  clean: number;
  /** Annotated findings selected for fixing in this round or a later one, counted once per
   *  finding. `annotated` minus this is the number of hits that stood: the precision a drop
   *  switch would have to earn. */
  fixedLater: number;
  /** A finding can carry two signals, so these can sum above `annotated`. */
  signals: Record<Signal, SignalTally>;
};

export type CheckReport = { verdicts: Verdict[]; counts: Counts };

/** `does not import `, `doesn't include `, `never calls `: the reviewer's own wording, and
 *  the claim's code names follow the verb. Free-form absence ("does not handle", "is
 *  wrong") uses none of these verbs and matches nothing — that is the point, and the
 *  reason this check fires so rarely. */
const ABSENCE_BEFORE = /(?:does not|doesn't|never|no longer)\s+(?:add|include|contain|call|import|export|define|declare|mention|list|register)s?\s+/gi;

/** The other half of the same wording: "`X` is missing", "`X` not imported". */
const ABSENCE_AFTER = /`([^`\n]+)`\s+(?:is\s+)?(?:missing|not\s+(?:added|imported|exported|defined|declared|registered|listed|called))/gi;

/** The code names one claim carries: a backticked token, then any further tokens the same
 *  claim joins with `,`, `or` or `and`. "does not import `A` or `B`" claims two, and both
 *  must be on an added line before the claim is contradicted — one is not enough. */
function tokenRun(text: string, start: number): string[] {
  const tokens: string[] = [];
  let at = start;
  for (;;) {
    const token = /^`([^`\n]+)`/.exec(text.slice(at));
    if (token === null) return tokens;
    tokens.push((token[1] ?? "").trim());
    at += token[0].length;
    const joiner = /^\s*(?:,\s*(?:(?:or|and)\s+)?|(?:or|and)\s+)/i.exec(text.slice(at));
    if (joiner === null) return tokens;
    at += joiner[0].length;
  }
}

/** A code name shorter than this is noise in a from-memory match (`\`a\``, `\`on\``). */
const MIN_TOKEN = 3;

const SHORT_SHA = 8;

/** Both templates, every unique captured token, in the order the description raises them. */
export function absenceTokens(description: string): string[] {
  const found: { at: number; token: string }[] = [];
  for (const template of [ABSENCE_BEFORE, ABSENCE_AFTER]) {
    // A fresh lastIndex per call: the regexes are module-level and stateful under /g.
    template.lastIndex = 0;
    for (const match of description.matchAll(template)) {
      const at = match.index;
      if (template === ABSENCE_BEFORE) {
        for (const token of tokenRun(description, at + match[0].length)) found.push({ at, token });
      } else {
        found.push({ at, token: (match[1] ?? "").trim() });
      }
    }
  }
  const seen = new Set<string>();
  const unique: string[] = [];
  for (const entry of found.filter((item) => item.token.length > 0).sort((left, right) => left.at - right.at)) {
    if (seen.has(entry.token)) continue;
    seen.add(entry.token);
    unique.push(entry.token);
  }
  return unique;
}

/** Lines in a file's text, counting a final newline as the end of the last line, not a new one. */
export function lineCount(text: string): number {
  if (text === "") return 0;
  const lines = text.split("\n");
  if (lines.at(-1) === "") lines.pop();
  return lines.length;
}

/** The finding's path, or null when it names none: a claim about no file is not a claim. */
function citedPath(finding: Finding): string | null {
  const path = finding.file.trim();
  return path === "" ? null : path;
}

/** `phantom-location`: the file is in neither revision and no commit names it, or the line
 *  is past the end of the file at head. A path that a commit in the branch added and then
 *  deleted stays untouched — that is how a real finding about a deleted template looked. */
function phantomLocation(finding: Finding, base: string, head: string, facts: RepoFacts): Hit | null {
  const path = citedPath(finding);
  if (path === null) return null;
  const atHead = facts.fileAt(head, path);
  const atBase = facts.fileAt(base, path);
  if (atHead === null && atBase === null) {
    if (facts.pathsTouched(base, head).has(path)) return null;
    return {
      signal: "phantom-location",
      evidence: `${path} is at neither ${head.slice(0, SHORT_SHA)} nor ${base.slice(0, SHORT_SHA)}, and no commit in base..head names it`,
    };
  }
  if (atHead === null || finding.line === undefined) return null;
  const total = lineCount(atHead);
  if (finding.line <= total) return null;
  return {
    signal: "phantom-location",
    evidence: `line ${finding.line} is past the ${total} lines ${path} has at ${head.slice(0, SHORT_SHA)}`,
  };
}

/** `absence-contradicted`: the description says a code name is absent, and every name it
 *  says that about is on an added line of the file it cites. */
function absenceContradicted(finding: Finding, base: string, head: string, facts: RepoFacts): Hit | null {
  const path = citedPath(finding);
  if (path === null) return null;
  const tokens = absenceTokens(finding.description);
  if (tokens.length === 0) return null;
  if (tokens.some((token) => token.length < MIN_TOKEN)) return null;
  const added = facts.addedLines(base, head, path);
  const found: { token: string; line: AddedLine }[] = [];
  for (const token of tokens) {
    const line = added.find((candidate) => candidate.text.includes(token));
    if (line === undefined) return null;
    found.push({ token, line });
  }
  const evidence = found.map(({ token, line }) => `\`${token}\` is on the added line ${path}:${line.line}`).join("; ");
  return { signal: "absence-contradicted", evidence };
}

/** `already-decided`: the same id was declined by a user selection in an earlier round. */
function alreadyDecided(finding: Finding, declined: ReadonlySet<string>): Hit | null {
  if (!declined.has(finding.id)) return null;
  return { signal: "already-decided", evidence: "a user selection declined this id in an earlier round of this run" };
}

/** What the checks receive: the findings of one round, the revisions it reviewed, and the
 *  decisions the document recorded around it. */
export type CheckInput = {
  findings: readonly Finding[];
  base: string;
  head: string;
  /** Ids an earlier round's user selection declined. */
  declined: ReadonlySet<string>;
  /** Ids selected for fixing in this round or a later one: the outcome half of the counter. */
  fixedLater?: ReadonlySet<string>;
};

/** Every hit of every finding — all of them, never only the first, because a finding that
 *  trips two checks is exactly the finding a single-signal report would flatten. */
export function checkFindings(input: CheckInput, facts: RepoFacts): CheckReport {
  const fixedLater = input.fixedLater ?? new Set<string>();
  const verdicts: Verdict[] = input.findings.map((finding) => {
    const hits = [
      phantomLocation(finding, input.base, input.head, facts),
      absenceContradicted(finding, input.base, input.head, facts),
      alreadyDecided(finding, input.declined),
    ].filter((hit): hit is Hit => hit !== null);
    return { finding, hits, isFixedLater: fixedLater.has(finding.id) };
  });
  return { verdicts, counts: tally(verdicts) };
}

function emptyTally(): Record<Signal, SignalTally> {
  return Object.fromEntries(SIGNALS.map((signal) => [signal, { annotated: 0, fixedLater: 0 }])) as Record<Signal, SignalTally>;
}

function tally(verdicts: readonly Verdict[]): Counts {
  const counts: Counts = { findings: verdicts.length, annotated: 0, clean: 0, fixedLater: 0, signals: emptyTally() };
  for (const verdict of verdicts) {
    if (verdict.hits.length === 0) {
      counts.clean += 1;
      continue;
    }
    counts.annotated += 1;
    if (verdict.isFixedLater) counts.fixedLater += 1;
    for (const hit of verdict.hits) {
      const signal = counts.signals[hit.signal];
      signal.annotated += 1;
      if (verdict.isFixedLater) signal.fixedLater += 1;
    }
  }
  return counts;
}

/** The count line, and the whole vocabulary of the run summary: `findings` is what the
 *  round produced, `annotated` is how many carry a signal (they are still in the output),
 *  `clean` are the ordinary ones, and `fixed later` is the outcome — of the annotated
 *  findings, how many were selected for fixing in this round or a later one. One line, so
 *  a status line can carry it. */
export function formatCountLine(counts: Counts): string {
  const perSignal = (read: (tally: SignalTally) => number): string =>
    SIGNALS.map((signal) => `${signal} ${read(counts.signals[signal])}`).join(", ");
  return [
    `findings ${counts.findings}`,
    `annotated ${counts.annotated} (${perSignal((tally) => tally.annotated)})`,
    `clean ${counts.clean}`,
    `fixed later ${counts.fixedLater} of ${counts.annotated} (${perSignal((tally) => tally.fixedLater)})`,
  ].join(" · ");
}

/** One annotated finding, signal first and evidence under it. Nothing is hidden: the same
 *  finding is in the review's own output, and this is the note attached to it. */
export function renderAnnotations(report: CheckReport): string[] {
  const blocks: string[][] = [];
  for (const verdict of report.verdicts) {
    if (verdict.hits.length === 0) continue;
    const { finding } = verdict;
    const path = citedPath(finding);
    const where = path === null ? null : finding.line === undefined ? path : `${path}:${finding.line}`;
    for (const hit of verdict.hits) {
      const header =
        where === null
          ? `${hit.signal}  ${finding.id} (${finding.severity})`
          : `${hit.signal}  ${where}  ${finding.id} (${finding.severity})`;
      blocks.push([header, `  ${hit.evidence}`]);
    }
  }
  return blocks.flatMap((block, index) => (index === 0 ? block : ["", ...block]));
}

/** One review round of a run, as the document records it. */
export type ReviewRound = {
  number: number;
  findings: Finding[];
  /** Ids this round's selection picked. */
  selected: ReadonlySet<string>;
  /** The selection came from the person, not from an automatic selector. */
  isUserSelection: boolean;
  head: string | null;
};

/** The rounds document, flattened: `axi rounds --step review --json` (or one of the
 *  captured runs the eval corpus stores), plus any revisions the document names. */
export type RoundDocument = { rounds: ReviewRound[]; base: string | null; head: string | null };

type RawRecord = Record<string, unknown>;

function asRecord(value: unknown): RawRecord | null {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? (value as RawRecord) : null;
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim() !== "" ? value.trim() : null;
}

function parseFinding(value: unknown): Finding | null {
  const record = asRecord(value);
  if (record === null) return null;
  const id = asString(record.id);
  const description = asString(record.description);
  if (id === null || description === null) return null;
  const file = asString(record.file) ?? "";
  const line = typeof record.line === "number" && Number.isFinite(record.line) ? record.line : undefined;
  const finding: Finding = { id, severity: asString(record.severity) ?? "unknown", file, description };
  return line === undefined ? finding : { ...finding, line };
}

/** The findings of one raw round: `findings` in a live document, `findings_json` in a
 *  captured one (a JSON string the pipeline stored). A malformed list is not a crash: the
 *  round contributes what it can prove. */
function rawFindings(record: RawRecord): Finding[] {
  const stored = record.findings_json;
  let list: unknown = record.findings;
  if (typeof stored === "string" && stored.trim() !== "") {
    try {
      list = asRecord(JSON.parse(stored))?.findings ?? [];
    } catch {
      list = [];
    }
  }
  return Array.isArray(list) ? list.map(parseFinding).filter((finding): finding is Finding => finding !== null) : [];
}

/** A list of ids, however the document carries it: the live shape writes an array, and the
 *  eval capture stores the same array as the JSON text the database column holds. Reading
 *  only the array made every id of every earlier round look declined. */
function idSet(value: unknown): Set<string> {
  let list: unknown = value;
  if (typeof value === "string") {
    try {
      list = JSON.parse(value);
    } catch {
      list = [];
    }
  }
  return new Set(Array.isArray(list) ? list.filter((item): item is string => typeof item === "string") : []);
}

/** One raw round as a ReviewRound, or null when it is another step's round. */
function parseRound(record: unknown, position: number): ReviewRound | null {
  const raw = asRecord(record);
  if (raw === null) return null;
  const step = asString(raw.step_name);
  if (step !== null && step !== "review") return null;
  const number = typeof raw.round === "number" && Number.isFinite(raw.round) ? raw.round : position + 1;
  return {
    number,
    findings: rawFindings(raw),
    selected: idSet(raw.selected_finding_ids),
    isUserSelection: raw.selection_source === "user",
    head: asString(raw.reviewed_head_sha) ?? asString(raw.head_sha),
  };
}

/** Read the document a run prints. Accepts the live shape (`{rounds:[…]}`), the captured
 *  shape (an array of rounds), and a bare `{findings:[…]}` — the last one carries no
 *  chronology, so it can be annotated but cannot measure a decline or an outcome. */
export function parseRoundDocument(text: string): RoundDocument {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch (error) {
    throw new Error(`the rounds document is not JSON: ${error instanceof Error ? error.message : String(error)}`);
  }
  if (Array.isArray(parsed)) {
    const rounds = parsed.map(parseRound).filter((round): round is ReviewRound => round !== null);
    if (rounds.length === 0) throw new Error("the rounds document has no review round: run `no-mistakes axi rounds --step review --json`");
    return { rounds: sortRounds(rounds), base: null, head: null };
  }
  const record = asRecord(parsed);
  if (record === null) throw new Error("the rounds document is not an object or an array of rounds");
  const base = asString(record.base_sha) ?? asString(record.base);
  const head = asString(record.head_sha) ?? asString(record.head);
  if (Array.isArray(record.rounds)) {
    const rounds = record.rounds.map(parseRound).filter((round): round is ReviewRound => round !== null);
    if (rounds.length === 0) throw new Error("the rounds document has no review round: run `no-mistakes axi rounds --step review --json`");
    return { rounds: sortRounds(rounds), base, head };
  }
  if (Array.isArray(record.findings)) {
    const findings = record.findings.map(parseFinding).filter((finding): finding is Finding => finding !== null);
    return { rounds: [{ number: 1, findings, selected: new Set(), isUserSelection: false, head }], base, head };
  }
  throw new Error("the document has neither rounds nor findings: pass `axi rounds --step review --json` or a `{findings:[…]}` file");
}

function sortRounds(rounds: ReviewRound[]): ReviewRound[] {
  return [...rounds].sort((left, right) => left.number - right.number);
}

/** What one round is annotated with: its own findings, the ids earlier rounds declined,
 *  and the ids this round or a later one selected for fixing. `requestedRound` picks a
 *  round from a finished run, so the same document can answer "what would this have said
 *  then, and was it right". */
export type RoundSelection = {
  number: number;
  findings: Finding[];
  declined: Set<string>;
  fixedLater: Set<string>;
  head: string | null;
  base: string | null;
};

export function selectRound(document: RoundDocument, requestedRound?: number): RoundSelection {
  const numbers = document.rounds.map((round) => round.number);
  const anchor = document.rounds.at(-1);
  if (anchor === undefined) throw new Error("the rounds document has no review round");
  const number = requestedRound ?? anchor.number;
  const reviewed = document.rounds.find((round) => round.number === number);
  if (reviewed === undefined) {
    throw new Error(`round ${number} is not in the document; its review rounds are ${numbers.join(", ")}`);
  }
  const declined = new Set<string>();
  const fixedLater = new Set<string>();
  for (const round of document.rounds) {
    if (round.number < number && round.isUserSelection) {
      for (const finding of round.findings) {
        if (!round.selected.has(finding.id)) declined.add(finding.id);
      }
      // A later round that selected the id ended the decline: a finding fixed and then
      // re-raised is an incomplete fix, not a decided theme, and must stay clean.
      for (const id of round.selected) declined.delete(id);
    }
    if (round.number >= number) for (const id of round.selected) fixedLater.add(id);
  }
  return { number, findings: reviewed.findings, declined, fixedLater, head: reviewed.head, base: document.base };
}
