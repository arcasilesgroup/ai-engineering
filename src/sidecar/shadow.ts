// Shadow evaluation — runs two rule configurations in parallel and records
// whether they disagree. Produces a dataset for threshold calibration:
// for each tool call, which rules matched, what action each config chose,
// and whether the action changed. Inspired by Pyro's shadow profiles.

import { writeFileSync, mkdirSync, readFileSync, readdirSync, existsSync } from "node:fs";
import { join } from "node:path";
import type { LocalRule } from "../guards/local-rules.ts";
import { evaluateLocalRules } from "../guards/local-rules.ts";

export interface ShadowResult {
  schema: "urn:ai-eng:shadow-eval:1";
  id: string;
  tool: string;
  toolInput: Record<string, unknown>;
  sessionId: string | undefined;
  /** The active config's decision. */
  active: { action: string; risk: number; matchedRules: string[] };
  /** The shadow config's decision. */
  shadow: { action: string; risk: number; matchedRules: string[] };
  /** true when active.action !== shadow.action */
  changed: boolean;
  ts: string;
}

export interface ShadowEvalConfig {
  /** Rules for the active configuration (the one that governs). */
  activeRules: LocalRule[];
  /** Rules for the shadow configuration (the one being tested). */
  shadowRules: LocalRule[];
  /** Directory to write shadow evaluation results. */
  outputDir?: string;
}

function decideAction(rules: LocalRule[], tool: string, toolInput: Record<string, unknown>, toolResponse?: unknown): { action: string; risk: number; matchedRules: string[] } {
  const payload = { tool_name: tool, tool_input: toolInput, tool_response: toolResponse };
  const matches = evaluateLocalRules(payload as never, rules);
  if (matches.length === 0) return { action: "allow", risk: 0, matchedRules: [] };
  const blockMatch = matches.find((m) => m.rule.action === "block");
  if (blockMatch) return { action: "block", risk: blockMatch.rule.risk, matchedRules: matches.map((m) => m.rule.id) };
  const reviewMatch = matches[0]!;
  return { action: "review", risk: reviewMatch.rule.risk, matchedRules: matches.map((m) => m.rule.id) };
}

/** Evaluate a payload against both active and shadow configs. Returns the result
 *  and optionally writes it to the output directory. */
export function evaluateShadow(
  config: ShadowEvalConfig,
  id: string,
  tool: string,
  toolInput: Record<string, unknown>,
  sessionId?: string,
  toolResponse?: unknown,
): ShadowResult {
  const active = decideAction(config.activeRules, tool, toolInput, toolResponse);
  const shadow = decideAction(config.shadowRules, tool, toolInput, toolResponse);
  const result: ShadowResult = {
    schema: "urn:ai-eng:shadow-eval:1",
    id,
    tool,
    toolInput,
    sessionId,
    active,
    shadow,
    changed: active.action !== shadow.action,
    ts: new Date().toISOString(),
  };
  if (config.outputDir) {
    writeShadowResult(config.outputDir, result);
  }
  return result;
}

function writeShadowResult(dir: string, result: ShadowResult): void {
  try {
    mkdirSync(dir, { recursive: true });
    const stamp = result.ts.replace(/[:.]/g, "-");
    writeFileSync(join(dir, `${stamp}-${result.id}.json`), JSON.stringify(result));
  } catch {
    // Shadow writes must never crash the evaluator.
  }
}

export interface CalibrationDataset {
  total: number;
  changed: number;
  /** Breakdown by action transition: { "allow→block": N, ... } */
  transitions: Record<string, number>;
  /** Per-rule hit counts across all evaluations. */
  ruleHits: Record<string, number>;
}

/** Aggregate shadow evaluation results from a directory into a calibration dataset. */
export function loadCalibrationDataset(dir: string): CalibrationDataset {
  if (!existsSync(dir)) return { total: 0, changed: 0, transitions: {}, ruleHits: {} };
  const files = readdirSync(dir).filter((f) => f.endsWith(".json"));
  const dataset: CalibrationDataset = { total: files.length, changed: 0, transitions: {}, ruleHits: {} };
  for (const file of files) {
    try {
      const content = JSON.parse(readFileSync(join(dir, file), "utf8")) as ShadowResult;
      if (content.schema !== "urn:ai-eng:shadow-eval:1") continue;
      if (content.changed) dataset.changed += 1;
      const transition = `${content.active.action}→${content.shadow.action}`;
      dataset.transitions[transition] = (dataset.transitions[transition] ?? 0) + 1;
      for (const ruleId of content.shadow.matchedRules) {
        dataset.ruleHits[ruleId] = (dataset.ruleHits[ruleId] ?? 0) + 1;
      }
    } catch {
      // Skip malformed files.
    }
  }
  return dataset;
}
