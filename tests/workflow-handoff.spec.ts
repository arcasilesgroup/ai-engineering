import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = join(import.meta.dir, "..");

function lifecycle(path: string): string {
  const text = readFileSync(join(root, path), "utf8");
  const block = text.split("## Lifecycle")[1] ?? "";
  return block.split("\n## ")[0] ?? "";
}

function section(path: string, heading: string): { text: string; body: string } {
  const text = readFileSync(join(root, path), "utf8");
  const start = text.indexOf(heading);
  if (start < 0) return { text, body: "" };
  const bodyStart = start + heading.length;
  const nextHeading = /^#{1,3} /m.exec(text.slice(bodyStart));
  return {
    text,
    body: text.slice(bodyStart, nextHeading ? bodyStart + nextHeading.index : undefined),
  };
}

describe("workflow kit — feature work hands off to ai-orchestrator", () => {
  test("ai-brainstorm Lifecycle names ai-orchestrator", () => {
    expect(lifecycle("skills/ai-brainstorm/SKILL.md")).toContain("ai-orchestrator");
  });

  test("ai-orchestrator owns the approve stop", () => {
    const block = lifecycle("skills/ai-orchestrator/SKILL.md");
    expect(block).toContain("Stop: approve");
    expect(block).toContain("approve");
  });

  test("U13: Phase 0 selects or creates the clean same-slug worktree before Phase 1", () => {
    const { text, body } = section("skills/ai-orchestrator/SKILL.md", "## Phase 0: Preflight");
    const phase1 = text.indexOf("## Phase 1: Plan");
    const list = body.indexOf("ai-eng worktree list");
    expect(list).toBeGreaterThanOrEqual(0);

    const afterPreflight = body.slice(list);
    const normalizedAfterPreflight = afterPreflight.replace(/\s+/g, " ");
    const create = afterPreflight.indexOf("ai-eng worktree new");

    expect(afterPreflight).toMatch(/same slug/i);
    expect(afterPreflight).toMatch(/Git-listed path/i);
    expect(afterPreflight).toMatch(/\b(?:resume|existing worktree)\b/i);
    expect(normalizedAfterPreflight).toMatch(
      /only if that same-slug entry is clean[\s\S]{0,160}resume it using its exact git-listed path/i,
    );
    expect(normalizedAfterPreflight).toMatch(/(?:only|otherwise|else)[\s\S]{0,100}(?:slug[\s\S]{0,40}not listed|no matching slug)[\s\S]{0,100}ai-eng worktree new/i);
    expect(body).toMatch(/\bclean\b/i);
    expect(body).toMatch(/\btrusted\b/i);
    expect(create).toBeGreaterThan(0);
    expect(text.indexOf("## Phase 0: Preflight")).toBeLessThan(phase1);
  });

  test("U14: Phase 0 pauses likely overlaps but allows clearly unrelated work", () => {
    const { body } = section("skills/ai-orchestrator/SKILL.md", "## Phase 0: Preflight");

    expect(body).toMatch(/likely overlap/i);
    expect(body).toMatch(/\bpause\b/i);
    expect(body).toMatch(/(?:pause|stop)[\s\S]{0,100}(?:human|user)[\s\S]{0,100}(?:decision|choose|confirm)/i);
    expect(body).toMatch(/clearly unrelated/i);
    expect(body).toMatch(/\b(?:continue|proceed)\b/i);
  });

  test("U16a: Phase 0 stops on dirty or unknown same-slug status before lifecycle actions", () => {
    const { body } = section("skills/ai-orchestrator/SKILL.md", "## Phase 0: Preflight");
    const normalized = body.replace(/[`*_]/g, "").replace(/\s+/g, " ").toLowerCase();
    const listing = normalized.indexOf("ai-eng worktree list");
    const dirtyGuard = normalized.indexOf("has dirty or unknown status", listing);
    const refusal = normalized.slice(dirtyGuard, normalized.indexOf("only if that same-slug entry is clean", dirtyGuard));
    const resume = normalized.indexOf("resume it using its exact git-listed path", dirtyGuard);
    const noMatch = normalized.indexOf("if the slug is not listed", resume);
    const create = normalized.indexOf("ai-eng worktree new", noMatch);

    expect(listing).toBeGreaterThanOrEqual(0);
    expect(dirtyGuard).toBeGreaterThan(listing);
    expect(refusal).toContain("has dirty or unknown status");
    for (const status of ["dirty", "unknown", "missing", "untrusted"]) {
      expect(refusal).toContain(status);
    }
    expect(refusal).toMatch(/preserve it[\s\S]*report its exact git-listed path and evidence[\s\S]*stop phase 0 immediately/);
    expect(refusal).toMatch(
      /do not run ai-eng worktree new, resume it, rebase it, run ai-eng worktree rm, reset it, switch branches, or otherwise mutate it/,
    );
    expect(resume).toBeGreaterThan(dirtyGuard);
    expect(noMatch).toBeGreaterThan(resume);
    expect(create).toBeGreaterThan(noMatch);
  });

  test("U18: only resumed pending legacy plans wait for checkpoint approval", () => {
    const { text, body } = section("skills/ai-orchestrator/SKILL.md", "## Phase 1: Plan");
    const legacyStart = body.indexOf("For a resumed legacy plan");
    const freshPlan = body.slice(0, legacyStart);
    const legacyPlan = body.slice(legacyStart).replace(/[`*]/g, "").replace(/\s+/g, " ").toLowerCase();
    const humanStop = legacyPlan.indexOf("human _stop_ 1: checkpoint review");
    const askHuman = legacyPlan.indexOf("ask_user_question", humanStop);
    const approvalChoice = legacyPlan.indexOf("offer:", askHuman);
    const approveTransition = legacyPlan.indexOf(
      "after approval, set the lifecycle phase to implementation",
      approvalChoice,
    );
    const transitionInText = text
      .replace(/[`*_]/g, "")
      .toLowerCase()
      .indexOf("after approval, set the lifecycle phase to implementation");
    const phase2 = text.indexOf("## Phase 2: Checkpoint loop");
    const firstDispatch = text.indexOf("Use one `general-purpose` subagent", phase2);

    expect(legacyStart).toBeGreaterThanOrEqual(0);
    expect(freshPlan).not.toMatch(/ask_user_question|human _stop_ 1: checkpoint review/);
    expect(humanStop).toBeGreaterThanOrEqual(0);
    expect(askHuman).toBeGreaterThan(humanStop);
    expect(approvalChoice).toBeGreaterThan(askHuman);
    expect(legacyPlan.slice(approvalChoice)).toMatch(/offer:\s*approve,\s*edit[\s\S]{0,80}or stop/);
    expect(legacyPlan).toMatch(
      /do not (?:begin|run) phase 2 or dispatch its workers until the human approves the checkpoint plan/,
    );
    expect(approveTransition).toBeGreaterThan(approvalChoice);
    expect(phase2).toBeGreaterThanOrEqual(0);
    expect(text.indexOf("## Phase 1: Plan")).toBeLessThan(phase2);
    expect(firstDispatch).toBeGreaterThan(phase2);
    expect(phase2).toBeGreaterThan(transitionInText);
  });

  test("U23: sync gates capture local main before the later human app-review handoff", () => {
    const { text: orchestrator } = section("skills/ai-orchestrator/SKILL.md", "## Phase 3: Wrap-up");
    const normalized = orchestrator.replace(/[`*]/g, "").replace(/\s+/g, " ").toLowerCase();
    const phase3Start = normalized.indexOf("## phase 3: wrap-up");
    const phase4Start = normalized.indexOf("## phase 4: human stop 2, app review", phase3Start);
    const phase3 = normalized.slice(phase3Start, phase4Start);
    const rebase = phase3.indexOf("git rebase refs/heads/main");
    const clearConflict = phase3.indexOf("a clear conflict", rebase);
    const afterSync = phase3.indexOf("after a clean rebase or clear resolution", clearConflict);
    const behaviorGate = phase3.indexOf("rerun affected behavior checks", afterSync);
    const uiGate = phase3.indexOf("rerun affected ui checks only when the checkpoint has a ui gate", behaviorGate);
    const reviewGate = phase3.indexOf("rerun the affected review gate", uiGate);
    const gatesPassed = phase3.indexOf("after all affected gates pass", reviewGate);
    const mainRead = phase3.indexOf("git rev-parse refs/heads/main", gatesPassed);
    const currentMain = phase3.indexOf("require it to equal the exact local-main target used for the rebase", mainRead);
    const guardedWrite = phase3.indexOf("guarded edit or write", currentMain);
    const reviewedMain = phase3.indexOf("lifecycle.reviewed_main", guardedWrite);
    const fullCommitId = phase3.indexOf("exact full commit id returned by that command", reviewedMain);
    const featureTip = phase3.indexOf("git rev-parse refs/heads/feat/<slug>", gatesPassed);
    const reviewedFeature = phase3.indexOf("lifecycle.reviewed_feature", featureTip);
    const awaitingReview = phase3.indexOf("lifecycle.phase to awaiting-app-review", reviewedFeature);
    const pendingReview = phase3.indexOf("lifecycle.app_review to pending", awaitingReview);
    const reviewCommit = phase3.indexOf("checkpoint-only commit", pendingReview);
    const onlyThen = phase3.indexOf("only then proceed to phase 4", reviewCommit);
    const appReview = section("skills/ai-orchestrator/SKILL.md", "## Phase 4: Human stop 2, app review")
      .body.toLowerCase();
    const humanAppReview = appReview.indexOf("ask the user to try the feature");

    expect(phase3Start).toBeGreaterThanOrEqual(0);
    expect(phase4Start).toBeGreaterThan(phase3Start);
    expect(rebase).toBeGreaterThanOrEqual(0);
    expect(clearConflict).toBeGreaterThan(rebase);
    expect(afterSync).toBeGreaterThan(clearConflict);
    expect(behaviorGate).toBeGreaterThan(rebase);
    expect(uiGate).toBeGreaterThan(behaviorGate);
    expect(reviewGate).toBeGreaterThan(uiGate);
    expect(gatesPassed).toBeGreaterThan(reviewGate);
    expect(mainRead).toBeGreaterThan(gatesPassed);
    expect(currentMain).toBeGreaterThan(mainRead);
    expect(guardedWrite).toBeGreaterThan(currentMain);
    expect(reviewedMain).toBeGreaterThan(guardedWrite);
    expect(fullCommitId).toBeGreaterThan(reviewedMain);
    expect(featureTip).toBeGreaterThan(gatesPassed);
    expect(reviewedFeature).toBeGreaterThan(featureTip);
    expect(phase3).toMatch(/reviewed_feature[\s\S]{0,120}(?:exact|full) (?:commit )?(?:id|sha)/);
    expect(awaitingReview).toBeGreaterThan(reviewedFeature);
    expect(pendingReview).toBeGreaterThan(awaitingReview);
    expect(reviewCommit).toBeGreaterThan(pendingReview);
    expect(onlyThen).toBeGreaterThan(reviewCommit);
    expect(reviewGate).toBeLessThan(phase4Start);
    expect(humanAppReview).toBeGreaterThanOrEqual(0);
    expect(appReview).toMatch(/reviewed_main[\s\S]{0,100}(?:exact|current)[\s\S]{0,100}local main/i);
    expect(appReview).not.toMatch(/git rebase/i);
  });

  test("U28a: CAS loss invalidates only the checkpoint before resynchronization and renewed review", () => {
    const { body } = section("skills/ai-orchestrator/SKILL.md", "## Phase 4: Human stop 2, app review");
    const normalized = body.replace(/[`*]/g, "").replace(/\s+/g, " ");
    const approval = normalized.split("- Approve:")[1]?.split("- Stop here:")[0] ?? "";
    const mergeCommand = approval.indexOf("ai-eng worktree merge <slug>");
    const casLoss = approval.indexOf("If the command refuses", mergeCommand);
    const implementation = approval.indexOf("phase: implementation", casLoss);
    const appReview = approval.indexOf("app_review: not-started", casLoss);
    const reviewedMain = approval.indexOf("reviewed_main: null", casLoss);
    const reviewedFeature = approval.indexOf("reviewed_feature: null", casLoss);
    const invalidation = approval.indexOf("checkpoint-only commit", casLoss);
    const resync = approval.indexOf("Phase 3", invalidation);
    const rerunGates = approval.indexOf("affected gates", resync);
    const renewedReview = approval.indexOf("renewed human app review", rerunGates);

    expect(mergeCommand).toBeGreaterThanOrEqual(0);
    expect(casLoss).toBeGreaterThan(mergeCommand);
    expect(implementation).toBeGreaterThan(casLoss);
    expect(appReview).toBeGreaterThan(casLoss);
    expect(reviewedMain).toBeGreaterThan(casLoss);
    expect(reviewedFeature).toBeGreaterThan(casLoss);
    expect(invalidation).toBeGreaterThan(casLoss);
    expect(implementation).toBeGreaterThan(invalidation);
    expect(appReview).toBeGreaterThan(invalidation);
    expect(reviewedMain).toBeGreaterThan(invalidation);
    expect(reviewedFeature).toBeGreaterThan(invalidation);
    expect(resync).toBeGreaterThan(invalidation);
    expect(rerunGates).toBeGreaterThan(resync);
    expect(renewedReview).toBeGreaterThan(rerunGates);
  });

  test("U34: approved brainstorm opens the plan and proceeds to implementation without another approval", () => {
    const { text: orchestrator } = section("skills/ai-orchestrator/SKILL.md", "## The brainstorm gate");
    const { body: brainstormHandoff } = section(
      "skills/ai-brainstorm/SKILL.md",
      "## The ai-engineering seam",
    );
    const brainstormGate = orchestrator.indexOf("## The brainstorm gate");
    const phase0 = orchestrator.indexOf("## Phase 0: Preflight");
    const phase1 = orchestrator.indexOf("## Phase 1: Plan");
    const checkpointPlan = orchestrator.indexOf(
      ".ai-engineering/workflow/checkpoints/<slug>.json",
      phase1,
    );
    const viewer = orchestrator.indexOf(
      "http://localhost:8765/.ai-engineering/workflow/checkpoints/viewer.html?plan=<slug>",
      phase1,
    );
    const phase2 = orchestrator.indexOf("## Phase 2: Checkpoint loop");
    const gateText = orchestrator.slice(brainstormGate, phase0);
    const { body: plan } = section("skills/ai-orchestrator/SKILL.md", "## Phase 1: Plan");
    const normalizedPlan = plan.replace(/[`*]/g, "").replace(/\s+/g, " ").toLowerCase();
    const normalizedBrainstormHandoff = brainstormHandoff
      .replace(/[`*]/g, "")
      .replace(/\s+/g, " ")
      .toLowerCase();
    const checkpointStepStart = normalizedPlan.indexOf("1. checkpoints:");
    const testPlanStart = normalizedPlan.indexOf("2. test plan", checkpointStepStart);
    const initialPlanLifecycle = normalizedPlan.slice(checkpointStepStart, testPlanStart);
    const { body: appReview } = section(
      "skills/ai-orchestrator/SKILL.md",
      "## Phase 4: Human stop 2, app review",
    );
    const normalizedAppReview = appReview.replace(/[`*]/g, "").replace(/\s+/g, " ").toLowerCase();
    const humanReview = normalizedAppReview.indexOf("ask the user to try the feature");
    const approval = normalizedAppReview.indexOf("approve:", humanReview);
    const merge = normalizedAppReview.indexOf("ai-eng worktree merge <slug>", approval);

    expect(gateText).toContain('<meta name="ai-approved">');
    expect(gateText).toContain("within 14 days");
    expect(phase0).toBeGreaterThan(brainstormGate);
    expect(phase1).toBeGreaterThan(phase0);
    expect(checkpointPlan).toBeGreaterThan(phase1);
    expect(viewer).toBeGreaterThan(phase1);
    expect(viewer).toBeGreaterThan(checkpointPlan);
    expect(phase2).toBeGreaterThan(viewer);

    expect(initialPlanLifecycle).toContain("phase: implementation");
    expect(initialPlanLifecycle).toContain("plan_approval: approved");
    expect(initialPlanLifecycle).toContain("app_review: not-started");
    expect(initialPlanLifecycle).toContain("reviewed_main: null");
    expect(initialPlanLifecycle).toContain("reviewed_feature: null");
    expect(initialPlanLifecycle).not.toContain("ask_user_question");
    expect(initialPlanLifecycle).not.toContain("human _stop_ 1: checkpoint review");
    expect(normalizedBrainstormHandoff).toContain("blueprint stop 0");
    expect(normalizedBrainstormHandoff).toContain(
      "a new checkpoint plan proceeds to implementation without another approval stop",
    );
    expect(normalizedBrainstormHandoff).toContain("the final app review remains a human stop");
    expect(normalizedPlan).toContain("proceed directly to phase 2 without another approval question");
    const legacyPlanStart = normalizedPlan.indexOf("for a resumed legacy plan");
    const legacyPlan = normalizedPlan.slice(legacyPlanStart);
    expect(legacyPlan).toContain("ask_user_question");
    expect(legacyPlan).toContain("human _stop_ 1: checkpoint review");

    expect(humanReview).toBeGreaterThanOrEqual(0);
    expect(approval).toBeGreaterThan(humanReview);
    expect(merge).toBeGreaterThan(approval);
  });
});
