// The first half of `ai-eng update`: the binary itself. One registry read (3 s), the
// install delegated to the package manager that installed ai-eng, then the new binary
// is run so the sync that follows writes the new payload — the old binary only carries
// its own files. Nothing here downloads or verifies a binary: the package manager does,
// and trust stays with it. The sync that follows is still offline.

import { spawnSync } from "node:child_process";
import { fetchLatest, noticesOff, writeCache } from "../notice.ts";
import { VERSION, compareVersions } from "../version.ts";
import { scriptedInput } from "../ui.ts";
import * as ui from "../ui.ts";

/** Set on the relaunched run, so it syncs instead of asking the registry again. */
export const RELAUNCHED_ENV = "AI_ENG_UPDATE_RELAUNCHED";
const RELEASE_NOTES = "https://github.com/arcasilesgroup/ai-engineering/releases/tag/v";

export type Manager = "bun" | "npm";

/** The manager that installed this binary, read from where it lives: a global bun
 *  install runs from ~/.bun; anything else came from npm. */
export function managerFor(execPath: string): Manager {
  return /[\\/]\.bun[\\/]/.test(execPath) ? "bun" : "npm";
}

export function installCommand(manager: Manager, version: string): string[] {
  return manager === "bun" ? ["bun", "add", "-g", `ai-engineering@${version}`] : ["npm", "install", "-g", `ai-engineering@${version}`];
}

type Run = (command: string, args: string[], options: { inherit: boolean; env?: NodeJS.ProcessEnv }) => { status: number | null; stdout: string };

/** Everything that touches the world, so a test can answer each part. */
export type BinaryDeps = {
  fetchLatest: () => Promise<string | null>;
  run: Run;
  which: (name: string) => string | null;
  isInteractive: () => boolean;
  confirm: (message: string) => Promise<boolean>;
  execPath: string;
};

function defaultDeps(): BinaryDeps {
  return {
    fetchLatest,
    // npm, and an npm-installed ai-eng, are .cmd shims on Windows: those need a shell.
    run: (command, args, options) => {
      const done = spawnSync(command, args, {
        encoding: "utf8",
        stdio: options.inherit ? "inherit" : "pipe",
        env: options.env ?? process.env,
        shell: process.platform === "win32" && (command === "npm" || command.toLowerCase().endsWith(".cmd")),
      });
      return { status: done.status, stdout: done.stdout ?? "" };
    },
    which: (name) => Bun.which(name),
    isInteractive: () => process.stdin.isTTY === true && process.stdout.isTTY === true,
    confirm: (message) => ui.confirmDefault(message, false, scriptedInput() as never),
    execPath: process.execPath,
  };
}

/** Null: carry on and sync with this binary. A number: the exit code of the relaunched
 *  run, or of a refusal to sync with a binary that is not the one just installed. */
export async function updateBinary(opts: { yes: boolean }, deps: BinaryDeps = defaultDeps()): Promise<number | null> {
  if (process.env[RELAUNCHED_ENV] === "1" || noticesOff()) return null;
  const spin = ui.spinner();
  spin.start("Checking the registry");
  const latest = await deps.fetchLatest();
  spin.stop();
  writeCache(latest);
  // Offline, a failed read, or nothing newer: the sync runs exactly as before, quietly.
  if (latest === null || compareVersions(latest, VERSION) <= 0) return null;

  const manager = managerFor(deps.execPath);
  const command = installCommand(manager, latest);
  ui.section(`ai-eng ${latest} is available`, [
    { mark: "muted", text: `you have ${VERSION}` },
    { mark: "sub", text: `changes: ${RELEASE_NOTES}${latest}` },
    { mark: "sub", text: `install: ${command.join(" ")}` },
  ]);
  if (!opts.yes) {
    // Nobody to ask (an agent, a script): installing for every repo on the machine is
    // the person's call, so the command is shown and the sync goes on with this binary.
    if (!deps.isInteractive()) {
      ui.info(`not installed — no terminal to confirm in. Run it yourself: ${command.join(" ")}`);
      return null;
    }
    if (!(await deps.confirm(`Install ai-eng ${latest} with ${manager}? It changes ai-eng for every repo on this machine.`))) return null;
  }

  const installed = deps.run(command[0]!, command.slice(1), { inherit: true });
  if (installed.status !== 0) {
    ui.warn(`${command.join(" ")} failed — ai-eng ${VERSION} stays and syncs as before`);
    return null;
  }
  // The sync must run on the new binary. Two installs (bun and npm) can leave the old
  // one first on PATH: syncing with it would write the old payload and call it done.
  const onPath = deps.which("ai-eng");
  const reported = onPath === null ? null : (/\d+\.\d+\.\d+\S*/.exec(deps.run(onPath, ["--version"], { inherit: false }).stdout)?.[0] ?? null);
  if (onPath === null || reported !== latest) {
    const found = onPath === null ? "there is no ai-eng on PATH" : `the ai-eng on PATH (${onPath}) reports ${reported ?? "no version"}`;
    ui.fail(`installed ai-eng ${latest}, but ${found} — another install shadows it. Remove that one, then run ai-eng update again. Nothing was synced.`);
    return 1;
  }
  const relaunched = deps.run(onPath, ["update", ...(opts.yes ? ["--yes"] : [])], { inherit: true, env: { ...process.env, [RELAUNCHED_ENV]: "1" } });
  return relaunched.status ?? 1;
}
