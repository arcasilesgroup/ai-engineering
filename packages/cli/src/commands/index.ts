import { board } from "./board.ts";
import { bootstrap } from "./bootstrap.ts";
import { cleanup } from "./cleanup.ts";
import { doctor } from "./doctor.ts";
import { governance } from "./governance.ts";
import { llm } from "./llm.ts";
import { migrate } from "./migrate.ts";
import { releaseGate } from "./release_gate.ts";
import { risk } from "./risk.ts";
import { skill } from "./skill.ts";
import { syncMirrors } from "./sync_mirrors.ts";

export type CommandHandler = (args: string[]) => Promise<number>;

const stub =
  (name: string): CommandHandler =>
  async (_args) => {
    process.stdout.write(
      `[ai-eng] '${name}' is scaffolded but not yet wired (Phase 4 driving adapters).\n      The plan + storyboards live in the README and ADRs.\n`,
    );
    return 0;
  };

export const commands: Readonly<Record<string, CommandHandler>> = Object.freeze({
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
  // Governance — Phase 4.1 wired
  governance,
  "release-gate": releaseGate,
  risk,
  // Skill catalog — Phase 4.1 wired
  skill,
  // Board (fail-open) — Phase 4.1 wired
  board,
  // Plugins — Phase 7
  plugin: stub("plugin"),
  // Multi-LLM — Phase 4.1 stub wiring (Phase 5 fills in BYOK)
  llm,
  // SDLC ops — Phase 4.1 wired
  cleanup,
  migrate,
  resolve: stub("resolve"),
  postmortem: stub("postmortem"),
  hotfix: stub("hotfix"),
});
