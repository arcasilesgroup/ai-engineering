#!/usr/bin/env bun
// skills/ai-verify/evals/scripts/apply-pack.ts — apply a pack of known defects
// to a working repo, on a scratch branch. Stdlib (node:) only: this runs from a
// skill folder with no node_modules.
//
// The answer key never enters the repo. It is written to a run directory outside
// the working tree, because a review that finds the bugs by reading the list of
// bugs tells you nothing.
//
// Usage:
//     bun apply-pack.ts --pack evals/packs/example-node-web/answer-key.json [--repo .] [--out DIR]
//     bun apply-pack.ts --cleanup                 # from inside the repo, drop the scratch branch

import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, realpathSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { basename, join, resolve } from "node:path";

const RUN_ROOT = join(homedir(), ".claude", "evals");

const USAGE =
  "usage: apply-pack.ts [-h] [--pack PACK] [--repo REPO] [--out OUT] [--branch BRANCH]\n" +
  "                     [--cleanup]";

const HELP = `${USAGE}

Apply a pack of known defects to a working repo, on a scratch branch.

The answer key never enters the repo. It is written to a run directory outside
the working tree, because a review that finds the bugs by reading the list of
bugs tells you nothing.

Usage:
    bun apply-pack.ts --pack evals/packs/example-node-web/answer-key.json [--repo .] [--out DIR]
    bun apply-pack.ts --cleanup                 # from inside the repo, drop the scratch branch

options:
  -h, --help  show this help message and exit
  --pack PACK  path to an answer-key.json
  --repo REPO  repo to apply into (default: cwd)
  --out OUT    run directory (default: ~/.claude/evals/<repo>-<stamp>)
  --branch BRANCH
               branch name (default: eval/<pack>-<stamp>)
  --cleanup    delete the current eval branch
`;

interface Bug {
  id: string;
  class: string;
  lane: string;
  severity: string;
  file: string;
  find: string;
  replace: string;
  /** 1-indexed; which of several identical `find` hits to use. */
  occurrence?: number | null;
  expect?: string;
  match?: string[];
  // Added while applying, so they land in the manifest next to the pack fields.
  line_at_apply: number;
  line_candidates: number[];
  line: number;
}

interface Pack {
  pack?: string | null;
  bugs?: Bug[];
}

interface Args {
  pack?: string;
  repo: string;
  out?: string;
  branch?: string;
  cleanup: boolean;
  help: boolean;
}

function die(msg: string): never {
  process.stderr.write("error: " + msg + "\n");
  process.exit(1);
}

/** argparse-style usage failure: usage + message on stderr, exit 2. */
function usageError(msg: string): never {
  process.stderr.write(USAGE + "\n");
  process.stderr.write(`apply-pack.ts: error: ${msg}\n`);
  process.exit(2);
}

/** Python's str() for the values that reach a message here: None is spelled out. */
function pyStr(value: unknown): string {
  return value === null || value === undefined ? "None" : String(value);
}

/**
 * argv parsing. Hand-rolled because the port must ship without dependencies.
 * Unlike argparse it does not accept unambiguous long-option abbreviations
 * (`--cle`); nothing here relies on that.
 */
function parseArgs(argv: string[]): Args {
  const args: Args = { repo: ".", cleanup: false, help: false };
  for (let i = 0; i < argv.length; i++) {
    const raw = argv[i]!;
    const eq = raw.indexOf("=");
    const flag = eq === -1 ? raw : raw.slice(0, eq);
    const inline = eq === -1 ? undefined : raw.slice(eq + 1);
    const take = (): string => {
      if (inline !== undefined) return inline;
      const next = argv[++i];
      if (next === undefined || next.startsWith("-")) {
        usageError(`argument ${flag}: expected one argument`);
      }
      return next;
    };
    switch (flag) {
      case "-h":
      case "--help":
        args.help = true;
        break;
      case "--pack":
        args.pack = take();
        break;
      case "--repo":
        args.repo = take();
        break;
      case "--out":
        args.out = take();
        break;
      case "--branch":
        args.branch = take();
        break;
      case "--cleanup":
        args.cleanup = true;
        break;
      default:
        usageError(`unrecognized arguments: ${raw}`);
    }
  }
  return args;
}

function git(repo: string, ...args: string[]): string {
  const proc = spawnSync("git", ["-C", repo, ...args], { encoding: "utf8" });
  if (proc.status !== 0) {
    die(`git ${args.join(" ")} failed:\n${(proc.stderr ?? "").trim()}`);
  }
  return proc.stdout.trim();
}

function requireClean(repo: string): void {
  if (git(repo, "status", "--porcelain")) {
    die(
      "working tree is dirty. Commit or stash first — applying a pack on top of " +
        "uncommitted work makes the diff scope meaningless.",
    );
  }
}

function lineOf(text: string, index: number): number {
  return (text.slice(0, index).match(/\n/g)?.length ?? 0) + 1;
}

/**
 * Every non-overlapping literal occurrence of `needle`, in order. Python used
 * re.finditer(re.escape(needle)); scanning for the literal is the same thing
 * without carrying a regex engine — except for the empty needle, which Python
 * matches at every position including one past the end, so it is spelled out.
 */
function findHits(text: string, needle: string): number[] {
  if (needle === "") return Array.from({ length: text.length + 1 }, (_, i) => i);
  const hits: number[] = [];
  // Advance past the whole match: re.finditer is non-overlapping, so "  " in
  // four spaces is two hits, not three.
  for (let i = text.indexOf(needle); i !== -1; i = text.indexOf(needle, i + needle.length)) {
    hits.push(i);
  }
  return hits;
}

/** Apply one find/replace edit. Returns the 1-indexed line it landed on. */
function applyBug(repo: string, bug: Bug): number {
  const path = join(repo, bug.file);
  if (!existsSync(path)) die(`bug ${bug.id}: file not found: ${bug.file}`);

  const text = readFileSync(path, "utf8");
  const find = bug.find;
  const hits = findHits(text, find);

  if (hits.length === 0) {
    die(
      `bug ${bug.id}: \`find\` text not present in ${bug.file}. The pack has drifted from ` +
        "the repo — update the pack, do not loosen the match.",
    );
  }

  const want = bug.occurrence ?? null;
  let idx: number;
  if (want === null) {
    if (hits.length > 1) {
      die(
        `bug ${bug.id}: \`find\` matches ${hits.length} times in ${bug.file}. Make it unique or set ` +
          '"occurrence".',
      );
    }
    idx = hits[0]!;
  } else {
    if (want < 1 || want > hits.length) {
      die(`bug ${bug.id}: occurrence ${want} requested, only ${hits.length} matches`);
    }
    idx = hits[want - 1]!;
  }

  const line = lineOf(text, idx);
  writeFileSync(path, text.slice(0, idx) + bug.replace + text.slice(idx + find.length), "utf8");
  return line;
}

/**
 * Re-derive line numbers from the final file contents.
 *
 * Two bugs in one file shift each other, so apply-time lines are only a
 * fallback (used when `replace` is empty, i.e. a deletion).
 */
function resolveLines(repo: string, bugs: Bug[]): void {
  for (const bug of bugs) {
    const replace = bug.replace;
    if (!replace.trim()) {
      bug.line = bug.line_at_apply;
      bug.line_candidates = [bug.line_at_apply];
      continue;
    }
    const text = readFileSync(join(repo, bug.file), "utf8");
    const hits = findHits(text, replace).map((i) => lineOf(text, i));
    bug.line_candidates = hits.length ? hits : [bug.line_at_apply];
    bug.line = bug.line_candidates[0]!;
  }
}

function cleanup(repo: string): void {
  const branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD");
  if (!branch.startsWith("eval/")) {
    die(`current branch is '${branch}', not an eval branch. Refusing.`);
  }
  requireClean(repo);
  git(repo, "checkout", "-");
  git(repo, "branch", "-D", branch);
  process.stdout.write(`removed branch ${branch}\n`);
}

/**
 * Python's json.dumps(ensure_ascii=True): JSON.stringify already matches its
 * key order, 2-space indent and no trailing newline, but leaves non-ASCII
 * characters raw. The manifest is an answer key, so the bytes stay identical.
 */
function pythonJson(value: unknown): string {
  return JSON.stringify(value, null, 2).replace(/[\u0080-\uffff]/g, (ch) => {
    return "\\u" + ch.charCodeAt(0).toString(16).padStart(4, "0");
  });
}

function stampNow(): string {
  const d = new Date();
  const p = (n: number): string => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}` +
    `-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`
  );
}

function main(): void {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    process.stdout.write(HELP);
    return;
  }

  // Python's Path.resolve() is realpath, so /tmp becomes /private/tmp on macOS
  // and every path in the manifest and the closing checklist matches. It throws
  // on a path that does not exist; Python still returns one, hence the fallback.
  let repo: string;
  try {
    repo = realpathSync(args.repo);
  } catch {
    repo = resolve(args.repo);
  }
  if (!existsSync(join(repo, ".git"))) die(`${repo} is not a git repository`);

  if (args.cleanup) {
    cleanup(repo);
    return;
  }

  if (!args.pack) die("--pack is required (or --cleanup)");

  const pack = JSON.parse(readFileSync(args.pack, "utf8")) as Pack;
  const bugs = pack.bugs ?? [];
  if (bugs.length === 0) die("pack contains no bugs");

  const ids = bugs.map((b) => b.id);
  if (new Set(ids).size !== ids.length) die("duplicate bug ids in pack");

  requireClean(repo);
  const stamp = stampNow();
  const base = git(repo, "rev-parse", "HEAD");
  const baseBranch = git(repo, "rev-parse", "--abbrev-ref", "HEAD");
  const packName = "pack" in pack ? pack.pack : "pack";
  const branch = args.branch || `eval/${pyStr(packName)}-${stamp}`;

  git(repo, "checkout", "-b", branch);

  for (const bug of bugs) {
    bug.line_at_apply = applyBug(repo, bug);
  }
  resolveLines(repo, bugs);

  git(repo, "add", "-A");
  git(repo, "commit", "-m", `eval: apply ${pyStr(pack.pack)} (${bugs.length} defects)`);
  const head = git(repo, "rev-parse", "HEAD");

  // Left as given, not resolved: pathlib.Path(args.out) is relative to cwd and
  // its relative spelling is what the printed manifest path keeps.
  const out = args.out ? args.out : join(RUN_ROOT, `${basename(repo)}-${stamp}`);
  mkdirSync(out, { recursive: true });
  const manifest = {
    pack: pack.pack ?? null,
    applied_at: stamp,
    repo,
    base_branch: baseBranch,
    base_commit: base,
    branch,
    head_commit: head,
    bugs,
  };
  const manifestPath = join(out, "manifest.json");
  writeFileSync(manifestPath, pythonJson(manifest), "utf8");

  process.stdout.write(`applied ${bugs.length} defects on branch ${branch}\n`);
  for (const bug of bugs) {
    process.stdout.write(
      `  ${bug.id.padEnd(4)} ${bug.class.padEnd(24)} ${bug.file}:${bug.line}\n`,
    );
  }
  process.stdout.write("\n");
  process.stdout.write(`answer key: ${manifestPath}\n`);
  process.stdout.write("  It is outside the repo on purpose. Do not show it to the reviewer,\n");
  process.stdout.write("  do not paste it into the session, do not let an agent read it.\n");
  process.stdout.write("\n");
  process.stdout.write("next:\n");
  process.stdout.write(`  1. run the review skill under test against \`${baseBranch}...HEAD\`\n`);
  process.stdout.write(`  2. score.ts --run ${manifestPath}\n`);
  process.stdout.write(`  3. apply-pack.ts --repo ${repo} --cleanup\n`);
}

main();
