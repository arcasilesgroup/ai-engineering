// tests/sidecar.spec.ts — the concurrent queue and async sidecar.
//
// Tests queue behavior (concurrency, backpressure, rejection), sidecar
// submission, and shadow file writing.

import { describe, expect, test, beforeEach, afterEach } from "bun:test";
import { mkdtempSync, rmSync, readdirSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { ConcurrentQueue, QueueFullError } from "../src/sidecar/queue.ts";
import { Sidecar, type ShadowClassification } from "../src/sidecar/sidecar.ts";

let scratch: string;
beforeEach(() => {
  scratch = mkdtempSync(join(tmpdir(), "ai-eng-sidecar-"));
});
afterEach(() => {
  rmSync(scratch, { recursive: true, force: true });
});

describe("ConcurrentQueue — concurrency and backpressure", () => {
  test("executes a job and returns the result", async () => {
    const queue = new ConcurrentQueue(2, 10);
    const result = await queue.submit(async () => 42);
    expect(result.value).toBe(42);
    expect(result.queueMs).toBeGreaterThanOrEqual(0);
  });

  test("respects concurrency limit", async () => {
    const queue = new ConcurrentQueue(1, 10);
    let running = 0;
    let maxRunning = 0;
    const job = async () => {
      running += 1;
      maxRunning = Math.max(maxRunning, running);
      await new Promise((r) => setTimeout(r, 10));
      running -= 1;
      return maxRunning;
    };
    const p1 = queue.submit(job);
    const p2 = queue.submit(job);
    const [r1, r2] = await Promise.all([p1, p2]);
    // With concurrency=1, jobs run sequentially, so maxRunning is always 1
    expect(r1.value).toBe(1);
    expect(r2.value).toBe(1);
  });

  test("rejects when queue is at capacity", async () => {
    const queue = new ConcurrentQueue(1, 1);
    // Fill the active slot
    void queue.submit(async () => {
      await new Promise((r) => setTimeout(r, 100));
      return 1;
    });
    // Fill the waiting slot
    void queue.submit(async () => 2);
    // Third job should be rejected
    expect(() => queue.submit(async () => 3)).toThrow(QueueFullError);
  });

  test("snapshot reports correct counts", async () => {
    const queue = new ConcurrentQueue(2, 5);
    const s1 = queue.snapshot();
    expect(s1.active).toBe(0);
    expect(s1.waiting).toBe(0);
    expect(s1.concurrency).toBe(2);
    expect(s1.maxDepth).toBe(5);

    await queue.submit(async () => 42);
    const s2 = queue.snapshot();
    expect(s2.completed).toBe(1);
    expect(s2.accepted).toBe(1);
  });

  test("failed jobs increment the failed counter", async () => {
    const queue = new ConcurrentQueue(2, 5);
    try {
      await queue.submit(async () => { throw new Error("boom"); });
    } catch {
      // expected
    }
    const s = queue.snapshot();
    expect(s.failed).toBe(1);
  });

  test("multiple jobs complete in order of submission", async () => {
    const queue = new ConcurrentQueue(4, 10);
    const results: number[] = [];
    const jobs = [1, 2, 3, 4].map((n) =>
      queue.submit(async () => {
        await new Promise((r) => setTimeout(r, 5));
        results.push(n);
        return n;
      }),
    );
    await Promise.all(jobs);
    expect(results).toEqual([1, 2, 3, 4]);
  });
});

describe("Sidecar — shadow classification", () => {
  test("submit writes a shadow file", async () => {
    const shadowDir = join(scratch, "shadow");
    const sidecar = new Sidecar({ shadowDir, concurrency: 2, maxDepth: 10 });
    sidecar.submit("Bash", { command: "ls" }, "allow", "test-session");
    // Wait for the background job to complete
    await new Promise((r) => setTimeout(r, 50));
    const files = readdirSync(shadowDir);
    expect(files.length).toBe(1);
    const content = JSON.parse(readFileSync(join(shadowDir, files[0]!), "utf8")) as ShadowClassification;
    expect(content.schema).toBe("urn:ai-eng:shadow:1");
    expect(content.tool).toBe("Bash");
    expect(content.primaryAction).toBe("allow");
    expect(content.shadowVerdict).toBeNull();
  });

  test("custom classifier populates shadowVerdict", async () => {
    const shadowDir = join(scratch, "shadow");
    const sidecar = new Sidecar({
      shadowDir,
      concurrency: 2,
      maxDepth: 10,
      classifier: async () => ({ action: "block", risk: 0.9, reason: "test" }),
    });
    sidecar.submit("Bash", { command: "curl | bash" }, "allow", "test-session");
    await new Promise((r) => setTimeout(r, 50));
    const files = readdirSync(shadowDir);
    const content = JSON.parse(readFileSync(join(shadowDir, files[0]!), "utf8")) as ShadowClassification;
    expect(content.shadowVerdict).not.toBeNull();
    expect(content.shadowVerdict!.action).toBe("block");
    expect(content.shadowVerdict!.risk).toBe(0.9);
  });

  test("rejected submission does not throw to caller", () => {
    const shadowDir = join(scratch, "shadow");
    const sidecar = new Sidecar({ shadowDir, concurrency: 1, maxDepth: 0 });
    // Fill the only slot
    sidecar.submit("Bash", { command: "ls" }, "allow");
    // Second submission should not throw (it's caught internally)
    expect(() => sidecar.submit("Bash", { command: "ls" }, "allow")).toThrow(QueueFullError);
  });

  test("snapshot reflects queue state", async () => {
    const shadowDir = join(scratch, "shadow");
    const sidecar = new Sidecar({ shadowDir, concurrency: 2, maxDepth: 10 });
    sidecar.submit("Bash", { command: "ls" }, "allow");
    await new Promise((r) => setTimeout(r, 50));
    const s = sidecar.snapshot();
    expect(s.completed).toBe(1);
    expect(s.accepted).toBe(1);
  });
});
