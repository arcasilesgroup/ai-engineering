// The one build entry point. `bun build --compile` writes the executable to a
// scratch file (".<hash>-<n>.bun-build", ~59 MB) and renames it into --outfile
// only when the compile finishes, so an interrupted build leaves the scratch
// behind in the cwd and Bun never sweeps one from an earlier run (measured
// 2026-09-05: two orphans, 118 MB, invisible because .gitignore hides them).
// Sweep before and after: the scratch either gets renamed away or it does not
// outlive this script.
import { readdirSync, rmSync } from "node:fs";
import { spawnSync } from "node:child_process";

const args = process.argv.slice(2);

function sweep(): number {
  let removed = 0;
  for (const dir of [".", "dist"]) {
    let entries: string[];
    try {
      entries = readdirSync(dir);
    } catch {
      continue; // dist/ does not exist before the first build
    }
    for (const entry of entries) {
      if (!entry.endsWith(".bun-build")) continue;
      rmSync(`${dir}/${entry}`, { force: true });
      removed += 1;
    }
  }
  return removed;
}

const orphans = sweep();
if (orphans > 0) console.log(`build: swept ${orphans} orphaned .bun-build scratch file(s)`);

const done = spawnSync(
  process.execPath,
  ["build", "src/cli.ts", "--compile", "--minify", "--sourcemap", "--bytecode", "--outfile", "dist/ai-eng", ...args],
  { stdio: "inherit" },
);

const left = sweep();
if (left > 0) console.log(`build: swept ${left} scratch file(s) this build left behind`);
process.exit(done.status ?? 1);
