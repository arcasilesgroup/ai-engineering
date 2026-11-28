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
  type BigIntStats,
} from "node:fs";
import { homedir } from "node:os";
import { basename, dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { isDeepStrictEqual } from "node:util";
import { resolveContext } from "../git/context.ts";
import { runGit } from "../git/run.ts";
import { readNoFollowFile, writeNoFollowFile } from "../shared-project-fs.ts";
import { inlineShellPrograms, jsonToolOperands, readCommands, readCommandsLenient, readsOperandsOnly, type ShellCommand } from "./shell.ts";
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
// Interpreters that can write any file their code names. Every other write form
// (redirection, tee, sed -i, cp, mv, rm, truncate) is judged by its target in
// shellWritesIntoCheckpoints.
// A versioned spelling (`python3.11`), a packaged one (`my-python3`) and a Windows one
// (`node.exe`) run the same program, so one predicate answers for all of them. Of the code
// writers only these can name a file the reader cannot see; awk writes only through its own
// program, judged below.
const CODE_WRITER = /(?:^|[-_])(?:python|node|perl)(?:\d+(?:\.\d+)*)?$/;
// The cwd rule treats every program that can reach a file as opaque, as it always has.
const OPAQUE_WRITER = /(?:^|[-_])(?:python|node|perl|ruby|bun|deno|jq|awk|gawk|mawk|nawk)(?:\d+(?:\.\d+)*)?$/;
const AWK = new Set(["awk", "gawk", "mawk", "nawk"]);
const AWK_WRITE = />|\||system\(/;
const CHECKPOINTS_DIR = ".ai-engineering/workflow/checkpoints";
const MAX_LINK_HOPS = 40;
const isCodeWriter = (name: string): boolean => CODE_WRITER.test(name);
const isOpaqueWriter = (name: string): boolean => OPAQUE_WRITER.test(name);
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
    const named = statSync(path, { bigint: true });
    const other = statSync(swapped, { bigint: true });
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
 *  case-variant name), by device and inode. Both as bigints: an NTFS file id passes 2^53,
 *  and as a JS number two checkpoints written a moment apart round to one id. */
function checkpointWithSameInode(folder: string, path: string): string | null {
  let target: BigIntStats;
  try {
    target = statSync(path, { bigint: true });
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
      const candidate = statSync(join(folder, name), { bigint: true });
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
  let html: string | null;
  try {
    // A symlink is not the file the person approved. Following it would let a
    // session point the approval check at a file they wrote somewhere else.
    html = readNoFollowFile(join(root, ".ai-engineering", "brainstorm.html"));
  } catch (error) {
    return deny(`Checkpoint ${checkpoint.slug}`, "plan approval", `cannot read the matching brainstorm (${error instanceof Error ? error.message : String(error)})`, "restore the approved brainstorm and retry the plan write");
  }
  if (html === null) {
    return deny(`Checkpoint ${checkpoint.slug}`, "plan approval", "cannot read the matching brainstorm (ENOENT: brainstorm.html is missing)", "restore the approved brainstorm and retry the plan write");
  }
  const problem = brainstormApprovalProblem(html, checkpoint.slug, new Date());
  if (problem !== null) {
    return deny(`Checkpoint ${checkpoint.slug}`, "plan approval", problem, "approve the matching brainstorm within the last 14 days");
  }
  return undefined;
}

function rawLifecycle(text: string): unknown {
  try {
    return (JSON.parse(text) as { lifecycle?: unknown }).lifecycle;
  } catch {
    return undefined;
  }
}

/** Why a plan on disk that does not validate cannot be repaired by this write, or null. It
 *  can when it is the committed plan, so nothing wrote it behind the gates, and the repair
 *  keeps its lifecycle, so a broken file never becomes a new approval. */
function repairProblem(context: CheckpointContext, previousText: string, nextText: string): string | null {
  const committed = runGit(["show", `HEAD:${CHECKPOINTS_DIR}/${context.slug}.json`], { cwd: context.repoPath, isolated: true });
  if (committed.status !== 0 || committed.stdout !== previousText) {
    return `cannot repair ${CHECKPOINTS_DIR}/${context.slug}.json: it does not validate and is not the committed plan`;
  }
  const lifecycle = rawLifecycle(previousText);
  if (lifecycle === undefined || !isDeepStrictEqual(lifecycle, rawLifecycle(nextText))) {
    return `cannot repair ${CHECKPOINTS_DIR}/${context.slug}.json: a repair keeps the committed lifecycle`;
  }
  return null;
}

function writtenPath(input: Record<string, unknown>): unknown {
  return input.file_path ?? input.notebook_path ?? input.path;
}

function checkPlanWrite(payload: Payload, repoRoot: string): CheckpointGuardResult {
  const filePath = writtenPath(payload.tool_input);
  const target = checkpointTarget(repoRoot, filePath);
  if (target === null) {
    const alias = aliasedCheckpoint(repoRoot, filePath);
    if (alias === null) return undefined;
    return deny(`Checkpoint ${alias}`, "write gate", `does not allow writing ${CHECKPOINTS_DIR}/${alias}.json through another path (${String(filePath)})`, `edit ${CHECKPOINTS_DIR}/${alias}.json by that path so checkpoint gates are validated`);
  }
  if (payload.tool_name === "NotebookEdit") {
    return deny(`Checkpoint ${target.slug}`, "write gate", "does not accept NotebookEdit of a checkpoint", "use Edit or Write so checkpoint gates are validated");
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
  } catch (error) {
    return deny(`Checkpoint ${target.slug}`, "checkpoint gate", `cannot read ${target.path} (${error instanceof Error ? error.message : String(error)})`, "repair the checkpoint file and retry the guarded write");
  }
  // A plan on disk that does not validate has no state to order against: only the write's
  // result is judged, so the file can be repaired from inside a session.
  let isRepair = false;
  try {
    if (previousText !== null) previous = parseCheckpoint(previousText, context);
  } catch {
    isRepair = true;
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
  if (isRepair) {
    const problem = repairProblem(context, previousText ?? "", text);
    return problem === null ? { deny: false } : deny(`Checkpoint ${target.slug}`, "checkpoint gate", problem, "restore the committed plan, then repair it with Edit or Write");
  }

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

/** The words one command runs: its program and its arguments, past `NAME=value` and the
 *  wrappers that run the next word, as the one shell model reads them. */
function commandWords(command: ShellCommand): string[] {
  return [command.verb, ...command.args.map((word) => word.value)];
}

/** Every command a line runs: the segments the reader hands over, the body of every heredoc
 *  it feeds, and the program each interpreter word runs, which is a command of its own. */
function commandsOf(command: string): ShellCommand[] {
  const programs = inlineShellPrograms(command);
  const commands = readCommands(command) ?? readCommandsLenient(command);
  const bodies = commands.flatMap((parsed) => parsed.segment.heredocs.flatMap(({ body }) => readCommands(body) ?? readCommandsLenient(body)));
  return [...commands, ...bodies, ...programs.flatMap((program) => readCommands(program) ?? readCommandsLenient(program))];
}

/** Verbs whose every operand is a path they write. */
const OPERAND_WRITERS = new Set(["tee", "mv", "rm", "truncate", "touch"]);
/** Verbs that end their argument list with the one path they write (`cp a b`, `install a b`). */
const DESTINATION_LAST = new Set(["cp", "install"]);

/** The word a stdin-fed writer substitutes each input for: `{}` unless xargs names another
 *  with `-I`/`-J`/`--replace`, whose value follows it or is attached. */
function stdinPlaceholder(prefix: readonly string[]): string {
  for (const [index, word] of prefix.entries()) {
    const attached = /^(?:-I|--replace=)(.+)$/.exec(word);
    if (attached !== null) return attached[1]!;
    if (["-I", "-J", "--replace"].includes(word)) return prefix[index + 1] ?? "{}";
  }
  return "{}";
}

/** The paths one command writes, unresolved: the files its redirections name, and the
 *  operands of the verbs that write them. Null when a wrapper feeds a writer from stdin and
 *  the destination's folder comes from it too (`echo demo.json | xargs rm`), so no folder is
 *  on the line to judge. */
function writeTargetsOf(command: ShellCommand): string[] | null {
  const targets = command.writes.map((word) => word.value);
  const operands = command.args.map((word) => word.value).filter((word) => !word.startsWith("-"));
  const isInPlaceSed = command.verb === "sed" && command.args.some((word) => /^-[a-zA-Z]*i/.test(word.value) || word.value.startsWith("--in-place"));
  const writesOperand = OPERAND_WRITERS.has(command.verb) || DESTINATION_LAST.has(command.verb) || command.verb === "dd" || isInPlaceSed;
  const prefix = command.plain.slice(0, command.verbIndex).map((word) => word.value);
  const isFedFromStdin = prefix.some((word) => basename(word) === "xargs");
  const named: string[] = [];
  const args = command.args.map((word) => word.value);
  // `dd if=… of=<file>` names its destination as an operand of its own.
  for (const operand of operands) if (operand.startsWith("of=")) named.push(operand.slice("of=".length));
  const targetDirectory = (): string | null => {
    const detached = args.findIndex((arg) => arg === "--target-directory" || /^-[A-Za-z]*t$/.test(arg));
    if (detached >= 0) return args[detached + 1] ?? "";
    const attached = args.flatMap((arg) => [/^--target-directory=(.+)$/.exec(arg)?.[1], /^-[A-Za-z]*t(.+)$/.exec(arg)?.[1]]);
    return attached.find((value) => value !== undefined) ?? null;
  };
  const directory = targetDirectory();
  // `ln target linkname` and `cp a b` create their last operand; with `-t dir` the
  // destination is that folder, and every operand is a source it leaves alone.
  if (command.verb === "ln" || DESTINATION_LAST.has(command.verb)) {
    named.push(...(directory === null ? operands.slice(-1) : [directory]));
  } else if (OPERAND_WRITERS.has(command.verb) || isInPlaceSed) {
    named.push(...operands);
    // `mv a b -t dir` both removes its operands and creates them inside dir.
    if (command.verb === "mv" && directory !== null) named.push(directory);
  }
  const written = named.filter((target) => target.length > 0);
  // A writer fed from stdin leaves its destination unnamed only while the folder it lands in
  // is the input's: `/tmp/backup/{}` lands outside wherever that input came from.
  if (isFedFromStdin && (writesOperand || operands.some((operand) => operand.startsWith("of=")))) {
    const placeholder = stdinPlaceholder(prefix);
    const isFolderUnknown = (target: string): boolean => {
      const cut = target.lastIndexOf("/");
      return cut < 0 ? target === placeholder : target.slice(0, cut).includes(placeholder);
    };
    if (written.length === 0 || written.some(isFolderUnknown)) return null;
  }
  targets.push(...written);
  return targets.filter((target) => target.length > 0);
}

/** json.tool only reads when its one operand is the checkpoint file. A second operand is
 *  the file it writes, and `-` makes it read stdin, so the operand after `-` is written. */
function isJsonToolRead(words: readonly string[], isCheckpointFile: (operand: string) => boolean): boolean {
  const operands = jsonToolOperands(words);
  if (operands?.length !== 1) return false;
  const operand = operands[0]!;
  return operand !== "-" && isCheckpointFile(operand);
}

/** Whether a command runs an interpreter that can write any path its code names: its verb,
 *  or a word a launcher outside the reader's prefixes runs (`npx node -e`, `uv run python3`).
 *  A command that only reads its operands runs nothing: `grep python3 plan.json` searches. */
function runsInterpreter(command: ShellCommand, isInterpreter: (name: string) => boolean): boolean {
  const programName = (word: string): string => basename(word).replace(/\.exe$/i, "");
  if (isInterpreter(programName(command.verb))) return true;
  if (readsOperandsOnly(command.verb, command.args.map((word) => word.value))) return false;
  return command.plain.some((word) => isInterpreter(programName(word.value)));
}

/** Whether awk's own program writes: an output redirection inside it, a system() call, or a
 *  program read from a file the guard cannot see. awk's own options take the word after them,
 *  so the program is the first word that is not one. */
function awkProgramWrites(command: ShellCommand): boolean {
  const args = command.args.map((word) => word.value);
  if (args.some((arg) => arg === "-i" || arg === "--inplace" || arg === "-iinplace")) return true;
  for (let index = 0; index < args.length; index++) {
    const arg = args[index]!;
    if (arg === "-f" || arg === "--file" || /^--file=/.test(arg) || /^-f.+/.test(arg)) return true;
    if (arg === "-v" || arg === "-F" || arg === "--assign" || arg === "--field-separator") {
      index += 1;
      continue;
    }
    if (/^-(?:v|F).+/.test(arg) || /^--(?:assign|field-separator)=/.test(arg)) continue;
    if (arg.startsWith("-")) continue;
    return AWK_WRITE.test(arg);
  }
  return false;
}

/** Whether one command that names a checkpoint runs an interpreter that could write it.
 *  json.tool with the checkpoint as its one operand only reads it. */
function hasOpaqueWriteForm(command: ShellCommand): boolean {
  if (isJsonToolRead(commandWords(command), (operand) => CHECKPOINT_TARGET.test(operand))) return false;
  if (runsInterpreter(command, isCodeWriter)) return true;
  return runsInterpreter(command, (name) => AWK.has(name)) && awkProgramWrites(command);
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
function shellWritesIntoCheckpoints(command: string, cwd: string | null, repo: RealRepo, mentions = /checkpoints/i.test(command)): boolean {
  const commands = readCommands(command) ?? readCommandsLenient(command);
  return commandsWriteIntoCheckpoints(commands, cwd, repo, mentions);
}

/** The same question asked of commands the reader already produced: each written where it
 *  stands, past the cd/pushd/popd the shell it runs in has run before it. */
function commandsWriteIntoCheckpoints(commands: readonly ShellCommand[], cwd: string | null, repo: RealRepo, mentions: boolean): boolean {
  const directories = new Map<number, string | null>([[0, cwd]]);
  const parents = new Map<number, number>();
  const stacks = new Map<number, Array<string | null>>();
  /** The directory one shell runs in: its own once a cd moved it, otherwise the one it
   *  inherited from the shell that started it. A nested shell moves only its own. */
  const directoryOf = (scope: number, parentScope: number): string | null => {
    parents.set(scope, parentScope);
    const known = directories.get(scope);
    if (known !== undefined) return known;
    let ancestor = parentScope;
    while (ancestor !== scope && ancestor !== 0 && !directories.has(ancestor)) ancestor = parents.get(ancestor) ?? 0;
    const inherited = directories.has(ancestor) ? directories.get(ancestor)! : cwd;
    directories.set(scope, inherited);
    return inherited;
  };
  for (const shellCommand of commands) {
    const words = commandWords(shellCommand);
    const [name, ...rest] = words;
    const { scope } = shellCommand.segment;
    const directory = directoryOf(scope, shellCommand.segment.parentScope);
    const stack = stacks.get(scope) ?? [];
    stacks.set(scope, stack);
    if (name === "cd" || name === "pushd") {
      const operand = rest.find((word) => !word.startsWith("-") || word === "-");
      if (name === "pushd") stack.push(directory);
      const next: string | null = operand === undefined ? homedir() : operand === "-" || directory === null ? null : shellPath(directory, operand);
      directories.set(scope, next);
      continue;
    }
    if (name === "popd") {
      directories.set(scope, stack.pop() ?? null);
      continue;
    }
    // A program handed to an interpreter runs where this command stands, in a shell of its own.
    for (const program of inlineShellPrograms(shellCommand.segment.text)) {
      if (shellWritesIntoCheckpoints(program, directory, repo, mentions)) return true;
    }
    // So does the body of a heredoc this command feeds: text alone cannot tell a program from
    // a commit message, so every body is judged as the commands it holds.
    for (const { body } of shellCommand.segment.heredocs) {
      if (commandsWriteIntoCheckpoints(readCommands(body) ?? readCommandsLenient(body), directory, repo, mentions)) return true;
    }
    if (directory !== null && runsInterpreter(shellCommand, isOpaqueWriter) && landsInCheckpoints(repo, directory)) {
      const here = directory;
      const isCheckpointFile = (operand: string): boolean => {
        const absolute = shellPath(here, operand);
        return absolute !== null && landsInCheckpoints(repo, absolute);
      };
      if (!isJsonToolRead(commandWords(shellCommand), isCheckpointFile)) return true;
    }
    const targets = writeTargetsOf(shellCommand);
    // A writer fed from stdin names no path on this line: the folder it runs in is all the
    // guard has, and a command that names the folder is refused rather than guessed at.
    if (targets === null) {
      if (directory === null ? mentions : landsInCheckpoints(repo, directory)) return true;
      continue;
    }
    for (const target of targets) {
      const absolute = isAbsolute(target) || target.startsWith("~") ? shellPath("/", target) : directory === null ? null : shellPath(directory, target);
      if (absolute === null ? mentions : landsInCheckpoints(repo, absolute)) return true;
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
  const isNamedWrite = CHECKPOINT_TARGET.test(command) && commandsOf(command).some(hasOpaqueWriteForm);
  if (!isNamedWrite && !shellWritesIntoCheckpoints(command, cwd, realRepo(repoRoot))) return undefined;
  return deny("Checkpoint", "shell gate", "does not allow direct Bash writes to checkpoint JSON", "use Edit or Write so checkpoint gates are validated");
}

/** True when this session is driving the plan: it started the orchestrator and dispatched a
 *  checkpoint marker for this slug. A plan path that merely appears in the transcript (git
 *  status, a listing, a refusal quoting it) is another feature's plan, not this session's. */
function drivesPlan(transcript: string, slug: string): boolean {
  const marker = new RegExp(`\\[checkpoint\\s+${slug.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}#\\d+\\s+\\w+\\]`);
  return marker.test(transcript);
}

/** The transcript of a session that started the orchestrator, or null: read once per Stop. */
function orchestratorTranscript(payload: Payload): string | null {
  const transcriptPath = payload.transcript_path;
  if (typeof transcriptPath !== "string" || transcriptPath.length === 0) return null;
  try {
    const transcript = readFileSync(transcriptPath, "utf8");
    return /"skill"\s*:\s*"ai-orchestrator"|<command-name>\/ai-orchestrator<\/command-name>/.test(transcript) ? transcript : null;
  } catch {
    return null;
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

/** How many consecutive Stops this session was refused for `reason`, this one included.
 *  The file holds the count, a newline, and the reason; another reason starts again at one. */
function bumpStopCounter(path: string, root: string, reason: string): number {
  ensureCounterDirectory(dirname(path), root);
  let count = 0;
  try {
    const stat = lstatSync(path);
    if (stat.isSymbolicLink() || !stat.isFile()) throw new Error(`${path} is not a regular file`);
    const stored = readNoFollowFile(path) ?? "";
    const newline = stored.indexOf("\n");
    const previous = Number(stored.slice(0, newline));
    if (newline > 0 && stored.slice(newline + 1) === reason && Number.isSafeInteger(previous) && previous > 0) count = previous;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
  }
  const next = count + 1;
  writeNoFollowFile(path, `${next}\n${reason}`);
  return next;
}

/** A plan the Stop gate cannot read is a file to repair, not a reason to hold the turn: it
 *  is said once per session, on stderr. A warning that cannot be remembered is still said. */
function warnOnce(root: string, sessionId: unknown, line: string): void {
  const path = `${stopCounterPath(root, sessionId).slice(0, -".txt".length)}.warned`;
  try {
    ensureCounterDirectory(dirname(path), root);
    let seen = "";
    try {
      if (!lstatSync(path).isFile()) throw new Error(`${path} is not a regular file`);
      seen = readNoFollowFile(path) ?? "";
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    }
    if (seen.split("\n").includes(line)) return;
    writeNoFollowFile(path, `${seen}${line}\n`);
  } catch {
    /* said below, unremembered */
  }
  process.stderr.write(`${line}\n`);
}

/** Exit 2 on Stop makes Claude continue, and it then sends the next Stop with
 *  `stop_hook_active`. A fault the agent cannot cure by continuing (the checkpoint file is
 *  itself guarded) must not hold the turn forever:
 *  - a fault that leaves nothing to judge (no repo, an unreadable folder, a counter that
 *    cannot be saved) is refused once, then the stop goes through;
 *  - a checkpoint file that cannot be validated is a warning (warnOnce), never a refusal;
 *  - every other refusal is counted and bounded by MAX_STOP_BLOCKS. */
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

  // One resolution serves every plan: the base is the repository's, not the plan's.
  let repository: ReturnType<typeof resolveContext>;
  try {
    repository = resolveContext(repoRoot);
  } catch (error) {
    return faultRefusal(payload, deny("Checkpoint", "Stop gate", `cannot resolve the repository (${error instanceof Error ? error.message : String(error)})`, "return to the repository and retry the Stop event"));
  }

  const root = repository.root;
  const baseRef = repository.base === null ? "" : `refs/heads/${repository.base}`;
  const folder = join(root, ".ai-engineering", "workflow", "checkpoints");
  let files: string[];
  try {
    files = readdirSync(folder).filter((file) => file.endsWith(".json")).sort();
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return { deny: false };
    return faultRefusal(payload, deny("Checkpoint", "Stop gate", `cannot list ${folder} (${error instanceof Error ? error.message : String(error)})`, "restore access to the checkpoint directory before stopping"));
  }

  const transcript = orchestratorTranscript(payload);
  const problems: string[] = [];
  for (const file of files) {
    const slug = file.slice(0, -".json".length);
    if (transcript === null || !drivesPlan(transcript, slug)) continue;
    const path = join(folder, file);
    let checkpoint: Checkpoint;
    try {
      checkpoint = readCheckpoint(path, { repoPath: root, slug, baseRef });
    } catch (error) {
      warnOnce(root, payload.session_id, `[ai-eng] checkpoint: warning: Stop gate cannot validate ${path} (${error instanceof Error ? error.message : String(error)}); repair it with Edit or Write`);
      continue;
    }
    if (requireSequentialCheckpoints(checkpoint, path) !== undefined) {
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

  const reason = problems.join("; ");
  let blocks: number;
  try {
    blocks = bumpStopCounter(counter, root, reason);
  } catch (error) {
    return faultRefusal(payload, deny("Checkpoint", "Stop gate", `cannot persist the consecutive-stop limit (${error instanceof Error ? error.message : String(error)})`, "restore access to .ai-engineering/cache and retry"));
  }
  // Past the limit the same open checkpoint (a background worker still running) lets every
  // Stop through: refusing again only burns the turns it is waiting with.
  if (blocks > MAX_STOP_BLOCKS) {
    warnOnce(root, payload.session_id, `[ai-eng] checkpoint: warning: Stop allowed after ${MAX_STOP_BLOCKS} refusals; the checkpoint is still open: ${reason}`);
    return { deny: false };
  }
  return deny("Checkpoint", "Stop gate", `${reason}. Continue the checkpoint loop; if a human must take over, record halted with its reason and checkpoint`, "continue the loop or set the top-level halted reason before stopping");
}

export function runCheckpointGuard(payload: Payload, repoRoot: string | null): CheckpointGuardResult {
  if (repoRoot === null) return undefined;
  try {
    if (payload._event === "Stop" || payload.hook_event_name === "Stop") {
      return checkStop(payload, repoRoot);
    }
    if (payload.tool_name === "Bash" || payload.tool_name === "PowerShell" || payload.tool_name === "shell" || payload.tool_name === "command") return checkBash(payload, repoRoot);
    if (payload.tool_name === "Task" || payload.tool_name === "Agent") {
      return checkMarker(payload, repoRoot);
    }
    if (payload.tool_name === "Write" || payload.tool_name === "Edit" || payload.tool_name === "MultiEdit" || payload.tool_name === "NotebookEdit") {
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
