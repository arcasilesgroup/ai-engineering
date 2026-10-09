import { embeddedTemplate } from "../embed.ts";
import { discoverConfiguredWorkspace, handleWorkspaceApi, type WorkspaceFolderPicker } from "./api.ts";
import { readWorkspaceRoots } from "./settings.ts";

export const WORKSPACE_OVERVIEW_PATH = "/.ai-engineering/workflow/checkpoints/overview.html";
const HEALTH_PATH = "/health";
const HEALTH_BODY = { service: "ai-eng-workspace", status: "ok" };
const activeServers = new Map<number, WorkspaceServer>();

export interface WorkspaceServer {
  hostname: string;
  port: number;
  url: URL;
  stop(force?: boolean): void;
}

export async function isWorkspaceHealthy(port: number): Promise<boolean> {
  try {
    const response = await fetch(`http://127.0.0.1:${port}${HEALTH_PATH}`, {
      signal: AbortSignal.timeout(500),
    });
    if (response.status !== 200) return false;
    const body: unknown = await response.json();
    return body !== null
      && typeof body === "object"
      && !Array.isArray(body)
      && (body as Record<string, unknown>).service === "ai-eng-workspace"
      && (body as Record<string, unknown>).status === "ok";
  } catch {
    return false;
  }
}

export async function startWorkspaceServer(options: {
  port: number;
  folderPicker?: WorkspaceFolderPicker;
}): Promise<WorkspaceServer> {
  const { port, folderPicker } = options;
  if (!Number.isInteger(port) || port < 0 || port > 65535) {
    throw new Error("Workspace port must be an integer between 0 and 65535.");
  }

  readWorkspaceRoots();
  if (port > 0) {
    const current = activeServers.get(port);
    if (current && await isWorkspaceHealthy(port)) return current;
    if (await isWorkspaceHealthy(port)) return externalServer(port);
  }

  let workspaceSnapshot = await discoverConfiguredWorkspace();
  let server: ReturnType<typeof Bun.serve>;
  try {
    server = Bun.serve({
      hostname: "127.0.0.1",
      port,
      fetch: async (request) => {
        const pathname = new URL(request.url).pathname;
        if (request.method === "GET" && pathname === HEALTH_PATH) {
          return Response.json(HEALTH_BODY, { headers: { "cache-control": "no-store" } });
        }
        let apiResponse: Response | null;
        try {
          apiResponse = await handleWorkspaceApi(
            request,
            () => workspaceSnapshot,
            async () => {
              workspaceSnapshot = await discoverConfiguredWorkspace();
              return workspaceSnapshot;
            },
            folderPicker,
          );
        } catch (error) {
          apiResponse = Response.json({
            error: error instanceof Error ? error.message : String(error),
          }, {
            status: 500,
            headers: { "cache-control": "no-store" },
          });
        }
        if (apiResponse !== null) return apiResponse;
        if (request.method === "GET" && pathname === WORKSPACE_OVERVIEW_PATH) {
          return new Response(embeddedTemplate("workspace.html.tpl"), {
            headers: {
              "content-type": "text/html; charset=utf-8",
              "cache-control": "no-store",
            },
          });
        }
        return new Response("Not found\n", { status: 404 });
      },
    });
  } catch {
    if (port > 0 && await isWorkspaceHealthy(port)) {
      return activeServers.get(port) ?? externalServer(port);
    }
    throw new Error(
      `Workspace port ${port} is occupied or unavailable. Stop the process using that port, or choose another with AI_ENG_WORKSPACE_PORT.`,
    );
  }

  const serverPort = server.port;
  if (serverPort === undefined) {
    await server.stop(true);
    throw new Error("Workspace server did not report a bound port.");
  }

  const instance: WorkspaceServer = {
    hostname: "127.0.0.1",
    port: serverPort,
    url: new URL(`http://127.0.0.1:${serverPort}`),
    stop(force) {
      void server.stop(force);
      activeServers.delete(serverPort);
    },
  };
  activeServers.set(instance.port, instance);
  return instance;
}

function externalServer(port: number): WorkspaceServer {
  return {
    hostname: "127.0.0.1",
    port,
    url: new URL(`http://127.0.0.1:${port}`),
    stop() {},
  };
}
