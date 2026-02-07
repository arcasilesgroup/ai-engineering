import * as p from '@clack/prompts';
import type { IDE } from '../../utils/config.js';

const IDE_OPTIONS: { value: IDE; label: string; hint: string }[] = [
  { value: 'claude-code', label: 'Claude Code', hint: 'CLAUDE.md + commands + hooks (full enforcement)' },
  { value: 'copilot', label: 'GitHub Copilot', hint: 'copilot-instructions.md + git hooks' },
  { value: 'codex', label: 'Codex', hint: 'codex.md + git hooks' },
];

export async function promptIDESelect(detected: IDE[]): Promise<IDE[]> {
  const result = await p.multiselect({
    message: 'Which AI coding assistants do you use?',
    options: IDE_OPTIONS.map((opt) => ({
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

  return result as IDE[];
}
