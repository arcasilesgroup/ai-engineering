import * as p from '@clack/prompts';
import type { Stack } from '../../utils/config.js';

const STACK_OPTIONS: { value: Stack; label: string; hint: string }[] = [
  { value: 'typescript-react', label: 'TypeScript / React', hint: 'TS strict, React patterns, Vitest + RTL' },
  { value: 'dotnet', label: '.NET', hint: 'C#, ASP.NET Core, EF Core, Clean Architecture' },
  { value: 'python', label: 'Python', hint: 'Typing, async, FastAPI/Django, pytest' },
  { value: 'cicd', label: 'CI/CD', hint: 'GitHub Actions + Azure Pipelines' },
];

export async function promptStackSelect(detected: Stack[]): Promise<Stack[]> {
  const result = await p.multiselect({
    message: 'Which technology stacks does this project use?',
    options: STACK_OPTIONS.map((opt) => ({
      value: opt.value,
      label: opt.label,
      hint: opt.hint,
      initialValue: detected.includes(opt.value),
    })),
    required: true,
  });

  if (p.isCancel(result)) {
    p.cancel('Setup cancelled.');
    process.exit(0);
  }

  return result as Stack[];
}
