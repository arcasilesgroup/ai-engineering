import { spawnSync } from "node:child_process";
import { ensureWorkspaceInstance, workspacePort } from "../workspace/instance.ts";
import { startWorkspaceServer } from "../workspace/server.ts";
import { readWorkspaceRoots } from "../workspace/settings.ts";

const USAGE = "usage: ai-eng workspace\n";

export async function workspaceMain(args: string[], isServer = false): Promise<number> {
  if (isServer) {
    if (args.length !== 1 || args[0] !== "--serve") {
      process.stderr.write(USAGE);
      return 2;
    }
    try {
      await startWorkspaceServer({ port: workspacePort() });
      await new Promise<void>(() => {});
      return 0;
    } catch (error) {
      process.stderr.write(`ai-eng workspace: ${errorMessage(error)}\n`);
      return 2;
    }
  }

  if (args.length !== 0) {
    process.stderr.write(USAGE);
    return 2;
  }

  try {
    readWorkspaceRoots();
    const url = await ensureWorkspaceInstance();
    openDefaultBrowser(url.toString());
    process.stdout.write(`Workspace ready: ${url}\n`);
    return 0;
  } catch (error) {
    process.stderr.write(`ai-eng workspace: ${errorMessage(error)}\n`);
    return 2;
  }
}

function openDefaultBrowser(url: string): void {
  const isWindows = process.platform === "win32";
  const command = process.platform === "darwin" ? "open" : isWindows ? "cmd" : "xdg-open";
  const args = isWindows ? ["/c", "start", "", url] : [url];
  const result = spawnSync(command, args, { stdio: "ignore" });
  if (result.error || result.status !== 0) {
    throw new Error(`Could not open the browser. Open ${url} manually.`);
  }
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
