// Generated payload artifacts match their source — the class, not one instance.
//
// gen-assets.ts writes three things: the chain bundle (a `bun build` of
// scripts/chain-entry.ts), the `.embed` fixture copies, and src/assets.ts. All three
// are committed, so all three can silently disagree with what they were made from.
// Two of them disagree in silence and are gated here:
//
//   · the chain bundle — it is what every in-process surface plants as the guard that
//     runs inside the host (gen-assets.ts:26-37). Measured 2026-09-10: a chain fix
//     lived in src/ while every planted guard still ran the old code, and doctor
//     reported the chain green.
//   · the `.embed` fixture copies — a fixture is the SUBJECT an eval measures, and a
//     stale copy measures a repo that no longer exists (gen-assets.ts:43-46 records
//     the shipped bug: an answer key citing files that were never materialized).
//
// The third, src/assets.ts, is left alone on purpose: a payload file that is missing
// from it does not fail silently — `embeddedTemplate` throws "template not embedded"
// (embed.ts:101) — and catching it here would mean reimplementing the generator.

import { expect, test } from "bun:test";
import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, readdirSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const root = join(import.meta.dir, "..");

test("rebuilding chain-entry.ts reproduces the committed chain bundle byte for byte", () => {
  const dir = mkdtempSync(join(tmpdir(), "ai-eng-bundle-"));
  const out = join(dir, "ai-eng-chain.ts");
  execFileSync(process.execPath, ["build", "scripts/chain-entry.ts", "--target=bun", "--format=esm", `--outfile=${out}`], { cwd: root, stdio: "pipe" });
  // gen-assets.ts:37 appends the default export that lets tsc type the asset import
  // as a string. A bare rebuild does not carry it, so the expectation adds it back.
  const rebuilt = `${readFileSync(out, "utf8")}\nexport default "ai-eng-chain";\n`;
  expect(readFileSync(join(root, "skills", ".chain-bundle", "ai-eng-chain.ts"), "utf8")).toBe(rebuilt);
  rmSync(dir, { recursive: true, force: true });
});

test("every .embed fixture copy is the byte-for-byte twin of the skill it came from", () => {
  const copyDir = join(root, "scripts", ".embed");
  const copies = readdirSync(copyDir, { recursive: true }).filter((entry) => String(entry).endsWith(".txt"));
  // Empty-test protection: a moved directory must fail loudly, not pass vacuously.
  expect(copies.length).toBeGreaterThan(0);
  for (const entry of copies) {
    const rel = String(entry);
    const source = join(root, "skills", rel.slice(0, -".txt".length));
    expect(existsSync(source)).toBe(true);
    expect(readFileSync(join(copyDir, rel), "utf8")).toBe(readFileSync(source, "utf8"));
  }
});
