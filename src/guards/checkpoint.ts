// src/guards/checkpoint.ts — checkpoint ordering runs in the chain, beside every other guard.

import { createHash } from "node:crypto";
import {
  lstatSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  readlinkSync,
  realpathSync,
  statSync,
  unlinkSync,
  writeFileSync,
  type Stats,
} from "node:fs";
import { homedir } from "node:os";
import { basename, dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { isDeepStrictEqual } from "node:util";
import { resolveContext } from "../git/context.ts";
import {
  assertCheckpointTransition,
  brainstormApprovalProblem,
  checkpointComplete,
  parseCheckpoint,
  readCheckpoint,
  readCheckpointText,
  type Checkpoint,
  type CheckpointContext,
  type CheckpointItem,
} from "../workflow/checkpoint.ts";
import type { Payload } from "../payload.ts";
import { embeddedPatchPaths } from "../payload.ts";

type CheckpointGuardResult = { deny: true; reason: string } | { deny: false } | undefined;

const GATES = ["behavior", "ui", "review"] as const;
const STAGES = new Set(["tests", "implement", "behavior", "ui", "review", "fix"]);
const MARKER = /^\s*\[checkpoint\s+([\w.-]+)#(\d+)\s+(\w+)\]/;
const CHECKPOINT_PATH = /^\.ai-engineering\/workflow\/checkpoints\/([a-z0-9][a-z0-9._-]*)\.json$/;
const CHECKPOINT_TARGET = /\.ai-engineering\/workflow\/checkpoints\/[^\s/]+\.json/;
const BASH_WRITE = />|\btee\b|\bsed\s+-i|\bpython3?\b|\bnode\b|\bperl\b|\bjq\b.*>|\bmv\b|\bcp\b|\brm\b|\btruncate\b/;
const CHECKPOINTS_DIR = ".ai-engineering/workflow/checkpoints";
const MAX_LINK_HOPS = 40;
// Command separators: `&&`, `||`, `;`, newlines, pipes and a background `&` — but not the
// `|` of `>|` nor the `&` of `2>&1` / `&>`.
const SHELL_SEGMENT = /&&|\|\||;|\n|(?<!>)\|&?|(?<![<>])&(?!>)/;
// A redirection target: `>f`, `> f`, `>>f`, `2>f`, `&>f`, `>|f`; never an fd copy like `>&1`.
const REDIRECTION = /(?:^|[^<>&\d])(?:\d*|&)>{1,2}\|?\s*([^\s;&|<>()]+)/g;
// Redirections that write no file: into /dev/null, or onto another descriptor (`2>&1`, `>&2`).
const DISCARD_REDIRECTION = /(?:\d*|&)>{1,2}\|?\s*(['"]?)\/dev\/null\1(?![^\s;&|<>()])|\d*>&\d+(?![^\s;&|<>()])/g;
const COMMAND_PREFIXES = new Set(["sudo", "command", "builtin", "exec", "env", "time", "nohup", "nice"]);
// Writers whose target cannot be read off the command line.
const OPAQUE_WRITERS = new Set(["python", "python3", "node", "perl", "ruby", "bun", "deno", "jq", "awk"]);
const MAX_STOP_BLOCKS = 3;

function deny(checkpoint: string, gate: string, detail: string, next: string): CheckpointGuardResult {
  return {
    deny: true,
    reason: `${checkpoint} cannot pass: ${gate} ${detail}. Next: ${next}.`,
  };
}

function checkpointContext(repoRoot: string, slug: string): CheckpointContext {
  const context = resolveContext(repoRoot);
  return {
    repoPath: context.root,
    slug,
    baseRef: context.base === null ? "" : `refs/heads/${context.base}`,
  };
}

function realRootOf(root: string): string {
  try {
    return realpathSync(root);
  } catch {
    return root;
  }
}

function checkpointTarget(repoRoot: string, filePath: unknown): { path: string; slug: string } | null {
  if (typeof filePath !== "string" || filePath.length === 0) return null;
  const root = resolve(repoRoot);
  const absolutePath = isAbsolute(filePath) ? resolve(filePath) : resolve(root, filePath);
  // The repository's own path, as named or as resolved (a root reached through /var vs /private/var).
  for (const base of new Set([root, realRootOf(root)])) {
    const match = CHECKPOINT_PATH.exec(relative(base, absolutePath).split(sep).join("/"));
    if (match?.[1]) return { path: absolutePath, slug: match[1] };
  }
  return null;
}

/** `path` with every part that exists resolved: the realpath of its deepest existing
 *  ancestor plus the rest as named, following a dangling link at any level. */
function realTarget(path: string, hops = 0): string {
  const rest: string[] = [];
  let current = path;
  for (;;) {
    try {
      return join(realpathSync(current), ...rest);
    } catch {
      /* missing, or a link to something missing: resolved below */
    }
    try {
      if (hops < MAX_LINK_HOPS && lstatSync(current).isSymbolicLink()) {
        return realTarget(join(resolve(dirname(current), readlinkSync(current)), ...rest), hops + 1);
      }
    } catch {
      /* nothing at this name: look one level up */
    }
    const parent = dirname(current);
    if (parent === current) return path;
    rest.unshift(basename(current));
    current = parent;
  }
}

/** True when the filesystem holding `path` ignores case (macOS and Windows defaults):
 *  the same folder answers under the case-swapped name. */
function isCaseInsensitive(path: string): boolean {
  const swapped = path.replace(/[a-z]/gi, (letter) => (letter === letter.toLowerCase() ? letter.toUpperCase() : letter.toLowerCase()));
  if (swapped === path) return false;
  try {
    const named = statSync(path);
    const other = statSync(swapped);
    return named.dev === other.dev && named.ino === other.ino;
  } catch {
    return false;
  }
}

/** Where a path really lands relative to the real repository root, in `/` form,
 *  lower-cased where the filesystem ignores case. */
type RealRepo = { root: string; isCaseInsensitive: boolean };

function realRepo(repoRoot: string): RealRepo {
  const root = realpathSync(repoRoot);
  return { root, isCaseInsensitive: isCaseInsensitive(root) };
}

function landsAt(repo: RealRepo, absolutePath: string): string {
  const landed = relative(repo.root, realTarget(absolutePath)).split(sep).join("/");
  return repo.isCaseInsensitive ? landed.toLowerCase() : landed;
}

function landsInCheckpoints(repo: RealRepo, absolutePath: string): boolean {
  const landed = landsAt(repo, absolutePath);
  return landed === CHECKPOINTS_DIR || landed.startsWith(`${CHECKPOINTS_DIR}/`);
}

/** The checkpoint file that is the same file as `path` (a hard link, a symlink, a
 *  case-variant name), by device and inode. */
function checkpointWithSameInode(folder: string, path: string): string | null {
  let target: Stats;
  try {
    target = statSync(path);
  } catch {
    return null;
  }
  if (!target.isFile()) return null;
  let names: string[];
  try {
    names = readdirSync(folder);
  } catch {
    return null;
  }
  for (const name of names) {
    if (!name.endsWith(".json")) continue;
    try {
      const candidate = statSync(join(folder, name));
      if (candidate.dev === target.dev && candidate.ino === target.ino) return name.slice(0, -".json".length);
    } catch {
      /* gone since the listing */
    }
  }
  return null;
}

/** The slug of the checkpoint file an Edit/Write lands on when its path text does not name
 *  that file: the guard reads paths, so another name for the same file would skip it. */
function aliasedCheckpoint(repoRoot: string, filePath: unknown): string | null {
  if (typeof filePath !== "string" || filePath.length === 0) return null;
  const repo = realRepo(repoRoot);
  const absolutePath = isAbsolute(filePath) ? resolve(filePath) : resolve(repoRoot, filePath);
  const sameFile = checkpointWithSameInode(join(repo.root, CHECKPOINTS_DIR), absolutePath);
  if (sameFile !== null) return sameFile;
  return CHECKPOINT_PATH.exec(landsAt(repo, absolutePath))?.[1] ?? null;
}

function applyEdit(contents: string, edit: Record<string, unknown>): string | null {
  const oldString = edit.old_string ?? edit.oldString;
  const newString = edit.new_string ?? edit.newString;
  if (typeof oldString !== "string" || oldString.length === 0 || typeof newString !== "string") return null;
  if (!contents.includes(oldString)) return null;
  if (edit.replace_all === true || edit.replaceAll === true) return contents.split(oldString).join(newString);
  return contents.replace(oldString, newString);
}

function proposedContents(payload: Payload, target: { path: string; slug: string }, context: CheckpointContext): string | null {
  const toolInput = payload.tool_input;
  if (payload.tool_name === "Write") {
    return typeof toolInput.content === "string" ? toolInput.content : null;
  }
  const contents = readCheckpointText(target.path, context);
  if (contents === null) return null;
  if (payload.tool_name === "Edit") return applyEdit(contents, toolInput);
  if (payload.tool_name !== "MultiEdit" || !Array.isArray(toolInput.edits)) return null;

  let updated = contents;
  for (const edit of toolInput.edits) {
    if (edit === null || typeof edit !== "object" || Array.isArray(edit)) return null;
    const result = applyEdit(updated, edit as Record<string, unknown>);
    if (result === null) return null;
    updated = result;
  }
  return updated;
}

function runtimeState(checkpoint: CheckpointItem): unknown {
  return [
    checkpoint.status,
    ...GATES.map((gate) => checkpoint.gates[gate].status),
  ];
}

function started(checkpoint: CheckpointItem): boolean {
  return GATES.some((gate) => {
    const state = checkpoint.gates[gate];
    return state.status === "passed" || state.status === "failed" || state.attempts > 0;
  });
}

function requireSequentialCheckpoints(checkpoint: Checkpoint, source: string): CheckpointGuardResult | undefined {
  for (const [index, item] of checkpoint.checkpoints.entries()) {
    if (item.id !== index + 1) {
      return deny(`CP${item.id}`, "checkpoint schema", `IDs in ${source} must be sequential starting at 1`, "renumber the checkpoints and retry the guarded write");
    }
  }
  return undefined;
}

function reviewedPayload(plan: Checkpoint): unknown {
  const copy = JSON.parse(JSON.stringify(plan)) as Record<string, unknown>;
  delete copy["lifecycle"];
  const checkpoints = copy["checkpoints"];
  if (!Array.isArray(checkpoints)) return copy;
  for (const checkpointValue of checkpoints) {
    if (checkpointValue === null || typeof checkpointValue !== "object") continue;
    const checkpoint = checkpointValue as Record<string, unknown>;
    delete checkpoint["status"];
    const gates = checkpoint["gates"];
    if (gates === null || typeof gates !== "object") continue;
    for (const gateValue of Object.values(gates)) {
      if (gateValue === null || typeof gateValue !== "object") continue;
      const gate = gateValue as Record<string, unknown>;
      delete gate["status"];
      delete gate["attempts"];
      delete gate["findings"];
    }
  }
  return copy;
}

function hasAppReviewClaim(checkpoint: Checkpoint): boolean {
  const lifecycle = checkpoint.lifecycle;
  return lifecycle.phase === "awaiting-app-review" ||
    lifecycle.phase === "ready-to-merge" ||
    (lifecycle.phase === "blocked" && lifecycle.app_review !== "not-started");
}

function assertProgress(previous: Checkpoint | null, next: Checkpoint): CheckpointGuardResult | undefined {
  for (const checkpoint of next.checkpoints) {
    const behavior = checkpoint.gates.behavior.status;
    const ui = checkpoint.gates.ui.status;
    const review = checkpoint.gates.review.status;
    if (ui === "passed" && behavior !== "passed") {
      return deny(`CP${checkpoint.id}`, "ui gate", "cannot pass before behavior has passed", `run the CP${checkpoint.id} behavior gate`);
    }
    if (review === "passed" && (behavior !== "passed" || (ui !== "passed" && ui !== "n/a"))) {
      return deny(`CP${checkpoint.id}`, "review gate", "cannot pass before behavior and ui have passed or ui is n/a", `run the CP${checkpoint.id} behavior and ui gates`);
    }

    const oldCheckpoint = previous?.checkpoints.find((candidate) => candidate.id === checkpoint.id);
    const hasChanged = oldCheckpoint !== undefined &&
      !isDeepStrictEqual(runtimeState(oldCheckpoint), runtimeState(checkpoint));
    if ((hasChanged || (oldCheckpoint === undefined && started(checkpoint))) &&
      next.checkpoints.some((candidate) => candidate.id < checkpoint.id && !checkpointComplete(candidate))) {
      return deny(`CP${checkpoint.id}`, "checkpoint order", "cannot change while an earlier checkpoint is still open", "finish every earlier checkpoint first");
    }
  }
  return undefined;
}

function checkFirstPlan(root: string, checkpoint: Checkpoint): CheckpointGuardResult | undefined {
  const state = checkpoint.lifecycle;
  if (
    state.phase !== "implementation" ||
    state.plan_approval !== "approved" ||
    state.app_review !== "not-started" ||
    state.reviewed_base !== null ||
    state.reviewed_feature !== null
  ) {
    return deny(`Checkpoint ${checkpoint.slug}`, "plan approval", "a first plan must start approved for implementation with no app review", "approve the matching brainstorm, then write the implementation plan");
  }
  let html: string;
  try {
    html = readFileSync(join(root, ".ai-engineering", "brainstorm.html"), "utf8");
  } catch (error) {
    return deny(`Checkpoint ${checkpoint.slug}`, "plan approval", `cannot read the matching brainstorm (${error instanceof Error ? error.message : String(error)})`, "restore the approved brainstorm and retry the plan write");
  }
  const problem = brainstormApprovalProblem(html, checkpoint.slug, new Date());
  if (problem !== null) {
    return deny(`Checkpoint ${checkpoint.slug}`, "plan approval", problem, "approve the matching brainstorm within the last 14 days");
  }
  return undefined;
}

function checkPlanWrite(payload: Payload, repoRoot: string): CheckpointGuardResult {
  const target = checkpointTarget(repoRoot, payload.tool_input.file_path);
  if (target === null) {
    const alias = aliasedCheckpoint(repoRoot, payload.tool_input.file_path);
    if (alias === null) return undefined;
    return deny(`Checkpoint ${alias}`, "write gate", `does not allow writing ${CHECKPOINTS_DIR}/${alias}.json through another path (${String(payload.tool_input.file_path)})`, `edit ${CHECKPOINTS_DIR}/${alias}.json by that path so checkpoint gates are validated`);
  }
  let context: CheckpointContext;
  try {
    context = checkpointContext(repoRoot, target.slug);
  } catch (error) {
    return deny(`Checkpoint ${target.slug}`, "checkpoint gate", `cannot detect the repository base (${error instanceof Error ? error.message : String(error)})`, "repair the repository Git context and retry the guarded write");
  }

  let previous: Checkpoint | null = null;
  let previousText: string | null;
  try {
    previousText = readCheckpointText(target.path, context, true);
    if (previousText !== null) previous = parseCheckpoint(previousText, context);
  } catch (error) {
    return deny(`Checkpoint ${target.slug}`, "checkpoint gate", `cannot read ${target.path} (${error instanceof Error ? error.message : String(error)})`, "repair the checkpoint file and retry the guarded write");
  }

  const text = proposedContents(payload, target, context);
  if (text === null) return undefined;
  let next: Checkpoint;
  try {
    next = parseCheckpoint(text, context, { forWrite: true });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    const item = /checkpoints\[(\d+)\]/.exec(message);
    const checkpoint = item?.[1] === undefined ? `Checkpoint ${target.slug}` : `CP${Number(item[1]) + 1}`;
    return deny(checkpoint, "checkpoint schema", message, "repair the checkpoint JSON schema and retry the guarded write");
  }
  const sequenceError = requireSequentialCheckpoints(next, target.path);
  if (sequenceError !== undefined) return sequenceError;
  if (previous !== null) {
    const oldSequenceError = requireSequentialCheckpoints(previous, target.path);
    if (oldSequenceError !== undefined) return oldSequenceError;
  }

  const progressError = assertProgress(previous, next);
  if (progressError !== undefined) return progressError;

  if (previous === null) {
    return checkFirstPlan(context.repoPath, next) ?? { deny: false };
  }

  if (
    (hasAppReviewClaim(next) || (hasAppReviewClaim(previous) && next.lifecycle.phase !== "implementation")) &&
    !isDeepStrictEqual(reviewedPayload(previous), reviewedPayload(next))
  ) {
    return deny(`Checkpoint ${target.slug}`, "app-review gate", "cannot change reviewed plan fields after app review begins", "request changes or repeat the app review for the updated plan");
  }

  if (!isDeepStrictEqual(previous.lifecycle, next.lifecycle)) {
    try {
      assertCheckpointTransition({ ...previous }, next, context);
    } catch (error) {
      return deny(`Checkpoint ${target.slug}`, "lifecycle gate", error instanceof Error ? error.message : String(error), "make only an allowed lifecycle transition and retry the guarded write");
    }
  }
  return { deny: false };
}

function checkMarker(payload: Payload, repoRoot: string): CheckpointGuardResult {
  const prompt = payload.tool_input.prompt;
  if (typeof prompt !== "string") return undefined;
  const match = MARKER.exec(prompt);
  if (!match) return undefined;
  const slug = match[1] ?? "";
  const checkpointId = Number(match[2]);
  const stage = match[3] ?? "";
  const label = `CP${checkpointId}`;
  if (!STAGES.has(stage)) {
    return deny(label, "checkpoint stage", `does not recognize "${stage}"`, "use tests, implement, behavior, ui, review, or fix");
  }

  let checkpoint: Checkpoint;
  const path = join(repoRoot, ".ai-engineering", "workflow", "checkpoints", `${slug}.json`);
  try {
    checkpoint = readCheckpoint(path, checkpointContext(repoRoot, slug));
  } catch (error) {
    return deny(label, "checkpoint gate", `cannot read ${path} (${error instanceof Error ? error.message : String(error)})`, "repair the checkpoint file and retry the marked task");
  }
  const sequenceError = requireSequentialCheckpoints(checkpoint, path);
  if (sequenceError !== undefined) return sequenceError;
  if (checkpoint.lifecycle.phase !== "implementation" || checkpoint.lifecycle.plan_approval !== "approved") {
    return deny(label, "plan approval gate", "implementation is not authorized by the lifecycle approval", "approve the plan before starting checkpoint work");
  }

  const current = checkpoint.checkpoints.find((item) => item.id === checkpointId);
  if (current === undefined) {
    return deny(label, "checkpoint order", `does not exist in ${slug}.json`, "use an existing checkpoint number");
  }
  if (checkpoint.checkpoints.some((item) => item.id < checkpointId && !checkpointComplete(item))) {
    return deny(label, "checkpoint order", "cannot start while an earlier checkpoint is still open", "finish every earlier checkpoint first");
  }
  if (current.status === "passed") {
    return deny(label, "checkpoint status", "has already passed", `reopen CP${checkpointId} with a failing gate before working on it again`);
  }
  if (stage === "ui" && current.gates.behavior.status !== "passed") {
    return deny(label, "ui gate", `needs behavior passed first (behavior is "${current.gates.behavior.status}")`, `run the CP${checkpointId} behavior gate`);
  }
  if (stage === "review" && (current.gates.behavior.status !== "passed" ||
    (current.gates.ui.status !== "passed" && current.gates.ui.status !== "n/a"))) {
    return deny(label, "review gate", `needs behavior passed and ui passed or n/a (behavior="${current.gates.behavior.status}", ui="${current.gates.ui.status}")`, `run the CP${checkpointId} behavior and ui gates`);
  }
  return { deny: false };
}

function unquote(word: string): string {
  return word.replace(/^(['"])(.*)\1$/s, "$2");
}

/** The words of one shell segment, quotes removed, with leading `VAR=value` and
 *  wrapper commands (sudo, env, …) dropped so the first word is the real command. */
function commandWords(segment: string): string[] {
  const words = (segment.replace(/^[\s({]+|[\s)}]+$/g, "").match(/"[^"]*"|'[^']*'|\S+/g) ?? []).map(unquote);
  while (words.length > 0 && (/^\w+=/.test(words[0]!) || COMMAND_PREFIXES.has(words[0]!))) words.shift();
  return words;
}

/** The paths one segment writes, unresolved: redirection targets, and the operands of
 *  tee, sed -i, cp (destination), mv, rm and truncate. */
function writeTargets(segment: string, words: readonly string[]): string[] {
  const targets = [...segment.matchAll(REDIRECTION)].map((match) => unquote(match[1] ?? ""));
  const [name, ...rest] = words;
  const operands = rest.filter((word) => !word.startsWith("-"));
  const isInPlaceSed = name === "sed" && rest.some((word) => /^-[a-zA-Z]*i/.test(word) || word.startsWith("--in-place"));
  if (name === "cp") targets.push(...operands.slice(-1));
  if (name === "tee" || name === "mv" || name === "rm" || name === "truncate" || isInPlaceSed) targets.push(...operands);
  return targets.filter((target) => target.length > 0);
}

/** The operands of `python3 -m json.tool …`, or null for any other command. A bare `-`
 *  is an operand (stdin), everything after `--` is an operand, and `--indent` takes the
 *  next word as its value. */
function jsonToolOperands(words: readonly string[]): string[] | null {
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

/** json.tool only reads when its one operand is the checkpoint file. A second operand is
 *  the file it writes, and `-` makes it read stdin, so the operand after `-` is written. */
function isJsonToolRead(words: readonly string[], isCheckpointFile: (operand: string) => boolean): boolean {
  const operands = jsonToolOperands(words);
  if (operands?.length !== 1) return false;
  const operand = operands[0]!;
  return operand !== "-" && isCheckpointFile(operand);
}

/** Whether one segment of a command that names a checkpoint has a write form. Output thrown
 *  away (`> /dev/null`, `2>&1`, `>&2`) writes no file, and json.tool on the checkpoint only reads it. */
function hasWriteForm(segment: string): boolean {
  const kept = segment.replace(DISCARD_REDIRECTION, " ");
  if (isJsonToolRead(commandWords(kept), (operand) => CHECKPOINT_TARGET.test(operand))) return kept.includes(">");
  return BASH_WRITE.test(kept);
}

/** A path as the shell would resolve it from `cwd`, or null when it hangs off a variable,
 *  a substitution or `~user` that the guard cannot know. */
function shellPath(cwd: string, word: string): string | null {
  if (/[$`]/.test(word) || /^~[^/]/.test(word)) return null;
  if (word === "~" || word.startsWith("~/")) return join(homedir(), word.slice(1));
  return resolve(cwd, word);
}

/** True when a command writes into the checkpoints folder by a path the text check cannot
 *  see: after a cd/pushd into (or towards) it, through a link, or under another case.
 *  Reads (cat, git diff, git add) are never write forms. A directory the guard cannot
 *  follow (cd $DIR, cd -) decides nothing — then any write that mentions the checkpoints
 *  folder by name is refused. */
function shellWritesIntoCheckpoints(command: string, cwd: string, repo: RealRepo): boolean {
  let directory: string | null = cwd;
  const stack: Array<string | null> = [];
  const mentionsCheckpoints = /checkpoints/i.test(command);
  for (const segment of command.split(SHELL_SEGMENT)) {
    const words = commandWords(segment);
    const [name, ...rest] = words;
    if (name === "cd" || name === "pushd") {
      const operand = rest.find((word) => !word.startsWith("-") || word === "-");
      if (name === "pushd") stack.push(directory);
      const next: string | null = operand === undefined ? homedir() : operand === "-" || directory === null ? null : shellPath(directory, operand);
      directory = next;
      continue;
    }
    if (name === "popd") {
      directory = stack.pop() ?? null;
      continue;
    }
    if (directory !== null && name !== undefined && OPAQUE_WRITERS.has(basename(name)) && landsInCheckpoints(repo, directory)) {
      const here = directory;
      const isCheckpointFile = (operand: string): boolean => {
        const absolute = shellPath(here, operand);
        return absolute !== null && landsInCheckpoints(repo, absolute);
      };
      if (!isJsonToolRead(commandWords(segment.replace(DISCARD_REDIRECTION, " ")), isCheckpointFile)) return true;
    }
    for (const target of writeTargets(segment, words)) {
      const absolute = isAbsolute(target) || target.startsWith("~") ? shellPath("/", target) : directory === null ? null : shellPath(directory, target);
      if (absolute === null ? mentionsCheckpoints : landsInCheckpoints(repo, absolute)) return true;
    }
  }
  return false;
}

function checkBash(payload: Payload, repoRoot: string): CheckpointGuardResult {
  const command = payload.tool_input.command;
  if (typeof command !== "string") return undefined;
  const hostCwd = payload["cwd"];
  const cwd = typeof hostCwd === "string" && hostCwd.length > 0 ? resolve(repoRoot, hostCwd) : resolve(repoRoot);
  // A shell apply_patch is a write by another name: its headers are the files it touches.
  if (command.includes("*** Begin Patch")) {
    let patched: string[];
    try {
      patched = embeddedPatchPaths(command);
    } catch {
      patched = [];
    }
    const gated = patched.map((path) => resolve(cwd, path)).find((path) => checkpointTarget(repoRoot, path) !== null || aliasedCheckpoint(repoRoot, path) !== null);
    if (gated !== undefined) {
      return deny("Checkpoint", "shell gate", `does not accept a patch to ${gated}`, "use Edit or Write so checkpoint gates are validated");
    }
  }
  const isNamedWrite = CHECKPOINT_TARGET.test(command) && command.split(SHELL_SEGMENT).some(hasWriteForm);
  if (!isNamedWrite && !shellWritesIntoCheckpoints(command, cwd, realRepo(repoRoot))) return undefined;
  return deny("Checkpoint", "shell gate", "does not allow direct Bash writes to checkpoint JSON", "use Edit or Write so checkpoint gates are validated");
}

function orchestratorTranscript(payload: Payload, slug: string): boolean {
  const transcriptPath = payload.transcript_path;
  if (typeof transcriptPath !== "string" || transcriptPath.length === 0) return false;
  try {
    const transcript = readFileSync(transcriptPath, "utf8");
    const startedOrchestrator = /"skill"\s*:\s*"ai-orchestrator"|<command-name>\/ai-orchestrator<\/command-name>/.test(transcript);
    return startedOrchestrator && transcript.includes(`.ai-engineering/workflow/checkpoints/${slug}.json`);
  } catch {
    return false;
  }
}

function stopCounterPath(root: string, sessionId: unknown): string {
  const session = typeof sessionId === "string" && sessionId.trim() ? sessionId.trim() : "unknown";
  const hash = createHash("sha256").update(session).digest("hex");
  return join(root, ".ai-engineering", "cache", "checkpoint-stop", `${hash}.txt`);
}

function ensureCounterDirectory(directory: string, root: string): void {
  let current = root;
  for (const part of relative(root, directory).split(sep)) {
    current = join(current, part);
    try {
      const stat = lstatSync(current);
      if (stat.isSymbolicLink() || !stat.isDirectory()) throw new Error(`${current} is not a real directory`);
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
      mkdirSync(current);
    }
  }
}

function resetStopCounter(path: string): void {
  try {
    unlinkSync(path);
  } catch {
    // No prior stop refusal needs clearing.
  }
}

function bumpStopCounter(path: string, root: string): number {
  ensureCounterDirectory(dirname(path), root);
  let count = 0;
  try {
    const stat = lstatSync(path);
    if (stat.isSymbolicLink() || !stat.isFile()) throw new Error(`${path} is not a regular file`);
    const previous = Number(readFileSync(path, "utf8"));
    if (Number.isSafeInteger(previous) && previous > 0) count = previous;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
  }
  const next = count + 1;
  writeFileSync(path, String(next), { mode: 0o600 });
  return next;
}

/** Exit 2 on Stop makes Claude continue, and it then sends the next Stop with
 *  `stop_hook_active`. A fault the agent cannot cure by continuing (the checkpoint file is
 *  itself guarded) must not hold the turn forever:
 *  - a fault that leaves nothing to judge (no repo, an unreadable folder, a counter that
 *    cannot be saved) is refused once, then the stop goes through;
 *  - a fault in one checkpoint file becomes one more problem beside the other files' open
 *    gates, so it is still reported and bounded by MAX_STOP_BLOCKS like they are. */
function isContinuingAfterStop(payload: Payload): boolean {
  return payload["stop_hook_active"] === true;
}

function faultRefusal(payload: Payload, refusal: CheckpointGuardResult): CheckpointGuardResult {
  return isContinuingAfterStop(payload) ? { deny: false } : refusal;
}

function checkStop(payload: Payload, repoRoot: string): CheckpointGuardResult {
  if (payload.stop_reason === "user_interrupt" || payload.stop_reason === "ask_user_question") {
    return { deny: false };
  }

  let root: string;
  try {
    root = resolveContext(repoRoot).root;
  } catch (error) {
    return faultRefusal(payload, deny("Checkpoint", "Stop gate", `cannot resolve the repository (${error instanceof Error ? error.message : String(error)})`, "return to the repository and retry the Stop event"));
  }

  const folder = join(root, ".ai-engineering", "workflow", "checkpoints");
  let files: string[];
  try {
    files = readdirSync(folder).filter((file) => file.endsWith(".json")).sort();
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return { deny: false };
    return faultRefusal(payload, deny("Checkpoint", "Stop gate", `cannot list ${folder} (${error instanceof Error ? error.message : String(error)})`, "restore access to the checkpoint directory before stopping"));
  }

  const problems: string[] = [];
  for (const file of files) {
    const slug = file.slice(0, -".json".length);
    if (!orchestratorTranscript(payload, slug)) continue;
    const path = join(folder, file);
    let checkpoint: Checkpoint;
    try {
      checkpoint = readCheckpoint(path, checkpointContext(root, slug));
    } catch (error) {
      const detail = `cannot validate ${path} (${error instanceof Error ? error.message : String(error)})`;
      if (!isContinuingAfterStop(payload)) return deny(`Checkpoint ${slug}`, "Stop gate", detail, "repair the checkpoint JSON before ending the turn");
      problems.push(`${slug}: ${detail}`);
      continue;
    }
    const sequenceError = requireSequentialCheckpoints(checkpoint, path);
    if (sequenceError !== undefined) {
      if (!isContinuingAfterStop(payload)) return sequenceError;
      problems.push(`${slug}: checkpoint IDs in ${path} are not sequential`);
      continue;
    }
    const halted = checkpoint.halted;
    if (
      typeof halted === "object" &&
      halted !== null &&
      "reason" in halted &&
      typeof halted.reason === "string" &&
      halted.reason.length > 0
    ) continue;

    for (const item of checkpoint.checkpoints) {
      if (item.status === "passed" || !started(item)) continue;
      const openGates = GATES
        .filter((gate) => item.gates[gate].status !== "passed" && item.gates[gate].status !== "n/a")
        .map((gate) => `${gate}=${item.gates[gate].status}`)
        .join(", ");
      problems.push(`${slug} CP${item.id} ${item.title ?? ""}: gates not yet proven (${openGates}) at ${path}`);
    }
  }

  const counter = stopCounterPath(root, payload.session_id);
  if (problems.length === 0) {
    resetStopCounter(counter);
    return { deny: false };
  }

  let blocks: number;
  try {
    blocks = bumpStopCounter(counter, root);
  } catch (error) {
    return faultRefusal(payload, deny("Checkpoint", "Stop gate", `cannot persist the consecutive-stop limit (${error instanceof Error ? error.message : String(error)})`, "restore access to .ai-engineering/cache and retry"));
  }
  if (blocks > MAX_STOP_BLOCKS) {
    resetStopCounter(counter);
    return { deny: false };
  }
  return deny("Checkpoint", "Stop gate", `${problems.join("; ")}. Continue the checkpoint loop; if a human must take over, record halted with its reason and checkpoint`, "continue the loop or set the top-level halted reason before stopping");
}

export function runCheckpointGuard(payload: Payload, repoRoot: string | null): CheckpointGuardResult {
  if (repoRoot === null) return undefined;
  try {
    if (payload._event === "Stop" || payload.hook_event_name === "Stop") {
      return checkStop(payload, repoRoot);
    }
    if (payload.tool_name === "Bash") return checkBash(payload, repoRoot);
    if (payload.tool_name === "Task" || payload.tool_name === "Agent") {
      return checkMarker(payload, repoRoot);
    }
    if (payload.tool_name === "Write" || payload.tool_name === "Edit" || payload.tool_name === "MultiEdit") {
      // A patch is a diff, not the file's next contents: the gates cannot be checked on it.
      const patched = payload.tool_input.file_paths;
      if (Array.isArray(patched)) {
        const gated = patched.find((path) => checkpointTarget(repoRoot, path) !== null || aliasedCheckpoint(repoRoot, path) !== null);
        if (gated !== undefined) {
          return deny("Checkpoint", "write gate", `does not accept a patch to ${String(gated)}`, `edit ${CHECKPOINTS_DIR}/<slug>.json with the edit or create tool so checkpoint gates are validated`);
        }
      }
      return checkPlanWrite(payload, repoRoot);
    }
  } catch (error) {
    return deny("Checkpoint", "checkpoint gate", `could not decide safely (${error instanceof Error ? error.message : String(error)})`, "repair the checkpoint guard input and retry");
  }
  return undefined;
}
