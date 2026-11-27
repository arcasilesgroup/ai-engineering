import { afterEach, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { chmodSync, cpSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import {
  packageConsumerFailures,
  runPackageConsumerSmoke,
  tarballDigestRefusal,
} from "../scripts/package-consumer-smoke.ts";

const SMOKE_SCRIPT = join(import.meta.dir, "..", "scripts", "package-consumer-smoke.ts");
const LAUNCHER = join(import.meta.dir, "..", "bin", "ai-eng.js");
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

/** A package built on purpose to be stale: its manifest says 9.9.9 while the
 *  binary it carries answers 3.2.2, and the stamp that binary carries names the
 *  manifest — a build older than the manifest it travels beside, the shape of an
 *  install whose binary outvoted its manifest. Never a real release; the release
 *  gate has to refuse it all the same, which is what makes the gate worth
 *  trusting. */
function stalePackageTarball(root: string): string {
  const packageRoot = join(root, "package");
  const shipped: Record<string, string> = {
    "package.json": `${JSON.stringify(
      { name: "ai-engineering", version: "9.9.9", type: "module", bin: { "ai-eng": "bin/ai-eng.js" } },
      null,
      2,
    )}\n`,
    "src/cli.ts": 'console.log("ai-eng 3.2.2");\n',
    "dist/BUILD-VERSION-ai-eng": "9.9.9\n",
    "dist/ai-eng": "#!/bin/sh\necho ai-eng 3.2.2\n",
  };
  for (const [path, contents] of Object.entries(shipped)) {
    mkdirSync(dirname(join(packageRoot, path)), { recursive: true });
    writeFileSync(join(packageRoot, path), contents);
  }
  mkdirSync(join(packageRoot, "bin"), { recursive: true });
  cpSync(LAUNCHER, join(packageRoot, "bin", "ai-eng.js"));
  for (const executable of ["bin/ai-eng.js", "dist/ai-eng"]) chmodSync(join(packageRoot, executable), 0o755);

  const tarball = join(root, "ai-engineering-9.9.9.tgz");
  const packed = spawnSync("tar", ["-czf", tarball, "-C", root, "package"], { encoding: "utf8" });
  if (packed.status !== 0) throw new Error(`tar could not pack the stale package: ${packed.stderr}`);
  return tarball;
}

// A shell-script binary only executes on a POSIX kernel; the Windows shim path is
// covered by the fresh-install case, which the same version assertion guards.
test.skipIf(process.platform === "win32")(
  "the release gate fails on a package whose binary answers a version its manifest does not name",
  async () => {
    const root = mkdtempSync(join(tmpdir(), "package-consumer-stale-"));
    scratchRoots.push(root);

    const result = await runPackageConsumerSmoke({ tarball: stalePackageTarball(root) });
    const failures = packageConsumerFailures(result);

    expect(result.version).toBe("9.9.9");
    expect(result.npmCommand.stdout).toBe("ai-eng 3.2.2\n");
    expect(failures).toContain("npm consumer command did not return the exact version output and status");
    expect(failures).toContain(
      "tarball ships dist/ai-eng: a compiled binary must never travel beside a package.json it can outvote",
    );
  },
  { timeout: 120_000 },
);
