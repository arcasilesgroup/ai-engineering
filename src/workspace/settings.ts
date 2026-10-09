import { existsSync, mkdirSync, readFileSync, realpathSync, renameSync, statSync, unlinkSync, writeFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { isAbsolute, join } from "node:path";
import { home } from "../env.ts";

function settingsPath(): string {
  return join(home(), "workspace.json");
}

export function readWorkspaceRoots(): string[] {
  return validateRoots(readStoredRoots(settingsPath()) ?? []);
}

function readStoredRoots(path: string): string[] | undefined {
  if (!existsSync(path)) return undefined;
  const parsed: unknown = JSON.parse(readFileSync(path, "utf8"));
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("Workspace settings must be an object containing only a roots array.");
  }
  const settings = parsed as Record<string, unknown>;
  if (Object.keys(settings).length !== 1
    || !Array.isArray(settings.roots)
    || settings.roots.some((root) => typeof root !== "string")) {
    throw new Error("Workspace settings must be an object containing only a roots array.");
  }
  return settings.roots as string[];
}

export function writeWorkspaceRoots(roots: string[]): void {
  const path = settingsPath();
  readStoredRoots(path);
  const validatedRoots = validateRoots(roots);
  const serialized = `${JSON.stringify({ roots: validatedRoots }, null, 2)}\n`;
  const directory = home();
  mkdirSync(directory, { recursive: true });
  const temporaryPath = join(directory, `.workspace-${randomUUID()}.tmp`);
  try {
    writeFileSync(temporaryPath, serialized, { flag: "wx" });
    renameSync(temporaryPath, path);
  } catch (error) {
    try {
      unlinkSync(temporaryPath);
    } catch {}
    throw error;
  }
}

function validateRoots(roots: unknown[]): string[] {
  const seen = new Set<string>();
  for (const root of roots) {
    if (typeof root !== "string" || !isAbsolute(root) || root.split(/[\\/]/).includes("..")) {
      throw new Error("Each workspace root must be a canonical absolute directory path.");
    }
    let canonicalRoot: string;
    try {
      canonicalRoot = realpathSync(root);
    } catch {
      throw new Error(`Workspace root does not exist or cannot be read: ${root}`);
    }
    if (canonicalRoot !== root || !isDirectory(root)) {
      throw new Error(`Workspace root must be a canonical absolute directory: ${root}`);
    }
    if (seen.has(root)) throw new Error(`Workspace root is duplicated: ${root}`);
    seen.add(root);
  }
  return roots as string[];
}

function isDirectory(path: string): boolean {
  try {
    return statSync(path).isDirectory();
  } catch {
    return false;
  }
}
