// The spoken-secret classifier's contract, lifted from the original pack's
// tests/test_classify.py: a false positive registers an ordinary string and turns
// every later mention of it into noise, so the negatives are the contract — the
// positives only prove the detector fires at all. The negatives pin the 10 cases
// the original refuses, byte for byte.

import { describe, expect, test } from "bun:test";
import { candidates, judge, runSpokenSecret, slug } from "../src/guards/spoken-secret.ts";

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

describe("judge — every refusal names its reason, byte for byte", () => {
  test("unkeyed key name", () => expect(judge("PORT", "3000").reason).toBe("key name does not look like a secret"));
  test("public-by-design key name", () =>
    expect(judge("NEXT_PUBLIC_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9").reason).toBe("public-by-design key name"));
  test("placeholder or non-secret value", () => expect(judge("DB_PASSWORD", "changeme").reason).toBe("placeholder or non-secret value"));
  test("numeric value under a secret-shaped key: the value itself is read", () =>
    expect(judge("PASSWORD", "12345678").reason).toBe("numeric value"));
  test("filesystem path under a secret-shaped key", () => expect(judge("PASSWORD", "/var/log/app.log").reason).toBe("filesystem path"));
  test("below the 4-byte floor", () => expect(judge("TOKEN", "ab").reason).toBe("2 bytes: too short for any rule"));
  test("between the floors: handled by hand, never by rule", () =>
    expect(judge("TOKEN", "abcde").reason).toBe("5 bytes: below the 8-byte floor; handle by hand"));
});

describe("candidates — the extracted value and label are exact", () => {
  test("a quoted passphrase yields the inner text, quotes stripped", () => {
    const { auto } = candidates('the admin password is "copper lantern thicket" ok?');
    expect(auto.length).toBe(1);
    expect(auto[0]!.value).toBe("copper lantern thicket");
  });

  test("trailing sentence punctuation is not part of the value", () => {
    const { auto } = candidates("note the password is hunter2-delta-9.");
    expect(auto.length).toBe(1);
    expect(auto[0]!.value).toBe("hunter2-delta-9");
  });

  test("an assignment key names its own label", () => {
    expect(candidates("ADMIN_PASSWORD=hunter-and-friends").auto[0]!.label).toBe("prompt-admin-password");
  });

  test("digits alone are never auto-registered, and never handed to the agent", () => {
    expect(candidates("set TOKEN=12345678")).toEqual({ auto: [], manual: [] });
  });

  test("slug strips leading and trailing punctuation runs", () => {
    expect(slug("!!hello!!")).toBe("hello");
    expect(slug("Hello, World!")).toBe("hello-world");
  });
});

describe("runSpokenSecret — the denial text is the contract", () => {
  const run = (prompt?: string) =>
    runSpokenSecret({ tool_name: "Bash", tool_input: {}, ...(prompt === undefined ? {} : { prompt }) });

  const reasonOf = (prompt: string): string => {
    const out = run(prompt);
    if (!out || out.deny !== true) throw new Error("expected the prompt to be denied");
    return out.reason;
  };

  test("one auto secret: singular, its label, and the exact guidance", () => {
    const reason = reasonOf("my new staging password is velvet-anchor-thistle-21");
    expect(reason).toContain("the prompt carries 1 probable credential (label: prompt-staging-password).");
    expect(reason).toContain(
      "Do not write the value into code, .env or a commit: put it in a gitignored file (or the user's secret store) and refer to it by label.",
    );
  });

  test("two auto secrets: plural, labels comma-joined in prompt order", () => {
    const reason = reasonOf("set ADMIN_PASSWORD=hunter-and-friends and MY_TOKEN=velvet-anchor-thistle-21");
    expect(reason).toContain("the prompt carries 2 probable credentials (labels: prompt-admin-password, prompt-token).");
  });

  test("a free-text clause names its key and carries the hand-off sentence", () => {
    const reason = reasonOf("the admin password is purple monkey dishwasher");
    expect(reason).toContain("the prompt names a credential (the admin password) as free text whose exact value cannot be pinned automatically.");
    expect(reason).toContain(
      "Ask the user to move it to a gitignored file or a secret store before acting on anything else in this prompt.",
    );
  });

  test("two free-text clauses are comma-joined, never concatenated", () => {
    const reason = reasonOf("my password is purple monkey dishwasher; my token is red velvet cake dessert");
    expect(reason).toContain("(my password, my token)");
  });

  test("auto and manual halves meet at a single space", () => {
    const reason = reasonOf("set ADMIN_PASSWORD=hunter-and-friends; my password is purple monkey dishwasher");
    expect(reason).toContain("refer to it by label. the prompt names a credential");
  });

  test("no prompt field, or nothing to protect, stays silent", () => {
    expect(run()).toBeUndefined();
    expect(run("add a dark mode toggle to the settings page")).toBeUndefined();
  });
});
