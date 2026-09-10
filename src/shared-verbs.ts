// src/shared-verbs.ts — the verb name is the first thing a human gets wrong, and
// `unknown verb: chian` was the whole answer. §14.5b: no ai-eng output ends on an
// error without the line of action that follows it.
//
// It lives here rather than in cli.ts because cli.ts runs main() on import and so
// cannot be a pure seam — and the suggestion is the part worth testing.

/** Every verb the binary answers to. The four machine verbs stay out of TAB and
 *  --help (§14) — but a human who types `ai-eng chian` still deserves the answer. */
export const ALL_VERBS: readonly string[] = [
  "init",
  "doctor",
  "config",
  "update",
  "upgrade",
  "uninstall",
  "chain",
  "git",
  "wrap",
  "spec",
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
