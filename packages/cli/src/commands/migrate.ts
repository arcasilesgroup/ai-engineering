import { existsSync } from "node:fs";
import { join } from "node:path";

import { hasFlag, parseArgs } from "./_args.ts";
import type { CommandHandler } from "./index.ts";

/**
 * `ai-eng migrate <from-to>` — migration helper.
 *
 * Phase 4.1 ships only `migrate v2-to-v3 --dry-run` as a deterministic
 * preview. The actual rewriter lands in Phase 8 — until then, running
 * without `--dry-run` exits 1 to prevent accidental destructive runs.
 *
 * The dry-run inspects a small set of v2 sentinel paths and prints the
 * planned moves so the user can review before committing.
 */
interface Plan {
  readonly from: string;
  readonly to: string;
  readonly action: "move" | "rewrite" | "skip";
  readonly reason?: string;
}

const SENTINELS: ReadonlyArray<{
  readonly from: string;
  readonly to: string;
  readonly action: "move" | "rewrite";
}> = Object.freeze([
  {
    from: ".ai-engineering/manifest.yml",
    to: ".ai-engineering/manifest.toml",
    action: "rewrite",
  },
  { from: ".ai-engineering/skills", to: "skills/catalog", action: "move" },
  { from: ".ai-engineering/agents", to: "agents/catalog", action: "move" },
  {
    from: ".ai-engineering/contexts",
    to: ".ai-engineering/contexts",
    action: "move",
  },
]);

const buildPlan = (cwd: string): ReadonlyArray<Plan> => {
  const out: Plan[] = [];
  for (const s of SENTINELS) {
    const abs = join(cwd, s.from);
    if (existsSync(abs)) {
      out.push({ from: s.from, to: s.to, action: s.action });
    } else {
      out.push({
        from: s.from,
        to: s.to,
        action: "skip",
        reason: "source not present",
      });
    }
  }
  return out;
};

const v2ToV3Handler = async (rest: ReadonlyArray<string>): Promise<number> => {
  const parsed = parseArgs(rest);
  if (!hasFlag(parsed, "dry-run")) {
    process.stderr.write(
      "[ai-eng] migrate v2-to-v3: Phase 8 not yet implemented. Re-run with --dry-run for a preview.\n",
    );
    return 1;
  }
  const plan = buildPlan(process.cwd());
  if (hasFlag(parsed, "json")) {
    process.stdout.write(`${JSON.stringify({ plan }, null, 2)}\n`);
    return 0;
  }
  process.stdout.write("[ai-eng] migrate v2-to-v3 (dry-run)\n");
  for (const p of plan) {
    if (p.action === "skip") {
      process.stdout.write(`  [SKIP] ${p.from} -- ${p.reason ?? "(no reason)"}\n`);
    } else {
      process.stdout.write(`  [${p.action.toUpperCase()}] ${p.from} -> ${p.to}\n`);
    }
  }
  process.stdout.write(
    `[ai-eng] migrate v2-to-v3: ${plan.filter((p) => p.action !== "skip").length} planned action(s); no files modified.\n`,
  );
  return 0;
};

const usage = (): void => {
  process.stderr.write("usage: ai-eng migrate v2-to-v3 [--dry-run] [--json]\n");
};

export const migrate: CommandHandler = async (args) => {
  const [sub, ...rest] = args;
  if (sub === undefined) {
    usage();
    return 1;
  }
  if (sub === "v2-to-v3") return v2ToV3Handler(rest);
  process.stderr.write(`unknown migrate subcommand: ${sub}\n`);
  usage();
  return 1;
};
