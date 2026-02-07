import { hasBranch, hasRemoteBranch, exec } from '../utils/git.js';
import { logger } from '../utils/logger.js';
import type { BranchConfig } from '../utils/config.js';

export interface BranchSetupResult {
  config: BranchConfig;
  createdBranches: string[];
  warnings: string[];
}

export function setupBranches(defaultBranch: string, autoCreate: boolean): BranchSetupResult {
  logger.step(2, 4, 'Configuring compliance branches...');

  const result: BranchSetupResult = {
    config: {
      defaultBranch,
      developBranch: 'develop',
      protectedBranches: [defaultBranch, 'develop'],
    },
    createdBranches: [],
    warnings: [],
  };

  // Check if develop branch exists
  const hasDevelop = hasBranch('develop') || hasRemoteBranch('develop');

  if (!hasDevelop && autoCreate) {
    // Create develop branch from default
    const currentDefault = exec(`git rev-parse --verify ${defaultBranch} 2>/dev/null`);
    if (currentDefault) {
      exec(`git branch develop ${defaultBranch}`);
      result.createdBranches.push('develop');
      logger.success(`Created 'develop' branch from '${defaultBranch}'`);
    } else {
      result.warnings.push(`Cannot create 'develop' — '${defaultBranch}' branch not found. Create it after first commit.`);
    }
  } else if (!hasDevelop) {
    result.warnings.push("No 'develop' branch found. Consider creating one for the compliance branch workflow.");
  }

  logger.success(`Default branch: ${defaultBranch}`);
  logger.success(`Protected branches: ${result.config.protectedBranches.join(', ')}`);

  return result;
}
