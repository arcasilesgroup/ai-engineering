import { execSync } from 'node:child_process';
import { logger } from './logger.js';
import type { Platform } from './config.js';

export interface GitInfo {
  isGitRepo: boolean;
  remoteUrl: string | null;
  platform: Platform;
  defaultBranch: string;
  currentBranch: string | null;
  hasDevelopBranch: boolean;
}

export function exec(command: string, cwd?: string): string {
  try {
    return execSync(command, {
      cwd,
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'pipe'],
    }).trim();
  } catch {
    return '';
  }
}

export function isGitRepo(cwd?: string): boolean {
  const result = exec('git rev-parse --is-inside-work-tree', cwd);
  return result === 'true';
}

export function getRemoteUrl(cwd?: string): string | null {
  const url = exec('git remote get-url origin', cwd);
  return url || null;
}

export function detectPlatform(remoteUrl: string | null): Platform {
  if (!remoteUrl) return 'local-only';
  if (remoteUrl.includes('github.com')) return 'github';
  if (remoteUrl.includes('dev.azure.com') || remoteUrl.includes('visualstudio.com')) return 'azure-devops';
  return 'local-only';
}

export function getDefaultBranch(platform: Platform, cwd?: string): string {
  if (platform === 'github') {
    const result = exec('gh repo view --json defaultBranchRef --jq .defaultBranchRef.name', cwd);
    if (result) return result;
  }

  if (platform === 'azure-devops') {
    const result = exec('az repos show --query defaultBranch -o tsv', cwd);
    if (result) {
      return result.replace('refs/heads/', '');
    }
  }

  // Fallback: check refs
  const headRef = exec('git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null', cwd);
  if (headRef) {
    return headRef.replace('refs/remotes/origin/', '');
  }

  // Last resort
  const branches = exec('git branch -r', cwd);
  if (branches.includes('origin/main')) return 'main';
  if (branches.includes('origin/master')) return 'master';

  return 'main';
}

export function getCurrentBranch(cwd?: string): string | null {
  const branch = exec('git branch --show-current', cwd);
  return branch || null;
}

export function hasBranch(branchName: string, cwd?: string): boolean {
  const result = exec(`git branch --list ${branchName}`, cwd);
  return result.trim().length > 0;
}

export function hasRemoteBranch(branchName: string, cwd?: string): boolean {
  const result = exec(`git branch -r --list origin/${branchName}`, cwd);
  return result.trim().length > 0;
}

export function getGitInfo(cwd?: string): GitInfo {
  if (!isGitRepo(cwd)) {
    return {
      isGitRepo: false,
      remoteUrl: null,
      platform: 'local-only',
      defaultBranch: 'main',
      currentBranch: null,
      hasDevelopBranch: false,
    };
  }

  const remoteUrl = getRemoteUrl(cwd);
  const platform = detectPlatform(remoteUrl);
  const defaultBranch = getDefaultBranch(platform, cwd);
  const currentBranch = getCurrentBranch(cwd);
  const hasDevelop = hasBranch('develop', cwd) || hasRemoteBranch('develop', cwd);

  logger.debug(`Git info: platform=${platform}, default=${defaultBranch}, current=${currentBranch}`);

  return {
    isGitRepo: true,
    remoteUrl,
    platform,
    defaultBranch,
    currentBranch,
    hasDevelopBranch: hasDevelop,
  };
}

export function initGitRepo(cwd?: string): void {
  exec('git init', cwd);
  logger.success('Initialized git repository');
}

export function createBranch(branchName: string, cwd?: string): void {
  exec(`git checkout -b ${branchName}`, cwd);
  logger.success(`Created branch: ${branchName}`);
}
