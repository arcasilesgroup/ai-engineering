// The README's images: every one it references exists, every file in the folder is
// referenced, and the words the README repeats from a figure match the figure.
import { describe, expect, test } from "bun:test";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { BUTTONS, CARDS, HEADINGS, OUT_DIR, renderedFiles, THEMES } from "../scripts/readme-assets.ts";
import { DIAGRAM_VARS, FIGURES } from "../scripts/readme-figures.ts";

const ROOT = resolve(import.meta.dir, "..");
const README = readFileSync(join(ROOT, "README.md"), "utf8");
const STILLS = ["deny-no-verify.webp", "deny-silence.webp", "rewrite-test.webp", "receipt.webp"];

const referenced = (): string[] => [...README.matchAll(/(?:src|srcset)="(\.github\/assets\/[^"#]+)/g)].map((match) => match[1] as string);

/** WCAG 2.1 contrast ratio of two `#RRGGBB` colours. */
function contrast(foreground: string, background: string): number {
  const luminance = (hex: string): number => {
    const [red, green, blue] = [1, 3, 5].map((at) => {
      const channel = Number.parseInt(hex.slice(at, at + 2), 16) / 255;
      return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
    }) as [number, number, number];
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
  };
  const [light, dark] = [luminance(foreground), luminance(background)].sort((left, right) => right - left) as [number, number];
  return (light + 0.05) / (dark + 0.05);
}

describe("README images", () => {
  test("every image the README references is in the repository", () => {
    for (const path of referenced()) expect(existsSync(join(ROOT, path)), path).toBe(true);
  });

  test("no file in .github/assets/readme is an orphan, and the script's own files all exist", () => {
    const onDisk = readdirSync(OUT_DIR).sort();
    expect(onDisk).toEqual([...renderedFiles(), ...STILLS].sort());
    const used = new Set(referenced().map((path) => path.split("/").pop()));
    expect(onDisk.filter((file) => !used.has(file))).toEqual([]);
  });

  test("the README uses no absolute local path and loads no third-party image host but shields.io", () => {
    expect(README).not.toMatch(/(?:src|href|srcset)="(?:\/Users|\/home|[A-Za-z]:\\)/);
    const hosts = new Set([...README.matchAll(/src="https:\/\/([^/"]+)/g)].map((match) => match[1]));
    expect([...hosts]).toEqual(["img.shields.io"]);
  });

  test("every image carries alt text", () => {
    for (const tag of README.match(/<img\b[^>]*>/g) ?? []) expect(tag, tag).toMatch(/\balt="[^"]+"/);
  });
});

describe("README repeats the assets' words", () => {
  test("each heading's text is the alt text of its image", () => {
    for (const heading of HEADINGS) expect(README).toContain(`alt="${heading.text}"`);
  });

  test("each button's text is the alt text of its image", () => {
    for (const button of BUTTONS) expect(README).toContain(`alt="${button.text}"`);
  });

  test("each figure's alt text, caption and text version are in the README", () => {
    for (const figure of FIGURES) {
      expect(README, `alt of figure ${figure.n}`).toContain(`alt="${figure.alt}"`);
      expect(README, `caption of figure ${figure.n}`).toContain(figure.caption.replace(/^Figure (\d)\./, "<b>Figure $1.</b>"));
      expect(README, `text version of figure ${figure.n}`).toContain(`<summary>Text version of figure ${figure.n}</summary>`);
      figure.textVersion.forEach((step, index) => expect(README, `step ${index + 1} of figure ${figure.n}`).toContain(`${index + 1}. ${step}`));
    }
  });

  test("each card's chip and closing line are in the README alt text", () => {
    for (const card of CARDS) {
      expect(README).toContain(card.closing);
      expect(README).toContain(card.title);
    }
  });

  test("the hero's claim is the alt text", () => {
    expect(README).toContain("Your coding agent can't quietly turn off your checks; we publish where it still can.");
  });
});

describe("the figures stay legible in both modes", () => {
  test("text and node borders clear their contrast floors on the card and the node", () => {
    for (const mode of ["dark", "light"] as const) {
      const vars = DIAGRAM_VARS[mode];
      for (const surface of ["--surface", "--surface-2"]) {
        for (const text of ["--text", "--dim", "--accent", "--warn", "--bad"]) expect(contrast(vars[text] as string, vars[surface] as string), `${mode} ${text} on ${surface}`).toBeGreaterThanOrEqual(4.5);
      }
      expect(contrast(vars["--line-strong"] as string, vars["--surface-2"] as string), `${mode} border`).toBeGreaterThanOrEqual(3);
    }
  });

  test("hero, heading and card text clear 4.5:1 on their field", () => {
    for (const mode of ["dark", "light"] as const) {
      const theme = THEMES[mode];
      for (const text of [theme.ink, theme.muted, theme.accent]) expect(contrast(text, theme.field), `${mode} ${text} on field`).toBeGreaterThanOrEqual(4.5);
      for (const text of [theme.ink, theme.muted, theme.badText, theme.goodText]) expect(contrast(text, theme.raised), `${mode} ${text} on card`).toBeGreaterThanOrEqual(4.5);
    }
  });
});
