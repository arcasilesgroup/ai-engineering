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
// Not ported on purpose: the Jev semantic layer (an LLM deciding per call is a
// prompt where this repo requires code) and apply_patch parsing (a Codex-only
// heredoc form; the edit tools cover it here).

import { readFileSync, realpathSync } from "node:fs";
import { join, posix } from "node:path";
import { homedir, tmpdir } from "node:os";

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

/** The original skips /tmp because temp files are not system state; on macOS
 *  the temp dir lives under /var/folders, which the system-path rule would
 *  otherwise swallow — so the same skip covers both tmpdir spellings. Paths
 *  arrive lowercased (classification normalises), so the roots compare in
 *  lowercase too. */
const TEMP_ROOTS = [...new Set([tmpdir(), realpathSync(tmpdir())])].map((r) => r.replace(/\/$/, "").toLowerCase());

function isTempPath(resolved: string): boolean {
  return resolved === "/tmp" || resolved.startsWith("/tmp/") || TEMP_ROOTS.some((root) => resolved === root || resolved.startsWith(`${root}/`));
}

/** Four octal digits, or `0000`. An unusable mode denies everything — never
 *  falls open, because a typo in config must not become a silent policy hole. */
export function normalizeMode(mode: string | undefined, fallback: string = DEFAULT_MODE): string {
  const value = mode !== undefined && mode.length > 0 ? mode : fallback;
  if (value.length === 4 && [...value].every((c) => c >= "0" && c <= "7")) return value;
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
    .replace(/[;,)]+$/, "");
  if (path.length === 0) return "";
  if (path.split("/").includes("..")) return resolveParentSegments(path, cwd);
  if (path.startsWith("/") || path.startsWith("~")) return path;
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
 *  sends it to external. */
function resolveParentSegments(path: string, cwd: string): string {
  if (path === "~" || path.startsWith("~/")) {
    const home = homedir().toLowerCase();
    if (!home.startsWith("/")) return path;
    const landed = posix.resolve(home, path.slice(2));
    return landed === home || landed.startsWith(`${home}/`) ? `~${landed.slice(home.length)}` : landed;
  }
  if (path.startsWith("/")) return posix.normalize(path);
  if (path.startsWith("~") || !cwd.startsWith("/")) return path;
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
        : RE_EXTERNAL_PATH.test(resolved) || resolved.includes("..")
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
  segment.includes("curl -f ") ||
  segment.includes("curl -t ");

/** curl | bash — the network-execute form. */
const NETWORK_EXECUTE = (segment: string): boolean =>
  (segment.includes("| bash") ||
    segment.includes("| sh") ||
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
 *  segment with no resolvable path still costs a workspace write. */
const WRITES = (segment: string): boolean =>
  segment.includes(">") ||
  segment.includes("tee ") ||
  segment.startsWith("mkdir ") ||
  segment.startsWith("touch ") ||
  segment.startsWith("cp ") ||
  segment.startsWith("mv ") ||
  segment.startsWith("rm ") ||
  segment.includes(" rm ") ||
  segment.includes("sed -i") ||
  segment.includes(" -delete") ||
  segment.startsWith("git fetch") ||
  segment.startsWith("git pull") ||
  segment.startsWith("git clone") ||
  segment.startsWith("git commit") ||
  segment.startsWith("git add") ||
  segment.startsWith("git checkout") ||
  segment.startsWith("git merge") ||
  segment.startsWith("git rebase") ||
  segment.startsWith("git stash") ||
  segment.startsWith("npm install") ||
  segment.startsWith("pnpm install") ||
  segment.startsWith("yarn install") ||
  segment.startsWith("cargo build") ||
  segment.startsWith("go test") ||
  segment.startsWith("npm test");

/** A redirection, optionally fd-prefixed (`2>`, `{fd}>`): the operator and the target
 *  when it is attached. Heredocs (`<<`) and process substitution (`<(`, `>(`) are not
 *  file targets. `>&` comes before `>` so `>&1` reads as a descriptor copy. */
const REDIRECT = /^(?:\d+|\{\w+\})?(&>>?|>&|>>?[|!]?|<>|<&|<)(?![<(])(.*)$/;

/** `x>/etc/foo` is the word `x` and a redirect to /etc/foo, as the shell reads it.
 *  A quote before the operator may make it text, so that word is left whole. */
function splitAttachedRedirect(token: string): string[] {
  let at = token.search(/[<>]/);
  if (at <= 0 || /["'`]/.test(token.slice(0, at))) return [token];
  if (token[at - 1] === "&") at--;
  return at === 0 ? [token] : [token.slice(0, at), token.slice(at)];
}

function scanSegment(mask: { value: number }, segment: string, cwd: string): void {
  if (SYSTEM_EXECUTE(segment)) addMode(mask, SCOPE_SYSTEM, PERM_EXECUTE);
  if (SYSTEM_WRITE(segment)) addMode(mask, SCOPE_SYSTEM, PERM_WRITE);
  if (NETWORK_READ(segment)) addMode(mask, SCOPE_NETWORK, PERM_READ);
  if (NETWORK_WRITE(segment)) {
    addMode(mask, SCOPE_NETWORK, PERM_WRITE);
  } else if (NETWORK_EXECUTE(segment)) {
    addMode(mask, SCOPE_NETWORK, PERM_EXECUTE);
  }
  if (RE_ROOT_DELETE.test(segment) || RE_DEVICE_WRITE.test(segment)) {
    addMode(mask, SCOPE_SYSTEM, PERM_WRITE);
  }
  if (WORKSPACE_EXECUTE(segment)) addMode(mask, SCOPE_WORKSPACE, PERM_EXECUTE);

  let pathPermissions = PERM_READ;
  let flags = 0;
  if (WRITES(segment)) {
    pathPermissions = PERM_READ | PERM_WRITE;
    flags = 1;
  }

  let pending: { permissions: number; isDuplicate: boolean } | null = null;
  const judgeRedirect = (target: string, permissions: number, isDuplicate: boolean): void => {
    // `2>&1`, `<&0` and `>&-` copy or close a descriptor: they name no file.
    if (isDuplicate && /^(\d+|-)$/.test(target)) return;
    addPath(mask, target, permissions, cwd);
    flags = 3;
  };
  for (const token of segment.split(/\s+/).flatMap(splitAttachedRedirect)) {
    if (pending !== null) {
      judgeRedirect(token, pending.permissions, pending.isDuplicate);
      pending = null;
      continue;
    }
    const redirect = REDIRECT.exec(token);
    if (redirect !== null) {
      const operator = redirect[1]!;
      const target = redirect[2]!;
      const permissions = operator === "<>" ? PERM_READ | PERM_WRITE : operator.startsWith("<") ? PERM_READ : PERM_WRITE;
      const isDuplicate = operator === ">&" || operator === "<&";
      if (target.length === 0) pending = { permissions, isDuplicate };
      else judgeRedirect(target, permissions, isDuplicate);
    } else if (
      token.startsWith("/") ||
      token.startsWith("./") ||
      token.startsWith("../") ||
      token.startsWith("~/") ||
      RE_SENSITIVE_PATH.test(token)
    ) {
      addPath(mask, token, pathPermissions, cwd);
      flags = 3;
    } else if (token.includes("/") && !token.startsWith("-")) {
      const isUrl =
        token.startsWith("http://") ||
        token.startsWith("https://") ||
        token.startsWith("ftp://") ||
        token.includes("://") ||
        token.includes(":/");
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
        addPath(mask, token, pathPermissions, cwd);
        flags = 3;
      }
    }
  }
  if (flags === 1 && !segment.includes("/tmp/")) addMode(mask, SCOPE_WORKSPACE, PERM_WRITE);
}

function scanScript(script: string, cwd: string): number {
  const mask = { value: 0 };
  const joined = script.replace(/\\\n/g, " ");
  if (joined.includes("/dev/tcp")) addMode(mask, SCOPE_NETWORK, PERM_READ | PERM_WRITE);
  const normalized = joined.replaceAll("&&", "\n").replaceAll("||", "\n").replaceAll(";", "\n");
  for (const segment of normalized.split("\n").map((s) => s.trim())) {
    if (segment.length > 0) scanSegment(mask, segment, cwd);
  }
  return mask.value;
}

function maskToMode(mask: number): string {
  return `${(mask >> 9) & 7}${(mask >> 6) & 7}${(mask >> 3) & 7}${mask & 7}`;
}

/** The mode this command needs, as four octal digits. An empty command needs
 *  nothing; a command with no recognised shape costs a workspace read (the
 *  floor every shell call pays). */
export function classifyRequiredMode(command: string, cwd: string): string {
  if (command.length === 0) return "0000";
  const mask = scanScript(command.toLowerCase(), cwd.toLowerCase());
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
