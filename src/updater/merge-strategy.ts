import { sha256 } from '../utils/filesystem.js';

export type FileClassification = 'framework-only' | 'compiled-output' | 'user-customizable' | 'user-owned';

export interface MergeResult {
  file: string;
  action: 'replace' | 'merge' | 'skip' | 'conflict';
  hasConflict: boolean;
  content: string | null;
}

/**
 * Classify a file to determine its update strategy.
 */
export function classifyFile(relativePath: string): FileClassification {
  // User-owned: never touched by updates
  if (
    relativePath.startsWith('.ai-engineering/knowledge/') ||
    relativePath.includes('/decisions/')
  ) {
    return 'user-owned';
  }

  // Framework-only: safe to auto-replace
  if (
    relativePath.startsWith('.ai-engineering/hooks/') ||
    relativePath === '.ai-engineering/.version'
  ) {
    return 'framework-only';
  }

  // Compiled output: re-compile from updated standards
  if (
    relativePath === 'CLAUDE.md' ||
    relativePath === '.github/copilot-instructions.md' ||
    relativePath === 'codex.md' ||
    relativePath.startsWith('.claude/commands/') ||
    relativePath.startsWith('.ai-engineering/standards/')
  ) {
    return 'compiled-output';
  }

  // User-customizable: 3-way merge
  if (
    relativePath === '.ai-engineering/config.yml' ||
    relativePath === '.ai-engineering/hooks/blocklist.sh' ||
    relativePath === 'lefthook.yml' ||
    relativePath === '.gitleaks.toml' ||
    relativePath === '.claude/settings.json'
  ) {
    return 'user-customizable';
  }

  return 'framework-only';
}

/**
 * Parse the version file to get original checksums.
 */
export function parseVersionFile(versionContent: string): Map<string, string> {
  const checksums = new Map<string, string>();
  const lines = versionContent.trim().split('\n');

  // First line is version, rest are path:checksum
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i];
    if (!line) continue;
    const colonIdx = line.lastIndexOf(':');
    if (colonIdx === -1) continue;
    const path = line.substring(0, colonIdx);
    const checksum = line.substring(colonIdx + 1);
    checksums.set(path, checksum);
  }

  return checksums;
}

/**
 * Perform 3-way merge for user-customizable files.
 *
 * Compare:
 * 1. Original installed version (from checksum comparison)
 * 2. Current file (may have user changes)
 * 3. New version from framework update
 *
 * If file unchanged from original → safe replace with new.
 * If file was customized → attempt line-by-line merge.
 */
export function threeWayMerge(
  originalChecksum: string | undefined,
  currentContent: string,
  newContent: string,
): MergeResult {
  const currentChecksum = sha256(currentContent);

  // If current matches original → user didn't customize, safe to replace
  if (originalChecksum && currentChecksum === originalChecksum) {
    return {
      file: '',
      action: 'replace',
      hasConflict: false,
      content: newContent,
    };
  }

  // If current matches new → already up to date
  const newChecksum = sha256(newContent);
  if (currentChecksum === newChecksum) {
    return {
      file: '',
      action: 'skip',
      hasConflict: false,
      content: null,
    };
  }

  // User customized the file — attempt merge
  // Simple strategy: if the new content is a superset of changes,
  // try to apply. Otherwise, flag as conflict.
  const merged = attemptSimpleMerge(currentContent, newContent);
  if (merged) {
    return {
      file: '',
      action: 'merge',
      hasConflict: false,
      content: merged,
    };
  }

  // Can't auto-merge — conflict
  return {
    file: '',
    action: 'conflict',
    hasConflict: true,
    content: generateConflictMarkers(currentContent, newContent),
  };
}

/**
 * Simple merge: if the files differ only in additive sections,
 * combine them. Otherwise return null to indicate conflict.
 */
function attemptSimpleMerge(current: string, incoming: string): string | null {
  const currentLines = current.split('\n');
  const incomingLines = incoming.split('\n');

  // If incoming is identical to current, nothing to merge
  if (current === incoming) return current;

  // Simple heuristic: if current is a subset of incoming (incoming has more lines
  // and starts/ends similarly), we can take the incoming version
  if (incomingLines.length > currentLines.length) {
    const currentStart = currentLines.slice(0, 5).join('\n');
    const incomingStart = incomingLines.slice(0, 5).join('\n');

    if (currentStart === incomingStart) {
      // Same start, incoming has additions → take incoming
      return incoming;
    }
  }

  // Cannot auto-merge
  return null;
}

function generateConflictMarkers(current: string, incoming: string): string {
  return [
    '<<<<<<< CURRENT (your customizations)',
    current,
    '=======',
    incoming,
    '>>>>>>> INCOMING (framework update)',
  ].join('\n');
}
