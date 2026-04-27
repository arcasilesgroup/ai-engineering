import { type Result, IOError, err, ok } from "../../shared/kernel/index.ts";
import type { FilesystemPort } from "../../shared/ports/filesystem.ts";
import type {
  LLMCapability,
  LLMError,
  LLMPort,
  LLMRequest,
  LLMResponse,
} from "../../shared/ports/llm.ts";
import type {
  FrameworkEvent,
  SpanHandle,
  TelemetryPort,
} from "../../shared/ports/telemetry.ts";

/**
 * In-memory fakes for skills/application tests.
 *
 * Real adapters live in `skills/adapters/`; these fakes exist solely to
 * exercise the application layer without touching the filesystem or
 * a real LLM bridge.
 */
export class FakeFilesystemPort implements FilesystemPort {
  readonly files = new Map<string, string>();

  async read(path: string): Promise<Result<string, IOError>> {
    const content = this.files.get(path);
    if (content === undefined) {
      return err(new IOError(`No such file: ${path}`));
    }
    return ok(content);
  }

  async write(path: string, content: string): Promise<Result<void, IOError>> {
    this.files.set(path, content);
    return ok(undefined);
  }

  async exists(path: string): Promise<boolean> {
    return this.files.has(path);
  }

  async list(_path: string): Promise<Result<string[], IOError>> {
    return ok([...this.files.keys()]);
  }

  async remove(path: string): Promise<Result<void, IOError>> {
    this.files.delete(path);
    return ok(undefined);
  }

  async hash(path: string): Promise<Result<string, IOError>> {
    const content = this.files.get(path);
    if (content === undefined) {
      return err(new IOError(`No such file: ${path}`));
    }
    // Deterministic non-cryptographic digest — sufficient for tests.
    let h = 0;
    for (let i = 0; i < content.length; i += 1) {
      h = (h * 31 + content.charCodeAt(i)) | 0;
    }
    return ok(`fake:${(h >>> 0).toString(16)}`);
  }
}

export class FakeLLMPort implements LLMPort {
  readonly invocations: LLMRequest[] = [];
  supportedCapabilities: ReadonlySet<LLMCapability>;

  constructor(supported: ReadonlyArray<LLMCapability> = ["tool_use"]) {
    this.supportedCapabilities = new Set(supported);
  }

  async invoke(request: LLMRequest): Promise<Result<LLMResponse, LLMError>> {
    this.invocations.push(request);
    return ok({
      text: "fake-response",
      tokensUsed: 0,
      costUsd: 0,
      providerId: "fake",
      modelId: "fake-model",
      latencyMs: 0,
    });
  }

  async supports(capabilities: ReadonlyArray<LLMCapability>): Promise<boolean> {
    return capabilities.every((c) => this.supportedCapabilities.has(c));
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
    const handle: SpanHandle = {
      spanId,
      traceId,
      setAttribute: () => {},
      end: (extra) => {
        void this.emit({
          level: "info",
          type: "span.ended",
          traceId,
          spanId,
          ...(parentSpanId !== undefined ? { parentSpanId } : {}),
          attributes: { name, ...(extra ?? {}) },
        });
      },
    };
    return handle;
  }
}
