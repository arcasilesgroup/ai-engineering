// src/cli.ts — flags first (@bomb.sh/args), prompts only for what's missing
// (@clack/prompts), TAB everywhere (@bomb.sh/tab). Six human verbs; the four
// machine verbs (chain|git|wrap|spec) are the product's programming surface (§07)
// and appear in neither TAB nor --help.

import { parse } from "@bomb.sh/args";
import tabRoot from "@bomb.sh/tab";
import { chainMain } from "./chain/mod.ts";
import { doctorMain } from "./commands/doctor.ts";
import { initMain } from "./commands/init.ts";
import { updateMain } from "./commands/update.ts";
import { upgradeMain } from "./commands/upgrade.ts";
import { uninstallMain } from "./commands/uninstall.ts";
import { configMain } from "./commands/config.ts";
import { wrapMain } from "./wrap/index.ts";
import { specMain } from "./spec/index.ts";
import { floor } from "./floor/entry.ts";

const HUMAN = ["init", "doctor", "config", "update", "upgrade", "uninstall"];
const VERSION = "0.13.0";

function detectShell(): string {
  if (process.env["ZSH_VERSION"]) return "zsh";
  if (process.env["BASH_VERSION"]) return "bash";
  if (process.env["FISH_VERSION"]) return "fish";
  return "bash";
}

for (const verb of HUMAN) tabRoot.command(verb, `ai-eng ${verb}`);
// Completion script only when the shell asks for it — never on every invocation.
if (process.argv[2] === "complete") tabRoot.setup("ai-eng", "ai-eng", detectShell());

const flags = parse(process.argv.slice(2), {
  boolean: ["yes", "global", "help", "version", "gc"],
  string: ["surface"],
});

const verb = flags._[0];

if (flags.version) {
  process.stdout.write(`ai-eng ${VERSION}\n`);
  process.exit(0);
}
if (flags.help || !verb) {
  process.stdout.write(`{ai} Engineering ${VERSION} — plant, guard, prove.\n\n`);
  process.stdout.write("  ai-eng init       planta gobernanza (global sin repo; contrato dentro)\n");
  process.stdout.write("  ai-eng doctor     12 checks + prueba adversarial real + --gc\n");
  process.stdout.write("  ai-eng config     superficies y umbrales\n");
  process.stdout.write("  ai-eng update     re-planta assets del binario (cero red)\n");
  process.stdout.write("  ai-eng upgrade    delega en bun/npm\n");
  process.stdout.write("  ai-eng uninstall  revierte lo suyo, conserva lo tuyo\n\n");
  process.stdout.write("Verbos de máquina (hooks/CI): chain · git · wrap · spec\n");
  process.exit(flags.help ? 0 : 2);
}

const surfaceList: string[] = typeof flags.surface === "string" ? [flags.surface] : [];

async function main(): Promise<number> {
  switch (verb) {
    case "chain": {
      const event = String(flags._[1] ?? "");
      if (!event) {
        process.stderr.write("uso: ai-eng chain <evento> < payload-json\n");
        return 2;
      }
      const raw = await Bun.stdin.text();
      chainMain(event, raw, { dialect: "exit2", surface: "claude-code" });
      return 0; // chainMain exits on its own when it denies
    }
    case "git":
      return floor(String(flags._[1] ?? ""), flags._[2] != null ? String(flags._[2]) : undefined);
    case "wrap":
      return wrapMain(flags._.slice(1).map(String));
    case "spec":
      return specMain(flags._.slice(1).map(String));
    case "init":
      return initMain({ yes: flags.yes === true, global: flags.global === true, surface: surfaceList });
    case "doctor":
      return doctorMain({ gc: flags.gc === true });
    case "config": {
      const configFlags: { add?: string; remove?: string } = {};
      if (typeof flags.add === "string") configFlags.add = flags.add;
      if (typeof flags.remove === "string") configFlags.remove = flags.remove;
      return configMain(configFlags);
    }
    case "update":
      return updateMain();
    case "upgrade":
      return upgradeMain();
    case "uninstall":
      return uninstallMain();
    default:
      process.stderr.write(`verbo desconocido: ${String(verb)}\n`);
      return 2;
  }

}

main()
  .then((code) => process.exit(code))
  .catch((error) => {
    process.stderr.write(`ai-eng: ${error instanceof Error ? error.message : String(error)}\n`);
    process.exit(2);
  });
