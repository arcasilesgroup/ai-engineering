#!/usr/bin/env bun
// src/cli.ts — raw argv, prompts only for what's missing (@clack/prompts). Human
// verbs get a line in --help. Machine verbs are named on one line: agents and
// hooks type them, people do not. Both lists come from shared-verbs.ts.

import { VERSION } from "./version.ts";
import { showLogo } from "./branding.ts";
import { maybeNotice } from "./notice.ts";
import { chainMain } from "./chain/mod.ts";
import { surfaceDialect } from "./surfaces/adapters.ts";
import { doctorMain } from "./commands/doctor.ts";
import { initMain } from "./commands/init.ts";
import { updateMain } from "./commands/update.ts";
import { uninstallMain } from "./commands/uninstall.ts";
import { configMain } from "./commands/config.ts";
import { adaptMain } from "./commands/adapt.ts";
import { worktreeMain } from "./commands/worktree.ts";
import { wrapMain } from "./wrap/index.ts";
import { floor } from "./floor/entry.ts";
import { suggestVerb, HUMAN_VERBS, MACHINE_VERBS, ALL_VERBS } from "./shared-verbs.ts";


const argv = process.argv.slice(2);
const BOOLS: Record<string, true> = { yes: true, global: true, help: true, version: true, gc: true, force: true };
const boolFlags: Record<string, true> = {};
const valueFlags: Record<string, string> = {};
const positionals: string[] = [];
const surfaceList: string[] = [];
for (let i = 0; i < argv.length; i++) {
  const arg = argv[i]!;
  if (arg === "--surface" || arg.startsWith("--surface=")) {
    const value = arg === "--surface" ? (argv[++i] ?? "") : arg.slice("--surface=".length);
    surfaceList.push(...value.split(",").filter(Boolean));
  } else if (arg.startsWith("--") && BOOLS[arg.slice(2)]) {
    boolFlags[arg.slice(2)] = true;
  } else if (arg.startsWith("--")) {
    valueFlags[arg.slice(2)] = argv[++i] ?? "";
  } else {
    positionals.push(arg);
  }
}
const flags: { _: string[] } & Record<string, string | boolean | undefined> = Object.assign(
  { _: positionals } as { _: string[] } & Record<string, string | boolean | undefined>,
  boolFlags,
  valueFlags,
);
const verb = positionals[0];

if (flags.version) {
  process.stdout.write(`ai-eng ${VERSION}\n`);
  process.exit(0);
}
if (flags.help || !verb) {
  showLogo(VERSION);
  process.stdout.write("\n");
  const nameWidth = Math.max(...HUMAN_VERBS.map((entry) => entry.verb.length)) + 2;
  for (const { verb: name, description } of HUMAN_VERBS)
    process.stdout.write(`  ai-eng ${name.padEnd(nameWidth)}${description}\n`);
  process.stdout.write("\n");
  process.stdout.write(`Machine verbs (hooks/CI/agents): ${MACHINE_VERBS.join(" · ")}\n`);
  process.exit(flags.help ? 0 : 2);
}

/** The hook payload. Not `Bun.stdin.text()`: on Windows (Bun 1.4) that read, awaited after
 *  module evaluation, does not keep the process alive, so `chain` exited 0 before the
 *  payload arrived and every hook allowed (oven-sh/bun#41850). The stream iterator holds
 *  the event loop until EOF. */
async function readStdin(): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(String(chunk)));
  return Buffer.concat(chunks).toString("utf8");
}

async function main(): Promise<number> {
  const handler = verb !== undefined ? verbMain[verb] : undefined;
  if (handler) return await handler();
  const typed = String(verb);
  const suggestion = suggestVerb(typed);
  process.stderr.write(`unknown verb: ${typed}\n`);
  process.stderr.write(
    suggestion
      ? `did you mean \`ai-eng ${suggestion}\`? run \`ai-eng --help\` for the rest.\n`
      : "run `ai-eng --help` for the human verbs and the machine ones.\n",
  );
  return 2;
}

/** One handler per verb. The verb list is ALL_VERBS; a verb added there without
 *  a handler here crashes on boot instead of answering "unknown verb". */
const verbMain: Record<string, () => number | Promise<number>> = {
  chain: async () => {
    const event = String(flags._[1] ?? "");
    if (!event) {
      process.stderr.write("usage: ai-eng chain <event> < payload-json\n");
      return 2;
    }
    const raw = await readStdin();
    const surface = surfaceList[0] ?? "claude-code";
    chainMain(event, raw, { surface, dialect: surfaceDialect(surface) });
    return 0; // chainMain exits on its own when it denies
  },
  git: () => floor(String(flags._[1] ?? ""), flags._[2] != null ? String(flags._[2]) : undefined),
  wrap: () => wrapMain(process.argv.slice(3).map(String)),
  worktree: () => worktreeMain(flags._.slice(1).map(String), flags.force === true),
  init: async () => {
    const code = await initMain({ yes: flags.yes === true, global: flags.global === true, surface: surfaceList });
    if (code === 0) maybeNotice();
    return code;
  },
  doctor: async () => {
    const code = await doctorMain({ gc: flags.gc === true });
    if (code === 0) maybeNotice();
    return code;
  },
  config: () => {
    const configFlags: { add?: string; remove?: string } = {};
    if (typeof flags.add === "string") configFlags.add = flags.add;
    if (typeof flags.remove === "string") configFlags.remove = flags.remove;
    return configMain(configFlags);
  },
  adapt: () => adaptMain(flags._.slice(1).map(String)),
  update: () => updateMain({ yes: flags.yes === true }),
  uninstall: () => uninstallMain(),
};
const unhandledVerbs = ALL_VERBS.filter((name) => !(name in verbMain));
if (unhandledVerbs.length > 0) throw new Error(`verb without a handler: ${unhandledVerbs.join(", ")}`);

main()
  .then((code) => process.exit(code))
  .catch((error) => {
    process.stderr.write(`ai-eng: ${error instanceof Error ? error.message : String(error)}\n`);
    process.exit(2);
  });
