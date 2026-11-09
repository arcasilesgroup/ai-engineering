// The shell reader every Bash guard funnels through: where a command ends, what each
// word is once quoting is gone, which text is code, and what a static echo/printf
// substitution prints. Each case pins the exact structure a guard reads, so a reader
// that splits, joins or decodes one character differently from the shell fails here.
import { describe, expect, test } from "bun:test";
import {
  commandIndex,
  normalizeRedirects,
  rawShellWords,
  resolveSubstitutions,
  shellSegments,
  shellWords,
  SUBSTITUTION,
  unquoteShell,
  type ShellSegment,
} from "../src/guards/shell.ts";

const segment = (text: string, extra: Partial<ShellSegment> = {}): ShellSegment => ({
  text,
  isAfterPipe: false,
  opensSubstitution: text.includes(SUBSTITUTION),
  isProcessSubstitution: false,
  heredocs: [],
  substitutions: [],
  ...extra,
});
const word = (value: string, isQuoted = false, unquoted = isQuoted ? "" : value) => ({ value, isQuoted, isOperator: false, unquoted });
const operator = (value: string) => ({ value, isQuoted: false, isOperator: true, unquoted: value });
const resolved = (command: string): string[] => shellSegments(command)!.map(resolveSubstitutions);

describe("normalizeRedirects", () => {
  test("input duplication reads as `<`, every output form as `>`, process substitution untouched", () => {
    expect(normalizeRedirects("a <&3 2>&1 >| f >(tee g)")).toBe("a  < /dev/fd/3  > /dev/fd/1  >  f >(tee g)");
  });
});

describe("shellSegments: separators", () => {
  test("a pipe marks the next command as reading a pipe; `||` and `&&` do not, and leave no empty command", () => {
    expect(shellSegments("a | b || c && d")).toEqual([
      segment("a "),
      segment(" b ", { isAfterPipe: true }),
      segment(" c "),
      segment(" d"),
    ]);
  });

  test("`|&` pipes stderr too: one cut, the next command reads the pipe", () => {
    expect(shellSegments("a |& b")).toEqual([segment("a "), segment(" b", { isAfterPipe: true })]);
  });

  test("a lone `&` and the case fall-through `;&` each end a command once", () => {
    expect(shellSegments("a & b")).toEqual([segment("a "), segment(" b")]);
    expect(shellSegments("x;&y")).toEqual([segment("x"), segment(""), segment("y")]);
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
      segment("a "),
      segment(" id "),
      segment(` echo ${SUBSTITUTION} z`, { isAfterPipe: true, substitutions: ["id"] }),
    ]);
  });

  test("a pipeline inside a substitution records no first command", () => {
    expect(shellSegments("echo $(a; b)")).toEqual([
      segment("a"),
      segment(" b"),
      segment(`echo ${SUBSTITUTION}`, { substitutions: [""] }),
    ]);
  });

  test("a one-command substitution after an earlier command is still recorded", () => {
    expect(shellSegments("x; echo $(a)")).toEqual([
      segment("x"),
      segment("a"),
      segment(` echo ${SUBSTITUTION}`, { substitutions: ["a"] }),
    ]);
  });

  test("backticks open and close a substitution, also inside double quotes", () => {
    expect(shellSegments('echo "`whoami` x"')).toEqual([
      segment("whoami"),
      segment(`echo "${SUBSTITUTION} x"`, { substitutions: ["whoami"] }),
    ]);
  });

  test("a backtick inside double quotes inside backticks opens a nested substitution", () => {
    expect(shellSegments('echo `echo "`date`"`')).toEqual([
      segment("date"),
      segment(`echo "${SUBSTITUTION}"`, { substitutions: ["date"] }),
      segment(`echo ${SUBSTITUTION}`, { substitutions: [""] }),
    ]);
  });

  test("process substitution is code and is marked as such, also after a `<` redirect", () => {
    expect(shellSegments("cat < <(ls)")).toEqual([
      segment("ls", { isProcessSubstitution: true }),
      segment(`cat < ${SUBSTITUTION}`, { substitutions: ["ls"] }),
    ]);
    expect(shellSegments("diff <(ls) f")).toEqual([
      segment("ls", { isProcessSubstitution: true }),
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
      segment("echo  a "),
      segment(SUBSTITUTION, { substitutions: ["echo  a"] }),
      segment(""),
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
    expect(shellWords("\\-\\-x 'it s' a\\")).toEqual([word("--x", true, "x"), word("it s", true), word("a", true, "a")]);
    expect(shellWords("'abc")).toEqual([word("abc", true)]);
    expect(shellWords("'d\\' e")).toEqual([word("d\\", true), word("e")]);
  });

  test("$'…' decodes hex, octal, named and escaped quotes, and keeps unknown escapes' letter", () => {
    expect(shellWords("$'\\x414\\1012\\n\\q\\'z'")).toEqual([word("A4A2\nq'z", true)]);
  });

  test("double quotes keep a backslash unless it escapes one of \" \\ $ `", () => {
    expect(shellWords('"a\\"b\\$\\nc" $"d e"')).toEqual([word('a"b$\\nc', true), word("d e", true)]);
    expect(shellWords('"ab')).toEqual([word("ab", true)]);
  });

  test("unquoteShell joins continued lines before removing quotes", () => {
    expect(unquoteShell("git com\\\nmit 'x y'")).toBe("git commit x y");
  });

  test("a word records what the shell reads unquoted, where it expands", () => {
    expect(shellWords('"fix "{a,b} ${x:-y} \'*\'$v')).toEqual([word("fix {a,b}", true, "{a,b}"), word("${x:-y}", false), word("*$v", true, "$v")]);
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
