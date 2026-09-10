// Hash helper for the canon gates: doctor verifies every installed skill against
// the binary's embedded payload, uninstall matches the lock's recorded sha256.
// The frontmatter rules themselves live in tests/skills.spec.ts (the canon gate).

import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";

export function hashFile(path: string): string {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}
