// The release SBOM describes what a consumer actually installs: the packed package and
// the runtime dependencies Node resolves from it — never the repository root, never a
// development-only dependency, and never a component whose license nobody declared.
// Its serial number is derived, never random: the same input yields the same bytes.
import { afterEach, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { buildRuntimeSbom, MissingLicenseError, serialNumberFromDigest } from "../scripts/release-sbom.ts";

const PACKAGE_NAME = "ai-engineering";
const SBOM_SCRIPT = join(import.meta.dir, "..", "scripts", "release-sbom.ts");
// sha256("ai-engineering@9.9.9") = c3f396fa7a77926ef8b1…, as a version-8 UUID.
const NAME_VERSION_SERIAL = "urn:uuid:c3f396fa-7a77-826e-b8b1-72d55426d461";

const ROOT_REF = "pkg:npm/ai-engineering@9.9.9";
const A_REF = "pkg:npm/a@1.0.0";
const B_REF = "pkg:npm/%40s/b@3.0.0";
const C1_REF = "pkg:npm/c@1.2.3";
const C2_REF = "pkg:npm/c@2.0.0";

const fixtureRoots: string[] = [];

afterEach(() => {
  for (const root of fixtureRoots.splice(0)) rmSync(root, { recursive: true, force: true });
});

function newConsumerRoot(): string {
  const root = mkdtempSync(join(tmpdir(), "release-sbom-"));
  fixtureRoots.push(root);
  return root;
}

function writeManifest(directory: string, manifest: Record<string, unknown>): void {
  mkdirSync(directory, { recursive: true });
  writeFileSync(join(directory, "package.json"), `${JSON.stringify(manifest, null, 2)}\n`);
}

type FixtureOptions = { isRuntimeOrderReversed?: boolean };

/** consumer → ai-engineering@9.9.9 → { a@1.0.0 → c@1.2.3, @s/b@3.0.0 }, with a
 *  development-only `d` and an unrelated `stray` installed beside them. */
function writeBaseFixture(root: string, options: FixtureOptions = {}): void {
  const modules = join(root, "node_modules");
  const runtimeDependencies: Record<string, string> = options.isRuntimeOrderReversed
    ? { "@s/b": "^3.0.0", a: "^1.0.0" }
    : { a: "^1.0.0", "@s/b": "^3.0.0" };
  writeManifest(root, {
    name: "consumer",
    version: "0.0.0",
    license: "MIT",
    private: true,
    dependencies: { [PACKAGE_NAME]: "9.9.9", d: "^1.0.0", stray: "^1.0.0" },
  });
  writeManifest(join(modules, PACKAGE_NAME), {
    name: PACKAGE_NAME,
    version: "9.9.9",
    license: "Apache-2.0",
    dependencies: runtimeDependencies,
    devDependencies: { d: "^1.0.0" },
  });
  writeManifest(join(modules, "a"), { name: "a", version: "1.0.0", license: "MIT", dependencies: { c: "^1.0.0" } });
  writeManifest(join(modules, "c"), { name: "c", version: "1.2.3", license: "ISC" });
  writeManifest(join(modules, "@s", "b"), {
    name: "@s/b",
    version: "3.0.0",
    licenses: [{ type: "Apache-2.0", url: "https://www.apache.org/licenses/LICENSE-2.0" }],
  });
  writeManifest(join(modules, "d"), { name: "d", version: "1.0.0", license: "MIT" });
  writeManifest(join(modules, "stray"), { name: "stray", version: "1.0.0", license: "MIT" });
}

function rootComponent(): Record<string, unknown> {
  return {
    type: "application",
    "bom-ref": ROOT_REF,
    name: "ai-engineering",
    version: "9.9.9",
    purl: ROOT_REF,
    licenses: [{ license: { id: "Apache-2.0" } }],
  };
}

function captureError(build: () => unknown): unknown {
  try {
    build();
  } catch (error) {
    return error;
  }
  throw new Error("buildRuntimeSbom returned instead of refusing");
}

describe("buildRuntimeSbom — the installed package's runtime graph as CycloneDX", () => {
  test("describes the package and its runtime transitive components, exactly and in purl order", () => {
    const consumerRoot = newConsumerRoot();
    writeBaseFixture(consumerRoot);

    const bom = buildRuntimeSbom({ consumerRoot, packageName: PACKAGE_NAME });

    expect(bom).toEqual({
      bomFormat: "CycloneDX",
      specVersion: "1.5",
      serialNumber: NAME_VERSION_SERIAL,
      version: 1,
      metadata: { component: rootComponent() },
      components: [
        {
          type: "library",
          "bom-ref": B_REF,
          group: "@s",
          name: "b",
          version: "3.0.0",
          purl: B_REF,
          licenses: [{ license: { id: "Apache-2.0" } }],
        },
        {
          type: "library",
          "bom-ref": A_REF,
          name: "a",
          version: "1.0.0",
          purl: A_REF,
          licenses: [{ license: { id: "MIT" } }],
        },
        {
          type: "library",
          "bom-ref": C1_REF,
          name: "c",
          version: "1.2.3",
          purl: C1_REF,
          licenses: [{ license: { id: "ISC" } }],
        },
      ],
      dependencies: [
        { ref: B_REF, dependsOn: [] },
        { ref: A_REF, dependsOn: [C1_REF] },
        { ref: ROOT_REF, dependsOn: [B_REF, A_REF] },
        { ref: C1_REF, dependsOn: [] },
      ],
    });
  });

  test("resolves each dependency the way Node does: nearest node_modules from the parent wins", () => {
    const consumerRoot = newConsumerRoot();
    const modules = join(consumerRoot, "node_modules");
    const packageRoot = join(modules, PACKAGE_NAME);
    writeManifest(consumerRoot, {
      name: "consumer",
      version: "0.0.0",
      private: true,
      dependencies: { [PACKAGE_NAME]: "9.9.9", a: "^0.1.0" },
    });
    writeManifest(packageRoot, {
      name: PACKAGE_NAME,
      version: "9.9.9",
      license: "Apache-2.0",
      dependencies: { a: "^1.0.0", "@s/b": "^3.0.0" },
    });
    // The consumer's own a@0.1.0 sits at the top; the package's a@1.0.0 is nested under it.
    writeManifest(join(modules, "a"), { name: "a", version: "0.1.0", license: "0BSD" });
    writeManifest(join(packageRoot, "node_modules", "a"), {
      name: "a",
      version: "1.0.0",
      license: "MIT",
      dependencies: { c: "^2.0.0" },
    });
    writeManifest(join(packageRoot, "node_modules", "a", "node_modules", "c"), {
      name: "c",
      version: "2.0.0",
      license: "MIT",
    });
    writeManifest(join(modules, "@s", "b"), {
      name: "@s/b",
      version: "3.0.0",
      license: "(MIT OR Apache-2.0)",
      dependencies: { c: "^1.0.0" },
    });
    writeManifest(join(modules, "c"), { name: "c", version: "1.2.3", license: "ISC" });

    const bom = buildRuntimeSbom({ consumerRoot, packageName: PACKAGE_NAME });

    expect(bom).toEqual({
      bomFormat: "CycloneDX",
      specVersion: "1.5",
      serialNumber: NAME_VERSION_SERIAL,
      version: 1,
      metadata: { component: rootComponent() },
      components: [
        {
          type: "library",
          "bom-ref": B_REF,
          group: "@s",
          name: "b",
          version: "3.0.0",
          purl: B_REF,
          licenses: [{ expression: "(MIT OR Apache-2.0)" }],
        },
        {
          type: "library",
          "bom-ref": A_REF,
          name: "a",
          version: "1.0.0",
          purl: A_REF,
          licenses: [{ license: { id: "MIT" } }],
        },
        {
          type: "library",
          "bom-ref": C1_REF,
          name: "c",
          version: "1.2.3",
          purl: C1_REF,
          licenses: [{ license: { id: "ISC" } }],
        },
        {
          type: "library",
          "bom-ref": C2_REF,
          name: "c",
          version: "2.0.0",
          purl: C2_REF,
          licenses: [{ license: { id: "MIT" } }],
        },
      ],
      dependencies: [
        { ref: B_REF, dependsOn: [C1_REF] },
        { ref: A_REF, dependsOn: [C2_REF] },
        { ref: ROOT_REF, dependsOn: [B_REF, A_REF] },
        { ref: C1_REF, dependsOn: [] },
        { ref: C2_REF, dependsOn: [] },
      ],
    });
  });

  test("a dependency cycle is walked once and recorded on both edges", () => {
    const consumerRoot = newConsumerRoot();
    writeBaseFixture(consumerRoot);
    writeManifest(join(consumerRoot, "node_modules", "c"), {
      name: "c",
      version: "1.2.3",
      license: "ISC",
      dependencies: { a: "^1.0.0" },
    });

    const bom = buildRuntimeSbom({ consumerRoot, packageName: PACKAGE_NAME });

    expect(bom.components.map((component: { purl: string }) => component.purl)).toEqual([B_REF, A_REF, C1_REF]);
    expect(bom.dependencies).toEqual([
      { ref: B_REF, dependsOn: [] },
      { ref: A_REF, dependsOn: [C1_REF] },
      { ref: ROOT_REF, dependsOn: [B_REF, A_REF] },
      { ref: C1_REF, dependsOn: [A_REF] },
    ]);
  });

  test("a development-only dependency without a license neither appears nor blocks", () => {
    const consumerRoot = newConsumerRoot();
    writeBaseFixture(consumerRoot);
    writeManifest(join(consumerRoot, "node_modules", "d"), { name: "d", version: "1.0.0" });

    const bom = buildRuntimeSbom({ consumerRoot, packageName: PACKAGE_NAME });

    expect(bom.components.map((component: { purl: string }) => component.purl)).toEqual([B_REF, A_REF, C1_REF]);
  });

  test("the output is byte-identical whatever order dependencies were declared in, serial number included", () => {
    const declaredFirst = newConsumerRoot();
    const declaredReversed = newConsumerRoot();
    writeBaseFixture(declaredFirst);
    writeBaseFixture(declaredReversed, { isRuntimeOrderReversed: true });

    const first = buildRuntimeSbom({ consumerRoot: declaredFirst, packageName: PACKAGE_NAME });
    const reversed = buildRuntimeSbom({ consumerRoot: declaredReversed, packageName: PACKAGE_NAME });

    expect(JSON.stringify(reversed)).toBe(JSON.stringify(first));
    expect(first.serialNumber).toBe(NAME_VERSION_SERIAL);
  });

  test("runtime components without license metadata block the SBOM and are named", () => {
    const consumerRoot = newConsumerRoot();
    writeBaseFixture(consumerRoot);
    const modules = join(consumerRoot, "node_modules");
    writeManifest(join(modules, "c"), { name: "c", version: "1.2.3" });
    writeManifest(join(modules, "@s", "b"), { name: "@s/b", version: "3.0.0", licenses: [] });

    const error = captureError(() => buildRuntimeSbom({ consumerRoot, packageName: PACKAGE_NAME }));

    expect(error).toBeInstanceOf(MissingLicenseError);
    expect(error).toBeInstanceOf(Error);
    const refusal = error as MissingLicenseError;
    expect(refusal.components).toEqual([B_REF, C1_REF]);
    expect(refusal.message).toContain(B_REF);
    expect(refusal.message).toContain(C1_REF);
    expect(refusal.message).not.toContain(A_REF);
  });

  test("the package itself without license metadata blocks the SBOM", () => {
    const consumerRoot = newConsumerRoot();
    writeBaseFixture(consumerRoot);
    writeManifest(join(consumerRoot, "node_modules", PACKAGE_NAME), {
      name: PACKAGE_NAME,
      version: "9.9.9",
      license: "",
      dependencies: { a: "^1.0.0", "@s/b": "^3.0.0" },
    });

    const error = captureError(() => buildRuntimeSbom({ consumerRoot, packageName: PACKAGE_NAME }));

    expect(error).toBeInstanceOf(MissingLicenseError);
    expect((error as MissingLicenseError).components).toEqual([ROOT_REF]);
  });

  test("a declared runtime dependency that is not installed fails closed instead of vanishing", () => {
    const consumerRoot = newConsumerRoot();
    writeBaseFixture(consumerRoot);
    rmSync(join(consumerRoot, "node_modules", "c"), { recursive: true, force: true });

    const error = captureError(() => buildRuntimeSbom({ consumerRoot, packageName: PACKAGE_NAME }));

    expect(error).toBeInstanceOf(Error);
    expect(error).not.toBeInstanceOf(MissingLicenseError);
    // The diagnosis names who asked for it and what is missing.
    expect((error as Error).message).toContain(A_REF);
    expect((error as Error).message).toMatch(/\bc\b/);
  });

  test("UNLICENSED, SEE LICENSE IN, blank and non-SPDX text are missing license metadata, not a license", () => {
    const declarations: Array<[string, Record<string, unknown>]> = [
      ["a", { license: "UNLICENSED" }],
      ["c", { license: "SEE LICENSE IN LICENSE.md" }],
      ["@s/b", { license: "MIT License" }],
      ["d", { license: "   " }],
      ["e", { license: "(MIT OR UNLICENSED)" }],
      ["f", { license: { type: "SEE-LICENSE-IN-FILE" } }],
      ["g", { licenses: [{ type: "MIT" }, { type: "Custom terms" }] }],
    ];
    const consumerRoot = newConsumerRoot();
    const modules = join(consumerRoot, "node_modules");
    writeManifest(consumerRoot, { name: "consumer", version: "0.0.0", private: true });
    writeManifest(join(modules, PACKAGE_NAME), {
      name: PACKAGE_NAME,
      version: "9.9.9",
      license: "Apache-2.0",
      dependencies: Object.fromEntries(declarations.map(([name]) => [name, "1.0.0"])),
    });
    for (const [name, license] of declarations) writeManifest(join(modules, name), { name, version: "1.0.0", ...license });

    const error = captureError(() => buildRuntimeSbom({ consumerRoot, packageName: PACKAGE_NAME }));

    expect(error).toBeInstanceOf(MissingLicenseError);
    expect((error as MissingLicenseError).components).toEqual([
      "pkg:npm/%40s/b@1.0.0",
      "pkg:npm/a@1.0.0",
      "pkg:npm/c@1.0.0",
      "pkg:npm/d@1.0.0",
      "pkg:npm/e@1.0.0",
      "pkg:npm/f@1.0.0",
      "pkg:npm/g@1.0.0",
    ]);
  });

  test("an SPDX id is a license id; an SPDX expression with AND, OR or WITH stays an expression", () => {
    const consumerRoot = newConsumerRoot();
    const modules = join(consumerRoot, "node_modules");
    writeManifest(consumerRoot, { name: "consumer", version: "0.0.0", private: true });
    writeManifest(join(modules, PACKAGE_NAME), {
      name: PACKAGE_NAME,
      version: "9.9.9",
      license: "Apache-2.0",
      dependencies: { a: "1.0.0", c: "1.0.0", d: "1.0.0" },
    });
    writeManifest(join(modules, "a"), { name: "a", version: "1.0.0", license: "Apache-2.0 WITH LLVM-exception" });
    writeManifest(join(modules, "c"), { name: "c", version: "1.0.0", license: "MIT AND (BSD-3-Clause OR GPL-2.0+)" });
    writeManifest(join(modules, "d"), { name: "d", version: "1.0.0", licenses: ["MIT", { type: "LicenseRef-Vendor" }] });

    const bom = buildRuntimeSbom({ consumerRoot, packageName: PACKAGE_NAME });

    expect(bom.components.map((component) => [component.purl, component.licenses])).toEqual([
      ["pkg:npm/a@1.0.0", [{ expression: "Apache-2.0 WITH LLVM-exception" }]],
      ["pkg:npm/c@1.0.0", [{ expression: "MIT AND (BSD-3-Clause OR GPL-2.0+)" }]],
      ["pkg:npm/d@1.0.0", [{ license: { id: "MIT" } }, { license: { id: "LicenseRef-Vendor" } }]],
    ]);
  });
});

describe("the SBOM names the tarball it describes", () => {
  test("serialNumberFromDigest is a version-8 RFC 9562 UUID from the digest's first 16 bytes", () => {
    expect(serialNumberFromDigest("0".repeat(64))).toBe("urn:uuid:00000000-0000-8000-8000-000000000000");
    expect(serialNumberFromDigest("f".repeat(64))).toBe("urn:uuid:ffffffff-ffff-8fff-bfff-ffffffffffff");
    expect(serialNumberFromDigest("0123456789abcdef".repeat(4))).toBe("urn:uuid:01234567-89ab-8def-8123-456789abcdef");
    expect(() => serialNumberFromDigest("F".repeat(64))).toThrow();
    expect(() => serialNumberFromDigest("0".repeat(63))).toThrow();
  });

  test("given the tarball's sha256, the root component carries it and the serial number derives from it", () => {
    const consumerRoot = newConsumerRoot();
    writeBaseFixture(consumerRoot);
    const tarballSha256 = "0123456789abcdef".repeat(4);

    const bom = buildRuntimeSbom({ consumerRoot, packageName: PACKAGE_NAME, tarballSha256 });

    expect({ serialNumber: bom.serialNumber, component: bom.metadata.component }).toEqual({
      serialNumber: "urn:uuid:01234567-89ab-8def-8123-456789abcdef",
      component: { ...rootComponent(), hashes: [{ alg: "SHA-256", content: tarballSha256 }] },
    });
    expect(Object.keys(bom.metadata.component)).toEqual(["type", "bom-ref", "name", "version", "purl", "licenses", "hashes"]);
  });

  test(
    "the CLI built from --tarball names that file's sha256 and writes the same bytes on every run",
    () => {
      const root = newConsumerRoot();
      const packageDirectory = join(root, "package");
      writeManifest(packageDirectory, { name: PACKAGE_NAME, version: "9.9.9", license: "Apache-2.0" });
      const tarball = join(root, "ai-engineering.tgz");
      const packed = spawnSync("tar", ["-czf", tarball, "package"], { cwd: root, encoding: "utf8" });
      expect(packed.status).toBe(0);
      const tarballSha256 = createHash("sha256").update(readFileSync(tarball)).digest("hex");
      const build = (out: string) =>
        spawnSync(process.execPath, [SBOM_SCRIPT, "--tarball", tarball, "--out", join(root, out)], { cwd: root, encoding: "utf8" });

      const first = build("first.cdx.json");
      const second = build("second.cdx.json");

      expect({ status: first.status, stderr: first.stderr }).toEqual({ status: 0, stderr: "" });
      expect({ status: second.status, stderr: second.stderr }).toEqual({ status: 0, stderr: "" });
      const bytes = readFileSync(join(root, "first.cdx.json"), "utf8");
      expect(readFileSync(join(root, "second.cdx.json"), "utf8")).toBe(bytes);
      const bom = JSON.parse(bytes) as { serialNumber: string; metadata: { component: Record<string, unknown> } };
      expect({ serialNumber: bom.serialNumber, component: bom.metadata.component }).toEqual({
        serialNumber: serialNumberFromDigest(tarballSha256),
        component: { ...rootComponent(), hashes: [{ alg: "SHA-256", content: tarballSha256 }] },
      });
    },
    { timeout: 120_000 },
  );
});
