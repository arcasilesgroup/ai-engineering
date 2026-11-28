// Command-scope policy — the classification core of bash-guard (MIT,
// github.com/lloydzhou/bash-guard src/policy.rs), ported and verified against
// the original: every expectation in tests/policy-guard.spec.ts was first
// confirmed by running policy.rs itself. A command is classified into scopes
// (system / external / network / workspace) × permissions (read 4 / write 2 /
// execute 1), as four octal digits, left to right: `4667` = workspace
// everything, network read+write, external read+write, system read. A command
// runs when its required bits are a subset of the configured mode; an invalid
// mode normalises to `0000` — the same fail-closed as a crashing guard.
//
// Departed from on purpose, so an agent's daily commands pass: a redirect writes only its
// own target (`2>&1` writes nothing), and an absolute verb or a `NAME=value` prefix still
// reads as the command it runs. A heredoc's lines are still judged as commands.
//
// Not ported on purpose: the Jev semantic layer (an LLM deciding per call is a
// prompt where this repo requires code) and apply_patch parsing (a Codex-only
// heredoc form; the edit tools cover it here).

import { readFileSync, realpathSync } from "node:fs";
import { join, posix } from "node:path";
import { homedir, tmpdir } from "node:os";
import { commandIndex, expandedSegments, inlineShellPrograms, normalizeRedirects, quotedSpanEnd, readCommands, readCommandsLenient, shellWords, stripRedirectWords, type ShellCommand } from "./shell.ts";

/** What every install and new project gets while config.toml says nothing. System read
 *  includes the paths this file calls sensitive (~/.ssh, .env, *.pem): reading them is
 *  allowed; writing or executing anything at system scope is not. */
export const DEFAULT_MODE = "4667";

const SCOPE_SYSTEM = 8;
const SCOPE_EXTERNAL = 4;
const SCOPE_NETWORK = 2;
const SCOPE_WORKSPACE = 1;

const PERM_READ = 4;
const PERM_WRITE = 2;
const PERM_EXECUTE = 1;
// Every scope at every permission: what a program the reader cannot read costs.
const STRICT_MODE = 0o7777;

const RE_ROOT_DELETE = /(^|[\s;|&])rm\s+-[^\s]*[rf][^\s]*\s+\/(\s|$|[*])/i;
const RE_SYSTEM_PATH = /(^|[\s"'`])(\/etc|\/usr|\/bin|\/sbin|\/var|\/library|\/system|\/dev)(\/|[\s"'`]|$)/i;
// The token|credential|secret arm is why this regex is case-insensitive per
// call site and why the trailing class keeps ` and ' apart — it is the
// original's, byte for byte where it matters.
const RE_SENSITIVE_PATH =
  /(^|[\s"'`])(~|\$home)\/(\.ssh|\.gnupg|\.aws|\.docker)(\/|[\s"'`]|$)|(^|[\s"'`])([^\s"'`]*\.(env|pem|key)|[^\s"'`]*(token|credential|secret)[^\s"'`]*)/i;
const RE_EXTERNAL_PATH = /(^|[\s"'`])(~|\$home)(\/|[\s"'`]|$)|(^|[\s"'`])\/[A-Za-z0-9._-]/i;
const RE_DEVICE_WRITE =
  /(^|[\s])(of=|>|1>|>>|1>>)\s*\/dev\/(sd[a-z][0-9]*|disk[0-9]+|rdisk[0-9]+|nvme[0-9]+n[0-9]+(p[0-9]+)?|vd[a-z][0-9]*|xvd[a-z][0-9]*|hd[a-z][0-9]*)([\s]|$)/i;

// A win32 drive (`c:/…`) or a UNC share (`//server/share`): after backslash
// normalisation these are the spellings the POSIX root rules cannot name, so a
// path carrying one is never silently read as the workspace.
const RE_WIN32_ROOT = /^[a-z]:\/|^\/\//i;

/** A descriptor copy or close: the shell reader respells `2>&1` as the file fd 1 is. */
const DESCRIPTOR_TARGET = /^\/dev\/fd\/(?:\d+|-)$/;

/** The original skips /tmp because temp files are not system state; on macOS
 *  the temp dir lives under /var/folders, which the system-path rule would
 *  otherwise swallow — so the same skip covers both tmpdir spellings. Paths
 *  arrive lowercased (classification normalises), so the roots compare in
 *  lowercase too. */
const TEMP_ROOTS = [...new Set([tmpdir(), realpathSync(tmpdir())])].map((r) => r.replace(/\/$/, "").replaceAll("\\", "/").toLowerCase());

function isTempPath(resolved: string): boolean {
  return resolved === "/tmp" || resolved.startsWith("/tmp/") || TEMP_ROOTS.some((root) => resolved === root || resolved.startsWith(`${root}/`));
}

/** Four octal digits, or `0000`. An unusable mode denies everything — never
 *  falls open, because a typo in config must not become a silent policy hole. */
export function normalizeMode(mode: string | undefined, fallback: string = DEFAULT_MODE): string {
  const value = mode !== undefined && mode.length > 0 ? mode : fallback;
  if (/^[0-7]{4}$/.test(value)) return value;
  return "0000";
}

export function modeAllows(allowedMode: string, requiredMode: string): boolean {
  const allowed = Number.parseInt(normalizeMode(allowedMode, "0000"), 8) || 0;
  const required = Number.parseInt(normalizeMode(requiredMode, "0000"), 8) || 0;
  return (required & (0o7777 ^ allowed)) === 0;
}

export function denialReason(requiredMode: string, allowedMode: string): string {
  return (
    `blocked by the command-scope policy: this command needs ${requiredMode} and the mode allows ${allowedMode} ` +
    "(mode = system/external/network/workspace, bits = 4:read 2:write 1:execute). " +
    "A person widens guards.policy_mode in .ai-engineering/config.toml, in a reviewed diff."
  );
}

/** The configured mode, or the default. Read from the repo being judged, not
 *  from the process cwd: an in-process host judges many repos in one run. */
export function policyModeFor(root: string | null): string {
  if (!root) return DEFAULT_MODE;
  try {
    const doc = Bun.TOML.parse(readFileSync(join(root, ".ai-engineering", "config.toml"), "utf8")) as Record<string, unknown>;
    const guards = doc["guards"];
    const mode = guards !== null && typeof guards === "object" && !Array.isArray(guards)
      ? (guards as Record<string, unknown>)["policy_mode"]
      : undefined;
    return typeof mode === "string" ? mode : DEFAULT_MODE;
  } catch {
    return DEFAULT_MODE;
  }
}

function addMode(mask: { value: number }, scopes: number, permissions: number): void {
  let bits = 0;
  if ((scopes & SCOPE_SYSTEM) !== 0) bits |= permissions << 9;
  if ((scopes & SCOPE_EXTERNAL) !== 0) bits |= permissions << 6;
  if ((scopes & SCOPE_NETWORK) !== 0) bits |= permissions << 3;
  if ((scopes & SCOPE_WORKSPACE) !== 0) bits |= permissions;
  mask.value |= bits;
}

/** Relative paths resolve against the session cwd so `cat src/x.py` and
 *  `cat /repo/src/x.py` classify the same. A `..` segment is resolved before
 *  scoping; a path that merely contains `..` inside a segment (`./...`) stays
 *  unresolved and lands in external — the original's rule, and the one that
 *  classifies `go test ./...` as external read+write. */
function resolvePath(rawPath: string, cwd: string): string {
  const path = rawPath
    .replace(/^["']+|["']+$/g, "")
    .replace(/^of=/, "")
    .replace(/[;,)]+$/, "")
    // Windows paths arrive with `\`; everything below, including the win32 root
    // test, reasons in the `/` form.
    .replaceAll("\\", "/");
  if (path.length === 0) return "";
  if (path.split("/").includes("..")) return resolveParentSegments(path, cwd);
  if (RE_WIN32_ROOT.test(path) || path.startsWith("/") || path.startsWith("~")) return path;
  if (cwd.length === 0) return path;
  if (path.startsWith("./") || path.startsWith("../")) {
    if (path.includes("..")) return path;
    return `${cwd}/${path.replace(/^\.+/, "")}`;
  }
  return `${cwd}/${path}`;
}

/** A `..` segment moves the path, so the scope is judged where it lands: `x/../../y`
 *  from the repo is outside it, `/tmp/../etc` is /etc. `~/` resolves against the home
 *  directory and is written back as `~/…` so the sensitive-path rule still reads it.
 *  With no absolute cwd to resolve against the path stays as written, and its `..`
 *  sends it to external. A win32 drive cwd (`c:/repo`) joins and normalises the same way. */
export function resolveParentSegments(path: string, cwd: string, homeDirectory = homedir()): string {
  if (path === "~" || path.startsWith("~/")) {
    // Git Bash spells the Windows home `C:\Users\me` as `/c/users/me`; left as written, a
    // `..` detour (`~/x/../.ssh/id_rsa`) would never be read back as `~/.ssh`.
    const home = homeDirectory.toLowerCase().replaceAll("\\", "/").replace(/^([a-z]):/, "/$1");
    if (!home.startsWith("/")) return path;
    const landed = posix.resolve(home, path.slice(2));
    return landed === home || landed.startsWith(`${home}/`) ? `~${landed.slice(home.length)}` : landed;
  }
  if (path.startsWith("/") || RE_WIN32_ROOT.test(path)) return posix.normalize(path);
  if (path.startsWith("~") || !(cwd.startsWith("/") || RE_WIN32_ROOT.test(cwd))) return path;
  if (RE_WIN32_ROOT.test(cwd) && !cwd.startsWith("/")) return posix.normalize(`${cwd}/${path}`);
  return posix.resolve(cwd, path);
}

function addPath(mask: { value: number }, rawPath: string, permissions: number, cwd: string): void {
  const resolved = resolvePath(rawPath, cwd);
  if (resolved.length === 0 || isTempPath(resolved) || resolved === "/dev/null" || resolved.startsWith("&")) {
    return;
  }
  const scope = resolved.startsWith("/dev/tcp")
    ? SCOPE_NETWORK
    : resolved === "/" || resolved === "/*" || RE_SENSITIVE_PATH.test(resolved) || RE_SYSTEM_PATH.test(resolved)
      ? SCOPE_SYSTEM
      : cwd.length > 0 && (resolved === cwd || resolved.startsWith(`${cwd}/`))
        ? SCOPE_WORKSPACE
        : RE_EXTERNAL_PATH.test(resolved) || resolved.includes("..") || RE_WIN32_ROOT.test(resolved)
          ? SCOPE_EXTERNAL
          : SCOPE_WORKSPACE;
  addMode(mask, scope, permissions);
}

const NETWORK_READ = (segment: string): boolean =>
  segment.includes("curl ") ||
  segment.includes("wget ") ||
  segment.includes("http ") ||
  segment.includes("https://") ||
  segment.includes("http://") ||
  segment.startsWith("git clone") ||
  segment.startsWith("git fetch") ||
  segment.startsWith("git pull") ||
  segment.startsWith("git ls-remote");

const NETWORK_WRITE = (segment: string): boolean =>
  segment.startsWith("git push") ||
  segment.includes("scp ") ||
  segment.includes("curl -d ") ||
  segment.includes("curl --data") ||
  // -T reads as -t and -F as -f once the classification lowercases, and the flag
  // may sit anywhere in curl's flag list, so the match is not anchored after `curl`.
  (segment.includes("curl ") &&
    [" -t ", " -f ", " --upload-file", " --form"].some((flag) => segment.includes(flag)));

/** curl | bash — the network-execute form. */
const NETWORK_EXECUTE = (segment: string): boolean =>
  (/\|[ \t]*(bash|sh|zsh)\b/.test(segment) ||
    segment.includes("eval ") ||
    segment.includes("source <(") ||
    segment.includes("bash -c $(") ||
    segment.includes("sh -c $(")) &&
  (segment.includes("curl ") || segment.includes("wget ") || segment.includes("http://") || segment.includes("https://"));

const SYSTEM_EXECUTE = (segment: string): boolean =>
  /^(sudo|su|doas)(\s|$)/.test(segment) || /^(shutdown|reboot|halt|poweroff)/.test(segment);

const SYSTEM_WRITE = (segment: string): boolean =>
  /^(mkfs|fdisk|diskutil)/.test(segment) || /^mount |^umount /.test(segment);

const WORKSPACE_EXECUTE = (segment: string): boolean =>
  segment.startsWith("./") ||
  segment.startsWith("bash ") ||
  segment.startsWith("sh ") ||
  segment.startsWith("zsh ") ||
  segment.startsWith("python") ||
  segment.startsWith("node ") ||
  segment.startsWith("ruby ") ||
  segment.startsWith("perl ") ||
  segment.startsWith("npm test") ||
  segment.startsWith("npm run") ||
  segment.startsWith("make") ||
  segment.startsWith("cargo test") ||
  segment.startsWith("cargo build") ||
  segment.startsWith("go test") ||
  segment.startsWith("git commit") ||
  segment.startsWith("git add") ||
  segment.startsWith("git checkout") ||
  segment.startsWith("git merge") ||
  segment.startsWith("git rebase") ||
  segment.startsWith("git stash") ||
  segment.startsWith("git cherry-pick") ||
  segment.includes("function ") ||
  segment.includes("()") ||
  segment.includes("{") ||
  segment.includes(" if ") ||
  segment.startsWith("if ") ||
  segment.includes(" for ") ||
  segment.startsWith("for ") ||
  segment.includes(" while ") ||
  segment.startsWith("while ") ||
  segment.includes(" case ") ||
  segment.startsWith("case ") ||
  segment.includes(":(){:|:&};:");

/** A write-shaped segment: its path tokens are judged read+write, and a
 *  segment with no resolvable path still costs a workspace write. A redirect is not a
 *  shape: its own target is judged as the write, so `2>&1` writes nothing and
 *  `ls /usr/bin > out.txt` does not write /usr/bin (policy.rs counts both). */
const WRITES = (segment: string): boolean =>
  segment.includes("tee ") ||
  segment.startsWith("mkdir ") ||
  segment.startsWith("touch ") ||
  segment.startsWith("cp ") ||
  segment.startsWith("mv ") ||
  segment.startsWith("rm ") ||
  segment.includes(" rm ") ||
  segment.startsWith("del ") ||
  segment.includes(" del ") ||
  segment.startsWith("rd ") ||
  segment.includes(" rd ") ||
  segment.startsWith("chmod ") ||
  segment.startsWith("chown ") ||
  segment.startsWith("ln ") ||
  segment.startsWith("install ") ||
  segment.startsWith("truncate ") ||
  segment.startsWith("rsync ") ||
  segment.startsWith("dd ") ||
  segment.includes("sed -i") ||
  segment.includes(" -delete") ||
  // PowerShell's twins of the deleters and writers above.
  segment.includes("remove-item") ||
  segment.includes("set-content") ||
  segment.includes("new-item") ||
  segment.startsWith("git fetch") ||
  segment.startsWith("git pull") ||
  segment.startsWith("git clone") ||
  segment.startsWith("git checkout") ||
  segment.startsWith("git merge") ||
  segment.startsWith("git rebase") ||
  segment.startsWith("npm install") ||
  segment.startsWith("pnpm install") ||
  segment.startsWith("yarn install") ||
  segment.startsWith("cargo build") ||
  segment.startsWith("go test") ||
  segment.startsWith("npm test");

/** Git verbs that write only the repository's own index and history: their arguments
 *  are message data and pathspecs, never files the verb writes, so their tokens are
 *  judged read-only — a commit message that mentions a secret, or `git add` of a design
 *  file called tokens.json, is not a sensitive write. A secret staged this way is the
 *  commit floor's to stop (gitleaks), not this guard's. */
const WRITES_MESSAGE_VERBS = (segment: string): boolean =>
  segment.startsWith("git commit") || segment.startsWith("git stash") || segment.startsWith("git add");

/** The quoted spans of `text` that carry plain data — no `$`, no backtick, no way
 *  to expand into an argument — become one space: the shapes read the shell the
 *  command runs, not the prose a `-m` message quotes. Spans that could expand
 *  stay in, fail-closed. */
function blankDataQuotedSpans(text: string): string {
  let out = "";
  let at = 0;
  while (at < text.length) {
    const spanEnd = text[at] === "'" || text[at] === '"' ? quotedSpanEnd(text, at) : -1;
    if (spanEnd < at + 1 || spanEnd >= text.length) {
      out += text[at];
      at += 1;
      continue;
    }
    const body = text.slice(at + 1, spanEnd);
    out += body.includes("$") || body.includes("`") ? text.slice(at, spanEnd + 1) : " ";
    at = spanEnd + 1;
  }
  return out;
}

function commandLead(written: string): string {
  const words = stripRedirectWords(shellWords(normalizeRedirects(written)));
  const values = words.map((word) => word.value);
  const at = commandIndex(values);
  const names = values.slice(0, at).map((word) => word.split("/").pop() ?? word);
  const rest = words
    .slice(at)
    .map((word, index) => (index > 0 && word.isQuoted && !/[$`]/.test(word.value) ? " " : word.value))
    .join(" ");
  // A privilege wrapper is a prefix to commandIndex, and it is the thing this guard has to see.
  if (names.some((name) => name === "sudo" || name === "doas" || name === "su")) return `sudo ${rest}`.trim();
  return rest;
}

/** The modes the shapes read off one line of shell text, as written: a program name, a URL,
 *  a pipeline form or a destructive shape. A substitution, the command that holds it and
 *  the shell a pipeline hands it to are one shape, though the reader hands them over as
 *  separate commands, so this runs over the whole line as well as over each command. */
function shapeMask(written: string): number {
  const mask = { value: 0 };
  const lead = commandLead(written);
  // The shapes read `git push` however it is spelled: `/usr/bin/git push` and
  // `TMPDIR=x git push` run the same program (policy.rs reads neither as git push).
  const segment = written.replace(/^(?:[a-z_]\w*\+?=\S*\s+)*/, "").replace(/^\/\S*\/(?=[^\s/]+(?:\s|$))/, "");
  // The shapes judge the shell the command runs; quoted data (a `-m` message) is
  // not shell. Path tokens elsewhere keep their raw words: `rm "~/.ssh/id"` stays a
  // sensitive write.
  const text = blankDataQuotedSpans(segment);
  if (SYSTEM_EXECUTE(text) || SYSTEM_EXECUTE(lead)) addMode(mask, SCOPE_SYSTEM, PERM_EXECUTE);
  if (SYSTEM_WRITE(text) || SYSTEM_WRITE(lead)) addMode(mask, SCOPE_SYSTEM, PERM_WRITE);
  // The network shapes look for a URL anywhere, so they also read the prefix the
  // stripping drops: `X=https://… fetch $X | bash` keeps its URL there.
  const either = (shape: (segment: string) => boolean): boolean => shape(blankDataQuotedSpans(written)) || shape(text);
  if (either(NETWORK_READ)) addMode(mask, SCOPE_NETWORK, PERM_READ);
  if (either(NETWORK_WRITE)) addMode(mask, SCOPE_NETWORK, PERM_WRITE);
  if (either(NETWORK_EXECUTE)) addMode(mask, SCOPE_NETWORK, PERM_EXECUTE);
  if (RE_ROOT_DELETE.test(text) || RE_DEVICE_WRITE.test(text)) addMode(mask, SCOPE_SYSTEM, PERM_WRITE);
  if (WORKSPACE_EXECUTE(text)) addMode(mask, SCOPE_WORKSPACE, PERM_EXECUTE);
  return mask.value;
}

/** One command classified. The words and the redirections come from the one shell model,
 *  so a construct another guard reads is a construct this classifier reads too. `line` is
 *  the pipeline this command sits in: the shapes read `curl … | bash` as one shape. */
function scanCommand(mask: { value: number }, command: ShellCommand, line: string, cwd: string, isExpanded: boolean): void {
  const written = [line.trim(), ...command.segment.substitutions].join(" ").trim();
  const lead = commandLead(written);
  const verbAt = command.verbIndex;
  const segment = written.replace(/^(?:[a-z_]\w*\+?=\S*\s+)*/, "").replace(/^\/\S*\/(?=[^\s/]+(?:\s|$))/, "");
  const text = blankDataQuotedSpans(segment);
  mask.value |= shapeMask(written);

  let pathPermissions = PERM_READ;
  let flags = 0;
  // The writer is judged by the program it runs, whatever sits before it: a shell keyword
  // (`then /bin/rm …`), an env prefix or an absolute path.
  const writerShape = text
    .replace(/^(?:(?:then|do|else|elif|if|while|until|time|!|\{|\()\s+)+/, "")
    .replace(/^(?:[a-z_]\w*\+?=\S*\s+)*/, "")
    .replace(/^\/\S*\/(?=[^\s/]+(?:\s|$))/, "");
  if (WRITES(writerShape) || WRITES(lead)) {
    pathPermissions = PERM_READ | PERM_WRITE;
    flags = 1;
  } else if (WRITES_MESSAGE_VERBS(writerShape)) {
    // The write is the workspace itself, whatever the tokens judge: the message
    // is data and pathspecs. Commit writes it, stash writes it.
    addMode(mask, SCOPE_WORKSPACE, PERM_WRITE);
    flags = 1;
  }

  const judgeRedirect = (target: string, permissions: number): void => {
    // `2>&1`, `<&0` and `>&-` copy or close a descriptor, which the one reader respells
    // as the file the descriptor is: they name no path to scope.
    if (DESCRIPTOR_TARGET.test(target)) return;
    // A target the expansion could not resolve is not a known path: the name could have been
    // set in a branch the guards cannot read, so it is judged where it could land.
    if (isExpanded && /[$`]/.test(target)) {
      addMode(mask, SCOPE_SYSTEM, permissions);
      flags = 3;
      return;
    }
    addPath(mask, target, permissions, cwd);
    flags = 3;
  };
  // Every redirection the shell reads, judged by the permission its operator carries. The
  // model reports them, so `x>/etc/foo`, `{fd}>f` and `<>f` need no pattern here.
  for (const { operator, target } of command.redirects) {
    // A heredoc or a here-string feeds a program text; it names no file to scope.
    if (operator.startsWith("<<") || target === null || target.isOperator) continue;
    const permissions = operator === "<>" ? PERM_READ | PERM_WRITE : operator.startsWith("<") ? PERM_READ : PERM_WRITE;
    judgeRedirect(target.original, permissions);
  }
  // The paths the program names. Running a program reads it and never writes it:
  // `/usr/bin/git rm a` writes a, not git.
  for (const [at, word] of command.plain.entries()) {
    const token = word.original;
    const tokenPermissions = at === verbAt ? PERM_READ : pathPermissions;
    if (
      token.startsWith("/") ||
      token.startsWith("./") ||
      token.startsWith("../") ||
      token.startsWith("~/") ||
      RE_SENSITIVE_PATH.test(token)
    ) {
      addPath(mask, token, tokenPermissions, cwd);
      flags = 3;
    } else if (
      (token.includes("/") ||
        // A win32 raw path (`c:\…`, `\\server\…`) carries no `/`: it is still a path.
        RE_WIN32_ROOT.test(token.replaceAll("\\", "/"))) &&
      !token.startsWith("-")
    ) {
      const isUrl =
        token.startsWith("http://") ||
        token.startsWith("https://") ||
        token.startsWith("ftp://") ||
        token.includes("://") ||
        // A win32 drive (`c:/…`) also carries `:/`; it is a path, not a URL scheme.
        (token.includes(":/") && !RE_WIN32_ROOT.test(token));
      const isPath =
        !isUrl &&
        !token.endsWith(".exe") &&
        !token.endsWith(".sh") &&
        !token.includes("git") &&
        !token.includes("npm") &&
        !token.includes("cargo") &&
        !token.includes("python") &&
        !token.includes("node");
      if (isPath) {
        addPath(mask, token, tokenPermissions, cwd);
        flags = 3;
      }
    }
  }
  if (flags === 1 && !text.includes("/tmp/")) addMode(mask, SCOPE_WORKSPACE, PERM_WRITE);
}

function scanScript(script: string, cwd: string): number {
  const joined = script.replace(/\\\n/g, " ");
  const mask = { value: shapeMask(joined) };
  if (joined.includes("/dev/tcp")) addMode(mask, SCOPE_NETWORK, PERM_READ | PERM_WRITE);
  // `bash -c "…"` and the body of a heredoc handed to a shell run commands of their own.
  // The one reader already hands `$(…)` and backticks over as segments, so only the
  // interpreter's program needs asking for.
  const expansions = expandedSegments(script);
  const bodies = expansions.flatMap((text) => inlineShellPrograms(text));
  // The line as written still carries every `$name` the shell may fill in; the expanded
  // passes are the only ones that know which names the reader could not resolve.
  const passes = [
    { text: joined, isExpanded: false },
    ...expansions.map((text) => ({ text, isExpanded: true })),
    ...bodies.map((text) => ({ text, isExpanded: true })),
    ...bodies.flatMap(expandedSegments).map((text) => ({ text, isExpanded: true })),
  ];
  for (const { text, isExpanded } of passes) {
    if (text.trim().length === 0) continue;
    scanCommands(mask, text, cwd, isExpanded);
  }
  return mask.value;
}

/** One text judged command by command, with the program each command hands to an interpreter
 *  and the body of every heredoc it feeds judged the same way. A program the reader cannot
 *  read costs every scope the mode has, never one opaque workspace token. */
function scanCommands(mask: { value: number }, text: string, cwd: string, isExpanded: boolean, depth = 0): void {
  // A line whose quoting cannot be read is still judged by the words it shows.
  let pipeline = "";
  for (const command of readCommands(text) ?? readCommandsLenient(text)) {
    // A pipeline is one shape for the classification (`curl … | bash` is the
    // network-execute form); a `&&`, `||`, `;` or newline chain is not.
    pipeline = command.segment.isAfterPipe ? `${pipeline} | ${command.segment.text}` : command.segment.text;
    scanCommand(mask, command, pipeline, cwd, isExpanded);
    // A heredoc's lines are judged as commands, whoever reads them: text alone cannot
    // tell a commit message from a program.
    for (const { body } of command.segment.heredocs) scanCommands(mask, body, cwd, isExpanded, depth);
    if (depth >= 3) continue;
    for (const program of inlineShellPrograms(command.segment.text)) {
      if (readCommands(program) === null) mask.value |= STRICT_MODE;
      else scanCommands(mask, program, cwd, true, depth + 1);
    }
  }
}

function maskToMode(mask: number): string {
  return `${(mask >> 9) & 7}${(mask >> 6) & 7}${(mask >> 3) & 7}${mask & 7}`;
}

/** The mode this command needs, as four octal digits. An empty command needs
 *  nothing; a command with no recognised shape costs a workspace read (the
 *  floor every shell call pays). */
export function classifyRequiredMode(command: string, cwd: string): string {
  if (command.length === 0) return "0000";
  const mask = scanScript(command.toLowerCase(), cwd.toLowerCase().replaceAll("\\", "/"));
  return maskToMode(mask === 0 ? PERM_READ : mask);
}

/** The guard's whole decision for one shell command. */
export function evaluate(
  command: string,
  cwd: string,
  allowedMode: string,
): { allowed: boolean; required: string; allowedMode: string } {
  const required = classifyRequiredMode(command, cwd);
  const allowed = normalizeMode(allowedMode, DEFAULT_MODE);
  return { allowed: modeAllows(allowed, required), required, allowedMode: allowed };
}

/** Guard entry: deny with the person-facing reason, or undefined to allow. */
export function runPolicy(command: string, cwd: string, allowedMode: string): { deny: true; reason: string } | undefined {
  const decision = evaluate(command, cwd, allowedMode);
  if (decision.allowed) return undefined;
  return { deny: true, reason: denialReason(decision.required, decision.allowedMode) };
}
