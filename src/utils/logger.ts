import chalk from 'chalk';

export type LogLevel = 'debug' | 'info' | 'warn' | 'error' | 'success';

let verbose = false;

export function setVerbose(enabled: boolean): void {
  verbose = enabled;
}

export function isVerbose(): boolean {
  return verbose;
}

export const logger = {
  debug(message: string, ...args: unknown[]): void {
    if (verbose) {
      console.log(chalk.gray(`  [debug] ${message}`), ...args);
    }
  },

  info(message: string, ...args: unknown[]): void {
    console.log(chalk.blue('  ℹ'), message, ...args);
  },

  success(message: string, ...args: unknown[]): void {
    console.log(chalk.green('  ✓'), message, ...args);
  },

  warn(message: string, ...args: unknown[]): void {
    console.log(chalk.yellow('  ⚠'), message, ...args);
  },

  error(message: string, ...args: unknown[]): void {
    console.error(chalk.red('  ✗'), message, ...args);
  },

  step(stepNumber: number, total: number, message: string): void {
    console.log(chalk.cyan(`  [${stepNumber}/${total}]`), message);
  },

  header(message: string): void {
    console.log();
    console.log(chalk.bold.underline(message));
    console.log();
  },

  divider(): void {
    console.log(chalk.gray('  ─'.repeat(30)));
  },

  list(items: string[]): void {
    for (const item of items) {
      console.log(chalk.gray('    •'), item);
    }
  },

  blank(): void {
    console.log();
  },
};
