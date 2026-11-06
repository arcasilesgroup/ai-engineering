// The release SBOM: what a consumer actually installs from the packed tarball — the
// package and every runtime dependency Node resolves from it, each with its license.
// Development-only dependencies never install for a consumer, so they never appear.
//
// Usage: bun scripts/release-sbom.ts --tarball <file.tgz> --out <sbom.json>
//        bun scripts/release-sbom.ts --consumer <installed consumer dir> --out <sbom.json>
import { randomUUID } from "node:crypto";
import { existsSync, mkdtempSync, readFileSync, realpathSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join, resolve } from "node:path";
import { parseArgs } from "node:util";
import { runCommand } from "./package-consumer-smoke.ts";

type Manifest = {
  name?: string;
  version?: string;
  license?: unknown;
  licenses?: unknown;
  dependencies?: Record<string, string> | null;
  optionalDependencies?: Record<string, string> | null;
};

type License = { license: { id: string } } | { expression: string };

type Component = {
  type: "application" | "library";
  "bom-ref": string;
  group?: string;
  name: string;
  version: string;
  purl: string;
  licenses: License[];
};

type DependencyEdge = { ref: string; dependsOn: string[] };

export type CycloneDxBom = {
  bomFormat: "CycloneDX";
  specVersion: "1.5";
  serialNumber: string;
  version: 1;
  // Loosely typed on purpose: callers compare it against plain JSON records.
  metadata: { component: Record<string, unknown> };
  components: Component[];
  dependencies: DependencyEdge[];
};

export class MissingLicenseError extends Error {
  readonly components: string[];

  constructor(components: string[]) {
    super(`No license metadata for runtime component(s): ${components.join(", ")}`);
    this.name = "MissingLicenseError";
    this.components = components;
  }
}

const SPDX_ID = /^[A-Za-z0-9.+-]+$/;

function readManifest(directory: string): Manifest {
  return JSON.parse(readFileSync(join(directory, "package.json"), "utf8")) as Manifest;
}

function purlOf(name: string, version: string): string {
  const [scope, bareName] = name.startsWith("@") ? name.split("/", 2) : [undefined, name];
  const namespace = scope ? `${encodeURIComponent(scope)}/` : "";
  return `pkg:npm/${namespace}${encodeURIComponent(bareName ?? name)}@${encodeURIComponent(version)}`;
}

function licenseOf(value: string): License {
  return SPDX_ID.test(value) ? { license: { id: value } } : { expression: value };
}

/** `license: "MIT"`, `license: "(MIT OR ISC)"`, or the legacy `licenses: [{ type }]`. */
function licensesOf(manifest: Manifest): License[] {
  const declared = manifest.license;
  if (typeof declared === "string" && declared.trim() !== "") return [licenseOf(declared.trim())];
  if (typeof declared === "object" && declared !== null && "type" in declared && typeof declared.type === "string") {
    return [licenseOf(declared.type)];
  }
  const legacy = Array.isArray(manifest.licenses) ? (manifest.licenses as unknown[]) : [];
  return legacy
    .map((entry) => (typeof entry === "string" ? entry : (entry as { type?: unknown } | null)?.type))
    .filter((type): type is string => typeof type === "string" && type.trim() !== "")
    .map((type) => licenseOf(type.trim()));
}

/** Node's lookup: `<dir>/node_modules/<name>` from the requiring package up to the
 *  consumer root, skipping `node_modules/node_modules`. Never above the consumer, so
 *  the host's own packages cannot stand in for one the consumer lacks. */
function resolveDependency(fromDirectory: string, name: string, consumerRoot: string): string | undefined {
  for (let directory = fromDirectory; ; directory = dirname(directory)) {
    if (basename(directory) !== "node_modules") {
      const candidate = join(directory, "node_modules", name);
      if (existsSync(join(candidate, "package.json"))) return candidate;
    }
    if (directory === consumerRoot || dirname(directory) === directory) return undefined;
  }
}

function componentOf(manifest: Manifest, directory: string, type: Component["type"]): Component {
  const { name, version } = manifest;
  if (!name || !version) throw new Error(`${join(directory, "package.json")} has no name or version`);
  const purl = purlOf(name, version);
  const [group, bareName] = name.startsWith("@") ? name.split("/", 2) : [undefined, name];
  return {
    type,
    "bom-ref": purl,
    ...(group ? { group } : {}),
    name: bareName ?? name,
    version,
    purl,
    licenses: licensesOf(manifest),
  };
}

function byText(left: string, right: string): number {
  if (left === right) return 0;
  return left < right ? -1 : 1;
}

export function buildRuntimeSbom(options: { consumerRoot: string; packageName: string }): CycloneDxBom {
  const consumerRoot = resolve(options.consumerRoot);
  const packageDirectory = join(consumerRoot, "node_modules", options.packageName);
  if (!existsSync(join(packageDirectory, "package.json"))) {
    throw new Error(`${options.packageName} is not installed under ${consumerRoot}`);
  }

  const root = componentOf(readManifest(packageDirectory), packageDirectory, "application");
  const components = new Map<string, Component>([[root.purl, root]]);
  const edges = new Map<string, string[]>();
  const pending: Array<{ directory: string; purl: string }> = [{ directory: packageDirectory, purl: root.purl }];

  for (let next = pending.pop(); next !== undefined; next = pending.pop()) {
    const manifest = readManifest(next.directory);
    const runtime = Object.keys(manifest.dependencies ?? {});
    const optional = new Set(Object.keys(manifest.optionalDependencies ?? {}));
    const dependsOn = new Set<string>();
    for (const name of [...new Set([...runtime, ...optional])]) {
      const directory = resolveDependency(next.directory, name, consumerRoot);
      if (!directory) {
        if (optional.has(name)) continue;
        throw new Error(`${next.purl} depends on ${name}, but ${name} is not installed under ${consumerRoot}`);
      }
      const component = componentOf(readManifest(directory), directory, "library");
      dependsOn.add(component.purl);
      if (components.has(component.purl)) continue;
      components.set(component.purl, component);
      pending.push({ directory, purl: component.purl });
    }
    edges.set(next.purl, [...dependsOn].sort(byText));
  }

  const unlicensed = [...components.values()]
    .filter((component) => component.licenses.length === 0)
    .map((component) => component.purl)
    .sort(byText);
  if (unlicensed.length > 0) throw new MissingLicenseError(unlicensed);

  return {
    bomFormat: "CycloneDX",
    specVersion: "1.5",
    serialNumber: `urn:uuid:${randomUUID()}`,
    version: 1,
    metadata: { component: root },
    components: [...components.values()].filter((component) => component !== root).sort((left, right) => byText(left.purl, right.purl)),
    dependencies: [...edges.entries()]
      .map(([ref, dependsOn]) => ({ ref, dependsOn }))
      .sort((left, right) => byText(left.ref, right.ref)),
  };
}

/** Installs the exact tarball the way a consumer does — runtime dependencies only,
 *  no install scripts — in a scratch directory outside the checkout. */
function installConsumer(tarball: string): string {
  const consumerRoot = mkdtempSync(join(realpathSync(tmpdir()), "ai-eng-release-sbom-"));
  writeFileSync(join(consumerRoot, "package.json"), '{"name":"sbom-consumer","private":true}\n');
  const install = runCommand(
    "npm",
    ["install", "--omit=dev", "--ignore-scripts", "--no-audit", "--no-fund", resolve(tarball)],
    consumerRoot,
  );
  if (install.status !== 0) {
    rmSync(consumerRoot, { recursive: true, force: true });
    throw new Error(`npm install of ${tarball} failed (status ${install.status ?? install.errorCode}).\n${install.stderr || install.stdout}`);
  }
  return consumerRoot;
}

function main(): void {
  const { values } = parseArgs({
    options: { tarball: { type: "string" }, consumer: { type: "string" }, out: { type: "string" } },
  });
  const { tarball, consumer, out } = values;
  if (!out || Boolean(tarball) === Boolean(consumer)) {
    throw new Error("usage: bun scripts/release-sbom.ts (--tarball <file.tgz> | --consumer <dir>) --out <sbom.json>");
  }
  const consumerRoot = consumer ? resolve(consumer) : installConsumer(tarball ?? "");
  try {
    const bom = buildRuntimeSbom({ consumerRoot, packageName: "ai-engineering" });
    writeFileSync(out, `${JSON.stringify(bom, null, 2)}\n`);
    process.stdout.write(`SBOM for ${String(bom.metadata.component["purl"])}: ${bom.components.length} runtime component(s) → ${out}\n`);
  } finally {
    if (!consumer) rmSync(consumerRoot, { recursive: true, force: true, maxRetries: 10, retryDelay: 200 });
  }
}

if (import.meta.main) {
  try {
    main();
  } catch (error: unknown) {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
    process.exitCode = 1;
  }
}
