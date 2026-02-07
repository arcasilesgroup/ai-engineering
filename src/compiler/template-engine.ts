import Handlebars from 'handlebars';
import { readFile, fileExists } from '../utils/filesystem.js';
import { logger } from '../utils/logger.js';
import { resolvePath } from '../utils/filesystem.js';

let initialized = false;

function initHelpers(): void {
  if (initialized) return;

  Handlebars.registerHelper('ifEquals', function (this: unknown, a: unknown, b: unknown, options: Handlebars.HelperOptions) {
    return a === b ? options.fn(this) : options.inverse(this);
  });

  Handlebars.registerHelper('ifIncludes', function (this: unknown, arr: unknown[], value: unknown, options: Handlebars.HelperOptions) {
    if (Array.isArray(arr) && arr.includes(value)) {
      return options.fn(this);
    }
    return options.inverse(this);
  });

  Handlebars.registerHelper('join', function (arr: unknown[], separator: string) {
    if (Array.isArray(arr)) {
      return arr.join(typeof separator === 'string' ? separator : ', ');
    }
    return '';
  });

  Handlebars.registerHelper('uppercase', function (str: string) {
    return typeof str === 'string' ? str.toUpperCase() : '';
  });

  Handlebars.registerHelper('lowercase', function (str: string) {
    return typeof str === 'string' ? str.toLowerCase() : '';
  });

  Handlebars.registerHelper('capitalize', function (str: string) {
    if (typeof str !== 'string' || str.length === 0) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
  });

  Handlebars.registerHelper('stackLabel', function (stack: string) {
    const labels: Record<string, string> = {
      'typescript-react': 'TypeScript/React',
      dotnet: '.NET',
      python: 'Python',
      cicd: 'CI/CD',
    };
    return labels[stack] ?? stack;
  });

  Handlebars.registerHelper('ideLabel', function (ide: string) {
    const labels: Record<string, string> = {
      'claude-code': 'Claude Code',
      copilot: 'GitHub Copilot',
      codex: 'Codex',
    };
    return labels[ide] ?? ide;
  });

  Handlebars.registerHelper('timestamp', function () {
    return new Date().toISOString().split('T')[0];
  });

  Handlebars.registerHelper('each-with-index', function (this: unknown, context: unknown[], options: Handlebars.HelperOptions) {
    let result = '';
    if (Array.isArray(context)) {
      context.forEach((item, index) => {
        const itemObj = typeof item === 'object' && item !== null ? item : {};
        result += options.fn(Object.assign({}, itemObj, { '@index': index, '@first': index === 0, '@last': index === context.length - 1 }));
      });
    }
    return result;
  });

  initialized = true;
}

export function compileTemplate(templateContent: string, data: Record<string, unknown>): string {
  initHelpers();
  const template = Handlebars.compile(templateContent, { noEscape: true });
  return template(data);
}

export function compileTemplateFile(templatePath: string, data: Record<string, unknown>): string {
  if (!fileExists(templatePath)) {
    throw new Error(`Template not found: ${templatePath}`);
  }
  const content = readFile(templatePath);
  return compileTemplate(content, data);
}

export function resolveTemplatePath(templateName: string): string {
  // Try relative to package root (development)
  const devPath = resolvePath(import.meta.dirname ?? '.', '../../templates', templateName);
  if (fileExists(devPath)) return devPath;

  // Try relative to dist (installed)
  const distPath = resolvePath(import.meta.dirname ?? '.', '../templates', templateName);
  if (fileExists(distPath)) return distPath;

  logger.debug(`Template paths tried: ${devPath}, ${distPath}`);
  throw new Error(`Template not found: ${templateName}`);
}
