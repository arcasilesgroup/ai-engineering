import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { createHash } from "node:crypto";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, sep } from "node:path";

import { IOError } from "../../../shared/kernel/errors.ts";
import { isErr, isOk } from "../../../shared/kernel/result.ts";
import { NodeFilesystemAdapter } from "../node_filesystem.ts";

let root = "";
let adapter: NodeFilesystemAdapter;

beforeEach(() => {
  root = mkdtempSync(join(tmpdir(), "ai-eng-fs-"));
  adapter = new NodeFilesystemAdapter();
});

afterEach(() => {
  rmSync(root, { recursive: true, force: true });
});

describe("NodeFilesystemAdapter — write + read", () => {
  test("writes a new file and reads it back", async () => {
    const path = join(root, "hello.txt");
    const w = await adapter.write(path, "world");
    expect(isOk(w)).toBe(true);

    const r = await adapter.read(path);
    expect(isOk(r)).toBe(true);
    if (isOk(r)) expect(r.value).toBe("world");
  });

  test("write creates parent directories", async () => {
    const path = join(root, "nested", "deep", "file.txt");
    const w = await adapter.write(path, "ok");
    expect(isOk(w)).toBe(true);

    const r = await adapter.read(path);
    if (isOk(r)) expect(r.value).toBe("ok");
  });

  test("write overwrites existing file", async () => {
    const path = join(root, "x.txt");
    await adapter.write(path, "first");
    await adapter.write(path, "second");
    const r = await adapter.read(path);
    if (isOk(r)) expect(r.value).toBe("second");
  });

  test("read non-existent file returns IOError", async () => {
    const r = await adapter.read(join(root, "missing.txt"));
    expect(isErr(r)).toBe(true);
    if (isErr(r)) {
      expect(r.error).toBeInstanceOf(IOError);
      expect(r.error.adapter).toBe("filesystem");
    }
  });
});

describe("NodeFilesystemAdapter — exists", () => {
  test("returns true for existing file", async () => {
    const path = join(root, "exists.txt");
    writeFileSync(path, "x");
    expect(await adapter.exists(path)).toBe(true);
  });

  test("returns true for existing directory", async () => {
    expect(await adapter.exists(root)).toBe(true);
  });

  test("returns false for missing path", async () => {
    expect(await adapter.exists(join(root, "no-such-thing"))).toBe(false);
  });
});

describe("NodeFilesystemAdapter — list", () => {
  test("lists entries in a directory", async () => {
    writeFileSync(join(root, "a.txt"), "");
    writeFileSync(join(root, "b.txt"), "");
    mkdirSync(join(root, "sub"));

    const r = await adapter.list(root);
    expect(isOk(r)).toBe(true);
    if (isOk(r)) {
      expect(r.value.sort()).toEqual(["a.txt", "b.txt", "sub"]);
    }
  });

  test("returns empty array for empty directory", async () => {
    const r = await adapter.list(root);
    if (isOk(r)) expect(r.value).toHaveLength(0);
  });

  test("listing a missing path returns IOError", async () => {
    const r = await adapter.list(join(root, "nope"));
    expect(isErr(r)).toBe(true);
    if (isErr(r)) expect(r.error).toBeInstanceOf(IOError);
  });

  test("listing a regular file returns IOError", async () => {
    const path = join(root, "file.txt");
    writeFileSync(path, "x");
    const r = await adapter.list(path);
    expect(isErr(r)).toBe(true);
  });
});

describe("NodeFilesystemAdapter — remove", () => {
  test("removes a file", async () => {
    const path = join(root, "del.txt");
    writeFileSync(path, "x");
    const r = await adapter.remove(path);
    expect(isOk(r)).toBe(true);
    expect(await adapter.exists(path)).toBe(false);
  });

  test("removes a directory recursively", async () => {
    const dir = join(root, "tree");
    mkdirSync(dir);
    writeFileSync(join(dir, "a.txt"), "x");
    mkdirSync(join(dir, "sub"));
    writeFileSync(join(dir, "sub", "b.txt"), "y");

    const r = await adapter.remove(dir);
    expect(isOk(r)).toBe(true);
    expect(await adapter.exists(dir)).toBe(false);
  });

  test("removing a missing path returns ok (idempotent)", async () => {
    const r = await adapter.remove(join(root, "ghost"));
    expect(isOk(r)).toBe(true);
  });
});

describe("NodeFilesystemAdapter — hash", () => {
  test("computes sha256 hex of file contents", async () => {
    const path = join(root, "hashme.txt");
    const content = "the quick brown fox";
    writeFileSync(path, content);

    const r = await adapter.hash(path);
    expect(isOk(r)).toBe(true);
    if (isOk(r)) {
      const expected = createHash("sha256").update(content).digest("hex");
      expect(r.value).toBe(expected);
      expect(r.value).toMatch(/^[0-9a-f]{64}$/);
    }
  });

  test("hash is stable across calls", async () => {
    const path = join(root, "stable.txt");
    writeFileSync(path, "stable-content");
    const a = await adapter.hash(path);
    const b = await adapter.hash(path);
    if (isOk(a) && isOk(b)) expect(a.value).toBe(b.value);
  });

  test("hash differs when content differs", async () => {
    const p1 = join(root, "one.txt");
    const p2 = join(root, "two.txt");
    writeFileSync(p1, "alpha");
    writeFileSync(p2, "beta");
    const a = await adapter.hash(p1);
    const b = await adapter.hash(p2);
    if (isOk(a) && isOk(b)) expect(a.value).not.toBe(b.value);
  });

  test("hash of missing file returns IOError", async () => {
    const r = await adapter.hash(join(root, "ghost.txt"));
    expect(isErr(r)).toBe(true);
    if (isErr(r)) expect(r.error).toBeInstanceOf(IOError);
  });

  test("hash of empty file is sha256 of empty string", async () => {
    const path = join(root, "empty.txt");
    writeFileSync(path, "");
    const r = await adapter.hash(path);
    if (isOk(r)) {
      const expected = createHash("sha256").update("").digest("hex");
      expect(r.value).toBe(expected);
    }
  });
});

describe("NodeFilesystemAdapter — cross-platform paths", () => {
  test("write + read works with platform-native separator", async () => {
    const path = ["nested", "via", "sep", "f.txt"].join(sep);
    const full = join(root, path);
    const w = await adapter.write(full, "platform-ok");
    expect(isOk(w)).toBe(true);
    const r = await adapter.read(full);
    if (isOk(r)) expect(r.value).toBe("platform-ok");
  });
});
