import { describe, it, expect } from 'vitest';
import { assemble } from '../../../src/compiler/assembler.js';
import { compileClaudeCode } from '../../../src/compiler/targets/claude-code.js';
import { createDefaultConfig } from '../../../src/utils/config.js';

describe('claude-code target', () => {
  it('should generate CLAUDE.md', () => {
    const config = createDefaultConfig();
    const ir = assemble(config);
    const output = compileClaudeCode(ir, '/tmp/test-project');

    expect(output.claudeMd).toBeTruthy();
    expect(output.claudeMd).toContain('Project Standards');
    expect(output.claudeMd).toContain('DANGER ZONE');
    expect(output.claudeMd).toContain('git push --force');
    expect(output.claudeMd).toContain('Compliance Branches');
    expect(output.claudeMd).toContain('Available Commands');
  });

  it('should include all slash commands', () => {
    const config = createDefaultConfig();
    const ir = assemble(config);
    const output = compileClaudeCode(ir, '/tmp/test-project');

    expect(output.commands.size).toBeGreaterThan(0);

    // Check for expected commands
    const commandNames = Array.from(output.commands.keys());
    expect(commandNames).toContain('ai-commit');
    expect(commandNames).toContain('ai-pr');
    expect(commandNames).toContain('ai-implement');
    expect(commandNames).toContain('ai-review');
  });

  it('should generate settings.json for strict level', () => {
    const config = createDefaultConfig({ level: 'strict' });
    const ir = assemble(config);
    const output = compileClaudeCode(ir, '/tmp/test-project');

    const settings = JSON.parse(output.settingsJson);
    expect(settings.hooks).toBeTruthy();
    expect(settings.hooks.PreToolUse).toBeTruthy();
    expect(settings.hooks.PostToolUse).toBeTruthy();
  });

  it('should generate empty settings for non-strict level', () => {
    const config = createDefaultConfig({ level: 'standard' });
    const ir = assemble(config);
    const output = compileClaudeCode(ir, '/tmp/test-project');

    const settings = JSON.parse(output.settingsJson);
    expect(settings.hooks).toBeUndefined();
  });

  it('should include protected branches in danger zone', () => {
    const config = createDefaultConfig({
      branches: {
        defaultBranch: 'master',
        developBranch: 'dev',
        protectedBranches: ['master', 'dev'],
      },
    });
    const ir = assemble(config);
    const output = compileClaudeCode(ir, '/tmp/test-project');

    expect(output.claudeMd).toContain('master');
    expect(output.claudeMd).toContain('dev');
  });

  it('should include multi-stack standards', () => {
    const config = createDefaultConfig({
      stacks: ['typescript-react', 'dotnet'],
    });
    const ir = assemble(config);
    const output = compileClaudeCode(ir, '/tmp/test-project');

    expect(output.claudeMd).toContain('TypeScript/React');
    expect(output.claudeMd).toContain('.NET');
  });
});
