// A `gitleaks` stand-in the floor finds on PATH on every platform. The floor probes and
// runs a bare `gitleaks`, which Windows resolves only to an executable, never to a
// `#!/bin/sh` script; so the stand-in is tests/fixtures/gitleaks-shim-main.ts compiled
// once per file, and each test writes the answer it should give beside it.
import { spawnSync } from "node:child_process";
import { mkdtempSync, realpathSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { delimiter, dirname, join } from "node:path";

export type GitleaksBehaviour =
  /** `version` passes; a scan exits 1 with a finding when the scanned tree holds an AWS key id. */
  | { mode: "grep" }
  /** Only the floor's exact argv gets `scanOut`/`scanExit`; anything else exits 42 with BADECHO. */
  | { mode: "strict"; scanExit: number; scanOut?: string; versionExit?: number }
  /** Records GITLEAKS_CONFIG (or "unset") to `record`, copies the config to `record.copy`, passes. */
  | { mode: "record-env"; record: string }
  /** Like the real binary with exemptions: honours the handed GITLEAKS_CONFIG allowlist
   *  paths and a .gitleaksignore in the scan root; finds the AWS key otherwise. */
  | { mode: "leaky" };

/** Compiles the stand-in into a fresh directory and returns that directory. */
export function compileGitleaksShim(): string {
  const dir = mkdtempSync(join(tmpdir(), "ai-eng-gitleaks-shim-"));
  const binary = join(dir, process.platform === "win32" ? "gitleaks.exe" : "gitleaks");
  const built = spawnSync(process.execPath, ["build", "--compile", join(import.meta.dir, "gitleaks-shim-main.ts"), "--outfile", binary], { encoding: "utf8" });
  if (built.status !== 0) {
    rmSync(dir, { recursive: true, force: true });
    throw new Error(`cannot compile the gitleaks stand-in: ${built.stderr || String(built.error)}`);
  }
  return dir;
}

/** Sets what the stand-in answers and puts it first on PATH. */
export function useGitleaksShim(dir: string, behaviour: GitleaksBehaviour, pathBefore: string): void {
  writeFileSync(join(dir, "gitleaks-shim.json"), JSON.stringify(behaviour));
  process.env.PATH = `${dir}${delimiter}${pathBefore}`;
}

/** A PATH holding git's own directory and nothing else: how "gitleaks is not installed"
 *  is proved without depending on what this machine has elsewhere on PATH. */
export function pathWithOnlyGit(): string {
  const git = Bun.which("git");
  if (git === null) throw new Error("git is not on PATH");
  const onlyGit = dirname(realpathSync(git));
  if (Bun.which("gitleaks", { PATH: onlyGit }) !== null) throw new Error(`${onlyGit} also holds gitleaks`);
  return onlyGit;
}

/** The install hint the floor prints on the OS running the test, so an assertion
 *  on it holds on every CI leg, not only the one that runs brew. */
export function gitleaksInstallHint(): string {
  return process.platform === "win32"
    ? "choco install gitleaks (or scoop install gitleaks)"
    : process.platform === "darwin"
      ? "brew install gitleaks"
      : "apt install gitleaks (or download the binary from the gitleaks releases page)";
}
