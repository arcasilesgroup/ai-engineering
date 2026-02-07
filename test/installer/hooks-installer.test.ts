import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, rmSync, existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { execSync } from "node:child_process";
import { installHooks } from "../../src/installer/hooks-installer.js";
import { createDefaultConfig } from "../../src/utils/config.js";

describe("hooks-installer", () => {
  let tempDir: string;

  beforeEach(() => {
    tempDir = mkdtempSync(join(tmpdir(), "ai-eng-hooks-test-"));
    execSync("git init", { cwd: tempDir, stdio: "pipe" });
  });

  afterEach(() => {
    rmSync(tempDir, { recursive: true, force: true });
  });

  it("should always install lefthook config", () => {
    const config = createDefaultConfig();
    installHooks(tempDir, config);

    expect(existsSync(join(tempDir, "lefthook.yml"))).toBe(true);
    const content = readFileSync(join(tempDir, "lefthook.yml"), "utf-8");
    expect(content).toContain("pre-commit");
    expect(content).toContain("gitleaks");
  });

  it("should always install gitleaks config", () => {
    const config = createDefaultConfig();
    installHooks(tempDir, config);

    expect(existsSync(join(tempDir, ".gitleaks.toml"))).toBe(true);
  });

  it("should include TypeScript linting in lefthook for TS stack", () => {
    const config = createDefaultConfig({
      stacks: ["typescript-react"],
    });
    installHooks(tempDir, config);

    const content = readFileSync(join(tempDir, "lefthook.yml"), "utf-8");
    expect(content).toContain("eslint");
    expect(content).toContain("prettier");
  });

  it("should include Python linting in lefthook for Python stack", () => {
    const config = createDefaultConfig({
      stacks: ["python"],
    });
    installHooks(tempDir, config);

    const content = readFileSync(join(tempDir, "lefthook.yml"), "utf-8");
    expect(content).toContain("ruff");
    expect(content).toContain("black");
  });

  it("should include .NET formatting in lefthook for .NET stack", () => {
    const config = createDefaultConfig({
      stacks: ["dotnet"],
    });
    installHooks(tempDir, config);

    const content = readFileSync(join(tempDir, "lefthook.yml"), "utf-8");
    expect(content).toContain("dotnet-format");
  });

  it("should include branch protection in pre-push", () => {
    const config = createDefaultConfig({
      branches: {
        defaultBranch: "main",
        developBranch: "develop",
        protectedBranches: ["main", "develop"],
      },
    });
    installHooks(tempDir, config);

    const content = readFileSync(join(tempDir, "lefthook.yml"), "utf-8");
    expect(content).toContain("pre-push");
    expect(content).toContain("branch-protection");
    expect(content).toContain("main");
    expect(content).toContain("develop");
  });

  it("should include commit-msg hook with conventional commits", () => {
    const config = createDefaultConfig();
    installHooks(tempDir, config);

    const content = readFileSync(join(tempDir, "lefthook.yml"), "utf-8");
    expect(content).toContain("commit-msg");
    expect(content).toContain("conventional");
    expect(content).toContain("feat");
  });

  it("should include full-project lint in pre-push", () => {
    const config = createDefaultConfig({
      stacks: ["typescript-react"],
    });
    installHooks(tempDir, config);

    const content = readFileSync(join(tempDir, "lefthook.yml"), "utf-8");
    expect(content).toContain("npx eslint .");
  });

  it("should include build in pre-push", () => {
    const config = createDefaultConfig({
      stacks: ["typescript-react"],
    });
    installHooks(tempDir, config);

    const content = readFileSync(join(tempDir, "lefthook.yml"), "utf-8");
    expect(content).toContain("npm run build");
  });

  it("should include gitleaks-branch in pre-push", () => {
    const config = createDefaultConfig();
    installHooks(tempDir, config);

    const content = readFileSync(join(tempDir, "lefthook.yml"), "utf-8");
    expect(content).toContain("gitleaks detect");
    expect(content).toContain("gitleaks-branch");
  });

  it("should include semgrep in pre-push", () => {
    const config = createDefaultConfig();
    installHooks(tempDir, config);

    const content = readFileSync(join(tempDir, "lefthook.yml"), "utf-8");
    expect(content).toContain("semgrep --config=auto");
  });

  it("should always include dep audit for TS stack", () => {
    const config = createDefaultConfig({
      stacks: ["typescript-react"],
    });
    installHooks(tempDir, config);

    const content = readFileSync(join(tempDir, "lefthook.yml"), "utf-8");
    expect(content).toContain("npm-audit");
  });

  it("should include Python lint and audit", () => {
    const config = createDefaultConfig({
      stacks: ["python"],
    });
    installHooks(tempDir, config);

    const content = readFileSync(join(tempDir, "lefthook.yml"), "utf-8");
    expect(content).toContain("ruff check .");
    expect(content).toContain("pip-audit");
  });

  it("should include dotnet build in pre-push", () => {
    const config = createDefaultConfig({
      stacks: ["dotnet"],
    });
    installHooks(tempDir, config);

    const content = readFileSync(join(tempDir, "lefthook.yml"), "utf-8");
    expect(content).toContain("dotnet build --no-restore");
  });
});
