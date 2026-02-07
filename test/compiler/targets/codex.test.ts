import { describe, it, expect } from 'vitest';
import { assemble } from '../../../src/compiler/assembler.js';
import { compileCodex } from '../../../src/compiler/targets/codex.js';
import { createDefaultConfig } from '../../../src/utils/config.js';

describe('codex target', () => {
  it('should generate codex.md', () => {
    const config = createDefaultConfig();
    const ir = assemble(config);
    const output = compileCodex(ir);

    expect(output.codexMd).toBeTruthy();
    expect(output.codexMd).toContain('Codex Instructions');
    expect(output.codexMd).toContain('Absolute Rules');
    expect(output.codexMd).toContain('git push --force');
  });

  it('should include branch model', () => {
    const config = createDefaultConfig();
    const ir = assemble(config);
    const output = compileCodex(ir);

    expect(output.codexMd).toContain('Branch Model');
    expect(output.codexMd).toContain('main');
    expect(output.codexMd).toContain('develop');
  });

  it('should include implementation workflow', () => {
    const config = createDefaultConfig();
    const ir = assemble(config);
    const output = compileCodex(ir);

    expect(output.codexMd).toContain('Implementation Workflow');
    expect(output.codexMd).toContain('Review Checklist');
  });

  it('should include security standards', () => {
    const config = createDefaultConfig();
    const ir = assemble(config);
    const output = compileCodex(ir);

    expect(output.codexMd).toContain('Security');
  });
});
