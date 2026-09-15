/**
 * Artifact brand gate — one token set for every HTML artifact ai-engineering
 * generates. `spec.html` and `plan.html` carry the tokens inline (they must
 * render standalone, with no request of their own), and the canon's artifact
 * design system is the reference every other generator copies from. A token that
 * differs between them is a defect, not a preference: the artifacts are read side
 * by side, and two of them in two palettes read as two products.
 *
 * The values are NOT pinned here. The brand declares them once, in
 * brand/tokens.json, and this test calls the same gate the CLI runs
 * (`bun scripts/brand.ts artifact`). A test that re-states the palette is a
 * second palette — which is the thing being tested for.
 */
import { describe, test, expect } from "bun:test";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { artifactDrift, loadTokens } from "../scripts/brand.ts";

const ROOT = join(import.meta.dir, "..");

/** Every SKILL.md in the canon, so the gate covers a skill added tomorrow. */
function skillFiles(): string[] {
  const out: string[] = [];
  const walk = (dir: string): void => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const full = join(dir, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (entry.name === "SKILL.md") out.push(full);
    }
  };
  walk(join(ROOT, "skills"));
  return out;
}

describe("the artifact design system is the single token source", () => {
  test("every artifact token block matches brand/tokens.json", async () => {
    const { problems } = await artifactDrift(await loadTokens());
    // Each problem names the file, the token, the value found and the value the
    // brand declares — so a failure is a diff to apply, not a hunt to run.
    expect(problems.join("\n")).toBe("");
  });
});

describe("every skill that emits an artifact names the design system", () => {
  test("each one links artifact-design.md, so no generator invents a second style", () => {
    const silent: string[] = [];
    for (const file of skillFiles()) {
      const body = readFileSync(file, "utf8");
      const writes = /^Writes:\s*(.+)$/m.exec(body)?.[1];
      if (!writes?.includes(".html")) continue;
      if (!body.includes("artifact-design.md")) silent.push(file.slice(ROOT.length + 1));
    }
    expect(silent).toEqual([]);
  });
});
