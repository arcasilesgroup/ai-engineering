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
const asOperator = (operator: string): string => (operator.includes("<&") ? " < " : operator.includes("<>") ? " <> " : " > ");
function redirectAt(text: string, at: number): string | null {
  REDIRECT_OPERATOR.lastIndex = at;
  return REDIRECT_OPERATOR.exec(text)?.[0] ?? null;
}

/** Every redirection operator, spelled as one ` > ` or ` < `, so `>|`, `>!`, `>&`, `&>`,
 *  `&>>`, `>>|` and `{fd}>` reach the same target test and their `|`/`&` stop reading as
 *  command separators. Only where the shell reads an operator: a quoted or escaped `>` is
 *  a character, and spacing it out would turn `\>` into an escaped space and a redirect. */
export function normalizeRedirects(command: string): string {
  const read = readShell(command);
  if (read.normalized !== null) return read.normalized;
  // The quoting cannot be read, so the operators are found without it: a `>` inside a
  // quoted span, a `${…}` or after a backslash is a character, never a redirection.
  let out = "";
  let at = 0;
  while (at < command.length) {
    const spanEnd = quotedSpanEnd(command, at);
    if (spanEnd >= 0) {
      out += command.slice(at, spanEnd + 1);
      at = spanEnd + 1;
      continue;
    }
    const operator = redirectAt(command, at);
    if (operator === null) {
      out += command[at];
      at += 1;
      continue;
    }
    out += asOperator(operator);
    at += operator.length;
  }
  return out;
}

export type ShellSegment = {
  text: string;
  isAfterPipe: boolean;
  opensSubstitution: boolean;
  isInSubstitution: boolean;
  isProcessSubstitution: boolean;
  /** Heredoc bodies this segment reads on stdin: data to `cat`, code to `bash`. A literal
   *  body (quoted delimiter) is exactly what was written; an unquoted one expands. */
  heredocs: Array<{ body: string; isLiteral: boolean }>;
  /** The first command inside each SUBSTITUTION this segment holds, in order. */
  substitutions: string[];
  /** Variable-tracking scope id (0 = top-level shell) and the scope it inherits from. */
  scope: number;
  parentScope: number;
  /** Whether this segment stands inside a branch, loop body or `&&`/`||` list, so the
   *  shell may never run it and its assignments decide nothing. */
  isConditional: boolean;
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
  type Frame = {
    kind: "substitution" | "subshell" | "compound";
    quote: string | null;
    closer: string;
    parent: string;
    parentIsAfterPipe: boolean;
    parentSubstitutions: string[];
    parentHeredocs: Heredoc[];
    parentScope: number;
    innerStart: number;
    /** The scope this frame opened; a compound keeps it only if it runs in a subshell. */
    frameScope: number;
    /** A compound that is the right member of a pipeline already runs in its own subshell. */
    isIsolated: boolean;
    /** Whether a branch of this frame is already running, and whether it may never run. */
    isConditionalBase: boolean;
    isConditionalBody: boolean;
  };
  const nesting: Frame[] = [];
  // A compound command runs in the current shell unless a `|` or a `&` follows its closing
  // word, which is known only after the word itself, so it resolves at the next separator.
  const closedCompounds: Frame[] = [];
  const currentShellCompounds = new Map<number, number>();
  const pending: Array<{ delimiter: string; isLiteral: boolean; stripsTabs: boolean; owner: Heredoc[] }> = [];
  const scopeParents = new Map<number, number>([[0, 0]]);
  let scope = 0;
  let nextScope = 0;
  let current = "";
  let quote: string | null = null;
  let isAfterPipe = false;
  let isAfterCondition = false;
  let isProcessSubstitution = false;
  let substitutions: string[] = [];
  // The heredocs of the command being read: filled in after the line that declares them.
  let heredocs: Heredoc[] = [];
  const currentConditional = (): boolean => {
    const frame = nesting.at(-1);
    return isAfterCondition || (frame !== undefined && (frame.isConditionalBase || frame.isConditionalBody));
  };
  const cut = (nextIsAfterPipe = false, isIsolated = false): void => {
    const isolate = isIsolated || isAfterPipe;
    const segScope = isolate ? ++nextScope : scope;
    const segParent = isolate ? scope : (scopeParents.get(scope) ?? 0);
    segments.push({
      text: current,
      isAfterPipe,
      opensSubstitution: current.includes(SUBSTITUTION),
      isInSubstitution: nesting.length > 0,
      isProcessSubstitution,
      heredocs,
      substitutions,
      scope: segScope,
      parentScope: segParent,
      isConditional: currentConditional(),
    });
    current = "";
    isAfterPipe = nextIsAfterPipe;
    isProcessSubstitution = false;
    substitutions = [];
    heredocs = [];
  };
  const open = (closer: string): void => {
    const childScope = ++nextScope;
    scopeParents.set(childScope, scope);
    nesting.push({ kind: "substitution", quote, closer, parent: current, parentIsAfterPipe: isAfterPipe, parentSubstitutions: substitutions, parentHeredocs: heredocs, parentScope: scope, innerStart: segments.length, frameScope: childScope, isIsolated: false, isConditionalBase: currentConditional(), isConditionalBody: false });
    scope = childScope;
    quote = null;
    current = "";
    isAfterPipe = false;
    substitutions = [];
    heredocs = [];
  };
  const openSubshell = (): void => {
    cut();
    const childScope = ++nextScope;
    scopeParents.set(childScope, scope);
    nesting.push({ kind: "subshell", quote: null, closer: ")", parent: "", parentIsAfterPipe: false, parentSubstitutions: [], parentHeredocs: [], parentScope: scope, innerStart: segments.length, frameScope: childScope, isIsolated: false, isConditionalBase: currentConditional(), isConditionalBody: false });
    scope = childScope;
    isAfterCondition = false;
  };
  const openCompound = (closer: string): void => {
    // Read before the cut, which starts the next segment with no pipe behind it.
    const isIsolated = isAfterPipe || isCoprocPrefix(current);
    const isConditionalBase = currentConditional();
    cut();
    const frameScope = ++nextScope;
    scopeParents.set(frameScope, scope);
    nesting.push({ kind: "compound", quote: null, closer, parent: "", parentIsAfterPipe: false, parentSubstitutions: [], parentHeredocs: [], parentScope: scope, innerStart: segments.length, frameScope, isIsolated, isConditionalBase, isConditionalBody: closer === "esac" });
    scope = frameScope;
    isAfterCondition = false;
  };
  const closeCompound = (): void => {
    cut();
    const frame = nesting.pop()!;
    scope = frame.parentScope;
    closedCompounds.push(frame);
  };
  /** What the words already read say about the compounds that just closed: a `|` or a
   *  background `&` puts them in a subshell, and anything else leaves them in this shell. */
  const resolveCompounds = (isIsolated: boolean): void => {
    for (const frame of closedCompounds.splice(0)) {
      if (isIsolated || frame.isIsolated) continue;
      currentShellCompounds.set(frame.frameScope, frame.parentScope);
    }
  };
  const close = (): void => {
    cut();
    const frame = nesting.pop()!;
    scope = frame.parentScope;
    if (frame.kind === "subshell") return;
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
  // Grammar stands where a command starts, never as an argument: in `echo if` the `if` is data.
  const isCommandStart = (): boolean => isCoprocPrefix(current) || isGrammarPrefix(shellWords(current));
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
      cut(isAfterPipe);
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
          const base = ++nextScope;
          let maxInner = 0;
          for (const inner of expanded) {
            if (inner.scope > maxInner) maxInner = inner.scope;
            segments.push({
              ...inner,
              scope: base + inner.scope,
              parentScope: inner.scope === 0 ? scope : base + inner.parentScope,
            });
          }
          nextScope += maxInner;
        }
      }
    } else if (wasWordStart && isCommandStart() && compoundTokenAt(source, index) !== null) {
      const token = compoundTokenAt(source, index)!;
      const closer = COMPOUND_CLOSERS[token];
      if (BODY_WORDS.has(token)) {
        const body = nesting.at(-1);
        if (body !== undefined && body.kind === "compound") body.isConditionalBody = true;
      } else if (closer === undefined) {
        if (nesting.at(-1)?.closer === token) {
          resolveCompounds(false);
          closeCompound();
        }
      } else {
        resolveCompounds(false);
        openCompound(closer);
      }
      current += token;
      index += token.length - 1;
    } else if (char === "|") {
      const isOr = next === "|";
      if (isOr || next === "&") index++;
      resolveCompounds(!isOr);
      cut(!isOr, !isOr);
      if (isOr) isAfterCondition = true;
      isWordStart = true;
    } else if (char === "(") {
      resolveCompounds(false);
      openSubshell();
      isWordStart = true;
    } else if (char === ")" && nesting.at(-1)?.closer === ")") {
      const wasSubshell = nesting.at(-1)!.kind === "subshell";
      resolveCompounds(false);
      close();
      if (wasSubshell) isWordStart = true;
    } else if (";&\n)".includes(char)) {
      const isBackground = char === "&" && next !== "&";
      const isAndOr = char === "&" && next === "&";
      if (isAndOr) index++;
      // `;&` and `;;` fall through a case, they do not put the command behind them in the background.
      resolveCompounds(isBackground && source[index - 1] !== ";");
      // A line that ends on `|` continues the pipeline: the next command is still after a pipe.
      cut(char === "\n" && isAfterPipe, isBackground);
      isAfterCondition = isAndOr;
      isWordStart = true;
    } else {
      current += char;
      isWordStart = /\s/.test(char);
    }
  }
  resolveCompounds(false);
  cut();
  // A compound left open is a syntax error, so bash never runs it: read it as this shell's.
  for (const frame of nesting) if (frame.kind === "compound") currentShellCompounds.set(frame.frameScope, frame.parentScope);
  if (quote !== null || nesting.some((frame) => frame.kind !== "compound")) return UNREADABLE;
  const homeScope = (id: number): number => {
    let scopeId = id;
    while (currentShellCompounds.has(scopeId)) scopeId = currentShellCompounds.get(scopeId)!;
    return scopeId;
  };
  for (const segment of segments) {
    segment.scope = homeScope(segment.scope);
    segment.parentScope = homeScope(segment.parentScope);
  }
  return { segments, normalized: normalized + source.slice(copiedUpTo) };
}
const UNREADABLE = { segments: null, normalized: null };

/** Words the shell reads as grammar where a command name would stand: `{ git …; }`,
 *  `! git …`, `if git …`, `do git …`. `for`, `select` and `case` are not here: the words
 *  after them are a name and a list, never a command, so they stand as the name. */
export const RESERVED_WORDS = new Set(["!", "{", "}", "if", "then", "elif", "else", "fi", "do", "done", "while", "until", "esac", "coproc"]);

/** The word that closes each compound command. Bash runs the compound in the current shell
 *  unless a `|` or a background `&` puts it in a subshell, so where its assignments land
 *  depends on the operator after its closing word, not on the compound itself. */
const COMPOUND_CLOSERS: Record<string, string> = { "{": "}", if: "fi", while: "done", until: "done", for: "done", select: "done", case: "esac" };
/** Every word that opens or ends a compound command. */
const COMPOUND_WORDS = new Set([...Object.keys(COMPOUND_CLOSERS), ...Object.values(COMPOUND_CLOSERS)]);

/** Words that open a branch a compound may never run: `then`, an `elif`/`else` alternative
 *  and a `do` loop body. */
const BODY_WORDS = new Set(["then", "elif", "else", "do"]);

/** The compound keyword or brace starting at `at` of `source`, as the shell words it: the
 *  longest run of letters that ends the word, so `iffy` is a name and `if` is grammar. */
function compoundTokenAt(source: string, at: number): string | null {
  const token = /^[a-z]{1,6}|^[{}]/.exec(source.slice(at, at + 7))?.[0];
  if (token === undefined || !(COMPOUND_WORDS.has(token) || BODY_WORDS.has(token))) return null;
  const after = source[at + token.length];
  return after === undefined || /[\s;&|()<>]/.test(after) ? token : null;
}

/** `coproc { …; }` and `coproc name { …; }` run the compound in a subshell, as `&` would. */
function isCoprocPrefix(text: string): boolean {
  return /^\s*coproc(?:\s+[A-Za-z_]\w*)?\s*$/.test(text);
}

/** Grammar standing where a command starts rather than being it: a reserved word, bash's
 *  `time` keyword, and the `-p` that may follow it. Each runs the words after it in this shell. */
function isGrammarAt(words: readonly ShellWord[], at: number): boolean {
  const word = words[at]!;
  if (word.isQuoted || word.isOperator) return false;
  if (RESERVED_WORDS.has(word.value) || word.value === "time") return true;
  const before = words[at - 1];
  return word.value === "-p" && before !== undefined && !before.isQuoted && before.value === "time";
}

/** Whether every word of `words` is grammar in front of a command, so a keyword after it starts one. */
function isGrammarPrefix(words: readonly ShellWord[]): boolean {
  return words.every((_word, at) => isGrammarAt(words, at));
}

/** Commands that run the command after them (`nice -n 5 git …`, `sudo -u x rm …`). */
export const COMMAND_PREFIXES = new Set(["sudo", "doas", "command", "builtin", "exec", "env", "nohup", "time", "nice", "xargs", "timeout", "stdbuf", "busybox"]);

/** Prefix options that take the next word as their value (`xargs -a list rm`). */
const PREFIX_VALUE_OPTIONS: Record<string, RegExp> = {
  xargs: /^-[0-9A-Za-z]*[aIiLlnsPEed]$/,
  sudo: /^-[A-Za-z]*[ugCDhpRrT]$/,
  doas: /^-[A-Za-z]*[uC]$/,
  env: /^(?:-[A-Za-z]*[uCS]|--(?:split-string|unset|chdir))$/,
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
    if (RESERVED_WORDS.has(word) || /^[A-Za-z_]\w*\+?=/.test(word)) {
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
  /** The word exactly as written, quotes and escapes kept: a path token keeps the spelling
   *  the guard has to judge, and the verb word keeps the spelling it cannot decode. */
  original: string;
};

/** A word the shell expands before the program sees it: an unquoted glob or brace. */
export const GLOB_CHARS = /[*?[]/;

/** Commands that print the bytes of the files they name, so reading one is how a payload
 *  reaches the model. Every guard that asks "what does this command read" asks here. */
const FILE_CONTENT_READERS = new Set([
  "cat", "bat", "tac", "nl", "head", "tail", "less", "more", "strings", "xxd", "od",
  "sed", "awk", "grep", "rg", "zgrep", "zcat", "sort", "uniq", "cut", "tr", "column",
  "diff", "jq", "yq",
]);

/** Commands whose operands they only read. Wider than the printers above because naming a
 *  governed path with `test`, `cd` or `stat` writes nothing either. A command here that can
 *  also write through a flag is not a reader; `WRITE_FLAGS` holds those flags. */
const OPERAND_READERS = new Set([
  "cat", "less", "more", "head", "tail", "grep", "egrep", "fgrep", "rg", "ag", "wc", "diff", "cmp", "ls", "stat",
  "file", "sha256sum", "sha1sum", "sha512sum", "shasum", "md5", "md5sum", "cksum", "test", "[", "[[", "echo",
  "printf", "realpath", "readlink", "basename", "dirname", "jq", "nl", "od", "hexdump", "strings", "du", "bat",
  "tree", "cd", "pushd", "popd",
  // PowerShell readers (case-insensitive: names are compared lowercased)
  "get-content", "gc", "type", "select-string", "sls", "test-path", "get-item", "gi", "get-childitem", "gci",
  "dir", "resolve-path", "write-output", "write-host",
]);

/** A long output option always writes, whatever the command is. */
const OUTPUT_OPTION = /^--(?:output|out|output-document|outfile|log-file)(?:=|$)/;

/** The flags that turn a reader into a writer: `sed -i`, `awk -i inplace`, `sort -o`. */
const WRITE_FLAGS: Record<string, RegExp> = { sed: /^-[A-Za-z]*i/, awk: /^-[A-Za-z]*i/, sort: /^-[A-Za-z]*o/ };

/** Whether `name` prints the bytes of its file arguments into the reader's context. `-i`
 *  rewrites the file instead, so an in-place `sed`/`awk` reads nothing. */
export function printsFileContent(name: string, args: readonly string[]): boolean {
  if (!FILE_CONTENT_READERS.has(name)) return false;
  return !(args.some((arg) => OUTPUT_OPTION.test(arg)) || args.some((arg) => WRITE_FLAGS[name]?.test(arg) ?? false));
}

/** Whether `name` only reads the paths it names, so a governed path in its arguments is
 *  not a write to it. The guard that judges writes asks this; the printers above are a
 *  subset of it, and both tables live here so a new command is added once. */
export function readsOperandsOnly(name: string, args: readonly string[]): boolean {
  if (!OPERAND_READERS.has(name)) return false;
  if (args.some((arg) => OUTPUT_OPTION.test(arg))) return false;
  return !args.some((arg) => WRITE_FLAGS[name]?.test(arg) ?? false);
}

const ANSI_ESCAPES: Record<string, string> = { n: "\n", t: "\t", r: "\r", "\\": "\\", "'": "'", '"': '"', e: "\x1b", a: "\x07", "0": "\0" };

/** The words of one segment as the shell hands them to the program: quotes removed,
 *  escapes applied, `$'…'` decoded, and `<`/`>` runs split off as operators. */
/** The operands of `python3 -m json.tool …`, or null for any other command. A bare `-`
 *  is an operand (stdin), everything after `--` is an operand, and `--indent` takes the
 *  next word as its value. With one operand json.tool only reads it; a second is written. */
export function jsonToolOperands(words: readonly string[]): string[] | null {
  const [name, flag, module, ...rest] = words;
  if (!/^(?:.*\/)?python3?$/.test(name ?? "") || flag !== "-m" || module !== "json.tool") return null;
  const operands: string[] = [];
  for (let index = 0; index < rest.length; index += 1) {
    const word = rest[index]!;
    if (word === "--") return [...operands, ...rest.slice(index + 1)];
    const isOption = word.length > 1 && word.startsWith("-");
    if (!isOption) operands.push(word);
    if (word === "--indent") index += 1;
  }
  return operands;
}

export function shellWords(text: string): ShellWord[] {
  const words: ShellWord[] = [];
  let value = "";
  let unquoted = "";
  let isQuoted = false;
  let hasWord = false;
  let start = 0;
  const end = (stop: number): void => {
    if (hasWord) words.push({ value, isQuoted, isOperator: false, unquoted, original: text.slice(start, stop) });
    value = "";
    unquoted = "";
    isQuoted = false;
    hasWord = false;
  };
  for (let index = 0; index < text.length; index++) {
    const char = text[index]!;
    const next = text[index + 1];
    if (!hasWord) start = index;
    if (/\s/.test(char)) {
      end(index);
    } else if (char === "<" || char === ">") {
      end(index);
      let operator = char;
      while (text[index + 1] === "<" || text[index + 1] === ">") operator += text[++index];
      words.push({ value: operator, isQuoted: false, isOperator: true, unquoted: operator, original: operator });
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
  end(text.length);
  return words;
}

/** Words with every redirection operator and its target dropped, as the shell hands them to a program. */
export function stripRedirectWords(words: readonly ShellWord[]): ShellWord[] {
  const kept: ShellWord[] = [];
  for (let at = 0; at < words.length; at++) {
    if (words[at]!.isOperator) {
      at++;
      continue;
    }
    kept.push(words[at]!);
  }
  return kept;
}

/** Every redirection form, one spelling. `<>`, `<<<`, `<<-`, `&>>`, `2>f`, `{fd}>`, `>|`
 *  and `>&` are all this grammar, and a guard that has a word it never parsed asks here
 *  instead of carrying a regular expression of its own. */
const REDIRECT_FORM = /(?:\{\w+\}|\d+)?(?:&>>?|>>?[|!&]?|<>|<{1,3}|<&)(?!\()/;

/** Where a redirection starts in `word` the guard has not parsed, and the part of the word
 *  it covers: `f>x` is a word and a redirect, `>f` is an operator and its file. */
export function findRedirect(word: string): { index: number; operator: string; attached: string } | null {
  const found = REDIRECT_FORM.exec(word);
  if (found === null) return null;
  return { index: found.index, operator: found[0], attached: word.slice(found.index + found[0].length) };
}

/** One redirection the shell reads: the operator as written, and the word naming the file
 *  it reads or writes (`null` when nothing follows, as in `echo x >`). */
export type ShellRedirect = { operator: string; target: ShellWord | null };

/** Whether a redirection target names a file this session creates: not a descriptor copy
 *  (`&1`, `&-`), not a bare descriptor number, and not a device. */
function isFileTarget(target: ShellWord | null): target is ShellWord {
  return target !== null
    && !target.isOperator
    && target.value !== "-"
    && !/^\d+$/.test(target.value)
    && !target.value.startsWith("&")
    && !target.value.startsWith("/dev/");
}

/** The words a program receives, and every redirection read out as operator + target. One
 *  pass over one word list, so a guard never needs a redirection regex of its own. */
function readRedirects(words: readonly ShellWord[]): { plain: ShellWord[]; redirects: ShellRedirect[] } {
  const plain: ShellWord[] = [];
  const redirects: ShellRedirect[] = [];
  for (let at = 0; at < words.length; at++) {
    const word = words[at]!;
    if (!word.isOperator) {
      plain.push(word);
      continue;
    }
    // The word after an operator belongs to it, exactly as stripRedirectWords reads it.
    const next = words[at + 1];
    redirects.push({ operator: word.value, target: next ?? null });
    at++;
  }
  return { plain, redirects };
}

/** One command as the shell runs it: the single model every guard is a predicate over.
 *  Where the program name stands, the words it receives, the files its redirections name,
 *  and whether the shell expands each argument. */
export type ShellCommand = {
  /** The segment this command came from: pipes, substitutions, heredocs and scope. */
  segment: ShellSegment;
  /** Every word of the segment, redirection operators included, as the shell hands them over. */
  words: ShellWord[];
  /** `words` without the redirection operators and the words they name. */
  plain: ShellWord[];
  redirects: ShellRedirect[];
  /** Where the program name stands in `plain`, past `NAME=value` and wrappers like `sudo`.
   *  Equal to `plain.length` when the segment runs no program. */
  verbIndex: number;
  /** The program's name, the basename of its word, or "" when nothing runs. */
  verb: string;
  /** The words the program receives after its name. */
  args: ShellWord[];
  /** The files an output redirect creates: no descriptor copies, no devices. */
  writes: ShellWord[];
  /** The files an input redirect reads: a heredoc's delimiter and a here-string's text
   *  name none, and a descriptor copy or a device is no file to read. */
  reads: ShellWord[];
  /** Whether the shell expands each of `args`: an unquoted glob, brace or `$name`. */
  isArgExpanded: boolean[];
};

/** One segment as a typed command. `text` is the segment as the shell would hand it over:
 *  the caller passes a substitution-resolved or variable-expanded form when it wants the
 *  program's own view rather than the line as written. */
export function commandOf(segment: ShellSegment, text: string = segment.text): ShellCommand {
  // Nothing to respell: a segment with no redirection and no continued line reaches the
  // program exactly as the reader handed it over, so it is not parsed a second time.
  const words = /[<>]/.test(text) || /\\\r?\n/.test(text) ? shellWords(normalizeRedirects(text)) : shellWords(text);
  return withWords(segment, words);
}

/** One segment as a typed command over a word list the caller has already resolved: the
 *  guard that follows `$name` through a line substitutes each word and asks again, instead
 *  of tokenising the line a second time. */
export function withWords(segment: ShellSegment, words: readonly ShellWord[]): ShellCommand {
  const { plain, redirects } = readRedirects(words);
  const verbIndex = commandIndex(plain.map((word) => word.value));
  const writes = redirects.flatMap(({ operator, target }) => (operator.startsWith(">") && isFileTarget(target) ? [target] : []));
  const reads = redirects.flatMap(({ operator, target }) => ((operator === "<" || operator === "<>") && isFileTarget(target) ? [target] : []));
  const args = plain.slice(verbIndex + 1);
  return {
    segment,
    words: [...words],
    plain,
    redirects,
    verbIndex,
    verb: basename(plain[verbIndex]?.value ?? ""),
    args,
    writes,
    reads,
    isArgExpanded: args.map((word) => GLOB_CHARS.test(word.unquoted) || /\{[^}]*,/.test(word.unquoted)),
  };
}

/** One parse of the whole line into typed commands, or null when the quoting cannot be
 *  read. Every guard reads a command through this and judges the model; none of them
 *  tokenises the line a second time. */
export function readCommands(command: string): ShellCommand[] | null {
  const segments = shellSegments(command);
  return segments === null ? null : segments.map((segment) => commandOf(segment));
}

/** One command read from text whose quoting the reader cannot resolve: the words it can
 *  see, judged as a single command. A guard that cannot read the line whole still judges
 *  what it can see rather than passing it. */
function readCommandLenient(text: string, isAfterPipe = false): ShellCommand {
  return commandOf({
    text,
    isAfterPipe,
    opensSubstitution: false,
    isInSubstitution: false,
    isProcessSubstitution: false,
    heredocs: [],
    substitutions: [],
    scope: 0,
    parentScope: 0,
    isConditional: false,
  }, text);
}

/** One lenient command per piece of a text the reader could not read whole, cut where the
 *  shell cuts a command: a newline, `;`, `&&`, `||`, a background `&` end one, and a `|`
 *  starts the next stage of the pipeline. */
export function readCommandsLenient(text: string): ShellCommand[] {
  const pieces = text.split(/(\|\||&&|\|&|\||;|(?<![<>])&(?!>)|\r?\n)/);
  const commands: ShellCommand[] = [];
  for (let index = 0; index < pieces.length; index += 2) {
    const piece = pieces[index]!;
    if (piece.trim().length === 0) continue;
    const separator = pieces[index - 1];
    commands.push(readCommandLenient(piece, separator === "|" || separator === "|&"));
  }
  return commands;
}

/** The argument words of one normalized segment, with redirections and their targets stripped. */
export function argumentWords(text: string): ShellWord[] {
  return stripRedirectWords(shellWords(text));
}

/** The words an output redirect writes to as a file: not `2>&1` or `>&-`, which copy or
 *  close a descriptor (the `&` stays on the target word), and not a `/dev/` device. */
export function fileRedirectTargets(words: readonly ShellWord[]): ShellWord[] {
  const targets: ShellWord[] = [];
  for (let index = 0; index < words.length; index++) {
    const word = words[index]!;
    if (!word.isOperator || !word.value.includes(">") || word.value.includes("&")) continue;
    const target = words[index + 1];
    if (target === undefined || target.isOperator) continue;
    if (/^\d+$/.test(target.value) || target.value === "-" || target.value.startsWith("&") || target.value.startsWith("/dev/")) continue;
    targets.push(target);
  }
  return targets;
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

const INLINE_SHELLS = new Set(["sh", "bash", "zsh", "dash", "ksh", "mksh", "ash", "fish"]);
/** Verbs whose words are a program of their own: PowerShell and cmd spell the flag their
 *  own way, and `eval` takes its whole remainder as the program. */
const PROGRAM_VERBS = new Set(["pwsh", "powershell", "cmd", "eval"]);
const PROGRAM_FLAG = /^(?:-[A-Za-z]*c[A-Za-z]*|-[Cc]ommand|\/[ck])$/;

/** The program one verb hands to an interpreter, or null when its words carry none. A
 *  POSIX shell receives its program as a single word; PowerShell, cmd and eval receive
 *  the rest of their line. */
function inlineProgram(name: string, rest: readonly string[]): string | null {
  if (name === "eval") {
    const program = rest.filter((word) => word !== "--").join(" ");
    return program.length === 0 ? null : program;
  }
  const flag = rest.findIndex((word) => PROGRAM_FLAG.test(word));
  if (flag < 0) return null;
  const after = rest.slice(flag + 1);
  const program = INLINE_SHELLS.has(name) ? (after[0] === "--" ? after[1] : after[0]) : after.join(" ");
  return program === undefined || program.length === 0 ? null : program;
}

/** Every program `command` hands to an interpreter (`sh -c '…'`, `pwsh -Command '…'`,
 *  `cmd /c '…'`, `eval '…'`), including ones nested inside those programs. The words come
 *  from the same reader the guards already share, so a quoted program is one word and not a
 *  second grammar. Empty when the line cannot be read. */
export function inlineShellPrograms(command: string): string[] {
  const found: string[] = [];
  const visit = (text: string, depth: number): void => {
    if (depth > 3) return;
    const segments = shellSegments(text);
    if (segments === null) return;
    for (const segment of segments) {
      const words = shellWords(segment.text).filter((word) => !word.isOperator).map((word) => word.value);
      const at = commandIndex(words);
      const name = basename(words[at] ?? "");
      if (!INLINE_SHELLS.has(name) && !PROGRAM_VERBS.has(name)) continue;
      const body = inlineProgram(name, words.slice(at + 1));
      if (body === null) continue;
      found.push(body);
      visit(body, depth + 1);
    }
  };
  visit(command, 0);
  return found;
}

/** A value that can replace `$name` without becoming a new command. */
function isSafeExpansion(value: string): boolean {
  return value.length > 0 && !/[\s;&|`$<>\\'",(){}]/.test(value);
}

/** `$name` and `${name}` outside single quotes, using `variables` as they stand now. */
function expandDollars(text: string, variables: ReadonlyMap<string, string | null>): string {
  let out = "";
  let quote: "'" | '"' | null = null;
  for (let index = 0; index < text.length; index++) {
    const char = text[index]!;
    if (quote === "'") {
      out += char;
      if (char === "'") quote = null;
      continue;
    }
    if (char === "\\" && quote === null) {
      out += char + (text[index + 1] ?? "");
      index++;
      continue;
    }
    if (char === "'") {
      quote = "'";
      out += char;
      continue;
    }
    if (char === '"') {
      quote = quote === '"' ? null : '"';
      out += char;
      continue;
    }
    const match = char === "$" ? /^\$\{([A-Za-z_]\w*)\}|^\$([A-Za-z_]\w*)/.exec(text.slice(index)) : null;
    const name = match?.[1] ?? match?.[2];
    const value = name === undefined ? undefined : variables.get(name);
    if (match !== null && typeof value === "string" && isSafeExpansion(value)) {
      out += value;
      index += match[0].length - 1;
      continue;
    }
    out += char;
  }
  return out;
}

const ASSIGNMENT_BUILTINS = new Set(["export", "declare", "typeset", "local", "readonly"]);

export type VariableMap = Map<string, string | null>;
export type VariableScope = Map<number, VariableMap>;

export function createVariableScope(initial?: Iterable<[string, string]>): VariableScope {
  return new Map([[0, new Map<string, string | null>(initial)]]);
}

export function variablesForSegment(scopes: VariableScope, segment: ShellSegment): VariableMap {
  let table = scopes.get(segment.scope);
  if (table === undefined) {
    const parent = scopes.get(segment.parentScope) ?? scopes.get(0)!;
    table = new Map(parent);
    scopes.set(segment.scope, table);
  }
  return table;
}

/** `$name` and `${name}` in `value`, from the values known now; unknown names stay as written. */
export function substituteVariables(value: string, variables: ReadonlyMap<string, string | null>): string {
  return value.replace(/\$\{([A-Za-z_]\w*)\}|\$([A-Za-z_]\w*)/g, (all, braced: string | undefined, bare: string | undefined) => {
    const found = variables.get(braced ?? bare ?? "");
    return typeof found === "string" ? found : all;
  });
}

function assign(variables: VariableMap, name: string, raw: string, isAppend: boolean, requireSafe: boolean, isConditional: boolean): void {
  const rhs = substituteVariables(raw, variables);
  const prior = variables.get(name);
  if (isAppend && prior === null) return;
  const value = isAppend ? `${prior ?? ""}${rhs}` : rhs;
  if (isConditional || /[$`]/.test(value) || (requireSafe && value.length > 0 && !isSafeExpansion(value))) variables.set(name, null);
  else variables.set(name, value);
}

/** What this segment leaves in `variables` once it has run, so it is applied after the
 *  segment's own words are expanded. `f=x` alone and `export f=x` stay set. A prefix
 *  `f=x cmd` is only cmd's environment: cmd's words still see the old value and the next
 *  segment does too, whatever cmd is (`f=x :` and `f=x export` keep the earlier value in
 *  bash and zsh, the shells the floor runs). With `requireSafe`, a value that could not
 *  stand in the text as one word drops the name. A segment that only runs when a condition
 *  holds cannot decide a name the rest of the command reads, so its names stay unknown. */
export function applySegmentAssignments(text: string, variables: VariableMap, requireSafe: boolean, isConditional = false): void {
  const words = shellWords(normalizeRedirects(text));
  const prefix: Array<[string, string, boolean]> = [];
  let commandAt = -1;
  for (let index = 0; index < words.length; index++) {
    const word = words[index]!;
    if (word.isOperator) {
      index++;
      continue;
    }
    if (prefix.length === 0 && isGrammarAt(words, index)) continue;
    const assignment = /^[A-Za-z_]\w*\+?=/.test(word.unquoted) ? /^([A-Za-z_]\w*)(\+?)=(.*)$/s.exec(word.value) : null;
    if (assignment === null) {
      commandAt = index;
      break;
    }
    prefix.push([assignment[1]!, assignment[3]!, assignment[2] === "+"]);
  }
  if (commandAt < 0) {
    for (const [name, raw, isAppend] of prefix) assign(variables, name, raw, isAppend, requireSafe, isConditional);
    return;
  }
  const command = basename(words[commandAt]!.value);
  if (!ASSIGNMENT_BUILTINS.has(command)) return;
  for (let index = commandAt + 1; index < words.length; index++) {
    const word = words[index]!;
    if (word.isOperator) {
      index++;
      continue;
    }
    const assignment = /^([A-Za-z_]\w*)(\+?)=(.*)$/s.exec(word.value);
    if (assignment !== null) assign(variables, assignment[1]!, assignment[3]!, assignment[2] === "+", requireSafe, isConditional);
  }
}

const OCTAL_DIGITS = /^[0-7]{1,3}/;

/** The text `printf` prints for the `\` escapes in one of its words, or null for an escape
 *  whose output this reader cannot compute (`\c` stops the output, `\u`/`\U` name a code
 *  point). One to three octal digits are one character, and in a `%b` argument a leading
 *  zero is a prefix for three more. An escape it does not know stands as written. */
function printfEscapes(text: string, isArgument = false): string | null {
  let out = "";
  for (let index = 0; index < text.length; index++) {
    const char = text[index]!;
    if (char !== "\\") {
      out += char;
      continue;
    }
    const next = text[index + 1] ?? "";
    index++;
    if (next === "c" || next === "u" || next === "U") return null;
    const prefixed = isArgument && next === "0" ? OCTAL_DIGITS.exec(text.slice(index + 1))?.[0] : undefined;
    const hex = next === "x" ? /^[0-9a-fA-F]{1,2}/.exec(text.slice(index + 1))?.[0] : undefined;
    const octal = OCTAL_DIGITS.exec(text.slice(index))?.[0];
    if (prefixed !== undefined) {
      out += String.fromCharCode(parseInt(prefixed, 8));
      index += prefixed.length;
    } else if (hex !== undefined) {
      out += String.fromCharCode(parseInt(hex, 16));
      index += hex.length;
    } else if (octal !== undefined) {
      out += String.fromCharCode(parseInt(octal, 8));
      index += octal.length - 1;
    } else {
      out += PRINTF_ESCAPES[next] ?? `\\${next}`;
    }
  }
  return out;
}

const PRINTF_ESCAPES: Record<string, string> = { a: "\x07", b: "\b", e: "\x1b", E: "\x1b", f: "\f", n: "\n", r: "\r", t: "\t", v: "\v", "\\": "\\", '"': '"' };

/** What `printf -v name format args` stores. The format is read the way bash reads it: its
 *  escapes expand, `%s` takes the argument as written, `%b` expands the argument's escapes,
 *  and the format repeats while arguments are left over. Null when that cannot be known. */
export function staticPrintfValue(args: readonly string[]): string | null {
  if (args.length === 0 || args.some((arg) => /[$`]/.test(arg))) return null;
  const format = printfEscapes(args[0]!);
  if (format === null || /%(?![%sb])/.test(format)) return null;
  const values = args.slice(1);
  let isUnknown = false;
  let out = "";
  let index = 0;
  let isFirstPass = true;
  while (isFirstPass || index < values.length) {
    isFirstPass = false;
    const firstValue = index;
    out += format.replace(/%(?:%|s|b)/g, (token) => {
      if (token === "%%") return "%";
      const next = values[index++] ?? "";
      if (token === "%s") return next;
      const expanded = printfEscapes(next, true);
      if (expanded === null) isUnknown = true;
      return expanded ?? "";
    });
    // A format with nothing to fill runs once, and one short of arguments still runs once.
    if (index === firstValue || index >= values.length) break;
  }
  return isUnknown ? null : out;
}

/** `printf -v` and `read` mutate variables for the next segment. A value this reader cannot
 *  evaluate drops the name, so a later `$name` stays unresolved instead of a stale safe path. */
export function applySegmentMutations(text: string, variables: VariableMap, requireSafe: boolean, isConditional = false): void {
  const words = argumentWords(normalizeRedirects(text)).map((word) => word.value);
  const at = commandIndex(words);
  const verb = basename(words[at] ?? "");
  const args = words.slice(at + 1);
  if (verb === "printf") {
    const attached = /^-[A-Za-z]*v(.*)$/.exec(args[0] ?? "");
    let name: string | undefined;
    let rest: string[] = [];
    if (args[0] === "-v") {
      name = args[1];
      rest = args.slice(2);
    } else if (attached !== null && attached[1] !== undefined && attached[1].length > 0) {
      name = attached[1];
      rest = args.slice(1);
    }
    if (name === undefined || !/^[A-Za-z_]\w*$/.test(name)) return;
    const value = staticPrintfValue(rest);
    if (value === null || isConditional || (requireSafe && !isSafeExpansion(value))) variables.set(name, null);
    else variables.set(name, value);
    return;
  }
  if (verb === "read") {
    for (let index = 0; index < args.length; index++) {
      const arg = args[index]!;
      if (arg === "--") continue;
      if (/^-[A-Za-z]*[dnNpauit]$/.test(arg)) {
        index++;
        continue;
      }
      if (arg.startsWith("-")) continue;
      if (/^[A-Za-z_]\w*$/.test(arg)) variables.set(arg, null);
    }
  }
}

/** Each segment's text with `$name` replaced by the value in force when that segment
 *  runs: a later `f=safe` does not rewrite an earlier `$f`, and a prefix `f=x cmd` never
 *  rewrites cmd's own `$f`. Empty when the command cannot be read. */
export function expandedSegments(command: string): string[] {
  const segments = shellSegments(command);
  if (segments === null) return [];
  const scopes = createVariableScope();
  return segments.map((segment) => {
    const variables = variablesForSegment(scopes, segment);
    const expanded = expandDollars(segment.text, variables);
    applySegmentAssignments(segment.text, variables, true, segment.isConditional);
    applySegmentMutations(segment.text, variables, true, segment.isConditional);
    return expanded;
  });
}

/** A segment's text with each simple echo/printf substitution replaced by what it prints. */
export function resolveSubstitutions(segment: ShellSegment): string {
  let index = 0;
  return segment.text.replace(/\$__SUB__/g, () => staticOutput(segment.substitutions[index++] ?? "") ?? SUBSTITUTION);
}
