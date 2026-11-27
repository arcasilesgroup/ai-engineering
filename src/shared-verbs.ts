// src/shared-verbs.ts — the verb name is the first thing a human gets wrong, and
// `unknown verb: chian` is not an answer. No ai-eng output ends on an
// error without the line of action that follows it.
//
// It lives here rather than in cli.ts because cli.ts runs main() on import and so
// cannot be a pure seam — and the suggestion is the part worth testing.

import { CI_PROVIDERS } from "./env.ts";

/** One flag a verb answers to, with the answer it gives. */
export type VerbFlag = { readonly flag: string; readonly helps: string };

/** A verb as every surface needs it: one line for the menu, and the usage, flags and
 *  note that `ai-eng <verb> --help` prints. The two live together so a verb cannot be
 *  listed without being explainable. */
export type VerbEntry = {
  readonly verb: string;
  readonly description: string;
  /** One line after `usage: `, arguments and optional flags included. */
  readonly usage: string;
  readonly flags: readonly VerbFlag[];
  /** One paragraph under the flags: what the flags cannot say in a column. */
  readonly note?: string;
};

/** The verbs a person types, in help order, each with its one-line --help answer. */
export const HUMAN_VERBS: readonly VerbEntry[] = [
  {
    verb: "init",
    description: "install the contract in this repo (--global = this machine)",
    usage: "ai-eng init [--yes] [--global] [--surface <host,host>] [--ci <provider>]",
    flags: [
      { flag: "--yes", helps: "take every default instead of asking" },
      { flag: "--global", helps: "repair this machine's canon and stop; the repo is untouched" },
      { flag: "--surface", helps: "with --yes, install these hosts only — an advisory host is refused" },
      { flag: "--ci", helps: `write the CI template for one of ${CI_PROVIDERS.join(", ")}` },
    ],
    note: "The host picker starts with the hosts detected in this repo ticked; --surface takes effect with --yes.",
  },
  {
    verb: "doctor",
    description: "verify hooks, canon, and one live deny",
    usage: "ai-eng doctor [--gc]",
    flags: [{ flag: "--gc", helps: "delete receipts and artifacts past their retention window" }],
    note: "It sends a real attack payload through the guard: a doctor that only reads files is not evidence. Exit 2 means a check failed.",
  },
  {
    verb: "config",
    description: "change surfaces or the CI provider",
    usage: "ai-eng config [--add <host>] [--remove <host>] [--ci <provider>]",
    flags: [
      { flag: "--add", helps: "start governing this host too" },
      { flag: "--remove", helps: "stop governing this host" },
      { flag: "--ci", helps: `switch the CI template to one of ${CI_PROVIDERS.join(", ")}` },
    ],
    note: "With none of the three it asks, one question at a time.",
  },
  {
    verb: "update",
    description: "install a newer binary, then sync this repo",
    usage: "ai-eng update [--yes]",
    flags: [{ flag: "--yes", helps: "install the newer binary without asking" }],
    note: "It asks the registry for a newer release, installs it, then syncs this machine and this repo to the files that binary carries.",
  },
  {
    verb: "work",
    description: "list lanes; park, resume, tidy, or drop",
    usage: "ai-eng work [--json] | tidy | park <branch> <reason> [--until <YYYY-MM-DD>] | resume <branch> | drop <branch> | release",
    flags: [
      { flag: "--json", helps: "the lane board as JSON, for a program" },
      { flag: "--until", helps: "on park: the date the lane is expected back" },
    ],
    note: "Bare `work` prints the board. tidy closes the lanes that have landed and drop archives one; park keeps a lane for later and resume reopens it; release frees this folder's session lease.",
  },
  {
    verb: "uninstall",
    description: "remove ai-eng here; keep your files",
    usage: "ai-eng uninstall",
    flags: [],
    note: "Removes the files init installed in this repo; the extra scope takes it off this machine too. Your own files and your own hooks stay.",
  },
];

/** Verbs typed by agents and hooks. One line each in --help, same column as the human verbs. */
export const MACHINE_VERBS: readonly VerbEntry[] = [
  {
    verb: "chain",
    description: "hook decision, JSON in, JSON out",
    usage: "ai-eng chain <event> [--surface <host>] < payload.json",
    flags: [{ flag: "--surface", helps: "the host whose payload dialect to read (default claude-code)" }],
    note:
      "Events: PreToolUse, Stop, PostToolUse, UserPromptSubmit, SessionStart, SessionEnd. Where the verdict lands depends on the host: claude-code reads the exit code, so a deny exits 2 and an allow says nothing; cursor, codex and copilot read the JSON on stdout and exit 0.",
  },
  {
    verb: "git",
    description: "pre-commit, commit-msg, pre-push",
    usage: "ai-eng git <pre-commit|commit-msg|pre-push> [msgfile]",
    flags: [],
    note: "The hook entry points the installer wires into .git/hooks. The hook runs them; you rarely type this.",
  },
  {
    verb: "wrap",
    description: "run tests, print failures only",
    usage: "ai-eng wrap test --base64 <encoded command>",
    flags: [],
    note: "The guard rewrites a test command to this shape. Run it by hand only to reproduce what that rewrite ran.",
  },
  {
    verb: "worktree",
    description: "new, list, merge, rm a lane checkout",
    usage: "ai-eng worktree new <branch> | list [<slug>] | merge <slug> | request-changes <slug> <sha> | rm <slug> [--force]",
    flags: [{ flag: "--force", helps: "on rm: also permanently delete ignored files inside the checkout" }],
    note: "A lane is one branch in its own checkout. merge lands it; rm removes the checkout, never the branch.",
  },
  {
    verb: "findings",
    description: "annotate the findings of a git diff review",
    usage: "ai-eng findings check <rounds.json|-> [--json] [--round <n>] [--base <rev>] [--head <rev>]",
    flags: [
      { flag: "--json", helps: "counts and per-finding verdicts as one JSON object" },
      { flag: "--round", helps: "read round n of a document that holds several" },
      { flag: "--base", helps: "the commit the review started from; inferred when the document says" },
      { flag: "--head", helps: "the commit the review looked at; defaults to HEAD" },
    ],
    note:
      "It attaches the evidence a program can check to each finding of a review of a git diff: the file and line the finding cites, the lines the diff added, and the ids earlier rounds declined or later fixed. The annotation is a note, not a verdict: nothing is removed and a hit exits 0.\n\n" +
      "The generic input is a `{findings: [...]}` file plus --base and --head. A review tool that prints its rounds as JSON can be piped in instead: `no-mistakes` is a review pipeline whose `axi` command does it, as in `no-mistakes axi rounds --step review --json` (that is the worked example, not a requirement).",
  },
];

/** Every verb the binary answers to. */
export const ALL_VERBS: readonly string[] = [
  ...HUMAN_VERBS.map((entry) => entry.verb),
  ...MACHINE_VERBS.map((entry) => entry.verb),
];

/** `ai-eng <verb> --help`, or null for a verb this binary does not have. The caller
 *  falls back to the global menu only when nothing was named: someone who asked about
 *  `findings` is not asking what `ai-eng` is. */
export function renderVerbHelp(verb: string): string | null {
  const entry = [...HUMAN_VERBS, ...MACHINE_VERBS].find((candidate) => candidate.verb === verb);
  if (entry === undefined) return null;
  const lines = [`ai-eng ${entry.verb} · ${entry.description}`, "", `usage: ${entry.usage}`];
  if (entry.flags.length > 0) {
    const flagWidth = Math.max(...entry.flags.map((item) => item.flag.length)) + 2;
    lines.push("");
    for (const { flag, helps } of entry.flags) lines.push(`  ${flag.padEnd(flagWidth)}${helps}`);
  }
  if (entry.note !== undefined) lines.push("", entry.note);
  lines.push("", "Run 'ai-eng --help' for every verb.");
  return `${lines.join("\n")}\n`;
}

/** Levenshtein, two rows. The inputs are short and there is no dependency to add. */
export function editDistance(a: string, b: string): number {
  let previous: number[] = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i += 1) {
    const current: number[] = [i];
    for (let j = 1; j <= b.length; j += 1) {
      const substitute = (previous[j - 1] ?? 0) + (a[i - 1] === b[j - 1] ? 0 : 1);
      current[j] = Math.min(substitute, (previous[j] ?? 0) + 1, (current[j - 1] ?? 0) + 1);
    }
    previous = current;
  }
  return previous[b.length] ?? 0;
}

/** The nearest verb, when one is close enough to be worth naming. Two edits, never
 *  less — a transposition (`chian` → `chain`) costs two in plain Levenshtein and is
 *  the most common typo there is. The floor of 2 keeps `xyz` from becoming "git". */
export function suggestVerb(input: string, verbs: readonly string[] = ALL_VERBS): string | null {
  const typed = input.trim().toLowerCase();
  if (typed.length === 0) return null;
  let best: string | null = null;
  let bestDistance = Number.POSITIVE_INFINITY;
  for (const verb of verbs) {
    const distance = editDistance(typed, verb);
    if (distance < bestDistance) {
      bestDistance = distance;
      best = verb;
    }
  }
  return best !== null && bestDistance <= Math.max(2, Math.floor(typed.length / 3)) ? best : null;
}
