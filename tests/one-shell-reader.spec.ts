// tests/one-shell-reader.spec.ts — the architecture of the guards, enforced.
//
// Every critical hole the ai-engineering audit found was a parsing divergence: three
// guards each read the shell their own way, so policy allowed what self-protect denied.
// The repair is one module owning the grammar and the guards asking predicates over the
// model it produces. This file is what keeps it that way: a second reader is a failing
// test, not a discovery three releases later.
import { describe, expect, test } from "bun:test";
import { readFileSync, readdirSync } from "node:fs";
import { join, relative } from "node:path";
import { readCommands } from "../src/guards/shell.ts";

const SRC = join(import.meta.dir, "..", "src");

/** The one module allowed to know how the shell reads a line. */
const READER = "guards/shell.ts";

function sourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return entry.name.endsWith(".ts") ? [path] : [];
  });
}

const FILES = sourceFiles(SRC).map((path) => ({ path, rel: relative(SRC, path), text: readFileSync(path, "utf8") }));

/** A declaration that is a second reader. Each entry is one of the duplications the audit
 *  found three of; the name says which question the copy was answering. */
const SECOND_READER: Array<{ what: string; pattern: RegExp }> = [
  { what: "a redirection grammar", pattern: /^\s*(?:export\s+)?const\s+\w*(?:REDIRECT|REDIRECTION)\w*\s*=\s*\//m },
  { what: "a command-separator grammar", pattern: /^\s*(?:export\s+)?const\s+\w*(?:SEPARATORS?|SHELL_SEGMENT|SEGMENT_SPLIT)\w*\s*=\s*\//m },
  { what: "a reader table", pattern: /^\s*(?:export\s+)?const\s+\w*READERS\w*\s*=\s*new Set/m },
  { what: "a command-prefix table", pattern: /^\s*(?:export\s+)?const\s+\w*(?:COMMAND_PREFIXES|EXEC_WRAPPERS)\w*\s*=\s*new Set/m },
];

/** Names the guards still own on purpose, mapped to the question they answer. None of them
 *  is the shell's grammar: `GIT_READERS` asks which git subcommand reads, `BINARY_BYTE_READERS`
 *  asks which tool emits raw bytes. */
const OWN_QUESTION: Record<string, string> = {
  GIT_READERS: "which git subcommand only reads",
  BINARY_BYTE_READERS: "which tool emits raw file bytes",
};

describe("one shell reader", () => {
  test("no module outside the reader declares a redirection, a separator, a reader or a prefix table", () => {
    const copies: string[] = [];
    for (const file of FILES) {
      if (file.rel === READER) continue;
      for (const { what, pattern } of SECOND_READER) {
        const found = pattern.exec(file.text)?.[0]?.trim();
        if (found === undefined) continue;
        const name = /\bconst\s+(\w+)/.exec(found)?.[1] ?? found;
        if (name in OWN_QUESTION) continue;
        copies.push(`src/${file.rel}: ${what} (${name}) — ${OWN_QUESTION[name] ?? "ask it of src/guards/shell.ts instead"}`);
      }
    }
    expect(copies).toEqual([]);
  });

  test("the model answers every word question the guards used to answer with their own regex", () => {
    // A redirect is an operator and the file it names, read once, in the reader.
    const [echo] = readCommands("echo x > out 2>&1 >> log")!;
    expect(echo!.redirects.map(({ operator, target }) => [operator, target?.value ?? null])).toEqual([
      [">", "out"],
      [">", "/dev/fd/1"],
      [">", "log"],
    ]);
    expect(echo!.plain.map((word) => word.value)).toEqual(["echo", "x"]);
    // The verb stands past `NAME=value` and the wrappers that run the next word.
    expect(readCommands("sudo -u root FOO=1 git push")![0]!.verb).toBe("git");
    expect(readCommands("nice -n 5 rm -rf /etc/x")![0]!.verb).toBe("rm");
    // A word keeps the spelling it was written with, which is what a path token is judged on.
    expect(readCommands("rm .\\rm x")![0]!.plain.map((word) => word.original)).toEqual(["rm", ".\\rm", "x"]);
  });

  test("an unreadable line is null, so a caller must deny rather than guess", () => {
    expect(readCommands("echo 'unclosed")).toBeNull();
    expect(readCommands("echo ${x:-> f}")).toBeNull();
    expect(readCommands("echo ok")).not.toBeNull();
  });
});
