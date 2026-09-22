// tests/cli-ux.test.ts — unit gates for cli-ux-14: the verb suggestion seam and
// the terminal identity. The frame layer's scripted-input replay is exercised
// through the sandbox proofs (scripts/proof-cli-ux.sh), not here.
import { describe, expect, spyOn, test } from "bun:test";
import { suggestVerb } from "../src/shared-verbs.ts";


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
