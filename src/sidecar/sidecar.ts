// Async sidecar for background classification. Receives tool call payloads,
// queues them for classification (against Jev or local rules), and writes
// results to .ai-engineering/shadow/ alongside receipts. Uses the concurrent
// queue for backpressure — rejects when full instead of accumulating.

import { writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { randomUUID } from "node:crypto";
import { ConcurrentQueue } from "./queue.ts";

export interface ShadowClassification {
  schema: "urn:ai-eng:shadow:1";
  id: string;
  tool: string;
  toolInput: Record<string, unknown>;
  sessionId: string | undefined;
  /** The primary guard's decision (allow/deny/review) before shadow classification. */
  primaryAction: string;
  /** The shadow classifier's verdict. null when classification failed. */
  shadowVerdict: { action: string; risk: number; reason: string } | null;
  latencyMs: number;
  ts: string;
}

export interface SidecarOptions {
  /** Directory to write shadow classifications. Defaults to .ai-engineering/shadow/. */
  shadowDir?: string;
  /** Maximum concurrent classifications. Default: 4. */
  concurrency?: number;
  /** Maximum queued jobs. Default: 100. */
  maxDepth?: number;
  /** Classification function. Receives the payload and returns a verdict.
   *  When absent, the sidecar writes a null verdict (placeholder for future Jev integration). */
  classifier?: (payload: Record<string, unknown>) => Promise<{ action: string; risk: number; reason: string }>;
}

export class Sidecar {
  private readonly queue: ConcurrentQueue;
  private readonly shadowDir: string;
  private readonly classifier: SidecarOptions["classifier"];

  constructor(options: SidecarOptions = {}) {
    this.queue = new ConcurrentQueue(options.concurrency ?? 4, options.maxDepth ?? 100);
    this.shadowDir = options.shadowDir ?? join(process.cwd(), ".ai-engineering", "shadow");
    this.classifier = options.classifier;
  }

  /** Enqueue a tool call for background classification. Returns the job ID.
   *  Throws QueueFullError when at capacity. */
  submit(
    tool: string,
    toolInput: Record<string, unknown>,
    primaryAction: string,
    sessionId?: string,
  ): string {
    const id = randomUUID();
    this.queue.submit(async () => {
      const started = Date.now();
      let shadowVerdict: ShadowClassification["shadowVerdict"] = null;
      try {
        if (this.classifier) {
          shadowVerdict = await this.classifier({ tool_name: tool, tool_input: toolInput, session_id: sessionId });
        }
      } catch {
        shadowVerdict = null;
      }
      const classification: ShadowClassification = {
        schema: "urn:ai-eng:shadow:1",
        id,
        tool,
        toolInput,
        sessionId,
        primaryAction,
        shadowVerdict,
        latencyMs: Date.now() - started,
        ts: new Date().toISOString(),
      };
      this.writeShadow(classification);
      return classification;
    }, id).catch(() => {
      // Background job — errors are logged via writeShadow, not propagated.
    });
    return id;
  }

  /** Current queue state. */
  snapshot() {
    return this.queue.snapshot();
  }

  private writeShadow(classification: ShadowClassification): void {
    try {
      mkdirSync(this.shadowDir, { recursive: true });
      const stamp = classification.ts.replace(/[:.]/g, "-");
      writeFileSync(
        join(this.shadowDir, `${stamp}-${classification.id}.json`),
        JSON.stringify(classification),
      );
    } catch {
      // Shadow writes must never crash the sidecar.
    }
  }
}
