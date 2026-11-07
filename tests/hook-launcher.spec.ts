// The hook line a Windows host runs must name a shim PowerShell will start under the
// Restricted execution policy a fresh laptop ships with: a bare `ai-eng` resolves to npm's
// ai-eng.ps1, which that policy refuses to load (first-install probe, windows-latest, 3.0.0).
import { afterAll, describe, expect, test } from "bun:test";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { carrierFiles, hookLauncher, withLauncher } from "../src/surfaces/adapters.ts";
import { canonicalSurfaceId } from "../src/env.ts";
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
  test("every hook line calls the shim, and the guards still probe for any ai-eng", () => {
    const rendered = withLauncher(embeddedTemplate("settings.claude.json.tpl"), "ai-eng.cmd");
    expect(rendered).not.toContain('"ai-eng chain ');
    expect(rendered).toContain('"ai-eng.cmd chain PreToolUse"');
    const copilot = withLauncher(embeddedTemplate("settings.copilot.json.tpl"), "ai-eng.cmd");
    expect(copilot).toContain("command -v ai-eng >/dev/null 2>&1 || exit 0; ai-eng.cmd chain PreToolUse");
  });

  test("a repo carrier is the same bytes on every OS: only machine files name the launcher", () => {
    // Run on any OS: the repo render never depends on this machine's PATH.
    expect(carrierFiles("cursor", "repo")!.main).toBe(embeddedTemplate("settings.cursor.json.tpl"));
    expect(carrierFiles("copilot-cli", "repo")!.main).toBe(embeddedTemplate("settings.copilot.json.tpl"));
  });

  test("3.0.0's Copilot lines are ours: a re-init replaces them instead of adding a second hook", () => {
    const legacy = (event: string) => ({ type: "command", command: `command -v ai-eng >/dev/null 2>&1 && ai-eng chain ${event} --surface copilot-cli || exit 0`, timeoutSec: 10 });
    const old = `${JSON.stringify({ version: 1, hooks: { preToolUse: [legacy("PreToolUse")], postToolUse: [legacy("PostToolUse")] } }, null, 2)}\n`;
    const merged = mergeSharedText(old, embeddedTemplate("settings.copilot.json.tpl"));
    if ("refused" in merged) throw new Error(merged.refused);
    const hooks = (JSON.parse(merged.text) as { hooks: Record<string, unknown[]> }).hooks;
    expect(hooks["preToolUse"]).toHaveLength(1);
    expect(hooks["postToolUse"]).toHaveLength(1);
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
  test("every entry fails open only on a missing ai-eng, never on a chain that crashed", () => {
    const hooks = (JSON.parse(embeddedTemplate("settings.copilot.json.tpl")) as { hooks: Record<string, Array<Record<string, string>>> }).hooks;
    for (const entries of Object.values(hooks)) {
      for (const entry of entries) {
        // `a && b || exit 0` would also turn b's failure into an allow.
        expect(entry["command"]).toStartWith("command -v ai-eng >/dev/null 2>&1 || exit 0; ai-eng chain ");
        expect(entry["command"]).not.toEndWith("|| exit 0");
        // An Application is a .cmd or .exe, never the .ps1 a Restricted policy refuses.
        expect(entry["powershell"]).toStartWith("$c = Get-Command ai-eng -CommandType Application ");
        // A shim that could not start leaves $LASTEXITCODE unset: `exit $null` would allow.
        expect(entry["powershell"]).toContain("if ($null -eq $LASTEXITCODE) { exit 1 }");
      }
    }
  });

  test("VS Code selects the Copilot surface: one carrier set, so no hook runs twice", () => {
    expect(canonicalSurfaceId("vscode")).toBe("copilot-cli");
    expect(canonicalSurfaceId("copilot-vscode")).toBe("copilot-cli");
    expect(canonicalSurfaceId("copilot")).toBe("copilot-cli");
  });
});
