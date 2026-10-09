import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, realpathSync, rmSync, writeFileSync } from "node:fs";
import { join, sep } from "node:path";
import { pathToFileURL } from "node:url";

interface WorkspaceSettingsApi {
  readWorkspaceRoots(): string[] | Promise<string[]>;
  writeWorkspaceRoots(roots: string[]): void | Promise<void>;
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

function projectRoot(): string {
  const path = join(sandbox, "projects", "alpha");
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

  test("does not overwrite malformed settings bytes", async () => {
    const settingsPath = join(settingsHome, "workspace.json");
    const malformedBytes = Buffer.from('{"roots": [\n');
    writeFileSync(settingsPath, malformedBytes);

    const api = settings();
    await expectRejected(() => api.readWorkspaceRoots());
    await expectRejected(() => api.writeWorkspaceRoots([projectRoot()]));

    expect(readFileSync(settingsPath)).toEqual(malformedBytes);
  });
});
