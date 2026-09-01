#!/usr/bin/env bun
// src/cli.ts — flags first (@bomb.sh/args), prompts only for what's missing
// (@clack/prompts), TAB everywhere (@bomb.sh/tab). Six human verbs; the four
// machine verbs (chain|git|wrap|spec) are the product's programming surface (§07)
// and appear in neither TAB nor --help.

import { parse } from "@bomb.sh/args";
import tabRoot from "@bomb.sh/tab";
import { VERSION } from "./version.ts";
import { showLogo } from "./branding.ts";
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
  showLogo(VERSION);
  process.stdout.write("\n");
  process.stdout.write("  ai-eng init       plant governance (global without a repo; contract inside)\n");
  process.stdout.write("  ai-eng doctor     12 checks + one real adversarial probe + --gc\n");
  process.stdout.write("  ai-eng config     surfaces and thresholds\n");
  process.stdout.write("  ai-eng update     re-plant binary assets (zero network)\n");
  process.stdout.write("  ai-eng upgrade    delegate to bun/npm\n");
  process.stdout.write("  ai-eng uninstall  revert ours, keep yours\n\n");
  process.stdout.write("Machine verbs (hooks/CI): chain · git · wrap · spec\n");
  process.exit(flags.help ? 0 : 2);
}

const surfaceList: string[] = typeof flags.surface === "string" ? [flags.surface] : [];

async function main(): Promise<number> {
  switch (verb) {
    case "chain": {
      const event = String(flags._[1] ?? "");
      if (!event) {
        process.stderr.write("usage: ai-eng chain <event> < payload-json\n");
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
      process.stderr.write(`unknown verb: ${String(verb)}\n`);
      return 2;
  }

}

main()
  .then((code) => process.exit(code))
  .catch((error) => {
    process.stderr.write(`ai-eng: ${error instanceof Error ? error.message : String(error)}\n`);
    process.exit(2);
  });
