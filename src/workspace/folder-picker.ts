import { existsSync, realpathSync, statSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, isAbsolute, parse } from "node:path";

export type WorkspaceFolderSelection =
  | { status: "selected"; path: string }
  | { status: "cancelled" }
  | { status: "unsupported"; reason: string };

type NativePicker = { executable: string; args: string[] };

function nativePicker(): NativePicker | null {
  if (process.platform === "darwin") {
    return {
      executable: "/usr/bin/osascript",
      args: ["-e", 'POSIX path of (choose folder with prompt "Choose a workspace folder")'],
    };
  }
  if (process.platform === "linux") {
    for (const executable of ["/usr/bin/zenity", "/usr/bin/kdialog"]) {
      if (existsSync(executable)) {
        return {
          executable,
          args: executable.endsWith("/zenity")
            ? ["--file-selection", "--directory", "--title=Choose a workspace folder"]
            : ["--getexistingdirectory", ".", "--title", "Choose a workspace folder"],
        };
      }
    }
  }
  return null;
}

export function validateWorkspaceRoot(root: string): string {
  if (!isAbsolute(root) || root.split(/[\\/]/).includes("..")) {
    if (!root.startsWith("~/") && !root.startsWith("~\\")) {
      throw new Error("Each workspace root must be a canonical absolute directory path.");
    }
    if (root.replace(/\\/g, "/").split("/").includes("..")) {
      throw new Error("Parent-directory segments are not allowed in a workspace root.");
    }
  }
  const candidatePath = root.startsWith("~/") || root.startsWith("~\\")
    ? `${homedir()}/${root.slice(2)}`
    : root;
  const pathRoot = parse(candidatePath).root;
  const candidate = candidatePath.length > pathRoot.length
    ? candidatePath.replace(/[\\/]+$/, "")
    : pathRoot;
  let canonicalRoot: string;
  try {
    canonicalRoot = realpathSync(candidate);
  } catch {
    throw new Error(`Workspace root does not exist or cannot be read: ${candidate}`);
  }
  if (canonicalRoot !== candidate || dirname(candidate) === candidate || !statSync(candidate).isDirectory()) {
    throw new Error(`Workspace root must be a canonical absolute directory: ${candidate}`);
  }
  return canonicalRoot;
}

export async function pickWorkspaceFolder(): Promise<WorkspaceFolderSelection> {
  const picker = nativePicker();
  if (picker === null) {
    return { status: "unsupported", reason: "Native folder selection is unavailable on this system." };
  }

  try {
    const child = Bun.spawn([picker.executable, ...picker.args], {
      stdin: "ignore",
      stdout: "pipe",
      stderr: "pipe",
    });
    const [output, errorOutput, exitCode] = await Promise.all([
      new Response(child.stdout).text(),
      new Response(child.stderr).text(),
      child.exited,
    ]);
    if (exitCode !== 0) {
      if (exitCode === 1) return { status: "cancelled" };
      return {
        status: "unsupported",
        reason: errorOutput.trim() || "The native folder chooser could not be opened.",
      };
    }
    const selectedPath = output.trim();
    if (!selectedPath) {
      return { status: "unsupported", reason: "The native folder chooser returned no folder path." };
    }
    return { status: "selected", path: validateWorkspaceRoot(selectedPath) };
  } catch (error) {
    return {
      status: "unsupported",
      reason: error instanceof Error ? error.message : String(error),
    };
  }
}
