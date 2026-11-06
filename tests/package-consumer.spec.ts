import { expect, test } from "bun:test";
import {
  packageConsumerFailures,
  runPackageConsumerSmoke,
} from "../scripts/package-consumer-smoke.ts";

test(
  "the packed tarball installs and runs from isolated npm and Bun consumers",
  async () => {
    const result = await runPackageConsumerSmoke();
    const failures = packageConsumerFailures(result);

    expect(result.npmInstall.status).toBe(0);
    expect(result.bunInstall.status).toBe(0);
    expect(result.packedFiles).toContain("bin/ai-eng.js");
    expect(result.packedFiles).toContain("src/cli.ts");
    expect(result.packedFiles).toContain("src/version.ts");
    expect(result.packedFiles).not.toContain("scripts/build.ts");
    expect(result.npmInstalledFiles).toEqual(result.packedFiles);
    expect(result.bunInstalledFiles).toEqual(result.packedFiles);
    expect(result.npmCommand).toEqual({
      status: 0,
      stdout: `ai-eng ${result.version}\n`,
      stderr: "",
      errorCode: null,
    });
    expect(result.nodeProbe.status).not.toBe(0);
    expect(result.bunOnlyCommand).toEqual({
      status: 0,
      stdout: `ai-eng ${result.version}\n`,
      stderr: "",
      errorCode: null,
    });
    expect(result.runtimeDependencies).not.toContain("smol-toml");
    expect(result.tarballHashAfter).toBe(result.tarballHashBefore);
    expect(failures).toEqual([]);
  },
  { timeout: 180_000 },
);
