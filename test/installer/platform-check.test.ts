import { describe, it, expect } from 'vitest';
import { runPlatformCheck } from '../../src/installer/platform-check.js';

describe('platform-check', () => {
  it('should check platform dependencies for basic level', () => {
    const result = runPlatformCheck(['typescript-react'], 'basic', 'local-only');

    expect(result).toBeTruthy();
    expect(result.platform).toBe('local-only');
    expect(result.installedTools).toBeDefined();
    expect(Array.isArray(result.missingTools)).toBe(true);
  });

  it('should require git for all levels', () => {
    const result = runPlatformCheck(['typescript-react'], 'basic', 'local-only');

    const gitTool = result.installedTools.find((t) => t.name === 'git');
    expect(gitTool).toBeTruthy();
    // Git should be available in test environment
    expect(gitTool?.available).toBe(true);
  });

  it('should require gitleaks for standard level', () => {
    const result = runPlatformCheck(['typescript-react'], 'standard', 'local-only');

    const hasGitleaksRequirement = result.installedTools.some((t) => t.name === 'gitleaks') ||
      result.missingTools.some((t) => t.name === 'gitleaks');
    expect(hasGitleaksRequirement).toBe(true);
  });

  it('should check Python-specific tools', () => {
    const result = runPlatformCheck(['python'], 'standard', 'local-only');

    const hasPipAudit = result.installedTools.some((t) => t.name === 'pip-audit') ||
      result.missingTools.some((t) => t.name === 'pip-audit');
    expect(hasPipAudit).toBe(true);
  });

  it('should check .NET-specific tools', () => {
    const result = runPlatformCheck(['dotnet'], 'standard', 'local-only');

    const hasDotnet = result.installedTools.some((t) => t.name === 'dotnet') ||
      result.missingTools.some((t) => t.name === 'dotnet');
    expect(hasDotnet).toBe(true);
  });

  it('should detect default branch', () => {
    const result = runPlatformCheck(['typescript-react'], 'basic', 'local-only');
    expect(result.defaultBranch).toBeTruthy();
  });
});
