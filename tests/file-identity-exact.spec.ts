// "Is this still the same file?" is answered by device, file id and times. On NTFS a file id
// is 64 bits and passes 2^53, where a JS number drops its low bits: a file swapped in a moment
// later could carry the judged file's id. So every snapshot that a later write or unlink is
// bound to holds the id as an exact bigint and the times in nanoseconds.

import { afterEach, expect, test } from "bun:test";
import { mkdtempSync, realpathSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { readProjectFileSnapshot } from "../src/shared-project-fs.ts";
import { readableMachineSettings } from "../src/surfaces/machine-state.ts";

const roots: string[] = [];
afterEach(() => {
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

function fileInNewFolder(): { root: string; path: string } {
  const root = realpathSync(mkdtempSync(join(tmpdir(), "ai-eng-exact-id-")));
  roots.push(root);
  const path = join(root, "settings.json");
  writeFileSync(path, "{}\n");
  return { root, path };
}

test("a project file snapshot keeps its id exact and its times in nanoseconds", () => {
  const { root, path } = fileInNewFolder();
  const snapshot = readProjectFileSnapshot(root, path);
  expect(snapshot).not.toBeNull();
  expect(typeof snapshot!.dev).toBe("bigint");
  expect(typeof snapshot!.ino).toBe("bigint");
  expect(typeof snapshot!.mtimeNs).toBe("bigint");
  expect(typeof snapshot!.ctimeNs).toBe("bigint");
  expect(snapshot!.size).toBe(3);
  expect(snapshot!.nlink).toBe(1);
});

test("a machine settings snapshot keeps the file's id and its folder's id exact", () => {
  const { path } = fileInNewFolder();
  const snapshot = readableMachineSettings(path);
  expect(snapshot?.file).not.toBeNull();
  expect(typeof snapshot!.file!.stat.ino).toBe("bigint");
  expect(typeof snapshot!.file!.stat.mtimeNs).toBe("bigint");
  expect(typeof snapshot!.sourceParent.ino).toBe("bigint");
});
