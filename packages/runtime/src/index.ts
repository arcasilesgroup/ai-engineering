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

// Adapters (concrete implementations)
export { NdjsonTelemetryAdapter } from "./observability/adapters/ndjson_writer.ts";
