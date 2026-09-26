// Spoken-secret guard — the classifier core of agit-secret-guard (MIT-unknown pack,
// ~/Downloads/agit-secret-guard), ported and verified against the original: every
// expectation in tests/spoken-secret.spec.ts was first confirmed by the original's
// tests/test_classify.py. A prompt is scanned for the two shapes a low-entropy
// spoken secret takes:
//
//   1. ASSIGNED — "ADMIN_PASSWORD=hunter-and-friends" / "api key: abc…"
//   2. SPOKEN   — "my new staging password is velvet-anchor-thistle-21"
//
// The verdict is advice, never an action: candidates() returns labels and a
// needs-attention list, and it is the caller's contract to never print or log the
// candidate value (the original's rule: a secret never travels via argv or stdout).
//
// Not ported on purpose: the agit vault plumbing (register/check/bootstrap/verify —
// speaks to `agit secrets`, and agit is not a dependency of this repo) and the
// file-scanning bootstrap (the floor's gitleaks gate already owns what lands in a
// commit; this guard's surface is the PROMPT, the one place gitleaks cannot see).

import type { Payload } from "../chain/payload.ts";

export const MIN_BYTES = 8; // a rule shorter than this matches inside unrelated words
export const SHORT_FLOOR = 4; // below this no rule should exist at all

const NOT_A_SECRET: Record<string, true> = {
  true: true, false: true, yes: true, no: true, on: true, off: true, development: true, production: true,
  staging: true, test: true, local: true, localhost: true, debug: true, info: true, warn: true, error: true,
  "utf-8": true, utf8: true, postgres: true, mysql: true, sqlite: true, redis: true, memory: true,
};
const SECRET_KEY =
  /(pass(word|wd|phrase)?|pwd|secret|token|credential|auth|private[_-]?key|api[_-]?key|access[_-]?key|client[_-]?secret|salt|signing|signature|session[_-]?key|cookie[_-]?secret|dsn|webhook|licen[cs]e[_-]?key|service[_-]?account|refresh[_-]?token|bearer|encryption)/i;

// public-by-design values: registering them only makes history unreadable
const PUBLIC_KEY = /(public|publishable|anon[_-]?key|_pub$|client[_-]?id)/i;

// a URL/DSN carrying inline credentials — the inner password is the real secret
const URL_CREDS = /^[a-z][a-z0-9+.-]*:\/\/(?<user>[^:/?#\s]+):(?<pw>[^@/?#\s]+)@/i;

const PLACEHOLDER =
  /^(your[_-]|my[_-]|some[_-]|the[_-])|^(changeme|change[_-]me|replace|placeholder|example|dummy|sample|todo|tbd|none|null|nil|n\/?a|xxx+|\.\.\.|\*+)$|^[<${].*[>}]$|(here|goes[_-]here|_here)$/i;

const BARE_PATH = /^(\/|~\/|\.\/|[a-z]:\\)/i;
const BARE_HOST_OR_URL = /^([a-z][a-z0-9+.-]*:\/\/)?[a-z0-9.-]+(:\d+)?(\/[^\s]*)?$/i;

const LABEL_NOISE: Record<string, true> = {
  my: true, the: true, our: true, a: true, an: true, new: true, current: true, old: true, and: true, is: true,
  this: true, that: true, his: true, her: true, their: true, your: true, its: true,
};

// "ADMIN_PASSWORD=hunter-and-friends" / "api key: abc…"
const ASSIGNED =
  /\b(?<key>[A-Za-z][A-Za-z0-9_-]*(?:pass(?:word|wd|phrase)?|pwd|secret|token|key|credential|dsn))\s*[:=]\s*(?<val>"[^"\n]+"|'[^'\n]+'|`[^`\n]+`|[^\s,;]+)/gi;

// "my new staging password is velvet-anchor-thistle-21"
// `val` is the first bare token; `clause` runs to the end of the sentence, because an
// unquoted passphrase ("purple monkey dishwasher") has no token boundary to stop at.
const SPOKEN =
  /\b(?<key>(?:[A-Za-z]+[ _-]){0,3}?(?:pass(?:word|phrase)|secret|api[ _-]?key|access[ _-]?key|token|credential)s?)\b(?:\s+(?:is|are|was|will be)|\s*[:=])\s+(?<val>"[^"\n]+"|'[^'\n]+'|`[^`\n]+`|[^\s,;]+)(?<rest>[^,;.\n]*)/gi;

const QUOTES = "\"'`";

export function slug(text: string): string {
  return (
    text
      .replace(/[^a-zA-Z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .toLowerCase()
      .slice(0, 48) || "value"
  );
}

/** Should this key/value pair be treated as a spoken secret? (decide, reason). */
export function judge(key: string, value: string): { decide: boolean; reason: string } {
  const leaf = key.split(".").pop() ?? key;
  const creds = URL_CREDS.test(value);
  const keyed = SECRET_KEY.test(leaf);

  if (PUBLIC_KEY.test(leaf) && !creds) return { decide: false, reason: "public-by-design key name" };
  if (!keyed && !creds) return { decide: false, reason: "key name does not look like a secret" };
  if (PLACEHOLDER.test(value) || NOT_A_SECRET[value.toLowerCase()])
    return { decide: false, reason: "placeholder or non-secret value" };
  if (/^\d+$/.test(value)) return { decide: false, reason: "numeric value" };
  if (!creds && BARE_PATH.test(value)) return { decide: false, reason: "filesystem path" };
  if (!creds && !keyed && BARE_HOST_OR_URL.test(value)) return { decide: false, reason: "host or URL without credentials" };
  const n = new TextEncoder().encode(value).length;
  if (n < SHORT_FLOOR) return { decide: false, reason: `${n} bytes: too short for any rule` };
  if (n < MIN_BYTES) return { decide: false, reason: `${n} bytes: below the 8-byte floor; handle by hand` };
  return { decide: true, reason: "" };
}

function unquote(value: string): { token: string; quoted: boolean } {
  if (value.length >= 2 && QUOTES.includes(value[0]!) && value[0] === value[value.length - 1])
    return { token: value.slice(1, -1), quoted: true };
  return { token: value, quoted: false };
}

function usable(value: string): boolean {
  return (
    value.length > 0 &&
    !/^\d+$/.test(value) &&
    new TextEncoder().encode(value).length >= MIN_BYTES &&
    !PLACEHOLDER.test(value) &&
    !NOT_A_SECRET[value.toLowerCase()]
  );
}

function labelFor(key: string): string {
  const words = key
    .toLowerCase()
    .split(/[\s_-]+/)
    .filter((w) => w.length > 0 && !LABEL_NOISE[w]);
  return slug("prompt-" + (words.length > 0 ? words.join("-") : "secret"));
}

export type Candidates = {
  /** Exact values with a clean boundary: a label for the thing, never the value. */
  auto: Array<{ value: string; label: string }>;
  /** Keys of unquoted multi-word clauses whose end the regex cannot know — the
   *  caller (or the model) must pin the exact value by hand. */
  manual: string[];
};

/** Scan a prompt for spoken secrets. Values are returned to the caller for
 *  handling, never printed or logged by this module. */
export function candidates(prompt: string): Candidates {
  const auto: Candidates["auto"] = [];
  const manual: string[] = [];
  const seen = new Set<string>();
  for (const match of [...prompt.matchAll(ASSIGNED), ...prompt.matchAll(SPOKEN)]) {
    const groups = match.groups ?? {};
    const { token, quoted } = unquote(groups.val ?? "");
    const trimmed = token.trim().replace(/[.,;:!?]+$/, "");
    const key = (groups.key ?? "secret").replace(/^[-_ ]+|[-_ ]+$/g, "");
    if (PUBLIC_KEY.test(key) || trimmed.length === 0 || seen.has(trimmed)) continue;
    seen.add(trimmed);
    // an exact span: quoted, or a single bare token that stands on its own
    if (quoted || usable(trimmed)) {
      if (usable(trimmed)) auto.push({ value: trimmed, label: labelFor(key) });
      continue;
    }
    // otherwise the value may be an unquoted multi-word passphrase, whose end the
    // regex cannot know — hand the whole clause's existence to the agent, not a guess
    const clause = (trimmed + (groups.rest ?? "")).trim();
    if (clause.includes(" ") && new TextEncoder().encode(clause).length >= MIN_BYTES) manual.push(key);
  }
  return { auto, manual };
}

export type GuardResult = { deny: true; reason: string } | { deny: false } | undefined;

/** Chain entry: the UserPromptSubmit arm. Reads the host's `prompt` field (Claude
 *  Code and Codex both send it; Copilot CLI's `userPromptSubmitted` names it the same).
 *  A hit never echoes the value back — the message names the SHAPE and what to do,
 *  and returns deny so the prompt cannot enter the transcript carrying a secret the
 *  agent has not been told to protect. */
export function runSpokenSecret(payload: Payload): GuardResult {
  const prompt = payload["prompt"];
  if (typeof prompt !== "string" || prompt.length === 0) return undefined;
  const { auto, manual } = candidates(prompt);
  if (auto.length === 0 && manual.length === 0) return undefined;
  const labels = auto.map((c) => c.label).join(", ");
  const manualKeys = manual.join(", ");
  const parts: string[] = [];
  if (auto.length > 0)
    parts.push(
      `the prompt carries ${auto.length} probable credential${auto.length > 1 ? "s" : ""} (label${auto.length > 1 ? "s" : ""}: ${labels}). ` +
        "Do not write the value into code, .env or a commit: put it in a gitignored file (or the user's secret store) and refer to it by label.",
    );
  if (manual.length > 0)
    parts.push(
      `the prompt names a credential (${manualKeys}) as free text whose exact value cannot be pinned automatically. ` +
        "Ask the user to move it to a gitignored file or a secret store before acting on anything else in this prompt.",
    );
  return {
    deny: true,
    reason: `spoken-secret: ${parts.join(" ")} The prompt text itself is the leak surface: treat every value it carried as something to keep out of the repo.`,
  };
}
