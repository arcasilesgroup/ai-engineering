import { afterEach, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  packageConsumerFailures,
  runPackageConsumerSmoke,
  tarballDigestRefusal,
} from "../scripts/package-consumer-smoke.ts";

const SMOKE_SCRIPT = join(import.meta.dir, "..", "scripts", "package-consumer-smoke.ts");
const DIGEST = "0123456789abcdef".repeat(4);
const OTHER_DIGEST = "f".repeat(64);

const scratchRoots: string[] = [];

afterEach(() => {
  for (const root of scratchRoots.splice(0)) rmSync(root, { recursive: true, force: true });
});

describe("--digest: the smoke test only vouches for the tarball its digest names", () => {
  const refusalFor = (digestText: string) =>
    tarballDigestRefusal({
      tarballPath: join("packed", "ai-engineering.tgz"),
      tarballSha256: DIGEST,
      digestPath: "ai-engineering.tgz.sha256",
      digestText,
    });

  test("a sha256sum line naming this tarball with its digest is accepted, in text or binary mode", () => {
    expect(refusalFor(`${DIGEST}  ai-engineering.tgz\n`)).toBeUndefined();
    expect(refusalFor(`${DIGEST.toUpperCase()} *ai-engineering.tgz\r\n`)).toBeUndefined();
  });

  test("another digest, another file, or anything but one sha256sum line refuses", () => {
    expect(refusalFor(`${OTHER_DIGEST}  ai-engineering.tgz\n`)).toBe(
      `ai-engineering.tgz has sha256 ${DIGEST}, but ai-engineering.tgz.sha256 records ${OTHER_DIGEST}: this is not the tarball whose digest was recorded.`,
    );
    expect(refusalFor(`${DIGEST}  other.tgz\n`)).toBe(
      "ai-engineering.tgz.sha256 records the digest of other.tgz, not ai-engineering.tgz: smoke-test the tarball the digest names.",
    );
    const malformed =
      "ai-engineering.tgz.sha256 is not one sha256sum line for ai-engineering.tgz: record it with sha256sum ai-engineering.tgz > ai-engineering.tgz.sha256.";
    for (const text of ["", `${DIGEST}\n`, `${DIGEST.slice(1)}  ai-engineering.tgz\n`, `${DIGEST}  ai-engineering.tgz\n${DIGEST}  ai-engineering.tgz\n`]) {
      expect(refusalFor(text)).toBe(malformed);
    }
  });

  test("the CLI prints the tarball's sha256 and refuses a mismatched digest before installing anything", () => {
    const root = mkdtempSync(join(tmpdir(), "package-consumer-digest-"));
    scratchRoots.push(root);
    const tarball = join(root, "ai-engineering.tgz");
    writeFileSync(tarball, "not the tarball the digest names");
    const sha256 = createHash("sha256").update("not the tarball the digest names").digest("hex");
    writeFileSync(join(root, "ai-engineering.tgz.sha256"), `${OTHER_DIGEST}  ai-engineering.tgz\n`);

    const result = spawnSync(
      process.execPath,
      [SMOKE_SCRIPT, "--tarball", "ai-engineering.tgz", "--digest", "ai-engineering.tgz.sha256"],
      { cwd: root, encoding: "utf8" },
    );

    expect({ status: result.status, stdout: result.stdout, stderr: result.stderr }).toEqual({
      status: 1,
      stdout: `sha256=${sha256}\n`,
      stderr: `✗ ai-engineering.tgz has sha256 ${sha256}, but ai-engineering.tgz.sha256 records ${OTHER_DIGEST}: this is not the tarball whose digest was recorded.\n`,
    });
  });
});

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
