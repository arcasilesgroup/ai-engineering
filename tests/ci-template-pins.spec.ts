import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const ROOT = resolve(import.meta.dir, "..");
const TEMPLATE = resolve(ROOT, "templates/ci.yml.tpl");
const WORKFLOW = resolve(ROOT, ".github/workflows/check.yml");
const TOOLCHAIN = resolve(ROOT, "scripts/toolchain.sh");

const template = readFileSync(TEMPLATE, "utf8");
const workflow = readFileSync(WORKFLOW, "utf8");
const toolchain = readFileSync(TOOLCHAIN, "utf8");

function pinOf(source: string, name: string): string | undefined {
  return source.match(new RegExp(`${name}@([0-9a-f]{40})(?: # (v[\\d.]+))?`))?.[0];
}

function toolchainValue(key: string): string {
  return toolchain.match(new RegExp(`^${key}=(.+)$`, "m"))?.[1] ?? "";
}

// The template embeds version + sha256 inline ("ver=X" + "echo "<sha>  name.tgz").
function templateToolPin(tool: string): string {
  const ver = template.match(new RegExp(`ver=([\\d.]+)[\\s\\S]{0,120}?${tool}_`))?.[1] ?? "";
  const sha256 = template.match(new RegExp(`"([0-9a-f]{64})\\s+${tool}\\.tgz"`))?.[1] ?? "";
  return `${ver} ${sha256}`;
}

function toolchainToolPin(prefix: string): string {
  return `${toolchainValue(`${prefix}_VERSION`)} ${toolchainValue(`${prefix}_SHA256`)}`;
}

// Failures name the file to regenerate, not just the diff.
function expectSamePin(actual: string, expected: string, regenerate: string): void {
  expect(`${regenerate} pins ${actual} — regenerate it to pin ${expected}`).toBe(
    `${regenerate} pins ${expected} — regenerate it to pin ${expected}`,
  );
}

describe("ci template pins track their source of truth", () => {
  test("actions/checkout matches .github/workflows/check.yml", () => {
    expectSamePin(
      pinOf(template, "actions/checkout") ?? "(none)",
      pinOf(workflow, "actions/checkout") ?? "(none)",
      "templates/ci.yml.tpl (source of truth: .github/workflows/check.yml)",
    );
  });

  test("gitleaks version + sha256 match scripts/toolchain.sh", () => {
    expectSamePin(
      templateToolPin("gitleaks"),
      toolchainToolPin("GITLEAKS"),
      "templates/ci.yml.tpl (source of truth: scripts/toolchain.sh)",
    );
  });

  test("trivy version + sha256 match scripts/toolchain.sh", () => {
    expectSamePin(
      templateToolPin("trivy"),
      toolchainToolPin("TRIVY"),
      "templates/ci.yml.tpl (source of truth: scripts/toolchain.sh)",
    );
  });
});
