// src/shared-verbs.ts — the verb name is the first thing a human gets wrong, and
// `unknown verb: chian` is not an answer. No ai-eng output ends on an
// error without the line of action that follows it.
//
// It lives here rather than in cli.ts because cli.ts runs main() on import and so
// cannot be a pure seam — and the suggestion is the part worth testing.

/** The verbs a person types, in help order, each with its one-line --help answer. */
export const HUMAN_VERBS: readonly { readonly verb: string; readonly description: string }[] = [
  { verb: "init", description: "install the contract in this repo (--global = this machine)" },
  { verb: "doctor", description: "verify hooks, canon, and one live deny" },
  { verb: "config", description: "change surfaces or the CI provider" },
  { verb: "update", description: "install a newer binary, then sync this repo" },
  { verb: "work", description: "list lanes; tidy, park, or drop to close one" },
  { verb: "uninstall", description: "remove ai-eng here; keep your files" },
];

/** Verbs typed by agents and hooks. One line each in --help, same column as the human verbs. */
export const MACHINE_VERBS: readonly { readonly verb: string; readonly description: string }[] = [
  { verb: "chain", description: "hook decision, JSON in, JSON out" },
  { verb: "git", description: "pre-commit, commit-msg, pre-push" },
  { verb: "wrap", description: "run tests, print failures only" },
  { verb: "worktree", description: "new, list, merge, rm a lane checkout" },
  { verb: "findings", description: "annotate review findings a program can disprove" },
];

/** Every verb the binary answers to. */
export const ALL_VERBS: readonly string[] = [
  ...HUMAN_VERBS.map((entry) => entry.verb),
  ...MACHINE_VERBS.map((entry) => entry.verb),
];

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
