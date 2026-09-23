// The spoken-secret classifier's contract, lifted from the original pack's
// tests/test_classify.py: a false positive registers an ordinary string and turns
// every later mention of it into noise, so the negatives are the contract — the
// positives only prove the detector fires at all. The negatives pin the 10 cases
// the original refuses, byte for byte.

import { describe, expect, test } from "bun:test";
import { candidates, judge, slug } from "../src/guards/spoken-secret.ts";

describe("judge — registers real secrets", () => {
  const registers = (key: string, value: string) => {
    const verdict = judge(key, value);
    expect(verdict.decide).toBe(true);
    expect(verdict.reason).toBe("");
  };
  test("low-entropy passphrase under a secret-shaped key", () => registers("ADMIN_PASSWORD", "purple monkey dishwasher"));
  test("shaped key", () => registers("STRIPE_SECRET_KEY", "sk_test_51NxAbCdEfGhIjKlMnOpQr"));
  test("DSN with inline password (the inner password is the secret)", () => registers("DATABASE_URL", "postgres://admin:correct-horse@db:5432/app"));
  test("camelCase signing key", () => registers("jwt.signingKey", "a9f3c1d0e7b4a2f8c6"));
});

describe("judge — the 10 negatives (the contract)", () => {
  const refuses = (key: string, value: string, why: RegExp) => {
    const verdict = judge(key, value);
    expect(verdict.decide).toBe(false);
    expect(verdict.reason).toMatch(why);
  };
  test("PORT=3000 — unkeyed: refused on the key name before the value is read", () => refuses("PORT", "3000", /key name does not look/));
  test("NODE_ENV=development — unkeyed", () => refuses("NODE_ENV", "development", /key name does not look/));
  test("INTERNAL_HOST — host without credentials, unkeyed", () => refuses("INTERNAL_HOST", "events-db.corp.lan", /key name does not look/));
  test("LOG_PATH — filesystem path", () => refuses("LOG_PATH", "/var/log/app.log", /path|key name does not look/));
  test("DB_PASSWORD=your-password-here — placeholder prefix", () => refuses("DB_PASSWORD", "your-password-here", /placeholder/));
  test("DB_PASSWORD=changeme — placeholder value", () => refuses("DB_PASSWORD", "changeme", /placeholder/));
  test("ADMIN_PASSWORD=${ADMIN_PW} — template placeholder", () => refuses("ADMIN_PASSWORD", "${ADMIN_PW}", /placeholder/));
  test("NEXT_PUBLIC_ANON_KEY=JWT — public-by-design key", () => refuses("NEXT_PUBLIC_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", /public-by-design/));
  test("API_KEY=abc123 — 6 bytes: a short rule matches everywhere", () => refuses("API_KEY", "abc123", /bytes/));
  test("SESSION_TIMEOUT=3600 — unkeyed", () => refuses("SESSION_TIMEOUT", "3600", /key name does not look/));
});

describe("judge — boundary cases the original defines", () => {
  test("a public DSN still hides a real password: URL creds beat a public key name", () => {
    expect(judge("NEXT_PUBLIC_DATABASE_URL", "postgres://admin:correct-horse@db:5432/app").decide).toBe(true);
  });
  test("below 4 bytes is refused outright", () => {
    expect(judge("TOKEN", "ab").decide).toBe(false);
  });
  test("4-7 bytes needs the hand path, never an automatic rule", () => {
    const verdict = judge("TOKEN", "abcde");
    expect(verdict.decide).toBe(false);
    expect(verdict.reason).toMatch(/hand/);
  });
});

describe("candidates — prompt extraction", () => {
  test("exact values are auto-registerable", () => {
    for (const prompt of [
      "my new staging password is velvet-anchor-thistle-21, note it",
      'the admin password is "copper lantern thicket" ok?',
      "set ADMIN_PASSWORD=gravel-harbor-plume-19 in the env file",
    ]) {
      const { auto, manual } = candidates(prompt);
      expect(auto.length).toBe(1);
      expect(manual).toEqual([]);
    }
  });

  test("an unquoted multi-word passphrase goes to the agent, never a guess", () => {
    const { auto, manual } = candidates("the admin password is purple monkey dishwasher");
    expect(auto).toEqual([]);
    expect(manual.length).toBe(1);
  });

  test("quiet when there is nothing to protect", () => {
    for (const prompt of [
      "add a dark mode toggle to the settings page",
      "set DB_PASSWORD=your-password-here for now",
      "NEXT_PUBLIC_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9 is fine to commit",
      "the port is 5432 and the timeout is 30 seconds",
    ]) {
      expect(candidates(prompt)).toEqual({ auto: [], manual: [] });
    }
  });

  test("labels name the thing, never the value", () => {
    const { auto } = candidates("my new staging password is velvet-anchor-thistle-21");
    expect(auto[0]!.label).toBe("prompt-staging-password");
    expect(auto[0]!.label).not.toContain("velvet");
  });

  test("assignment form works too", () => {
    const { auto } = candidates("ADMIN_PASSWORD=hunter-and-friends");
    expect(auto.length).toBe(1);
    expect(auto[0]!.value).toBe("hunter-and-friends");
  });

  test("slug keeps its length cap and fallback", () => {
    expect(slug("!!!")).toBe("value");
    expect(slug("a very long label name that goes on and on and on")).toBe("a-very-long-label-name-that-goes-on-and-on-and-o");
  });
});
