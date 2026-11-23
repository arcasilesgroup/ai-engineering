// stryker.conf.mjs — the mutation tier's single config (§17.1). Every odd-looking
// setting below has a measured reason; none of them is a default we forgot to think
// about. The spike that produced them is written up in
// .ai-engineering/research/005-mutation-tier-facts.html and .ai-engineering/brainstorm.md.
//
// `bun run mutation` locally, `bunx stryker run` in CI (the CLI declares a node
// shebang and bunx honours it; the test children still run under Bun).
import { rmSync } from "node:fs";

const TEMP_DIR = ".stryker-tmp";
// A killed run (Ctrl-C, a CI timeout) cleans nothing, not even with cleanTempDir
// "always": its sandboxes are swept when the next run loads this config, the way
// scripts/build.ts sweeps an interrupted compile's scratch.
rmSync(TEMP_DIR, { recursive: true, force: true });

export default {
  // The plugin is NOT in the @stryker-mutator/* scope, so Stryker's default plugin
  // glob never finds it. The plugin's own README omits this line.
  plugins: ["@hughescr/stryker-bun-runner"],
  testRunner: "bun",
  coverageAnalysis: "perTest",
  // The governance core, and nothing else: these are the modules whose tests decide
  // whether a guard still denies. commands/, surfaces/, spec/ and wrap/ are out of
  // scope for this milestone.
  mutate: ["src/guards/**/*.ts", "src/chain/**/*.ts", "src/floor/**/*.ts"],
  // Two, not four: the gate runs on a slower runner than the laptop that measured it,
  // and the plugin's inspector stream truncates under load (one spurious dry-run
  // failure in seven). todo: one config for both jobs; the lever if CI flakes is
  // this number, then @hughescr/stryker-bun-runner 1.4.0 once it clears the 7-day floor.
  concurrency: 2,
  // 223 of 1,927 mutants are static and take 81% of the time. They decide nothing a
  // test can observe, so they are out.
  ignoreStatic: true,
  inPlace: false,
  // The default is `true`, and it expands to **/*.{js,ts,jsx,tsx,html,vue,mjs,mts,cts,cjs}
  // over the whole project: inside the sandbox it rewrote skills/**/*.ts and broke the
  // .embed test. `bun test` never typechecks, so nothing here needs it.
  disableTypeChecks: false,
  // TSConfigPreprocessor calls a TypeScript API that TS 7 removed. Its only consumer
  // guards on the path existing, so a path that is not a project file is skipped.
  tsconfigFile: ".stryker/absent.json",
  // This test rebuilds the bundle with `bun build` and compares bytes: inside the
  // sandbox src/ is instrumented, so it can never match. It imports nothing mutated,
  // so it can kill no mutant either. Excluded by pattern, auto-discovery intact.
  // `.codegraph/daemon.sock` is a machine-local UNIX socket: copyfile() cannot clone
  // it into the sandbox, and CI never has the directory.
  // dist/ and an interrupted build's *.bun-build scratch are ~250 MB a sandbox, read by no
  // test (the suite runs before the build, on purpose).
  ignorePatterns: ["tests/generated-payload.test.ts", ".codegraph/**", "dist/**", "*.bun-build"],
  // The cache is what makes the pull-request job cheap: ~35s warm against ~8min cold.
  // A cached kill survives only while its killing test is unchanged (research 005 §01).
  incremental: true,
  incrementalFile: "reports/stryker-incremental.json",
  reporters: ["clear-text", "json"],
  jsonReporter: { fileName: "reports/mutation.json" },
  // A ratchet at the last measured incremental score, not an aspiration. Clean was
  // 59.21%, incremental 58.51% — the number CI sees, because the pull-request job
  // restores that cache. break sits under it, so a campaign that still denies what
  // it denied can pass, and the number only moves up. high stays the mark to aim at.
  // Dropping the pull-request trigger would leave a nightly that is red at 85 and a
  // pull request with no mutation signal at all. Below break, the clear-text report
  // names the survivors.
  thresholds: { high: 90, low: 58, break: 58 },
  tempDirName: TEMP_DIR,
  // The default (`true`) deletes the sandboxes only after a successful run: every failed
  // or timed-out run left a full copy of the project behind (3 GB after a few).
  cleanTempDir: "always",
  // The plugin's `timeout` is the whole `bun test` subprocess, not one test, and it adds a
  // fixed 30 s drain ceiling: 30 000 here meant 60 s for the full dry run, which measured
  // 57 s at 2,332 tests on a hosted runner and passed 60 s once the suite grew past 2,400
  // (3 min on a loaded laptop). Five minutes leaves room to grow; a mutant's run selects
  // only its covering tests, far below it.
  bun: { timeout: 300000 },
  // The serial suite is ~2,100 tests; its instrumented dry run passes 5 minutes (the
  // default) on a hosted runner. The score threshold above is unchanged.
  dryRunTimeoutMinutes: 15,
};
