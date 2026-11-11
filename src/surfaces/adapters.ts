// src/surfaces/adapters.ts — the surfaces registry and carrier table: the declared surfaces
// (SURFACES, from surfaces.json), where each host reads its carrier, and the template each
// carrier is written from (with this machine's hook launcher taken into account). The work
// that hangs off the table lives in its own modules: canon-install.ts (canon + mirrors),
// machine-state.ts (the machine.json record and its custody) and carriers-install.ts
// (writing and removing the carriers).

import surfacesJson from "./surfaces.json";
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync, unlinkSync } from "node:fs";
import { delimiter, join } from "node:path";
import { machineBase } from "../env.ts";
import { KEEP_EXIT_STATUS, portableHookText, sha256 } from "../install.ts";
import {
  embeddedTemplate, embeddedChainBundle,
} from "../embed.ts";
import type { Dialect } from "../chain/dialect.ts";

export type Surface = {
  readonly id: string;
  readonly label: string;
  readonly tier: "core" | "experimental" | "best-effort" | "skills-only";
  /** The host's denial vocabulary in the chain (chain/dialect.ts). Absent for the
   *  hosts that run the chain in-process — their template turns the outcome into
   *  throw/block itself. */
  readonly dialect?: Dialect;
  readonly can: {
    /** `true` we deny · `"throw"` we deny by throwing (in-process hosts) · `"host-only"`
     *  the HOST can deny through its own permissions and we have no hook to run in — the
     *  two are different facts, and collapsing them made the picker print "can't block
     *  tool calls" about a host that can. */
    readonly deny: boolean | "throw" | "host-only";
    readonly rewriteOut: boolean | "total-replacement";
    /** The native goal loop (§20.3) — "unverified" means plausible but never
     *  measured with a receipt, "none" that the human loop is the honest mode
     *  there (Pi: extensions only; Zed: skills-only). Nothing is "native" until
     *  a receipt says so, and the field never guesses upward. */
    readonly loop: "native" | "unverified" | "none";
    /** The measurement behind `loop` — the installed version and the flag that
     *  grants it. A claim about a surface carries its evidence or it is a guess:
     *  the registry test refuses `native` and `none` without one (§20.3). */
    readonly loopEvidence?: string;
  };
  readonly carriers: readonly Carrier[];
  readonly note?: string;
};

/** Where a host READS its carrier, and the evidence for it. A path claimed from memory
 *  is the failure this table exists to end: ai-engineering wrote the OMP carrier into
 *  `.agents/hooks/`, which OMP never reads, and doctor called it green (§13.2). Every
 *  path here carries its source and the date it was read, so a stale claim is a delta
 *  against a recorded measurement instead of against somebody's memory. */
export type Carrier = {
  /** `machine` = the user's home, written once per machine; `repo` = inside the
   *  governed repo, for the readers that only exist there. */
  readonly scope: "repo" | "machine";
  /** `settings` files may already belong to the user and are MERGED into by marker;
   *  `module` files are ours whole. */
  readonly kind: "settings" | "module";
  /** Home-relative when scope is machine, repo-relative when repo. Never absolute:
   *  a machine path in a versioned file is a leak. */
  readonly path: string;
  /** The chain bundle that must sit beside an in-process carrier. */
  readonly chain?: string;
  /** The environment variable this host resolves its agent directory from (omp and pi:
   *  PI_CODING_AGENT_DIR). A relocatable agent dir is not a detail — the carrier has to
   *  land where the host will look, or it is the `.agents/hooks/` bug again. */
  readonly agentDirEnv?: string;
  readonly source: string;
  readonly measured: string;
};

export const SURFACES: Surface[] = (surfacesJson as { surfaces: Surface[] }).surfaces;

/** The carrier this surface keeps in the repo (Cursor and Copilot, whose cloud readers
 *  only see the checkout). Null for everything else. */
export function repoCarrier(surface: Surface): Carrier | null {
  return surface.carriers.find((carrier) => carrier.scope === "repo") ?? null;
}

/** The carrier this surface keeps on the machine. Null for a host that only reads repo
 *  files. */
export function machineCarrier(surface: Surface): Carrier | null {
  return surface.carriers.find((carrier) => carrier.scope === "machine") ?? null;
}

/** Where a carrier's path is rooted: the machine base, unless this host resolves its
 *  agent directory from an environment variable that IS set — then that, because that is
 *  where the host will look. Installing a carrier the host never reads is the bug this
 *  whole table exists to end, and a relocatable agent dir is the same bug wearing a hat. */
export function carrierBase(placement: Carrier): string {
  if (placement.scope === "machine" && placement.agentDirEnv !== undefined) {
    const override = process.env[placement.agentDirEnv];
    if (override !== undefined && override.length > 0) return override;
  }
  return machineBase();
}

/** The absolute path of a carrier file (the entry, or its chain bundle). One function for
 *  the installer, the remover and doctor: two resolutions of the same path is how a
 *  carrier gets written somewhere and checked somewhere else. */
export function carrierPath(placement: Carrier, relative?: string): string {
  const rel = relative ?? placement.path;
  const base = carrierBase(placement);
  if (base === machineBase()) return join(base, rel);
  // The host's agent dir already IS the `.omp/agent` (or `.pi/agent`) the path names.
  return join(base, rel.replace(/^\.(omp|pi)\/agent\//, ""));
}

/** surface id → the entry template and whether the host needs the chain bundle
 *  beside it. Copilot fails CLOSED on a missing binary, in both scopes, so its one
 *  template guards the call per shell (`bash` and `powershell`). Null for a surface
 *  with no generator (§13: no adapter, no offer). */
const CARRIER_TEMPLATES: Record<string, { main: string; chain: boolean; isExitStatusRead?: boolean }> = {
  // Claude denies by exit status (2); every other JSON host reads the verdict from stdout.
  "claude-code": { main: "settings.claude.json.tpl", chain: false, isExitStatusRead: true },
  "oh-my-pi": { main: "plugin.omp.ts.tpl", chain: true },
  opencode: { main: "plugin.opencode.ts.tpl", chain: true },
  pi: { main: "plugin.pi.ts.tpl", chain: true },
  codex: { main: "settings.codex.json.tpl", chain: false },
  cursor: { main: "settings.cursor.json.tpl", chain: false },
  copilot: { main: "settings.copilot.json.tpl", chain: false },
};

/** The launcher name a hook line must call on this machine. On Windows a bare `ai-eng`
 *  resolves, in PowerShell, to npm's `ai-eng.ps1` — and the Restricted execution policy a
 *  fresh Windows laptop ships with refuses to load it, so every hook errors and the
 *  fail-closed hosts deny every tool call. The `.exe` (bun) or `.cmd` (npm) shim beside it
 *  runs under any policy, in PowerShell, cmd and Git Bash alike. First hit in PATH order,
 *  the way the shell will resolve it; `.cmd` when nothing is on PATH yet (npm's shim). */
/** Whether a file of exactly this name sits in a PATH directory. */
export function isOnPath(name: string, path: string = process.env["PATH"] ?? process.env["Path"] ?? ""): boolean {
  return path.split(delimiter).filter(Boolean).some((dir) => existsSync(join(dir, name)));
}

export function hookLauncher(platform: NodeJS.Platform = process.platform, path: string = process.env["PATH"] ?? process.env["Path"] ?? ""): string {
  if (platform !== "win32") return "ai-eng";
  for (const dir of path.split(";").filter(Boolean)) {
    for (const name of ["ai-eng.exe", "ai-eng.cmd"]) if (existsSync(join(dir, name))) return name;
  }
  return "ai-eng.cmd";
}

/** npm writes three shims for `ai-eng` on Windows, and PowerShell resolves the bare name to
 *  `ai-eng.ps1` first. The Restricted policy a fresh laptop ships with refuses to load it, and
 *  under `-Command` it hands the program no stdin, so a hook gets an empty payload. Every
 *  PowerShell host hits it (Cursor's repo line has no per-OS key), and so does a person
 *  typing `ai-eng init` in PowerShell. The `ai-eng.cmd` beside it does the same job under
 *  any policy. Only a .ps1 that launches this package goes, and only beside its .cmd; npm
 *  writes it again on the next install, and the next init or update takes it out again. */
export function retireNpmPowerShellShim(platform: NodeJS.Platform = process.platform, path: string = process.env["PATH"] ?? process.env["Path"] ?? ""): string | null {
  if (platform !== "win32") return null;
  for (const dir of path.split(";").filter(Boolean)) {
    const shim = join(dir, "ai-eng.ps1");
    if (!existsSync(shim)) continue;
    // Only the first .ps1 on PATH is the one PowerShell runs; removing a later one fixes nothing.
    if (!existsSync(join(dir, "ai-eng.cmd"))) return null;
    try {
      if (!/ai-engineering[\\/]+bin[\\/]+ai-eng\.js/.test(readFileSync(shim, "utf8"))) return null;
      unlinkSync(shim);
      return `✓ removed npm's ${shim}: PowerShell now runs ai-eng.cmd, under any execution policy`;
    } catch {
      return `⚠ ${shim} could not be removed: PowerShell hosts will run it, and the Restricted policy refuses it — delete it, or install with bun`;
    }
  }
  return null;
}

/** `powershell -Command` turns a native exit 2 into exit 1, and Claude reads exit 1 as a
 *  non-blocking error: the denial becomes an allow (first-install probe, windows-latest).
 *  Passing the status on by hand keeps it 2. Git Bash reads the same text the same way:
 *  `$LASTEXITCODE` is unset there, so `exit` returns the chain's own status. */

/** A settings template with its hook lines calling `launcher`. Only the call is renamed:
 *  the `command -v ai-eng` / `Get-Command ai-eng` probes look for any form of it. */
export function withLauncher(template: string, launcher: string = hookLauncher(), isExitStatusRead = false): string {
  if (launcher === "ai-eng") return template;
  const renamed = template.replaceAll("ai-eng chain ", `${launcher} chain `);
  return isExitStatusRead ? renamed.replace(/("command": "[^"]+ chain [A-Za-z]+)"/g, `$1${KEEP_EXIT_STATUS}"`) : renamed;
}

/** The definition machine.json records for a carrier: its hash with this machine's launcher
 *  taken out, so a PATH that puts the bun or the npm shim first changes nothing. */
export function carrierDefinition(main: string): string {
  return sha256(portableHookText(main));
}

/** OpenCode 1.x keeps the 1.x template; 2.x gets the one this binary ships as `main`. */
const OPENCODE_V1_TEMPLATE = "plugin.opencode.v1.ts.tpl";

/** Which OpenCode plugin API the host on PATH speaks. 2.x takes a default `{ id, setup }`
 *  definition; 1.x calls each exported function and keeps the hooks it returns. The two
 *  are mutually exclusive — the wrong file stops the host at startup, which is exactly what
 *  3.0.x shipped — so the carrier follows the binary. `AI_ENG_OPENCODE_MAJOR` pins the
 *  answer for tests and for a host this PATH does not reach. */
let probedOpencodeMajor: number | null | undefined;

function opencodeMajor(): number | null {
  const pinned = process.env["AI_ENG_OPENCODE_MAJOR"];
  if (pinned !== undefined) return /^\d+$/.test(pinned) ? Number(pinned) : null;
  if (probedOpencodeMajor === undefined) {
    // On Windows an npm install is an `opencode.cmd` shim, which spawnSync cannot execute
    // without a shell; the probe failing there would hand a 1.x host the 2.x file.
    const probe = spawnSync("opencode", ["--version"], { encoding: "utf8", timeout: 5000, shell: process.platform === "win32" });
    const match = /^v?(\d+)/.exec((probe.stdout ?? "").trim());
    probedOpencodeMajor = match === null ? null : Number(match[1]);
  }
  return probedOpencodeMajor;
}

/** The template this host will load. Unknown counts as the current major: a host that is
 *  not installed reads nothing, and the next update corrects the file once it is. */
export function carrierFiles(id: string, scope: Carrier["scope"] = "machine"): { main: string; chain: string | null } | null {
  // The surface id is copilot-cli; the template row kept the short name.
  const row = CARRIER_TEMPLATES[id] ?? (id === "copilot-cli" ? CARRIER_TEMPLATES["copilot"] : undefined);
  if (!row) return null;
  const template = embeddedTemplate(id === "opencode" && (opencodeMajor() ?? 2) < 2 ? OPENCODE_V1_TEMPLATE : row.main);
  // Only this machine's own files name this machine's launcher. A repo file is committed
  // and read on every teammate's OS: `ai-eng.cmd` there is "command not found" on a Mac.
  // Module carriers run the chain in-process: there is no hook line to rename.
  const main = scope === "machine" && row.main.endsWith(".json.tpl") ? withLauncher(template, hookLauncher(), row.isExitStatusRead === true) : template;
  return { main, chain: row.chain ? embeddedChainBundle() : null };
}

/** What the chain must write when this surface denies. Default: claude. */
export function surfaceDialect(id: string | undefined): Dialect {
  return SURFACES.find((s) => s.id === id)?.dialect ?? "claude";
}

/** init aborts if the chosen surface cannot carry a required guard: better not to
 *  promise than to promise falsely (§13). */
export function surfaceCanGovern(surface: Surface): boolean {
  // Only the hosts that RUN us can be governed: a host that denies on its own, without
  // calling our chain, has nowhere for a guard to stand.
  return surface.can.deny === true || surface.can.deny === "throw";
}
