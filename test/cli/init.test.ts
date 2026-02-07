import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mkdtempSync, rmSync, existsSync, readFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { execSync } from 'node:child_process';
import { createDefaultConfig, saveConfig } from '../../src/utils/config.js';
import { writeFile, ensureDir } from '../../src/utils/filesystem.js';

describe('init command', () => {
  let tempDir: string;

  beforeEach(() => {
    tempDir = mkdtempSync(join(tmpdir(), 'ai-eng-test-'));
    // Initialize git repo in temp dir
    execSync('git init', { cwd: tempDir, stdio: 'pipe' });
    execSync('git config user.email "test@test.com"', { cwd: tempDir, stdio: 'pipe' });
    execSync('git config user.name "Test"', { cwd: tempDir, stdio: 'pipe' });
  });

  afterEach(() => {
    rmSync(tempDir, { recursive: true, force: true });
  });

  it('should create default config', () => {
    const config = createDefaultConfig();
    expect(config.version).toBe('0.1.0');
    expect(config.stacks).toEqual(['typescript-react']);
    expect(config.ides).toEqual(['claude-code']);
    expect(config.level).toBe('standard');
    expect(config.platform).toBe('github');
  });

  it('should create config with overrides', () => {
    const config = createDefaultConfig({
      stacks: ['dotnet', 'python'],
      ides: ['copilot', 'codex'],
      level: 'strict',
      platform: 'azure-devops',
    });

    expect(config.stacks).toEqual(['dotnet', 'python']);
    expect(config.ides).toEqual(['copilot', 'codex']);
    expect(config.level).toBe('strict');
    expect(config.platform).toBe('azure-devops');
  });

  it('should save and load config file', () => {
    const config = createDefaultConfig({
      stacks: ['typescript-react', 'cicd'],
      ides: ['claude-code'],
      level: 'standard',
    });

    saveConfig(tempDir, config);

    const configPath = join(tempDir, '.ai-engineering/config.yml');
    expect(existsSync(configPath)).toBe(true);

    const content = readFileSync(configPath, 'utf-8');
    expect(content).toContain('typescript-react');
    expect(content).toContain('cicd');
    expect(content).toContain('claude-code');
    expect(content).toContain('standard');
  });

  it('should detect already-initialized project', () => {
    // Create a config file
    saveConfig(tempDir, createDefaultConfig());
    const configPath = join(tempDir, '.ai-engineering/config.yml');
    expect(existsSync(configPath)).toBe(true);
  });

  it('should support multi-stack config', () => {
    const config = createDefaultConfig({
      stacks: ['typescript-react', 'dotnet', 'python', 'cicd'],
    });

    expect(config.stacks).toHaveLength(4);
    expect(config.stacks).toContain('typescript-react');
    expect(config.stacks).toContain('dotnet');
    expect(config.stacks).toContain('python');
    expect(config.stacks).toContain('cicd');
  });

  it('should support multi-IDE config', () => {
    const config = createDefaultConfig({
      ides: ['claude-code', 'copilot', 'codex'],
    });

    expect(config.ides).toHaveLength(3);
  });

  it('should configure branch compliance', () => {
    const config = createDefaultConfig({
      branches: {
        defaultBranch: 'master',
        developBranch: 'dev',
        protectedBranches: ['master', 'dev'],
      },
    });

    expect(config.branches.defaultBranch).toBe('master');
    expect(config.branches.developBranch).toBe('dev');
    expect(config.branches.protectedBranches).toEqual(['master', 'dev']);
  });
});
