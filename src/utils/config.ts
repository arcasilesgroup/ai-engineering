import yaml from 'js-yaml';
import Ajv from 'ajv';
import { readFile, readFileOrNull, writeFile, fileExists } from './filesystem.js';
import { logger } from './logger.js';
import { resolvePath } from './filesystem.js';

export type Stack = 'typescript-react' | 'dotnet' | 'python' | 'cicd';
export type IDE = 'claude-code' | 'copilot' | 'codex';
export type EnforcementLevel = 'basic' | 'standard' | 'strict';
export type Platform = 'github' | 'azure-devops' | 'local-only';

export interface BranchConfig {
  defaultBranch: string;
  developBranch: string;
  protectedBranches: string[];
}

export interface Config {
  version: string;
  stacks: Stack[];
  ides: IDE[];
  level: EnforcementLevel;
  platform: Platform;
  branches: BranchConfig;
  customizations?: {
    blocklist?: string[];
    allowlist?: string[];
    excludePaths?: string[];
  };
}

const CONFIG_FILE = '.ai-engineering/config.yml';
const SCHEMA_PATH = 'schemas/config.schema.json';

export function getConfigPath(projectRoot: string): string {
  return resolvePath(projectRoot, CONFIG_FILE);
}

export function loadConfig(projectRoot: string): Config {
  const configPath = getConfigPath(projectRoot);
  if (!fileExists(configPath)) {
    throw new Error(`Config not found at ${configPath}. Run 'npx ai-engineering init' first.`);
  }

  const raw = readFile(configPath);
  const parsed = yaml.load(raw) as Config;
  validateConfig(parsed);
  return parsed;
}

export function loadConfigOrNull(projectRoot: string): Config | null {
  try {
    return loadConfig(projectRoot);
  } catch {
    return null;
  }
}

export function saveConfig(projectRoot: string, config: Config): void {
  const configPath = getConfigPath(projectRoot);
  const content = yaml.dump(config, {
    indent: 2,
    lineWidth: 120,
    noRefs: true,
    sortKeys: false,
  });
  writeFile(configPath, content);
  logger.debug(`Saved config to ${configPath}`);
}

export function validateConfig(config: unknown): asserts config is Config {
  const ajv = new Ajv({ allErrors: true });

  const schema = loadSchema();
  const validate = ajv.compile(schema);

  if (!validate(config)) {
    const errors = validate.errors?.map((e) => `  ${e.instancePath} ${e.message}`).join('\n') ?? 'Unknown validation error';
    throw new Error(`Invalid configuration:\n${errors}`);
  }
}

function loadSchema(): Record<string, unknown> {
  const schemaPath = resolveSchemaPath();
  const content = readFileOrNull(schemaPath);
  if (!content) {
    logger.warn('Config schema not found, skipping validation');
    return { type: 'object' };
  }
  return JSON.parse(content) as Record<string, unknown>;
}

function resolveSchemaPath(): string {
  // Try relative to package root (development)
  const devPath = resolvePath(import.meta.dirname ?? '.', '../../', SCHEMA_PATH);
  if (fileExists(devPath)) return devPath;

  // Try relative to dist (installed)
  const distPath = resolvePath(import.meta.dirname ?? '.', '../', SCHEMA_PATH);
  if (fileExists(distPath)) return distPath;

  return devPath;
}

export function createDefaultConfig(overrides: Partial<Config> = {}): Config {
  return {
    version: '0.1.0',
    stacks: ['typescript-react'],
    ides: ['claude-code'],
    level: 'standard',
    platform: 'github',
    branches: {
      defaultBranch: 'main',
      developBranch: 'develop',
      protectedBranches: ['main', 'develop'],
    },
    ...overrides,
  };
}
