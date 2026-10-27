import { lstatSync, readFileSync, realpathSync } from "node:fs";
import { isAbsolute, join, relative, sep } from "node:path";
import { resolveContext } from "../git/context.ts";
import { runGit } from "../git/run.ts";

export type CheckpointPhase =
  | "awaiting-plan-approval"
  | "implementation"
  | "blocked"
  | "awaiting-app-review"
  | "ready-to-merge";

export interface CheckpointLifecycle {
  phase: string;
  plan_approval: "pending" | "approved";
  app_review: "not-started" | "pending" | "approved";
  base_ref?: string | null;
  reviewed_base?: string | null;
  reviewed_feature?: string | null;
  [key: string]: unknown;
}

export interface CheckpointGate {
  status: string;
  attempts: number;
  findings: string[];
}

export interface CheckpointItem {
  id: number;
  title?: string;
  goal?: string;
  tasks?: string[];
  files?: string[];
  acceptance?: string[];
  verify?: string[];
  ui?: null | { route: string; prototype: string; scope: string; states: string[] };
  status: string;
  changed_files?: string[];
  gates: {
    behavior: CheckpointGate;
    ui: CheckpointGate;
    review: CheckpointGate;
  };
}

export interface Checkpoint {
  slug: string;
  checkpoints: CheckpointItem[];
  lifecycle: CheckpointLifecycle;
  [key: string]: unknown;
}

export interface CheckpointContext {
  repoPath: string;
  slug: string;
  baseRef: string;
}

const SHA_PATTERN = /^(?:[0-9a-f]{40}|[0-9a-f]{64})$/;
const SLUG_PATTERN = /^[a-z0-9][a-z0-9._-]*$/;
const GATE_STATUSES = ["pending", "failed", "passed", "n/a", "blocked"];
const CHECKPOINT_STATUSES = ["pending", "in_progress", "passed", "blocked"];
// A same-base reset is accepted only from a checkpoint already read or transitioned here.
const verifiedCheckpoints = new WeakSet<object>();

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function fail(field: string, message: string): never {
  throw new Error(`checkpoint ${field}: ${message}`);
}

function textList(value: unknown, field: string): value is string[] {
  if (!Array.isArray(value) || value.some((entry) => typeof entry !== "string")) {
    fail(field, "must be an array of strings");
  }
  return true;
}

function git(context: CheckpointContext, args: string[]) {
  return runGit(args, { cwd: context.repoPath, isolated: true });
}

function baseRefName(context: CheckpointContext): string {
  const prefix = "refs/heads/";
  if (!context.baseRef.startsWith(prefix) || context.baseRef.length === prefix.length) {
    fail("base_ref", `must be a local branch ref, got ${JSON.stringify(context.baseRef)}`);
  }
  return context.baseRef.slice(prefix.length);
}

function baseCommit(context: CheckpointContext): string {
  const branch = baseRefName(context);
  let root: string;
  try {
    root = resolveContext(context.repoPath, { explicitBase: branch }).root;
  } catch (error) {
    fail("base_ref", error instanceof Error ? error.message : String(error));
  }
  const result = runGit(
    ["rev-parse", "--verify", `${context.baseRef}^{commit}`],
    { cwd: root, isolated: true },
  );
  const commit = result.stdout.trim();
  if (result.status !== 0 || result.stderr.trim() !== "" || !SHA_PATTERN.test(commit)) {
    fail("base_ref", `cannot read ${context.baseRef} as a commit`);
  }
  return commit;
}

function knownCommit(context: CheckpointContext, sha: string, field: string): void {
  const result = git(context, ["cat-file", "-e", `${sha}^{commit}`]);
  if (result.status !== 0 || result.stderr.trim() !== "") {
    fail(field, `${sha} is not a known commit`);
  }
}

function requireAncestor(
  context: CheckpointContext,
  ancestor: string,
  descendant: string,
  field: string,
): void {
  const result = git(context, ["merge-base", "--is-ancestor", ancestor, descendant]);
  if (result.status !== 0 || result.stderr.trim() !== "") {
    fail(field, `${descendant} is not a descendant of reviewed_base ${ancestor}`);
  }
}

function normalizeLifecycle(
  value: unknown,
  context: CheckpointContext,
): CheckpointLifecycle {
  if (!isRecord(value)) fail("lifecycle", "must be an object");
  const keys = Object.keys(value);
  const legacy = Object.hasOwn(value, "reviewed_main");
  const allowed = new Set([
    "phase",
    "plan_approval",
    "app_review",
    "base_ref",
    "reviewed_base",
    "reviewed_main",
    "reviewed_feature",
  ]);
  if (
    keys.some((key) => !allowed.has(key)) ||
    keys.length < 4 ||
    keys.length > (legacy ? 6 : 6) ||
    (legacy && Object.hasOwn(value, "reviewed_base"))
  ) {
    fail("lifecycle", "contains missing, duplicate or unsupported fields");
  }

  const phase = value.phase === "complete" ? "ready-to-merge" : value.phase;
  if (
    phase !== "awaiting-plan-approval" &&
    phase !== "implementation" &&
    phase !== "blocked" &&
    phase !== "awaiting-app-review" &&
    phase !== "ready-to-merge"
  ) {
    fail("phase", `${String(value.phase)} is not supported`);
  }
  if (value.plan_approval !== "pending" && value.plan_approval !== "approved") {
    fail("plan_approval", "must be pending or approved");
  }
  if (
    value.app_review !== "not-started" &&
    value.app_review !== "pending" &&
    value.app_review !== "approved"
  ) {
    fail("app_review", "must be not-started, pending or approved");
  }

  const reviewedBase = legacy ? value.reviewed_main : value.reviewed_base;
  const baseRef = typeof value.base_ref === "string"
    ? value.base_ref
    : reviewedBase !== null && reviewedBase !== undefined
      ? context.baseRef
      : null;
  if (baseRef !== null && baseRef !== context.baseRef) {
    fail("base_ref", `must match the detected base ${context.baseRef}`);
  }
  for (const [field, sha] of [
    ["reviewed_base", reviewedBase],
    ["reviewed_feature", value.reviewed_feature],
  ] as const) {
    if (sha !== null && sha !== undefined && (typeof sha !== "string" || !SHA_PATTERN.test(sha))) {
      fail(field, "must be a full lowercase commit SHA");
    }
  }

  const hasReviewedBase = typeof reviewedBase === "string";
  const hasReviewedFeature = typeof value.reviewed_feature === "string";
  const hasNoReview = reviewedBase === null || reviewedBase === undefined
    ? value.reviewed_feature === null || value.reviewed_feature === undefined
    : false;
  if ((phase === "awaiting-plan-approval" && value.plan_approval !== "pending") ||
    (phase !== "awaiting-plan-approval" && value.plan_approval !== "approved" && phase !== "blocked")) {
    fail("plan_approval", `does not match phase ${phase}`);
  }
  if (phase === "implementation" && (hasReviewedBase || hasReviewedFeature)) {
    fail("reviewed_base", "must be cleared in implementation");
  }
  if (phase === "awaiting-plan-approval" || phase === "implementation") {
    const expectedApproval = phase === "awaiting-plan-approval" ? "pending" : "approved";
    if (value.plan_approval !== expectedApproval || value.app_review !== "not-started" || !hasNoReview) {
      fail("app_review", `fields do not match phase ${phase}`);
    }
  }
  if (phase === "awaiting-app-review" || phase === "ready-to-merge") {
    const expectedReview = phase === "awaiting-app-review" ? "pending" : "approved";
    if (value.app_review !== expectedReview) fail("app_review", `must be ${expectedReview} in phase ${phase}`);
    if (!hasReviewedBase || !hasReviewedFeature) {
      fail("reviewed_base", `reviewed_base and reviewed_feature are required in phase ${phase}`);
    }
  }
  if (phase === "blocked" && value.plan_approval === "pending" &&
    (value.app_review !== "not-started" || !hasNoReview)) {
    fail("app_review", "blocked must preserve pending plan approval");
  }
  if (phase === "blocked" && value.plan_approval === "approved" &&
    ((value.app_review === "not-started" && !hasNoReview) ||
      (value.app_review !== "not-started" && (!hasReviewedBase || !hasReviewedFeature)))) {
    fail("reviewed_base", "blocked must preserve earlier review state");
  }
  if (
    (phase === "awaiting-app-review" || phase === "ready-to-merge" ||
      (phase === "blocked" && value.app_review !== "not-started")) &&
    baseRef !== context.baseRef
  ) {
    fail("base_ref", `is required for pinned review state and must match ${context.baseRef}`);
  }

  if (hasReviewedBase && hasReviewedFeature) {
    baseCommit(context);
    knownCommit(context, reviewedBase as string, "reviewed_base");
    knownCommit(context, value.reviewed_feature as string, "reviewed_feature");
    requireAncestor(
      context,
      reviewedBase as string,
      value.reviewed_feature as string,
      "reviewed_feature",
    );
  }
  return {
    phase,
    plan_approval: value.plan_approval,
    app_review: value.app_review,
    base_ref: baseRef,
    reviewed_base: reviewedBase as string | null,
    reviewed_feature: (value.reviewed_feature ?? null) as string | null,
  };
}

function normalizeCheckpoint(value: unknown, context: CheckpointContext): Checkpoint {
  if (!SLUG_PATTERN.test(context.slug) || /\p{C}/u.test(context.slug)) {
    fail("slug", "context must contain a valid feature slug");
  }
  if (!isRecord(value)) fail("JSON", "must contain an object");
  if (value.slug !== context.slug) {
    fail("slug", `expected ${JSON.stringify(context.slug)}, got ${JSON.stringify(value.slug)}`);
  }
  if (!Array.isArray(value.checkpoints) || value.checkpoints.length === 0) {
    fail("checkpoints", "must be a non-empty array");
  }
  const legacyShape = !isRecord(value.lifecycle) || Object.hasOwn(value.lifecycle, "reviewed_main");
  for (const [index, checkpoint] of value.checkpoints.entries()) {
    const prefix = `checkpoints[${index}]`;
    if (!isRecord(checkpoint)) fail(prefix, "must be an object");
    if (!Number.isSafeInteger(checkpoint.id) || (checkpoint.id as number) < 1) {
      fail(`${prefix}.id`, "must be a positive finite integer");
    }
    if (!isRecord(checkpoint.gates)) fail(`${prefix}.gates`, "must be an object");
    for (const name of ["behavior", "ui", "review"] as const) {
      const gate = checkpoint.gates[name];
      if (!isRecord(gate)) fail(`${prefix}.gates.${name}`, "must be an object");
      if (!GATE_STATUSES.includes(String(gate.status))) {
        fail(`${prefix}.gates.${name}.status`, "is not supported");
      }
      if (!Number.isSafeInteger(gate.attempts) || (gate.attempts as number) < 0) {
        fail(`${prefix}.gates.${name}.attempts`, "must be a non-negative integer");
      }
      textList(gate.findings, `${prefix}.gates.${name}.findings`);
    }
    if (
      checkpoint.status === "passed" &&
      ["behavior", "ui", "review"].some((name) => {
        const status = (checkpoint.gates as Record<string, Record<string, unknown>>)[name]?.status;
        return status !== "passed" && status !== "n/a";
      })
    ) {
      fail(`${prefix}.status`, "passed requires every gate to be passed or n/a");
    }
    if (!CHECKPOINT_STATUSES.includes(String(checkpoint.status))) {
      fail(`${prefix}.status`, "is not supported");
    }
    for (const field of ["title", "goal"] as const) {
      if ((!legacyShape && typeof checkpoint[field] !== "string") ||
        (checkpoint[field] !== undefined && typeof checkpoint[field] !== "string")) {
        fail(`${prefix}.${field}`, "must be text");
      }
    }
    for (const field of ["tasks", "files", "acceptance", "verify", "changed_files"] as const) {
      if (!legacyShape && checkpoint[field] === undefined) {
        fail(`${prefix}.${field}`, "is required");
      }
      if (checkpoint[field] !== undefined) textList(checkpoint[field], `${prefix}.${field}`);
    }
    if (!legacyShape && checkpoint.ui === undefined) fail(`${prefix}.ui`, "is required");
    if (checkpoint.ui !== undefined && checkpoint.ui !== null) {
      if (!isRecord(checkpoint.ui)) fail(`${prefix}.ui`, "must be null or an object");
      for (const field of ["route", "prototype", "scope"] as const) {
        if (typeof checkpoint.ui[field] !== "string") fail(`${prefix}.ui.${field}`, "must be text");
      }
      textList(checkpoint.ui.states, `${prefix}.ui.states`);
    }
  }
  if (value.halted !== undefined && value.halted !== null) {
    if (!isRecord(value.halted) || typeof value.halted.reason !== "string" ||
      !Number.isSafeInteger(value.halted.checkpoint)) {
      fail("halted", "must be null or include a reason and checkpoint number");
    }
  }
  for (const field of ["assumptions", "notes"] as const) {
    if (value[field] !== undefined) textList(value[field], field);
  }
  const lifecycle = normalizeLifecycle(value.lifecycle, context);
  return { ...value, slug: context.slug, checkpoints: value.checkpoints as CheckpointItem[], lifecycle } as Checkpoint;
}

export function parseCheckpoint(contents: string, context: CheckpointContext): Checkpoint {
  let value: unknown;
  try {
    value = JSON.parse(contents);
  } catch (error) {
    fail("JSON", error instanceof Error ? error.message : String(error));
  }
  const checkpoint = normalizeCheckpoint(value, context);
  verifiedCheckpoints.add(checkpoint);
  return checkpoint;
}

export function readCheckpoint(path: string, context: CheckpointContext): Checkpoint {
  let contents: string;
  try {
    const repoRoot = realpathSync(context.repoPath);
    const stat = lstatSync(path);
    const realPath = realpathSync(path);
    const relativePath = relative(repoRoot, realPath);
    const expectedPath = join(repoRoot, ".ai-engineering", "workflow", "checkpoints", `${context.slug}.json`);
    if (
      !stat.isFile() ||
      stat.isSymbolicLink() ||
      relativePath === "" ||
      relativePath === ".." ||
      relativePath.startsWith(`..${sep}`) ||
      isAbsolute(relativePath) ||
      realPath !== expectedPath
    ) {
      fail("path", "is not the repository-local checkpoint file for this slug");
    }
    contents = readFileSync(path, "utf8");
  } catch (error) {
    if (error instanceof Error && error.message.startsWith("checkpoint ")) throw error;
    fail("path", error instanceof Error ? error.message : String(error));
  }
  return parseCheckpoint(contents, context);
}

export function serializeCheckpoint(checkpoint: Checkpoint): string {
  return `${JSON.stringify(checkpoint, null, 2)}\n`;
}

function gatesComplete(checkpoint: Checkpoint): boolean {
  return checkpoint.checkpoints.every((item) =>
    item.status === "passed" &&
    ["behavior", "ui", "review"].every((name) => {
      const status = item.gates[name as keyof CheckpointItem["gates"]].status;
      return status === "passed" || status === "n/a";
    })
  );
}

function sameReview(left: CheckpointLifecycle, right: CheckpointLifecycle): boolean {
  return left.plan_approval === right.plan_approval &&
    left.app_review === right.app_review &&
    left.base_ref === right.base_ref &&
    left.reviewed_base === right.reviewed_base &&
    left.reviewed_feature === right.reviewed_feature;
}

export function assertCheckpointTransition(
  previous: Checkpoint,
  next: Checkpoint,
  context: CheckpointContext,
): void {
  if (isRecord(next.lifecycle) && next.lifecycle.phase === "complete") {
    fail("phase", "complete is a legacy read-only phase");
  }
  const before = normalizeCheckpoint(previous, context);
  const after = normalizeCheckpoint(next, context);
  const hasVerifiedPrevious = verifiedCheckpoints.has(previous);
  const oldState = before.lifecycle;
  const newState = after.lifecycle;
  if (before.slug !== after.slug || before.slug !== context.slug) fail("slug", "cannot change during a transition");

  if (newState.phase === "blocked") {
    if (!sameReview(oldState, newState)) fail("lifecycle", "blocked must preserve earlier approvals");
    verifiedCheckpoints.add(next);
    return;
  }
  if (oldState.phase === "awaiting-plan-approval" && newState.phase === "implementation") {
    if (newState.plan_approval !== "approved") fail("plan_approval", "must be approved before implementation");
    verifiedCheckpoints.add(next);
    return;
  }
  if (oldState.phase === "implementation" && newState.phase === "awaiting-app-review") {
    if (!gatesComplete(after)) fail("gates", "all checkpoints must pass before app review");
    if (newState.reviewed_base !== baseCommit(context)) {
      fail("reviewed_base", "must pin the current base before app review");
    }
    const featureTip = git(context, ["rev-parse", "--verify", `refs/heads/feat/${context.slug}^{commit}`]);
    if (featureTip.status !== 0 || featureTip.stderr.trim() !== "" ||
      featureTip.stdout.trim() !== newState.reviewed_feature) {
      fail("reviewed_feature", "must pin the current feature tip before app review");
    }
    verifiedCheckpoints.add(next);
    return;
  }
  if (oldState.phase === "awaiting-app-review" && newState.phase === "implementation") {
    if (newState.app_review !== "not-started" ||
      newState.reviewed_base !== null ||
      newState.reviewed_feature !== null) {
      fail("reviewed_base", "request-changes must clear the reviewed SHAs");
    }
    if (baseCommit(context) === oldState.reviewed_base && !hasVerifiedPrevious) {
      fail("base_ref", "review invalidation requires a lost base compare-and-swap");
    }
    verifiedCheckpoints.add(next);
    return;
  }
  if (oldState.phase === "awaiting-app-review" && newState.phase === "ready-to-merge") {
    if (!gatesComplete(after)) fail("gates", "all checkpoints must pass before approval");
    if (
      newState.app_review !== "approved" ||
      newState.reviewed_base !== oldState.reviewed_base ||
      newState.reviewed_feature !== oldState.reviewed_feature ||
      newState.base_ref !== oldState.base_ref ||
      baseCommit(context) !== oldState.reviewed_base
    ) {
      fail("app_review", "approval must preserve the current reviewed base and feature SHAs");
    }
    verifiedCheckpoints.add(next);
    return;
  }
  if (oldState.phase === "blocked" && newState.phase === "ready-to-merge") {
    if (
      oldState.app_review !== "approved" ||
      !sameReview(oldState, newState) ||
      !gatesComplete(after)
    ) {
      fail("lifecycle", "blocked state may resume only with its preserved approval");
    }
    verifiedCheckpoints.add(next);
    return;
  }
  fail("phase", `${oldState.phase} cannot transition to ${newState.phase}`);
}

function htmlAttributes(source: string): Record<string, string> | null {
  const attributes: Record<string, string> = {};
  const attribute = /([^\s=/>]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/g;
  let cursor = 0;
  for (const match of source.matchAll(attribute)) {
    if (source.slice(cursor, match.index).trim() !== "") return null;
    const name = match[1]?.toLowerCase();
    const value = match[2] ?? match[3];
    if (name === undefined || value === undefined || Object.hasOwn(attributes, name)) return null;
    attributes[name] = value;
    cursor = (match.index ?? 0) + match[0].length;
  }
  return source.slice(cursor).replace(/\/\s*$/, "").trim() === "" ? attributes : null;
}

function htmlIsWellFormed(html: string): boolean {
  const withoutComments = html.replace(/<!--[\s\S]*?-->/gu, "");
  if (/<!--|-->/u.test(withoutComments)) return false;
  const withoutRawText = withoutComments.replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1\s*>/giu, "");
  if (/<(?:script|style)\b/iu.test(withoutRawText)) return false;
  const voidTags = new Set(["area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"]);
  const openTags: string[] = [];
  let htmlRoots = 0;
  for (const match of withoutRawText.matchAll(/<\/?([a-z][\w:-]*)\b[^>]*>/giu)) {
    const tag = (match[1] ?? "").toLowerCase();
    const isClosing = match[0]?.startsWith("</") === true;
    if (tag === "html" && !isClosing) htmlRoots += 1;
    if (isClosing) {
      if (openTags.pop() !== tag) return false;
    } else if (!voidTags.has(tag) && !match[0]?.endsWith("/>")) {
      openTags.push(tag);
    }
  }
  return htmlRoots === 1 && openTags.length === 0;
}

function decodedStatusLine(html: string): string[] {
  const lines: string[] = [];
  const container =
    /<([a-z][\w:-]*)\b(?=[^>]*\bclass\s*=\s*(?:"[^"]*\bmeta\b[^"]*"|'[^']*\bmeta\b[^']*'))[^>]*>([\s\S]*?)<\/\1\s*>/giu;
  for (const match of html.matchAll(container)) {
    const line = (match[2] ?? "").split(/<br\b[^>]*>/iu, 1)[0] ?? "";
    lines.push(
      line.replace(/<[^>]*>/gu, "")
        .replace(/&middot;|&#183;|&#x0*b7;/giu, "·")
        .replace(/&nbsp;|&#160;|&#x0*a0;/giu, " ")
        .replace(/&amp;/giu, "&")
        .replace(/&lt;/giu, "<")
        .replace(/&gt;/giu, ">")
        .replace(/&quot;/giu, '"')
        .replace(/&#39;|&apos;/giu, "'")
        .replace(/\s+/gu, " ")
        .trim(),
    );
  }
  return lines;
}

function brainstormApprovalResult(
  html: string,
  slug: string,
  now: Date,
): { approval: { slug: string; approvedOn: string } | null; problem: string | null } {
  if ((slug !== "" && (!SLUG_PATTERN.test(slug) || /\p{C}/u.test(slug)))) {
    return { approval: null, problem: "brainstorm feature slug is missing or ambiguous" };
  }
  if (!htmlIsWellFormed(html)) return { approval: null, problem: "brainstorm is malformed" };
  const metadata: Record<string, string[]> = { "ai-feature": [], "ai-approved": [] };
  for (const match of html.matchAll(/<meta\b([^>]*)>/giu)) {
    const attributes = htmlAttributes(match[1] ?? "");
    if (attributes === null) return { approval: null, problem: "brainstorm metadata is malformed" };
    const name = attributes.name;
    if (name === "ai-feature" || name === "ai-approved") {
      metadata[name]?.push(attributes.content ?? "");
    }
  }
  const feature = metadata["ai-feature"] ?? [];
  const approved = metadata["ai-approved"] ?? [];
  if (feature.length !== 1) {
    return { approval: null, problem: "brainstorm feature slug is missing or ambiguous" };
  }
  if (approved.length !== 1 || !/^\d{4}-\d{2}-\d{2}$/.test(approved[0] ?? "")) {
    return { approval: null, problem: "brainstorm approval date is missing or ambiguous" };
  }
  const featureSlug = feature[0] ?? "";
  if (!SLUG_PATTERN.test(featureSlug) || /\p{C}/u.test(featureSlug)) {
    return { approval: null, problem: "brainstorm feature slug is missing or ambiguous" };
  }
  if (slug !== "" && featureSlug !== slug) {
    return { approval: null, problem: `brainstorm belongs to ${featureSlug}, not ${slug}` };
  }
  const approvedOn = approved[0] ?? "";
  const [year, month, day] = approvedOn.split("-").map(Number);
  const approvedDate = new Date(Date.UTC(year ?? 0, (month ?? 1) - 1, day ?? 0));
  if (
    approvedDate.getUTCFullYear() !== year ||
    approvedDate.getUTCMonth() + 1 !== month ||
    approvedDate.getUTCDate() !== day
  ) {
    return { approval: null, problem: "brainstorm approval date is malformed" };
  }
  const statusLines = decodedStatusLine(html);
  if (statusLines.length !== 1 || statusLines[0] !== `complete · ${approvedOn}`) {
    return { approval: null, problem: "brainstorm approval does not match its complete status" };
  }
  const todayStart = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  const ageDays = (todayStart - approvedDate.getTime()) / 86_400_000;
  if (ageDays < 0 || ageDays > 14) {
    return { approval: null, problem: "brainstorm approval is expired or future-dated" };
  }
  return { approval: { slug: featureSlug, approvedOn }, problem: null };
}

export function parseBrainstormApproval(
  html: string,
  slug: string,
  now: Date,
): { slug: string; approvedOn: string } | null {
  return brainstormApprovalResult(html, slug, now).approval;
}

export function brainstormApprovalProblem(html: string, slug: string, now: Date): string | null {
  return brainstormApprovalResult(html, slug, now).problem;
}
