// --no-verify, and everything else that skips .git/hooks — plus every linter silence
// too, because silencing a check is the same act as skipping a hook.

import { basename, resolve, isAbsolute, join } from "node:path";
import { realpathSync } from "node:fs";
import type { Payload } from "../payload.ts";
import { argumentWords, COMMAND_PREFIXES, commandIndex, fileRedirectTargets, inlineShellPrograms, normalizeRedirects, RESERVED_WORDS, shellSegments, shellWords, SUBSTITUTION, unquoteShell, type ShellSegment, type ShellWord } from "./shell.ts";

type Skip = { pattern: RegExp; label: string };

const SKIPS: Skip[] = [
  { pattern: /\bHUSKY=0\b|\bPRE_COMMIT_ALLOW_NO_VERIFY\b|\bSKIP_HOOKS\b/, label: "an environment flag" },
  // Config from the environment or another file can point core.hooksPath anywhere without
  // naming it on this line.
  { pattern: /\bGIT_CONFIG_(?:COUNT|KEY_\d+|VALUE_\d+|PARAMETERS|GLOBAL|SYSTEM)\b|\bGIT_CONFIG\b|--config-env\b/, label: "git config from the environment" },
  { pattern: /\bgit\b[^|;&]*\binclude(?:if\.[^\s=]*)?\.path\b/i, label: "a git config include" },
  { pattern: /\brm\b[^|;&]*\.git\/hooks/, label: "deleting .git/hooks" },
];

/** Read only when the shell grammar cannot be: the token check below is the precise one. */
const RAW_SKIPS: Skip[] = [
  // git accepts any unique prefix of a long option: `--no-veri` is `--no-verify`.
  { pattern: /\bgit\b[^|;&]*\b(commit|push|merge|rebase|am|pull)\b[^|;&]*--no-veri/, label: "--no-verify" },
  { pattern: /\bgit\b[^|;&]*\bcommit\b[^|;&]*(?<![\w-])-[a-zA-Z]*n/, label: "git commit -n" },
];

const HOOKED = new Set(["commit", "push", "merge", "pull", "rebase", "am", "cherry-pick", "revert"]);
/** Options whose next word is a value (a message, a file, an author), never an option. */
const VALUE_OPTIONS = new Set(["-m", "--message", "-F", "--file", "-t", "--template", "--author", "--date", "--trailer", "--cleanup", "-C", "--reuse-message", "-c", "--reedit-message", "--fixup", "--squash"]);
const GLOBAL_VALUE_OPTIONS = new Set(["-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env", "--super-prefix", "--attr-source"]);

const XARGS_STDIN = "xargs completing git arguments from stdin";

/** Same option-value spellings commandIndex consumes. A drift here would read a
 *  prefix value as the program (`sudo -u xargs` is a user, not xargs). */
function prefixTakesValue(prefix: string, option: string): boolean {
  if (prefix === "xargs") return /^-[0-9A-Za-z]*[aIiLlnsPEed]$/.test(option);
  if (prefix === "sudo") return /^-[A-Za-z]*[ugCDhpRrT]$/.test(option);
  if (prefix === "doas") return /^-[A-Za-z]*[uC]$/.test(option);
  if (prefix === "env") return /^(?:-[A-Za-z]*[uCS]|--(?:split-string|unset|chdir))$/.test(option);
  if (prefix === "nice") return option === "-n";
  if (prefix === "timeout") return /^-[sk]$/.test(option);
  if (prefix === "stdbuf") return /^-[ioe]$/.test(option);
  if (prefix === "exec") return option === "-a";
  return false;
}

/** When xargs builds this git command, the words it appends are not on the line.
 *  `placeholder` is the -I / -i / --replace token stdin is substituted for. */
function xargsFeed(words: ShellWord[], gitAt: number): { invokes: boolean; placeholder: string | undefined } {
  let index = 0;
  let sawXargs = false;
  let placeholder: string | undefined;
  while (index < words.length) {
    const value = words[index]!.value;
    const name = basename(value);
    if (RESERVED_WORDS.has(value) || /^[A-Za-z_]\w*\+?=/.test(value)) {
      index++;
      continue;
    }
    if (!COMMAND_PREFIXES.has(name)) return { invokes: sawXargs && index === gitAt, placeholder };
    if (name === "xargs") sawXargs = true;
    const prefix = name;
    index++;
    while (index < words.length && /^(?:-|[A-Za-z_]\w*=|\d+(?:\.\d+)?[smhd]?$)/.test(words[index]!.value)) {
      const option = words[index]!.value;
      if (prefix === "xargs") {
        const attached = /^(?:-I|-J|-i|--replace=)(.+)$/.exec(option)?.[1];
        if (attached !== undefined) placeholder = attached;
        else if (option === "-i" || option === "--replace") placeholder = "{}";
        else if ((option === "-I" || option === "-J") && words[index + 1] !== undefined) placeholder = words[index + 1]!.value;
      }
      index += prefixTakesValue(prefix, option) ? 2 : 1;
    }
  }
  return { invokes: false, placeholder };
}

/** stdin can still name the hooked subcommand when the line has none, or when the
 *  subcommand word is the xargs placeholder (`xargs git`, `xargs -I{} git {}`). */
function xargsHidesHook(words: ShellWord[], gitAt: number, sub: string): boolean {
  const feed = xargsFeed(words, gitAt);
  if (!feed.invokes) return false;
  return sub === "" || (feed.placeholder !== undefined && sub === feed.placeholder);
}

/** The hook skip a hooked git command spells as the shell will read it, or null. A message
 *  that mentions `-n` or `--no-verify` is prose; `$x`, `$(…)` or a glob in an option slot is
 *  an option computed at run time, which the shell could turn into `--no-verify`.
 *  Undefined: the grammar could not be read, so the raw patterns decide. */
function gitHookSkip(command: string, depth = 0): string | null | undefined {
  if (depth > 3) return "git aliases nested too deep to read";
  const segments = shellSegments(normalizeRedirects(command));
  if (segments === null) return undefined;
  for (const segment of segments) {
    const words = argumentWords(segment.text);
    const commandAt = commandIndex(words.map((word) => word.value));
    // Every `git` word is judged, not only the one in command position: a wrapper this
    // reader does not know (`chronic git commit -n`) still runs git with its flags.
    for (let gitAt = 0; gitAt < words.length; gitAt++) {
      if (basename(words[gitAt]!.value) !== "git") continue;
      const skip = gitInvocationSkip(segment, words, gitAt, gitAt !== commandAt, depth);
      if (skip) return skip;
    }
  }
  return null;
}

/** The hook skip of the git invocation whose `git` word stands at `gitAt`, or null. When
 *  `git` is not the command name, the first hooked subcommand after it is the one judged. */
function gitInvocationSkip(segment: ShellSegment, words: ShellWord[], gitAt: number, isWrapped: boolean, depth: number): string | null {
  const environment = words.slice(0, gitAt).map((word) => word.value);
  let position = gitAt + 1;
  const globals: string[] = [];
  while (position < words.length && words[position]!.value.startsWith("-")) {
    const option = words[position]!.value;
    const takesNext = GLOBAL_VALUE_OPTIONS.has(option);
    globals.push(takesNext ? `${option}=${words[position + 1]?.value ?? ""}` : option);
    position += takesNext ? 2 : 1;
  }
  if (isWrapped && !HOOKED.has(words[position]?.value ?? "")) {
    const hooked = words.findIndex((word, at) => at > position && HOOKED.has(word.value));
    if (hooked >= 0) position = hooked;
  }
  const sub = words[position]?.value ?? "";
  // An alias is a command git will run later under another name: judge what it expands to.
  const aliases = globals.map((option) => /^-c=?(alias\.[^=]+)=(.*)$/s.exec(option.replace(/^-c(?=[^=])/, "-c=")))
    .filter((match) => match !== null).map((match) => match[2]!);
  if (sub === "config") {
    const rest = words.slice(position + 1).map((word) => word.value).filter((value) => !value.startsWith("-"));
    if (/^alias\./i.test(rest[0] ?? "") && rest[1] !== undefined) aliases.push(rest[1]);
  }
  for (const alias of aliases) {
    const expanded = gitHookSkip(alias.startsWith("!") ? alias.slice(1) : `git ${alias}`, depth + 1);
    if (expanded) return expanded;
  }
  if (!HOOKED.has(sub)) {
    if (xargsHidesHook(words, gitAt, sub)) return XARGS_STDIN;
    return null;
  }
  // Another git directory, exec path or config home is another set of hooks.
  if (environment.some((value) => /^(?:GIT_DIR|GIT_COMMON_DIR|GIT_EXEC_PATH|GIT_TEMPLATE_DIR|HOME|XDG_CONFIG_HOME)=/.test(value))
    || globals.some((option) => /^--(?:git-dir|exec-path)(?:=|$)/.test(option))) {
    return "pointing git at another directory or config";
  }
  const takesValue = (value: string): boolean => VALUE_OPTIONS.has(value) || /^-[a-zA-Z]*[mFtCc]$/.test(value);
  // A `$(…)` may name a ref from a read-only git query (`git push origin "$(git branch
  // --show-current)"`); anywhere else a computed word could be `--no-verify`.
  const isGitQuery = (word: ShellWord): boolean =>
    word.value.includes(SUBSTITUTION) && segment.substitutions.every((inner) => /^git\s+(?:rev-parse|branch|symbolic-ref|describe)\b/.test(inner));
  // Unquoted, `$x`, `*` and `{a,b}` become several words — a message value included:
  // `-m {x,--no-verify}` is `-m x --no-verify`.
  const splitsIntoWords = (word: ShellWord): boolean => /[$`*?[]|\{[^}]*,/.test(word.unquoted);
  for (let at = position + 1; at < words.length; at++) {
    const word = words[at]!;
    const value = word.value;
    if (isGitQuery(word)) continue;
    if (/[$`]/.test(value) || splitsIntoWords(word)) return "an option computed at run time";
    if (takesValue(value)) {
      if (sub === "commit" && /^-[a-zA-Z]*n[a-zA-Z]*$/.test(value)) return "git commit -n";
      at++;
      const optionValue = words[at];
      if (optionValue !== undefined && !isGitQuery(optionValue) && splitsIntoWords(optionValue)) return "an option computed at run time";
      continue;
    }
    if (value.startsWith("--no-veri")) return "--no-verify";
    if (sub === "commit" && /^-[a-zA-Z]*n[a-zA-Z]*$/.test(value)) return "git commit -n";
  }
  // Appended by xargs, so they are not words on this line: a pipe, -I{}, or a
  // process substitution feeding xargs. A non-hooked utility stays allowed
  // (`git ls-files | xargs wc -l`, `xargs git status`).
  if (xargsFeed(words, gitAt).invokes) return XARGS_STDIN;
  return null;
}

const SILENCES: RegExp[] = [
  /\/\/\s*eslint-disable(?!-next-line\s+prettier)/,
  /\/\*\s*eslint-disable(?!-next-line\s+prettier)/,
  /@ts-(ignore|expect-error|nocheck)/,
  /#\s*(noqa|nosec)\b/,
  /\/\/\s*oxlint-disable\b/,
  /\/\*\s*oxlint-disable\b/,
  /\/\/\s*biome-ignore\b/,
  /\/\*\s*biome-ignore\b/,
  /#\s*type:\s*ignore\b/,
  /\bNOLINTNEXTLINE\b/,
  /"\$allow-list"\s*:/,
];

// `-c core.hooksPath=x`, attached `-ccore.hooksPath=x`, and the bare `-c core.hooksPath`,
// which git reads as the boolean `true` — a relative directory with no hooks in it.
const INLINE = /-c\s*core\.hookspath(?:=(\S*))?(?=\s|$)/gi;

/** Every value this command would leave core.hooksPath at, as written. Unsetting is
 *  deliberately absent: no core.hooksPath at all is git's default .git/hooks — the
 *  floor's own location, since init wires no redirect there — so `--unset` is the safe
 *  direction (it restores the hooks, it does not stop them) and the set-or-change
 *  direction is the one this list exists to deny. */
function hooksPathTargetsIn(command: string): string[] {
  const words = command.split(/\s+/);
  const found: string[] = [];
  for (const match of command.matchAll(INLINE)) found.push((match[1] ?? "true").replace(/^["']|["']$/g, ""));
  if (words.some((w) => w === "config") && words.some((w) => w.toLowerCase() === "core.hookspath")) {
    // A read flag only covers the segment it stands in. The next segment can still set the key.
    if (!words.some((w) => ["--get", "--get-all", "--list"].includes(w))) {
      const index = words.findIndex((w) => w.toLowerCase() === "core.hookspath");
      const after = words.slice(index + 1).filter((w) => !w.startsWith("-"));
      if (after.length > 0) found.push(after[0]!.replace(/^["']|["']$/g, ""));
    }
  }
  return found;
}

/** Every value this command would leave core.hooksPath at, one shell segment at a time. */
export function hooksPathTargets(command: string): string[] {
  const segments = shellSegments(normalizeRedirects(command));
  const pieces = segments === null ? [command] : segments.map((segment) => segment.text);
  return pieces.flatMap(hooksPathTargetsIn);
}

export function hooksPathElsewhere(value: string, repoRoot: string | null): boolean {
  if (!value) return true;
  const root = repoRoot ?? process.cwd();
  try {
    const candidate = isAbsolute(value) ? value : resolve(root, value);
    // Only this repo's own .git/hooks, where the floor's shims live: /dev/null, /tmp, an
    // empty `src/` or a directory holding a look-alike pre-commit all stop the real hooks.
    const floor = join(root, ".git", "hooks");
    return realpathSync(candidate) !== realpathSync(floor);
  } catch {
    return true;
  }
}

export type GuardResult = { deny: true; reason: string } | { deny: false } | undefined;

/** Judge a Bash command for hook skips. */
function skipDenial(label: string): GuardResult {
  return {
    deny: true,
    reason: `${label} skips the git hooks, the floor every agent and every person in this repository commits through. Whatever the hooks would have said is what needs fixing. Run the command without it.`,
  };
}

export function checkBash(rawCommand: string, repoRoot: string | null, depth = 0): GuardResult {
  if (depth > 3) return skipDenial("a shell command nested too deep to read");
  const tokenSkip = gitHookSkip(rawCommand);
  if (tokenSkip) return skipDenial(tokenSkip);
  // `--no-ver''ify` and `\-\-no-verify` are `--no-verify` to the shell; judge both forms.
  const skips = tokenSkip === undefined ? [...SKIPS, ...RAW_SKIPS] : SKIPS;
  for (const command of [rawCommand, unquoteShell(rawCommand)]) {
    const denied = checkBashForm(command, repoRoot, skips);
    if (denied) return denied;
  }
  // The raw patterns name what they recognise; a git command they miss is still unread.
  if (tokenSkip === undefined && /\bgit\b/.test(rawCommand)) return skipDenial("a git command whose quoting or expansion cannot be read");
  const written = silenceInWrites(rawCommand);
  if (written) return written;
  if (depth === 0) {
    for (const inner of inlineShellPrograms(rawCommand)) {
      const nested = checkBash(inner, repoRoot, depth + 1);
      if (nested) return nested;
    }
  }
  return undefined;
}

/** True when this segment invokes `tee` targeting at least one real file. */
function isTeeToFile(text: string): boolean {
  const words = argumentWords(text).map((word) => word.value);
  const at = commandIndex(words);
  if (basename(words[at] ?? "") !== "tee") return false;
  return words.slice(at + 1).some((arg) => !arg.startsWith("-") && !arg.startsWith("/dev/"));
}

/** A redirect or tee into a file carries the bytes a shell write puts on disk.
 *  Stderr redirects (`2>&1`, `2>/dev/null`) and commit-message heredocs are not file writes. */
function silenceInWrites(command: string): GuardResult {
  const segments = shellSegments(normalizeRedirects(command));
  if (segments === null) return undefined;
  for (let index = 0; index < segments.length; index++) {
    const segment = segments[index]!;
    const next = segments[index + 1];
    const pipesIntoTee = next !== undefined && next.isAfterPipe && isTeeToFile(next.text);
    const writesFile = fileRedirectTargets(shellWords(segment.text)).length > 0 || isTeeToFile(segment.text) || pipesIntoTee;
    if (!writesFile) continue;
    for (const heredoc of segment.heredocs) {
      const hit = checkContent(heredoc.body);
      if (hit) return hit;
    }
    const hit = checkContent(segment.text);
    if (hit) return hit;
  }
  return undefined;
}

function checkBashForm(command: string, repoRoot: string | null, skips: Skip[]): GuardResult {
  for (const target of hooksPathTargets(command)) {
    if (hooksPathElsewhere(target, repoRoot)) {
      return {
        deny: true,
        reason: `this points core.hooksPath at ${target || "nothing"} instead of the floor this install wires, so the git hooks stop running and nothing says so. Whatever the hooks would have said is what needs fixing.`,
      };
    }
  }
  const skip = skips.find((candidate) => candidate.pattern.test(command));
  return skip === undefined ? undefined : skipDenial(skip.label);
}

/** Judge file content for linter silences — the same act in the other vocabulary. */
export function checkContent(content: string): GuardResult {
  for (const rule of SILENCES) {
    if (rule.test(content)) {
      return {
        deny: true,
        reason:
          "this silences a check (eslint-disable / @ts-ignore / noqa / nosec / NOLINT / allow-list). Silencing a check is skipping a hook. If the skip is legitimate, .ai-engineering/overrides.toml with a reason — it lands in the receipt and the commit.",
      };
    }
  }
  return undefined;
}

function writtenChunks(input: Record<string, unknown>): string[] {
  const chunks: string[] = [];
  // An empty new_string is the edit. content beside it is not a second write.
  const primary = typeof input["new_string"] === "string" ? input["new_string"] : input["content"];
  if (typeof primary === "string" && primary.length > 0) chunks.push(primary);
  const source = input["new_source"];
  if (typeof source === "string" && source.length > 0) chunks.push(source);
  const edits = input["edits"];
  if (!Array.isArray(edits)) return chunks;
  for (const edit of edits) {
    if (edit === null || typeof edit !== "object" || Array.isArray(edit)) continue;
    const next = (edit as Record<string, unknown>)["new_string"];
    if (typeof next === "string" && next.length > 0) chunks.push(next);
  }
  return chunks;
}

export function runNoVerify(payload: Payload, repoRoot: string | null): GuardResult {
  const shells = new Set(["Bash", "PowerShell", "shell", "command"]);
  if (shells.has(payload.tool_name)) {
    const command = payload.tool_input["command"];
    if (typeof command === "string" && command.length > 0) return checkBash(command, repoRoot);
    return undefined;
  }
  for (const chunk of writtenChunks(payload.tool_input)) {
    const hit = checkContent(chunk);
    if (hit) return hit;
  }
  return undefined;
}
