// tests/self-protect.spec.ts — the fence around the four things that govern the
// session: the chain's own files, the git floor, the approved spec, and the machine-side
// canon and carriers. A survivor here is an edit nobody denied, so these tests assert
// the exact denial text, the exact allow around every deny, and the derived literal
// list itself — not that "the function was called".

import { afterAll, afterEach, beforeAll, describe, expect, test } from "bun:test";
import { existsSync, mkdirSync, mkdtempSync, realpathSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { protectedPaths, writesTo, runSelfProtect } from "../src/guards/self-protect.ts";

const roots: string[] = [];
const HOME_BEFORE = process.env.AI_ENG_HOME;
const CWD_BEFORE = process.cwd();

beforeAll(() => {
  process.env.AI_ENG_HOME = mkdtempSync(join(tmpdir(), "ai-eng-selfprotect-home-"));
});
afterAll(() => {
  if (HOME_BEFORE === undefined) delete process.env.AI_ENG_HOME;
  else process.env.AI_ENG_HOME = HOME_BEFORE;
});
afterEach(() => {
  process.chdir(CWD_BEFORE);
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

function tempDir(prefix: string): string {
  const dir = mkdtempSync(join(tmpdir(), prefix));
  roots.push(dir);
  return dir;
}

function tempRepo(): string {
  const dir = tempDir("ai-eng-selfprotect-repo-");
  mkdirSync(join(dir, ".ai-engineering"), { recursive: true });
  writeFileSync(join(dir, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n');
  return dir;
}

function write(root: string, name: string, content: string): string {
  const path = join(root, name);
  mkdirSync(join(path, ".."), { recursive: true });
  writeFileSync(path, content);
  return path;
}

function pin(repo: string, sha: string): void {
  write(repo, join(".ai-engineering", "ai-eng.lock"), `spec_sha256 = "${sha}"\n`);
}

const FILE_REASON = (target: string) =>
  `${target} is part of what governs this session — it is how the rules reach you and how what happens here is recorded. Changing it from inside the session it governs is not a change a session gets to make. A person edits it, in a diff, in a pull request.`;
const CMD_REASON = (found: string) =>
  `this command writes to ${found}, which is part of what governs this session. A person changes that, in a reviewed diff — not the session it governs.`;

describe("protectedPaths — the list is derived from the wiring, never copied", () => {
  test("repo-less call: the machine-side paths only", () => {
    const paths = protectedPaths(null);
    const base = process.env.AI_ENG_HOME!;
    expect(paths.literals).toContain(join(base, "skills"));
    expect(paths.literals).toContain(join(base, ".claude", "skills"));
    expect(paths.literals).toContain(join(base, ".agents", "skills"));
    expect(paths.literals).toContain(join(base, ".config", "opencode", "skill"));
    for (const carrier of [".claude/settings.json", ".config/opencode/plugins", ".codex/hooks.json", ".omp/agent/hooks", ".pi/agent/extensions", ".copilot/hooks", "machine.json"]) {
      expect(paths.literals).toContain(join(base, carrier));
    }
    expect(paths.specPinned).toBe(false);
    expect(paths.terminal).toEqual([]);
  });

  test("no literal is ever the empty string — an empty literal matches every command", () => {
    expect(protectedPaths(null).literals.every((p) => p.length > 0)).toBe(true);
    expect(protectedPaths(tempRepo()).literals.every((p) => p.length > 0)).toBe(true);
  });

  test("the repo adds the four files the chain reads, the git hooks, and nothing else by default", () => {
    const repo = tempRepo();
    const paths = protectedPaths(repo);
    for (const name of ["config.toml", "overrides.toml", "ai-eng.lock", "arch.rules.json"]) {
      expect(paths.literals).toContain(join(repo, ".ai-engineering", name));
    }
    expect(paths.literals).toContain(join(repo, ".git", "hooks"));
    expect(paths.terminal).toEqual([".ai-engineering", join(repo, ".ai-engineering")]);
    expect(paths.specPinned).toBe(false);
  });

  test("surface wiring is a literal only where install actually wrote it", () => {
    const repo = tempRepo();
    const before = protectedPaths(repo);
    const claude = write(repo, ".claude/settings.json", "{}\n");
    const opencode = write(repo, ".opencode/plugins/ai-eng.ts", "export {}\n");
    const agents = write(repo, ".agents/hooks/ai-eng.ts", "export {}\n");
    const after = protectedPaths(repo);
    expect(after.literals).toContain(claude);
    expect(after.literals).toContain(opencode);
    expect(after.literals).toContain(agents);
    for (const ghost of [".claude/settings.json", ".opencode/plugins/ai-eng.ts", ".agents/hooks/ai-eng.ts"]) {
      expect(before.literals).not.toContain(join(repo, ghost));
    }
  });

  test("the pin criterion: a 64-hex sha256 in the lock pins spec.html; anything else does not", () => {
    const hex64 = "a".repeat(64);
    const pinned = tempRepo();
    pin(pinned, hex64);
    expect(protectedPaths(pinned).specPinned).toBe(true);
    expect(protectedPaths(pinned).literals).toContain(join(pinned, ".ai-engineering", "spec.html"));

    for (const [name, sha] of [["no-lock", null], ["short-sha", "abc"], ["numeric-sha", 12345] ] as const) {
      const repo = tempRepo();
      if (sha !== null) write(repo, join(".ai-engineering", "ai-eng.lock"), `spec_sha256 = ${typeof sha === "string" ? `"${sha}"` : sha}\n`);
      const paths = protectedPaths(repo);
      expect(paths.specPinned, name).toBe(false);
      expect(paths.literals, name).not.toContain(join(repo, ".ai-engineering", "spec.html"));
    }

    // A repo that never pinned must not protect spec.html: the session writes its own
    // draft contract. (Kills `specPinned = true` on both the init and the catch path.)
    const unpinned = tempRepo();
    const draft = join(unpinned, ".ai-engineering", "spec.html");
    writeFileSync(draft, "<html></html>\n");
    expect(runSelfProtect({ tool_name: "Write", tool_input: { file_path: draft } }, unpinned)).toBeUndefined();
  });

  test("an install with no surface files leaves no ghost literal behind", () => {
    // The surfaces list is derived from what install wrote; a mutation that seeds the
    // collector with a phantom path must show up here as a literal that protects nothing.
    const repo = tempRepo();
    const paths = protectedPaths(repo);
    for (const literal of paths.literals) {
      expect(
        literal.startsWith(process.env.AI_ENG_HOME!) || literal.startsWith(repo),
        literal,
      ).toBe(true);
      expect(literal).not.toContain("Stryker was here");
    }
    const repoless = protectedPaths(null);
    for (const literal of repoless.literals) {
      expect(literal.startsWith(process.env.AI_ENG_HOME!), literal).toBe(true);
      expect(literal).not.toContain("Stryker was here");
    }
  });

  test("a lock whose spec_sha256 is not a string does not pin spec.html", () => {
    // TOML arrays are objects with a length; only a string sha pins. (Also kills the
    // `typeof` guard removal: an array of 64 elements has length >= 64.)
    const repo = tempRepo();
    write(repo, join(".ai-engineering", "ai-eng.lock"), `spec_sha256 = [${Array.from({ length: 64 }, (_, i) => i).join(",")}]\n`);
    const paths = protectedPaths(repo);
    expect(paths.specPinned).toBe(false);
    expect(paths.literals).not.toContain(join(repo, ".ai-engineering", "spec.html"));
  });
});

describe("writesTo — one shell command, judged", () => {
  const paths: ProtectedPaths = {
    literals: ["/x/ai-eng.lock"],
    specPinned: false,
    terminal: [".ai-engineering"],
  };

  test("the writer verbs: a protected argument is denied, every one of them", () => {
    const verbs = ["rm", "mv", "cp", "install", "truncate", "dd", "tee", "chmod", "chown", "ln", "python", "python3", "perl", "ruby", "node", "sh", "bash", "zsh", "bun"];
    for (const verb of verbs) {
      expect(writesTo(paths, `${verb} /x/ai-eng.lock`), verb).toBe("/x/ai-eng.lock");
    }
  });

  test("a non-writer is not judged by the verb arm; a quoted verb still is", () => {
    expect(writesTo(paths, "cat /x/ai-eng.lock")).toBeNull();
    expect(writesTo(paths, '"rm" /x/ai-eng.lock')).toBe("/x/ai-eng.lock");
  });

  test("sed joins only with -i", () => {
    expect(writesTo(paths, "sed -i s/a/b/ /x/ai-eng.lock")).toBe("/x/ai-eng.lock");
    expect(writesTo(paths, "sed -n 1p /x/ai-eng.lock")).toBeNull();
  });

  test("a pipe target is judged as the downstream writer's argument; an argument that merely contains rm is not", () => {
    expect(writesTo(paths, "echo x | tee /x/ai-eng.lock")).toBe("/x/ai-eng.lock");
    expect(writesTo(paths, "echo a rm /x/ai-eng.lock")).toBeNull();
  });

  test("a redirect is judged by where it points", () => {
    expect(writesTo(paths, "echo x > /x/ai-eng.lock")).toBe("/x/ai-eng.lock");
    expect(writesTo(paths, "echo x >> .ai-engineering")).toBe(".ai-engineering");
    expect(writesTo(paths, 'echo x > "/x/ai-eng.lock"')).toBe("/x/ai-eng.lock");
    expect(writesTo(paths, "echo x > /x/somewhere-else")).toBeNull();
    expect(writesTo(paths, 'echo x > /x/"ai-eng.lock"')).toBeNull(); // a mid-quote belongs to the name: not the lock
    expect(writesTo(paths, 'echo x > ".ai-engineering"')).toBe(".ai-engineering"); // quotes are stripped before the judge
    expect(writesTo(paths, "echo a > /tmp/ok.txt > /x/ai-eng.lock")).toBe("/x/ai-eng.lock"); // every redirect is judged
    expect(writesTo(paths, "echo > /x/ai-eng.lock | b")).toBe("/x/ai-eng.lock"); // a redirect before a dead pipe is still judged
  });


  test("blank and whitespace-only commands judge to nothing", () => {
    expect(writesTo(paths, "")).toBeNull();
    expect(writesTo(paths, "   ")).toBeNull();
  });

  test("only sed itself earns the -i clause: another verb with -i is still a non-writer", () => {
    expect(writesTo(paths, "cat -i /x/ai-eng.lock")).toBeNull();
    expect(writesTo(paths, "grep -i needle /x/ai-eng.lock")).toBeNull();
  });

  test("a bare literal (a basename with no directory) matches as a whole segment only", () => {
    const bare: ProtectedPaths = { literals: ["ai-eng.lock"], specPinned: false, terminal: [] };
    expect(writesTo(bare, "rm x/ai-eng.lock")).toBe("ai-eng.lock");
    expect(writesTo(bare, "rm ai-eng.lock")).toBeNull(); // a bare word alone is not a path naming the file
    expect(writesTo(bare, "rm xai-eng.locky")).toBeNull(); // never a substring
    expect(writesTo(bare, "rm x/ai-eng.lock.bak")).toBeNull(); // the segment must be exactly the name
  });
});

describe("runSelfProtect — file targets", () => {
  test("each of the four chain files is denied, with the exact reason", () => {
    for (const name of ["config.toml", "overrides.toml", "ai-eng.lock", "arch.rules.json"]) {
      const repo = tempRepo();
      const target = join(repo, ".ai-engineering", name);
      expect(runSelfProtect({ tool_name: "Write", tool_input: { file_path: target } }, repo)).toEqual({
        deny: true,
        reason: FILE_REASON(target),
      });
    }
  });

  test("a session artifact inside .ai-engineering is allowed; the directory itself is not", () => {
    const repo = tempRepo();
    const artifact = join(repo, ".ai-engineering", "research", "001-x.html");
    write(repo, "research/001-x.html", "<html></html>\n");
    expect(runSelfProtect({ tool_name: "Write", tool_input: { file_path: artifact } }, repo)).toBeUndefined();
    // The command's relative-ish spelling still carries the relative terminal name the
    // judge reports; the canonical repo prefix is rewritten, the last segment is kept.
    expect(runSelfProtect({ tool_name: "Bash", tool_input: { command: `rm -rf ${join(repo, ".ai-engineering")}` } }, repo)).toEqual({
      deny: true,
      reason: CMD_REASON(".ai-engineering"),
    });
  });

  test("a path that spells the pinned spec is denied in every spelling", () => {
    const repo = tempRepo();
    pin(repo, "a".repeat(64));
    const spec = join(repo, ".ai-engineering", "spec.html");
    expect(runSelfProtect({ tool_name: "Edit", tool_input: { file_path: spec } }, repo)?.deny).toBe(true);
    expect(runSelfProtect({ tool_name: "Bash", tool_input: { command: `rm ${spec}` } }, repo)?.deny).toBe(true);
  });

  test("the machine-side paths are protected on a repo-less call", () => {
    const base = process.env.AI_ENG_HOME!;
    for (const target of [join(base, "skills", "x.md"), join(base, "machine.json")]) {
      expect(runSelfProtect({ tool_name: "Write", tool_input: { file_path: target } }, null)?.deny).toBe(true);
    }
  });

  test("tilde spellings of the machine side are denied", () => {
    expect(runSelfProtect({ tool_name: "Write", tool_input: { file_path: "~" } }, null)?.deny).toBe(true);
    expect(runSelfProtect({ tool_name: "Write", tool_input: { file_path: "~/skills/x.md" } }, null)?.deny).toBe(true);
    expect(runSelfProtect({ tool_name: "Edit", tool_input: { path: "~/skills/x.md" } }, null)?.deny).toBe(true);
    expect(runSelfProtect({ tool_name: "Write", tool_input: { file_path: "~" } }, null)!.reason).toBe(
      FILE_REASON("~"),
    );
  });

  test("the relative path resolves against the repo root, not the process cwd", () => {
    const repo = tempRepo();
    process.chdir(tempDir("ai-eng-selfprotect-cwd-"));
    expect(runSelfProtect({ tool_name: "Write", tool_input: { file_path: ".ai-engineering/config.toml" } }, repo)?.deny).toBe(true);
    expect(runSelfProtect({ tool_name: "Bash", tool_input: { command: "rm .ai-engineering/config.toml" } }, repo)?.deny).toBe(true);
  });

  test("the macOS /var alias: the canonical form of a /var path is judged, not the alias", () => {
    const repo = tempRepo();
    // realpathSync the repo so the guard's own canon and ours agree, then hand the
    // command the /var spelling the agent would use.
    const real = realpathSync(repo);
    if (real === repo) return; // tmpdir not behind /var here (Linux CI) — nothing to alias
    const alias = repo.replace(/^\/private/, "");
    expect(alias).toMatch(/^\/var\//);
    expect(runSelfProtect({ tool_name: "Bash", tool_input: { command: `rm -rf ${alias}/.ai-engineering` } }, real)?.deny).toBe(true);
    expect(runSelfProtect({ tool_name: "Write", tool_input: { file_path: `${alias}/.ai-engineering/config.toml` } }, real)?.deny).toBe(true);
  });

  test("a file_path that is not a string, or names nothing governed, is not a denial and not a crash", () => {
    const repo = tempRepo();
    expect(runSelfProtect({ tool_name: "Write", tool_input: { file_path: 123 } }, repo)).toBeUndefined();
    expect(runSelfProtect({ tool_name: "Write", tool_input: { file_path: [join(repo, ".ai-engineering", "config.toml")] } }, repo)).toBeUndefined();
    expect(runSelfProtect({ tool_name: "Write", tool_input: { file_path: join(repo, "src", "main.ts") } }, repo)).toBeUndefined();
  });

  test("a file_path into a governed-but-not-yet-existing prefix is still denied (longest-existing-prefix canon)", () => {
    const repo = tempRepo();
    pin(repo, "b".repeat(64));
    const ghost = join(repo, ".ai-engineering", "spec.html");
    expect(existsSync(ghost)).toBe(false);
    expect(runSelfProtect({ tool_name: "Write", tool_input: { file_path: ghost } }, repo)?.deny).toBe(true);
  });

  test("an empty tool_input judges nothing, even with the process cwd sitting on the protected home", () => {
    // No file_path, no path, no command: the guard has no target to judge. A cwd that
    // IS a protected path must not invent one — resolve("", cwd) hits the home literal
    // only if the branch is entered.
    process.chdir(process.env.AI_ENG_HOME!);
    try {
      expect(runSelfProtect({ tool_name: "Write", tool_input: {} }, null)).toBeUndefined();
    } finally {
      process.chdir(CWD_BEFORE);
    }
  });

  test("a governed file spelled through a symlinked repo root is judged, not lost to the canon", () => {
    // The longest-existing-prefix canon resolves the symlink; the raw spelling the agent
    // used must still be one of the judged candidates — a nonexistent lock file spelled
    // through the link is denied by it.
    const real = mkdtempSync(join(tmpdir(), "ai-eng-selfprotect-real-"));
    roots.push(real);
    mkdirSync(join(real, ".ai-engineering"));
    const link = join(real, "via-link");
    symlinkSync(real, link);
    const ghost = join(link, ".ai-engineering", "overrides.toml");
    expect(existsSync(ghost)).toBe(false); // judged before it exists, through the link
    expect(runSelfProtect({ tool_name: "Write", tool_input: { file_path: ghost } }, link)?.deny).toBe(true);
  });
});

describe("runSelfProtect — shell commands", () => {
  test("writing a chain file by command is denied, with the exact reason", () => {
    const repo = tempRepo();
    const lock = join(repo, ".ai-engineering", "ai-eng.lock");
    expect(runSelfProtect({ tool_name: "Bash", tool_input: { command: `rm ${lock}` } }, repo)).toEqual({
      deny: true,
      reason: CMD_REASON(lock),
    });
  });

  test("the git floor: the hooks directory is protected, the bare .git is not", () => {
    const repo = tempRepo();
    const hooks = join(repo, ".git", "hooks");
    expect(runSelfProtect({ tool_name: "Bash", tool_input: { command: `rm -rf ${hooks}` } }, repo)?.deny).toBe(true);
    expect(runSelfProtect({ tool_name: "Bash", tool_input: { command: `rm -rf ${join(repo, ".git")}` } }, repo)).toBeUndefined();
  });

  test("a machine carrier by bare name is protected only under machineBase", () => {
    const base = process.env.AI_ENG_HOME!;
    expect(runSelfProtect({ tool_name: "Bash", tool_input: { command: `rm ${join(base, "machine.json")}` } }, null)?.deny).toBe(true);
    expect(runSelfProtect({ tool_name: "Bash", tool_input: { command: "rm /tmp/machine.json" } }, null)).toBeUndefined();
  });

  test("redirects and pipes into governed paths are denied", () => {
    const repo = tempRepo();
    const config = join(repo, ".ai-engineering", "config.toml");
    expect(runSelfProtect({ tool_name: "Bash", tool_input: { command: `echo x > ${config}` } }, repo)?.deny).toBe(true);
    expect(runSelfProtect({ tool_name: "Bash", tool_input: { command: `echo x >> ${config}` } }, repo)?.deny).toBe(true);
    expect(runSelfProtect({ tool_name: "Bash", tool_input: { command: `echo x | tee ${config}` } }, repo)?.deny).toBe(true);
    expect(runSelfProtect({ tool_name: "Bash", tool_input: { command: `sed -i s/a/b/ ${config}` } }, repo)?.deny).toBe(true);
  });

  test("separators are judged per command; a heredoc is one command", () => {
    const repo = tempRepo();
    const lock = join(repo, ".ai-engineering", "ai-eng.lock");
    const safe = `echo hello`;
    expect(runSelfProtect({ tool_name: "Bash", tool_input: { command: `${safe}; rm ${lock}` } }, repo)?.deny).toBe(true);
    expect(runSelfProtect({ tool_name: "Bash", tool_input: { command: `cat <<EOF\n${safe}\nEOF` } }, repo)).toBeUndefined();
  });

  test("tilde commands expand to the machine base", () => {
    expect(runSelfProtect({ tool_name: "Bash", tool_input: { command: "rm ~/skills/x.md" } }, null)?.deny).toBe(true);
    expect(runSelfProtect({ tool_name: "Bash", tool_input: { command: "echo x > ~/machine.json" } }, null)?.deny).toBe(true);
  });

  test("a path spelled with .. still resolves to the file it names", () => {
    const repo = tempRepo();
    const cmd = `rm ${repo}/nowhere/../.ai-engineering/ai-eng.lock`;
    expect(cmd).toContain(".."); // the spelling itself, not one join() normalized away
    expect(runSelfProtect({ tool_name: "Bash", tool_input: { command: cmd } }, repo)?.deny).toBe(true);
  });

  test("a governed file reached through an in-repo symlink directory is denied", () => {
    const repo = mkdtempSync(join(tmpdir(), "ai-eng-selfprotect-link-"));
    roots.push(repo);
    mkdirSync(join(repo, ".ai-engineering"));
    writeFileSync(join(repo, ".ai-engineering", "config.toml"), 'surfaces = ["claude"]\n');
    symlinkSync(join(repo, ".ai-engineering"), join(repo, "linkdir"));
    const viaLink = `${realpathSync(repo)}/linkdir/config.toml`;
    expect(runSelfProtect({ tool_name: "Bash", tool_input: { command: `rm ${viaLink}` } }, repo)?.deny).toBe(true);
  });

  test("the heredoc body is the writer's argument; a bare verb line after it is not", () => {
    const repo = tempRepo();
    const lock = join(repo, ".ai-engineering", "ai-eng.lock");
    // The heredoc tail is judged as one command; "rm" alone on its own line names nothing.
    expect(runSelfProtect({ tool_name: "Bash", tool_input: { command: `cat <<EOF\nhello\nEOF\nrm\n${lock}` } }, repo)).toBeUndefined();
    // A heredoc started on a writer line carries the paths of the lines below it.
    expect(runSelfProtect({ tool_name: "Bash", tool_input: { command: `echo x\nrm <<F\n${lock}` } }, repo)?.deny).toBe(true);
    // The joined heredoc tail is judged with the pieces separated, so a path split across
    // lines does not become a protected name.
    const stem = lock.slice(0, -".lock".length);
    expect(runSelfProtect({ tool_name: "Bash", tool_input: { command: `rm <<F\n${stem}\n.lock` } }, repo)).toBeUndefined();
  });
});
