import { readFile, listMarkdownFiles, fileExists, resolvePath } from '../utils/filesystem.js';
import { logger } from '../utils/logger.js';
import type { Config, Stack } from '../utils/config.js';

export interface AssembledContent {
  standards: string;
  agents: string;
  skills: string;
  security: string;
  testing: string;
  git: string;
}

export interface IntermediateRepresentation {
  config: Config;
  assembled: AssembledContent;
  stackSections: Map<Stack, string>;
  agentSections: Map<string, string>;
  skillSections: Map<string, string>;
}

function resolveContentPath(relativePath: string): string {
  // Try relative to package root (development)
  const devPath = resolvePath(import.meta.dirname ?? '.', '../../', relativePath);
  if (fileExists(devPath)) return devPath;

  // Try relative to dist (installed)
  const distPath = resolvePath(import.meta.dirname ?? '.', '../', relativePath);
  if (fileExists(distPath)) return distPath;

  return devPath;
}

function readContentFile(relativePath: string): string {
  const fullPath = resolveContentPath(relativePath);
  if (!fileExists(fullPath)) {
    logger.debug(`Content file not found: ${fullPath}`);
    return '';
  }
  return readFile(fullPath);
}

function assembleStackStandards(stack: Stack): string {
  const dir = resolveContentPath(`stacks/${stack}`);
  const files = listMarkdownFiles(dir);

  if (files.length === 0) {
    logger.warn(`No standards files found for stack: ${stack}`);
    return '';
  }

  const stackLabels: Record<Stack, string> = {
    'typescript-react': 'TypeScript/React',
    dotnet: '.NET',
    python: 'Python',
    cicd: 'CI/CD',
  };

  const parts: string[] = [`## ${stackLabels[stack]} Standards\n`];

  for (const file of files.sort()) {
    const content = readFile(file);
    parts.push(content);
    parts.push('');
  }

  return parts.join('\n');
}

function assembleBase(): { standards: string; security: string; testing: string; git: string } {
  return {
    standards: readContentFile('stacks/_base/standards.md'),
    security: readContentFile('stacks/_base/security.md'),
    testing: readContentFile('stacks/_base/testing.md'),
    git: readContentFile('stacks/_base/git.md'),
  };
}

function assembleAgents(): Map<string, string> {
  const agents = new Map<string, string>();
  const dir = resolveContentPath('agents');
  const files = listMarkdownFiles(dir);

  for (const file of files) {
    const name = file.split('/').pop()?.replace('.md', '') ?? '';
    if (name === '_base') continue;
    agents.set(name, readFile(file));
  }

  return agents;
}

function assembleSkills(): Map<string, string> {
  const skills = new Map<string, string>();
  const dir = resolveContentPath('skills');

  const categories = ['sdlc', 'git', 'quality', 'learning'];
  for (const category of categories) {
    const catDir = resolvePath(dir, category);
    const files = listMarkdownFiles(catDir);
    for (const file of files) {
      const name = file.split('/').pop()?.replace('.md', '') ?? '';
      skills.set(`${category}/${name}`, readFile(file));
    }
  }

  return skills;
}

export function assemble(config: Config): IntermediateRepresentation {
  logger.step(1, 3, 'Assembling standards...');

  // Base standards
  const base = assembleBase();

  // Stack-specific standards
  const stackSections = new Map<Stack, string>();
  const stackParts: string[] = [];

  for (const stack of config.stacks) {
    const content = assembleStackStandards(stack);
    stackSections.set(stack, content);
    stackParts.push(content);
  }

  // Agents
  logger.step(2, 3, 'Assembling agents and skills...');
  const baseAgent = readContentFile('agents/_base.md');
  const agentSections = assembleAgents();

  let agentsContent = '# Agent Definitions\n\n';
  agentsContent += '## Shared Agent Capabilities\n\n' + baseAgent + '\n\n';
  for (const [_name, content] of agentSections) {
    agentsContent += content + '\n\n';
  }

  // Skills
  const skillSections = assembleSkills();
  let skillsContent = '# Available Skills\n\n';
  for (const [_name, content] of skillSections) {
    skillsContent += content + '\n\n';
  }

  logger.step(3, 3, 'Assembly complete');

  // Combine all standards
  const allStandards = [
    '# Coding Standards\n',
    '## Universal Standards\n',
    base.standards,
    '\n',
    ...stackParts,
  ].join('\n');

  return {
    config,
    assembled: {
      standards: allStandards,
      agents: agentsContent,
      skills: skillsContent,
      security: base.security,
      testing: base.testing,
      git: base.git,
    },
    stackSections,
    agentSections,
    skillSections,
  };
}
