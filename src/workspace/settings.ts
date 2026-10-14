import { existsSync, mkdirSync, readFileSync, renameSync, unlinkSync, writeFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { join } from "node:path";
import { home } from "../env.ts";
import { validateWorkspaceRoot } from "./folder-picker.ts";

function settingsPath(): string {
  return join(home(), "workspace.json");
}

export function readWorkspaceRoots(): string[] {
  return readStoredRoots(settingsPath()) ?? [];
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

export function addWorkspaceRoot(root: string | null): void {
  if (root === null) return;
  const roots = readWorkspaceRoots();
  writeWorkspaceRoots([...roots, root]);
}

export function removeWorkspaceRoot(root: string): void {
  writeWorkspaceRoots(readWorkspaceRoots().filter((entry) => entry !== root));
}

function validateRoots(roots: unknown[]): string[] {
  const seen = new Set<string>();
  const canonicalRoots: string[] = [];
  for (const root of roots) {
    if (typeof root !== "string") {
      throw new Error("Each workspace root must be a canonical absolute directory path.");
    }
    const canonicalRoot = validateWorkspaceRoot(root);
    if (seen.has(canonicalRoot)) throw new Error(`Workspace root is duplicated: ${root}`);
    seen.add(canonicalRoot);
    canonicalRoots.push(canonicalRoot);
  }
  return canonicalRoots;
}
