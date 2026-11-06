import { spawnSync } from "node:child_process";
import { createHash, randomUUID } from "node:crypto";
import {
  copyFileSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { dirname, join, sep } from "node:path";
import { fileURLToPath } from "node:url";

type CommandResult = {
  status: number | null;
  stdout: string;
  stderr: string;
  errorCode: string | null;
};

type PackageConsumerResult = {
  version: string;
  packedFiles: string[];
  npmInstalledFiles: string[];
  bunInstalledFiles: string[];
  npmInstall: CommandResult;
  bunInstall: CommandResult;
  npmCommand: CommandResult;
  bunOnlyCommand: CommandResult;
  nodeProbe: CommandResult;
  runtimeDependencies: string[];
  tarballHashBefore: string;
  tarballHashAfter: string;
};

const PACKAGE_ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const REQUIRED_PACKED_FILES = [
  "package.json",
  "bin/ai-eng.js",
  "src/cli.ts",
  "src/version.ts",
  "skills/ai-verify/SKILL.md",
];
const FORBIDDEN_PACKED_FILES = ["scripts/build.ts"];

function runCommand(
  command: string,
  args: string[],
  cwd: string,
  env: NodeJS.ProcessEnv = process.env,
): CommandResult {
  const result = spawnSync(command, args, {
    cwd,
    env,
    encoding: "utf8",
    timeout: 120_000,
    maxBuffer: 10 * 1024 * 1024,
    shell: process.platform === "win32" && (command === "npm" || command.endsWith(".cmd")),
  });
  return {
    status: result.status,
    stdout: result.stdout ?? "",
    stderr: result.stderr ?? "",
    errorCode: result.error?.code ?? null,
  };
}

function requireCommandSuccess(label: string, result: CommandResult): void {
  if (result.status === 0) return;
  throw new Error(
    `${label} failed (status ${result.status ?? result.errorCode ?? "unknown"}).\n` +
      `${result.stderr || result.stdout}`,
  );
}

function listFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return listFiles(path).map((child) => join(entry.name, child));
    return [entry.name];
  }).map((path) => path.split(sep).join("/")).sort();
}

function sha256File(path: string): string {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function createBunOnlyPath(directory: string): string {
  const binDirectory = join(directory, "bin");
  mkdirSync(binDirectory);
  const bunName = process.platform === "win32" ? "bun.exe" : "bun";
  const bunPath = join(binDirectory, bunName);
  if (process.platform === "win32") copyFileSync(process.execPath, bunPath);
  else symlinkSync(process.execPath, bunPath);
  return binDirectory;
}

function packSummary(output: string): { filename: string; files: string[] } {
  const summaries = JSON.parse(output) as Array<{
    filename?: string;
    files?: Array<{ path?: string }>;
  }>;
  const summary = summaries[0];
  if (!summary?.filename || !summary.files) {
    throw new Error("npm pack did not return a tarball filename and file inventory.");
  }
  const files = summary.files.map((file) => file.path);
  if (files.some((path) => !path)) throw new Error("npm pack returned a file without a path.");
  return { filename: summary.filename, files: (files as string[]).sort() };
}

function installPath(consumerRoot: string): string {
  return join(consumerRoot, "node_modules", "ai-engineering");
}

function installedCommandPath(consumerRoot: string): string {
  return join(
    consumerRoot,
    "node_modules",
    ".bin",
    process.platform === "win32" ? "ai-eng.cmd" : "ai-eng",
  );
}

export async function runPackageConsumerSmoke(): Promise<PackageConsumerResult> {
  const smokeRoot = join(PACKAGE_ROOT, `.package-consumer-smoke-${process.pid}-${randomUUID()}`);
  const packDirectory = join(smokeRoot, "packed");
  const npmConsumer = join(smokeRoot, "npm-consumer");
  const bunConsumer = join(smokeRoot, "bun-consumer");
  mkdirSync(packDirectory, { recursive: true });
  mkdirSync(npmConsumer);
  mkdirSync(bunConsumer);

  try {
    const pack = runCommand(
      "npm",
      ["pack", "--json", "--pack-destination", packDirectory],
      PACKAGE_ROOT,
    );
    requireCommandSuccess("npm pack", pack);
    const packed = packSummary(pack.stdout);
    const tarballPath = join(packDirectory, packed.filename);
    const tarballHashBefore = sha256File(tarballPath);

    writeFileSync(join(npmConsumer, "package.json"), '{"name":"npm-consumer","private":true}\n');
    writeFileSync(join(bunConsumer, "package.json"), '{"name":"bun-consumer","private":true}\n');
    const npmInstall = runCommand(
      "npm",
      ["install", "--no-audit", "--no-fund", "--ignore-scripts", tarballPath],
      npmConsumer,
    );
    requireCommandSuccess("npm consumer install", npmInstall);

    const bunInstall = runCommand(process.execPath, ["add", tarballPath], bunConsumer);
    requireCommandSuccess("Bun consumer install", bunInstall);

    const npmPackageRoot = installPath(npmConsumer);
    const bunPackageRoot = installPath(bunConsumer);
    const npmManifest = JSON.parse(readFileSync(join(npmPackageRoot, "package.json"), "utf8")) as {
      version: string;
      dependencies?: Record<string, string>;
    };
    const bunManifest = JSON.parse(readFileSync(join(bunPackageRoot, "package.json"), "utf8")) as {
      version: string;
    };
    const npmCommand = runCommand(
      installedCommandPath(npmConsumer),
      ["--version"],
      npmConsumer,
    );

    const bunOnlyDirectory = createBunOnlyPath(smokeRoot);
    const bunOnlyEnvironment = { ...process.env, PATH: bunOnlyDirectory };
    const nodeProbe = runCommand("node", ["--version"], bunConsumer, bunOnlyEnvironment);
    const bunOnlyCommand =
      process.platform === "win32"
        ? runCommand(
            process.execPath,
            [join(bunPackageRoot, "bin", "ai-eng.js"), "--version"],
            bunConsumer,
            bunOnlyEnvironment,
          )
        : runCommand(
            installedCommandPath(bunConsumer),
            ["--version"],
            bunConsumer,
            bunOnlyEnvironment,
          );
    const tarballHashAfter = sha256File(tarballPath);

    if (bunManifest.version !== npmManifest.version) {
      throw new Error("npm and Bun consumers installed different package versions.");
    }

    return {
      version: npmManifest.version,
      packedFiles: packed.files,
      npmInstalledFiles: listFiles(npmPackageRoot),
      bunInstalledFiles: listFiles(bunPackageRoot),
      npmInstall,
      bunInstall,
      npmCommand,
      bunOnlyCommand,
      nodeProbe,
      runtimeDependencies: Object.keys(npmManifest.dependencies ?? {}).sort(),
      tarballHashBefore,
      tarballHashAfter,
    };
  } finally {
    rmSync(smokeRoot, { recursive: true, force: true });
  }
}

export function packageConsumerFailures(result: PackageConsumerResult): string[] {
  const failures: string[] = [];
  const expectedOutput = `ai-eng ${result.version}\n`;
  const packedFiles = new Set(result.packedFiles);

  for (const requiredFile of REQUIRED_PACKED_FILES) {
    if (!packedFiles.has(requiredFile)) failures.push(`tarball is missing ${requiredFile}`);
  }
  for (const forbiddenFile of FORBIDDEN_PACKED_FILES) {
    if (packedFiles.has(forbiddenFile)) failures.push(`tarball unexpectedly contains ${forbiddenFile}`);
  }
  if (JSON.stringify(result.npmInstalledFiles) !== JSON.stringify(result.packedFiles)) {
    failures.push("npm consumer files do not exactly match the packed tarball inventory");
  }
  if (JSON.stringify(result.bunInstalledFiles) !== JSON.stringify(result.packedFiles)) {
    failures.push("Bun consumer files do not exactly match the packed tarball inventory");
  }
  if (result.npmCommand.status !== 0 || result.npmCommand.stdout !== expectedOutput || result.npmCommand.stderr !== "") {
    failures.push("npm consumer command did not return the exact version output and status");
  }
  if (
    result.bunOnlyCommand.status !== 0 ||
    result.bunOnlyCommand.stdout !== expectedOutput ||
    result.bunOnlyCommand.stderr !== ""
  ) {
    failures.push("Bun-only consumer command did not return the exact version output and status");
  }
  if (result.nodeProbe.status === 0) failures.push("Node was available on the Bun-only PATH");
  if (result.runtimeDependencies.includes("smol-toml")) {
    failures.push("the packed package declares smol-toml as a runtime dependency");
  }
  if (result.tarballHashBefore !== result.tarballHashAfter) {
    failures.push("the packed tarball changed during consumer installation");
  }
  return failures;
}

if (import.meta.main) {
  runPackageConsumerSmoke()
    .then((result) => {
      const failures = packageConsumerFailures(result);
      if (failures.length > 0) {
        for (const failure of failures) process.stderr.write(`✗ ${failure}\n`);
        process.exitCode = 1;
        return;
      }
      process.stdout.write(`Package consumer smoke passed for ai-engineering ${result.version}.\n`);
    })
    .catch((error: unknown) => {
      process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
      process.exitCode = 1;
    });
}
