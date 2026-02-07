import * as p from '@clack/prompts';
import { setVerbose, logger } from '../../utils/logger.js';
import { loadConfig } from '../../utils/config.js';
import { fileExists, resolvePath } from '../../utils/filesystem.js';
import { checkForUpdates } from '../../updater/version-check.js';
import { runUpdate, rollbackUpdate } from '../../updater/updater.js';

interface UpdateOptions {
  dryRun?: boolean;
  rollback?: boolean;
  ci?: boolean;
  branch?: string;
  verbose?: boolean;
}

export async function updateCommand(options: UpdateOptions): Promise<void> {
  if (options.verbose) setVerbose(true);

  const projectRoot = process.cwd();
  const configPath = resolvePath(projectRoot, '.ai-engineering/config.yml');

  if (!fileExists(configPath)) {
    logger.error('ai-engineering is not initialized in this project.');
    logger.info("Run 'npx ai-engineering init' first.");
    process.exit(1);
  }

  p.intro('ai-engineering — Update');

  // Handle rollback
  if (options.rollback) {
    logger.header('Rolling back to previous version...');
    const result = await rollbackUpdate(projectRoot);
    if (result.success) {
      logger.success(`Rolled back to version ${result.previousVersion}`);
    } else {
      logger.error(`Rollback failed: ${result.error}`);
    }
    p.outro('Done.');
    return;
  }

  // Check for updates
  const config = loadConfig(projectRoot);
  logger.step(1, 3, 'Checking for updates...');

  const updateInfo = await checkForUpdates(projectRoot);
  if (!updateInfo.updateAvailable) {
    logger.success(`Already on the latest version (${updateInfo.currentVersion})`);
    p.outro('No update needed.');
    return;
  }

  logger.info(`Current: ${updateInfo.currentVersion} → Latest: ${updateInfo.latestVersion}`);

  if (updateInfo.changelog) {
    logger.blank();
    logger.info('Changelog:');
    console.log(updateInfo.changelog);
  }

  // Dry run
  if (options.dryRun) {
    logger.blank();
    logger.header('Dry Run — What would change:');
    const plan = await runUpdate(projectRoot, config, { dryRun: true });
    for (const change of plan.changes) {
      const icon = change.action === 'replace' ? '↻' : change.action === 'merge' ? '⊕' : '?';
      logger.info(`  ${icon} ${change.file} (${change.action}${change.hasConflict ? ' — CONFLICT' : ''})`);
    }
    p.outro('Dry run complete. No files were modified.');
    return;
  }

  // Run update
  logger.step(2, 3, 'Applying updates...');
  const result = await runUpdate(projectRoot, config, {
    dryRun: false,
    ci: options.ci,
    branch: options.branch,
  });

  logger.step(3, 3, 'Update summary');
  logger.success(`Updated: ${result.updatedFiles.length} files`);
  if (result.mergedFiles.length > 0) {
    logger.info(`Merged: ${result.mergedFiles.length} files`);
  }
  if (result.conflicts.length > 0) {
    logger.warn(`Conflicts: ${result.conflicts.length} files need manual resolution`);
    logger.list(result.conflicts);
  }

  p.outro('Update complete!');
}
