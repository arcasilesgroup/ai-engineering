// Session handoff briefing — auto-generate state at session start so the agent
// doesn't waste 30-50 messages rebuilding context (research 005, research 006 R1).
// Called via `ai-eng briefing` or at the start of a session when the surface
// supports promptHook.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { repoRoot, isGoverned } from "../env.ts";
import { summarizeReceipts, type ReceiptSummary } from "../receipts.ts";

export type Briefing = {
  /** ISO timestamp of this briefing. */
  ts: string;
  /** Whether the repo is governed (has .ai-engineering/config.toml). */
  governed: boolean;
  /** The spec slot status. */
  spec: { exists: boolean; approved: boolean; gates?: string };
  /** Current plan step (first non-green gate, or "all green"). */
  plan: { exists: boolean; current_step: string };
  /** Recent denies (last 10). */
  recent_denies: Array<{ ts: string; tool: string; guard: string; reason: string }>;
  /** Receipt summary (total runs, denies, p50, p95). */
  receipts: ReceiptSummary;
  /** Active overrides from overrides.toml. */
  overrides: string[];
  /** Research cache files. */
  research_cache: string[];
};

function readTextSafe(path: string): string | null {
  try {
    return readFileSync(path, "utf8");
  } catch {
    return null;
  }
}

function parseSpecGates(html: string): string | undefined {
  // First pending gate only — RegExp.exec (Sonar S6594), not String.match.
  const match = /- \[ \] (G\d+): (.+)/.exec(html);
  return match ? `${match[1]}: ${match[2]}` : undefined;
}

function parsePlanCurrentStep(html: string): string {
  const match = /- \[ \] (.+)/.exec(html);
  return match?.[1] ?? "all green";
}

function loadOverrides(root: string): string[] {
  const overridesPath = join(root, ".ai-engineering", "overrides.toml");
  const content = readTextSafe(overridesPath);
  if (!content) return [];
  const lines = content.split("\n").filter((l) => l.trim() && !l.startsWith("#"));
  return lines.map((l) => l.trim());
}

function loadResearchCache(root: string): string[] {
  const cacheDir = join(root, ".ai-engineering", "research-cache");
  if (!existsSync(cacheDir)) return [];
  return readdirSync(cacheDir).filter((f) => f.endsWith(".md"));
}

/** Generate a session handoff briefing. Called at session start to give the agent
 *  immediate context without re-reading every file. */
export function generateBriefing(root?: string | null): Briefing {
  const resolved = root ?? repoRoot();
  const governed = resolved !== null && isGoverned(resolved);

  // Spec
  const specPath = resolved ? join(resolved, ".ai-engineering", "spec.html") : null;
  const specContent = specPath ? readTextSafe(specPath) : null;
  const specExists = specContent !== null;
  const specApproved = specContent?.includes("sha256 in lock") ?? false;
  const specGates = specContent ? parseSpecGates(specContent) : null;

  // Plan
  const planPath = resolved ? join(resolved, ".ai-engineering", "plan.html") : null;
  const planContent = planPath ? readTextSafe(planPath) : null;
  const planExists = planContent !== null;
  const planCurrentStep = planContent ? parsePlanCurrentStep(planContent) : "no plan";

  // Receipts
  const receipts = summarizeReceipts();

  // Recent denies (last 10, reading receipt files directly)
  const recentDenies: Briefing["recent_denies"] = [];
  // Read the actual receipt files to get deny details
  if (governed && resolved) {
    const receiptsDir = join(resolved, ".ai-engineering", "receipts");
    if (existsSync(receiptsDir)) {
      try {
        const files = readdirSync(receiptsDir)
          .filter((f) => f.endsWith(".json") && f !== "summary.json" && f !== "denies.json")
          .sort((left, right) => right.localeCompare(left))
          .slice(0, 50); // newest names first
        for (const file of files) {
          if (recentDenies.length >= 10) break;
          try {
            const receipt = JSON.parse(readFileSync(join(receiptsDir, file), "utf8"));
            if (receipt.outcome === "deny") {
              recentDenies.push({
                ts: receipt.ts ?? "",
                tool: receipt.tool ?? "",
                guard: receipt.guards?.denied_by ?? "",
                reason: (receipt.guards?.denied_by ? `denied by ${receipt.guards.denied_by}` : "denied"),
              });
            }
          } catch {
            /* torn write */
          }
        }
      } catch {
        /* no receipts */
      }
    }
  }

  // Overrides
  const overrides = governed && resolved ? loadOverrides(resolved) : [];

  // Research cache
  const researchCache = governed && resolved ? loadResearchCache(resolved) : [];

  return {
    ts: new Date().toISOString(),
    governed,
    spec: { exists: specExists, approved: specApproved, ...(specGates ? { gates: specGates } : {}) },
    plan: { exists: planExists, current_step: planCurrentStep },
    recent_denies: recentDenies,
    receipts,
    overrides,
    research_cache: researchCache,
  };
}

/** Print the briefing as human-readable text for the agent to consume. */
export function formatBriefing(briefing: Briefing): string {
  const lines: string[] = [];
  lines.push(`# Session Handoff Briefing — ${briefing.ts}`);
  lines.push("");

  if (!briefing.governed) {
    lines.push("⚠ This repo is not governed (no .ai-engineering/config.toml).");
    lines.push("Run `ai-eng init` to start governing.");
    return lines.join("\n");
  }

  // Spec
  if (briefing.spec.exists) {
    if (briefing.spec.approved) {
      lines.push("✅ Spec: approved (sha256 in lock)");
    } else {
      lines.push("⚠ Spec: exists but NOT approved — run `ai-eng spec approve` before starting work");
    }
    if (briefing.spec.gates) {
      lines.push(`   Next gate: ${briefing.spec.gates}`);
    }
  } else {
    lines.push("❌ Spec: no spec.html — nothing to execute");
  }

  // Plan
  if (briefing.plan.exists) {
    lines.push(`📋 Plan: ${briefing.plan.current_step}`);
  }

  // Receipts
  if (briefing.receipts.total > 0) {
    lines.push(`📊 Receipts: ${briefing.receipts.total} runs, ${briefing.receipts.denies} denies, p50=${briefing.receipts.p50}ms p95=${briefing.receipts.p95}ms`);
  }

  // Recent denies
  if (briefing.recent_denies.length > 0) {
    lines.push(`🚫 Recent denies (${briefing.recent_denies.length}):`);
    for (const deny of briefing.recent_denies.slice(0, 5)) {
      lines.push(`   - [${deny.ts.slice(0, 19)}] ${deny.tool}: ${deny.reason}`);
    }
  }

  // Overrides
  if (briefing.overrides.length > 0) {
    lines.push(`🔧 Active overrides: ${briefing.overrides.length}`);
  }

  // Research cache
  if (briefing.research_cache.length > 0) {
    lines.push(`📚 Research cache: ${briefing.research_cache.length} files`);
  }

  return lines.join("\n");
}
