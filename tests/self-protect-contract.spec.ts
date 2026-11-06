// tests/self-protect-contract.spec.ts — the exact verdict self-protect gives each shell
// shape, and which layer gives it. Three layers can refuse one command: the ai-eng verb
// check, the per-command write check and the shell reader. Each names a different next
// step, so every case pins the whole reason: a layer that stops catching what it owns
// shows up as another layer's words, or as an allow.

import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import { mkdirSync, mkdtempSync, realpathSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, sep } from "node:path";
import { runSelfProtect } from "../src/guards/self-protect.ts";

const HOME_BEFORE = process.env.AI_ENG_HOME;
const scratch: string[] = [];
let repo = "";

beforeAll(() => {
  const home = mkdtempSync(join(tmpdir(), "ai-eng-spcontract-home-"));
  repo = realpathSync(mkdtempSync(join(tmpdir(), "ai-eng-spcontract-repo-")));
  scratch.push(home, repo);
  process.env.AI_ENG_HOME = home;
  mkdirSync(join(repo, ".ai-engineering"), { recursive: true });
  writeFileSync(join(repo, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n');
});
afterAll(() => {
  if (HOME_BEFORE === undefined) delete process.env.AI_ENG_HOME;
  else process.env.AI_ENG_HOME = HOME_BEFORE;
  for (const dir of scratch) rmSync(dir, { recursive: true, force: true });
});

/** A path as a Bash command line carries it: `/`-separated, the way Git Bash takes it. */
const shellSpelling = (path: string): string => path.split(sep).join("/");
const inRepo = (...parts: string[]): string => join(repo, ...parts);

const CLI = "this command invokes a governance-changing or internal ai-eng verb. Run it from outside the governed agent session.";
const WRITES = (found: string): string =>
  `this command writes to ${found}, which is part of what governs this session. A person changes that, in a reviewed diff — not the session it governs.`;
const UNREADABLE = (why: string): string =>
  `this command cannot run here: ${why}. Write the command out plainly, and leave governance files to a person. This check reads the shell; it is not a sandbox.`;
const GOVERNED_FILE = (target: string): string =>
  `${target} is part of what governs this session — it is how the rules reach you and how what happens here is recorded. Changing it from inside the session it governs is not a change a session gets to make. A person edits it, in a diff, in a pull request.`;
const EXTRACTS = (name: string, into: string): string =>
  UNREADABLE(`${name} extracts files into ${into}, which holds what governs this session; extract somewhere else`);
const NAMES = (name: string, hit: string): string =>
  UNREADABLE(`${name} names ${hit}, which governs this session, and ${name} is not a read-only command`);
const STDIN_PROGRAM = UNREADABLE("an interpreter reading its program from stdin runs code the guards cannot read");
const GENERATED_PROGRAM = UNREADABLE("an interpreter fed generated text runs code the guards cannot read");
const EVAL = UNREADABLE("eval runs text the guards cannot read");
const ENCODED = UNREADABLE("an encoded PowerShell command hides what it runs");
const CALL_OPERATOR = UNREADABLE("the call operator runs a command name computed at run time");
const AI_ENG_VERB = UNREADABLE("it invokes a governance-changing or internal ai-eng verb");
const APPLY_PATCH = UNREADABLE("apply_patch reads a patch the guards cannot see; pass it as one quoted heredoc");

type Case = [command: string, reason: string | null];

function verdict(command: string, tool = "Bash"): { deny: true; reason: string } | { deny: false } | undefined {
  return runSelfProtect({ tool_name: tool, tool_input: { command } }, repo);
}

function expectCases(cases: Case[], tool = "Bash"): void {
  for (const [command, reason] of cases) {
    expect(verdict(command, tool), command).toEqual(reason === null ? undefined : { deny: true, reason });
  }
}

describe("ai-eng verbs: refused with the run-it-outside step before anything else reads the line", () => {
  test("only the governance-changing verbs, and the whole verb pair", () => {
    expectCases([
      ["ai-eng uninstall --force", CLI],
      ["ai-eng adapt apply", CLI],
      ["ai-eng adapt", null],
      ["ai-eng config", null],
      ["ai-eng config --remove x", CLI],
      ["npx ai-eng uninstall", CLI],
      ["bun src/cli.ts uninstall", CLI],
      ["bun scripts/build.ts wrap", null],
    ]);
  });

  test("a shell's -c program is read as its own command line", () => {
    expectCases([
      ['bash -c "ai-eng uninstall"', CLI],
      ['bash -x -c "ai-eng uninstall"', CLI],
      ['bash -lc "ai-eng uninstall"', CLI],
      ['pwsh -Command "ai-eng uninstall"', CLI],
      ["cmd /c ai-eng uninstall", CLI],
      ["cmd /k ai-eng uninstall", CLI],
    ]);
  });

  test("redirections before the verb are skipped; a redirect target is not an argument", () => {
    expectCases([
      ["> /dev/null ai-eng uninstall", CLI],
      [">/dev/null ai-eng uninstall", CLI],
      ["ai-eng status > wrap", null],
      ["ai-eng status 2>out wrap", CLI],
      // The glued redirect only splits off once the line is normalised: the second pass owns it.
      ["ai-eng uninstall>out.txt", CLI],
    ]);
  });

  test("past the nesting the verb check reads, the shell reader still finds the verb", () => {
    expectCases([["bash -c bash -c bash -c bash -c bash -c bash -c ai-eng uninstall", AI_ENG_VERB]]);
  });

  test("ai-eng behind a prefix the verb check does not know is caught by the shell reader", () => {
    expectCases([
      ["nice ai-eng uninstall", AI_ENG_VERB],
      ["nice bun scripts/cli.ts uninstall", AI_ENG_VERB],
      ["nice node scripts/cli.js uninstall", AI_ENG_VERB],
      ["nice ai-eng status", null],
      // Only an xargs before ai-eng feeds it arguments; one after it is an argument.
      ["ai-eng status xargs", null],
      ["ai-eng $verb", UNREADABLE("it runs ai-eng with arguments computed at run time")],
      ["nice ai-eng $verb status", UNREADABLE("it runs ai-eng with arguments computed at run time")],
    ]);
  });
});

describe("writes to the git floor: the verb is found past escapes, wrappers and their options", () => {
  const hooks = (): string => inRepo(".git", "hooks");

  test("escaped, parenthesised and Windows-spelled verbs are still rm", () => {
    expectCases([
      ["((rm .git/hooks/pre-commit))", WRITES(hooks())],
      ["r\\m .git/hooks/pre-commit", WRITES(hooks())],
      [".\\rm .git/hooks/pre-commit", WRITES(hooks())],
      ["C:\\tools\\rm .git/hooks/pre-commit", WRITES(hooks())],
    ]);
  });

  test("prefix options and their values are skipped to reach the verb", () => {
    expectCases([
      ["command -p rm .git/hooks/pre-commit", WRITES(hooks())],
      ["timeout 10 rm .git/hooks/pre-commit", WRITES(hooks())],
      ["timeout 10s rm .git/hooks/pre-commit", WRITES(hooks())],
      ["env FOO=1 rm .git/hooks/pre-commit", WRITES(hooks())],
    ]);
  });

  test("a PowerShell backtick escape is removed before the verb is read", () => {
    expectCases([["r`m .git/hooks/pre-commit", WRITES(hooks())]], "PowerShell");
  });

  test("a governance file outside the literal list is named by its path, not by the verb's flag", () => {
    expectCases([["rm -f .github/hooks/pre.json", WRITES(inRepo(".github", "hooks", "pre.json"))]]);
  });

  test.skipIf(sep === "\\")("on POSIX a backslash is part of a file name, not a separator", () => {
    expectCases([["rm '.git\\hooks\\pre-commit'", null]]);
  });
});

describe("the shell reader: each unreadable shape names itself", () => {
  test("shapes whose code is not on the line", () => {
    expectCases([
      ["diff <(ls) notes.txt", UNREADABLE("process substitution runs a command whose text is not on the line")],
      ["$tool notes.txt", UNREADABLE("the command name is computed at run time")],
      ["r[m] notes.txt", UNREADABLE("the command name is a pattern the shell expands")],
      ["echo 'unterminated", UNREADABLE("its quoting cannot be read, so neither can what it runs")],
      ["eval ls", EVAL],
      ["alias ll=ls x", UNREADABLE("an alias renames commands the guards judge by name")],
      ["alias ll", null],
      ["hash -p /bin/rm ls", UNREADABLE("hash -p renames a command the guards judge by name")],
      ["source /dev/stdin", UNREADABLE("sourcing stdin runs text the guards cannot read")],
      ["printf id | ksh", UNREADABLE("piping text into a shell runs code the guards cannot read")],
      ["BASH_ENV=x ls", UNREADABLE("BASH_ENV sources a file the guards cannot read")],
      ["MYENV=1 ls", null],
      ["base64 -d notes.b64", UNREADABLE("decoding base64 hides the command it carries")],
      ["base64 x-d", null],
    ]);
  });

  test("six nested -exec programs are deeper than the reader follows", () => {
    const nested = `${"find src -exec ".repeat(6)}ls \\;`;
    expectCases([[nested, UNREADABLE("it nests shells too deep to read")]]);
  });

  test("an interpreter with no program reads one from stdin; -c in any cluster is a program", () => {
    expectCases([
      ["python3", STDIN_PROGRAM],
      ["python3 <<'EOF'\nprint(1)\nEOF", null],
      ["python3 <<< 'print(1)'", null],
      ["bash -c", null],
      ["bash -lc", null],
      ["bash -cx", null],
      ["bash -c1", STDIN_PROGRAM],
    ]);
  });

  test("a program computed at run time is refused for what it is", () => {
    expectCases([
      ['bash -c "$(date)"', GENERATED_PROGRAM],
      ['bash -c "$(date)" arg0', GENERATED_PROGRAM],
      ['python3 <<< "$(date)"', GENERATED_PROGRAM],
    ]);
  });

  test("an encoded PowerShell command is refused however the host and flag are spelled", () => {
    expectCases([
      ["pwsh -enc AAAA", ENCODED],
      ["p\\wsh -enc AAAA", ENCODED],
      ["p\\wsh -EC AAAA", ENCODED],
      ["p\\wsh -e AAAA", ENCODED],
      ["p\\wsh - AAAA", null],
    ]);
  });

  test("apply_patch runs only from one quoted heredoc that holds a readable patch", () => {
    const patch = "*** Begin Patch\n*** Add File: notes.md\n+hi\n*** End Patch";
    expectCases([
      ["apply_patch", APPLY_PATCH],
      [`apply_patch <<'EOF'\n${patch}\nEOF`, null],
      [`apply_patch <<EOF\n${patch}\nEOF`, APPLY_PATCH],
      ["apply_patch <<'EOF'\nhello\nEOF", APPLY_PATCH],
      [`apply_patch <<'A' <<B\n${patch}\nA\nhello\nB`, APPLY_PATCH],
    ]);
  });

  test("a patch is judged by every file it names, and a header it cannot read is refused", () => {
    expectCases([
      [
        "apply_patch <<'EOF'\n*** Begin Patch\n*** Update File: .ai-engineering/config.toml\n@@\n-a\n+b\n*** End Patch\nEOF",
        GOVERNED_FILE(".ai-engineering/config.toml"),
      ],
      [
        "apply_patch <<'EOF'\n*** Begin Patch\n*** Bogus\n*** End Patch\nEOF",
        "this command carries a patch whose files cannot be read safely. Use well-formed *** Begin Patch / *** End Patch blocks.",
      ],
    ]);
  });
});

describe("the shell reader: write targets and paths", () => {
  test("$'\\'' is one quote, so the redirect after it is read; a ${…} that expands to words is unreadable", () => {
    expectCases([
      ["echo $'\\'' >| .git/hooks/pre-commit #'", WRITES(inRepo(".git", "hooks"))],
      ["echo ${x:-> notes.txt}", UNREADABLE("its quoting cannot be read, so neither can what it runs")],
      ["echo $'a' >| notes.txt #'", null],
      ["echo ${HOME}", null],
      ['echo "a>b"', null],
    ]);
  });
  test("redirect targets are judged where they land; input redirects are not writes", () => {
    expectCases([
      ["echo x > $f", UNREADABLE("it writes to a path computed at run time")],
      [
        "echo x > .ai-engineering/workflow/checkpoints/1.json",
        UNREADABLE(`it writes to ${inRepo(".ai-engineering", "workflow", "checkpoints", "1.json")}, which governs this session`),
      ],
      ["sort < .git/hooks/pre-commit", null],
      ["sort <<<", null],
      ["echo x >", null],
    ]);
  });

  test("after a cd to a computed directory, relative targets are unknowable and absolute ones are not", () => {
    const relativeWrite = UNREADABLE("it writes to a relative path after a cd to a directory computed at run time");
    const relativeAct = UNREADABLE("rm acts on a relative path after a cd to a directory computed at run time");
    expectCases([
      ["cd $d && echo x > out.txt", relativeWrite],
      ["cd -- $d && echo x > out.txt", relativeWrite],
      ["cd -LP $d && echo x > out.txt", relativeWrite],
      ["cd src && echo x > out.txt", null],
      ["cd && echo x > out.txt", null],
      ["cd $d && rm notes.txt", relativeAct],
      [`cd $d && rm -f ${shellSpelling(inRepo("notes.txt"))}`, null],
    ]);
  });

  test("a writer's computed, braced, globbed or variable path is resolved before it is judged", () => {
    const hook = inRepo(".git", "hooks", "pre-commit");
    expectCases([
      ["rm $f", UNREADABLE("rm acts on a path computed at run time")],
      ["rm {a,.git}/hooks/pre-commit", NAMES("rm", hook)],
      ["f=.git/hooks/pre-commit; rm $f", NAMES("rm", hook)],
      ["f=.git/hooks/pre-commit; rm ${f}", NAMES("rm", hook)],
      ["rm src/*.tmp", null],
      ["vim .ai-engineering/config.toml", NAMES("vim", inRepo(".ai-engineering", "config.toml"))],
      ["rm -rf .", UNREADABLE("rm acts on ., which contains what governs this session; name the files you mean")],
      ["sed -i s/x/y/ .", UNREADABLE("sed acts on ., which contains what governs this session; name the files you mean")],
    ]);
  });

  test("verbs that write from stdin or a diff are refused for that, not for a path", () => {
    expectCases([
      ["ls | xargs rm", UNREADABLE("rm acts on paths read from stdin")],
      ["nice rm notes.txt", null],
      ["patch -p1 < fix.diff", UNREADABLE("patch applies edits whose target files are not on the command line; use the edit tool")],
      ["cp /usr/local/bin/ai-eng ./bin/x", UNREADABLE("it copies or links the ai-eng binary, which would let its verbs run under another name")],
    ]);
  });

  test("an output option computed at run time is refused; a literal one is not", () => {
    const computed = UNREADABLE("sort writes to an output path computed at run time");
    expectCases([
      ["sort -o $f notes.txt", computed],
      ["sort -o$f notes.txt", computed],
      ["sort -o out.txt notes.txt", null],
      ["sort -oout.txt notes.txt", null],
    ]);
  });

  test("text a non-shell program reads as input or code is searched for verbs and governed paths", () => {
    expectCases([
      ["at now <<< 'ai-eng uninstall'", UNREADABLE("at reads input that invokes a governance-changing ai-eng verb")],
      [
        "at now <<< 'cat src/a.ts .git/hooks/pre-commit'",
        UNREADABLE(`at reads input that names ${inRepo(".git", "hooks", "pre-commit")}, which governs this session`),
      ],
      ["at now <<< 'echo hi'", null],
      [`osascript -e 'do shell script "ai-eng uninstall"'`, UNREADABLE("osascript is handed code that invokes a governance-changing ai-eng verb")],
    ]);
  });
});

describe("archive extraction lands in the cwd unless told otherwise", () => {
  const intoRoot = (name: string): string => EXTRACTS(name, ".");

  test("tar: every spelling of extract, and every spelling of the directory", () => {
    expectCases([
      ["tar -xf a.tar", intoRoot("tar")],
      ["tar --extract -f a.tar", intoRoot("tar")],
      ["tar --get -f a.tar", intoRoot("tar")],
      ["tar xf a.tar", intoRoot("tar")],
      ["tar xvf a.tar", intoRoot("tar")],
      ["tar zxf a.tgz", intoRoot("tar")],
      ["tar -zxf a.tgz", intoRoot("tar")],
      ["tar -x -f a.tar", intoRoot("tar")],
      ["tar -xf a.tar -C=out", intoRoot("tar")],
      ["tar -tf a.tar", null],
      ["tar cf a.tar src", null],
      ["tar -cf my-x src", null],
      ["tar -xf a.tar -C out", null],
      ["tar -C out -xf a.tar", null],
      ["tar -xf a.tar --directory out", null],
      ["tar -xf a.tar --directory=out", null],
      ["tar -xf a.tar --directory=.ai-engineering", EXTRACTS("tar", ".ai-engineering")],
      ["tar -xf a.tar -C .git/hooks/pre-commit", EXTRACTS("tar", ".git/hooks/pre-commit")],
      ["tar -xf a.tar -C '{out,.}'", EXTRACTS("tar", "{out,.}")],
    ]);
  });

  test("unzip, cpio and 7z", () => {
    expectCases([
      ["unzip a.zip", intoRoot("unzip")],
      ["unzip my-l.zip", intoRoot("unzip")],
      ["unzip -l a.zip", null],
      ["unzip -ql a.zip", null],
      ["unzip a.zip -d out", null],
      ["cpio -i < a.cpio", intoRoot("cpio")],
      ["cpio -vi < a.cpio", intoRoot("cpio")],
      ["cpio -v -i < a.cpio", intoRoot("cpio")],
      ["cpio --extract < a.cpio", intoRoot("cpio")],
      ["cpio -o < list.txt", null],
      ["7z x a.7z", intoRoot("7z")],
      ["7z e a.7z", intoRoot("7z")],
      ["7z l a.7z", null],
      ["7z x a.7z -oout", null],
      ["7z x a.7z -o.ai-engineering", EXTRACTS("7z", ".ai-engineering")],
    ]);
  });
});

describe("find: a reader until an action hands its matches to a writer", () => {
  const treeWrite = UNREADABLE("find acts on ., which contains what governs this session; name the files you mean");

  test("tests and reader actions read; -delete and writer actions write", () => {
    expectCases([
      ["find .git/hooks -name x", null],
      ["find . -name '*.md'", null],
      ["find . -fprint out.txt", null],
      ["find . -exec cat {} +", null],
      ["find . -exec git log {} +", null],
      ["find . -executable -print", null],
      ["find . -delete", treeWrite],
      ["find . -exec rm {} +", treeWrite],
    ]);
  });

  test("an -exec program ends at its terminator and is judged as code", () => {
    expectCases([
      ["find src -exec python3 \\;", STDIN_PROGRAM],
      ["find src -exec python3", STDIN_PROGRAM],
      ["find src -exec cat {} \\; python3", null],
      ["find src -exec cat {} + python3", null],
      ["find src -exec bash -c 'eval x' \\;", EVAL],
    ]);
  });
});

describe("code carried inside arguments is judged as code", () => {
  test("git runs the values of its program keys, from -c and from git config", () => {
    expectCases([
      ["git -c core.pager='eval x' log", EVAL],
      ["git -c user.name='eval x' log", null],
      ["git config core.pager 'eval x'", EVAL],
      ["git config --global core.pager 'eval x'", EVAL],
      ["git config core.pager", null],
    ]);
  });

  test("command runners and shells: every carried program, joined as the shell joins it", () => {
    expectCases([
      ["watch ls 'eval x'", EVAL],
      ["watch -n 1 'eval x'", EVAL],
      ["bash -c 'eval x' name", EVAL],
      ["bash -c eval x", EVAL],
      ["bash -lc 'eval x'", EVAL],
      ["bash -x eval", null],
      ["bash eval", null],
      ["pwsh -NoProfile eval x", EVAL],
    ]);
  });

  test("a program handed to a PowerShell host is read as PowerShell, and only then", () => {
    expectCases([
      ["pwsh -NoProfile '& (gcm rm) x'", CALL_OPERATOR],
      ["watch '& (gcm rm) x'", null],
    ]);
  });
});

describe("PowerShell reaches code without a command word", () => {
  test(".NET calls into files, processes and code are refused; other type literals are not calls", () => {
    expectCases([
      ["[System.IO.File]::WriteAllText('x','y')", UNREADABLE("[System.IO.File]:: reaches files or code without a command the guards can read")],
      ["[System.IO.File] ::ReadAllText('x')", UNREADABLE("[System.IO.File]:: reaches files or code without a command the guards can read")],
      ["[Process]::Start('x')", UNREADABLE("[Process]:: reaches files or code without a command the guards can read")],
      ["[IO.Compression.ZipFile]::ExtractToDirectory('a','b')", UNREADABLE("[IO.Compression.ZipFile]:: reaches files or code without a command the guards can read")],
      ["[int]::MaxValue", UNREADABLE("the command name is a pattern the shell expands")],
      // A type is judged by its last segment and its namespace root, not by a word inside it.
      ["[MyApp.FileHelper]::Run()", UNREADABLE("the command name is a pattern the shell expands")],
      ["[MyApp.Net]::Run()", UNREADABLE("the command name is a pattern the shell expands")],
      ["[MyApp.Microsoft.Win32]::Run()", UNREADABLE("the command name is a pattern the shell expands")],
    ], "PowerShell");
  });

  test("the call operator on a computed name, and names built by concatenation", () => {
    expectCases([
      ["& $cmd", CALL_OPERATOR],
      ["&$cmd", CALL_OPERATOR],
      ["&(gcm rm) x", CALL_OPERATOR],
      ["if ($true) { & $cmd }", CALL_OPERATOR],
      ["Remove-Item ( '.git/' + 'x')", UNREADABLE("it builds a name or path by concatenation at run time")],
    ], "PowerShell");
  });
});
