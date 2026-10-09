import { afterEach, describe, expect, test } from "bun:test";

interface WorkspaceServer {
  hostname: string;
  port: number;
  url: URL;
  stop(force?: boolean): void;
}

const activeServers = new Set<Pick<Bun.Server<undefined>, "stop"> | WorkspaceServer>();
const serverModulePath = new URL("../src/workspace/server.ts", import.meta.url).href;

afterEach(async () => {
  for (const server of activeServers) await server.stop(true);
  activeServers.clear();
});

async function startWorkspaceServer(port = 0): Promise<WorkspaceServer> {
  const serverModule = (await import(serverModulePath)) as {
    startWorkspaceServer?: (options: { port: number }) => Promise<WorkspaceServer> | WorkspaceServer;
  };
  if (typeof serverModule.startWorkspaceServer !== "function") {
    throw new Error("Expected src/workspace/server.ts to export startWorkspaceServer");
  }

  const server = await serverModule.startWorkspaceServer({ port });
  activeServers.add(server);
  return server;
}

describe("workspace server", () => {
  test("binds only to 127.0.0.1", async () => {
    const server = await startWorkspaceServer();

    expect(server.hostname).toBe("127.0.0.1");
  });

  test("answers the health route", async () => {
    const server = await startWorkspaceServer();
    const response = await fetch(new URL("/health", server.url));

    expect(response.status).toBe(200);
  });

  test("reuses a healthy instance on a second start", async () => {
    const first = await startWorkspaceServer();
    const second = await startWorkspaceServer(first.port);

    expect(second).toBe(first);
  });

  test("reports an actionable error for an occupied unhealthy port without starting another server", async () => {
    const occupiedServer = Bun.serve({
      hostname: "127.0.0.1",
      port: 0,
      fetch: () => new Response("unrelated service", { status: 503 }),
    });
    activeServers.add(occupiedServer);

    let competingServer: WorkspaceServer | undefined;
    let startupError: unknown;
    try {
      competingServer = await startWorkspaceServer(occupiedServer.port);
    } catch (error) {
      startupError = error;
    }
    if (competingServer) activeServers.add(competingServer);

    expect(competingServer).toBeUndefined();
    expect(startupError).toBeInstanceOf(Error);
    expect((startupError as Error).message).toMatch(/occupied|already in use/i);
    expect((startupError as Error).message).toMatch(/stop|close|free|another port|restart/i);
    expect(await (await fetch(occupiedServer.url)).text()).toBe("unrelated service");
  });
});
