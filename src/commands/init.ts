import { existsSync, readFileSync, writeFileSync, symlinkSync, chmodSync } from "node:fs";
import { spawnSync, execFileSync } from "node:child_process";
// `ai-eng init` — one verb, two phases (§14.0a). Outside a repo: phase 1, the
// machine (canon + mirrors). Inside a repo: both phases — first the canon (missing
// is installed, never aborts), then the project contract. Idempotent: re-init
// offers update, never overwrites an edited file (§14.5b's six paths).

import { join } from "node:path";
import { intro, multiselect, select, spinner, note, isCancel, confirm } from "@clack/prompts";
import { SURFACES, surfaceCanGovern, installCanon } from "../surfaces/adapters.ts";
import { plant, buildLock, lockText } from "../plant.ts";
import { home } from "../env.ts";
import { updateMain } from "./update.ts";
import { VERSION, planEntries, contractEntries } from "./init-shared.ts";

function isGitRepo(cwd: string): boolean {
  return existsSync(join(cwd, ".git"));
}

function scaffoldProject(surfaces: string[]): string[] {
  const cwd = process.cwd();
  const lines: string[] = [];
  // Contract files: written ONCE. plant() skips anything the user already has.
  const contractReport = plant(cwd, contractEntries(new Date().toISOString().slice(0, 10)));
  for (const written of contractReport.written) lines.push(`✓ ${written} (contrato)`);
  for (const untouched of contractReport.untouched) lines.push(`· ${untouched} — tuyo, no se toca`);
  // CLAUDE.md: symlink to AGENTS.md where the OS allows, one-line import where not.
  const claudePath = join(cwd, "CLAUDE.md");
  if (!existsSync(claudePath)) {
    try {
      symlinkSync("AGENTS.md", claudePath);
      lines.push("✓ CLAUDE.md → symlink a AGENTS.md");
    } catch {
      writeFileSync(claudePath, "@AGENTS.md\n");
      lines.push("✓ CLAUDE.md → una línea @AGENTS.md (symlink rechazado por el FS)");
    }
  }
  const report = plant(cwd, planEntries(surfaces));
  for (const written of report.written) lines.push(`✓ ${written}`);
  for (const conflict of report.conflicts) lines.push(`⚠ ${conflict} — editado por ti: diff 3-vías requerido, no se toca`);
  // Hook shims must be executable or git silently ignores them (measured).
  for (const shim of ["pre-commit", "commit-msg", "pre-push"]) {
    const shimPath = join(cwd, ".git", "hooks", shim);
    if (existsSync(shimPath)) chmodSync(shimPath, 0o755);
  }
  lines.push("✓ git floor → .git/hooks/{pre-commit,commit-msg,pre-push} (marker-managed)");
  // core.hooksPath is NOT redirected: the hooks live in their standard location.
  try {
    const wired = spawnSync("git", ["-C", cwd, "config", "core.hooksPath"], { encoding: "utf8" });
    if ((wired.stdout ?? "").trim() !== "") {
      execFileSync("git", ["-C", cwd, "config", "--unset", "core.hooksPath"], { cwd });
      lines.push("✓ core.hooksPath custom redirect removed (hooks now standard .git/hooks/)");
    }
  } catch {
    /* no custom hooksPath: nothing to clean */
  }
  writeFileSync(join(cwd, ".ai-engineering", "ai-eng.lock"), lockText(lock));
  lines.push(`✓ .ai-engineering/ai-eng.lock (${Object.keys(lock.assets).length} assets con sha256)`);
  return lines;
}

export async function initMain(flags: { yes?: boolean; global?: boolean; surface?: string[] }): Promise<number> {
  intro(`{ai} Engineering ${VERSION}`);
  const cwd = process.cwd();
  const inRepo = isGitRepo(cwd) || existsSync(join(cwd, ".ai-engineering"));
  // Phase 1: global, or missing canon — installs/repairs the machine side either way.
  // home() (not HOME) so AI_ENG_HOME test installs stay isolated.
  const canonDir = join(home(), "skills");
  if (flags.global || !existsSync(canonDir)) {
    installCanon(VERSION).forEach((line) => process.stdout.write(`${line}\n`));
  }
  // Outside a repo: carpeta pelada is not a refusal — §14.1 runs init in a bare
  // folder and init creates the repo itself (confirm, or --yes to proceed).
  if (!inRepo) {
    const ok = flags.yes === true || (await confirm({ message: "No git repo here. Create one? (git init -q)" }));
    if (isCancel(ok) || ok === false) {
      note("Dentro de un repo, ai-eng init lo gobierna además.", "next");
      return 0;
    }
    try {
      execFileSync("git", ["init", "-q"], { cwd });
      process.stdout.write("✓ git init -q\n");
    } catch {
      process.stderr.write("git init falló — abortando: sin repo no hay floor.\n");
      return 2;
    }
  }
  // ── Phase 2: the repo is governed — idempotent re-init never pisa tu trabajo (§14.5b).
  if (existsSync(join(cwd, ".ai-engineering", "config.toml"))) {
    const action = await select({
      message: "Esto ya está gobernado.",
      options: [
        { value: "exit", label: "Salir" },
        { value: "update", label: "Re-plantar assets (update)" },
      ],
    });
    if (isCancel(action) || action === "exit") return 0;
    return updateMain();
  }
  let picked: string[];
  if (flags.yes === true) {
    picked = flags.surface && flags.surface.length > 0 ? flags.surface : ["claude-code"];
  } else {
    const answer = await multiselect({
      message: "¿Qué superficies de agente usas?",
      options: SURFACES.map((s) => ({
        value: s.id,
        label: s.label,
        hint: s.tier === "core" ? "✔ core" : s.tier === "experimental" ? "⚠ experimental" : s.tier === "skills-only" ? "skills only" : "best-effort",
      })),
      required: true,
    });
    if (isCancel(answer)) return 0;
    picked = answer;
  }
  // Abort before promising what a surface cannot deliver (§13).
  for (const id of picked) {
    const surface = SURFACES.find((s) => s.id === id);
    if (surface && !surfaceCanGovern(surface)) {
      process.stderr.write(`"${id}" no puede negar herramientas: los guards no tienen dónde correr. Usa una superficie core.\n`);
      return 2;
    }
  }
  const sp = spinner();
  sp.start("Scaffolding governance…");
  const lines = scaffoldProject(picked);
  sp.stop("Scaffolded.");
  for (const line of lines) process.stdout.write(`${line}\n`);
  // The first commit of the contract: the lockfile and the Receipt-Id trailer get
  // their baseline from second zero (§08).
  try {
    execFileSync("git", ["add", "-A"], { cwd });
    execFileSync("git", ["commit", "-q", "-m", "chore(ai-eng): plant governance 0.13.0", "--no-verify", "--no-gpg-sign"], { cwd });
    process.stdout.write("✓ primer commit del contrato\n");
  } catch {
    process.stdout.write("· commit del contrato pendiente (hazlo tú con git)\n");
  }
  process.stdout.write("\nTwo steps I can't do for you:\n");
  process.stdout.write("  1. Confía el workspace en tu superficie (sin trust, los hooks no corren)\n");
  process.stdout.write("  2. ai-eng doctor — verifica que la cadena responde\n");
  return 0;
}

/** Canon version read for doctor/notice paths. */
export function canonVersion(): string {
  try {
    const path = join(process.env.HOME ?? "", ".ai-engineering", "version.json");
    return String(JSON.parse(readFileSync(path, "utf8")).version ?? "unknown");
  } catch {
    return "unknown";
  }
}
