import { describe, it, expect } from 'vitest';
import { assemble } from '../../src/compiler/assembler.js';
import { createDefaultConfig } from '../../src/utils/config.js';

describe('assembler', () => {
  it('should assemble single stack', () => {
    const config = createDefaultConfig({
      stacks: ['typescript-react'],
    });

    const ir = assemble(config);

    expect(ir.config).toBe(config);
    expect(ir.assembled.standards).toBeTruthy();
    expect(ir.assembled.standards.length).toBeGreaterThan(100);
    expect(ir.stackSections.size).toBeGreaterThanOrEqual(1);
  });

  it('should assemble multiple stacks', () => {
    const config = createDefaultConfig({
      stacks: ['typescript-react', 'dotnet'],
    });

    const ir = assemble(config);

    expect(ir.stackSections.size).toBeGreaterThanOrEqual(2);
    expect(ir.assembled.standards).toContain('TypeScript/React');
    expect(ir.assembled.standards).toContain('.NET');
  });

  it('should assemble agents', () => {
    const config = createDefaultConfig();
    const ir = assemble(config);

    expect(ir.assembled.agents).toBeTruthy();
    expect(ir.assembled.agents.length).toBeGreaterThan(100);
    expect(ir.agentSections.size).toBeGreaterThan(0);
  });

  it('should assemble skills', () => {
    const config = createDefaultConfig();
    const ir = assemble(config);

    expect(ir.assembled.skills).toBeTruthy();
    expect(ir.assembled.skills.length).toBeGreaterThan(100);
    expect(ir.skillSections.size).toBeGreaterThan(0);
  });

  it('should include security standards', () => {
    const config = createDefaultConfig();
    const ir = assemble(config);

    expect(ir.assembled.security).toBeTruthy();
    expect(ir.assembled.security.length).toBeGreaterThan(50);
  });

  it('should include git conventions', () => {
    const config = createDefaultConfig();
    const ir = assemble(config);

    expect(ir.assembled.git).toBeTruthy();
    expect(ir.assembled.git.length).toBeGreaterThan(50);
  });

  it('should include testing standards', () => {
    const config = createDefaultConfig();
    const ir = assemble(config);

    expect(ir.assembled.testing).toBeTruthy();
    expect(ir.assembled.testing.length).toBeGreaterThan(50);
  });

  it('should handle all four stacks', () => {
    const config = createDefaultConfig({
      stacks: ['typescript-react', 'dotnet', 'python', 'cicd'],
    });

    const ir = assemble(config);

    expect(ir.stackSections.size).toBeGreaterThanOrEqual(4);
  });
});
