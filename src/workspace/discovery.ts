import { lstatSync, readdirSync, realpathSync } from "node:fs";
import type { Dirent } from "node:fs";
import { isAbsolute, join, relative, sep } from "node:path";
import { classifyRepository, type WorkspaceFilter, type WorkspaceProject, type WorkspaceStatus } from "./status.ts";
import { repositoryWorktreeInventory } from "../shared-worktree.ts";

export interface WorkspaceDiscoveryResult {
  projects: WorkspaceProject[];
  errors: Array<{ root: string; detail: string }>;
}

export interface WorkspaceDiscoveryOptions {
  filter?: WorkspaceFilter;
  now?: Date;
}

function isWithin(root: string, path: string): boolean {
  const pathFromRoot = relative(root, path);
  return pathFromRoot === "" || (
    pathFromRoot !== ".." &&
    !pathFromRoot.startsWith(`..${sep}`) &&
    !isAbsolute(pathFromRoot)
  );
}

function canonicalRoot(root: string): { path: string } | { detail: string } {
  if (!isAbsolute(root) || root.split(/[\\/]/).includes("..")) {
    return { detail: "workspace root must be a canonical absolute directory" };
  }
  try {
    const stat = lstatSync(root);
    const resolved = realpathSync(root);
    if (stat.isSymbolicLink() || !stat.isDirectory() || resolved !== root) {
      return { detail: "workspace root must be a canonical absolute directory" };
    }
    return { path: resolved };
  } catch (error) {
    return { detail: `workspace root is unreadable: ${error instanceof Error ? error.message : String(error)}` };
  }
}

function gitMarker(path: string): "repository" | "marker" | null {
  try {
    const stat = lstatSync(join(path, ".git"));
    return stat.isDirectory() || stat.isFile() ? "repository" : "marker";
  } catch {
    return null;
  }
}

function findRepositories(
  scanRoot: string,
  directory: string,
  repositories: Set<string>,
  errors: Array<{ root: string; detail: string }>,
): void {
  const marker = gitMarker(directory);
  if (marker !== null) {
    if (marker === "repository") repositories.add(directory);
    return;
  }

  let entries: Dirent[];
  try {
    entries = readdirSync(directory, { withFileTypes: true });
  } catch (error) {
    const location = relative(scanRoot, directory) || ".";
    errors.push({
      root: scanRoot,
      detail: `cannot scan ${location}: ${error instanceof Error ? error.message : String(error)}`,
    });
    return;
  }
  entries.sort((left, right) => left.name.localeCompare(right.name));

  for (const entry of entries) {
    if (entry.isSymbolicLink() || !entry.isDirectory()) continue;
    const childPath = join(directory, entry.name);
    try {
      const canonicalChild = realpathSync(childPath);
      if (isWithin(scanRoot, canonicalChild)) {
        findRepositories(scanRoot, canonicalChild, repositories, errors);
      }
    } catch (error) {
      errors.push({
        root: scanRoot,
        detail: `cannot scan ${relative(scanRoot, childPath)}: ${error instanceof Error ? error.message : String(error)}`,
      });
    }
  }
}

function scanRoot(root: string): { repositories: string[]; errors: Array<{ root: string; detail: string }> } {
  const errors: Array<{ root: string; detail: string }> = [];
  const canonical = canonicalRoot(root);
  if ("detail" in canonical) return { repositories: [], errors: [{ root, detail: canonical.detail }] };
  const repositories = new Set<string>();
  findRepositories(canonical.path, canonical.path, repositories, errors);
  return { repositories: [...repositories].sort(), errors };
}

function filterProject(project: WorkspaceProject, filter: WorkspaceFilter): WorkspaceProject {
  if (filter === "all") return project;
  return {
    ...project,
    items: project.items.filter((item) => item.status === filter),
    history: filter === "closed" ? project.history : [],
  };
}

export function discoverWorkspace(
  roots: string[],
  options: WorkspaceDiscoveryOptions = {},
): WorkspaceDiscoveryResult {
  const filter = options.filter ?? "all";
  const projectsByRoot = new Map<string, WorkspaceProject>();
  const errors: Array<{ root: string; detail: string }> = [];

  for (const configuredRoot of roots) {
    const scan = scanRoot(configuredRoot);
    errors.push(...scan.errors);
    for (const repositoryRoot of scan.repositories) {
      const inventory = repositoryWorktreeInventory(repositoryRoot);
      if ("detail" in inventory) {
        projectsByRoot.set(repositoryRoot, {
          root: repositoryRoot,
          items: [],
          history: [],
          errors: [`${repositoryRoot}: ${inventory.detail}`],
        });
        continue;
      }
      const classification = classifyRepository(inventory);
      projectsByRoot.set(repositoryRoot, { root: repositoryRoot, ...classification });
    }
  }

  return {
    projects: [...projectsByRoot.values()]
      .map((project) => filterProject(project, filter))
      .sort((left, right) => left.root.localeCompare(right.root)),
    errors,
  };
}

export type { WorkspaceFilter, WorkspaceStatus };
