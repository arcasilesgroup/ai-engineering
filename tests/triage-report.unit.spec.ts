import { describe, expect, test } from "bun:test";
import {
  escapeHtml,
  renderAnalysis,
  sanitizeEvidenceUrl,
} from "../skills/ai-triage/scripts/render-report.mjs";

describe("report HTML sanitization", () => {
  test("formats analysis emphasis, code, paragraphs, and safe provider links", () => {
    expect(renderAnalysis(
      "**Decision**: *verify first* with `release/0.6.0`.\n\n[GitHub](https://github.com/org/repo/issues/42) and [Azure](https://dev.azure.com/org/project/_workitems/edit/42)",
    )).toBe(
      '<strong>Decision</strong>: <em>verify first</em> with <code>release/0.6.0</code>.\n\n<a href="https://github.com/org/repo/issues/42" target="_blank" rel="noreferrer noopener">GitHub</a> and <a href="https://dev.azure.com/org/project/_workitems/edit/42" target="_blank" rel="noreferrer noopener">Azure</a>',
    );
  });

  test("keeps raw HTML inert and redacts credentials before formatting", () => {
    const rendered = renderAnalysis(
      '<img src=x onerror=alert(1)> **<script>attack()</script>** `token=synthetic-secret` & "quotes"',
    );
    expect(rendered).toContain("&lt;img src=x onerror=alert(1)&gt;");
    expect(rendered).toContain("<strong>&lt;script&gt;attack()&lt;/script&gt;</strong>");
    expect(rendered).not.toContain("synthetic-secret");
    expect(rendered).not.toContain("<script>");
    expect(rendered).toContain("&amp; &quot;quotes&quot;");
  });

  test("rejects unsafe analysis links rather than emitting clickable content", () => {
    for (const url of [
      "javascript:alert",
      "data:text/html,attack",
      "https://example.test/?token=synthetic-secret",
      "https://example.test/%ZZ",
    ]) {
      expect(() => renderAnalysis(`[unsafe](${url})`)).toThrow(
        "Invalid analysis link",
      );
    }
  });

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

  test("rejects bearer and token assignments in URL fragments and decoded components", () => {
    const unsafeUrls = [
      "https://issues.example.test/items/42#bearer=synthetic-secret",
      "https://issues.example.test/items/42#%62earer=synthetic-secret",
      "https://issues.example.test/items/42#view=token%3Dsynthetic-secret",
      "https://issues.example.test/items/42#view=%2574oken%253Dsynthetic-secret",
      "https://issues.example.test/items/token%3Dsynthetic-secret",
    ];

    for (const unsafeUrl of unsafeUrls) {
      expect(sanitizeEvidenceUrl(unsafeUrl)).toBeNull();
    }
  });
});
