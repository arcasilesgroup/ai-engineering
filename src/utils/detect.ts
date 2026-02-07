import { readdirSync } from 'node:fs';
import { fileExists, resolvePath } from './filesystem.js';
import { logger } from './logger.js';
import type { Stack, IDE } from './config.js';

interface DetectionResult {
  stacks: Stack[];
  ides: IDE[];
}

export function autoDetect(projectRoot: string): DetectionResult {
  const stacks = detectStacks(projectRoot);
  const ides = detectIDEs(projectRoot);

  logger.debug(`Auto-detected stacks: ${stacks.join(', ') || 'none'}`);
  logger.debug(`Auto-detected IDEs: ${ides.join(', ') || 'none'}`);

  return { stacks, ides };
}

export function detectStacks(projectRoot: string): Stack[] {
  const stacks: Stack[] = [];

  // TypeScript/React detection
  if (
    fileExists(resolvePath(projectRoot, 'package.json')) ||
    fileExists(resolvePath(projectRoot, 'tsconfig.json'))
  ) {
    stacks.push('typescript-react');
  }

  // .NET detection
  if (
    hasFileWithExtension(projectRoot, '.csproj') ||
    hasFileWithExtension(projectRoot, '.sln') ||
    fileExists(resolvePath(projectRoot, 'global.json'))
  ) {
    stacks.push('dotnet');
  }

  // Python detection
  if (
    fileExists(resolvePath(projectRoot, 'pyproject.toml')) ||
    fileExists(resolvePath(projectRoot, 'setup.py')) ||
    fileExists(resolvePath(projectRoot, 'requirements.txt')) ||
    fileExists(resolvePath(projectRoot, 'Pipfile'))
  ) {
    stacks.push('python');
  }

  // CICD detection
  if (
    fileExists(resolvePath(projectRoot, '.github/workflows')) ||
    fileExists(resolvePath(projectRoot, 'azure-pipelines.yml')) ||
    fileExists(resolvePath(projectRoot, '.azure-pipelines'))
  ) {
    stacks.push('cicd');
  }

  return stacks;
}

export function detectIDEs(projectRoot: string): IDE[] {
  const ides: IDE[] = [];

  // Claude Code detection
  if (
    fileExists(resolvePath(projectRoot, 'CLAUDE.md')) ||
    fileExists(resolvePath(projectRoot, '.claude'))
  ) {
    ides.push('claude-code');
  }

  // Copilot detection
  if (fileExists(resolvePath(projectRoot, '.github/copilot-instructions.md'))) {
    ides.push('copilot');
  }

  // Codex detection
  if (fileExists(resolvePath(projectRoot, 'codex.md'))) {
    ides.push('codex');
  }

  return ides;
}

function hasFileWithExtension(dir: string, ext: string): boolean {
  try {
    const entries = readdirSync(dir, { withFileTypes: true });
    return entries.some((e) => e.isFile() && e.name.endsWith(ext));
  } catch {
    return false;
  }
}
