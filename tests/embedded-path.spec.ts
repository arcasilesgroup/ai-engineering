// The template reader once round-tripped every embedded ref through a URL, and the
// pathname of a file URL drops the drive letter on Windows — init could not read a
// single template there while macOS and Linux passed (measured in the windows leg of
// the e2e job: ENOENT /~BUN/root/settings.claude.json-*.tpl). This is that bug.
import { test, expect } from "bun:test";
import { embeddedPath } from "../src/embed.ts";

test("an absolute path is returned untouched, whatever the platform writes", () => {
  for (const path of ["/usr/share/ai-eng/x.tpl", "C:/bun/root/x.tpl", "C:\\bun\\root\\x.tpl", "/~BUN/root/x-abc.tpl"]) {
    expect(embeddedPath(path), path).toBe(path);
  }
});

test("a relative ref still resolves against the module, the source tree's case", () => {
  expect(embeddedPath("../templates/AGENTS.md.tpl", "file:///repo/src/embed.ts")).toBe("/repo/templates/AGENTS.md.tpl");
});
