#!/usr/bin/env bun
/**
 * ai-eng — CLI entry point for the ai-engineering framework.
 *
 * Three layers (see plan.md §1):
 *   1. Deterministic   — install, cleanup, doctor, plugin, board, governance
 *                        risk, migrate, sync-mirrors  (NO LLM)
 *   2. IDE delegation  — specify, plan, implement, debug, review, verify
 *                        (spawns claude-code/codex/cursor-agent/gemini)
 *   3. BYOK opt-in     — provider add  (only when no IDE host available)
 */

import { commands } from "./commands/index.ts";

const HELP_TEXT = `ai-eng — multi-IDE AI agentic governance framework

Usage:
  ai-eng <command> [args...]

Foundational:
  bootstrap            Install + scaffold a new project
  doctor               Diagnose + heal local install (--fix)
  sync-mirrors         Regenerate IDE mirrors from skills/catalog
  cleanup              Tidy up branches and worktrees

Workflow (delegates to IDE host):
  specify "<text>"     Interrogate + draft a spec (HARD GATE)
  plan                 Decompose approved spec into tasks
  implement            Execute approved plan via builder agent
  test | debug         TDD + root-cause diagnosis
  review | verify      Human-quality review + deterministic gates
  commit               Governed commit (ruff + gitleaks + conventional)
  pr                   Open PR + watch CI to green

Governance:
  governance audit     Compliance + ownership + manifest integrity
  release-gate         GO / CONDITIONAL / NO-GO across 8 dimensions
  risk accept          Logged risk acceptance (TTL by severity)

Plugins:
  plugin search <q>    Search 3-tier marketplace
  plugin install <id>  Verify Sigstore + SLSA + SBOM, then install
  plugin verify        Re-verify all installed plugins

Multi-LLM:
  llm list-providers   Configured providers (default: piggyback IDE host)
  llm add-provider     BYOK opt-in (CI use)

Run "ai-eng <command> --help" for more.`;

const main = async (argv: string[]): Promise<number> => {
  const [, , command, ...rest] = argv;

  if (!command || command === "--help" || command === "-h") {
    process.stdout.write(`${HELP_TEXT}\n`);
    return 0;
  }
  if (command === "--version" || command === "-v") {
    process.stdout.write("ai-eng 3.0.0-alpha.0\n");
    return 0;
  }

  const handler = commands[command];
  if (!handler) {
    process.stderr.write(
      `unknown command: ${command}\nrun 'ai-eng --help' to see available commands\n`,
    );
    return 2;
  }
  return handler(rest);
};

const code = await main(process.argv);
process.exit(code);
