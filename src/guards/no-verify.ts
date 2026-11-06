// --no-verify, and everything else that skips .git/hooks — plus every linter silence
// (§10's SILENCES row), because silencing a check is the same act as skipping a hook.

import { basename, resolve, isAbsolute, join } from "node:path";
import { realpathSync } from "node:fs";
import type { Payload } from "../payload.ts";
import { normalizeRedirects, shellSegments, shellWords, SUBSTITUTION, unquoteShell, type ShellWord } from "./shell.ts";

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
const RUN_PREFIXES = new Set(["sudo", "env", "command", "exec", "nohup", "time", "nice", "xargs"]);

/** The words git receives: the shell strips every redirection (`2>/dev/null`, `>log`,
 *  `<in`, `&>out`, `2>&1`) wherever it stands, so the operator and its target are not
 *  arguments and must never be read as the subcommand or an option's value. */
function argumentWords(text: string): ShellWord[] {
  const words = shellWords(text);
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
    let index = 0;
    while (index < words.length && (/^[A-Za-z_]\w*=/.test(words[index]!.value) || RUN_PREFIXES.has(basename(words[index]!.value)))) index++;
    if (basename(words[index]?.value ?? "") !== "git") continue;
    const environment = words.slice(0, index).map((word) => word.value);
    let position = index + 1;
    const globals: string[] = [];
    while (position < words.length && words[position]!.value.startsWith("-")) {
      const option = words[position]!.value;
      const takesNext = GLOBAL_VALUE_OPTIONS.has(option);
      globals.push(takesNext ? `${option}=${words[position + 1]?.value ?? ""}` : option);
      position += takesNext ? 2 : 1;
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
    if (!HOOKED.has(sub)) continue;
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
  }
  return null;
}

const SILENCES: RegExp[] = [
  /\/\/\s*eslint-disable(?!-next-line\s+prettier)/,
  /\/\*\s*eslint-disable(?!-next-line\s+prettier)/,
  /@ts-(ignore|expect-error|nocheck)/,
  /#\s*(noqa|nosec)\b/,
  /\bNOLINTNEXTLINE\b/,
  /"\$allow-list"\s*:/,
];

// `-c core.hooksPath=x`, attached `-ccore.hooksPath=x`, and the bare `-c core.hooksPath`,
// which git reads as the boolean `true` — a relative directory with no hooks in it.
const INLINE = /-c\s*core\.hookspath(?:=(\S*))?(?=\s|$)/gi;

/** Every value this command would leave core.hooksPath at, as written. Empty string
 *  means unset, which stops every hook in the repo and says nothing. */
export function hooksPathTargets(command: string): string[] {
  const words = command.split(/\s+/);
  const found: string[] = [];
  for (const match of command.matchAll(INLINE)) found.push((match[1] ?? "true").replace(/^["']|["']$/g, ""));
  if (words.some((w) => w === "config") && words.some((w) => w.toLowerCase() === "core.hookspath")) {
    if (words.some((w) => w.startsWith("--unset"))) {
      found.push("");
    } else if (!words.some((w) => ["--get", "--get-all", "--list"].includes(w))) {
      const index = words.findIndex((w) => w.toLowerCase() === "core.hookspath");
      const after = words.slice(index + 1).filter((w) => !w.startsWith("-"));
      if (after.length > 0) found.push(after[0]!.replace(/^["']|["']$/g, ""));
    }
  }
  return found;
}

/** Decided on the value, never on the verb: core.hooksPath may only name this repo's own
 *  .git/hooks. Resolved against the repo root first: a relative spelling of that
 *  directory is the same directory, and a string comparison would deny it. */
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

export function checkBash(rawCommand: string, repoRoot: string | null): GuardResult {
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

export function runNoVerify(payload: Payload, repoRoot: string | null): GuardResult {
  if (payload.tool_name === "Bash" || payload.tool_name === "PowerShell") {
    const command = payload.tool_input["command"];
    if (typeof command === "string" && command.length > 0) return checkBash(command, repoRoot);
    return undefined;
  }
  // Edit|Write|MultiEdit|NotebookEdit judge the content being written.
  const newString = payload.tool_input["new_string"] ?? payload.tool_input["content"] ?? "";
  if (typeof newString === "string" && newString.length > 0) return checkContent(newString);
  return undefined;
}
