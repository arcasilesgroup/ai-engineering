import { describe, it, expect } from 'vitest';
import { assemble } from '../../../src/compiler/assembler.js';
import { compileCopilot } from '../../../src/compiler/targets/copilot.js';
import { createDefaultConfig } from '../../../src/utils/config.js';

describe('copilot target', () => {
  it('should generate copilot-instructions.md', () => {
    const config = createDefaultConfig();
    const ir = assemble(config);
    const output = compileCopilot(ir);

    expect(output.instructionsMd).toBeTruthy();
    expect(output.instructionsMd).toContain('GitHub Copilot Instructions');
    expect(output.instructionsMd).toContain('Critical Rules');
    expect(output.instructionsMd).toContain('git push --force');
  });

  it('should include branch compliance', () => {
    const config = createDefaultConfig({
      branches: {
        defaultBranch: 'main',
        developBranch: 'develop',
        protectedBranches: ['main', 'develop'],
      },
    });
    const ir = assemble(config);
    const output = compileCopilot(ir);

    expect(output.instructionsMd).toContain('main');
    expect(output.instructionsMd).toContain('develop');
    expect(output.instructionsMd).toContain('Branch Compliance');
  });

  it('should include code review checklist', () => {
    const config = createDefaultConfig();
    const ir = assemble(config);
    const output = compileCopilot(ir);

    expect(output.instructionsMd).toContain('Code Review Checklist');
    expect(output.instructionsMd).toContain('Security');
  });

  it('should include multi-stack standards', () => {
    const config = createDefaultConfig({
      stacks: ['typescript-react', 'python'],
    });
    const ir = assemble(config);
    const output = compileCopilot(ir);

    expect(output.instructionsMd).toContain('TypeScript/React');
    expect(output.instructionsMd).toContain('Python');
  });
});
