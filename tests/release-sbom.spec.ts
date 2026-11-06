// The release SBOM describes what a consumer actually installs: the packed package and
// the runtime dependencies Node resolves from it — never the repository root, never a
// development-only dependency, and never a component whose license nobody declared.
import { afterEach, describe, expect, test } from "bun:test";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { buildRuntimeSbom, MissingLicenseError } from "../scripts/release-sbom.ts";

const PACKAGE_NAME = "ai-engineering";
const SERIAL_NUMBER = /^urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

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

function withoutSerialNumber(bom: Record<string, unknown>): Record<string, unknown> {
  const { serialNumber: _serialNumber, ...rest } = bom;
  return rest;
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

    expect(bom.serialNumber).toMatch(SERIAL_NUMBER);
    expect(bom).toEqual({
      bomFormat: "CycloneDX",
      specVersion: "1.5",
      serialNumber: bom.serialNumber,
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

    expect(withoutSerialNumber(bom)).toEqual({
      bomFormat: "CycloneDX",
      specVersion: "1.5",
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

  test("the output is identical whatever order dependencies were declared in, except the serial number", () => {
    const declaredFirst = newConsumerRoot();
    const declaredReversed = newConsumerRoot();
    writeBaseFixture(declaredFirst);
    writeBaseFixture(declaredReversed, { isRuntimeOrderReversed: true });

    const first = buildRuntimeSbom({ consumerRoot: declaredFirst, packageName: PACKAGE_NAME });
    const reversed = buildRuntimeSbom({ consumerRoot: declaredReversed, packageName: PACKAGE_NAME });

    expect(JSON.stringify(withoutSerialNumber(reversed))).toBe(JSON.stringify(withoutSerialNumber(first)));
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
});
