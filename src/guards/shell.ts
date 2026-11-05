// Just enough of the POSIX shell grammar to read a command the way the shell will: where
// one command ends, what each word is once quotes and escapes are gone, and which text is
// code (substitutions, a heredoc fed to a shell) rather than data. A guard that reads
// `unin\stall` as one thing while bash runs `uninstall` is a guard with a hole in it.
//
// ponytail: a reader, not a shell. It knows quotes, escapes, $( ), backticks, heredocs,
// comments and redirections; it does not expand aliases, functions or arithmetic. Shapes
// it cannot read come back as null and the caller denies.

/** Every redirection operator, spelled as one ` > ` or ` < `, so `>|`, `>!`, `>&`, `&>`,
 *  `&>>`, `>>|` and `{fd}>` reach the same target test and their `|`/`&` stop reading as
 *  command separators. `>(` is left alone: it is process substitution, not a redirect. */
const REDIRECT_OPERATOR = /(?:\{\w+\}|\d+)?(?:&>>?|>>?[|!&]?|<>|<&)(?!\()/g;
export function normalizeRedirects(command: string): string {
  return command.replace(REDIRECT_OPERATOR, (operator) => (operator.includes("<&") ? " < " : " > "));
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

const HEREDOC = /^<<(-?)[ \t]*(\\?)(['"]?)([^\s'"<>|;&()]+)\3/;

/** What a `$(…)`, backtick or `<(…)` leaves in the command that contains it: a word whose
 *  value the shell computes. It starts with `$` so every "computed at run time" test sees it. */
export const SUBSTITUTION = "$__SUB__";

/** Shell segments outside quotes, or null when the quoting cannot be read (the shell would
 *  refuse it too, so nothing legitimate is lost). The code inside `$(…)`, backticks and
 *  `<(…)` is its own segment, judged like top-level code; the command around it continues
 *  as one segment with SUBSTITUTION in its place, so `git commit -m "$(…)" --no-verify`
 *  keeps every word. Comments are skipped; an unquoted heredoc that expands is read too. */
export function shellSegments(command: string): ShellSegment[] | null {
  const segments: ShellSegment[] = [];
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
  for (let index = 0; index < source.length; index++) {
    const char = source[index]!;
    const next = source[index + 1];
    if (quote === "'") {
      if (char === "'") quote = null;
      current += char;
    } else if (char === "\\") {
      current += char + (next ?? "");
      index++;
    } else if (char === "$" && next === "(") {
      open(")");
      index++;
    } else if (char === "`") {
      if (quote === null && nesting.at(-1)?.closer === "`") close();
      else open("`");
    } else if (quote === '"') {
      if (char === '"') quote = null;
      current += char;
    } else if (char === "'" || char === '"') {
      quote = char;
      current += char;
    } else if ((char === "<" || char === ">") && next === "(") {
      open(")");
      isProcessSubstitution = true;
      index++;
    } else if (char === "#" && /(^|\s)$/.test(current)) {
      while (index + 1 < source.length && source[index + 1] !== "\n") index++;
    } else if (char === "<" && next === "<" && source[index + 2] === "<") {
      // A here-string is one word of data, not a heredoc.
      current += "<<<";
      index += 2;
    } else if (char === "<" && next === "<") {
      const heredoc = HEREDOC.exec(source.slice(index));
      if (heredoc === null) return null;
      pending.push({ delimiter: heredoc[4]!, isLiteral: heredoc[2] !== "" || heredoc[3] !== "", stripsTabs: heredoc[1] === "-", owner: heredocs });
      current += heredoc[0];
      index += heredoc[0].length - 1;
    } else if (char === "\n" && pending.length > 0) {
      cut();
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
          if (expanded === null) return null;
          segments.push(...expanded);
        }
      }
    } else if (char === "|") {
      const isOr = next === "|";
      if (isOr || next === "&") index++;
      cut(!isOr);
    } else if (char === ")" && nesting.at(-1)?.closer === ")") {
      close();
    } else if (";&\n()".includes(char)) {
      if (char === "&" && next === "&") index++;
      cut();
    } else {
      current += char;
    }
  }
  cut();
  return quote === null && nesting.length === 0 ? segments : null;
}

export type ShellWord = { value: string; isQuoted: boolean; isOperator: boolean };

const ANSI_ESCAPES: Record<string, string> = { n: "\n", t: "\t", r: "\r", "\\": "\\", "'": "'", '"': '"', e: "\x1b", a: "\x07", "0": "\0" };

/** The words of one segment as the shell hands them to the program: quotes removed,
 *  escapes applied, `$'…'` decoded, and `<`/`>` runs split off as operators. */
export function shellWords(text: string): ShellWord[] {
  const words: ShellWord[] = [];
  let value = "";
  let isQuoted = false;
  let hasWord = false;
  const end = (): void => {
    if (hasWord) words.push({ value, isQuoted, isOperator: false });
    value = "";
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
      words.push({ value: operator, isQuoted: false, isOperator: true });
    } else if (char === "\\") {
      value += next ?? "";
      hasWord = true;
      isQuoted = true;
      index++;
    } else if (char === "'" || (char === "$" && next === "'")) {
      const isAnsi = char === "$";
      let close = text.indexOf("'", index + (isAnsi ? 2 : 1));
      if (isAnsi) {
        while (close > 0 && text[close - 1] === "\\") close = text.indexOf("'", close + 1);
      }
      const body = text.slice(index + (isAnsi ? 2 : 1), close < 0 ? text.length : close);
      value += isAnsi
        ? body.replace(/\\x([0-9a-fA-F]{1,2})|\\([0-7]{1,3})|\\(.)/g, (_all, hex: string, octal: string, other: string) =>
          hex ? String.fromCharCode(parseInt(hex, 16)) : octal ? String.fromCharCode(parseInt(octal, 8)) : ANSI_ESCAPES[other] ?? other)
        : body;
      hasWord = true;
      isQuoted = true;
      index = close < 0 ? text.length : close;
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
