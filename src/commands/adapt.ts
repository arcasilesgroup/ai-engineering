// `ai-eng adapt apply` — the only writer of the four files a session must not
// Edit. The skill shows config-proposal.html. A spoken yes runs this verb.
// self-protect stays: it still denies Write/Edit of those paths. This process
// is the person, the same seam as `ai-eng spec approve`.

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { home } from "../env.ts";
import { lockText, parseLock, sha256 } from "../install.ts";

export const PROPOSAL_RELATIVE = ".ai-engineering/config-proposal.html";

const ALLOWED = [
  "AGENTS.md",
  ".ai-engineering/arch.rules.json",
  ".ai-engineering/config.toml",
  ".ai-engineering/overrides.toml",
] as const;

/** Dropped from the lock after a successful apply. Recording the new bytes as
 *  "ours" makes the next `update` treat them as a safe template refresh and
 *  overwrite the project's layers. Absent from the lock, they are the user's. */
const OWNED_BY_PROJECT = [
  ".ai-engineering/arch.rules.json",
  ".ai-engineering/config.toml",
  ".ai-engineering/overrides.toml",
];

export function proposalPayload(files: Record<string, string>): string {
  const ordered: Record<string, string> = {};
  for (const key of Object.keys(files).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0))) ordered[key] = files[key]!;
  return JSON.stringify(ordered).replace(/</g, "\\u003c");
}

export function proposalHtml(files: Record<string, string>): string {
  const payload = proposalPayload(files);
  const hash = sha256(payload);
  return `<!doctype html>\n<meta name="ai-eng-proposal-sha256" content="${hash}">\n<script type="application/json" id="payload">${payload}</script>\n`;
}

function gitEnv(): NodeJS.ProcessEnv {
  if (process.env["GIT_CONFIG_GLOBAL"] !== undefined) return process.env;
  return { ...process.env, GIT_CONFIG_GLOBAL: join(home(), "gitconfig") };
}

function git(root: string, args: string[]): { status: number; stdout: string; stderr: string } {
  const result = spawnSync("git", args, { cwd: root, env: gitEnv(), encoding: "utf8" });
  return { status: result.status ?? 1, stdout: result.stdout ?? "", stderr: result.stderr ?? "" };
}

function fail(message: string): number {
  process.stderr.write(`${message}\n`);
  return 2;
}

function overrideMissingUntil(toml: string): boolean {
  const blocks = toml.split("[[guard.off]]").slice(1);
  return blocks.some((block) => !/^\s*until\s*=/m.test(block));
}

function releaseProjectFiles(root: string): void {
  const lockPath = join(root, ".ai-engineering", "ai-eng.lock");
  if (!existsSync(lockPath)) return;
  const lock = parseLock(readFileSync(lockPath, "utf8"));
  for (const path of OWNED_BY_PROJECT) delete lock.assets[path];
  writeFileSync(lockPath, lockText(lock));
}

/** Apply the proposal in `root`. Refuses before any write. */
export function adaptApply(root: string): number {
  const top = git(root, ["rev-parse", "--show-toplevel"]);
  if (top.status !== 0) return fail("adapt apply: not a git repo.");

  const name = git(root, ["config", "--get", "user.name"]).stdout.trim();
  const email = git(root, ["config", "--get", "user.email"]).stdout.trim();
  if (name.length === 0 || email.length === 0) {
    return fail("adapt apply: git user.name and user.email must both be set. Refusing to record an empty user.name.");
  }

  const proposalPath = join(root, PROPOSAL_RELATIVE);
  if (!existsSync(proposalPath)) return fail(`adapt apply: missing ${PROPOSAL_RELATIVE}.`);
  const html = readFileSync(proposalPath, "utf8");
  const recorded = /name="ai-eng-proposal-sha256" content="([0-9a-f]{64})"/.exec(html)?.[1];
  const payload = /<script type="application\/json" id="payload">([\s\S]*?)<\/script>/.exec(html)?.[1];
  if (!recorded || payload === undefined) return fail("adapt apply: the proposal has no sha256 or no payload.");
  if (sha256(payload) !== recorded) {
    return fail("adapt apply: the proposal bytes no longer match the sha256 recorded on the page.");
  }

  let files: Record<string, unknown>;
  try {
    files = JSON.parse(payload) as Record<string, unknown>;
  } catch {
    return fail("adapt apply: the payload is not JSON.");
  }

  const writes: Array<{ path: string; text: string }> = [];
  for (const [path, text] of Object.entries(files)) {
    if (!ALLOWED.includes(path as (typeof ALLOWED)[number])) return fail(`adapt apply: ${path} is not a file this verb writes.`);
    if (typeof text !== "string") return fail(`adapt apply: ${path} is not text.`);
    writes.push({ path, text });
  }
  const overrides = writes.find((entry) => entry.path === ".ai-engineering/overrides.toml");
  if (overrides && overrideMissingUntil(overrides.text)) {
    return fail("adapt apply: an override has no until. Refusing to write overrides.toml.");
  }

  for (const entry of writes) {
    const absolute = join(root, entry.path);
    mkdirSync(join(absolute, ".."), { recursive: true });
    writeFileSync(absolute, entry.text);
  }
  releaseProjectFiles(root);

  const toAdd = writes.map((entry) => entry.path);
  if (existsSync(join(root, ".ai-engineering", "ai-eng.lock"))) toAdd.push(".ai-engineering/ai-eng.lock");
  const added = git(root, ["add", "--", ...toAdd]);
  if (added.status !== 0) return fail(`adapt apply: git add failed.\n${added.stderr}`);

  const staged = git(root, ["diff", "--cached", "--quiet"]);
  if (staged.status === 0) {
    process.stdout.write("adapt apply: files already match the proposal. Nothing to commit.\n");
    return 0;
  }
  if (staged.status !== 1) return fail(`adapt apply: git diff failed.\n${staged.stderr}`);

  const message = [`adapt: apply the approved project config`, `Approved-by: ${name} <${email}>`];
  const commit = git(root, ["commit", "-m", message[0]!, "-m", message[1]!]);
  if (commit.status !== 0) return fail(`adapt apply: the commit hook refused the commit.\n${commit.stderr}${commit.stdout}`);
  process.stdout.write(`adapt apply: committed. Approved-by: ${name} <${email}>\n`);
  return 0;
}

export function adaptMain(args: string[]): number {
  const sub = args[0];
  if (sub !== "apply") {
    process.stderr.write("usage: ai-eng adapt apply\n");
    return 2;
  }
  return adaptApply(process.cwd());
}
