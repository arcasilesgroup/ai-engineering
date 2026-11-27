// The git floor: what the 3-line shims call. Independent of every agent surface —
// this runs even for a person committing from Vim. gitleaks missing is HARD
// FAIL, never silent degradation.

import { execFileSync, spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { basename, dirname, join } from "node:path";
import { tmpdir } from "node:os";
import { repoRoot } from "../env.ts";
import { namedBase, namedBaseTrackingRef } from "../git/context.ts";
import { runGit } from "../git/run.ts";

type FloorResult = { ok: boolean; lines: string[] };

/** The install line both gitleaks hints print: pre-commit and pre-push must never drift
 *  apart, and the specs read this same source. Each one works without administrator
 *  rights first, because a managed PC may allow nothing above the user's own folders. */
export function gitleaksInstallHint(platform: NodeJS.Platform = process.platform): string {
  if (platform === "win32") {
    return "winget install --id Gitleaks.Gitleaks -e, or where winget is blocked, fetch gitleaks.exe with the curl and tar built into Windows into a folder on your user PATH (https://github.com/arcasilesgroup/ai-engineering/blob/main/docs/install.md, section Without administrator rights)";
  }
  if (platform === "darwin") return "brew install gitleaks";
  return "download the binary from the gitleaks releases page into ~/.local/bin (or, with sudo, apt install gitleaks)";
}

/** pre-commit: diff --check · gitleaks --staged · DECISIONS.md if >10 files or new dep. */
export function preCommit(cwd = repoRoot() ?? process.cwd()): FloorResult {
  const lines: string[] = [];
  const check = runGit(["diff", "--cached", "--check"], { cwd });
  if (check.status !== 0) {
    lines.push("diff --check found whitespace problems:");
    lines.push(`${check.stdout}${check.stderr}`.trim().replace(/\r\n?/g, "\n").replace(/\n+/g, " | "));
    return { ok: false, lines };
  }
  const leaks = stageSecrets(cwd);
  if (!leaks.ok) return { ok: false, lines: [...lines, ...leaks.lines] };
  lines.push(...leaks.lines);
  const decisions = decisionsBlock(cwd);
  if (!decisions.ok) return { ok: false, lines: [...lines, ...decisions.lines] };
  if (decisions.lines.length > 0) lines.push(...decisions.lines);
  return { ok: true, lines };
}

function whichGitleaks(): string | null {
  const probe = spawnSync("gitleaks", ["version"], { encoding: "utf8" });
  return probe.status === 0 ? "gitleaks" : null;
}

/** >10 files touched or a dependency changed → a DECISIONS.md block is required. */
function decisionsBlock(cwd: string): FloorResult {
  const nameOnly = runGit(["diff", "--cached", "--name-only"], { cwd }).stdout.trim();
  const files = nameOnly ? nameOnly.split("\n").filter((f) => f.length > 0) : [];
  const dependencyTouched = files.some((f) => /^(package\.json|Cargo\.toml|go\.mod|pyproject\.toml|Gemfile|composer\.json|pom\.xml|Package\.swift|.*\.csproj)$/.test(f));
  if (files.length <= 10 && !dependencyTouched) return { ok: true, lines: [] };
  const decisionsPath = join(cwd, "DECISIONS.md");
  if (!existsSync(decisionsPath)) {
    return { ok: false, lines: [`this commit touches ${files.length} files${dependencyTouched ? " (or a dependency)" : ""} and requires a DECISIONS.md block (§9.2) — none exists.`] };
  }
  const content = readFileSync(decisionsPath, "utf8");
  const blocks = content.split(/^## /m).length - 1;
  if (blocks === 0) {
    return { ok: false, lines: ["DECISIONS.md exists but carries no ## D-NNN block — add one (≤6 lines) or shrink the commit."] };
  }
  return { ok: true, lines: [] };
}

/** The staged scan's one exception: the allowlist `paths` exactly as they exist in
 *  HEAD's .gitleaksrc.toml — the reviewed baseline. A commit can widen the list and
 *  exploit it only in a LATER commit, never in the one that lands the widening, and
 *  only `paths` ever travels: this gate must not become a general trust in whatever
 *  config the working tree carries (pre-push loads the full file; this one stays
 *  narrow). No HEAD config, no parse, no paths → no exception: the default rules
 *  decide, which is the fail-narrow direction. The argv never changes — the
 *  contract test pins `dir --redact --no-banner --exit-code 1 <dir>` byte-exact. */

/** The dials of the staged exemption itself. When the staged diff touches any of them,
 *  the scan runs with NO exemption (no HEAD allowlist, no materialised
 *  .gitleaksignore): the editor of the allowlist cannot benefit from it, so a commit
 *  that widens the list while carrying its own secret — or its own fingerprint — is
 *  judged by the default rules. */
const ALLOWLIST_FILES = new Set([".gitleaksrc.toml", ".gitleaksignore", ".gitleaks.toml", "gitleaks.toml"]);

function headAllowlistEnv(cwd: string, scratch: string): NodeJS.ProcessEnv | undefined {
  const head = runGit(["show", "HEAD:.gitleaksrc.toml"], { cwd });
  if (head.status !== 0) return undefined;
  try {
    const parsed = Bun.TOML.parse(head.stdout) as { allowlist?: { paths?: unknown } };
    const paths = Array.isArray(parsed.allowlist?.paths)
      ? (parsed.allowlist.paths as unknown[]).filter((entry): entry is string => typeof entry === "string")
      : [];
    if (paths.length === 0) return undefined;
    const config = join(scratch, ".gitleaksrc.toml");
    writeFileSync(config, `[allowlist]\npaths = ${JSON.stringify(paths)}\n`);
    return { ...process.env, GITLEAKS_CONFIG: config };
  } catch {
    return undefined;
  }
}

function stageSecrets(cwd: string): FloorResult {
  const gitleaks = whichGitleaks();
  if (!gitleaks) {
    return {
      ok: false,
      lines: [
        "gitleaks is not installed — HARD FAIL, never silent degradation (§12.1).",
        `Install it: ${gitleaksInstallHint()}`,
      ],
    };
  }
  // `git --staged` scans 0 commits on a fresh HEAD and passes silently, so the
  // floor scans the files actually staged.
  const staged = runGit(["diff", "--cached", "--name-only", "--diff-filter=ACM"], { cwd }).stdout
    .split("\n")
    .map((f) => f.trim())
    .filter((f) => f.length > 0);
  if (staged.length === 0) return { ok: true, lines: [] };
  // The commit that edits the exemption dials is scanned without them (see
  // ALLOWLIST_FILES): basenames match because gitleaks honours a .gitleaksignore only
  // at the scan root, but a stray nested copy must not survive either.
  const isEditingAllowlist = staged.some((f) => ALLOWLIST_FILES.has(basename(f)));
  // The bytes git will commit, not the bytes on disk: a staged secret whose working
  // copy is overwritten would pass this gate and reach the commit (audit FLOOR-01).
  // `gitleaks git --staged` scans zero on a fresh HEAD, so the staged blobs are
  // materialised and scanned as files.
  const scratch = mkdtempSync(join(tmpdir(), "ai-eng-staged-"));
  const present: string[] = [];
  try {
    for (const file of staged) {
      // A materialised .gitleaksignore is an exemption the reviewed baseline never
      // carried: when the commit edits the dials, they never reach the scan at all.
      if (isEditingAllowlist && ALLOWLIST_FILES.has(basename(file))) continue;
      const blob = spawnSync("git", ["-C", cwd, "show", `:${file}`], { encoding: "buffer" });
      if (blob.status !== 0) continue;
      const copy = join(scratch, file);
      mkdirSync(dirname(copy), { recursive: true });
      writeFileSync(copy, blob.stdout);
      present.push(copy);
    }
    if (present.length === 0) return { ok: true, lines: [] };
    const args = ["dir", "--redact", "--no-banner", "--exit-code", "1", scratch];
    execFileSync(gitleaks, args, { cwd, stdio: "pipe", env: isEditingAllowlist ? undefined : headAllowlistEnv(cwd, scratch) });
    return { ok: true, lines: [] };
  } catch (error) {
    const e = error as { stdout?: unknown; stderr?: unknown; message?: string };
    const asText = (v: unknown): string => {
      if (Buffer.isBuffer(v)) return v.toString();
      if (typeof v === "string") return v;
      return "";
    };
    const out = `${asText(e.stdout)}\n${asText(e.stderr)}`.trim() || (e.message ?? "");
    const findings = out
      .split("\n")
      .filter((l) => l.startsWith("File:") || l.startsWith("RuleID:") || l.startsWith("Finding:"))
      .slice(0, 10)
      .join("\n");
    return { ok: false, lines: ["gitleaks: secret in the staged files → BLOCKED.", (findings || out.slice(0, 800)).split(scratch).join("<staged>")] };
  } finally {
    rmSync(scratch, { recursive: true, force: true });
  }
}
/** The eleven Conventional Commit types this repository's history is held to. One list, two
 *  askers: commit-msg judges the subject a person or an agent writes, and pre-push re-judges
 *  the subjects that arrive by a route the commit-msg hook never runs for — the pipeline
 *  writes its own fix commits, and it rewrites subjects after the commit exists. Both read
 *  the rule from here so the two doors can never disagree (R6). */
const CONVENTIONAL_SUBJECT = /^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9._/-]+\))?!?: \S/;

/** Why a commit subject breaks the convention, or null when it keeps it. */
export function subjectProblem(subject: string): string | null {
  return CONVENTIONAL_SUBJECT.test(subject) ? null : `the message does not follow the Conventional Commits convention: "${subject.slice(0, 72)}"`;
}

/** commit-msg: convention + Receipt-Id trailer. No Override-Reason: the floor has no
 *  guard an override can excuse, so any stamped reason would be false history (T19). */
export function commitMsg(msgFile: string, receiptId: string | (() => string)): FloorResult {
  const lines: string[] = [];
  let content: string;
  try {
    content = readFileSync(msgFile, "utf8");
  } catch {
    return { ok: false, lines: ["commit-msg: cannot read the commit message."] };
  }
  const first = content.split("\n")[0] ?? "";
  const problem = subjectProblem(first);
  if (problem !== null) return { ok: false, lines: [problem, "Format: type(scope): description"] };
  // The Receipt-Id trailer is idempotent: an amend (or the hook firing twice) finds it
  // already there and leaves the message untouched.
  let next = content;
  if (!next.includes("Receipt-Id:")) {
    const id = typeof receiptId === "function" ? receiptId() : receiptId;
    next = `${next.trimEnd()}\n\nReceipt-Id: ${id}\n`;
  }
  if (next !== content) writeFileSync(msgFile, next);
  return { ok: true, lines };
}

/** One line git hands pre-push on stdin: what is pushed, and where the remote ref stood. */
type PushTuple = { localSha: string; remoteRef: string; remoteSha: string };

const OBJECT_ID = /^(?:[0-9a-f]{40}|[0-9a-f]{64})$/;
const isZero = (sha: string): boolean => /^0+$/.test(sha);

/** `<local ref> <local sha> <remote ref> <remote sha>` per pushed ref, or the first line
 *  that is not one: a hook that cannot read what is pushed cannot say it is clean. */
function pushTuples(raw: string): PushTuple[] | { malformed: string } {
  const tuples: PushTuple[] = [];
  for (const line of raw.split("\n").map((entry) => entry.trim()).filter((entry) => entry.length > 0)) {
    const [localRef, localSha, remoteRef, remoteSha, ...rest] = line.split(/\s+/);
    if (localRef === undefined || remoteRef === undefined || rest.length > 0 || !OBJECT_ID.test(localSha ?? "") || !OBJECT_ID.test(remoteSha ?? "")) {
      return { malformed: line };
    }
    tuples.push({ localSha: localSha!, remoteRef, remoteSha: remoteSha! });
  }
  return tuples;
}

/** The commits this push sends, as `git log` revisions: every new tip, minus what the
 *  remote already has — the old tip of a ref it moves, or the remote's base for a ref it
 *  creates. One revision list for every ref, so a commit two refs share is scanned once.
 *  A deletion sends nothing. Whatever cannot be measured refuses, never widens or skips. */
function outgoingRevisions(cwd: string, tuples: PushTuple[]): { tips: string[]; known: string[] } | { refused: string } {
  const tips = new Set<string>();
  const known = new Set<string>();
  for (const tuple of tuples) {
    if (isZero(tuple.localSha)) continue;
    tips.add(tuple.localSha);
    if (!isZero(tuple.remoteSha)) {
      if (runGit(["cat-file", "-e", `${tuple.remoteSha}^{commit}`], { cwd }).status !== 0) {
        return { refused: `pre-push: ${tuple.remoteRef} on the remote is at ${tuple.remoteSha.slice(0, 12)}, which this clone does not have, so the outgoing commits cannot be told apart — git fetch, then push again.` };
      }
      known.add(tuple.remoteSha);
      continue;
    }
    const base = namedBaseTrackingRef(cwd);
    if (base === null || base.commit === null) {
      const where = base === null ? "the remote's base branch" : base.ref;
      return { refused: `pre-push: ${tuple.remoteRef} is new on the remote and ${where} is not in this clone, so the outgoing commits cannot be told apart — git fetch, or set [git] base in .ai-engineering/config.toml, then push again.` };
    }
    known.add(base.commit);
  }
  return { tips: [...tips], known: [...known] };
}

/** `[sha, subject]` for every commit a revision list selects. A read that fails is not "no
 *  commits": the caller refuses rather than judging less than it was asked to. */
function outgoingSubjects(cwd: string, revisions: string[]): Array<[string, string]> | { refused: string } {
  const done = runGit(["log", "--format=%H%x1f%s", ...revisions], { cwd, isolated: true });
  if (done.status !== 0) return { refused: `pre-push: cannot read the commits this push sends: ${done.stderr.trim().slice(0, 200)}` };
  return done.stdout
    .split("\n")
    .filter((line) => line !== "")
    .map((line) => {
      const [sha, subject] = line.split("\x1f");
      return [sha ?? "", subject ?? ""];
    });
}

/** pre-push: block direct pushes to the detected base + hold the outgoing subjects to the
 *  Conventional Commits rule + gitleaks over exactly the commits this push sends. The branch
 *  protection rule (PR required) lives on the forge, but admins can bypass it — this local
 *  guard catches that. The whole history is CI's scan, not this hook's: unpublished refs (a
 *  stash, an archive ref) are not what a push sends. */
export function prePush(cwd = repoRoot() ?? process.cwd()): FloorResult {
  const lines: string[] = [];
  let baseRef: string;
  try {
    // namedBase, not resolveContext: a base that is the current branch must still be guarded.
    const base = namedBase(cwd);
    // A guard that cannot name the base cannot rule out a push to it, so it denies (R8).
    if (base === null) {
      return { ok: false, lines: ['pre-push: no base branch could be resolved — set [git] base = "<branch>" in .ai-engineering/config.toml, then push again.'] };
    }
    baseRef = `refs/heads/${base}`;
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    return { ok: false, lines: [`pre-push: cannot resolve detected base: ${detail}`] };
  }
  // The pre-push hook shim captures stdin into AI_ENG_PUSH_REFS before calling us,
  // so we read it from the environment instead of fd 0 (which may already be consumed).
  const raw = process.env.AI_ENG_PUSH_REFS ?? "";
  // The base rule reads the remote ref of every line, parseable or not: it runs first.
  for (const line of raw.split("\n")) {
    const remoteRef = line.trim().split(/\s+/)[2];
    if (remoteRef === baseRef) {
      return { ok: false, lines: [`direct push to detected base ${baseRef} is not allowed — open a PR instead.`] };
    }
  }
  const gitleaks = whichGitleaks();
  if (!gitleaks) {
    return { ok: false, lines: [`gitleaks is not installed — HARD FAIL (§12.1). ${gitleaksInstallHint()}`] };
  }
  const tuples = pushTuples(raw);
  if ("malformed" in tuples) {
    return { ok: false, lines: [`pre-push: cannot read the pushed ref "${tuples.malformed.slice(0, 200)}" — expected "<local ref> <local sha> <remote ref> <remote sha>".`] };
  }
  const outgoing = outgoingRevisions(cwd, tuples);
  if ("refused" in outgoing) return { ok: false, lines: [outgoing.refused] };
  // Only deletions, or nothing at all: no commit leaves this clone.
  if (outgoing.tips.length === 0) return { ok: true, lines };
  // The commit-msg hook only sees the routes that run hooks. The pipeline writes its fix
  // commits itself and rewrites their subjects afterwards, so a bad subject can enter with
  // no hook in sight (PR #823: three did). Every route still leaves through one door, so
  // the same rule is asked again over exactly the commits this push sends (R6).
  // One revision list for both questions: what is judged is what is scanned.
  const revisions = [...outgoing.tips, "--not", ...outgoing.known];
  const subjects = outgoingSubjects(cwd, revisions);
  if ("refused" in subjects) return { ok: false, lines: [subjects.refused] };
  const offender = subjects.find(([, subject]) => subjectProblem(subject) !== null);
  if (offender !== undefined) {
    const [sha, subject] = offender;
    return {
      ok: false,
      lines: [`pre-push: ${sha.slice(0, 12)} does not follow the Conventional Commits convention: "${subject.slice(0, 72)}"`, "Format: type(scope): description — rewrite that commit's subject before pushing."],
    };
  }
  // Object ids only, handed to gitleaks as one argv element: no ref name reaches a shell.
  const range = revisions.join(" ");
  // The project's allowlist when it has one. ai-eng never installs that file, and a -c (or
  // the shim's GITLEAKS_CONFIG) naming a missing one makes gitleaks exit 1 before scanning
  // — which this hook would report as a secret: gitleaks' own rules apply instead.
  const config = join(cwd, ".gitleaksrc.toml");
  const hasConfig = existsSync(config);
  const { GITLEAKS_CONFIG: _unset, ...withoutConfig } = process.env;
  try {
    execFileSync(gitleaks, ["git", "--redact", "-v", `--log-opts=${range}`, ...(hasConfig ? ["-c", config] : [])], { cwd, stdio: "pipe", env: hasConfig ? process.env : withoutConfig });
  } catch (error) {
    const out = (error as { stdout?: string }).stdout ?? "";
    return { ok: false, lines: ["gitleaks in pre-push: secret in the unpushed history → BLOCKED.", out.toString().slice(0, 2000)] };
  }
  return { ok: true, lines };
}
