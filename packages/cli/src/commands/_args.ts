/**
 * _args — minimal flag/positional parser shared by Phase 4.1 commands.
 *
 * Why hand-rolled: the CLI commands are small and want zero runtime deps.
 * `node:util.parseArgs` is close but its strict mode rejects unknown options
 * (problematic for forwarded subcommand flags), and its `tokens` mode does
 * not match the ergonomics of `--key value` / `--flag` we need.
 *
 * Behavior:
 *   - `--key value` and `--key=value` both bind value to key.
 *   - `--flag` (no following value or value starts with `--`) is a boolean flag.
 *   - `-s`/`--short` get no special treatment; whatever the caller asks for,
 *     it gets back. Anything not a flag is a positional.
 */
export interface ParsedArgs {
  readonly flags: Readonly<Record<string, string | true>>;
  readonly positional: ReadonlyArray<string>;
}

export const parseArgs = (argv: ReadonlyArray<string>): ParsedArgs => {
  const flags: Record<string, string | true> = {};
  const positional: string[] = [];
  for (let i = 0; i < argv.length; i += 1) {
    const tok = argv[i];
    if (tok === undefined) continue;
    if (tok.startsWith("--")) {
      const eq = tok.indexOf("=");
      if (eq !== -1) {
        const key = tok.slice(2, eq);
        flags[key] = tok.slice(eq + 1);
        continue;
      }
      const key = tok.slice(2);
      const next = argv[i + 1];
      if (next === undefined || next.startsWith("--")) {
        flags[key] = true;
      } else {
        flags[key] = next;
        i += 1;
      }
    } else {
      positional.push(tok);
    }
  }
  return Object.freeze({
    flags: Object.freeze(flags),
    positional: Object.freeze(positional),
  });
};

/**
 * Convenience for boolean detection: `--json` is true regardless of whether
 * the user passed it as `--json` or `--json true`.
 */
export const hasFlag = (args: ParsedArgs, key: string): boolean => args.flags[key] !== undefined;

export const stringFlag = (args: ParsedArgs, key: string): string | undefined => {
  const v = args.flags[key];
  return typeof v === "string" ? v : undefined;
};
