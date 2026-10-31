// src/guards/checkpoint.ts — checkpoint ordering runs in the chain, beside every other guard.

import { createHash } from "node:crypto";
import {
  lstatSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { isDeepStrictEqual } from "node:util";
import { resolveContext } from "../git/context.ts";
import {
  assertCheckpointTransition,
  brainstormApprovalProblem,
  checkpointComplete,
  parseCheckpoint,
  readCheckpointText,
  type Checkpoint,
  type CheckpointContext,
  type CheckpointItem,
} from "../workflow/checkpoint.ts";
import type { Payload } from "../payload.ts";

type CheckpointGuardResult = { deny: true; reason: string } | { deny: false } | undefined;

const GATES = ["behavior", "ui", "review"] as const;
const STAGES = new Set(["tests", "implement", "behavior", "ui", "review", "fix"]);
const MARKER = /^\s*\[checkpoint\s+([\w.-]+)#(\d+)\s+(\w+)\]/;
const CHECKPOINT_PATH = /^\.ai-engineering\/workflow\/checkpoints\/([a-z0-9][a-z0-9._-]*)\.json$/;
const CHECKPOINT_TARGET = /\.ai-engineering\/workflow\/checkpoints\/[^\s/]+\.json/;
const BASH_WRITE = />|\btee\b|\bsed\s+-i|\bpython3?\b|\bnode\b|\bperl\b|\bjq\b.*>|\bmv\b|\bcp\b|\btruncate\b/;
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

function checkpointTarget(repoRoot: string, filePath: unknown): { path: string; slug: string } | null {
  if (typeof filePath !== "string" || filePath.length === 0) return null;
  const root = resolve(repoRoot);
  const absolutePath = isAbsolute(filePath) ? resolve(filePath) : resolve(root, filePath);
  const relativePath = relative(root, absolutePath).split(sep).join("/");
  const match = CHECKPOINT_PATH.exec(relativePath);
  return match?.[1] ? { path: absolutePath, slug: match[1] } : null;
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
    if (checkpoint.status === "passed" && !checkpointComplete(checkpoint)) {
      return deny(`CP${checkpoint.id}`, "checkpoint status", "cannot be passed until every gate is passed or n/a", `finish the CP${checkpoint.id} gates`);
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
  if (target === null) return undefined;
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

  let context: CheckpointContext;
  let checkpoint: Checkpoint;
  const path = join(repoRoot, ".ai-engineering", "workflow", "checkpoints", `${slug}.json`);
  try {
    context = checkpointContext(repoRoot, slug);
    const text = readCheckpointText(path, context);
    if (text === null) throw new Error("file does not exist");
    checkpoint = parseCheckpoint(text, context);
  } catch (error) {
    return deny(label, "checkpoint gate", `cannot read ${path} (${error instanceof Error ? error.message : String(error)})`, "repair the checkpoint file and retry the marked task");
  }
  if (checkpoint.slug !== slug) {
    return deny(label, "checkpoint gate", `plan slug does not match marker "${slug}"`, "use the slug from the checkpoint filename");
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

function checkBash(payload: Payload): CheckpointGuardResult {
  const command = payload.tool_input.command;
  if (
    typeof command !== "string" ||
    !CHECKPOINT_TARGET.test(command) ||
    !BASH_WRITE.test(command)
  ) {
    return undefined;
  }
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

function checkStop(payload: Payload, repoRoot: string): CheckpointGuardResult {
  if (payload.stop_reason === "user_interrupt" || payload.stop_reason === "ask_user_question") {
    return { deny: false };
  }

  let root: string;
  try {
    root = resolveContext(repoRoot).root;
  } catch (error) {
    return deny("Checkpoint", "Stop gate", `cannot resolve the repository (${error instanceof Error ? error.message : String(error)})`, "return to the repository and retry the Stop event");
  }

  const folder = join(root, ".ai-engineering", "workflow", "checkpoints");
  let files: string[];
  try {
    files = readdirSync(folder).filter((file) => file.endsWith(".json")).sort();
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return { deny: false };
    return deny("Checkpoint", "Stop gate", `cannot list ${folder} (${error instanceof Error ? error.message : String(error)})`, "restore access to the checkpoint directory before stopping");
  }

  const problems: string[] = [];
  for (const file of files) {
    const slug = file.slice(0, -".json".length);
    if (!orchestratorTranscript(payload, slug)) continue;
    const path = join(folder, file);
    let checkpoint: Checkpoint;
    let context: CheckpointContext;
    try {
      context = checkpointContext(root, slug);
      const text = readCheckpointText(path, context);
      if (text === null) throw new Error("file does not exist");
      checkpoint = parseCheckpoint(text, context);
    } catch (error) {
      return deny(`Checkpoint ${slug}`, "Stop gate", `cannot validate ${path} (${error instanceof Error ? error.message : String(error)})`, "repair the checkpoint JSON before ending the turn");
    }
    const sequenceError = requireSequentialCheckpoints(checkpoint, path);
    if (sequenceError !== undefined) return sequenceError;
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
    return deny("Checkpoint", "Stop gate", `cannot persist the consecutive-stop limit (${error instanceof Error ? error.message : String(error)})`, "restore access to .ai-engineering/cache and retry");
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
    if (payload.tool_name === "Bash") return checkBash(payload);
    if (payload.tool_name === "Task" || payload.tool_name === "Agent") {
      return checkMarker(payload, repoRoot);
    }
    if (payload.tool_name === "Write" || payload.tool_name === "Edit" || payload.tool_name === "MultiEdit") {
      return checkPlanWrite(payload, repoRoot);
    }
  } catch (error) {
    return deny("Checkpoint", "checkpoint gate", `could not decide safely (${error instanceof Error ? error.message : String(error)})`, "repair the checkpoint guard input and retry");
  }
  return undefined;
}
