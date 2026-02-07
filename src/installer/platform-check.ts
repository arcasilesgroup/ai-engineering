import { exec } from '../utils/git.js';
import { logger } from '../utils/logger.js';
import type { EnforcementLevel, Platform, Stack } from '../utils/config.js';

export interface ToolRequirement {
  name: string;
  purpose: string;
  detectionCommand: string;
  installCommand: string;
  installUrl: string;
  requiredFor: string;
}

export interface ToolInfo {
  name: string;
  version: string;
  available: boolean;
}

export interface PlatformCheckResult {
  platform: Platform;
  defaultBranch: string;
  missingTools: ToolRequirement[];
  installedTools: ToolInfo[];
  warnings: string[];
}

function checkTool(name: string, command: string): ToolInfo {
  const version = exec(command);
  return {
    name,
    version: version || 'not found',
    available: version.length > 0,
  };
}

function getRequiredTools(stacks: Stack[], level: EnforcementLevel, platform: Platform): ToolRequirement[] {
  const tools: ToolRequirement[] = [
    {
      name: 'git',
      purpose: 'Version control',
      detectionCommand: 'git --version',
      installCommand: '',
      installUrl: 'https://git-scm.com/downloads',
      requiredFor: 'All levels',
    },
  ];

  if (platform === 'github') {
    tools.push({
      name: 'gh',
      purpose: 'GitHub CLI',
      detectionCommand: 'gh --version',
      installCommand: 'brew install gh',
      installUrl: 'https://cli.github.com/',
      requiredFor: 'GitHub platform',
    });
  }

  if (platform === 'azure-devops') {
    tools.push({
      name: 'az',
      purpose: 'Azure CLI',
      detectionCommand: 'az --version',
      installCommand: 'brew install azure-cli',
      installUrl: 'https://docs.microsoft.com/en-us/cli/azure/install-azure-cli',
      requiredFor: 'Azure DevOps platform',
    });
  }

  if (level === 'standard' || level === 'strict') {
    tools.push(
      {
        name: 'gitleaks',
        purpose: 'Secret scanning',
        detectionCommand: 'gitleaks version',
        installCommand: 'brew install gitleaks',
        installUrl: 'https://github.com/gitleaks/gitleaks',
        requiredFor: 'Standard + Strict levels',
      },
      {
        name: 'lefthook',
        purpose: 'Git hooks',
        detectionCommand: 'lefthook version',
        installCommand: 'npm i -D @evilmartians/lefthook',
        installUrl: 'https://github.com/evilmartians/lefthook',
        requiredFor: 'Standard + Strict levels',
      },
    );
  }

  if (stacks.includes('python')) {
    tools.push({
      name: 'pip-audit',
      purpose: 'Python dependency audit',
      detectionCommand: 'pip-audit --version',
      installCommand: 'pip install pip-audit',
      installUrl: 'https://github.com/pypa/pip-audit',
      requiredFor: 'Python stack',
    });
  }

  if (stacks.includes('dotnet')) {
    tools.push({
      name: 'dotnet',
      purpose: '.NET CLI',
      detectionCommand: 'dotnet --version',
      installCommand: '',
      installUrl: 'https://dotnet.microsoft.com/download',
      requiredFor: '.NET stack',
    });
  }

  return tools;
}

export function runPlatformCheck(
  stacks: Stack[],
  level: EnforcementLevel,
  platform: Platform,
): PlatformCheckResult {
  logger.step(1, 4, 'Checking platform dependencies...');

  const requiredTools = getRequiredTools(stacks, level, platform);
  const results: ToolInfo[] = [];
  const missing: ToolRequirement[] = [];
  const warnings: string[] = [];

  for (const tool of requiredTools) {
    const info = checkTool(tool.name, tool.detectionCommand);
    results.push(info);

    if (!info.available) {
      missing.push(tool);
    }
  }

  // Report results
  for (const tool of results) {
    if (tool.available) {
      logger.success(`${tool.name}: ${tool.version}`);
    } else {
      logger.warn(`${tool.name}: not found`);
    }
  }

  if (missing.length > 0) {
    logger.blank();
    logger.warn('Missing tools:');
    for (const tool of missing) {
      const installHint = tool.installCommand
        ? `Install: ${tool.installCommand}`
        : `Download: ${tool.installUrl}`;
      logger.info(`  ${tool.name} (${tool.purpose}) — ${installHint}`);
    }
    warnings.push(`${missing.length} tool(s) not found. Some features may not work.`);
  }

  // Detect default branch
  let defaultBranch = 'main';
  if (platform === 'github') {
    const detected = exec('gh repo view --json defaultBranchRef --jq .defaultBranchRef.name');
    if (detected) defaultBranch = detected;
  }

  return {
    platform,
    defaultBranch,
    missingTools: missing,
    installedTools: results,
    warnings,
  };
}
