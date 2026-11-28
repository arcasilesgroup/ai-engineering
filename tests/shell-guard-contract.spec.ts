// The shell reader every Bash guard funnels through: where a command ends, what each
// word is once quoting is gone, which text is code, and what a static echo/printf
// substitution prints. Each case pins the exact structure a guard reads, so a reader
// that splits, joins or decodes one character differently from the shell fails here.
import { describe, expect, test } from "bun:test";
import {
  commandIndex,
  findRedirect,
  normalizeRedirects,
  printsFileContent,
  readCommands,
  readsOperandsOnly,
  rawShellWords,
  resolveSubstitutions,
  shellSegments,
  shellWords,
  SUBSTITUTION,
  unquoteShell,
  type ShellSegment,
} from "../src/guards/shell.ts";

/**
 * `scope` is the id of the subshell a guard must treat as isolated: every element of a
 * pipeline, `$( )`, `<$( )>` and a backtick each run in their own, so a variable set
 * there never leaks. `parentScope` is the scope it inherits from; 0 is the top-level
 * shell, and ids are allocated in reading order.
 */
const segment = (text: string, extra: Partial<ShellSegment> = {}): ShellSegment => ({
  text,
  isAfterPipe: false,
  opensSubstitution: text.includes(SUBSTITUTION),
  isInSubstitution: false,
  isProcessSubstitution: false,
  heredocs: [],
  substitutions: [],
  scope: 0,
  parentScope: 0,
  isConditional: false,
  ...extra,
});
/** `original` is the word as written; it differs from `value` only where quotes or escapes
 *  were removed, so a row names it only when it has to. */
const word = (value: string, isQuoted = false, unquoted = isQuoted ? "" : value, original = value) => ({ value, isQuoted, isOperator: false, unquoted, original });
const operator = (value: string) => ({ value, isQuoted: false, isOperator: true, unquoted: value, original: value });
const resolved = (command: string): string[] => shellSegments(command)!.map(resolveSubstitutions);

describe("normalizeRedirects", () => {
  test("input duplication reads as `<`, every output form as `>`, process substitution untouched", () => {
    expect(normalizeRedirects("a <&3 2>&1 >| f >(tee g)")).toBe("a  < /dev/fd/3  > /dev/fd/1  >  f >(tee g)");
  });
});

describe("shellSegments: separators", () => {
  test("a pipe marks the next command as reading a pipe; `||` and `&&` do not, and leave no empty command", () => {
    expect(shellSegments("a | b || c && d")).toEqual([
      segment("a ", { scope: 1 }),
      segment(" b ", { isAfterPipe: true, scope: 2 }),
      segment(" c ", { isConditional: true }),
      segment(" d", { isConditional: true }),
    ]);
  });

  test("`|&` pipes stderr too: one cut, the next command reads the pipe", () => {
    expect(shellSegments("a |& b")).toEqual([segment("a ", { scope: 1 }), segment(" b", { isAfterPipe: true, scope: 2 })]);
  });

  test("a lone `&` and the case fall-through `;&` each end a command once", () => {
    expect(shellSegments("a & b")).toEqual([segment("a ", { scope: 1 }), segment(" b")]);
    expect(shellSegments("x;&y")).toEqual([segment("x"), segment("", { scope: 1 }), segment("y")]);
  });

  test("an escaped separator is part of the word, and a trailing backslash adds nothing", () => {
    expect(shellSegments("a \\; b")).toEqual([segment("a \\; b")]);
    expect(shellSegments("a\\")).toEqual([segment("a\\")]);
  });
});

describe("shellSegments: comments", () => {
  test("a comment runs to the end of its line and the next line is still read", () => {
    expect(shellSegments("a # rm -rf /\nb")).toEqual([segment("a "), segment("b")]);
    expect(shellSegments("#x\nls")).toEqual([segment(""), segment("ls")]);
  });

  test("a `#` inside a word is not a comment", () => {
    expect(shellSegments("echo a#b c")).toEqual([segment("echo a#b c")]);
  });

  test("a `#` after an escaped space is inside the word: bash runs the next command", () => {
    expect(shellSegments("echo a\\ #; echo SECOND")).toEqual([segment("echo a\\ #"), segment(" echo SECOND")]);
    expect(shellSegments("echo a\\\t#; b")).toEqual([segment("echo a\\\t#"), segment(" b")]);
  });

  test("a `#` starting a word after an operator or a quoted word's space is a comment", () => {
    expect(shellSegments("a;#x\nb")).toEqual([segment("a"), segment(""), segment("b")]);
    expect(shellSegments("echo \"a # b\"; git status")).toEqual([segment("echo \"a # b\""), segment(" git status")]);
    expect(shellSegments("echo 'x' # c\nb")).toEqual([segment("echo 'x' "), segment("b")]);
  });
});

describe("shellSegments: substitutions", () => {
  test("`$( )` is its own command and leaves a computed word in the outer one", () => {
    expect(shellSegments("a | echo $( id ) z")).toEqual([
      segment("a ", { scope: 1 }),
      segment(" id ", { isInSubstitution: true, scope: 2 }),
      segment(` echo ${SUBSTITUTION} z`, { isAfterPipe: true, substitutions: ["id"], scope: 3 }),
    ]);
  });

  test("a pipeline inside a substitution records no first command", () => {
    expect(shellSegments("echo $(a; b)")).toEqual([
      segment("a", { isInSubstitution: true, scope: 1 }),
      segment(" b", { isInSubstitution: true, scope: 1 }),
      segment(`echo ${SUBSTITUTION}`, { substitutions: [""] }),
    ]);
  });

  test("a one-command substitution after an earlier command is still recorded", () => {
    expect(shellSegments("x; echo $(a)")).toEqual([
      segment("x"),
      segment("a", { isInSubstitution: true, scope: 1 }),
      segment(` echo ${SUBSTITUTION}`, { substitutions: ["a"] }),
    ]);
  });

  test("backticks open and close a substitution, also inside double quotes", () => {
    expect(shellSegments('echo "`whoami` x"')).toEqual([
      segment("whoami", { isInSubstitution: true, scope: 1 }),
      segment(`echo "${SUBSTITUTION} x"`, { substitutions: ["whoami"] }),
    ]);
  });

  test("a backtick inside double quotes inside backticks opens a nested substitution", () => {
    expect(shellSegments('echo `echo "`date`"`')).toEqual([
      segment("date", { isInSubstitution: true, scope: 2, parentScope: 1 }),
      segment(`echo "${SUBSTITUTION}"`, { isInSubstitution: true, substitutions: ["date"], scope: 1 }),
      segment(`echo ${SUBSTITUTION}`, { substitutions: [""] }),
    ]);
  });

  test("process substitution is code and is marked as such, also after a `<` redirect", () => {
    expect(shellSegments("cat < <(ls)")).toEqual([
      segment("ls", { isInSubstitution: true, isProcessSubstitution: true, scope: 1 }),
      segment(`cat < ${SUBSTITUTION}`, { substitutions: ["ls"] }),
    ]);
    expect(shellSegments("diff <(ls) f")).toEqual([
      segment("ls", { isInSubstitution: true, isProcessSubstitution: true, scope: 1 }),
      segment(`diff ${SUBSTITUTION} f`, { substitutions: ["ls"] }),
    ]);
  });

  test("an unclosed substitution or quote cannot be read", () => {
    expect(shellSegments("echo `x")).toBeNull();
    expect(shellSegments("echo $(x")).toBeNull();
    expect(shellSegments("echo 'x")).toBeNull();
  });
});

describe("shellSegments: here-strings and heredocs", () => {
  test("a here-string is data in the same command; a plain `<` is a redirect", () => {
    expect(shellSegments("cat <<< hi")).toEqual([segment("cat <<< hi")]);
    expect(shellSegments("sort < in")).toEqual([segment("sort < in")]);
  });

  test("the rest of the heredoc's own line still belongs to its command", () => {
    expect(shellSegments("cat <<EOF > out\nhi\nEOF")).toEqual([
      segment("cat <<EOF > out", { heredocs: [{ body: "hi\n", isLiteral: false }] }),
      segment(""),
    ]);
  });

  test("an unquoted heredoc body without code is data only", () => {
    expect(shellSegments("cat <<EOF\nhello\nEOF")).toEqual([
      segment("cat <<EOF", { heredocs: [{ body: "hello\n", isLiteral: false }] }),
      segment(""),
    ]);
  });

  test("a quoted or escaped delimiter makes the body literal", () => {
    expect(shellSegments("cat <<'EOF'\n$(x)\nEOF")).toEqual([
      segment("cat <<'EOF'", { heredocs: [{ body: "$(x)\n", isLiteral: true }] }),
      segment(""),
    ]);
    expect(shellSegments("cat <<\\EOF\n$(x)\nEOF")).toEqual([
      segment("cat <<\\EOF", { heredocs: [{ body: "$(x)\n", isLiteral: true }] }),
      segment(""),
    ]);
  });

  test("an unquoted body that holds code is read as code, quotes blanked", () => {
    expect(shellSegments('cat <<EOF\n$(echo "a")\nEOF')).toEqual([
      segment("cat <<EOF", { heredocs: [{ body: '$(echo "a")\n', isLiteral: false }] }),
      segment("echo  a ", { isInSubstitution: true, scope: 2, parentScope: 1 }),
      segment(SUBSTITUTION, { substitutions: ["echo  a"], scope: 1 }),
      segment("", { scope: 1 }),
      segment(""),
    ]);
  });

  test("the delimiter is the whole word: a `#` glued to it is part of it, not a comment", () => {
    expect(shellSegments("cat <<'EOF'#; ls\nEOF\nbody\nEOF#")).toEqual([
      segment("cat <<'EOF'#", { heredocs: [{ body: "EOF\nbody\n", isLiteral: true }] }),
      segment(" ls"),
      segment(""),
    ]);
    expect(shellSegments('cat <<"E"F#x\nEF#x')).toEqual([
      segment('cat <<"E"F#x', { heredocs: [{ body: "", isLiteral: true }] }),
      segment(""),
    ]);
  });

  test("an unreadable heredoc delimiter or body cannot be read", () => {
    expect(shellSegments("cat <<")).toBeNull();
    expect(shellSegments("cat <<$'EOF'\nEOF")).toBeNull();
    expect(shellSegments("cat <<EOF\n$(x\nEOF")).toBeNull();
  });

  test("`<<-` strips only leading tabs before matching the delimiter", () => {
    expect(shellSegments("cat <<-EOF\n\tbody\n\t\tEOF\nls")).toEqual([
      segment("cat <<-EOF", { heredocs: [{ body: "\tbody\n", isLiteral: false }] }),
      segment(""),
      segment("ls"),
    ]);
    expect(shellSegments("cat <<-EOF\nEOF\t\nEOF")).toEqual([
      segment("cat <<-EOF", { heredocs: [{ body: "EOF\t\n", isLiteral: false }] }),
      segment(""),
    ]);
  });

  test("plain `<<` does not strip tabs, and an unterminated body runs to the end", () => {
    expect(shellSegments("cat <<EOF\n\tEOF\nEOF")).toEqual([
      segment("cat <<EOF", { heredocs: [{ body: "\tEOF\n", isLiteral: false }] }),
      segment(""),
    ]);
    expect(shellSegments("cat <<EOF\nhi")).toEqual([
      segment("cat <<EOF", { heredocs: [{ body: "hi", isLiteral: false }] }),
      segment(""),
    ]);
  });
});

describe("shellWords", () => {
  test("redirect runs split off as operators", () => {
    expect(shellWords("a>b <<< c")).toEqual([word("a"), operator(">"), word("b"), operator("<<<"), word("c")]);
    expect(shellWords("a >> b <> c")).toEqual([word("a"), operator(">>"), word("b"), operator("<>"), word("c")]);
  });

  test("escapes and single quotes are removed and mark the word quoted", () => {
    expect(shellWords("\\-\\-x 'it s' a\\")).toEqual([
      word("--x", true, "x", "\\-\\-x"), word("it s", true, "", "'it s'"), word("a", true, "a", "a\\"),
    ]);
    expect(shellWords("'abc")).toEqual([word("abc", true, "", "'abc")]);
    expect(shellWords("'d\\' e")).toEqual([word("d\\", true, "", "'d\\'"), word("e")]);
  });

  test("$'…' decodes hex, octal, named and escaped quotes, and keeps unknown escapes' letter", () => {
    expect(shellWords("$'\\x414\\1012\\n\\q\\'z'")).toEqual([word("A4A2\nq'z", true, "", "$'\\x414\\1012\\n\\q\\'z'")]);
  });

  test("double quotes keep a backslash unless it escapes one of \" \\ $ `", () => {
    expect(shellWords('"a\\"b\\$\\nc" $"d e"')).toEqual([word('a"b$\\nc', true, "", '"a\\"b\\$\\nc"'), word("d e", true, "", '$"d e"')]);
    expect(shellWords('"ab')).toEqual([word("ab", true, "", '"ab')]);
  });

  test("a Windows path keeps its separators; the same backslash elsewhere is an escape", () => {
    // A path is spelled with `\`, so `\` there is a character: removed as an escape the
    // word names a file nobody wrote, and every guard downstream allows the write.
    expect(shellWords("cat C:\\repo\\.ai-engineering\\config.toml").map((word) => word.value))
      .toEqual(["cat", "C:\\repo\\.ai-engineering\\config.toml"]);
    expect(shellWords(".\\rm ..\\x").map((word) => word.value)).toEqual([".\\rm", "..\\x"]);
    // No drive and no leading `.`, so this is an ordinary word with an escape in it.
    expect(shellWords("r\\m C:tools\\rm").map((word) => word.value)).toEqual(["rm", "C:toolsrm"]);
  });

  test("unquoteShell joins continued lines before removing quotes", () => {
    expect(unquoteShell("git com\\\nmit 'x y'")).toBe("git commit x y");
  });

  test("a word records what the shell reads unquoted, where it expands", () => {
    expect(shellWords('"fix "{a,b} ${x:-y} \'*\'$v')).toEqual([
      word("fix {a,b}", true, "{a,b}", '"fix "{a,b}'), word("${x:-y}"), word("*$v", true, "$v", "'*'$v"),
    ]);
  });
});

describe("shellSegments: $'…' and ${…}", () => {
  test("$'…' closes only at an unescaped quote, so what follows `$'\\''` is code", () => {
    expect(shellSegments("echo $'\\'' ; ls #'")).toEqual([segment("echo $'\\'' "), segment(" ls ")]);
    expect(shellSegments("echo $'a;b' \"$'\" ; ls")).toEqual([segment("echo $'a;b' \"$'\" "), segment(" ls")]);
    expect(shellSegments("echo $'\\'")).toBeNull();
  });

  test("a one-word ${…} is part of its word; one that expands to words, or hides a quote, is unreadable", () => {
    expect(shellSegments("echo ${x:-a;b}x")).toBeNull();
    expect(shellSegments("echo ${HOME}/${#a[@]};ls")).toEqual([segment("echo ${HOME}/${#a[@]}"), segment("ls")]);
    expect(shellSegments('echo "${x:-a > b}"')).toEqual([segment('echo "${x:-a > b}"')]);
    for (const command of ["echo ${x:-> f}", "echo ${x:-a b}", "echo ${x:-$(id)}", "echo ${a:-${b}}", 'echo "${x:-"}"', "echo ${x"]) {
      expect(shellSegments(command), command).toBeNull();
    }
  });
});

describe("commandIndex", () => {
  const nameAt = (command: string): string => {
    const words = command.split(" ");
    return words[commandIndex(words)] ?? "";
  };

  test.each([
    ["{ git commit", "git"],
    ["! git commit", "git"],
    ["if git diff", "git"],
    ["do git commit", "git"],
    ["FOO=1 BAR=2 git push", "git"],
    ["command -p git commit", "git"],
    ["env -i -u FOO BAR=1 git commit", "git"],
    ["nice -n 5 git commit", "git"],
    ["time -p git push", "git"],
    ["xargs -n 1 git commit", "git"],
    ["sudo -u root git commit", "git"],
    ["timeout -s KILL 5 git push", "git"],
    ["stdbuf -o L git push", "git"],
    ["exec -a name git push", "git"],
    ["/usr/bin/env git push", "git"],
    ["for git in commit", "for"],
    ["chronic git commit", "chronic"],
    ["env FOO=1", ""],
  ])("%s runs %s", (command, name) => {
    expect(nameAt(command)).toBe(name);
  });
});

describe("rawShellWords", () => {
  test("splits only on unquoted space: quotes, escapes, $'…' and ${…} stay in their word, as written", () => {
    expect(rawShellWords(`echo "a b">x $'\\' y' \${x:-a b} c\\ d 'e`)).toEqual(['echo', '"a b">x', "$'\\' y'", "${x:-a b}", "c\\ d", "'e"]);
  });
});

describe("resolveSubstitutions", () => {
  test("echo prints its words, dropping only leading -n/-e/-E flags", () => {
    expect(resolved("cp $(echo -n -eE a  b) d")).toEqual(["echo -n -eE a  b", "cp a b d"]);
    expect(resolved("cp $(echo -nx x-n -n) d")[1]).toBe("cp -nx x-n -n d");
    expect(resolved("cp $(echo -ne) d")[1]).toBe("cp  d");
    expect(resolved("cp $(echo a-n b) d")[1]).toBe("cp a-n b d");
  });

  test("printf fills %s in order, empties missing values, and drops one trailing \\n", () => {
    expect(resolved("cp $(printf %s-%s a) d")[1]).toBe("cp a- d");
    expect(resolved("cp $(printf %s) d")[1]).toBe("cp %s d");
    expect(resolved("cp $(printf 'abc\\n') d")[1]).toBe("cp abc d");
  });

  test("each substitution resolves to its own command's output", () => {
    expect(resolved("cp $(echo a) $(echo b)")[2]).toBe("cp a b");
  });

  test("anything that cannot be known from the text stays a computed word", () => {
    for (const inner of ["printf", "cat x", "echo a > b", "echo $HOME", "echo 'a\"b'"]) {
      expect(resolved(`cp $(${inner}) d`).at(-1)).toBe(`cp ${SUBSTITUTION} d`);
    }
  });
});

describe("the command model — one parse every guard is a predicate over", () => {
  const command = (text: string) => readCommands(text)![0]!;

  test("a redirect is the operator and the file it names, whatever the spelling", () => {
    const spellings = [
      "echo x > out",
      "echo x >out",
      'echo x > "out"',
      "echo x 1> out",
      "echo x >| out",
      "echo x >> out",
    ];
    for (const text of spellings) {
      expect(command(text).redirects.map(({ operator, target }) => [operator, target?.value]), text).toEqual([[">", "out"]]);
      expect(command(text).plain.map((word) => word.value), text).toEqual(["echo", "x"]);
    }
    // A descriptor copy is respelled as the file the descriptor is; a device is no file.
    expect(command("echo x 2>&1 2>/dev/null").redirects.map(({ target }) => target?.value)).toEqual(["/dev/fd/1", "/dev/null"]);
    expect(command("echo x >& 1").redirects.map(({ target }) => target?.value)).toEqual(["/dev/fd/1"]);
    expect(command("echo x 2>&1 2>/dev/null").writes).toEqual([]);
    expect(command("echo x > out").writes.map((word) => word.value)).toEqual(["out"]);
  });

  test("an input redirect reads a file, a here-string and a heredoc delimiter name none", () => {
    const read = command("cat < notes.txt <<< 'done'");
    expect(read.reads.map((word) => word.value)).toEqual(["notes.txt"]);
    expect(read.writes).toEqual([]);
    expect(command("bash <<'EOF'").reads).toEqual([]);
    // Closing a descriptor is respelled as the file it is, like every other fd form.
    expect(command("cat 3<&-").redirects.map(({ target }) => target?.value)).toEqual(["/dev/fd/-"]);
    expect(command("cat 3<&-").reads).toEqual([]);
  });

  test("the verb stands past NAME=value and every wrapper the reader knows", () => {
    for (const [text, verb, args] of [
      ["sudo -u root doas env FOO=1 git push origin", "git", ["push", "origin"]],
      ["timeout -s KILL 5 stdbuf -oL nice -n 5 rm -rf x", "rm", ["-rf", "x"]],
      ["{ git commit -m x; }", "git", ["commit", "-m", "x"]],
      ["if git status; then echo ok; fi", "git", ["status"]],
      ["xargs -n 1 git commit", "git", ["commit"]],
    ] as const) {
      // A compound command opens its own segment, so the row asks for the segment that runs.
      const running = readCommands(text)!.find((parsed) => parsed.verb.length > 0)!;
      expect(running.verb, text).toBe(verb);
      expect(running.args.map((word) => word.value), text).toEqual([...args]);
    }
  });

  test("a word keeps the spelling it was written with, which is what a path is judged on", () => {
    const words = command("rm 'a b' \"c\" d\\ e $'f'").plain;
    expect(words.map((word) => word.value)).toEqual(["rm", "a b", "c", "d e", "f"]);
    expect(words.map((word) => word.original)).toEqual(["rm", "'a b'", '"c"', "d\\ e", "$'f'"]);
  });

  test("the pipeline, the substitution and the heredoc are the segment's own facts", () => {
    const segments = readCommands("echo $(id) | grep x && sh <<'EOF'\nid\nEOF")!;
    // The substitution is its own segment, first, and the command around it keeps a marker.
    expect(segments.map((parsed) => parsed.segment.text.trim()).filter((text) => text.length > 0))
      .toEqual(["id", "echo $__SUB__", "grep x", "sh <<'EOF'"]);
    const outer = segments.find((parsed) => parsed.segment.substitutions.length > 0)!;
    expect(outer.segment.substitutions).toEqual(["id"]);
    const piped = segments.find((parsed) => parsed.segment.isAfterPipe)!;
    expect(piped.verb).toBe("grep");
    const heredoc = segments.find((parsed) => parsed.segment.heredocs.length > 0)!;
    expect(heredoc.segment.heredocs).toEqual([{ body: "id\n", isLiteral: true }]);
  });

  test("findRedirect reads a redirect off a word a guard never parsed", () => {
    expect(findRedirect("f>x")).toEqual({ index: 1, operator: ">", attached: "x" });
    expect(findRedirect(">out")).toEqual({ index: 0, operator: ">", attached: "out" });
    // The descriptor prefix belongs to the operator, as the shell reads it.
    expect(findRedirect("2>>log")).toEqual({ index: 0, operator: "2>>", attached: "log" });
    expect(findRedirect("plain")).toBeNull();
  });
});

describe("the reader tables — one question each, answered here", () => {
  test("what prints a file into context, and what only reads its operands", () => {
    expect(printsFileContent("cat", ["notes.txt"])).toBe(true);
    expect(printsFileContent("grep", ["-i", "x", "notes.txt"])).toBe(true);
    // An in-place editor and an output option write instead of printing.
    expect(printsFileContent("sed", ["-i", "s/a/b/", "notes.txt"])).toBe(false);
    expect(printsFileContent("awk", ["-i", "inplace", "p", "notes.txt"])).toBe(false);
    expect(printsFileContent("sort", ["-o", "notes.txt"])).toBe(false);
    expect(printsFileContent("cat", ["--output=notes.txt"])).toBe(false);
    // `ls` reads its operands without printing their bytes, so only the second question
    // says yes to it: naming a governed path with it is not a write.
    expect(printsFileContent("ls", ["src"])).toBe(false);
    expect(readsOperandsOnly("ls", ["src"])).toBe(true);
    expect(readsOperandsOnly("git", ["status"])).toBe(false);
    expect(readsOperandsOnly("rm", ["x"])).toBe(false);
  });
});
