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

  test("preserves safe HTTPS GitHub and Azure links with normal query parameters", () => {
    const safeUrls = [
      "https://github.com/org/repo/issues/42?view=full&line=3",
      "https://dev.azure.com/org/project/_workitems/edit/42?view=full",
    ];

    for (const safeUrl of safeUrls) {
      expect(sanitizeEvidenceUrl(safeUrl)).toBe(safeUrl);
    }
  });

  test("rejects unsafe, malformed, and relative evidence URLs", () => {
    const invalidUrls = [
      "javascript:alert(1)",
      "data:text/html,<script>alert(1)</script>",
      "/items/42",
      "//issues.example.test/items/42",
      "https://[",
      "https://issues.example.test/items/%ZZ",
      "https://issues.example.test/items/%E0%A4%A",
      "https://user:password@issues.example.test/items/42",
      "https://user@issues.example.test/items/42",
    ];

    for (const evidenceUrl of invalidUrls) {
      expect(sanitizeEvidenceUrl(evidenceUrl)).toBeNull();
    }
  });

  test("rejects credential query keys and credential-like query values", () => {
    const credentialKeys = [
      "token",
      "auth",
      "password",
      "secret",
      "signature",
      "bearer",
    ];
    const syntheticToken = "github_pat_syntheticToken1234567890";
    const invalidUrls = [
      ...credentialKeys.map(
        (key) => `https://issues.example.test/items/42?${key}=synthetic-value`,
      ),
      `https://issues.example.test/items/42?view=Bearer%20${syntheticToken}`,
      `https://issues.example.test/items/42?view=Bearer%2520${syntheticToken}`,
    ];

    for (const invalidUrl of invalidUrls) {
      expect(sanitizeEvidenceUrl(invalidUrl)).toBeNull();
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
      "https://issues.example.test/%2567ithub_pat_syntheticToken1234567890",
      `https://issues.example.test/items/42?project=${encodedToken}`,
      "https://issues.example.test/items/42?%2561ccess_token=",
      `https://${encodedToken}@issues.example.test/items/42`,
      `https://issues.example.test/items/42?view=%2542earer%2520${encodedToken}`,
    ];

    for (const encodedUrl of encodedUrls) {
      expect(sanitizeEvidenceUrl(encodedUrl)).toBeNull();
    }
  });
});
