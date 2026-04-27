import { bootstrap } from "./bootstrap.ts";
import { doctor } from "./doctor.ts";
import { syncMirrors } from "./sync_mirrors.ts";

export type CommandHandler = (args: string[]) => Promise<number>;

const stub =
  (name: string): CommandHandler =>
  async (_args) => {
    process.stdout.write(
      `[ai-eng] '${name}' is scaffolded but not yet wired (Phase 4 driving adapters).\n` +
        "      The plan + storyboards live in the README and ADRs.\n",
    );
    return 0;
  };

export const commands: Readonly<Record<string, CommandHandler>> = Object.freeze(
  {
    bootstrap,
    doctor,
    "sync-mirrors": syncMirrors,
    // Workflow — Phase 4 wires these to IDE host delegation
    specify: stub("specify"),
    plan: stub("plan"),
    implement: stub("implement"),
    test: stub("test"),
    debug: stub("debug"),
    review: stub("review"),
    verify: stub("verify"),
    commit: stub("commit"),
    pr: stub("pr"),
    // Governance — Phase 1+2 in progress
    governance: stub("governance"),
    "release-gate": stub("release-gate"),
    risk: stub("risk"),
    // Plugins — Phase 7
    plugin: stub("plugin"),
    // Multi-LLM — Phase 5
    llm: stub("llm"),
    // SDLC ops
    cleanup: stub("cleanup"),
    resolve: stub("resolve"),
    postmortem: stub("postmortem"),
    hotfix: stub("hotfix"),
  },
);
