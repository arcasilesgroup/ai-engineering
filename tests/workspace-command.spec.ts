import { afterAll, describe, expect, test } from "bun:test";
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { createServer, type Server } from "node:http";
import { join } from "node:path";

const CLI = join(import.meta.dir, "..", "src", "cli.ts");
const sandbox = mkdtempSync(join(import.meta.dir, ".workspace-command-"));
const browserShimDirectory = join(sandbox, "bin");
mkdirSync(browserShimDirectory);
for (const browserCommand of ["open", "xdg-open"]) {
  const shim = join(browserShimDirectory, browserCommand);
  writeFileSync(shim, '#!/bin/sh\nprintf "%s\\n" "$*" >> "$WORKSPACE_OPEN_LOG"\n');
  chmodSync(shim, 0o755);
}

afterAll(() => rmSync(sandbox, { recursive: true, force: true }));

interface Run {
  status: number;
  stdout: string;
  stderr: string;
}

async function runWorkspace(args: string[], port?: number, openLog = join(sandbox, "opened-urls.log")): Promise<Run> {
  const home = join(sandbox, `home-${Date.now()}-${Math.random()}`);
  mkdirSync(home);
  const child = Bun.spawn([process.execPath, CLI, "workspace", ...args], {
    cwd: "/",
    env: {
      ...process.env,
      AI_ENG_HOME: home,
      ...(port === undefined ? {} : { AI_ENG_WORKSPACE_PORT: String(port) }),
      PATH: `${browserShimDirectory}:${process.env.PATH ?? ""}`,
      WORKSPACE_OPEN_LOG: openLog,
    },
    stdout: "pipe",
    stderr: "pipe",
  });
  const timeout = setTimeout(() => child.kill(), 5000);
  try {
    const [status, stdout, stderr] = await Promise.all([
      child.exited,
      new Response(child.stdout).text(),
      new Response(child.stderr).text(),
    ]);
    return { status, stdout, stderr };
  } finally {
    clearTimeout(timeout);
  }
}

async function startOccupiedPort(status: number): Promise<{ server: Server; port: number; requests: number }> {
  let requests = 0;
  const server = createServer((_request, response) => {
    requests += 1;
    response.writeHead(status, { "content-type": "application/json" });
    response.end(JSON.stringify({ ok: status === 200, status: "ok" }));
  });
  await new Promise<void>((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => resolve());
  });
  const address = server.address();
  if (address === null || typeof address === "string") throw new Error("test server did not bind a TCP port");
  return { server, port: address.port, get requests() { return requests; } };
}

async function closeServer(server: Server): Promise<void> {
  await new Promise<void>((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
}

describe("ai-eng workspace CLI", () => {
  test("opens the same healthy loopback hub on repeated invocations", async () => {
    const occupied = await startOccupiedPort(200);
    const openLog = join(sandbox, "healthy-open.log");
    try {
      const first = await runWorkspace([], occupied.port, openLog);
      const second = await runWorkspace([], occupied.port, openLog);
      expect(first.status).toBe(0);
      expect(second.status).toBe(0);
      expect(occupied.requests).toBeGreaterThan(0);
      expect(existsSync(openLog)).toBe(true);
      const openedUrls = readFileSync(openLog, "utf8");
      expect(openedUrls).toContain(`127.0.0.1:${occupied.port}`);
      expect(openedUrls.trim().split("\n")).toHaveLength(2);
    } finally {
      await closeServer(occupied.server);
    }
  });

  test("rejects invalid arguments with workspace-specific usage", async () => {
    const result = await runWorkspace(["unexpected"]);
    const output = `${result.stdout}\n${result.stderr}`;

    expect(result.status).not.toBe(0);
    expect(output).toMatch(/workspace/i);
    expect(output).toMatch(/usage|invalid|expected/i);
  });

  test("reports recovery guidance when the configured loopback port is unhealthy", async () => {
    const occupied = await startOccupiedPort(503);
    const openLog = join(sandbox, "unhealthy-open.log");
    try {
      const result = await runWorkspace([], occupied.port, openLog);
      const output = `${result.stdout}\n${result.stderr}`;

      expect(result.status).not.toBe(0);
      expect(output).toMatch(/port/i);
      expect(output).toMatch(/stop|close|free|restart|another/i);
      expect(occupied.requests).toBeGreaterThan(0);
      expect(occupied.server.listening).toBe(true);
      expect(existsSync(openLog)).toBe(false);
    } finally {
      await closeServer(occupied.server);
    }
  });
});
