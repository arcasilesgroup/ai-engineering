import { execSync } from 'node:child_process';
import { readFileOrNull, writeFile, resolvePath, fileExists } from '../utils/filesystem.js';
import { logger } from '../utils/logger.js';

export interface UpdateInfo {
  currentVersion: string;
  latestVersion: string;
  updateAvailable: boolean;
  changelog: string | null;
}

const CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours

function readCurrentVersion(projectRoot: string): string {
  const versionFile = resolvePath(projectRoot, '.ai-engineering/.version');
  const content = readFileOrNull(versionFile);
  if (!content) return '0.0.0';
  return content.split('\n')[0]?.trim() ?? '0.0.0';
}

function readCachedVersion(projectRoot: string): { version: string; fresh: boolean } | null {
  const cachePath = resolvePath(projectRoot, '.ai-engineering/.update-cache');
  if (!fileExists(cachePath)) return null;

  const content = readFileOrNull(cachePath);
  if (!content) return null;

  const lines = content.trim().split('\n');
  const timestamp = parseInt(lines[0] ?? '0', 10);
  const version = lines[1] ?? '';

  if (!version) return null;

  const fresh = Date.now() - timestamp < CACHE_TTL_MS;
  return { version, fresh };
}

function writeCacheVersion(projectRoot: string, version: string): void {
  const cachePath = resolvePath(projectRoot, '.ai-engineering/.update-cache');
  writeFile(cachePath, `${Date.now()}\n${version}\n`);
}

function fetchLatestVersion(): string | null {
  try {
    const result = execSync('npm view ai-engineering version', {
      encoding: 'utf-8',
      timeout: 10000,
      stdio: ['pipe', 'pipe', 'pipe'],
    }).trim();
    return result || null;
  } catch {
    logger.debug('Could not reach npm registry');
    return null;
  }
}

function fetchChangelog(_currentVersion: string, _latestVersion: string): string | null {
  try {
    const result = execSync(`npm view ai-engineering --json`, {
      encoding: 'utf-8',
      timeout: 10000,
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    const pkg = JSON.parse(result) as { description?: string };
    return pkg.description ? `  ${pkg.description}` : null;
  } catch {
    return null;
  }
}

export async function checkForUpdates(projectRoot: string): Promise<UpdateInfo> {
  const currentVersion = readCurrentVersion(projectRoot);

  // Check cache first
  const cached = readCachedVersion(projectRoot);
  if (cached?.fresh) {
    return {
      currentVersion,
      latestVersion: cached.version,
      updateAvailable: cached.version !== currentVersion,
      changelog: null,
    };
  }

  // Fetch from registry
  const latestVersion = fetchLatestVersion();
  if (!latestVersion) {
    return {
      currentVersion,
      latestVersion: currentVersion,
      updateAvailable: false,
      changelog: null,
    };
  }

  // Update cache
  writeCacheVersion(projectRoot, latestVersion);

  const updateAvailable = latestVersion !== currentVersion;
  const changelog = updateAvailable ? fetchChangelog(currentVersion, latestVersion) : null;

  return {
    currentVersion,
    latestVersion,
    updateAvailable,
    changelog,
  };
}
