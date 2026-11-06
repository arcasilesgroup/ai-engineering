// The template reader resolves an embedded ref to a path directly, never through a
// URL: the pathname of a file URL drops the drive letter on Windows, so init cannot
// read a template there while macOS and Linux pass (windows leg of the e2e job:
// ENOENT /~BUN/root/settings.claude.json-*.tpl).
import { test, expect } from "bun:test";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { embeddedPath } from "../src/embed.ts";

test("an absolute path is returned untouched, whatever the platform writes", () => {
  for (const path of ["/usr/share/ai-eng/x.tpl", "C:/bun/root/x.tpl", "C:\\bun\\root\\x.tpl", "/~BUN/root/x-abc.tpl"]) {
    expect(embeddedPath(path), path).toBe(path);
  }
});

test("a relative ref still resolves against the module, the source tree's case", () => {
  // resolve() gives the platform's absolute spelling: a drive letter on Windows.
  const moduleUrl = pathToFileURL(resolve("/repo/src/embed.ts")).href;
  expect(embeddedPath("../templates/AGENTS.md.tpl", moduleUrl)).toBe(resolve("/repo/templates/AGENTS.md.tpl"));
});
