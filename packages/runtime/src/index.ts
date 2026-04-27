// Public surface of @ai-engineering/runtime.
//
// Hexagonal layers:
//   - shared/kernel  — primitives (Result, errors, branded ids)
//   - shared/ports   — interfaces (FilesystemPort, LLMPort, PolicyPort, …)
//   - <ctx>/domain   — pure domain entities and policies
//   - <ctx>/application — use cases composed from domain + ports
//   - <ctx>/adapters — concrete adapter implementations
//
// Bounded contexts (Screaming Architecture): governance, skills, agents,
// observability, platform, delivery.

export * from "./shared/kernel/index.ts";
export * from "./shared/ports/index.ts";

// Skills domain
export * from "./skills/domain/skill.ts";
export * from "./skills/domain/spec.ts";

// Governance domain
export * from "./governance/domain/decision.ts";
export * from "./governance/domain/gate.ts";

// Observability domain
export * from "./observability/domain/event.ts";

// Application use cases (governance)
export {
  acceptRisk,
  StoreError,
  type AcceptRiskInput,
  type DecisionStorePort,
} from "./governance/application/accept_risk.ts";
export {
  runReleaseGate,
  type ReleaseAggregate,
  type ReleaseVerdict,
} from "./governance/application/run_release_gate.ts";
export {
  validateManifest,
  type ManifestKind,
  type SkillManifest,
  type PluginManifest,
} from "./governance/application/validate_manifest.ts";
export { InMemoryDecisionStore } from "./governance/application/_fakes.ts";

// Application use cases (skills)
export {
  registerSkill,
  type RegisterSkillInput,
} from "./skills/application/register_skill.ts";
export {
  invokeSkill,
  CapabilityMismatch,
  type InvokeSkillInput,
} from "./skills/application/invoke_skill.ts";
export {
  resolveTrigger,
  NoSkillMatched,
  type TriggerMatch,
} from "./skills/application/resolve_trigger.ts";

// Application use cases (observability)
export { emitEvent } from "./observability/application/emit_event.ts";

// Adapters (concrete implementations)
export { NdjsonTelemetryAdapter } from "./observability/adapters/ndjson_writer.ts";
export { OtelExporterAdapter } from "./observability/adapters/otel_exporter.ts";
export { CompositeTelemetryAdapter } from "./observability/adapters/composite_telemetry.ts";
export { NodeFilesystemAdapter } from "./platform/adapters/node_filesystem.ts";
export { GitAdapter } from "./platform/adapters/git.ts";
export { SigstoreAdapter } from "./platform/adapters/sigstore.ts";
