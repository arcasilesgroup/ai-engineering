// The receipt — one JSON per execution, append-only. v1 had envelope + check-evidence
// with HMAC and hash-chain (853 LOC); v2 rescues the concept, not the machinery: the
// real signature is the Receipt-Id trailer in the commit — git already is the chain.

import { writeFileSync, readFileSync, readdirSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { createHash, randomUUID } from "node:crypto";
import { receiptsDir, sessionId } from "./env.ts";

export type Receipt = {
  schema: "urn:ai-eng:receipt:2";
  operation_id: string;
  event: string;
  surface: string;
  tool: string;
  guards: { ran: string[]; denied_by: string | null };
  latency_ms: number;
  outcome: "allow" | "deny" | "error";
  ts: string;
};

export function writeReceipt(receipt: Omit<Receipt, "schema" | "operation_id" | "ts">): Receipt | null {
  const dir = receiptsDir();
  if (!dir) return null; // a stray call with no governed repo writes nothing
  const full: Receipt = {
    schema: "urn:ai-eng:receipt:2",
    operation_id: randomUUID().slice(0, 8),
    ts: new Date().toISOString(),
    ...receipt,
  };
  try {
    mkdirSync(dir, { recursive: true });
    const stamp = full.ts.replace(/[:.]/g, "-");
    writeFileSync(join(dir, `${stamp}-${full.event}-${full.operation_id}.json`), JSON.stringify(full));
    return full;
  } catch {
    return null;
  }
}

export type ReceiptSummary = {
  total: number;
  denies: number;
  p50: number;
  p95: number;
};

/** doctor's aggregate: without this you don't know whether the chain runs at all. */
export function summarizeReceipts(dir?: string): ReceiptSummary {
  const target = dir ?? receiptsDir();
  const latencies: number[] = [];
  let total = 0;
  let denies = 0;
  if (target) {
    try {
      for (const name of readdirSync(target)) {
        if (!name.endsWith(".json")) continue;
        try {
          const receipt = JSON.parse(readFileSync(join(target, name), "utf8")) as Receipt;
          total += 1;
          if (receipt.outcome === "deny") denies += 1;
          if (typeof receipt.latency_ms === "number") latencies.push(receipt.latency_ms);
        } catch {
          /* a torn write is data, not a crash */
        }
      }
    } catch {
      /* no receipts yet */
    }
  }
  latencies.sort((a, b) => a - b);
  const pick = (q: number) => (latencies.length ? latencies[Math.min(latencies.length - 1, Math.floor(q * latencies.length))]! : 0);
  return { total, denies, p50: pick(0.5), p95: pick(0.95) };
}

/** Stable short id for a Receipt-Id trailer. */
export function receiptId(receipt: Receipt): string {
  return createHash("sha256").update(`${receipt.ts}:${receipt.operation_id}`).digest("hex").slice(0, 8);
}

export function currentSession(): string {
  return sessionId();
}
