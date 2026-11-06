// Writes against the four things that govern the agent, and nothing else: the files the
// chain itself reads (config.toml, overrides.toml, ai-eng.lock, arch.rules.json), the git
// floor, spec.html once its sha256 is pinned in the lock (reopening an approved contract
// costs a human), and the machine-side canon and carriers.
//
// Everything else under .ai-engineering/ is the session's to write — the fence protects
// the machinery, not the session's own evidence. The slots (brainstorm/spec/plan/recap
// die at `spec close` and the session is their only writer) and the artifacts the
// canon's own nodes promise (ai-research writes research/NNN-{name}.html, ai-security
// writes security/run-N/, ai-design writes design/direction.html) all have to pass, and
// a guard that stops a session writing what its skill told it to write protects nothing
// and breaks the loop it governs. What stays protected is the machinery a session could
// use to unpin, unhook or re-date itself.

import { basename, isAbsolute, join, parse, resolve, sep } from "node:path";
import { existsSync, readFileSync, realpathSync } from "node:fs";
import type { Payload } from "../payload.ts";
import { embeddedPatchPaths } from "../payload.ts";
import { home, machineBase } from "../env.ts";
import { commandIndex, normalizeRedirects, RESERVED_WORDS, resolveSubstitutions, shellSegments, shellWords, type ShellSegment } from "./shell.ts";

/** A command whose first word is one of these writes wherever its arguments point.
 *  `sed` joins them only with -i. The list may over-deny: that is a person told to
 *  use the edit tool, never a write nobody saw. */
const WRITERS: Record<string, true> = {
  rm: true, mv: true, cp: true, install: true, truncate: true, dd: true, tee: true,
  chmod: true, chown: true, ln: true, python: true, python3: true, perl: true,
  ruby: true, node: true, sh: true, bash: true, zsh: true, bun: true,
};

const REDIRECT = /\d*>>?\s*("[^"]*"|'[^']*'|[^\s;|&]+)/g;
const SEPARATORS = /[\n;|&]+/;
const REDIRECTION = /^(?:\{[\w]+\})?\d*(?:&>>?|>>?[|!&]?|<>|<{1,3}|<&)(.*)$/;
/** A path-shaped token with at least one `/` and no leading `/` — the form the
 *  absolute-path rewrite cannot see, and therefore the form that evaded it. */
const RELATIVE_PATH = /(^|[\s"'=<>|;&(])((?:\.\.?\/)?[\w.@+-]+(?:\/[\w.@+-]+)+)/g;

type GuardResult = { deny: true; reason: string } | { deny: false } | undefined;

export type ProtectedPaths = {
  literals: string[]; // substring-matched against commands and resolved paths
  specPinned: boolean; // spec.html approved (sha256 in lock) → protected
  /** Matched as the LAST segment only: the protected directory itself, never a child of
   *  it. `rm -rf .ai-engineering` names it and nothing else; `.ai-engineering/research/…`
   *  inside it is the session's own material. */
  terminal: string[];
};

const AI_ENG_COMMANDS = new Set(["ai-eng", "ai-eng.js", "ai-eng.cmd", "ai-eng.exe", "ai-engineering"]);
const CLI_WRAPPERS = new Set(["bunx", "command", "env", "exec", "nohup", "npx", "npm", "pnpm", "script", "sudo", "time", "timeout", "xargs", "yarn"]);

function commandName(word: string): string {
  const unquoted = word.replace(/['"]/g, "").replace(/^[()]+|[()]+$/g, "");
  const isQuoted = /^['"].*['"]$/.test(word);
  const withoutRedirect = isQuoted
    ? unquoted
    : unquoted.replace(/(?:\{[\w]+\})?\d*(?:&>>?|>>?[|!&]?|<>|<{1,3}|<&).*$/, "");
  const isWindowsPath = /^(?:[A-Za-z]:|\.{1,2})\\/.test(withoutRedirect);
  const normalized = isWindowsPath || withoutRedirect.includes("/")
    ? withoutRedirect.replace(/\\/g, "/")
    : withoutRedirect.replace(/\\(.)/g, "$1");
  return basename(normalized);
}

function stripRedirections(args: string[]): string[] {
  const kept: string[] = [];
  for (let index = 0; index < args.length; index++) {
    const word = args[index]!;
    if (/^['"].*['"]$/.test(word)) {
      kept.push(word);
      continue;
    }
    const redirect = REDIRECTION.exec(word);
    if (!redirect) {
      kept.push(word);
      continue;
    }
    if (redirect[1] === "" && index + 1 < args.length) index++;
  }
  return kept;
}

function isCliEntrypoint(word: string): boolean {
  return ["cli.ts", "cli.js"].includes(commandName(word)) || AI_ENG_COMMANDS.has(commandName(word));
}

/** A verb word anywhere in the arguments counts: flags and their values are not parsed,
 *  because `-y`, `--color`, `--` and unknown value flags all shift a positional reading. */
function restrictedAiEngArgs(args: string[]): boolean {
  const words = stripRedirections(args);
  const has = (word: string): boolean => words.includes(word);
  return has("uninstall") || has("wrap") || (has("adapt") && has("apply"))
    || (has("config") && words.some((word) => /^--remove(?:=|$)/.test(word)));
}

const SHELL_KEYWORDS = new Set(["", "(", ")", ...RESERVED_WORDS]);

/** Where the command word sits: past keywords, `NAME=value` and redirections, which the
 *  shell lets come BEFORE the verb (`>/dev/null ai-eng uninstall`, `2>&1 rm x`). */
function commandStart(words: string[]): number {
  let index = 0;
  while (index < words.length) {
    const word = words[index]!;
    if (SHELL_KEYWORDS.has(word) || /^[A-Za-z_][A-Za-z0-9_]*=/.test(word)) {
      index++;
      continue;
    }
    const redirect = /^['"]/.test(word) ? null : REDIRECTION.exec(word);
    if (redirect === null) return index;
    index += redirect[1] === "" ? 2 : 1;
  }
  return index;
}

const SHELLS = new Set(["sh", "bash", "zsh", "dash", "ksh", "mksh", "ash", "fish", "csh", "tcsh", "pwsh", "powershell"]);
const INTERPRETERS = new Set([...SHELLS, "python", "python3", "node", "perl", "ruby", "bun", "deno", "php"]);
const STDIN_FILES = new Set(["-", "/dev/stdin", "/dev/fd/0", "/proc/self/fd/0"]);

/** The verb a segment runs, past redirections and run-it-for-me prefixes (`command rm`). */
function verbOf(words: string[]): { index: number; name: string } {
  const index = commandIndex(words, commandName, commandStart(words));
  return { index, name: commandName(words[index] ?? "") };
}

const INFO_FLAGS = /^(?:--version|--help|-V|-v|-h)$/;

/** True when an interpreter would read its program from stdin: no script and no inline
 *  program (`-c` in any short-option cluster for a shell, `-c`/`-e` for the others). */
function readsProgramFromStdin(name: string, args: string[]): boolean {
  const inline = SHELLS.has(name) ? /^-[A-Za-z]*c[A-Za-z]*$/ : /^-[A-Za-z]*[ceE][A-Za-z]*$/;
  if (args.some((arg) => INFO_FLAGS.test(arg) || inline.test(arg))) return false;
  return !args.some((arg) => !arg.startsWith("-"));
}

const READERS = new Set([
  "cat", "less", "more", "head", "tail", "grep", "egrep", "fgrep", "rg", "ag", "wc", "diff", "cmp", "ls", "stat",
  "file", "sha256sum", "sha1sum", "sha512sum", "shasum", "md5", "md5sum", "cksum", "test", "[", "[[", "echo",
  "printf", "realpath", "readlink", "basename", "dirname", "jq", "nl", "od", "hexdump", "strings", "du", "bat",
  "tree", "cd", "pushd", "popd",
  // PowerShell readers (case-insensitive: names are compared lowercased)
  "get-content", "gc", "type", "select-string", "sls", "test-path", "get-item", "gi", "get-childitem", "gci",
  "dir", "resolve-path", "write-output", "write-host",
]);
const GIT_READERS = new Set(["diff", "log", "show", "status", "blame", "ls-files", "cat-file", "grep", "check-ignore", "rev-parse", "shortlog", "describe"]);
const FIND_ACTIONS = /^-(?:delete|exec|execdir|ok|okdir|fprint0?|fprintf|fls)$/;
/** Verbs that act on a whole tree: naming a directory that holds governance names it too. */
const TREE_WRITERS = new Set([
  "rm", "rmdir", "mv", "cp", "ln", "chmod", "chown", "chgrp", "rsync", "tar", "unzip", "ditto", "install", "find",
  "tee", "truncate", "dd", "split", "csplit", "touch", "remove-item", "ri", "del", "erase", "rd", "move-item", "mi", "copy-item", "cpi",
  "rename-item", "rni", "set-content", "sc", "add-content", "ac", "out-file", "clear-content", "new-item", "ni",
]);
/** Writers whose targets live in a file the guards never read. */
const DIFF_APPLIERS = new Set(["patch", "ed", "ex"]);
const GIT_TREE_WRITERS = new Set(["mv", "rm", "checkout", "restore", "clean"]);
const GLOB_CHARS = /[*?[]/;
/** Options whose value is a file the program writes. */
const OUTPUT_OPTION = /^(?:-o|-O|-out|--out|--output|--output-document|--outfile|--log-file)$/;
const ATTACHED_OUTPUT = /^(?:-o.|-O.|--out=|--output=|--output-document=|--outfile=|--log-file=|of=)/;
const MAX_GLOB_MATCHES = 2000;
const MAX_SHELL_DEPTH = 4;

type ShellContext = { paths: ProtectedPaths; bases: string[]; isPowerShell: boolean };

function gitSubcommand(args: string[]): { name: string; index: number } {
  for (let index = 0; index < args.length; index++) {
    const arg = args[index]!;
    if (["-C", "-c", "--git-dir", "--work-tree", "--namespace"].includes(arg)) index++;
    else if (!arg.startsWith("-")) return { name: arg, index };
  }
  return { name: "", index: args.length };
}

function isReader(verb: string, args: string[]): boolean {
  // `git diff --output=x` writes: a long output option is never a read.
  if (args.some((arg) => /^--(?:output|out|output-document|outfile|log-file)(?:=|$)/.test(arg))) return false;
  if (verb === "git") return GIT_READERS.has(gitSubcommand(args).name);
  if (verb === "find") return !args.some((arg) => FIND_ACTIONS.test(arg));
  return READERS.has(verb);
}

function isTreeWriter(verb: string, args: string[]): boolean {
  if (verb === "git") return GIT_TREE_WRITERS.has(gitSubcommand(args).name);
  if (verb === "find") {
    // `-exec` hands every match to another program: anything but a reader may write it.
    return args.some((arg, index) => arg === "-delete"
      || (/^-(?:exec|execdir|ok|okdir)$/.test(arg) && !isReader(commandName(args[index + 1] ?? "").toLowerCase(), args.slice(index + 2))));
  }
  return TREE_WRITERS.has(verb) || (verb === "sed" && args.some((arg) => /^-[A-Za-z]*i/.test(arg)));
}

/** Path-shaped text inside one argument: `sed -n 'w .ai-engineering/config.toml'`,
 *  `node -e "fs.writeFileSync('.git/hooks/pre-commit', …)"`. */
const EMBEDDED_PATH = /(?:~|\.{1,2})?\/?[\w.@+-]*(?:\/[\w.@+-]+)+|\.ai-engineering\b[\w./-]*|\.git\b[\w./-]*/g;

/** A native path in the `/`-separated form the patterns here are written in: on Windows a
 *  resolved path separates with `\`, and `(?:^|/)\.git/hooks` would never see it. */
function slashed(path: string): string {
  return sep === "\\" ? path.replaceAll("\\", "/") : path;
}

/** On Windows `//host/share` — the tail of every URL, `https://example.com/i.sh` — resolves
 *  to a UNC path, and opening one connects to that host over SMB: seconds per name, and the
 *  machine's NTLM credentials offered to whoever answers. A network path is judged by its
 *  text alone; it is never resolved. A device path (`\\?\`, `\\.\`, `\??\`) is local only
 *  when it names a drive letter: `\\?\UNC\`, `\\?\GLOBALROOT\Device\Mup\` and the rest of
 *  the device namespace can reach a share, so they count as network and are never opened. */
export function isNetworkPath(path: string, isWindows = sep === "\\"): boolean {
  if (!isWindows) return false;
  const native = path.replaceAll("/", "\\");
  const device = /^(?:\\\\[?.]|\\\?\?)\\/.exec(native);
  if (device !== null) return !/^[A-Za-z]:(?:\\|$)/.test(native.slice(device[0].length));
  return native.startsWith("\\\\");
}

/** realpathSync for a local path; a network path throws, so callers keep its text form. */
function localRealpath(path: string): string {
  if (isNetworkPath(path)) throw new Error(`${path} is a network path and is never opened`);
  return realpathSync(path);
}

function expandBraces(pattern: string, found: string[] = []): string[] {
  const group = /\{([^{}]*,[^{}]*)\}/.exec(pattern);
  if (group === null) {
    found.push(pattern);
    return found;
  }
  for (const option of group[1]!.split(",")) {
    if (found.length >= 64) break;
    expandBraces(pattern.slice(0, group.index) + option + pattern.slice(group.index + group[0].length), found);
  }
  return found;
}

/** The absolute paths one word can stand for, as the shell (or the program, for a quoted
 *  glob) would expand it from every base the command can run in. Null: too broad to read. */
function pathCandidates(word: string, bases: string[]): string[] | null {
  const forms = [word];
  const equals = word.indexOf("=");
  if (equals > 0) forms.push(word.slice(equals + 1));
  // An attached short-option value: `-o.git/hooks/pre-commit`, `-C.ai-engineering`.
  const attached = /^-[A-Za-z](.+)$/.exec(word)?.[1];
  if (attached !== undefined) forms.push(attached);
  const found: string[] = [];
  for (const form of forms) {
    if (form.length === 0 || (form.startsWith("-") && !form.includes("/"))) continue;
    for (const pattern of expandBraces(expandTilde(form))) {
      for (const base of bases) {
        if (!GLOB_CHARS.test(pattern)) {
          found.push(resolve(base, pattern));
          continue;
        }
        const isRooted = isAbsolute(pattern);
        // A scan from a network directory would open it: too broad to read, so it denies.
        if (isNetworkPath(isRooted ? pattern : base)) return null;
        let count = 0;
        try {
          for (const match of new Bun.Glob(isRooted ? pattern.slice(1) : pattern).scanSync({ cwd: isRooted ? "/" : base, dot: true, absolute: true, onlyFiles: false })) {
            if (++count > MAX_GLOB_MATCHES) return null;
            found.push(match);
          }
        } catch {
          /* an unreadable directory matches nothing */
        }
      }
    }
  }
  return found;
}

function isAncestorOfProtected(paths: ProtectedPaths, candidate: string): boolean {
  let canonical = candidate;
  try {
    canonical = localRealpath(candidate);
  } catch {
    /* not there yet */
  }
  const protectedRoots = [...paths.literals, ...paths.terminal.filter((path) => isAbsolute(path))];
  return protectedRoots.some((root) => {
    let real = root;
    try {
      real = realpathSync(root);
    } catch {
      /* keep */
    }
    // A string prefix, not only a parent directory: `split -a1 x .ai-engineering/config.tom`
    // writes `config.toml` as its twelfth chunk.
    return [root, real].some((form) => [candidate, canonical].some((path) => form.toLowerCase().startsWith(path.toLowerCase())));
  });
}

/** Same-command assignments (`f=path; rm $f`) and $HOME, substituted the way bash would. */
function shellVariables(segments: ShellSegment[]): Map<string, string> {
  const variables = new Map<string, string>([["HOME", machineBase()]]);
  for (const segment of segments) {
    for (const word of shellWords(segment.text)) {
      const assignment = /^([A-Za-z_]\w*)=(.*)$/s.exec(word.value);
      if (assignment) variables.set(assignment[1]!, assignment[2]!);
    }
  }
  return variables;
}

function substitute(value: string, variables: Map<string, string>): string {
  return value.replace(/\$\{([A-Za-z_]\w*)\}|\$([A-Za-z_]\w*)/g, (all, braced: string | undefined, bare: string | undefined) => variables.get(braced ?? bare ?? "") ?? all);
}

// ponytail: reads the shell the way bash does, segment by segment, and refuses what it
// cannot read (decode → shell, curl | sh, <(…), eval, a computed verb or target) or what
// names a governed path from a verb that is not a known reader. A general-purpose
// interpreter handed an opaque program still runs it: only an OS sandbox closes that class.
function judgeShell(command: string, context: ShellContext, depth = 0): string | null {
  if (depth > MAX_SHELL_DEPTH) return "it nests shells too deep to read";
  if (context.isPowerShell) {
    const unreadable = powerShellUnreadable(command);
    if (unreadable !== null) return unreadable;
  }
  if (/\b(?:pwsh|powershell)(?:\.exe)?\b/i.test(command) && POWERSHELL_ENCODED.test(command)) return "an encoded PowerShell command hides what it runs";
  const expanded = command.replace(/\$\(\s*(?:which|command\s+-v)\s+([^)\s]+)\s*\)/g, "$1");
  const segments = shellSegments(normalizeRedirects(expanded));
  if (segments === null) return "its quoting cannot be read, so neither can what it runs";
  const variables = shellVariables(segments);
  const bases = [...context.bases];
  const parsed = segments.map((segment) => {
    const words = shellWords(resolveSubstitutions(segment)).map((word) => ({ ...word, original: word.value, value: substitute(word.value, variables) }));
    const plain: string[] = [];
    const writeTargets: string[] = [];
    // Here-strings: text the verb reads on stdin (`at now <<< '…'`).
    const inputs: string[] = [];
    for (let index = 0; index < words.length; index++) {
      const word = words[index]!;
      if (!word.isOperator) {
        plain.push(word.value);
        continue;
      }
      const target = words[index + 1];
      if (word.value.includes(">") && target !== undefined) writeTargets.push(target.value);
      if (word.value === "<<<" && target !== undefined) inputs.push(target.value);
      index++;
    }
    const verb = verbOf(plain);
    return { segment, words, plain, writeTargets, inputs, verb, name: verb.name.toLowerCase(), args: plain.slice(verb.index + 1) };
  });
  // Every directory a `cd` in this command can land in is a base for the relative paths
  // after it; a directory computed at run time makes those paths unknowable.
  let hasUnknownBase = false;
  for (const { name, args } of parsed) {
    if (name !== "cd" && name !== "pushd") continue;
    const target = args.find((arg) => !/^-[LPe@]*$/.test(arg) && arg !== "--");
    if (target === undefined || target === "-") continue;
    if (/[$`]/.test(target)) hasUnknownBase = true;
    else bases.push(...(pathCandidates(target, [...bases]) ?? []));
  }
  const names = (word: string, includesCheckpoints = true): string | null => {
    const candidates = pathCandidates(word, bases);
    if (candidates === null) return word;
    const hit = candidates.find((candidate) => offendingTarget(context.paths, candidate, bases) !== null || (includesCheckpoints && CHECKPOINT_FILE.test(slashed(candidate))));
    return hit ?? globNamesProtected(word, bases, context.paths);
  };
  const isRelative = (word: string): boolean => !isAbsolute(expandTilde(word)) && !word.startsWith("-");
  for (const { segment, words, plain, writeTargets, inputs, verb, name, args } of parsed) {
    // Judged as written, before substitution: `IFS=,; c=rm,x; $c` is still a computed verb.
    const verbWord = words.find((word) => !word.isOperator && word.value === plain[verb.index]);
    const rawVerb = verbWord?.original ?? "";
    if (segment.isProcessSubstitution) return "process substitution runs a command whose text is not on the line";
    // In PowerShell a leading `$x` is an expression, not a call; `& $x` is caught above.
    if (!context.isPowerShell && (rawVerb.startsWith("$") || rawVerb.startsWith("`"))) return "the command name is computed at run time";
    const isTestBracket = rawVerb === "[" || rawVerb === "[[";
    if (verbWord !== undefined && !verbWord.isQuoted && !isTestBracket && (GLOB_CHARS.test(rawVerb) || /\{[^}]*,/.test(rawVerb))) return "the command name is a pattern the shell expands";
    if (name === "eval" || name === "iex" || name === "invoke-expression") return `${name} runs text the guards cannot read`;
    if (name === "alias" && args.some((arg) => arg.includes("="))) return "an alias renames commands the guards judge by name";
    if (name === "hash" && args.includes("-p")) return "hash -p renames a command the guards judge by name";
    if ((name === "source" || name === ".") && STDIN_FILES.has(args[0] ?? "")) return "sourcing stdin runs text the guards cannot read";
    if (segment.isAfterPipe && SHELLS.has(name)) return "piping text into a shell runs code the guards cannot read";
    if (INTERPRETERS.has(name) && segment.heredocs.length === 0 && inputs.length === 0 && readsProgramFromStdin(name, args)) {
      return "an interpreter reading its program from stdin runs code the guards cannot read";
    }
    const inline = SHELLS.has(name) ? /^-[A-Za-z]*c[A-Za-z]*$/ : /^-[A-Za-z]*[ceE][A-Za-z]*$/;
    const program = args[args.findIndex((arg) => inline.test(arg)) + 1];
    if (INTERPRETERS.has(name) && ((program !== undefined && /[$`]/.test(program) && args.some((arg) => inline.test(arg))) || inputs.some((input) => /[$`]/.test(input)))) {
      return "an interpreter fed generated text runs code the guards cannot read";
    }
    const isPowerShellHost = name === "pwsh" || name === "powershell";
    if (isPowerShellHost && args.some((arg) => isOptionPrefix(arg, "-encodedcommand") || arg.toLowerCase() === "-ec")) {
      return "an encoded PowerShell command hides what it runs";
    }
    if (plain.slice(0, verb.index).some((word) => /^(?:BASH_ENV|ENV)=/.test(word))) return "BASH_ENV sources a file the guards cannot read";
    if (name === "base64" && args.some((arg) => /^(?:-d|-D|--decode)$/.test(arg))) return "decoding base64 hides the command it carries";
    if (name === "apply_patch") {
      const isReadable = segment.heredocs.length > 0 && segment.heredocs.every(({ body, isLiteral }) => {
        try {
          return isLiteral && embeddedPatchPaths(body).length > 0;
        } catch {
          return false;
        }
      });
      if (!isReadable) return "apply_patch reads a patch the guards cannot see; pass it as one quoted heredoc";
    }

    for (const target of writeTargets) {
      if (target.includes("$") || target.includes("`")) return "it writes to a path computed at run time";
      if (hasUnknownBase && isRelative(target)) return "it writes to a relative path after a cd to a directory computed at run time";
      const hit = names(target);
      if (hit !== null) return `it writes to ${hit}, which governs this session`;
    }
    const isWriter = isTreeWriter(name, args);
    if (isWriter && plain.slice(0, verb.index).some((before) => commandName(before) === "xargs")) {
      return `${name} acts on paths read from stdin`;
    }
    if (DIFF_APPLIERS.has(name) || (name === "git" && ["apply", "am"].includes(gitSubcommand(args).name))) {
      return `${name} applies edits whose target files are not on the command line; use the edit tool`;
    }
    if ((isWriter || writeTargets.length > 0) && args.some((arg) => AI_ENG_COMMANDS.has(commandName(arg)))) {
      return "it copies or links the ai-eng binary, which would let its verbs run under another name";
    }
    const extractTo = extractionTarget(name, args);
    if (extractTo !== null && (names(extractTo) !== null || (pathCandidates(extractTo, bases) ?? []).some((dir) => isAncestorOfProtected(context.paths, dir)))) {
      return `${name} extracts files into ${extractTo}, which holds what governs this session; extract somewhere else`;
    }
    if (!isReader(name, args)) {
      const computedOutput = args.findIndex((arg, index) => (OUTPUT_OPTION.test(arg) && /[$`]/.test(args[index + 1] ?? "")) || (ATTACHED_OUTPUT.test(arg) && /[$`]/.test(arg)));
      if (computedOutput >= 0) return `${name} writes to an output path computed at run time`;
      for (const arg of args) {
        if (isWriter && (arg.includes("$") || arg.includes("`"))) return `${name} acts on a path computed at run time`;
        if (isWriter && hasUnknownBase && isRelative(arg)) return `${name} acts on a relative path after a cd to a directory computed at run time`;
        // A commit message is prose: only git's whole arguments are paths. Git records
        // checkpoint files; it is the edit tools that must write them.
        const embedded = name === "git" ? [] : (arg.match(EMBEDDED_PATH) ?? []).filter((path) => path !== arg);
        for (const path of [arg, ...embedded]) {
          const hit = names(path, name !== "git");
          if (hit !== null) return `${name} names ${hit}, which governs this session, and ${name} is not a read-only command`;
        }
        if (isWriter && (pathCandidates(arg, bases) ?? []).some((candidate) => isAncestorOfProtected(context.paths, candidate))) {
          return `${name} acts on ${arg}, which contains what governs this session; name the files you mean`;
        }
      }
      // A heredoc or here-string is the program's input: `vim -es`, `sqlite3 .output`,
      // `python3`, `at` and `crontab` act on whatever it says. A git heredoc is a message.
      if (!SHELLS.has(name) && name !== "git") {
        for (const text of [...segment.heredocs.map(({ body }) => body), ...inputs]) {
          if (RESTRICTED_TEXT.test(text)) return `${name} reads input that invokes a governance-changing ai-eng verb`;
          const hit = (text.match(EMBEDDED_PATH) ?? []).map((path) => names(path)).find((found) => found !== null);
          if (hit) return `${name} reads input that names ${hit}, which governs this session`;
        }
        // Programs that take code as an argument (osascript -e, expect -c, tmux, xonsh -c).
        if (name !== "echo" && args.some((arg) => RESTRICTED_TEXT.test(arg))) return `${name} is handed code that invokes a governance-changing ai-eng verb`;
      }
    }

    // ai-eng anywhere in the segment: behind nice/watch/find -exec, or fed by xargs.
    for (let index = 0; index < plain.length; index++) {
      const word = plain[index]!;
      const viaRuntime = index > 0 && isCliEntrypoint(word) && plain.slice(0, index).some((before) => ["bun", "node"].includes(commandName(before)));
      if (!AI_ENG_COMMANDS.has(commandName(word)) && !viaRuntime) continue;
      const rest = plain.slice(index + 1).flatMap((arg) => expandBraces(arg));
      if (rest.some((arg) => /[$`]/.test(arg) || GLOB_CHARS.test(arg)) || plain.slice(0, index).some((before) => commandName(before) === "xargs")) {
        return "it runs ai-eng with arguments computed at run time";
      }
      if (restrictedAiEngArgs(rest)) return "it invokes a governance-changing or internal ai-eng verb";
    }

    // Code inside the words: `sh -c '…'`, a heredoc fed to a shell, `trap '…'`,
    // `find -exec`, a git config value git runs, `GIT_EDITOR=…`.
    const nested: string[] = [];
    if (SHELLS.has(name)) {
      const flag = args.findIndex((arg) => (isPowerShellHost ? isOptionPrefix(arg, "-command") : /^-[A-Za-z]*c[A-Za-z]*$/.test(arg)) || /^\/[ck]$/i.test(arg));
      if (flag >= 0 && args[flag + 1] !== undefined) nested.push(args.slice(flag + 1).join(" "));
      if (isPowerShellHost) nested.push(args.filter((arg) => !arg.startsWith("-")).join(" "));
      nested.push(...segment.heredocs.map(({ body }) => body), ...inputs);
    }
    if (COMMAND_RUNNERS.has(name)) nested.push(...args.filter((arg) => !arg.startsWith("-")));
    if (name === "find") {
      args.forEach((arg, index) => {
        if (!/^-(?:exec|execdir|ok|okdir)$/.test(arg)) return;
        const end = args.findIndex((word, position) => position > index && (word === ";" || word === "+"));
        nested.push(args.slice(index + 1, end < 0 ? undefined : end).join(" "));
      });
    }
    if (name === "git") nested.push(...gitCodeValues(args));
    for (const word of plain.slice(0, verb.index).concat(name === "export" || name === "declare" ? args : [])) {
      const assignment = /^([A-Za-z_]\w*)=(.*)$/s.exec(word);
      if (assignment && CODE_VARIABLES.has(assignment[1]!)) nested.push(assignment[2]!);
    }
    for (const body of nested) {
      const inner = judgeShell(body, { ...context, bases, isPowerShell: context.isPowerShell || isPowerShellHost }, depth + 1);
      if (inner !== null) return inner;
    }
  }
  return null;
}

const RESTRICTED_TEXT = /\bai-eng(?:ineering)?\b[^\n|;&]*?\b(?:uninstall|wrap|adapt\s+apply)\b|\bai-eng(?:ineering)?\b[^\n|;&]*\bconfig\b[^\n|;&]*--remove\b/;
const CHECKPOINT_FILE = /(?:^|\/)\.ai-engineering\/workflow\/checkpoints\//i;
const POWERSHELL_ENCODED = /(?:^|[\s,'"(])(?:-{1,2}|\/)e(?:c|n|nc|nco|ncod|ncode|ncoded|ncodedc|ncodedco|ncodedcom|ncodedcomm|ncodedcomma|ncodedcomman|ncodedcommand)?(?=$|[\s,'")])/i;

/** Where an archive tool writes, or null when the call does not extract. Without -C/-d an
 *  extraction lands in the cwd: the repo root, which holds the governance files. */
function extractionTarget(name: string, args: string[]): string | null {
  const after = (flags: string[]): string | undefined => {
    const index = args.findIndex((arg) => flags.includes(arg));
    if (index >= 0) return args[index + 1];
    const attached = args.find((arg) => flags.some((flag) => flag.startsWith("--") && arg.startsWith(`${flag}=`)));
    return attached?.slice(attached.indexOf("=") + 1);
  };
  if (["tar", "bsdtar", "gtar"].includes(name)) {
    const isExtract = args.includes("--extract") || args.includes("--get") || args.some((arg) => /^-[A-Za-z]*x[A-Za-z]*$/.test(arg)) || /^[A-Za-z]*x[A-Za-z]*$/.test(args[0] ?? "");
    return isExtract ? after(["-C", "--directory"]) ?? "." : null;
  }
  if (name === "unzip") return args.some((arg) => /^-[A-Za-z]*[lvtZ]/.test(arg)) ? null : after(["-d"]) ?? ".";
  if (name === "cpio") return args.some((arg) => /^-[A-Za-z]*i/.test(arg) || arg === "--extract") ? "." : null;
  if (["7z", "7za", "7zz"].includes(name) && ["x", "e"].includes(args[0] ?? "")) {
    return args.find((arg) => arg.startsWith("-o"))?.slice(2) || ".";
  }
  return null;
}

/** A glob or brace word that would expand onto a governed path (or into one), even when the
 *  file is not there yet to be found by a scan: `.git/hoo?s/pre-commit`. */
function globNamesProtected(word: string, bases: string[], paths: ProtectedPaths): string | null {
  if (!GLOB_CHARS.test(word) && !/\{[^}]*,/.test(word)) return null;
  const protectedRoots = [...paths.literals, ...paths.terminal.filter((path) => isAbsolute(path))];
  for (const pattern of expandBraces(expandTilde(word))) {
    for (const base of bases) {
      const segments = slashed(resolve(base, pattern)).toLowerCase().split("/");
      for (const root of protectedRoots) {
        const rootForm = slashed(root).toLowerCase();
        const depth = rootForm.split("/").length;
        const prefix = segments.slice(0, depth).join("/");
        try {
          if (new Bun.Glob(prefix).match(rootForm)) return root;
        } catch {
          return word;
        }
      }
    }
  }
  return null;
}

/** git config keys whose values git runs as programs. */
const GIT_CODE_KEYS = /^(?:core\.(?:fsmonitor|editor|pager|sshcommand)|diff\.external|sequence\.editor|credential\.helper|gpg\.program|alias\..*|filter\..*|.*\.(?:askpass|textconv|command|cmd|driver|tool))$/i;
/** Environment variables a tool runs as a command. */
const CODE_VARIABLES = new Set(["GIT_EDITOR", "GIT_PAGER", "GIT_SSH_COMMAND", "GIT_SSH", "GIT_EXTERNAL_DIFF", "GIT_ASKPASS", "GIT_SEQUENCE_EDITOR", "EDITOR", "VISUAL", "PAGER", "SSH_ASKPASS", "PROMPT_COMMAND", "BASH_ENV", "ENV"]);
/** Verbs that hand one of their arguments to a shell. */
const COMMAND_RUNNERS = new Set(["watch", "su", "runuser", "flock", "script", "trap"]);

/** The command strings a git invocation would run: `-c key=value` and `git config key value`
 *  for a key git executes, and `!` aliases. */
function gitCodeValues(args: string[]): string[] {
  const values: string[] = [];
  const consider = (key: string, value: string): void => {
    if (GIT_CODE_KEYS.test(key)) values.push(value.replace(/^!/, ""));
  };
  args.forEach((arg, index) => {
    if (args[index - 1] === "-c" || /^[\w.-]+\.[\w.-]+=/.test(arg)) {
      const equals = arg.indexOf("=");
      if (equals > 0) consider(arg.slice(0, equals), arg.slice(equals + 1));
    }
  });
  const sub = gitSubcommand(args);
  if (sub.name === "config") {
    const rest = args.slice(sub.index + 1).filter((arg) => !arg.startsWith("-"));
    if (rest[0] !== undefined && rest[1] !== undefined) consider(rest[0], rest[1]);
  }
  return values;
}

function isOptionPrefix(arg: string, option: string): boolean {
  const lower = arg.toLowerCase();
  return lower.length >= 2 && lower.startsWith("-") && option.startsWith(lower);
}

/** PowerShell reaches code and files without a command word: .NET calls, the call operator
 *  on a computed name, and names built by concatenation. */
function powerShellUnreadable(command: string): string | null {
  for (const call of command.matchAll(/\[([\w.]+)\]\s*::/g)) {
    if (/(?:^|\.)(?:file|directory|path|scriptblock|process|convert|activator|assembly|environment|appdomain|marshal|webclient|registry|runspace|powershell)$|^(?:system\.)?(?:io|reflection|management|diagnostics|runtime|net)\b|^microsoft\.win32\b/i.test(call[1]!)) {
      return `[${call[1]}]:: reaches files or code without a command the guards can read`;
    }
  }
  if (/(?:^|[\s;|{(])[&.]\s*[($]/.test(command)) return "the call operator runs a command name computed at run time";
  if (/\(\s*(['"])[^'"]*\1\s*\+/.test(command)) return "it builds a name or path by concatenation at run time";
  return null;
}

function restrictedCommandWords(words: string[], depth: number): boolean {
  if (depth > 4 || words.length === 0) return false;
  const index = commandStart(words);

  const executable = commandName(words[index] ?? "");
  if (AI_ENG_COMMANDS.has(executable)) return restrictedAiEngArgs(words.slice(index + 1));
  if (executable === "bun" || executable === "node") {
    const entrypoint = words.findIndex((word, position) => position > index && isCliEntrypoint(word));
    if (entrypoint >= 0) return restrictedAiEngArgs(words.slice(entrypoint + 1));
  }
  if (["sh", "bash", "zsh", "pwsh", "powershell", "cmd"].includes(executable)) {
    const commandIndex = words.findIndex((word, position) =>
      position > index && ["-c", "-lc", "-Command", "/c", "/k"].includes(word),
    );
    if (commandIndex >= 0) return isRestrictedCliCommand(words.slice(commandIndex + 1).join(" "), depth + 1);
  }
  if (CLI_WRAPPERS.has(executable)) {
    const invocation = words.findIndex((word, position) => position > index && AI_ENG_COMMANDS.has(commandName(word)));
    if (invocation >= 0) return restrictedAiEngArgs(words.slice(invocation + 1));
    const entrypoint = words.findIndex((word, position) => position > index && isCliEntrypoint(word));
    if (entrypoint >= 0) return restrictedAiEngArgs(words.slice(entrypoint + 1));
  }
  return false;
}

// ponytail: this catches direct CLI calls and common wrappers; arbitrary shell code needs an OS sandbox, not more denylist shapes.
function isRestrictedCliCommand(command: string, depth = 0): boolean {
  const expanded = command.replace(/\$\(\s*(?:which|command\s+-v)\s+([^)\s]+)\s*\)/g, "$1");
  const words = expanded.trim().split(/\s+/)
    .map((word) => word.replace(/['"]/g, "").replace(/^[()]+|[()]+$/g, ""));
  return restrictedCommandWords(words, depth);
}

function surfacesSettings(repoRoot: string): string[] {
  // The settings files this install wires, per surface (derived from what install
  // wrote; the on-disk check keeps an uninstall from leaving ghosts).
  const out: string[] = [];
  const candidates = [
    join(repoRoot, ".claude", "settings.json"),
    join(repoRoot, ".opencode", "plugins", "ai-eng.ts"),
    join(repoRoot, ".agents", "hooks", "ai-eng.ts"),
  ];
  for (const path of candidates) if (existsSync(path)) out.push(path);
  return out;
}

/** Every path this session may not write to. Derived, never copied: a list that can
 *  fall behind the wiring lets one edit to the IOC catalogue disarm the injection guard. */
export function protectedPaths(repoRoot: string | null): ProtectedPaths {
  const literals: string[] = [];
  // The machine side is protected whether or not this call happens inside a governed
  // repo: the canon and its mirrors govern every session on this machine, and a repo-less
  // call is exactly the one an injected instruction would use to unprotect them (R4).
  const globalHome = join(home(), "");
  literals.push(join(home(), "skills"));
  literals.push(join(machineBase(), ".claude", "skills"));
  literals.push(join(machineBase(), ".agents", "skills"));
  literals.push(join(machineBase(), ".config", "opencode", "skill"));
  literals.push(globalHome);
  for (const carrier of [".claude/settings.json", ".config/opencode/plugins", ".codex/hooks.json", ".omp/agent/hooks", ".pi/agent/extensions", ".copilot/hooks", "machine.json", ".gitconfig", ".config/git/config"]) {
    literals.push(join(machineBase(), carrier));
  }
  if (!repoRoot) return { literals: literals.filter((p) => p.length > 0), specPinned: false, terminal: [] };

  // Prose contracts the user owns: editable by the governed agent (blueprint §9.2
  // "AGENTS.md no es sagrado" / §13.3 "tú lo editas"), so they are NOT literals.
  // Only the machinery below stays protected.
  //
  // The directory is protected as a TERMINAL match — the last segment, never a prefix: a
  // command that names `.ai-engineering` is deleting everything the chain owns in one
  // word, while a file inside it is the session's own material (the four slots, the
  // research and security artifacts its own nodes write, the receipts). One substring
  // literal for the directory denied both, which is how a guard ends up stopping the loop
  // it governs.
  const aiEng = join(repoRoot, ".ai-engineering");
  const terminal = [".ai-engineering", aiEng];
  // The four files the chain itself reads: the ceiling, the guard switches, the pins, the
  // layer rules.
  for (const name of ["config.toml", "overrides.toml", "ai-eng.lock", "arch.rules.json"]) {
    literals.push(join(aiEng, name));
  }
  // The git floor itself. The shims live in .git/hooks/ (marker-managed, §13.2),
  // NOT under .ai-engineering/git/ — protecting a ghost there while the real shims
  // stay writable lets a session overwrite the hook with `exit 0`
  // (Write/Edit/redirect all allowed).
  literals.push(join(repoRoot, ".git", "hooks"));
  // spec.html is protected ONLY once approved: its sha256 sits in the lock (§9.3).
  // The fence is that file, not the word. Matching the substring "spec.html" also denied
  // `templates/spec.html.tpl` — the payload `init` generates every project's contract
  // from — and any future `docs/spec.html.md`, while the rule's own criterion is the
  // pinned file. Pushing the path through the literal list keeps the same protection on
  // the same file, through the same matching the other governed paths already use.
  let specPinned = false;
  try {
    const lock = Bun.TOML.parse(readFileSync(join(aiEng, "ai-eng.lock"), "utf8")) as Record<string, unknown>;
    const pinned = lock["spec_sha256"];
    specPinned = typeof pinned === "string" && pinned.length >= 64;
  } catch {
    specPinned = false;
  }
  if (specPinned) literals.push(join(aiEng, "spec.html"));
  // Surface wiring we ourselves wrote.
  literals.push(...surfacesSettings(repoRoot));
  // Global canon and machine state: ~/.ai-engineering/** and the home mirrors. Both are
  // protected above, for the repo-less call as well.
  // Drop empties: the test is substring, and "" is a substring of every command.
  return { literals: literals.filter((p) => p.length > 0), specPinned, terminal };
}


/** The protected path this ONE shell command writes to, or null. A redirect is
 *  judged by where it points; a pipe target (tee, xargs rm) is judged as a write
 *  when its receiver is a writer verb and the payload names a protected path. */
export function writesTo(paths: ProtectedPaths, command: string): string | null {
  const words = command.trim().split(/\s+/).filter((w) => w.length > 0);
  if (words.length === 0) return null;
  const verb = verbOf(words).name;
  if (WRITERS[verb] === true || (verb === "sed" && words.includes("-i"))) {
    return offendingPath(paths, command);
  }
  // A writer downstream of a pipe (echo x | tee <path>): its arguments carry the
  // destination. Judge the writer verb's own words, not the whole pipeline.
  for (let i = 1; i < words.length; i++) {
    if (words[i] === "|" && i + 1 < words.length) {
      const rest = words.slice(i + 1).join(" ");
      const downstream = writesTo(paths, rest);
      if (downstream) return downstream;
      break;
    }
  }
  for (const match of command.matchAll(REDIRECT)) {
    const found = offendingPath(paths, match[1]!.replace(/^["']|["']$/g, ""));
    if (found) return found;
  }
  return null;
}

function expandTilde(path: string): string {
  if (path === "~") return machineBase();
  if (path.startsWith("~/")) return join(machineBase(), path.slice(2));
  return path;
}

/** The governed file or path this text offends, or null.
 *
 *  The prose contracts the user owns (AGENTS.md, DECISIONS.md) are
 *  EDITABLE by the governed agent (blueprint §9.2: "AGENTS.md no es sagrado";
 *  §13.3: "tú lo editas") — they are instructions, not wiring, and are simply not
 *  in the protected literal list. What must never change from inside a session is
 *  the machinery: the four files the chain reads, surface settings, git hooks, the
 *  global canon, and spec.html once approved. Bare names match as whole path
 *  SEGMENTS (never substrings): "src/AGENTS.md.notes/x.md" is not a contract file.
 *  Absolute literals stay substring. */
/** Governance files by name, wherever they sit. The governed root is the outermost
 *  governed ancestor, so a config written above the repo (or a hook in a nested one)
 *  would otherwise move the root out from under the session. The host carriers are here
 *  too: a carrier rewritten, or a settings file with `disableAllHooks`, ungoverns the next
 *  session even when this one never wrote a governed file. */
const GOVERNANCE_FILE = new RegExp([
  String.raw`(?:^|/)\.ai-engineering/(?:config\.toml|overrides\.toml|ai-eng\.lock|arch\.rules\.json)$`,
  String.raw`(?:^|/)\.git/(?:hooks(?:/|$)|config$)`,
  String.raw`(?:^|/)\.github/hooks(?:/|$)`,
  String.raw`(?:^|/)\.github/copilot/settings(?:\.local)?\.json$`,
  String.raw`(?:^|/)\.claude/settings(?:\.local)?\.json$`,
  String.raw`(?:^|/)\.cursor/hooks\.json$`,
  String.raw`(?:^|/)\.codex/hooks\.json$`,
  String.raw`(?:^|/)\.(?:opencode/plugins|agents/hooks)/ai-eng[^/]*$`,
].join("|"), "i");

/** Case-folded on purpose: macOS and Windows filesystems ignore case, so
 *  `.Ai-Engineering/CONFIG.TOML` is the governed file there. On Linux the fold over-denies. */
function offendingPath(paths: ProtectedPaths, rawText: string): string | null {
  const text = slashed(rawText).toLowerCase();
  // The directory, as the last segment only. A child of it is the session's material, so
  // this cannot be a substring test: `.ai-engineering/research/x.html` contains the
  // directory and is not it.
  for (const path of paths.terminal) {
    const segment = new RegExp(`(^|/)${slashed(path).toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`);
    if (segment.test(text)) return path;
  }
  for (const path of paths.literals) {
    const bare = path === basename(path);
    if (bare) {
      // Match as a whole path segment: the text ends with the name after / or start.
      const segment = new RegExp(`(^|/)${path.toLowerCase().replace(/\./g, "\\.")}$`);
      if (segment.test(text)) return path;
      continue;
    }
    if (!text.includes(slashed(path).toLowerCase())) continue;
    return path;
  }
  if (GOVERNANCE_FILE.test(text)) return rawText.split(/\s+/).at(-1) ?? rawText;
  return null;
}

/** The protected path a file target lands on, judged from every directory it could be
 *  relative to: the repo root and the shell's own cwd (a session that cd'd into a
 *  subdirectory names `../.ai-engineering/config.toml`). */
function offendingTarget(paths: ProtectedPaths, target: string, bases: string[]): string | null {
  const expanded = expandTilde(target);
  for (const base of bases) {
    const resolved = isAbsolute(expanded) ? resolve(expanded) : resolve(base, expanded);
    // macOS: /var is a symlink of /private/var — canonicalize BEFORE the match, or
    // the tmpdir alias of a governed path evades (same canon the command branch uses).
    let canonical = resolved;
    try {
      canonical = localRealpath(resolved);
    } catch {
      // Not-yet-existing file: canonicalize the longest existing prefix.
      let prefix = parse(resolved).root;
      for (const part of resolved.slice(prefix.length).split(sep)) {
        const next = join(prefix, part);
        try {
          prefix = localRealpath(next);
        } catch {
          prefix = next;
        }
      }
      canonical = prefix;
    }
    const found = [canonical, resolved, expanded, target].map((form) => offendingPath(paths, form)).find((hit) => hit != null);
    if (found) return found;
  }
  return null;
}

function governedFileReason(target: string): string {
  return `${target} is part of what governs this session — it is how the rules reach you and how what happens here is recorded. Changing it from inside the session it governs is not a change a session gets to make. A person edits it, in a diff, in a pull request.`;
}

export function runSelfProtect(payload: Payload, repoRoot: string | null): GuardResult {
  const paths = protectedPaths(repoRoot);
  const args = payload.tool_input;
  const cwd = typeof payload["cwd"] === "string" && payload["cwd"].length > 0 ? payload["cwd"] : null;
  const bases = [...new Set([repoRoot ?? process.cwd(), ...(cwd === null ? [] : [cwd])])];
  // A patch names many files; every one of them is judged, not just the first.
  const targets = [args["file_path"] ?? args["path"], ...(Array.isArray(args["file_paths"]) ? args["file_paths"] : [])];
  for (const target of targets) {
    if (typeof target !== "string" || target.length === 0) continue;
    if (offendingTarget(paths, target, bases)) return { deny: true, reason: governedFileReason(target) };
  }
  const rawCommand = args["command"];
  if (typeof rawCommand === "string" && rawCommand.length > 0) {
    // `${IFS}` is a space to the shell; left as text it glues `rm${IFS}path` into one word.
    // PowerShell escapes with a backtick and separates paths with `\`.
    const isPowerShell = payload.tool_name === "PowerShell";
    const spaced = rawCommand.replace(/\$\{IFS\}|\$IFS(?![\w])/g, " ");
    const command = isPowerShell ? spaced.replace(/`(.)/gs, "$1").replace(/\\/g, "/") : spaced;
    // Codex runs apply_patch as a shell heredoc: its headers are the files it writes.
    if (command.includes("*** Begin Patch")) {
      let patched: string[];
      try {
        patched = embeddedPatchPaths(command);
      } catch {
        return { deny: true, reason: "this command carries a patch whose files cannot be read safely. Use well-formed *** Begin Patch / *** End Patch blocks." };
      }
      const governed = patched.find((target) => offendingTarget(paths, target, bases) !== null);
      if (governed !== undefined) return { deny: true, reason: governedFileReason(governed) };
    }
    if (isRestrictedCliCommand(command)) {
      return {
        deny: true,
        reason: "this command invokes a governance-changing or internal ai-eng verb. Run it from outside the governed agent session.",
      };
    }
    // macOS: /var is a symlink of /private/var — paths must be canonicalized
    // BEFORE the substring test, or the agent evades by writing the tmpdir alias.
    // The command branch shares the canonicalization above.
    const canonPath = (target: string): string => {
      // Canonicalize the longest existing prefix; a not-yet-created file inherits the
      // real prefix of its directory (rm -rf into a symlinked tmpdir must not evade).
      const root = parse(target).root;
      const parts = target.slice(root.length).split(sep === "\\" ? /[\\/]/ : "/");
      let current = root === "" ? process.cwd() : root;
      for (const part of parts) {
        if (part === "" || part === ".") continue;
        if (part === "..") {
          current = join(current, "..");
          try {
            current = realpathSync(current);
          } catch {
            /* keep */
          }
          continue;
        }
        const next = join(current, part);
        try {
          current = realpathSync(next);
        } catch {
          current = next;
        }
      }
      return current;
    };
    const canon = (text: string, base: string): string => {
      const expanded = text.replace(/(^|[\s"'=])~\//g, `$1${machineBase()}/`);
      // Only a path that starts at a `/`: the tail of `.git/hooks/x` is not `/hooks/x`, and
      // on Windows rewriting it as one turns its `/` into `\`, hiding it from the relative rewrite.
      const absolute = expanded.replace(/(?<![\w.@+-])(\/[\w.@+-]+)+/g, (m) => canonPath(m));
      // A relative path escapes a substring test on absolute literals:
      // `> .git/hooks/pre-commit` never matches the absolute literal, so a session
      // can disarm the floor with a redirect or a chmod. Resolve every relative
      // path token against the repo root and the shell's cwd before judging.
      return absolute.replace(RELATIVE_PATH, (match, lead: string, token: string) => `${lead}${canonPath(join(base, token))}`);
    };
    const canonicalPaths: ProtectedPaths = {
      literals: paths.literals.map((p) => {
        try {
          return realpathSync(p);
        } catch {
          return p;
        }
      }),
      specPinned: paths.specPinned,
      // The same canon as the literals: an absolute entry left in its raw form never
      // matches a command whose path tokens were rewritten above. The relative form is
      // left alone on purpose — realpathSync would resolve it against the process cwd,
      // not against the repo being judged.
      terminal: paths.terminal.map((p) => {
        if (!isAbsolute(p)) return p;
        try {
          return realpathSync(p);
        } catch {
          return p;
        }
      }),
    };
    for (const base of bases) {
      const expandedCommand = canon(normalizeRedirects(command), base);
      const pieces = expandedCommand.split(SEPARATORS).filter((p) => p.trim().length > 0);
      for (let index = 0; index < pieces.length; index++) {
        const one = pieces[index]!;
        // A heredoc is one command spanning lines; what it writes is in the body below.
        const judged = one.includes("<<") ? pieces.slice(index).join(" ") : one;
        if (isRestrictedCliCommand(judged)) {
          return {
            deny: true,
            reason: "this command invokes a governance-changing or internal ai-eng verb. Run it from outside the governed agent session.",
          };
        }
        const found = writesTo(canonicalPaths, judged);
        if (found) {
          return {
            deny: true,
            reason: `this command writes to ${found}, which is part of what governs this session. A person changes that, in a reviewed diff — not the session it governs.`,
          };
        }
      }
    }
    const unreadable = judgeShell(command, { paths, bases, isPowerShell });
    if (unreadable !== null) {
      return {
        deny: true,
        reason: `this command cannot run here: ${unreadable}. Write the command out plainly, and leave governance files to a person. This check reads the shell; it is not a sandbox.`,
      };
    }
  }
  return undefined;
}
