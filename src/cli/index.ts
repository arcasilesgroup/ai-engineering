import { Command } from 'commander';
import { initCommand } from './commands/init.js';
import { updateCommand } from './commands/update.js';

const program = new Command();

program
  .name('ai-engineering')
  .description('AI coding assistant framework with executable enforcement: prompts + runtime hooks + verification gates')
  .version('0.1.0-beta.1');

program
  .command('init')
  .description('Initialize ai-engineering in your project')
  .option('-s, --stack <stacks...>', 'Technology stacks (typescript-react, dotnet, python, cicd)')
  .option('-i, --ide <ides...>', 'IDE targets (claude-code, copilot, codex)')
  .option('-l, --level <level>', 'Enforcement level (basic, standard, strict)', 'standard')
  .option('-y, --yes', 'Skip interactive prompts, use defaults + flags')
  .option('-v, --verbose', 'Verbose output')
  .action(initCommand);

program
  .command('update')
  .description('Update ai-engineering to the latest version')
  .option('--dry-run', 'Show what would change without modifying anything')
  .option('--rollback', 'Restore the previous version from backup')
  .option('--ci', 'CI mode — create update branch instead of modifying in place')
  .option('--branch <name>', 'Branch name for CI mode', 'update/ai-engineering')
  .option('-v, --verbose', 'Verbose output')
  .action(updateCommand);

program.parse();
