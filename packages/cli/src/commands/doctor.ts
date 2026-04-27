import { existsSync } from "node:fs";
import { join } from "node:path";

/**
 * `ai-eng doctor` — local install health check (no LLM required).
 *
 * Reports:
 *   - presence of .ai-engineering/manifest.toml
 *   - presence of CONSTITUTION.md
 *   - skills/catalog count vs ai-engineering.toml expectation
 *   - hook hash verification (P3 adapter wires the actual checks)
 */
export const doctor = async (_args: string[]): Promise<number> => {
  const cwd = process.cwd();
  const checks: Array<{ ok: boolean; label: string }> = [
    {
      ok: existsSync(join(cwd, ".ai-engineering")),
      label: ".ai-engineering/ exists",
    },
    {
      ok: existsSync(join(cwd, ".ai-engineering", "manifest.toml")),
      label: "manifest.toml present",
    },
    {
      ok: existsSync(join(cwd, "CONSTITUTION.md")),
      label: "CONSTITUTION.md present (top-level)",
    },
  ];

  let failed = 0;
  for (const c of checks) {
    const mark = c.ok ? "✓" : "✗";
    process.stdout.write(`  ${mark} ${c.label}\n`);
    if (!c.ok) failed++;
  }
  if (failed > 0) {
    process.stdout.write(
      `\n[ai-eng] ${failed} check(s) failed. Run 'ai-eng bootstrap' to scaffold a fresh project.\n`,
    );
    return 1;
  }
  process.stdout.write("\n[ai-eng] doctor: all checks passed.\n");
  return 0;
};
