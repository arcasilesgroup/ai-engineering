// tests/cli-ux.test.ts — unit gates for cli-ux-14: the verb suggestion seam and
// the terminal identity. The frame layer's scripted-input replay is exercised
// through the sandbox proofs (scripts/proof-cli-ux.sh), not here.
import { afterAll, beforeAll, describe, expect, spyOn, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { ALL_VERBS, suggestVerb } from "../src/shared-verbs.ts";


describe("verb suggestion (§14.5b — no error without the line of action)", () => {
  test("a transposed verb is corrected", () => {
    expect(suggestVerb("chian")).toBe("chain");
    expect(suggestVerb("doctro")).toBe("doctor");
  });
  test("an exact verb is its own suggestion", () => {
    expect(suggestVerb("doctor")).toBe("doctor");
  });
  test("a word that resembles nothing is not 'corrected'", () => {
    expect(suggestVerb("xyz")).toBeNull();
    expect(suggestVerb("deploy")).toBeNull();
    expect(suggestVerb("")).toBeNull();
  });
  test("case and padding do not defeat it", () => {
    expect(suggestVerb("  INIT ")).toBe("init");
  });
});


describe("branding · the terminal identity", () => {
  test("the logo carries the version and the three verbs, into stdout", async () => {
    const chunks: string[] = [];
    const spy = spyOn(process.stdout, "write").mockImplementation(((chunk: unknown) => {
      chunks.push(String(chunk));
      return true;
    }) as never);
    try {
      const { showLogo } = await import("../src/branding.ts");
      showLogo("9.9.9");
    } finally {
      spy.mockRestore();
    }
    const painted = chunks.join("");
    expect(painted).toContain("e n g i n e e r i n g");
    expect(painted).toContain("v9.9.9 · install · guard · prove");
  });
  test("the banner paints the brand hex as truecolor on a TTY", async () => {
    // The declaration pins banner-green to the accent hex; styleText only accepts
    // named formats, so the strict runtimes (Bun 1.3) crashed on the first render
    // and the lenient ones silently dropped the colour. The frame must emit the
    // truecolor SGR for #00ED64 — r 0, g 237, b 100 — itself.
    const { showLogo } = await import("../src/branding.ts");
    const chunks: string[] = [];
    const descriptor = Object.getOwnPropertyDescriptor(process.stdout, "isTTY");
    Object.defineProperty(process.stdout, "isTTY", { value: true, configurable: true });
    const spy = spyOn(process.stdout, "write").mockImplementation(((chunk: unknown) => {
      chunks.push(String(chunk));
      return true;
    }) as never);
    // Env hygiene (see file header): a leaked NO_COLOR flips later specs.
    const ambientNoColor = process.env["NO_COLOR"];
    delete process.env["NO_COLOR"];
    try {
      showLogo("9.9.9");
    } finally {
      spy.mockRestore();
      if (descriptor) Object.defineProperty(process.stdout, "isTTY", descriptor);
      else Reflect.deleteProperty(process.stdout, "isTTY"); // inherited getter resumes
      if (ambientNoColor !== undefined) process.env["NO_COLOR"] = ambientNoColor;
    }
    expect(chunks.join("")).toContain("\u001B[38;2;0;237;100m");
  });
});


describe("the workspace hub is gone (floating-core#2)", () => {
  const cli = join(import.meta.dir, "..", "src", "cli.ts");
  let engHome: string;

  beforeAll(() => {
    engHome = mkdtempSync(join(tmpdir(), "ai-eng-cli-ux-"));
  });
  afterAll(() => rmSync(engHome, { recursive: true, force: true }));

  function eng(args: string[]): { status: number | null; stdout: string; stderr: string } {
    const run = spawnSync(process.execPath, [cli, ...args], {
      cwd: engHome,
      encoding: "utf8",
      env: { ...process.env, AI_ENG_HOME: engHome, NO_COLOR: "1", CI: "1", AI_ENG_NO_UPDATE_NOTICES: "1" },
      input: "",
      timeout: 20_000,
    });
    return { status: run.status, stdout: run.stdout ?? "", stderr: run.stderr ?? "" };
  }

  test("`ai-eng workspace` is an unknown verb", () => {
    const run = eng(["workspace"]);
    expect(run.status).toBe(2);
    expect(run.stderr).toContain("unknown verb: workspace\n");
  });

  for (const verb of ["briefing", "upgrade", "spec"]) {
    test(`\`ai-eng ${verb}\` is an unknown verb`, () => {
      const run = eng([verb]);
      expect(run.status).toBe(2);
      expect(run.stderr).toContain(`unknown verb: ${verb}\n`);
    });
  }

  test("`ai-eng --help` omits retired verbs", () => {
    const help = eng(["--help"]);
    expect(help.status).toBe(0);
    expect(help.stdout).toContain("ai-eng init");
    expect(help.stdout).not.toContain("workspace");
    expect(help.stdout).not.toMatch(/\b(?:briefing|upgrade|spec)\b/);
  });

  test("ALL_VERBS does not carry workspace", () => {
    expect(ALL_VERBS).toContain("init");
    expect(ALL_VERBS).not.toContain("workspace");
  });
});
