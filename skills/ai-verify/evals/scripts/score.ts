#!/usr/bin/env bun
// Score review reports against a manifest of applied bugs.
//
// Recall is computed automatically: every applied defect is either found or it is
// not. Precision is not — deciding whether an *extra* finding is real is a
// judgment call, so this prints a triage list for you to adjudicate and then
// computes precision from your answers.
//
// Usage:
//     score.ts --run ~/.claude/evals/myrepo-20260728-101500/manifest.json
//     score.ts --run MANIFEST --reports .claude/reviews --window 8
//     score.ts --run MANIFEST --adjudicate   # recompute after editing triage.json
//
// Port of the Python scorer this replaces. The flags, the report/manifest
// parsing, the recall and precision arithmetic, the stdout shape and the exit
// codes are kept identical on purpose: evals/README.md documents this output and
// the eval harness parses it. node: stdlib only — this file is copied into a
// skill folder with no node_modules.

import { existsSync, readdirSync, readFileSync, realpathSync, statSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { basename, dirname, extname, isAbsolute, join, resolve } from "node:path";

const SEV = "CRITICAL|HIGH|MEDIUM|LOW";
const HEADING_FINDING = new RegExp(`^#{2,5}\\s*\\[(${SEV})\\]\\s*(.+)$`, "i");
const LIST_FINDING = new RegExp(`^\\s*\\d+\\.\\s*\\*\\*\\[(${SEV})\\]\\s*(.+?)\\*\\*`, "i");
const SECTION = /^#{1,5}\s+\S/;
const REF = /([A-Za-z0-9_@./\\-]+\.[A-Za-z0-9]+):(\d+)/g;
const LANE_FROM_NAME = /^(.*?)-\d{8}-\d{6}\.md$/;
// Python's str.splitlines() boundaries. String.split("\n") would leave \r and
// U+2028 inside the line, where Python has already broken it.
const LINE_BREAK = /\r\n|[\n\r\v\f\u001c-\u001e\u0085\u2028\u2029]/g;

type Finding = {
  severity: string;
  claim: string;
  body: string[];
  lane: string;
  report: string;
  /** The finding's own block, joined — what `match` patterns are tested against. */
  text: string;
  /** `[path, line]` refs lifted from `text`, backslashes normalised to slashes. */
  refs: Array<[string, number]>;
  /** `lane::claim` triage key; only set for extra findings. */
  key?: string;
};

type Bug = {
  id: string;
  class: string;
  file: string;
  line: number;
  lane?: string | null;
  expect?: string | null;
  match?: string[] | null;
  line_candidates?: number[] | null;
};

type Manifest = {
  pack?: string | null;
  /** When the pack was applied, as stamped by the applier. */
  applied_at: string;
  branch: string;
  repo: string;
  bugs: Bug[];
};

type Quality = "FOUND" | "WEAK" | "MISSED";
type Row = [Bug, Quality, Finding | null, boolean];

const PROG = basename(process.argv[1] ?? "score.ts");
const USAGE = `usage: ${PROG} [-h] --run RUN [--reports REPORTS] [--window WINDOW] [--adjudicate]`;

function die(msg: string): never {
  process.stderr.write("error: " + msg + "\n");
  process.exit(1);
}

function usageError(msg: string): never {
  process.stderr.write(`${USAGE}\n${PROG}: error: ${msg}\n`);
  process.exit(2);
}

function helpText(): string {
  return [
    USAGE,
    "",
    "Score review reports against a manifest of applied bugs.",
    "",
    "Recall is computed automatically: every applied defect is either found or it is",
    "not. Precision is not -- deciding whether an *extra* finding is real is a",
    "judgment call, so this prints a triage list for you to adjudicate and then",
    "computes precision from your answers.",
    "",
    "options:",
    "  -h, --help           show this help message and exit",
    "  --run RUN            path to the run's manifest.json",
    "  --reports REPORTS    report dir or single .md",
    "  --window WINDOW      line tolerance (default 8)",
    "  --adjudicate         use triage.json verdicts",
    "",
  ].join("\n");
}

/** Python's str() over the JSON values we interpolate: a missing key is `undefined`
 *  here and `None` there, and the report is read by humans and by the harness. */
function pyStr(v: unknown): string {
  if (v === null || v === undefined) return "None";
  if (typeof v === "string") return v;
  if (v === true) return "True";
  if (v === false) return "False";
  return String(v);
}

/** Python's `{:.0%}` rounds half to even — format(0.125, ".0%") is "12%", where
 *  Math.round gives 13. Recall and precision are exact integer ratios, so round
 *  the fraction instead of a double whose tie the JS rounding gets wrong. */
function pct(num: number, den: number): string {
  if (den <= 0) return "0%"; // `recall = ... if bugs else 0.0`
  const q = Math.floor((num * 100) / den);
  const r = (num * 100) % den;
  const n = 2 * r > den || (2 * r === den && q % 2 === 1) ? q + 1 : q;
  return `${n}%`;
}

/** Python's str.splitlines(): every line boundary, and no trailing "" from a final one. */
function splitLines(text: string): string[] {
  const lines = text.split(LINE_BREAK);
  if (text !== "" && lines[lines.length - 1] === "") lines.pop();
  return lines;
}

/** pathlib.Path(...).expanduser().resolve(): "~" expanded (Python also expands
 *  "~user"), absolute, `..` collapsed, symlinks followed — but unlike realpathSync,
 *  no requirement that the leaf exists (Python's strict=False). */
function realResolve(p: string): string {
  const expanded = p === "~" ? homedir() : p.startsWith("~/") ? join(homedir(), p.slice(2)) : p;
  let cur = resolve(expanded);
  const tail: string[] = [];
  for (;;) {
    try {
      return tail.length ? join(realpathSync(cur), ...tail.reverse()) : realpathSync(cur);
    } catch {
      const parent = dirname(cur);
      if (parent === cur) return resolve(expanded); // root: nothing left to resolve
      tail.push(basename(cur));
      cur = parent;
    }
  }
}

function laneOf(path: string): string {
  const name = basename(path);
  const ext = extname(name); // pathlib.Path.stem: drop the last suffix, if any
  return LANE_FROM_NAME.exec(name)?.[1] ?? (ext ? basename(name, ext) : name);
}

/** Split a report into findings: severity, claim, body text, file:line refs. */
function parseReport(path: string): Finding[] {
  const findings: Finding[] = [];
  let current: Finding | null = null;
  // read_text(errors="replace"): invalid bytes become U+FFFD, not a crash.
  for (const raw of splitLines(readFileSync(path, "utf8"))) {
    const m = HEADING_FINDING.exec(raw) ?? LIST_FINDING.exec(raw);
    if (m) {
      if (current) findings.push(current);
      current = {
        severity: (m[1] ?? "").toUpperCase(),
        claim: (m[2] ?? "").trim().replace(/^\*+/, "").replace(/\*+$/, ""),
        body: [raw],
        lane: laneOf(path),
        report: basename(path),
        text: "",
        refs: [],
      };
      continue;
    }
    if (current !== null) {
      // A new non-finding section ends the current finding block.
      if (SECTION.test(raw) && !HEADING_FINDING.test(raw)) {
        findings.push(current);
        current = null;
        continue;
      }
      current.body.push(raw);
    }
  }
  if (current) findings.push(current);

  for (const f of findings) {
    const text = f.body.join("\n");
    f.text = text;
    f.refs = [...text.matchAll(REF)].map((r) => [(r[1] ?? "").replace(/\\/g, "/"), Number(r[2])]);
  }
  return findings;
}

function pathMatches(refPath: string, bugPath: string): boolean {
  const a = refPath.replace(/^[./]+|[./]+$/g, "").split("/");
  const b = bugPath.replace(/^[./]+|[./]+$/g, "").split("/");
  const n = Math.min(a.length, b.length);
  if (n === 0) return false;
  const ta = a.slice(a.length - n);
  const tb = b.slice(b.length - n);
  return ta.every((part, i) => part === tb[i]);
}

/** Return [finding, quality] for the best match, or [null, null]. */
function matchBug(bug: Bug, findings: Finding[], window: number): [Finding | null, Quality | null] {
  const lines = bug.line_candidates?.length ? bug.line_candidates : [bug.line];
  const patterns = (bug.match ?? []).map((p) => new RegExp(p, "i"));
  let best: [Finding, Quality] | null = null;
  for (const f of findings) {
    const near = f.refs.some(
      ([rp, rl]) => pathMatches(rp, bug.file) && lines.some((bl) => Math.abs(rl - bl) <= window),
    );
    if (!near) continue;
    // No `match` patterns at all means location alone is a full match; with
    // patterns, only the first finding that satisfies all of them wins.
    if (patterns.length && !patterns.every((p) => p.test(f.text))) {
      best ??= [f, "WEAK"];
      continue;
    }
    return [f, "FOUND"];
  }
  return best ?? [null, null];
}

/** A verdict file written by hand: json's null is a value like any other, and
 *  Python's dict.get returns it rather than treating it as absent. */
type Triage = Record<string, string | null>;

function loadTriage(runDir: string): Triage {
  const p = join(runDir, "triage.json");
  return existsSync(p) ? (JSON.parse(readFileSync(p, "utf8")) as Triage) : {};
}

/** Python's json.dumps(..., indent=2) escapes non-ASCII (ensure_ascii): one \uXXXX
 *  per UTF-16 unit, so an emoji lands as a surrogate pair exactly as it does there. */
function asciiJson(value: unknown): string {
  return JSON.stringify(value, null, 2).replace(
    /[\u007f-\uffff]/g,
    (c) => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0"),
  );
}

function nowStamp(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}

type Args = { run: string; reports: string; window: number; adjudicate: boolean };

function parseArgs(argv: string[]): Args {
  let run: string | null = null;
  const args: Args = { run: "", reports: ".claude/reviews", window: 8, adjudicate: false };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i] ?? "";
    let name = arg;
    let inline: string | null = null;
    if (arg.startsWith("--")) {
      const eq = arg.indexOf("=");
      if (eq !== -1) {
        name = arg.slice(0, eq);
        inline = arg.slice(eq + 1);
      }
    }
    const value = (): string => inline ?? argv[++i] ?? usageError(`argument ${name}: expected one argument`);
    const flag = (): void => {
      if (inline !== null) usageError(`argument ${name}: ignored explicit argument '${inline}'`);
    };
    switch (name) {
      case "-h":
      case "--help":
        process.stdout.write(helpText());
        process.exit(0);
      case "--run":
        run = value();
        break;
      case "--reports":
        args.reports = value();
        break;
      case "--window": {
        const raw = value();
        const t = raw.trim();
        // Python's int() also takes "1_0" and non-ASCII digits; argparse users do not.
        if (!/^[+-]?\d+$/.test(t)) usageError(`argument --window: invalid int value: '${raw}'`);
        args.window = Number(t);
        break;
      }
      case "--adjudicate":
        flag();
        args.adjudicate = true;
        break;
      default:
        usageError(`unrecognized arguments: ${arg}`);
    }
  }
  if (run === null) usageError("the following arguments are required: --run");
  args.run = run;
  return args;
}

function main(): void {
  const args = parseArgs(process.argv.slice(2));

  const manifestPath = realResolve(args.run);
  if (!existsSync(manifestPath)) die(`no manifest at ${manifestPath}`);
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8")) as Manifest;
  const runDir = dirname(manifestPath);
  const bugs = manifest.bugs;

  let rp = args.reports;
  if (!isAbsolute(rp)) rp = join(manifest.repo, rp);
  const reportFiles = isFile(rp) ? [rp] : listMd(rp);
  if (reportFiles.length === 0) {
    die(`no reports found at ${rp} — did the review write its report?`);
  }

  const findings: Finding[] = [];
  for (const f of reportFiles) findings.push(...parseReport(f));
  if (findings.length === 0) {
    die(
      `parsed 0 findings from ${reportFiles.length} report file(s). Either the review found ` +
        `nothing (recall 0 — that is a result) or it did not follow the ` +
        `output contract in CONVENTIONS.md §6.`,
    );
  }

  const triage: Triage = args.adjudicate ? loadTriage(runDir) : {};

  const rows: Row[] = [];
  const matched = new Set<Finding>();
  for (const bug of bugs) {
    const [f, quality] = matchBug(bug, findings, args.window);
    if (f) {
      matched.add(f);
      const lane = bug.lane;
      const rightLane = lane === undefined || lane === null || lane === f.lane;
      rows.push([bug, quality ?? "MISSED", f, rightLane]);
    } else {
      rows.push([bug, "MISSED", null, false]);
    }
  }

  const found = rows.filter((r) => r[1] === "FOUND");
  const weak = rows.filter((r) => r[1] === "WEAK");
  const missed = rows.filter((r) => r[1] === "MISSED");
  const wrongLane = found.filter((r) => !r[3]);
  const extra = findings.filter((f) => !matched.has(f));

  const verdicts = new Map<string, string | null>();
  for (const f of extra) {
    // Keyed on lane + claim, not on position, so a triage verdict survives
    // a re-run that adds or reorders findings.
    const key = `${f.lane}::${Array.from(f.claim.replace(/\s+/g, " ")).slice(0, 70).join("")}`;
    f.key = key;
    verdicts.set(key, Object.hasOwn(triage, key) ? (triage[key] ?? null) : "unknown");
  }
  let realExtra = 0;
  let noise = 0;
  let unknown = 0;
  for (const v of verdicts.values()) {
    if (v === "real") realExtra++;
    else if (v === "noise") noise++;
    else if (v === "unknown") unknown++;
  }

  // recall is len(found)/len(bugs), or 0.0 when a manifest carries no bugs — the
  // `den <= 0` guard in pct() is where that lands.
  const truePos = found.length + realExtra;
  // Precision is undefined while any extra finding is unjudged. Treating
  // `unknown` as real is exactly the flattery this harness exists to prevent.
  const precision = unknown === 0 && truePos + noise ? truePos / (truePos + noise) : null;

  const stamp = nowStamp();
  const out = [
    `# Eval score — ${pyStr(manifest.pack)}`,
    "",
    `**Run:** \`${manifest.branch}\` · applied ${manifest.applied_at} · scored ${stamp}`,
    `**Reports:** ${reportFiles.map((f) => basename(f)).join(", ")}`,
    `**Findings parsed:** ${findings.length} · line tolerance ±${args.window}`,
    "",
    "| Metric | Value |",
    "|---|---|",
    `| **Recall** | **${pct(found.length, bugs.length)}** (${found.length}/${bugs.length} applied defects found) |`,
    `| Weak matches | ${weak.length} (right location, claim does not describe the defect) |`,
    `| Wrong lane | ${wrongLane.length} (found, but by a lane that does not own it) |`,
    `| **Precision** | ${
      precision !== null
        ? `**${pct(truePos, truePos + noise)}** (${truePos} real / ${truePos + noise} judged)`
        : `pending — ${unknown} extra findings need adjudication`
    } |`,
    "",
    "## Applied defects",
    "",
    "| ID | Class | Expected lane | Where | Result | Found by |",
    "|---|---|---|---|---|---|",
  ];
  const mark: Record<Quality, string> = { FOUND: "✅ found", WEAK: "⚠️ weak", MISSED: "❌ missed" };
  for (const [bug, quality, f, rightLane] of rows) {
    let by = f ? f.lane : "—";
    if (f && !rightLane) by += " ⚠️";
    out.push(
      `| ${pyStr(bug.id)} | ${pyStr(bug.class)} | ${"lane" in bug ? pyStr(bug.lane) : "—"} | \`${pyStr(bug.file)}:${pyStr(bug.line)}\` | ${mark[quality]} | ${by} |`,
    );
  }

  if (missed.length || weak.length) {
    out.push("", "## Misses — read these, they are the point", "");
    for (const [bug, quality] of rows) {
      if (quality === "MISSED" || quality === "WEAK") {
        out.push(
          `- **${pyStr(bug.id)} (${mark[quality].split(" ").at(-1)})** — ${
            "expect" in bug ? pyStr(bug.expect) : pyStr(bug.class)
          } — \`${pyStr(bug.file)}:${pyStr(bug.line)}\`${
            quality === "MISSED" ? "" : "  ← flagged the line, described it wrong"
          }`,
        );
      }
    }
  }

  out.push(
    "",
    "## Extra findings — adjudicate these",
    "",
    "Mark each `real` or `noise` in `triage.json`, then re-run with " +
      "`--adjudicate`. A finding you cannot decide about is noise: if the " +
      "report did not make it decidable, it would not have been actioned either.",
    "",
  );
  if (extra.length === 0) out.push("_None. Every finding mapped to an applied defect._");
  for (const f of extra) {
    out.push(`- \`"${pyStr(f.key)}"\` — **[${f.severity}]** ${f.claim} _(from ${f.lane})_`);
  }

  const reportMd = join(runDir, `score-${stamp}.md`);
  writeFileSync(reportMd, out.join("\n") + "\n", "utf8");

  const triagePath = join(runDir, "triage.json");
  if (extra.length && !existsSync(triagePath)) {
    writeFileSync(
      triagePath,
      asciiJson(Object.fromEntries(extra.map((f) => [f.key, "unknown"]))),
      "utf8",
    );
  }

  console.log(
    `recall    ${pct(found.length, bugs.length)}  (${found.length}/${bugs.length} found, ${weak.length} weak, ${missed.length} missed)`,
  );
  if (precision !== null) {
    console.log(`precision ${pct(truePos, truePos + noise)}  (${truePos} real / ${truePos + noise} judged)`);
  } else {
    console.log(`precision pending — adjudicate ${unknown} findings in ${triagePath}`);
  }
  console.log(reportMd);
}

/** rp.is_file(): follows symlinks, false for a directory or a broken link. */
function isFile(p: string): boolean {
  try {
    return statSync(p).isFile();
  } catch {
    return false;
  }
}

/** sorted(rp.glob("*.md")): no recursion, case-sensitive suffix. Unlike a shell,
 *  pathlib's glob does match a leading-dot name (.draft.md) — verified against the
 *  original on this repo's Python; do not "fix" this to a shell dotfile rule. */
function listMd(dir: string): string[] {
  let names: string[];
  try {
    names = readdirSync(dir);
  } catch {
    return [];
  }
  return names
    .filter((n) => n.endsWith(".md"))
    .sort()
    .map((n) => join(dir, n));
}

main();
