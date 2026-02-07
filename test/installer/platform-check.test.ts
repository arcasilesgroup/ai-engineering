import { describe, it, expect } from "vitest";
import { runPlatformCheck } from "../../src/installer/platform-check.js";

describe("platform-check", () => {
  it("should check platform dependencies", () => {
    const result = runPlatformCheck(["typescript-react"], "local-only");

    expect(result).toBeTruthy();
    expect(result.platform).toBe("local-only");
    expect(result.installedTools).toBeDefined();
    expect(Array.isArray(result.missingTools)).toBe(true);
  });

  it("should require git", () => {
    const result = runPlatformCheck(["typescript-react"], "local-only");

    const gitTool = result.installedTools.find((t) => t.name === "git");
    expect(gitTool).toBeTruthy();
    // Git should be available in test environment
    expect(gitTool?.available).toBe(true);
  });

  it("should always require gitleaks", () => {
    const result = runPlatformCheck(["typescript-react"], "local-only");

    const hasGitleaksRequirement =
      result.installedTools.some((t) => t.name === "gitleaks") ||
      result.missingTools.some((t) => t.name === "gitleaks");
    expect(hasGitleaksRequirement).toBe(true);
  });

  it("should require semgrep", () => {
    const result = runPlatformCheck(["typescript-react"], "local-only");

    const hasSemgrepRequirement =
      result.installedTools.some((t) => t.name === "semgrep") ||
      result.missingTools.some((t) => t.name === "semgrep");
    expect(hasSemgrepRequirement).toBe(true);
  });

  it("should check Python-specific tools", () => {
    const result = runPlatformCheck(["python"], "local-only");

    const hasPipAudit =
      result.installedTools.some((t) => t.name === "pip-audit") ||
      result.missingTools.some((t) => t.name === "pip-audit");
    expect(hasPipAudit).toBe(true);
  });

  it("should check .NET-specific tools", () => {
    const result = runPlatformCheck(["dotnet"], "local-only");

    const hasDotnet =
      result.installedTools.some((t) => t.name === "dotnet") ||
      result.missingTools.some((t) => t.name === "dotnet");
    expect(hasDotnet).toBe(true);
  });

  it("should detect default branch", () => {
    const result = runPlatformCheck(["typescript-react"], "local-only");
    expect(result.defaultBranch).toBeTruthy();
  });
});
