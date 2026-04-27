import type { Result } from "../kernel/result.ts";

/**
 * AuditLogPort — Dual-Plane Architecture immutable audit log.
 *
 * Every prompt, every thought, every tool execution writes here. The log
 * is append-only and tamper-evident (hash-chained). Real adapters use:
 *   - S3 Object Lock + DynamoDB hash chain (banking)
 *   - QLDB (AWS-native ledger)
 *   - In-memory append-only (tests)
 *
 * Required for SOC2 CC7.2, HIPAA 164.312(b), DORA Art 11-13.
 */
export interface AuditEntry {
  readonly entryId: string;
  readonly timestamp: string;
  readonly actor: string;
  readonly action: string;
  readonly resource: string;
  readonly verdict: "allow" | "deny" | "executed";
  readonly previousHash: string; // hash chain
  readonly currentHash: string;
  readonly metadata: Readonly<Record<string, unknown>>;
}

export class AuditError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AuditError";
  }
}

export interface AuditLogPort {
  append(
    entry: Omit<AuditEntry, "entryId" | "previousHash" | "currentHash">,
  ): Promise<Result<AuditEntry, AuditError>>;
  verifyChain(): Promise<
    Result<{ valid: true } | { valid: false; brokenAt: string }, AuditError>
  >;
  query(
    filter: AuditQueryFilter,
  ): Promise<Result<ReadonlyArray<AuditEntry>, AuditError>>;
}

export interface AuditQueryFilter {
  readonly actor?: string;
  readonly action?: string;
  readonly since?: string;
  readonly until?: string;
}
