// Test-command detector → input rewrite. The only primitiva universal: rewrite the
// command BEFORE it runs, then let the deterministic filter print only failures (§15).

const RUNNERS = /\b(vitest|jest|playwright|turbo\s+run\s+test|bun\s+test|npm\s+test|npm\s+run\s+test|yarn\s+test|pnpm\s+test|pytest|go\s+test|cargo\s+test)\b/;
const SKIPS = /(--watch|--ui|--help|-h\b|--list|--reporter|&\s*$|\|\s*[^|]*$|\bgrep\b|\btail\b|\bhead\b)/;

export type WrapDecision = { wrap: true; runner: string } | { wrap: false };

export function isTestCommand(command: string): WrapDecision {
  if (SKIPS.test(command)) return { wrap: false };
  const found = RUNNERS.exec(command);
  if (!found) return { wrap: false };
  return { wrap: true, runner: found[1] ?? "test" };
}

/** The rewritten command the surface executes instead of the original. */
export function rewrite(command: string): string {
  return `ai-eng wrap test -- ${command}`;
}
