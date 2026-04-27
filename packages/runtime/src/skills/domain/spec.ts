import {
  type SpecId,
  ValidationError,
  type Result,
  ok,
  err,
} from "../../shared/kernel/index.ts";

/**
 * Spec — the contract approved before any code is written.
 *
 * Lifecycle: draft → approved → in_progress → merged | abandoned.
 * Once approved, a spec cannot transition back to draft (only to in_progress).
 *
 * SDD (Spec-Driven Development) — every implementation traces back to
 * a spec.id. The framework's HARD GATE is here: no `/ai-implement`
 * without an approved spec.
 */

export type SpecState =
  | "draft"
  | "approved"
  | "in_progress"
  | "merged"
  | "abandoned";

export interface Spec {
  readonly id: SpecId;
  readonly title: string;
  readonly motivation: string;
  readonly acceptanceCriteria: ReadonlyArray<string>;
  readonly nonGoals: ReadonlyArray<string>;
  readonly state: SpecState;
  readonly createdAt: Date;
  readonly updatedAt: Date;
}

const VALID_TRANSITIONS: Readonly<Record<SpecState, ReadonlyArray<SpecState>>> =
  Object.freeze({
    draft: ["approved", "abandoned"],
    approved: ["in_progress", "abandoned"],
    in_progress: ["merged", "abandoned"],
    merged: [],
    abandoned: [],
  });

export const canTransition = (from: SpecState, to: SpecState): boolean =>
  VALID_TRANSITIONS[from].includes(to);

export const createSpec = (input: {
  id: SpecId;
  title: string;
  motivation: string;
  acceptanceCriteria: ReadonlyArray<string>;
  nonGoals?: ReadonlyArray<string>;
  createdAt: Date;
}): Result<Spec, ValidationError> => {
  if (input.title.trim().length === 0) {
    return err(new ValidationError("Spec title cannot be empty", "title"));
  }
  if (input.motivation.trim().length === 0) {
    return err(
      new ValidationError("Spec motivation cannot be empty", "motivation"),
    );
  }
  if (input.acceptanceCriteria.length === 0) {
    return err(
      new ValidationError(
        "Spec must declare at least one acceptance criterion",
        "acceptanceCriteria",
      ),
    );
  }
  return ok(
    Object.freeze({
      id: input.id,
      title: input.title,
      motivation: input.motivation,
      acceptanceCriteria: Object.freeze([...input.acceptanceCriteria]),
      nonGoals: Object.freeze([...(input.nonGoals ?? [])]),
      state: "draft" as const,
      createdAt: input.createdAt,
      updatedAt: input.createdAt,
    }),
  );
};

export const transitionSpec = (
  spec: Spec,
  to: SpecState,
  now: Date,
): Result<Spec, ValidationError> => {
  if (!canTransition(spec.state, to)) {
    return err(
      new ValidationError(
        `Illegal Spec transition: ${spec.state} → ${to}`,
        "state",
      ),
    );
  }
  return ok(Object.freeze({ ...spec, state: to, updatedAt: now }));
};
