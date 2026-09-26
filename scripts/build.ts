// The one build entry point. `bun build --compile` writes the executable to a
// scratch file (".<hash>-<n>.bun-build", ~59 MB) and renames it into --outfile
// only when the compile finishes, so an interrupted build leaves the scratch
// behind in the cwd and Bun never sweeps one from an earlier run (invisible
// because .gitignore hides it). Sweep before and after: the scratch either gets
// renamed away or it does not outlive this script.
import { readdirSync, existsSync, rmSync, unlinkSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";

const args = process.argv.slice(2);

/** A cross-compile leg names its own artifact. All eight matrix legs wrote
 *  `dist/ai-eng`, and release assets must have unique names on the page the
 *  client's CI downloads from — eight files called `ai-eng` collide there.
 *  `--target bun-linux-x64` → `dist/ai-eng-linux-x64`; no target → `dist/ai-eng`. */
function outfile(flags: string[]): string {
  const at = flags.findIndex((flag) => flag === "--target" || flag.startsWith("--target="));
  if (at === -1) return "dist/ai-eng";
  const target = flags[at] === "--target" ? flags[at + 1] : flags[at]!.slice("--target=".length);
  if (!target) return "dist/ai-eng";
  return `dist/ai-eng-${target.replace(/^bun-/, "")}`;
}

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
  ["build", "src/cli.ts", "--compile", "--minify", "--sourcemap", "--bytecode", "--outfile", outfile(args), ...args],
  { stdio: "inherit" },
);

const left = sweep();

// A plain build (`bun run build`) emits dist/ai-eng. A leftover
// dist/ai-eng-<this host> is from an older --target run and would win over the
// file this build just wrote, so a dev checkout would keep running stale code.
// Removing it leaves dist/ai-eng, which bin/ai-eng.js runs. A --target build
// never deletes: that file is the platform refresh.
if (!args.includes("--target") && !args.some((flag) => flag.startsWith("--target="))) {
  const target = process.platform === "darwin" ? `darwin-${process.arch}`
    : process.platform === "win32" ? "windows-x64" : `${process.platform}-${process.arch}`;
  const platformBin = join("dist", `ai-eng-${target}`);
  if (existsSync(platformBin)) {
    unlinkSync(platformBin);
    console.log(`build: removed stale ${platformBin} — bin/ai-eng.js was preferring it over dist/ai-eng`);
  }
}

process.exit(done.status ?? 1);


