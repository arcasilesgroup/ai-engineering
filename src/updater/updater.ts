import { readFile, readFileOrNull, writeFile, ensureDir, resolvePath, fileExists, listFiles, sha256 } from '../utils/filesystem.js';
import { logger } from '../utils/logger.js';
import { compile } from '../compiler/index.js';
import { install } from '../installer/index.js';
import { classifyFile, parseVersionFile } from './merge-strategy.js';
import type { Config } from '../utils/config.js';

export interface UpdateChange {
  file: string;
  action: 'replace' | 'merge' | 'skip' | 'conflict' | 'recompile';
  hasConflict: boolean;
}

export interface UpdatePlan {
  changes: UpdateChange[];
}

export interface UpdateResult {
  success: boolean;
  updatedFiles: string[];
  mergedFiles: string[];
  conflicts: string[];
  previousVersion: string;
  newVersion: string;
}

export interface RollbackResult {
  success: boolean;
  previousVersion: string;
  error?: string;
}

interface UpdateOptions {
  dryRun: boolean;
  ci?: boolean;
  branch?: string;
}

function backupCurrentFiles(projectRoot: string, _config: Config): void {
  const versionContent = readFileOrNull(resolvePath(projectRoot, '.ai-engineering/.version'));
  const currentVersion = versionContent?.split('\n')[0]?.trim() ?? 'unknown';
  const backupDir = resolvePath(projectRoot, `.ai-engineering/.backup/${currentVersion}`);

  ensureDir(backupDir);

  // Backup all framework files
  const aiEngFiles = listFiles(resolvePath(projectRoot, '.ai-engineering'), true);
  for (const file of aiEngFiles) {
    if (file.includes('/.backup/') || file.includes('/knowledge/')) continue;
    const relativePath = file.replace(projectRoot + '/', '');
    const backupPath = resolvePath(backupDir, relativePath);
    try {
      const content = readFile(file);
      writeFile(backupPath, content);
    } catch {
      // Skip unreadable files
    }
  }

  // Backup IDE files
  const ideFiles = ['CLAUDE.md', '.github/copilot-instructions.md', 'codex.md', 'lefthook.yml', '.gitleaks.toml'];
  for (const file of ideFiles) {
    const fullPath = resolvePath(projectRoot, file);
    if (fileExists(fullPath)) {
      const content = readFile(fullPath);
      writeFile(resolvePath(backupDir, file), content);
    }
  }

  logger.debug(`Backed up to ${backupDir}`);
}

export async function runUpdate(
  projectRoot: string,
  config: Config,
  options: UpdateOptions,
): Promise<UpdateResult & { changes: UpdateChange[] }> {
  const versionContent = readFileOrNull(resolvePath(projectRoot, '.ai-engineering/.version')) ?? '';
  const previousVersion = versionContent.split('\n')[0]?.trim() ?? '0.0.0';
  const checksums = parseVersionFile(versionContent);

  const changes: UpdateChange[] = [];
  const updatedFiles: string[] = [];
  const mergedFiles: string[] = [];
  const conflicts: string[] = [];

  // Plan changes
  const allFiles = listFiles(resolvePath(projectRoot, '.ai-engineering'), true);
  for (const file of allFiles) {
    if (file.includes('/.backup/') || file.includes('/.update-cache')) continue;

    const relativePath = file.replace(projectRoot + '/', '');
    const classification = classifyFile(relativePath);

    switch (classification) {
      case 'user-owned':
        changes.push({ file: relativePath, action: 'skip', hasConflict: false });
        break;

      case 'framework-only':
        changes.push({ file: relativePath, action: 'replace', hasConflict: false });
        break;

      case 'compiled-output':
        changes.push({ file: relativePath, action: 'recompile', hasConflict: false });
        break;

      case 'user-customizable': {
        const currentContent = readFile(file);
        // For now, treat as a simple replacement check
        const originalChecksum = checksums.get(relativePath);
        const currentChecksum = sha256(currentContent);

        if (originalChecksum && currentChecksum === originalChecksum) {
          changes.push({ file: relativePath, action: 'replace', hasConflict: false });
        } else {
          changes.push({ file: relativePath, action: 'merge', hasConflict: false });
        }
        break;
      }
    }
  }

  if (options.dryRun) {
    return {
      success: true,
      changes,
      updatedFiles: changes.filter((c) => c.action === 'replace').map((c) => c.file),
      mergedFiles: changes.filter((c) => c.action === 'merge').map((c) => c.file),
      conflicts: changes.filter((c) => c.hasConflict).map((c) => c.file),
      previousVersion,
      newVersion: config.version,
    };
  }

  // Create backup before modifying
  backupCurrentFiles(projectRoot, config);

  // Re-compile everything (this handles framework-only, compiled-output, and generates new files)
  await compile(projectRoot, config);
  await install(projectRoot, config);

  // Classify results
  for (const change of changes) {
    switch (change.action) {
      case 'replace':
      case 'recompile':
        updatedFiles.push(change.file);
        break;
      case 'merge':
        mergedFiles.push(change.file);
        break;
      case 'conflict':
        conflicts.push(change.file);
        break;
    }
  }

  return {
    success: conflicts.length === 0,
    changes,
    updatedFiles,
    mergedFiles,
    conflicts,
    previousVersion,
    newVersion: config.version,
  };
}

export async function rollbackUpdate(projectRoot: string): Promise<RollbackResult> {
  const backupBase = resolvePath(projectRoot, '.ai-engineering/.backup');
  if (!fileExists(backupBase)) {
    return { success: false, previousVersion: '', error: 'No backup found' };
  }

  // Find the most recent backup
  const backupDirs = listFiles(backupBase, false);
  if (backupDirs.length === 0) {
    return { success: false, previousVersion: '', error: 'No backup versions found' };
  }

  // The backup dir name is the version
  const latestBackupDir = backupDirs.sort().pop();
  if (!latestBackupDir) {
    return { success: false, previousVersion: '', error: 'No backup found' };
  }

  const previousVersion = latestBackupDir.split('/').pop() ?? 'unknown';

  // Restore all files from backup
  const backupFiles = listFiles(latestBackupDir, true);
  for (const backupFile of backupFiles) {
    const relativePath = backupFile.replace(latestBackupDir + '/', '');
    const destPath = resolvePath(projectRoot, relativePath);
    try {
      const content = readFile(backupFile);
      writeFile(destPath, content);
    } catch {
      logger.warn(`Could not restore: ${relativePath}`);
    }
  }

  logger.success(`Restored from backup version ${previousVersion}`);
  return { success: true, previousVersion };
}
