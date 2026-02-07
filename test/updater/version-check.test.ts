import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, rmSync, mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { checkForUpdates } from '../../src/updater/version-check.js';

describe('version-check', () => {
  let tempDir: string;

  beforeEach(() => {
    tempDir = mkdtempSync(join(tmpdir(), 'ai-eng-version-test-'));
    mkdirSync(join(tempDir, '.ai-engineering'), { recursive: true });
  });

  afterEach(() => {
    rmSync(tempDir, { recursive: true, force: true });
  });

  it('should handle missing version file', async () => {
    const result = await checkForUpdates(tempDir);
    expect(result.currentVersion).toBe('0.0.0');
  });

  it('should read current version from version file', async () => {
    writeFileSync(join(tempDir, '.ai-engineering/.version'), '0.1.0\nfile.txt:abc123\n');

    const result = await checkForUpdates(tempDir);
    expect(result.currentVersion).toBe('0.1.0');
  });

  it('should use cache when fresh', async () => {
    writeFileSync(join(tempDir, '.ai-engineering/.version'), '0.1.0\n');
    writeFileSync(join(tempDir, '.ai-engineering/.update-cache'), `${Date.now()}\n0.1.0\n`);

    const result = await checkForUpdates(tempDir);
    // Should not have made network call, uses cache
    expect(result.currentVersion).toBe('0.1.0');
    expect(result.latestVersion).toBe('0.1.0');
    expect(result.updateAvailable).toBe(false);
  });

  it('should detect update available from cache', async () => {
    writeFileSync(join(tempDir, '.ai-engineering/.version'), '0.1.0\n');
    writeFileSync(join(tempDir, '.ai-engineering/.update-cache'), `${Date.now()}\n0.2.0\n`);

    const result = await checkForUpdates(tempDir);
    expect(result.currentVersion).toBe('0.1.0');
    expect(result.latestVersion).toBe('0.2.0');
    expect(result.updateAvailable).toBe(true);
  });
});
