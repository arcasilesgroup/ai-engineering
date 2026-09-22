// Single source of the product version: package.json is the only place a
// version number is written; the binary reads it at import. `bun build
// --compile` embeds the JSON, so no filesystem access happens at runtime.
import pkg from "../package.json";

export const VERSION: string = pkg.version;

/** Numeric segment compare: "2.10.0" is newer than "2.9.0", which a string compare
 *  gets wrong in exactly the release where it matters. Negative/0/positive = a-b. */
export function compareVersions(a: string, b: string): number {
  const left = a.split(".").map((part) => Number.parseInt(part, 10) || 0);
  const right = b.split(".").map((part) => Number.parseInt(part, 10) || 0);
  for (let i = 0; i < Math.max(left.length, right.length); i += 1) {
    const diff = (left[i] ?? 0) - (right[i] ?? 0);
    if (diff !== 0) return diff;
  }
  return 0;
}
