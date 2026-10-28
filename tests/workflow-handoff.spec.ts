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
  test("ai-orchestrator owns the approve stop", () => {
    const block = lifecycle("skills/ai-orchestrator/SKILL.md");
    expect(block).toContain("Stop: approve");
    expect(block).toContain("approve");
  });

  test("U13: Phase 0 uses the current checkout and makes isolation optional", () => {
    const { text, body } = section("skills/ai-orchestrator/SKILL.md", "## Phase 0: Preflight");
    const phase1 = text.indexOf("## Phase 1: Plan");
    const normalized = body.replace(/\s+/g, " ").toLowerCase();
    expect(normalized).toContain("work in the current checkout by default");
    expect(normalized).toContain("managed worktree is optional, not a prerequisite");
    expect(normalized).toContain("when isolation is useful or requested");
    expect(normalized).toContain("exact git-listed worktree path");
    expect(normalized).toContain("feature-owned dirty files are continuable");
    expect(text.indexOf("## Phase 0: Preflight")).toBeLessThan(phase1);
  });

  test("U14: Phase 0 pauses likely overlaps but allows clearly unrelated work", () => {
    const { body } = section("skills/ai-orchestrator/SKILL.md", "## Phase 0: Preflight");
    const normalized = body.replace(/\s+/g, " ").toLowerCase();

    expect(normalized).toContain("could overlap");
    expect(normalized).toMatch(/\bpause\b/);
    expect(normalized).toMatch(/(?:pause|stop)[\s\S]{0,100}(?:human|user)[\s\S]{0,100}(?:decision|choose|confirm)/);
    expect(normalized).toContain("clearly unrelated");
    expect(normalized).toMatch(/\b(?:continue|proceed)\b/);
  });

  test("U16a: Phase 0 resumes feature-owned edits and leaves foreign work untouched", () => {
    const { body } = section("skills/ai-orchestrator/SKILL.md", "## Phase 0: Preflight");
    const normalized = body.replace(/[`*_]/g, "").replace(/\s+/g, " ").toLowerCase();
    expect(normalized).toMatch(/resume an exact same-slug feature/);
    expect(normalized).toMatch(/feature-owned dirty files are continuable/);
    expect(normalized).toMatch(/do not stash or reset them/);
    expect(normalized).toMatch(/leave foreign files untouched/);
    expect(normalized).toMatch(/if the checkpoint or ownership is unknown[\s\S]*preserve all work and ask/);
    expect(normalized).not.toMatch(/dirty or unknown status[\s\S]*stop phase 0 immediately/);
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

  test("U23: sync gates pin the detected base before the later human app-review handoff", () => {
    const { text: orchestrator } = section("skills/ai-orchestrator/SKILL.md", "## Phase 3: Wrap-up");
    const normalized = orchestrator.replace(/[`*]/g, "").replace(/\s+/g, " ").toLowerCase();
    const phase3Start = normalized.indexOf("## phase 3: wrap-up");
    const phase4Start = normalized.indexOf("## phase 4: human stop 2, app review", phase3Start);
    const phase3 = normalized.slice(phase3Start, phase4Start);
    const baseRead = phase3.indexOf("git rev-parse <base_ref>");
    const rebase = phase3.indexOf("git rebase <detected base>", baseRead);
    const clearConflict = phase3.indexOf("if a conflict is clear", rebase);
    const afterSync = phase3.indexOf("after a clean rebase or clear resolution", clearConflict);
    const behaviorGate = phase3.indexOf("rerun affected behavior checks", afterSync);
    const uiGate = phase3.indexOf("rerun affected ui checks only when the checkpoint has a ui gate", behaviorGate);
    const reviewGate = phase3.indexOf("rerun the affected review gate", uiGate);
    const gatesPassed = phase3.indexOf("after all affected gates pass", reviewGate);
    const mainRead = phase3.indexOf("git rev-parse <base_ref>", gatesPassed);
    const currentMain = phase3.indexOf("require its exact full commit to equal the target used for the rebase", mainRead);
    const guardedWrite = phase3.indexOf("checkpoint-gated state update", currentMain);
    const reviewedMain = phase3.indexOf("lifecycle.reviewed_base", guardedWrite);
    const fullCommitId = phase3.indexOf("retain the exact full commit as lifecycle.reviewed_base", guardedWrite);
    const featureTip = phase3.indexOf("git rev-parse <selected branch ref>", gatesPassed);
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
    expect(baseRead).toBeGreaterThanOrEqual(0);
    expect(rebase).toBeGreaterThan(baseRead);
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
    expect(fullCommitId).toBeGreaterThan(guardedWrite);
    expect(featureTip).toBeGreaterThan(gatesPassed);
    expect(reviewedFeature).toBeGreaterThan(featureTip);
    expect(phase3).toContain("exact full commit as lifecycle.reviewed_feature");
    expect(awaitingReview).toBeGreaterThan(reviewedFeature);
    expect(pendingReview).toBeGreaterThan(awaitingReview);
    expect(reviewCommit).toBeGreaterThan(pendingReview);
    expect(onlyThen).toBeGreaterThan(reviewCommit);
    expect(reviewGate).toBeLessThan(phase4Start);
    expect(humanAppReview).toBeGreaterThanOrEqual(0);
    expect(appReview).toMatch(/reviewed_base[\s\S]{0,100}(?:exact|current)[\s\S]{0,100}detected base/i);
    expect(appReview).not.toMatch(/git rebase/i);
  });

  test("U28a: CAS loss is handled by merge and requires resynchronization and renewed review", () => {
    const { body } = section("skills/ai-orchestrator/SKILL.md", "## Phase 4: Human stop 2, app review");
    const normalized = body.replace(/[`*]/g, "").replace(/\s+/g, " ").toLowerCase();
    const approval = normalized.split("- approve:")[1]?.split("- stop here:")[0] ?? "";
    const mergeCommand = approval.indexOf("ai-eng worktree merge <slug>");
    const casLoss = approval.indexOf("if the detected base moved before merge", mergeCommand);
    const implementation = approval.indexOf("returns it to implementation", casLoss);
    const invalidation = approval.indexOf("command clears the stale review shas", casLoss);
    const resync = approval.indexOf("rerun affected gates", invalidation);
    const rerunGates = approval.indexOf("affected gates", resync);
    const renewedReview = approval.indexOf("renewed human app review", rerunGates);

    expect(mergeCommand).toBeGreaterThanOrEqual(0);
    expect(casLoss).toBeGreaterThan(mergeCommand);
    expect(implementation).toBeGreaterThan(casLoss);
    expect(invalidation).toBeGreaterThan(casLoss);
    expect(resync).toBeGreaterThan(invalidation);
    expect(rerunGates).toBeGreaterThan(resync);
    expect(renewedReview).toBeGreaterThan(rerunGates);
    expect(approval).toMatch(/command owns the compare-and-swap transaction/);
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
    expect(initialPlanLifecycle).toContain("base_ref: null");
    expect(initialPlanLifecycle).toContain("reviewed_base: null");
    expect(initialPlanLifecycle).toContain("reviewed_feature: null");
    expect(initialPlanLifecycle).not.toContain("ask_user_question");
    expect(initialPlanLifecycle).not.toContain("human _stop_ 1: checkpoint review");
    expect(normalizedBrainstormHandoff).toContain("blueprint stop 0");
    expect(normalizedBrainstormHandoff).toContain(
      "a new checkpoint plan proceeds to implementation without another approval stop",
    );
    expect(normalizedBrainstormHandoff).toContain("the final app review remains a human stop");
    expect(normalizedBrainstormHandoff).not.toContain("the plan approval downstream is stop 1");
    expect(normalizedBrainstormHandoff).not.toContain("one idea, two stops, both human");
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
