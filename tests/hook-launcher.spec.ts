// The hook line a Windows host runs must name a shim PowerShell will start under the
// Restricted execution policy a fresh laptop ships with: a bare `ai-eng` resolves to npm's
// ai-eng.ps1, which that policy refuses to load (first-install probe, windows-latest, 3.0.0).
import { afterAll, describe, expect, test } from "bun:test";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { hookLauncher, withLauncher } from "../src/surfaces/adapters.ts";
import { mergeSharedText, stripSharedText } from "../src/install.ts";
import { embeddedTemplate } from "../src/embed.ts";

const sandbox = mkdtempSync(join(tmpdir(), "hook-launcher-"));
afterAll(() => rmSync(sandbox, { recursive: true, force: true }));

function binDir(name: string, files: string[]): string {
  const dir = join(sandbox, name);
  mkdirSync(dir, { recursive: true });
  for (const file of files) writeFileSync(join(dir, file), "");
  return dir;
}

describe("hookLauncher — the name a hook line calls", () => {
  test("is plain ai-eng off Windows", () => {
    expect(hookLauncher("darwin", "/usr/bin")).toBe("ai-eng");
    expect(hookLauncher("linux", "/usr/bin")).toBe("ai-eng");
  });

  test("on Windows is npm's .cmd shim, never the .ps1 beside it", () => {
    const npm = binDir("npm", ["ai-eng", "ai-eng.cmd", "ai-eng.ps1"]);
    expect(hookLauncher("win32", npm)).toBe("ai-eng.cmd");
  });

  test("on Windows is bun's .exe shim, first hit in PATH order", () => {
    const bun = binDir("bun", ["ai-eng.exe", "ai-eng.bunx"]);
    const npm = binDir("npm-second", ["ai-eng.cmd", "ai-eng.ps1"]);
    expect(hookLauncher("win32", `${bun};${npm}`)).toBe("ai-eng.exe");
    expect(hookLauncher("win32", `${npm};${bun}`)).toBe("ai-eng.cmd");
  });

  test("on Windows with nothing on PATH yet falls back to the .cmd npm will write", () => {
    expect(hookLauncher("win32", "")).toBe("ai-eng.cmd");
  });
});

describe("withLauncher — only the call is renamed", () => {
  test("every hook line calls the shim, and the guard still probes for any ai-eng", () => {
    const rendered = withLauncher(embeddedTemplate("settings.copilot.json.tpl"), "ai-eng.cmd");
    expect(rendered).not.toContain('"ai-eng chain ');
    expect(rendered).toContain("ai-eng.cmd chain PreToolUse --surface copilot-cli");
    expect(rendered).toContain("Get-Command ai-eng -ErrorAction SilentlyContinue");
    expect(rendered).toContain("command -v ai-eng >/dev/null");
  });

  test("a Windows-rendered entry is ours: a re-init replaces it, uninstall takes it out", () => {
    const template = embeddedTemplate("settings.claude.json.tpl");
    const windows = withLauncher(template, "ai-eng.cmd");
    const user = `${JSON.stringify({ model: "opus" }, null, 2)}\n`;
    const installed = mergeSharedText(user, windows);
    if ("refused" in installed) throw new Error(installed.refused);
    const reinstalled = mergeSharedText(installed.text, windows);
    if ("refused" in reinstalled) throw new Error(reinstalled.refused);
    expect(reinstalled.changed).toBe(false);
    expect(stripSharedText(installed.text)).toBe(user);
  });
});

describe("the Copilot template — one file the CLI and VS Code both read", () => {
  test("every entry carries a bash line and a PowerShell line, each guarded against a missing ai-eng", () => {
    const hooks = (JSON.parse(embeddedTemplate("settings.copilot.json.tpl")) as { hooks: Record<string, Array<Record<string, string>>> }).hooks;
    for (const entries of Object.values(hooks)) {
      for (const entry of entries) {
        expect(entry["command"]).toStartWith("command -v ai-eng >/dev/null 2>&1 && ");
        expect(entry["command"]).toEndWith(" || exit 0");
        expect(entry["powershell"]).toStartWith("if (Get-Command ai-eng -ErrorAction SilentlyContinue) { ");
        expect(entry["powershell"]).toContain("exit $LASTEXITCODE");
      }
    }
  });
});
