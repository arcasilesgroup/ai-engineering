import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, rmSync, existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { execSync } from 'node:child_process';
import { installHooks } from '../../src/installer/hooks-installer.js';
import { createDefaultConfig } from '../../src/utils/config.js';

describe('hooks-installer', () => {
  let tempDir: string;

  beforeEach(() => {
    tempDir = mkdtempSync(join(tmpdir(), 'ai-eng-hooks-test-'));
    execSync('git init', { cwd: tempDir, stdio: 'pipe' });
  });

  afterEach(() => {
    rmSync(tempDir, { recursive: true, force: true });
  });

  it('should skip hooks for basic level', () => {
    const config = createDefaultConfig({ level: 'basic' });
    installHooks(tempDir, config);

    expect(existsSync(join(tempDir, 'lefthook.yml'))).toBe(false);
  });

  it('should install lefthook config for standard level', () => {
    const config = createDefaultConfig({ level: 'standard' });
    installHooks(tempDir, config);

    expect(existsSync(join(tempDir, 'lefthook.yml'))).toBe(true);
    const content = readFileSync(join(tempDir, 'lefthook.yml'), 'utf-8');
    expect(content).toContain('pre-commit');
    expect(content).toContain('gitleaks');
  });

  it('should install gitleaks config for standard level', () => {
    const config = createDefaultConfig({ level: 'standard' });
    installHooks(tempDir, config);

    expect(existsSync(join(tempDir, '.gitleaks.toml'))).toBe(true);
  });

  it('should include TypeScript linting in lefthook for TS stack', () => {
    const config = createDefaultConfig({
      level: 'standard',
      stacks: ['typescript-react'],
    });
    installHooks(tempDir, config);

    const content = readFileSync(join(tempDir, 'lefthook.yml'), 'utf-8');
    expect(content).toContain('eslint');
    expect(content).toContain('prettier');
  });

  it('should include Python linting in lefthook for Python stack', () => {
    const config = createDefaultConfig({
      level: 'standard',
      stacks: ['python'],
    });
    installHooks(tempDir, config);

    const content = readFileSync(join(tempDir, 'lefthook.yml'), 'utf-8');
    expect(content).toContain('ruff');
    expect(content).toContain('black');
  });

  it('should include .NET formatting in lefthook for .NET stack', () => {
    const config = createDefaultConfig({
      level: 'standard',
      stacks: ['dotnet'],
    });
    installHooks(tempDir, config);

    const content = readFileSync(join(tempDir, 'lefthook.yml'), 'utf-8');
    expect(content).toContain('dotnet-format');
  });

  it('should include branch protection in pre-push', () => {
    const config = createDefaultConfig({
      level: 'standard',
      branches: {
        defaultBranch: 'main',
        developBranch: 'develop',
        protectedBranches: ['main', 'develop'],
      },
    });
    installHooks(tempDir, config);

    const content = readFileSync(join(tempDir, 'lefthook.yml'), 'utf-8');
    expect(content).toContain('pre-push');
    expect(content).toContain('branch-protection');
    expect(content).toContain('main');
    expect(content).toContain('develop');
  });

  it('should include commit-msg hook with conventional commits', () => {
    const config = createDefaultConfig({ level: 'standard' });
    installHooks(tempDir, config);

    const content = readFileSync(join(tempDir, 'lefthook.yml'), 'utf-8');
    expect(content).toContain('commit-msg');
    expect(content).toContain('conventional');
    expect(content).toContain('feat');
  });

  it('should include dep audit for strict level', () => {
    const config = createDefaultConfig({
      level: 'strict',
      stacks: ['typescript-react'],
    });
    installHooks(tempDir, config);

    const content = readFileSync(join(tempDir, 'lefthook.yml'), 'utf-8');
    expect(content).toContain('npm-audit');
  });
});
