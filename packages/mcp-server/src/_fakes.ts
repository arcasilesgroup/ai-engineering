import type { FrameworkEvent, SpanHandle, TelemetryPort } from "@ai-engineering/runtime";

import type { AgentCatalogPort, ManifestPort, SkillCatalogPort } from "./ports.ts";

/**
 * In-memory test fakes for mcp-server integration tests.
 *
 * Real adapters (e.g. filesystem-backed catalog readers) live alongside
 * the CLI / runtime adapters; these fakes exist solely to exercise the
 * HTTP transport + handler dispatch surface without touching disk.
 */
export class FakeSkillCatalogPort implements SkillCatalogPort {
  readonly entries = new Map<string, string>();

  async list(): Promise<ReadonlyArray<{ name: string; uri: string }>> {
    return [...this.entries.keys()].map((name) => ({
      name,
      uri: `ai-engineering://skills/${name}`,
    }));
  }

  async read(name: string): Promise<string | null> {
    return this.entries.get(name) ?? null;
  }
}

export class FakeAgentCatalogPort implements AgentCatalogPort {
  readonly entries = new Map<string, string>();

  async list(): Promise<ReadonlyArray<{ name: string; uri: string }>> {
    return [...this.entries.keys()].map((name) => ({
      name,
      uri: `ai-engineering://agents/${name}`,
    }));
  }

  async read(name: string): Promise<string | null> {
    return this.entries.get(name) ?? null;
  }
}

export class FakeManifestPort implements ManifestPort {
  constructor(private readonly data: Record<string, unknown>) {}

  async load(): Promise<Record<string, unknown>> {
    return this.data;
  }
}

export class FakeTelemetryPort implements TelemetryPort {
  readonly emitted: Array<Omit<FrameworkEvent, "id" | "timestamp">> = [];

  async emit(event: Omit<FrameworkEvent, "id" | "timestamp">): Promise<void> {
    this.emitted.push(event);
  }

  startSpan(name: string, parentSpanId?: string): SpanHandle {
    const traceId = parentSpanId ?? "trace-fake";
    const spanId = `span-${this.emitted.length}`;
    return {
      spanId,
      traceId,
      setAttribute: () => {},
      end: (extra) => {
        void this.emit({
          level: "info",
          type: "span.ended",
          attributes: { name, ...(extra ?? {}) },
        });
      },
    };
  }
}
