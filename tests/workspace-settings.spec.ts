import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, realpathSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { join, sep } from "node:path";
import { pathToFileURL } from "node:url";

interface WorkspaceSettingsApi {
  readWorkspaceRoots(): string[] | Promise<string[]>;
  writeWorkspaceRoots(roots: string[]): void | Promise<void>;
  addWorkspaceRoot?: (root: string | null) => void | Promise<void>;
  removeWorkspaceRoot?: (root: string) => void | Promise<void>;
}

const SETTINGS_MODULE = join(import.meta.dir, "..", "src", "workspace", "settings.ts");
let settingsApi: WorkspaceSettingsApi | undefined;
let settingsImportError: unknown;
if (existsSync(SETTINGS_MODULE)) {
  try {
    settingsApi = (await import(pathToFileURL(SETTINGS_MODULE).href)) as WorkspaceSettingsApi;
  } catch (error) {
    settingsImportError = error;
  }
}

let sandbox = "";
let settingsHome = "";
let savedCwd = "";
const savedHome = process.env.AI_ENG_HOME;

beforeEach(() => {
  sandbox = mkdtempSync(join(import.meta.dir, ".workspace-settings-"));
  settingsHome = join(sandbox, "home");
  mkdirSync(settingsHome);
  process.env.AI_ENG_HOME = settingsHome;
  savedCwd = process.cwd();
  process.chdir("/");
});

afterEach(() => {
  process.chdir(savedCwd);
  if (savedHome === undefined) delete process.env.AI_ENG_HOME;
  else process.env.AI_ENG_HOME = savedHome;
  rmSync(sandbox, { recursive: true, force: true });
});

function settings(): WorkspaceSettingsApi {
  expect(existsSync(SETTINGS_MODULE), "workspace settings behavior is not implemented yet").toBe(true);
  if (settingsImportError !== undefined) throw settingsImportError;
  expect(settingsApi, "workspace settings exports are required").toBeDefined();
  return settingsApi!;
}

function rootSettings(): Required<Pick<WorkspaceSettingsApi, "addWorkspaceRoot" | "removeWorkspaceRoot">> & WorkspaceSettingsApi {
  const api = settings();
  expect(typeof api.addWorkspaceRoot, "addWorkspaceRoot export is required").toBe("function");
  expect(typeof api.removeWorkspaceRoot, "removeWorkspaceRoot export is required").toBe("function");
  return api as Required<Pick<WorkspaceSettingsApi, "addWorkspaceRoot" | "removeWorkspaceRoot">> & WorkspaceSettingsApi;
}

function projectRoot(name = "alpha"): string {
  const path = join(sandbox, "projects", name);
  mkdirSync(path, { recursive: true });
  return realpathSync(path);
}

async function expectRejected(action: () => unknown): Promise<void> {
  let isRejected = false;
  try {
    await action();
  } catch {
    isRejected = true;
  }
  expect(isRejected).toBe(true);
}

describe("workspace project-root settings", () => {
  test("persists canonical absolute roots under AI_ENG_HOME", async () => {
    const root = projectRoot();
    await settings().writeWorkspaceRoots([root]);

    expect(await settings().readWorkspaceRoots()).toEqual([root]);
    expect(existsSync(join(settingsHome, "workspace.json"))).toBe(true);
  });

  test("accepts native folder selections with a trailing separator and stores the canonical root", async () => {
    const root = projectRoot();
    await settings().writeWorkspaceRoots([`${root}${sep}`]);

    expect(await settings().readWorkspaceRoots()).toEqual([root]);
  });

  test("rejects duplicate roots and paths containing traversal", async () => {
    const root = projectRoot();
    const api = settings();
    await api.writeWorkspaceRoots([root]);
    const settingsPath = join(settingsHome, "workspace.json");
    const validBytes = readFileSync(settingsPath);

    await expectRejected(() => api.writeWorkspaceRoots([root, root]));
    expect(readFileSync(settingsPath)).toEqual(validBytes);

    const traversal = [sandbox, "projects", "missing", "..", "alpha"].join(sep);
    await expectRejected(() => api.writeWorkspaceRoots([traversal]));
    expect(readFileSync(settingsPath)).toEqual(validBytes);

    await expectRejected(() => api.writeWorkspaceRoots(["projects/alpha"]));
    expect(readFileSync(settingsPath)).toEqual(validBytes);
  });

  test("does not change saved roots when folder selection is cancelled", async () => {
    const root = projectRoot();
    await settings().writeWorkspaceRoots([root]);
    const settingsPath = join(settingsHome, "workspace.json");
    const savedBytes = readFileSync(settingsPath);
    const api = rootSettings();

    await api.addWorkspaceRoot(null);

    expect(await api.readWorkspaceRoots()).toEqual([root]);
    expect(readFileSync(settingsPath)).toEqual(savedBytes);
  });

  test("adds and removes roots through the settings API", async () => {
    const firstRoot = projectRoot("alpha");
    const secondRoot = projectRoot("beta");
    const api = rootSettings();

    await api.addWorkspaceRoot(firstRoot);
    await api.addWorkspaceRoot(secondRoot);
    expect(await api.readWorkspaceRoots()).toEqual([firstRoot, secondRoot]);

    await api.removeWorkspaceRoot(firstRoot);
    expect(await api.readWorkspaceRoots()).toEqual([secondRoot]);
  });

  test("add-root validation preserves canonical, duplicate, and traversal safeguards", async () => {
    const root = projectRoot();
    await settings().writeWorkspaceRoots([root]);
    const api = rootSettings();
    const settingsPath = join(settingsHome, "workspace.json");
    const savedBytes = readFileSync(settingsPath);
    const alias = join(sandbox, "projects", "alpha-alias");
    symlinkSync(root, alias);
    const traversal = [sandbox, "projects", "missing", "..", "alpha"].join(sep);

    await expectRejected(() => api.addWorkspaceRoot(root));
    expect(readFileSync(settingsPath)).toEqual(savedBytes);
    await expectRejected(() => api.addWorkspaceRoot(alias));
    expect(readFileSync(settingsPath)).toEqual(savedBytes);
    await expectRejected(() => api.addWorkspaceRoot(traversal));
    expect(readFileSync(settingsPath)).toEqual(savedBytes);
  });

  test("replaces a stale configured root without validating the removed path", async () => {
    const staleRoot = projectRoot();
    const api = settings();
    await api.writeWorkspaceRoots([staleRoot]);
    rmSync(staleRoot, { recursive: true, force: true });

    await api.writeWorkspaceRoots([]);

    expect(await api.readWorkspaceRoots()).toEqual([]);
  });

  test("does not overwrite malformed settings bytes", async () => {
    const settingsPath = join(settingsHome, "workspace.json");
    const malformedBytes = Buffer.from('{"roots": [\n');
    writeFileSync(settingsPath, malformedBytes);

    const api = settings();
    await expectRejected(() => api.readWorkspaceRoots());
    await expectRejected(() => api.writeWorkspaceRoots([projectRoot()]));

    expect(readFileSync(settingsPath)).toEqual(malformedBytes);
  });

  test("preserves settings bytes when serialization fails", async () => {
    const api = settings();
    await api.writeWorkspaceRoots([projectRoot()]);
    const settingsPath = join(settingsHome, "workspace.json");
    const originalBytes = readFileSync(settingsPath);
    const originalStringify = JSON.stringify;
    JSON.stringify = () => {
      throw new Error("serialization failed");
    };

    try {
      await expectRejected(() => api.writeWorkspaceRoots([]));
    } finally {
      JSON.stringify = originalStringify;
    }
    expect(readFileSync(settingsPath)).toEqual(originalBytes);

    chmodSync(settingsHome, 0o555);
    try {
      await expectRejected(() => api.writeWorkspaceRoots([]));
    } finally {
      chmodSync(settingsHome, 0o755);
    }

    expect(readFileSync(settingsPath)).toEqual(originalBytes);
  });
});
