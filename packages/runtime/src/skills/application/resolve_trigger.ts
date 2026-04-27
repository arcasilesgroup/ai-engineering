import {
  type Result,
  type SkillId,
  ValidationError,
  err,
  ok,
} from "../../shared/kernel/index.ts";
import type { Skill } from "../domain/skill.ts";

/**
 * ResolveTrigger — map a free-form user intent to the most relevant Skill.
 *
 * Pure function: deterministic keyword scoring against each Skill's frontmatter
 * description. The application layer keeps the matcher dumb on purpose —
 * "best matching" here is intentionally explainable so audit logs and
 * release-gate decisions can quote the score without being mystified by
 * an opaque embedding model.
 *
 * Tokens are lowercased, split on non-word boundaries, and short stopwords
 * (length < 3) are discarded. Score = count of distinct intent tokens that
 * appear in the skill's name + description. Tie-breaker: alphabetical SkillId.
 */
const STOPWORD_MIN_LEN = 3;
const TOKEN_RE = /[a-z0-9]+/g;

export class NoSkillMatched extends Error {
  readonly code = "NO_SKILL_MATCHED";
  constructor(intent: string) {
    super(`No skill matched intent: "${intent}"`);
    this.name = "NoSkillMatched";
  }
}

export interface TriggerMatch {
  readonly skillId: SkillId;
  readonly score: number;
  readonly matchedTokens: ReadonlyArray<string>;
}

const tokenize = (text: string): ReadonlyArray<string> =>
  (text.toLowerCase().match(TOKEN_RE) ?? []).filter(
    (t) => t.length >= STOPWORD_MIN_LEN,
  );

const uniqueTokens = (text: string): ReadonlySet<string> =>
  new Set(tokenize(text));

export const resolveTrigger = (
  skills: ReadonlyArray<Skill>,
  intent: string,
): Result<TriggerMatch, NoSkillMatched | ValidationError> => {
  if (intent.trim().length === 0) {
    return err(new ValidationError("Intent cannot be empty", "intent"));
  }
  if (skills.length === 0) {
    return err(new NoSkillMatched(intent));
  }

  const intentTokens = tokenize(intent);
  if (intentTokens.length === 0) {
    return err(new NoSkillMatched(intent));
  }

  let best: TriggerMatch | null = null;
  // Sort once for deterministic tie-breaking.
  const sorted = [...skills].sort((a, b) =>
    a.id < b.id ? -1 : a.id > b.id ? 1 : 0,
  );

  for (const skill of sorted) {
    const haystack = uniqueTokens(
      `${skill.frontmatter.name} ${skill.frontmatter.description}`,
    );
    const matched: string[] = [];
    for (const t of intentTokens) {
      if (haystack.has(t) && !matched.includes(t)) matched.push(t);
    }
    if (matched.length === 0) continue;
    const candidate: TriggerMatch = Object.freeze({
      skillId: skill.id,
      score: matched.length,
      matchedTokens: Object.freeze([...matched]),
    });
    if (best === null || candidate.score > best.score) {
      best = candidate;
    }
  }

  if (best === null) {
    return err(new NoSkillMatched(intent));
  }
  return ok(best);
};
