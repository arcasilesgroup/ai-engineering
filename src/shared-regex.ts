/** ReDoS screening (audit: the pattern comes from config, and a catastrophic regex
 *  hangs the hook instead of answering it). The conservative shapes rejected here:
 *  a quantified group whose body is itself quantified — `(a+)+`, `(?:\w+)*`, `((a+))+`
 *  — and a quantified group whose alternatives overlap — `(a|ab)+`, `(x|)*`. One
 *  subject position then has two ways to split, and a late overall failure backtracks
 *  exponentially. This is a cheap shape filter, not a regex analyser: anything over
 *  the length cap or matching a risky shape dies at load, and an odd rule can always
 *  be rewritten as several boring ones. */
const PATTERN_CAP = 512;

const QUANTIFIER = "(?:[+*]|\\{\\d+(?:,\\d*)?\\})";

export function isReDoSSafePattern(pattern: string): boolean {
  if (pattern.length > PATTERN_CAP) return false;
  // matches() only reaches the regex engine when metacharacters are present; a bare
  // literal goes through String.includes and cannot backtrack.
  if (!/[[\](){}*+?^$|\\]/.test(pattern)) return true;
  // Quantifier characters inside a class describe no structure: blank the classes out.
  let flattened = pattern.replace(/\[(?:[^\]\\]|\\.)*\]/g, " ");
  // Shape 1, one nesting level at a time: `(a+)+` directly, and `((a+))+` once its
  // inner group has bubbled up as the marker `S*`. No analyser — each pass is a
  // bounded scan over a pattern shorter than the cap.
  const nestedQuantifier = new RegExp(`\\((?:\\?:)?[^()]*${QUANTIFIER}[^()]*\\)${QUANTIFIER}`);
  const quantifiedGroup = new RegExp(`\\((?:\\?:)?[^()]*${QUANTIFIER}[^()]*\\)`, "g");
  let previous = "";
  while (true) {
    if (nestedQuantifier.test(flattened)) return false;
    previous = flattened;
    flattened = flattened.replace(quantifiedGroup, "S*");
    if (flattened === previous) break;
  }
  // Shape 2 — alternatives of a quantified group that overlap (one is a prefix of
  // another, or an empty one): the engine has two splittings per subject position.
  for (const group of flattened.matchAll(/\((?:\?:)?([^()]*)\)[*+{]/g)) {
    const alternatives = group[1]!.split("|");
    for (let left = 0; left < alternatives.length; left++) {
      for (let right = left + 1; right < alternatives.length; right++) {
        const first = alternatives[left]!;
        const second = alternatives[right]!;
        if (first === "" || second === "" || first.startsWith(second) || second.startsWith(first)) return false;
      }
    }
  }
  return true;
}
