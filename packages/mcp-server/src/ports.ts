import type {
  Decision,
  DecisionId,
  ReleaseAggregate,
  Result,
  Severity,
  StoreError,
  TelemetryPort,
  ValidationError,
} from "@ai-engineering/runtime";

/**
 * Driven ports consumed by the MCP server.
 *
 * Hexagonal: handlers depend on these interfaces, not on filesystem or
 * runtime adapters directly. The CLI wires concrete adapters in; tests
 * wire fakes in. The server module never imports a Bun-specific API.
 */

export interface SkillCatalogPort {
  /** Enumerate skills with stable URIs. */
  list(): Promise<ReadonlyArray<{ name: string; uri: string }>>;
  /** Read raw SKILL.md content (frontmatter + body). Null if missing. */
  read(name: string): Promise<string | null>;
}

export interface AgentCatalogPort {
  list(): Promise<ReadonlyArray<{ name: string; uri: string }>>;
  read(name: string): Promise<string | null>;
}

export interface ManifestPort {
  load(): Promise<Record<string, unknown>>;
}

/**
 * Input shape consumed by the `accept_risk` MCP tool.
 *
 * Distinct from runtime's `AcceptRiskInput` so the server can adapt MCP
 * arguments (snake_case JSON) into the kernel-id form the use case
 * expects without leaking JSON-RPC concerns into the runtime layer.
 */
export interface AcceptRiskCommand {
  readonly id: DecisionId;
  readonly findingId: string;
  readonly severity: Severity;
  readonly justification: string;
  readonly owner: string;
  readonly specRef: string;
  readonly issuedAt: Date;
}

export interface DecisionsPort {
  /** Returns currently-active decisions for `ai-engineering://decisions`. */
  list(): Promise<ReadonlyArray<unknown>>;
  /** Records a logged risk acceptance (per Constitution Article VII). */
  accept(input: AcceptRiskCommand): Promise<Result<Decision, ValidationError | StoreError>>;
}

export type RunReleaseGateFn = () => Promise<ReleaseAggregate>;

/** Composition root deps for the MCP server. */
export interface ServerDeps {
  readonly skills: SkillCatalogPort;
  readonly agents: AgentCatalogPort;
  readonly manifest: ManifestPort;
  readonly decisions: DecisionsPort;
  readonly runReleaseGate: RunReleaseGateFn;
  readonly constitution: string;
  readonly telemetry: TelemetryPort;
}
