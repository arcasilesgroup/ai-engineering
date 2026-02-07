import * as p from '@clack/prompts';
import type { EnforcementLevel } from '../../utils/config.js';

const LEVEL_OPTIONS: { value: EnforcementLevel; label: string; hint: string }[] = [
  {
    value: 'basic',
    label: 'Basic',
    hint: 'Prompt enforcement only — standards in IDE config files',
  },
  {
    value: 'standard',
    label: 'Standard',
    hint: 'Prompts + git hooks (gitleaks, lint, format, conventional commits)',
  },
  {
    value: 'strict',
    label: 'Strict',
    hint: 'All layers — prompts + runtime hooks + git hooks + CI/CD quality gates',
  },
];

export async function promptLevelSelect(): Promise<EnforcementLevel> {
  const result = await p.select({
    message: 'What enforcement level do you want?',
    options: LEVEL_OPTIONS.map((opt) => ({
      value: opt.value,
      label: opt.label,
      hint: opt.hint,
    })),
    initialValue: 'standard' as EnforcementLevel,
  });

  if (p.isCancel(result)) {
    p.cancel('Setup cancelled.');
    process.exit(0);
  }

  return result as EnforcementLevel;
}
