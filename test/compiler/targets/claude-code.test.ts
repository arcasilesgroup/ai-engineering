import { describe, it, expect } from "vitest";
import { assemble } from "../../../src/compiler/assembler.js";
import { compileClaudeCode } from "../../../src/compiler/targets/claude-code.js";
import { createDefaultConfig } from "../../../src/utils/config.js";

describe("claude-code target", () => {
  it("should generate CLAUDE.md", () => {
    const config = createDefaultConfig();
    const ir = assemble(config);
    const output = compileClaudeCode(ir, "/tmp/test-project");

    expect(output.claudeMd).toBeTruthy();
    expect(output.claudeMd).toContain("Project Standards");
    expect(output.claudeMd).toContain("DANGER ZONE");
    expect(output.claudeMd).toContain("git push --force");
    expect(output.claudeMd).toContain("Compliance Branches");
    expect(output.claudeMd).toContain("Available Commands");
  });

  it("should include all slash commands", () => {
    const config = createDefaultConfig();
    const ir = assemble(config);
    const output = compileClaudeCode(ir, "/tmp/test-project");

    expect(output.commands.size).toBeGreaterThan(0);

    // Check for expected commands
    const commandNames = Array.from(output.commands.keys());
    expect(commandNames).toContain("ai-ship");
    expect(commandNames).toContain("ai-implement");
    expect(commandNames).toContain("ai-review");
  });

  it("should always generate settings.json with hooks", () => {
    const config = createDefaultConfig();
    const ir = assemble(config);
    const output = compileClaudeCode(ir, "/tmp/test-project");

    const settings = JSON.parse(output.settingsJson);
    expect(settings.hooks).toBeTruthy();
    expect(settings.hooks.PreToolUse).toBeTruthy();
    expect(settings.hooks.PostToolUse).toBeTruthy();
    expect(settings.hooks.SessionStart).toBeTruthy();

    // Verify hook entries use the object format with type and command
    const preHook = settings.hooks.PreToolUse[0].hooks[0];
    expect(preHook).toEqual({
      type: "command",
      command: expect.stringContaining("pre-tool.sh"),
    });
    const postHook = settings.hooks.PostToolUse[0].hooks[0];
    expect(postHook).toEqual({
      type: "command",
      command: expect.stringContaining("post-tool.sh"),
    });
    const startupHook = settings.hooks.SessionStart[0].hooks[0];
    expect(startupHook).toEqual({
      type: "command",
      command: expect.stringContaining("version-check.sh"),
    });
  });

  it("should include protected branches in danger zone", () => {
    const config = createDefaultConfig({
      branches: {
        defaultBranch: "master",
        developBranch: "dev",
        protectedBranches: ["master", "dev"],
      },
    });
    const ir = assemble(config);
    const output = compileClaudeCode(ir, "/tmp/test-project");

    expect(output.claudeMd).toContain("master");
    expect(output.claudeMd).toContain("dev");
  });

  it("should include multi-stack standards", () => {
    const config = createDefaultConfig({
      stacks: ["typescript-react", "dotnet"],
    });
    const ir = assemble(config);
    const output = compileClaudeCode(ir, "/tmp/test-project");

    expect(output.claudeMd).toContain("TypeScript/React");
    expect(output.claudeMd).toContain(".NET");
  });

  it("should include actual standards content in CLAUDE.md (not empty sections)", () => {
    const config = createDefaultConfig();
    const ir = assemble(config);
    const output = compileClaudeCode(ir, "/tmp/test-project");

    // Verify sections have real content
    expect(output.claudeMd).toContain("Security Standards");
    expect(output.claudeMd).toContain("Git Conventions");
    expect(output.claudeMd).toContain("Testing Standards");
    expect(output.claudeMd).toContain("Agent Definitions");

    // Verify the assembled content is substantial (not just headers)
    expect(ir.assembled.security.length).toBeGreaterThan(100);
    expect(ir.assembled.git.length).toBeGreaterThan(100);
    expect(ir.assembled.testing.length).toBeGreaterThan(100);
  });

  it("should include all expected skill commands", () => {
    const config = createDefaultConfig();
    const ir = assemble(config);
    const output = compileClaudeCode(ir, "/tmp/test-project");

    expect(output.commands.size).toBeGreaterThanOrEqual(7);
    expect(output.commands.has("ai-ship")).toBe(true);
    expect(output.commands.has("ai-git")).toBe(true);
    expect(output.commands.has("ai-implement")).toBe(true);
    expect(output.commands.has("ai-review")).toBe(true);
    expect(output.commands.has("ai-security")).toBe(true);
    expect(output.commands.has("ai-explain")).toBe(true);
    expect(output.commands.has("ai-plan")).toBe(true);
  });

  it("should have non-empty content for each command", () => {
    const config = createDefaultConfig();
    const ir = assemble(config);
    const output = compileClaudeCode(ir, "/tmp/test-project");

    for (const [name, content] of output.commands) {
      expect(
        content.length,
        `command ${name} should have content`,
      ).toBeGreaterThan(100);
    }
  });
});
