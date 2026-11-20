// Builds the chain bundle the in-process plugin hosts (Oh My Pi, Pi, OpenCode) import:
// src/chain plus a host-safe chain() wrapper as ONE self-contained module. A re-export
// of src/ would not do: its relative imports die in a foreign repo.
//
// The bundle is a build artifact, never committed. It is rebuilt by every compile
// (scripts/build.ts), by every `bun test` (tests/preload.ts) and by `npm pack`
// (the prepack script), so it cannot drift from src/chain. Run by hand:
//   bun scripts/chain-bundle.ts
import { spawnSync } from "node:child_process";
import { join } from "node:path";

const root = join(import.meta.dir, "..");

/** Where the bundle lands, relative to the repository root. The same relative path is
 *  where src/embed.ts reads it, from the checkout or from inside the compiled binary. */
export const CHAIN_BUNDLE_PATH = join("generated", "chain", "ai-eng-chain.ts");

export function buildChainBundle(): void {
  const built = spawnSync(
    process.execPath,
    ["build", join(root, "scripts", "chain-entry.ts"), "--target=bun", "--format=esm", `--outfile=${join(root, CHAIN_BUNDLE_PATH)}`],
    { cwd: root, stdio: ["ignore", "ignore", "inherit"] },
  );
  if (built.status !== 0) throw new Error(`chain bundle build failed (exit ${String(built.status)})`);
}

// Silent on success: as the prepack script its stdout lands inside `npm pack --json`,
// which the release job parses.
if (import.meta.main) buildChainBundle();
