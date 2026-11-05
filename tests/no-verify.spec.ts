// Kills the survivors of src/guards/no-verify.ts: every branch of the
// hooksPath parser (exact arrays), the elsewhere resolution against a real
// fixture root, both deny reasons verbatim, and the runNoVerify routing and
// crash guards.
//
// The silencer literals are assembled by concatenation and the test labels
// avoid contiguous silencer bytes: this file is itself judged by the guard it
// tests when it is written.
import { describe, expect, test, beforeAll, afterAll } from "bun:test";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  checkBash,
  checkContent,
  hooksPathElsewhere,
  hooksPathTargets,
  runNoVerify,
} from "../src/guards/no-verify.ts";
import type { Payload } from "../src/payload.ts";

const hookReason = (target: string) => `this points core.hooksPath at ${target || "nothing"} instead`;
const skipReason = (label: string) => `${label} skips the git hooks`;
const silenceReason = "this silences a check";

const LINE_DISABLE = "// eslint-" + "disable";
const BLOCK_DISABLE = "/* eslint-" + "disable */";
const TS_IGNORE = "@ts-ig" + "nore";
const TS_EXPECT = "@ts-expect-" + "error";
const TS_NOCHECK = "@ts-no" + "check";
const NOQA = "# no" + "qa";
const NOSEC = "# no" + "sec";
const NOLINT = "NOLINT" + "NEXTLINE";
const ALLOW_LIST = '"$allow-' + 'list": {';

const payload = (tool_name: string, tool_input: Record<string, unknown>): Payload => ({
  tool_name,
  tool_input,
});

// Fixture root for the floor/no-floor arms: FX is the repo's own .git/hooks (the only
// accepted hooksPath); EMPTY and LOOKALIKE exist but are not it.
const FX = join(".git", "hooks");
const EMPTY = "noverify-empty-dir";
const LOOKALIKE = "noverify-lookalike-hooks";
let root = "";
beforeAll(() => {
  root = mkdtempSync(join(tmpdir(), "noverify-"));
  mkdirSync(join(root, FX), { recursive: true });
  mkdirSync(join(root, EMPTY));
  mkdirSync(join(root, LOOKALIKE));
  writeFileSync(join(root, LOOKALIKE, "pre-commit"), "#!/bin/sh\n# ai-eng git floor shim\nexit 0\n");
});
afterAll(() => rmSync(root, { recursive: true, force: true }));

describe("hooksPathTargets", () => {
  test.each([
    ["inline -c, quoted value", "git -c core.hooksPath='/tmp/evil' commit", ["/tmp/evil"]],
    ["inline -c, bare value", "git -c core.hooksPath=/tmp/evil commit", ["/tmp/evil"]],
    ["multiple inner spaces", "git  config  core.hooksPath  /tmp/evil", ["/tmp/evil"]],
    ["uppercase key", "git config CORE.HOOKSPATH /tmp/evil", ["/tmp/evil"]],
    ["main attack", "git config core.hooksPath /tmp/evil", ["/tmp/evil"]],
    ["-C before the subcommand", "git -C sub config core.hooksPath /tmp/evil", ["/tmp/evil"]],
    ["inline -c, interior quote survives", "git -c core.hooksPath=/tmp/ev'il commit", ["/tmp/ev'il"]],
    ["unset", "git config --unset core.hooksPath", [""]],
    ["--unset only as a suffix", "git config x--unset core.hooksPath /tmp/evil", ["/tmp/evil"]],
    ["single-quoted value", "git config core.hooksPath '/tmp/evil'", ["/tmp/evil"]],
    ["double-quoted value", 'git config core.hooksPath "/tmp/evil"', ["/tmp/evil"]],
    ["interior quote survives", "git config core.hooksPath /tmp/ev'il", ["/tmp/ev'il"]],
  ])("%s", (_name, command, expected) => {
    expect(hooksPathTargets(command)).toEqual(expected);
  });

  test.each([
    ["no hooksPath key", "git config /tmp/evil"],
    ["no config verb", "cat core.hooksPath /tmp/x"],
    ["--get", "git config --get core.hooksPath /tmp/evil"],
    ["--get-all", "git config --get-all core.hooksPath /tmp/evil"],
    ["--list", "git config --list core.hooksPath /tmp/evil"],
    ["only flags after the key", "git config core.hooksPath --global"],
  ])("%s → no target", (_name, command) => {
    expect(hooksPathTargets(command)).toEqual([]);
  });
});

describe("hooksPathElsewhere", () => {
  test("empty value is elsewhere", () => {
    expect(hooksPathElsewhere("", root)).toBe(true);
  });

  test("absolute path that exists is ours", () => {
    expect(hooksPathElsewhere(join(root, FX), root)).toBe(false);
  });

  test("resolve crashing on a non-string root lands in the catch: elsewhere", () => {
    expect(hooksPathElsewhere(FX, 42 as unknown as string)).toBe(true);
  });

  test("absolute path that does not exist is elsewhere", () => {
    expect(hooksPathElsewhere(join(root, "no-such-dir"), root)).toBe(true);
  });

  test("a path that exists but is not this repo's .git/hooks, or sits outside the repo, is elsewhere", () => {
    expect(hooksPathElsewhere(EMPTY, root)).toBe(true);
    expect(hooksPathElsewhere(LOOKALIKE, root)).toBe(true);
    expect(hooksPathElsewhere("/dev/null", root)).toBe(true);
    expect(checkBash("git commit --no-veri -m x", root)?.deny).toBe(true);
    expect(checkBash("git commit --no-ver''ify -m x", root)?.deny).toBe(true);
    expect(checkBash("GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/dev/null git commit -m x", root)?.deny).toBe(true);
    for (const command of [
      "x=--no-verify; git commit $x -m y", "git commit -m x $(echo --no-ver)ify", "git commit -m x --no-ver?fy",
      "git commit -m x --no-ver{ify,}", 'git commit -m "$(printf a)" --no-verify', "GIT_CONFIG_GLOBAL=h.cfg git commit -m x",
      "git -c include.path=h.cfg commit -m x", "git config include.path ../h.cfg", "git pull --no-verify",
      "git -ccore.hooksPath=/x commit -m x", "git -c core.hooksPath commit -m x", "git -c alias.c='commit --no-verify' c -m x",
      "git config alias.c 'commit --no-verify'", "git -c alias.x='!git commit -n' x", "GIT_DIR=x git commit -m x",
      "HOME=. git commit -m x", "git --git-dir=x commit -m x",
    ]) {
      expect(checkBash(command, root)?.deny, command).toBe(true);
    }
    for (const command of [
      'git commit -m "fix: handle -n flag"', "git commit -m 'docs: never use --no-verify'",
      "git commit -m \"$(cat <<'EOF'\nfeat: x\n\nUse -n carefully\nEOF\n)\"", 'git push origin "$(git branch --show-current)"',
      "git log -n 5", 'git commit -m "fix: $(date)"',
    ]) {
      expect(checkBash(command, root), command).toBeUndefined();
    }
  });

  test("relative path resolves against repoRoot, not cwd", () => {
    expect(hooksPathElsewhere(FX, root)).toBe(false);
    expect(hooksPathElsewhere(FX, join(root, EMPTY))).toBe(true);
  });
});

describe("checkBash", () => {
  test("denies an absolute hooksPath target, and the reason names it", () => {
    const result = checkBash("git config core.hooksPath /tmp/evil", root);
    expect(result?.deny).toBe(true);
    if (result?.deny) expect(result.reason).toInclude(hookReason("/tmp/evil"));
  });

  test("denies unset as 'nothing', and the reason says so", () => {
    const result = checkBash("git config --unset core.hooksPath", null);
    expect(result?.deny).toBe(true);
    if (result?.deny) expect(result.reason).toInclude(hookReason("nothing"));
  });

  test("denies an inline -c target", () => {
    const result = checkBash("git -c core.hooksPath=/tmp/evil commit", null);
    expect(result?.deny).toBe(true);
    if (result?.deny) expect(result.reason).toInclude(hookReason("/tmp/evil"));
  });

  test("allows a target that exists under repoRoot", () => {
    expect(checkBash(`git config core.hooksPath ${FX}`, root)).toBeUndefined();
  });

  test.each([
    ["--no-verify commit", "git commit --no-verify -m x", "--no-verify"],
    ["--no-verify push", "git push --no-verify", "--no-verify"],
    ["--no-verify merge", "git merge --no-verify other", "--no-verify"],
    ["--no-verify rebase", "git rebase --no-verify main", "--no-verify"],
    ["--no-verify am", "git am --no-verify patch.diff", "--no-verify"],
    ["git commit -n", "git commit -n -m x", "git commit -n"],
    ["HUSKY=0", "HUSKY=0 git commit -m x", "an environment flag"],
    ["PRE_COMMIT_ALLOW_NO_VERIFY", "PRE_COMMIT_ALLOW_NO_VERIFY=1 git commit -m x", "an environment flag"],
    ["SKIP_HOOKS", "SKIP_HOOKS=1 git push", "an environment flag"],
    ["rm .git/hooks", "rm -rf .git/hooks", "deleting .git/hooks"],
  ])("denies %s, reason verbatim", (_name, command, label) => {
    expect(checkBash(command, null)).toMatchObject({ deny: true, reason: expect.stringContaining(skipReason(label)) });
  });

  test.each([
    ["clean commit", "git commit -m ok"],
    ["HUSKY=1", "HUSKY=1 git commit -m ok"],
  ])("allows %s", (_name, command) => {
    expect(checkBash(command, null)).toBeUndefined();
  });
});

describe("checkContent", () => {
  test.each([
    ["line disable", LINE_DISABLE],
    ["block disable", BLOCK_DISABLE],
    ["ts ignore", TS_IGNORE],
    ["ts expect error", TS_EXPECT],
    ["ts nocheck", TS_NOCHECK],
    ["noqa", NOQA],
    ["nosec", NOSEC],
    ["nolint next line", NOLINT],
    ["allow-list key", ALLOW_LIST],
  ])("silences %s, reason verbatim", (_name, content) => {
    expect(checkContent(content)).toMatchObject({ deny: true, reason: expect.stringContaining(silenceReason) });
  });

  test("allows the prettier carve-out", () => {
    expect(checkContent("// eslint-disable-next-line prettier/prettier")).toBeUndefined();
  });
});

describe("runNoVerify", () => {
  test.each([
    ["Bash", { command: "git commit --no-verify" }],
    ["PowerShell", { command: "git commit --no-verify" }],
  ])("routes %s to checkBash", (tool, input) => {
    expect(runNoVerify(payload(tool, input), null)).toMatchObject({ deny: true });
  });

  test.each([
    ["array command", { command: [42] }],
    ["empty command", { command: "" }],
    ["non-string command", { command: 42 }],
  ])("Bash %s → undefined", (_name, input) => {
    expect(runNoVerify(payload("Bash", input), null)).toBeUndefined();
  });

  test("Edit new_string deny", () => {
    expect(runNoVerify(payload("Edit", { new_string: LINE_DISABLE }), null)).toMatchObject({ deny: true });
  });

  test("Write content fallback deny", () => {
    expect(runNoVerify(payload("Write", { content: TS_IGNORE }), null)).toMatchObject({ deny: true });
  });

  test("NotebookEdit content deny", () => {
    expect(runNoVerify(payload("NotebookEdit", { content: NOQA }), null)).toMatchObject({ deny: true });
  });

  test.each([
    ["array new_string", { new_string: [LINE_DISABLE] }],
    ["empty new_string", { new_string: "" }],
    ["empty new_string with silencing content", { new_string: "", content: TS_IGNORE }],
    ["no content keys", {}],
  ])("Write %s → undefined", (_name, input) => {
    expect(runNoVerify(payload("Write", input), null)).toBeUndefined();
  });
});
