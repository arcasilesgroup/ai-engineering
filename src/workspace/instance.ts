import { isWorkspaceHealthy, WORKSPACE_OVERVIEW_PATH } from "./server.ts";

const DEFAULT_PORT = 4173;
const STARTUP_TIMEOUT_MS = 5000;

export function workspacePort(): number {
  const configuredPort = process.env.AI_ENG_WORKSPACE_PORT;
  if (configuredPort === undefined) return DEFAULT_PORT;
  if (!/^\d+$/.test(configuredPort)) {
    throw new Error("AI_ENG_WORKSPACE_PORT must be a number between 1 and 65535.");
  }
  const port = Number(configuredPort);
  if (port < 1 || port > 65535) {
    throw new Error("AI_ENG_WORKSPACE_PORT must be a number between 1 and 65535.");
  }
  return port;
}

export async function ensureWorkspaceInstance(): Promise<URL> {
  const port = workspacePort();
  const url = workspaceUrl(port);
  if (await isWorkspaceHealthy(port)) return url;

  const entrypoint = process.argv[1];
  if (!entrypoint) throw new Error("Could not identify the ai-eng entry point to start the workspace hub.");

  // The command exits after opening the browser, so the long-lived service needs its own process.
  const service = Bun.spawn([process.execPath, entrypoint, "workspace", "--serve"], {
    detached: true,
    stdin: "ignore",
    stdout: "ignore",
    stderr: "ignore",
  });

  const deadline = Date.now() + STARTUP_TIMEOUT_MS;
  while (Date.now() < deadline) {
    if (await isWorkspaceHealthy(port)) return url;
    if (service.exitCode !== null) break;
    await Bun.sleep(50);
  }
  throw new Error(
    `Workspace port ${port} is occupied by an unhealthy service or the hub did not start. Stop the process using that port, or choose another with AI_ENG_WORKSPACE_PORT.`,
  );
}

function workspaceUrl(port: number): URL {
  return new URL(WORKSPACE_OVERVIEW_PATH, `http://127.0.0.1:${port}`);
}
