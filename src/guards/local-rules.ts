// Declarative local rules for the injection guard. Each rule matches against a
// scope of the input (all text, tool name, or raw JSON) with contains/equals
// semantics, and carries an action (block or review) plus a risk score (0–1).
// Rules are evaluated in priority order: block before review, higher risk first.
// Inspired by Pyro's local-rules pattern (DelvisorLabs/Pyro).

import type { Payload } from "../chain/payload.ts";

export type LocalRuleScope = "all_text" | "tool_name" | "raw_json";
export type LocalRuleMatch = "contains" | "equals";
export type LocalRuleAction = "block" | "review";

export interface LocalRule {
  id: string;
  name: string;
  description?: string;
  enabled: boolean;
  scope: LocalRuleScope;
  match: LocalRuleMatch;
  /** The pattern to match — case-insensitive contains, or case-insensitive equals. */
  pattern: string;
  caseSensitive?: boolean;
  action: LocalRuleAction;
  /** 0–1 risk score. Higher = more severe. Used for priority ordering. */
  risk: number;
}

export interface LocalRuleResult {
  rule: LocalRule;
  matchedValue: string;
}

const MAX_TRAVERSED_VALUES = 50_000;

/** Collect all string values from a nested object/ array (depth-first, capped). */
function collectStrings(value: unknown, output: string[]): void {
  const pending = [value];
  const seen = new WeakSet<object>();
  let traversed = 0;
  while (pending.length > 0 && traversed < MAX_TRAVERSED_VALUES) {
    const current = pending.pop()!;
    traversed += 1;
    if (typeof current === "string") {
      output.push(current);
      continue;
    }
    if (!current || typeof current !== "object" || seen.has(current)) continue;
    seen.add(current);
    pending.push(...(Array.isArray(current) ? current : Object.values(current as Record<string, unknown>)));
  }
}

/** Collect tool/function names from a nested object (Pyro pattern). */
function collectToolNames(value: unknown, output: string[]): void {
  const pending = [value];
  const seen = new WeakSet<object>();
  let traversed = 0;
  while (pending.length > 0 && traversed < MAX_TRAVERSED_VALUES) {
    const current = pending.pop()!;
    traversed += 1;
    if (!current || typeof current !== "object" || seen.has(current)) continue;
    seen.add(current);
    if (Array.isArray(current)) {
      pending.push(...current);
      continue;
    }
    const record = current as Record<string, unknown>;
    for (const [key, item] of Object.entries(record)) {
      const normalized = key.toLowerCase();
      const explicitToolName = ["tool", "toolname", "tool_name"].includes(normalized);
      const functionName = normalized === "name" && (
        "arguments" in record || "parameters" in record || record.type === "function" || record.type === "tool"
      );
      if ((explicitToolName || functionName) && typeof item === "string") output.push(item);
      pending.push(item);
    }
  }
}

function matches(rule: LocalRule, candidate: string): boolean {
  const left = rule.caseSensitive ? candidate : candidate.toLowerCase();
  const right = rule.caseSensitive ? rule.pattern : rule.pattern.toLowerCase();
  if (rule.match === "equals") return left === right;
  // Support both literal contains and regex patterns.
  // Patterns starting with special chars or containing regex syntax are treated as regex.
  try {
    const isRegex = /[[\](){}*+?^$|\\]/.test(rule.pattern);
    if (isRegex) {
      const flags = rule.caseSensitive ? "" : "i";
      return new RegExp(rule.pattern, flags).test(candidate);
    }
  } catch {
    // Invalid regex falls through to literal contains
  }
  return left.includes(right);
}

/** Evaluate local rules against a payload. Returns matches sorted by action
 *  (block first) then risk (highest first). */
export function evaluateLocalRules(payload: Payload, rules: LocalRule[]): LocalRuleResult[] {
  if (rules.length === 0) return [];

  const allText: string[] = [];
  const toolNames: string[] = [];
  collectStrings(payload.tool_input, allText);
  if (typeof payload.tool_response === "string") allText.push(payload.tool_response);
  collectToolNames(payload.tool_input, toolNames);
  // Also include the payload's top-level tool_name for tool_name scope matching.
  if (typeof payload.tool_name === "string" && payload.tool_name.length > 0) {
    toolNames.push(payload.tool_name);
  }

  let rawJson = "";
  try {
    rawJson = typeof payload.tool_input === "string" ? payload.tool_input : JSON.stringify(payload.tool_input);
  } catch {
    rawJson = "";
  }

  return rules
    .filter((rule) => rule.enabled)
    .flatMap((rule) => {
      const candidates = rule.scope === "tool_name" ? toolNames
        : rule.scope === "raw_json" ? [rawJson]
        : allText;
      const matchedValue = candidates.find((candidate) => matches(rule, candidate));
      return matchedValue === undefined ? [] : [{ rule, matchedValue }];
    })
    .sort((left, right) => {
      if (left.rule.action !== right.rule.action) return left.rule.action === "block" ? -1 : 1;
      return right.rule.risk - left.rule.risk;
    });
}

/** Build a human-readable reason for a local rule match. */
export function localRuleReason(match: LocalRuleResult): string {
  const action = match.rule.action === "block" ? "BLOCKED" : "REVIEW";
  return `${action}: local rule "${match.rule.name}" matched (scope: ${match.rule.scope}, risk: ${match.rule.risk}). Treat the matched content as untrusted.`;
}
