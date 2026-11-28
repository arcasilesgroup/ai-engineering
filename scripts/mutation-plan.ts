// Will the campaign fit in the job's ceiling? Answer it before the campaign starts.
//
// A ceiling below the real work does not report a failure: GitHub cancels the job,
// the check shows "cancelled", and a cancelled check reads like weather. The campaign
// was 40 minutes while the core had grown past it, so every nightly died at the wall
// and no coverage was ever delivered. This script turns that silent kill into a
// refusal that names the estimate, the ceiling and the way out.
//
// Every constant below is measured on a hosted runner, not calibrated on a laptop. The
// one that decides everything is the rate, and it took a cancelled run to measure it
// honestly: a campaign that reuses results is not a campaign that runs them.
//
// The three green nightlies reused most of their mutants, so only the fresh ones were
// executed, and only those cost time:
//
//   run 44730630181 — 2026-11-20, green. 9,056 instrumented, 5,764 reused, 3,292 fresh
//     in 28m20s → 116 fresh mutants a minute.
//   run 44898202664 — 2026-11-21, green. 9,126 instrumented, 5,752 reused, 3,374 fresh
//     in 27m35s → 122 a minute.
//   run 45018016173 — 2026-11-22, green. 9,126 instrumented, 5,671 reused, 3,455 fresh
//     in 28m33s → 121 a minute.
//
// Three runs agreeing within 2% is the measurement: about 120 fresh mutants a minute in
// November, on a 2,446-test suite.
//
//   run 46146987123 — 2026-11-28, workflow_dispatch, cancelled at 90 minutes. 12,033
//     instrumented, 4,688 reused, 7,345 fresh, and the mutation phase had not finished
//     after 87m39s of it. So the rate has fallen to at most 84 fresh mutants a minute:
//     the suite it re-runs for every mutant grew to 2,750 tests, and per-mutant cost
//     grows with the covering set. MUTANTS_PER_MINUTE takes the conservative 60, which
//     is that ceiling divided by 1.4 — a campaign refused here is loud, a campaign
//     cancelled at the wall is silent, so the estimate is allowed to be pessimistic.
//   runs 45999985299 and 46146987123 — the dry run took 2m05s over 2,703 tests and 2m16s
//     over 2,750, so DRY_RUN_MINUTES is 3.
//
// The density of a file is measured from the restored incremental report, whose entries
// carry the file's source as well as its mutants. Reading it per file, and multiplying
// by the file's size *now*, is what stops a report a week old from under-estimating a
// guard that grew.
//
// Usage: bun scripts/mutation-plan.ts --ceiling <minutes> [--report <path>] [--root <dir>] <file>[,<file>…]
// Exit:  0 the campaign fits · 1 it does not · 2 the arguments do not make a plan.
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

/** 120 fresh mutants a minute measured, degraded to 60 for the grown suite: see the header. */
export const MUTANTS_PER_MINUTE = 60;
/** 2m05s over 2,703 tests on 2026-11-27 and 2m16s over 2,750 on 2026-11-28. */
export const DRY_RUN_MINUTES = 3;
/** Checkout, Bun, dependencies and the artifact upload: about 15 seconds measured. */
export const SETUP_MINUTES = 1;
/** 12,183 mutants over 6,608 source lines is 1.84 a line; rounded up, for a file the report never saw. */
export const MUTANTS_PER_LINE = 2;

type ReportEntry = { mutants?: Record<string, { status?: string }>; source?: string };
type Report = { files?: Record<string, ReportEntry> };

export type CampaignPlan = {
  files: string[];
  mutants: number;
  minutes: number;
  ceiling: number;
  fits: boolean;
};

export type PlanOptions = {
  root: string;
  files: string[];
  ceiling: number;
  reportPath?: string;
};

/** The lines a text has, with a trailing newline terminating the last one instead of adding one. */
function countLines(text: string): number {
  if (text === "") return 0;
  return (text.endsWith("\n") ? text.slice(0, -1) : text).split("\n").length;
}

function readReport(path: string): Report | undefined {
  if (!existsSync(path)) return undefined;
  try {
    return JSON.parse(readFileSync(path, "utf8")) as Report;
  } catch {
    // A corrupt report is not a reason to refuse a campaign: the density falls back to
    // the measured one, which under-estimates nothing.
    return undefined;
  }
}

/** Mutants a file actually runs: the static ones Stryker marks `Ignored` decide nothing. */
function liveMutants(entry: ReportEntry): number {
  return Object.values(entry.mutants ?? {}).filter((mutant) => mutant.status !== "Ignored").length;
}

/** Mutants per source line for one file, measured from the report it appears in. */
function densityOf(entry: ReportEntry | undefined): number {
  if (!entry?.source) return MUTANTS_PER_LINE;
  const lines = countLines(entry.source);
  const live = liveMutants(entry);
  if (lines <= 0 || live <= 0) return MUTANTS_PER_LINE;
  return live / lines;
}

export function planCampaign(options: PlanOptions): CampaignPlan {
  const report = options.reportPath ? readReport(options.reportPath) : undefined;
  const files = [...options.files].sort();
  let mutants = 0;
  for (const file of files) {
    const full = join(options.root, file);
    const lines = existsSync(full) ? countLines(readFileSync(full, "utf8")) : 0;
    mutants += Math.ceil(lines * densityOf(report?.files?.[file]));
  }
  // The dry run and the setup are paid once per campaign, whatever its size; a campaign
  // with nothing to mutate pays neither, because it does not start.
  const minutes = mutants === 0 ? 0 : Math.ceil(SETUP_MINUTES + DRY_RUN_MINUTES + mutants / MUTANTS_PER_MINUTE);
  return { files, mutants, minutes, ceiling: options.ceiling, fits: minutes <= options.ceiling };
}

export function planLines(plan: CampaignPlan): string {
  return [
    `mutation plan: ${plan.mutants} mutants over ${plan.files.length} file(s), about ${plan.minutes} minute(s) against a ${plan.ceiling}-minute ceiling`,
    ...plan.files.map((file) => `  ${file}`),
  ].join("\n");
}

export function refusalMessage(plan: CampaignPlan): string {
  return (
    `::error::refused before it starts: this campaign would take about ${plan.minutes} minute(s) ` +
    `(${plan.mutants} mutants over ${plan.files.length} file(s) at ${MUTANTS_PER_MINUTE} a minute, plus a dry run) ` +
    `and the job is capped at ${plan.ceiling}. It is not started, so it is not killed at the ceiling and read as ` +
    `"cancelled". Split the surface, or raise the job's timeout-minutes and its mutation-plan --ceiling together.`
  );
}

/** Comma and newline both separate files, so a step can hand over either form. */
function splitSurface(args: string[]): string[] {
  const files = args
    .flatMap((argument) => argument.split(/[,\n]/))
    .map((file) => file.trim())
    .filter((file) => file !== "");
  return [...new Set(files)];
}

function parseArgs(argv: string[]): { ceiling: number; reportPath?: string; root: string; files: string[] } | undefined {
  let ceiling: number | undefined;
  let reportPath: string | undefined;
  let root = process.cwd();
  const surface: string[] = [];
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index] ?? "";
    if (argument === "--ceiling") {
      ceiling = Number(argv[index + 1]);
      index += 1;
    } else if (argument === "--report") {
      reportPath = argv[index + 1];
      index += 1;
    } else if (argument === "--root") {
      root = argv[index + 1] ?? root;
      index += 1;
    } else {
      surface.push(argument);
    }
  }
  if (ceiling === undefined || !Number.isFinite(ceiling) || ceiling <= 0) return undefined;
  const files = splitSurface(surface);
  return reportPath === undefined ? { ceiling, root, files } : { ceiling, reportPath, root, files };
}

if (import.meta.main) {
  const parsed = parseArgs(process.argv.slice(2));
  if (!parsed) {
    process.stderr.write("mutation-plan: --ceiling <minutes> is required and must be a positive number\n");
    process.exit(2);
  }
  const plan = planCampaign(parsed);
  process.stdout.write(`${planLines(plan)}\n`);
  if (!plan.fits) {
    // stdout, because that is where the runner reads a `::error::` workflow command from.
    process.stdout.write(`${refusalMessage(plan)}\n`);
    process.exit(1);
  }
}
