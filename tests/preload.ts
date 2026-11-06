import { afterAll } from "bun:test";
import { readdirSync, watch } from "node:fs";
import { SANDBOX_VARS, snapshotSandboxEnv } from "./fixtures/sandbox-env.ts";

// On Linux, Bun before 1.4.4 can miss a spawnSync child's exit when a garbage collection
// runs during the wait (oven-sh/bun#47257, fixed by #44581): the call blocks until the
// test's 5 s timeout, prints "killed 1 dangling process", and dozens of unrelated tests
// fail at random. One clear refusal beats that storm.
const minBunOnLinux = "1.4.4";
if (process.platform === "linux" && Bun.semver.order(Bun.version, minBunOnLinux) < 0) {
  throw new Error(`bun ${Bun.version} loses spawnSync exits on Linux (oven-sh/bun#47257); run the suite on bun >= ${minBunOnLinux}`);
}

// The suite is written for a piped runner, and an interactive shell leaks its TTY-ness
// into every test: ui.ts replays stdin as keypresses only off a TTY, wraps rendered rows
// only on a TTY stdout, and its frame module keeps one `frameOpen` flag per process —
// so a prompt that hangs on real stdin leaves the frame open for the tests after it.
// `columns` too: on a TTY stream Bun reports 0 once isTTY is pinned, and clack's
// getColumns prefers a numeric `columns` over its 80 fallback — width 0 wraps every
// prompt to one character per line. Piping reports `columns` absent; pin that shape.
// The TTY branches exercise themselves by redefining isTTY inside their own tests
// (config-command, cli-ux).
Object.defineProperty(process.stdin, "isTTY", { value: false, configurable: true });
Object.defineProperty(process.stdout, "isTTY", { value: false, configurable: true });
Object.defineProperty(process.stdout, "columns", { value: undefined, configurable: true });

const initialEnv = snapshotSandboxEnv();
const initialCwd = process.cwd();
// Watch lifecycle tests directly so cleanup cannot hide a transient temp root.
const leakPrefixes = [".worktree-lifecycle-", ".dirfd-probe-"];
const isLeakedName = (name: string): boolean => leakPrefixes.some((prefix) => name.startsWith(prefix));
const watchTestTree = Bun.main.endsWith("worktree-lifecycle.spec.ts") || process.env["HYGIENE_LEAK_PROBE"] === "1";
const existingLeaks = watchTestTree ? readdirSync(import.meta.dir).filter(isLeakedName) : [];
const observedNames: string[] = [];
const testTreeWatcher = watchTestTree
  ? watch(import.meta.dir, (_event, name) => {
    if (typeof name !== "string" || isLeakedName(name)) observedNames.push(name ?? "<unknown>");
  })
  : null;
afterAll(() => {
  const changedEnv = SANDBOX_VARS.filter((name) => process.env[name] !== initialEnv[name]);
  const changedCwd = process.cwd() !== initialCwd;
  testTreeWatcher?.close();
  const leakedNames = [...new Set([
    ...existingLeaks,
    ...observedNames.filter((name) => name === "<unknown>" || isLeakedName(name)),
    ...readdirSync(import.meta.dir).filter(isLeakedName),
  ])];
  if (changedEnv.length > 0 || changedCwd || leakedNames.length > 0) {
    const changed = [
      ...changedEnv,
      ...(changedCwd ? ["cwd"] : []),
      ...(leakedNames.length > 0 ? ["temporary paths under tests/"] : []),
    ].join(", ");
    throw new Error(`test suite leaked sandbox state: ${changed}`);
  }
});
