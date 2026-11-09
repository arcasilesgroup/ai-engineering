// Just enough of the POSIX shell grammar to read a command the way the shell will: where
// one command ends, what each word is once quotes and escapes are gone, and which text is
// code (substitutions, a heredoc fed to a shell) rather than data. A guard that reads
// `unin\stall` as one thing while bash runs `uninstall` is a guard with a hole in it.
//
// ponytail: a reader, not a shell. It knows quotes (`$'…'` included), escapes, $( ),
// backticks, heredocs, comments, redirections and one-word `${…}`; it does not expand
// aliases, functions or arithmetic. Shapes it cannot read come back as null and the caller denies.

import { basename } from "node:path";

/** A redirection operator starting at `lastIndex`. `>(` is process substitution, not a redirect. */
const REDIRECT_OPERATOR = /(?:\{\w+\}|\d+)?(?:&>>?|>>?[|!&]?|<>|<&)(?!\()/y;
const asOperator = (operator: string): string => (operator.includes("<&") ? " < " : " > ");
function redirectAt(text: string, at: number): string | null {
  REDIRECT_OPERATOR.lastIndex = at;
  return REDIRECT_OPERATOR.exec(text)?.[0] ?? null;
}

/** Every redirection operator, spelled as one ` > ` or ` < `, so `>|`, `>!`, `>&`, `&>`,
 *  `&>>`, `>>|` and `{fd}>` reach the same target test and their `|`/`&` stop reading as
 *  command separators. Only where the shell reads an operator: a quoted or escaped `>` is
 *  a character, and spacing it out would turn `\>` into an escaped space and a redirect. */
export function normalizeRedirects(command: string): string {
  return readShell(command).normalized ?? command.replace(new RegExp(REDIRECT_OPERATOR.source, "g"), asOperator);
}

export type ShellSegment = {
  text: string;
  isAfterPipe: boolean;
  opensSubstitution: boolean;
  isProcessSubstitution: boolean;
  /** Heredoc bodies this segment reads on stdin: data to `cat`, code to `bash`. A literal
   *  body (quoted delimiter) is exactly what was written; an unquoted one expands. */
  heredocs: Array<{ body: string; isLiteral: boolean }>;
  /** The first command inside each SUBSTITUTION this segment holds, in order. */
  substitutions: string[];
};

/** The heredoc operator starting at `at` and its delimiter, read as the one shell word bash
 *  reads: quoted parts and unquoted text run together until an unescaped blank or operator,
 *  so in `<<'EOF'#` the delimiter is `EOF#` and that `#` opens no comment. `delimiter` is
 *  the word with quotes removed; any quoting makes the body literal. Null when no word
 *  follows or the word holds something the reader cannot hold (`$'…'`, `$(…)`, a backtick). */
function heredocAt(source: string, at: number): { length: number; delimiter: string; isLiteral: boolean; stripsTabs: boolean } | null {
  const stripsTabs = source[at + 2] === "-";
  let index = at + (stripsTabs ? 3 : 2);
  while (source[index] === " " || source[index] === "\t") index++;
  const wordStart = index;
  let delimiter = "";
  let isLiteral = false;
  while (index < source.length && !/[\s<>|;&()]/.test(source[index]!)) {
    const char = source[index]!;
    if (char === "`" || (char === "$" && /['"({]/.test(source[index + 1] ?? ""))) return null;
    if (char === "\\") {
      if (index + 1 >= source.length) return null;
      delimiter += source[index + 1];
      isLiteral = true;
      index += 2;
    } else if (char === "'" || char === '"') {
      const close = quotedSpanEnd(source, index);
      if (close >= source.length) return null;
      const body = source.slice(index + 1, close);
      delimiter += char === '"' ? body.replace(/\\(["\\$`])/g, "$1") : body;
      isLiteral = true;
      index = close + 1;
    } else {
      delimiter += char;
      index++;
    }
  }
  if (index === wordStart) return null;
  return { length: index - at, delimiter, isLiteral, stripsTabs };
}

/** Where the quoted text, escape or `${…}` starting at `at` ends (its last character), -1
 *  when none starts there, or past the end when it never closes. Inside `$'…'` a backslash
 *  escapes, so `$'\''` is one quote character and not the start of a quoted run. */
export function quotedSpanEnd(text: string, at: number): number {
  const closeOf = (from: number, closer: string, hasEscapes: boolean): number => {
    for (let index = from; index < text.length; index++) {
      if (hasEscapes && text[index] === "\\") index++;
      else if (text[index] === closer) return index;
    }
    return text.length;
  };
  const char = text[at];
  const next = text[at + 1];
  if (char === "\\") return at + 1;
  if (char === "'") return closeOf(at + 1, "'", false);
  if (char === '"' || char === "`") return closeOf(at + 1, char, true);
  if (char === "$" && next === "'") return closeOf(at + 2, "'", true);
  if (char === "$" && next === "{") return closeOf(at + 2, "}", false);
  return -1;
}

/** A `${…}` this reader can hold as one word. Unquoted, `${x:-> --no-verify}` expands to
 *  words and its `>` is no redirect; quoted, a nested quote or command changes where the
 *  word ends. Either way the reader would misjudge it, so it is unreadable. */
function isReadableParameter(body: string, isInDoubleQuotes: boolean): boolean {
  return !(isInDoubleQuotes ? /["`\\(){}]/ : /[\s<>|;&'"`\\(){}]/).test(body);
}

/** The words of `text` as written, split only where the shell splits them: quotes,
 *  escapes and `${…}` stay inside their word, so `"a b">x` is one word, not two. */
export function rawShellWords(text: string): string[] {
  const words: string[] = [];
  let start = -1;
  for (let at = 0; at < text.length; at++) {
    if (/\s/.test(text[at]!)) {
      if (start >= 0) words.push(text.slice(start, at));
      start = -1;
      continue;
    }
    if (start < 0) start = at;
    const end = quotedSpanEnd(text, at);
    if (end >= 0) at = end;
  }
  if (start >= 0) words.push(text.slice(start));
  return words;
}

/** What a `$(…)`, backtick or `<(…)` leaves in the command that contains it: a word whose
 *  value the shell computes. It starts with `$` so every "computed at run time" test sees it. */
export const SUBSTITUTION = "$__SUB__";

/** Shell segments outside quotes, or null when the quoting cannot be read (the shell would
 *  refuse it too, so nothing legitimate is lost). The code inside `$(…)`, backticks and
 *  `<(…)` is its own segment, judged like top-level code; the command around it continues
 *  as one segment with SUBSTITUTION in its place, so `git commit -m "$(…)" --no-verify`
 *  keeps every word. Comments are skipped; an unquoted heredoc that expands is read too.
 *  A redirection operator is read whole, as written. */
export function shellSegments(command: string): ShellSegment[] | null {
  return readShell(command).segments;
}

/** One pass of the grammar: the segments, and the whole command with only the operators
 *  the shell reads respelled (null when the quoting cannot be read). */
function readShell(command: string): { segments: ShellSegment[] | null; normalized: string | null } {
  const segments: ShellSegment[] = [];
  let normalized = "";
  let copiedUpTo = 0;
  type Heredoc = { body: string; isLiteral: boolean };
  type Frame = { quote: string | null; closer: string; parent: string; parentIsAfterPipe: boolean; parentSubstitutions: string[]; parentHeredocs: Heredoc[]; innerStart: number };
  const nesting: Frame[] = [];
  const pending: Array<{ delimiter: string; isLiteral: boolean; stripsTabs: boolean; owner: Heredoc[] }> = [];
  let current = "";
  let quote: string | null = null;
  let isAfterPipe = false;
  let isProcessSubstitution = false;
  let substitutions: string[] = [];
  // The heredocs of the command being read: filled in after the line that declares them.
  let heredocs: Heredoc[] = [];
  const cut = (nextIsAfterPipe = false): void => {
    segments.push({ text: current, isAfterPipe, opensSubstitution: current.includes(SUBSTITUTION), isProcessSubstitution, heredocs, substitutions });
    current = "";
    isAfterPipe = nextIsAfterPipe;
    isProcessSubstitution = false;
    substitutions = [];
    heredocs = [];
  };
  const open = (closer: string): void => {
    nesting.push({ quote, closer, parent: current, parentIsAfterPipe: isAfterPipe, parentSubstitutions: substitutions, parentHeredocs: heredocs, innerStart: segments.length });
    quote = null;
    current = "";
    isAfterPipe = false;
    substitutions = [];
    heredocs = [];
  };
  const close = (): void => {
    cut();
    const frame = nesting.pop()!;
    quote = frame.quote;
    current = frame.parent + SUBSTITUTION;
    isAfterPipe = frame.parentIsAfterPipe;
    heredocs = frame.parentHeredocs;
    // Only a one-command substitution is recorded: a pipeline's output is not its first command's.
    const isSingleCommand = segments.length - frame.innerStart === 1;
    substitutions = [...frame.parentSubstitutions, isSingleCommand ? segments[frame.innerStart]!.text.trim() : ""];
  };
  const source = command.replace(/\\\r?\n/g, "");
  // Whether the next character begins a word: only there does `#` open a comment, so the
  // `#` of `a\ #` (an escaped space, still inside the word) is a character, as in bash.
  let isWordStart = true;
  for (let index = 0; index < source.length; index++) {
    const char = source[index]!;
    const next = source[index + 1];
    const wasWordStart = isWordStart;
    isWordStart = false;
    if (quote === "'") {
      if (char === "'") quote = null;
      current += char;
    } else if (char === "\\") {
      current += char + (next ?? "");
      index++;
    } else if (char === "$" && ((next === "'" && quote === null) || next === "{")) {
      const end = quotedSpanEnd(source, index);
      if (end >= source.length) return UNREADABLE;
      if (next === "{" && !isReadableParameter(source.slice(index + 2, end), quote === '"')) return UNREADABLE;
      current += source.slice(index, end + 1);
      index = end;
    } else if (char === "$" && next === "(") {
      open(")");
      isWordStart = true;
      index++;
    } else if (char === "`") {
      if (quote === null && nesting.at(-1)?.closer === "`") {
        close();
      } else {
        open("`");
        isWordStart = true;
      }
    } else if (quote === '"') {
      if (char === '"') quote = null;
      current += char;
    } else if (char === "'" || char === '"') {
      quote = char;
      current += char;
    } else if ((char === "<" || char === ">") && next === "(") {
      open(")");
      isProcessSubstitution = true;
      isWordStart = true;
      index++;
    } else if (char === "#" && wasWordStart) {
      while (index + 1 < source.length && source[index + 1] !== "\n") index++;
    } else if (char === "<" && next === "<" && source[index + 2] === "<") {
      // A here-string is one word of data, not a heredoc.
      current += "<<<";
      isWordStart = true;
      index += 2;
    } else if (char === "<" && next === "<") {
      const heredoc = heredocAt(source, index);
      if (heredoc === null) return UNREADABLE;
      pending.push({ delimiter: heredoc.delimiter, isLiteral: heredoc.isLiteral, stripsTabs: heredoc.stripsTabs, owner: heredocs });
      current += source.slice(index, index + heredoc.length);
      isWordStart = true;
      index += heredoc.length - 1;
    } else if (redirectAt(source, index) !== null) {
      const operator = redirectAt(source, index)!;
      // `2>&1` copies a descriptor. Respelled ` > 1` it would read as a write to a file named
      // 1, so the descriptor is spelled as the file it is: /dev/fd/1. A redirect right after
      // it (`2>&1>file`) is a redirect of its own, so `<` and `>` end the descriptor too.
      const descriptor = operator.endsWith("&") ? /^(?:\d+|-)(?=$|[\s;&|)<>])/.exec(source.slice(index + operator.length))?.[0] : undefined;
      normalized += source.slice(copiedUpTo, index) + asOperator(operator) + (descriptor === undefined ? "" : `/dev/fd/${descriptor}`);
      copiedUpTo = index + operator.length + (descriptor?.length ?? 0);
      // Read whole, so the `|` of `>|` or the `&` of `>&` never cuts the command.
      current += operator;
      isWordStart = true;
      index += operator.length - 1;
    } else if (char === "\n" && pending.length > 0) {
      cut();
      isWordStart = true;
      for (const heredoc of pending.splice(0)) {
        const bodyStart = index + 1;
        let lineStart = bodyStart;
        let bodyEnd = source.length;
        for (;;) {
          const lineEnd = source.indexOf("\n", lineStart);
          const line = source.slice(lineStart, lineEnd < 0 ? source.length : lineEnd);
          if ((heredoc.stripsTabs ? line.replace(/^\t+/, "") : line) === heredoc.delimiter) {
            bodyEnd = lineStart;
            index = (lineEnd < 0 ? source.length : lineEnd) - 1;
            break;
          }
          if (lineEnd < 0) {
            index = source.length - 1;
            break;
          }
          lineStart = lineEnd + 1;
        }
        const body = source.slice(bodyStart, bodyEnd);
        heredoc.owner.push({ body, isLiteral: heredoc.isLiteral });
        if (!heredoc.isLiteral && /\$\(|`/.test(body)) {
          const expanded = shellSegments(body.replace(/['"]/g, " "));
          if (expanded === null) return UNREADABLE;
          segments.push(...expanded);
        }
      }
    } else if (char === "|") {
      const isOr = next === "|";
      if (isOr || next === "&") index++;
      cut(!isOr);
      isWordStart = true;
    } else if (char === ")" && nesting.at(-1)?.closer === ")") {
      close();
    } else if (";&\n()".includes(char)) {
      if (char === "&" && next === "&") index++;
      cut();
      isWordStart = true;
    } else {
      current += char;
      isWordStart = /\s/.test(char);
    }
  }
  cut();
  if (quote !== null || nesting.length > 0) return UNREADABLE;
  return { segments, normalized: normalized + source.slice(copiedUpTo) };
}
const UNREADABLE = { segments: null, normalized: null };

/** Words the shell reads as grammar where a command name would stand: `{ git …; }`,
 *  `! git …`, `if git …`, `do git …`. `for`, `select` and `case` are not here: the words
 *  after them are a name and a list, never a command, so they stand as the name. */
export const RESERVED_WORDS = new Set(["!", "{", "}", "if", "then", "elif", "else", "fi", "do", "done", "while", "until", "esac", "coproc"]);

/** Commands that run the command after them (`nice -n 5 git …`, `sudo -u x rm …`). */
export const COMMAND_PREFIXES = new Set(["sudo", "doas", "command", "builtin", "exec", "env", "nohup", "time", "nice", "xargs", "timeout", "stdbuf", "busybox"]);

/** Prefix options that take the next word as their value (`xargs -a list rm`). */
const PREFIX_VALUE_OPTIONS: Record<string, RegExp> = {
  xargs: /^-[0-9A-Za-z]*[aIiLlnsPEed]$/,
  sudo: /^-[A-Za-z]*[ugCDhpRrT]$/,
  doas: /^-[A-Za-z]*[uC]$/,
  env: /^-[A-Za-z]*[uCS]$/,
  nice: /^-n$/,
  timeout: /^-[sk]$/,
  stdbuf: /^-[ioe]$/,
  exec: /^-a$/,
};

/** Where the command name of `words` stands, from `start`: past reserved words, `NAME=value`
 *  assignments, and run-it-for-me prefixes with their options and values. The one place
 *  every guard asks "which program runs here". `nameOf` reads a word as a program name. */
export function commandIndex(words: readonly string[], nameOf: (word: string) => string = basename, start = 0): number {
  let index = start;
  while (index < words.length) {
    const word = words[index]!;
    if (RESERVED_WORDS.has(word) || /^[A-Za-z_]\w*=/.test(word)) {
      index++;
      continue;
    }
    const prefix = nameOf(word);
    if (!COMMAND_PREFIXES.has(prefix)) return index;
    index++;
    while (index < words.length && /^(?:-|[A-Za-z_]\w*=|\d+(?:\.\d+)?[smhd]?$)/.test(words[index]!)) {
      index += PREFIX_VALUE_OPTIONS[prefix]?.test(words[index]!) ? 2 : 1;
    }
  }
  return index;
}

export type ShellWord = {
  value: string;
  isQuoted: boolean;
  isOperator: boolean;
  /** The characters the shell reads unquoted: where `$x`, `*` and `{a,b}` split or expand. */
  unquoted: string;
};

const ANSI_ESCAPES: Record<string, string> = { n: "\n", t: "\t", r: "\r", "\\": "\\", "'": "'", '"': '"', e: "\x1b", a: "\x07", "0": "\0" };

/** The words of one segment as the shell hands them to the program: quotes removed,
 *  escapes applied, `$'…'` decoded, and `<`/`>` runs split off as operators. */
export function shellWords(text: string): ShellWord[] {
  const words: ShellWord[] = [];
  let value = "";
  let unquoted = "";
  let isQuoted = false;
  let hasWord = false;
  const end = (): void => {
    if (hasWord) words.push({ value, isQuoted, isOperator: false, unquoted });
    value = "";
    unquoted = "";
    isQuoted = false;
    hasWord = false;
  };
  for (let index = 0; index < text.length; index++) {
    const char = text[index]!;
    const next = text[index + 1];
    if (/\s/.test(char)) {
      end();
    } else if (char === "<" || char === ">") {
      end();
      let operator = char;
      while (text[index + 1] === "<" || text[index + 1] === ">") operator += text[++index];
      words.push({ value: operator, isQuoted: false, isOperator: true, unquoted: operator });
    } else if (char === "\\") {
      value += next ?? "";
      hasWord = true;
      isQuoted = true;
      index++;
    } else if (char === "$" && next === "{") {
      const close = Math.min(quotedSpanEnd(text, index), text.length - 1);
      value += text.slice(index, close + 1);
      unquoted += text.slice(index, close + 1);
      hasWord = true;
      index = close;
    } else if (char === "'" || (char === "$" && next === "'")) {
      const isAnsi = char === "$";
      const close = quotedSpanEnd(text, index);
      const body = text.slice(index + (isAnsi ? 2 : 1), close);
      value += isAnsi
        ? body.replace(/\\x([0-9a-fA-F]{1,2})|\\([0-7]{1,3})|\\(.)/g, (_all, hex: string, octal: string, other: string) =>
          hex ? String.fromCharCode(parseInt(hex, 16)) : octal ? String.fromCharCode(parseInt(octal, 8)) : ANSI_ESCAPES[other] ?? other)
        : body;
      hasWord = true;
      isQuoted = true;
      index = close;
    } else if (char === '"' || (char === "$" && next === '"')) {
      let cursor = index + (char === "$" ? 2 : 1);
      while (cursor < text.length && text[cursor] !== '"') {
        if (text[cursor] === "\\" && /["\\$`]/.test(text[cursor + 1] ?? "")) cursor++;
        value += text[cursor];
        cursor++;
      }
      hasWord = true;
      isQuoted = true;
      index = cursor;
    } else {
      value += char;
      unquoted += char;
      hasWord = true;
    }
  }
  end();
  return words;
}

/** The command with quoting and escapes removed, for pattern checks that must not be
 *  defeated by `--no-ver''ify` or `\-\-no-verify`. */
export function unquoteShell(command: string): string {
  return shellWords(command.replace(/\\\r?\n/g, "")).map((word) => word.value).join(" ");
}

/** What `$(echo …)` or `$(printf …)` with literal words prints, or null when that cannot be
 *  known from the text. Lets `sort -o "$(printf .git/hooks/x)"` be judged by its real target. */
function staticOutput(inner: string): string | null {
  const words = shellWords(inner);
  if (words.length === 0 || words.some((word) => word.isOperator || /[$`]/.test(word.value))) return null;
  const [verb, ...args] = words.map((word) => word.value);
  let output: string;
  if (verb === "echo") {
    while (/^-[neE]+$/.test(args[0] ?? "")) args.shift();
    output = args.join(" ");
  } else if (verb === "printf" && args.length > 0) {
    const [format, ...values] = args;
    output = values.length === 0 ? format! : format!.replace(/%s/g, () => values.shift() ?? "");
    output = output.replace(/\\n$/, "");
  } else {
    return null;
  }
  return /["'\\$`\n]/.test(output) ? null : output;
}

/** A segment's text with each simple echo/printf substitution replaced by what it prints. */
export function resolveSubstitutions(segment: ShellSegment): string {
  let index = 0;
  return segment.text.replace(/\$__SUB__/g, () => staticOutput(segment.substitutions[index++] ?? "") ?? SUBSTITUTION);
}
