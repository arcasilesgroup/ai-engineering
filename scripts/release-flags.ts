// The version decides the release flags. `2.0.0-rc.1` is a prerelease and never
// claims Latest; `2.0.0` does. A human picking between the two by hand is the
// decision that always comes out the same — and the tag is derived the same way, so
// the release cannot be published under a name the version does not have.
//
// Usage: bun scripts/release-flags.ts 2.0.0-rc.1   → tag=v2.0.0-rc.1 / prerelease=true
export function releaseFlags(version: string): { tag: string; prerelease: boolean } {
  const clean = version.trim().replace(/^v/, "");
  if (!/^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$/.test(clean)) {
    throw new Error(`not a release version (semver X.Y.Z or X.Y.Z-suffix expected): ${version}`);
  }
  return { tag: `v${clean}`, prerelease: clean.includes("-") };
}

if (import.meta.main) {
  const version = process.argv[2] ?? "";
  try {
    const { tag, prerelease } = releaseFlags(version);
    process.stdout.write(`tag=${tag}\nprerelease=${prerelease}\n`);
  } catch (error) {
    process.stderr.write(`release-flags: ${error instanceof Error ? error.message : String(error)}\n`);
    process.exit(2);
  }
}
