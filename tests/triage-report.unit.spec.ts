import { describe, expect, test } from "bun:test";
import {
  escapeHtml,
  sanitizeEvidenceUrl,
} from "../skills/ai-triage/scripts/render-report.mjs";

describe("report HTML sanitization", () => {
  test("escapes every HTML-special character in text", () => {
    expect(escapeHtml(`&<>"'`)).toBe("&amp;&lt;&gt;&quot;&#39;");
  });

  test("escapes every HTML-special character before attribute interpolation", () => {
    const hostileAttribute = `" onmouseover='alert(1)' &`;

    expect(escapeHtml(hostileAttribute)).toBe(
      "&quot; onmouseover=&#39;alert(1)&#39; &amp;",
    );
  });

  test("preserves a valid HTTPS evidence URL", () => {
    const evidenceUrl = "https://issues.example.test/items/42?view=full";

    expect(sanitizeEvidenceUrl(evidenceUrl)).toBe(evidenceUrl);
  });

  test("rejects unsafe, malformed, and relative evidence URLs", () => {
    const invalidUrls = [
      "javascript:alert(1)",
      "data:text/html,<script>alert(1)</script>",
      "/items/42",
      "//issues.example.test/items/42",
      "https://[",
    ];

    for (const evidenceUrl of invalidUrls) {
      expect(sanitizeEvidenceUrl(evidenceUrl)).toBeNull();
    }
  });

  test("never returns synthetic authentication or token values", () => {
    const syntheticToken = "synthetic-access-token-7f3c";
    const authenticationValues = [
      `Bearer ${syntheticToken}`,
      `https://issues.example.test/items/42?access_token=${syntheticToken}`,
      `https://${syntheticToken}@issues.example.test/items/42`,
    ];

    for (const authenticationValue of authenticationValues) {
      const sanitizedUrl = sanitizeEvidenceUrl(authenticationValue);

      expect(sanitizedUrl ?? "").not.toContain(syntheticToken);
    }
  });

  test("rejects encoded credential-shaped URL components", () => {
    const encodedToken = "%67ithub_pat_syntheticToken1234567890";
    const encodedUrls = [
      `https://issues.example.test/${encodedToken}`,
      `https://issues.example.test/items/42?project=${encodedToken}`,
      `https://${encodedToken}@issues.example.test/items/42`,
    ];

    for (const encodedUrl of encodedUrls) {
      expect(sanitizeEvidenceUrl(encodedUrl)).toBeNull();
    }
  });
});
