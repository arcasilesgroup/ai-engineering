#!/usr/bin/env bun
// src/cli.ts — flags first (@bomb.sh/args), prompts only for what's missing
// (@clack/prompts), TAB everywhere (@bomb.sh/tab). Six human verbs; the four
// machine verbs (chain|git|wrap|spec) are the product's programming surface (§07)
// and appear in neither TAB nor --help.

import { parse } from "@bomb.sh/args";
import tabRoot from "@bomb.sh/tab";
import { VERSION } from "./version.ts";
import { showLogo } from "./branding.ts";
import { maybeNotice } from "./notice.ts";
import { chainMain } from "./chain/mod.ts";
import { surfaceDialect } from "./surfaces/adapters.ts";
import { doctorMain } from "./commands/doctor.ts";
import { initMain } from "./commands/init.ts";
import { updateMain } from "./commands/update.ts";
import { upgradeMain } from "./commands/upgrade.ts";
import { uninstallMain } from "./commands/uninstall.ts";
import { configMain } from "./commands/config.ts";
import { wrapMain } from "./wrap/index.ts";
import { specMain } from "./spec/index.ts";
import { floor } from "./floor/entry.ts";
import { suggestVerb } from "./shared-verbs.ts";

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
  process.stdout.write("  ai-eng init       install governance (global without a repo; contract inside)\n");
  process.stdout.write("  ai-eng doctor     12 checks + one real adversarial probe + --gc\n");
  process.stdout.write("  ai-eng config     surfaces and thresholds\n");
  process.stdout.write("  ai-eng update     rewrite ai-eng's files from the installed binary (zero network)\n");
  process.stdout.write("  ai-eng upgrade    delegate to bun/npm\n");
  process.stdout.write("  ai-eng uninstall  revert ours, keep yours\n\n");
  process.stdout.write("Machine verbs (hooks/CI): chain · git · wrap · spec\n");
  process.exit(flags.help ? 0 : 2);
}

// --surface accepts repetition AND comma lists: "--surface a --surface b" and
// "--surface a,b" both reach initMain as ["a","b"]. @bomb.sh/args collapses
// repeated string flags to the last value; raw argv is the only truth.
const surfaceList: string[] = process.argv
  .slice(2)
  .flatMap((arg, i, argv) => {
    if (arg === "--surface") return (argv[i + 1] ?? "").split(",").filter(Boolean);
    if (arg.startsWith("--surface=")) return arg.slice("--surface=".length).split(",").filter(Boolean);
    return [];
  });

async function main(): Promise<number> {
  switch (verb) {
    case "chain": {
      const event = String(flags._[1] ?? "");
      if (!event) {
        process.stderr.write("usage: ai-eng chain <event> < payload-json\n");
        return 2;
      }
      const raw = await Bun.stdin.text();
      const surface = surfaceList[0] ?? "claude-code";
      chainMain(event, raw, { surface, dialect: surfaceDialect(surface) });
      return 0; // chainMain exits on its own when it denies
    }
    case "git":
      return floor(String(flags._[1] ?? ""), flags._[2] != null ? String(flags._[2]) : undefined);
    case "wrap":
      return wrapMain(process.argv.slice(3).map(String));
    case "spec":
      return specMain(flags._.slice(1).map(String));
    case "init":
      { const code = await initMain({ yes: flags.yes === true, global: flags.global === true, surface: surfaceList }); if (code === 0) maybeNotice(); return code; }
    case "doctor":
      { const code = await doctorMain({ gc: flags.gc === true }); if (code === 0) maybeNotice(); return code; }
    case "config": {
      const configFlags: { add?: string; remove?: string } = {};
      if (typeof flags.add === "string") configFlags.add = flags.add;
      if (typeof flags.remove === "string") configFlags.remove = flags.remove;
      return configMain(configFlags);
    }
    case "update":
      { const code = await updateMain({ yes: flags.yes === true }); if (code === 0) maybeNotice(); return code; }
    case "upgrade":
      return upgradeMain();
    case "uninstall":
      return uninstallMain();
    default: {
      const typed = String(verb);
      const suggestion = suggestVerb(typed);
      process.stderr.write(`unknown verb: ${typed}\n`);
      process.stderr.write(
        suggestion
          ? `did you mean \`ai-eng ${suggestion}\`? run \`ai-eng --help\` for the rest.\n`
          : "run `ai-eng --help` for the six human verbs and the four machine ones.\n",
      );
      return 2;
    }
  }

}

main()
  .then((code) => process.exit(code))
  .catch((error) => {
    process.stderr.write(`ai-eng: ${error instanceof Error ? error.message : String(error)}\n`);
    process.exit(2);
  });
