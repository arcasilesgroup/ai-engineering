// The README's images: every one it references exists, every file in the folder is
// referenced, and the words the README repeats from a figure match the figure.
import { describe, expect, test } from "bun:test";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { BUTTONS, buttonFile, CARDS, cardFile, HEADINGS, headingFile, HERO, heroFile, OUT_DIR, renderedFiles, SKILL_GROUPS, skillsGridAlt, skillsGridFile, THEMES } from "../scripts/readme-assets.ts";
import { DIAGRAM_VARS, FIGURES, figureFile, figureSvg } from "../scripts/readme-figures.ts";

const ROOT = resolve(import.meta.dir, "..");
const README = readFileSync(join(ROOT, "README.md"), "utf8");
const STILLS = ["deny-no-verify.webp", "deny-silence.webp", "rewrite-test.webp", "receipt.webp"];

const referenced = (): string[] => [...README.matchAll(/(?:src|srcset)="(\.github\/assets\/[^"#]+)/g)].map((match) => match[1] as string);

function altFor(file: string): string {
  const tag = (README.match(/<img\b[^>]*>/g) ?? []).find((entry) => entry.includes(`src=".github/assets/readme/${file}"`));
  const alt = tag?.match(/\balt="([^"]*)"/)?.[1];
  expect(alt, `alt attribute for ${file}`).toBeDefined();
  return alt as string;
}

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
    const htmlHosts = [...README.matchAll(/\b(?:src|srcset)="([^"]+)"/g)].flatMap((match) =>
      [...(match[1] as string).matchAll(/https?:\/\/([^/\s,]+)/g)].map((url) => url[1] as string),
    );
    const markdownHosts = [...README.matchAll(/!\[[^\]]*\]\(https?:\/\/([^/\s)]+)/g)].map((match) => match[1] as string);
    expect([...new Set([...htmlHosts, ...markdownHosts])]).toEqual(["img.shields.io"]);
  });

  test("every image carries alt text", () => {
    for (const tag of README.match(/<img\b[^>]*>/g) ?? []) expect(tag, tag).toMatch(/\balt="[^"]+"/);
  });
});

describe("README repeats the assets' words", () => {
  test("each heading's text is the alt text of its image", () => {
    for (const heading of HEADINGS) expect(altFor(headingFile(heading.slug, "light"))).toBe(heading.text);
  });

  test("each button's text is the alt text of its image", () => {
    for (const button of BUTTONS) expect(altFor(buttonFile(button.slug, "light"))).toBe(button.text);
  });

  test("each figure's alt text, caption and text version are in the README", () => {
    for (const figure of FIGURES) {
      expect(altFor(figureFile(figure, "light")), `alt of figure ${figure.n}`).toBe(figure.alt);
      expect(README, `caption of figure ${figure.n}`).toContain(figure.caption.replace(/^Figure (\d)\./, "<b>Figure $1.</b>"));
      expect(README, `text version of figure ${figure.n}`).toContain(`<summary>Text version of figure ${figure.n}</summary>`);
      figure.textVersion.forEach((step, index) => expect(README, `step ${index + 1} of figure ${figure.n}`).toContain(`${index + 1}. ${step}`));
    }
  });

  test("each card's chip, title, bullets and closing line are in its alt text", () => {
    for (const card of CARDS) {
      const alt = altFor(cardFile(card.slug, "light"));
      expect(alt.toLowerCase(), `chip of ${card.slug}`).toContain(card.chip.toLowerCase());
      expect(alt, `title of ${card.slug}`).toContain(card.title);
      for (const bullet of card.bullets) expect(alt, `bullet of ${card.slug}`).toContain(bullet.replaceAll("`", ""));
      expect(alt, `closing of ${card.slug}`).toContain(card.closing);
    }
  });

  test("the hero's alt text is the wordmark and the claim, word for word", () => {
    expect(altFor(heroFile("light"))).toBe(`${HERO.eyebrow}. ${HERO.claim}`);
  });

  test("the skills grid names exactly the skills in skills/, once each, and its alt text lists them", () => {
    const onDisk = readdirSync(join(ROOT, "skills")).filter((name) => existsSync(join(ROOT, "skills", name, "SKILL.md"))).sort();
    expect(SKILL_GROUPS.flatMap((group) => group.skills).sort()).toEqual(onDisk);
    expect(altFor(skillsGridFile("light"))).toBe(skillsGridAlt());
    expect(README).toContain(`${onDisk.length} skills, grouped by job.`);
  });

  test("the README's figures are numbered in the order a reader meets them", () => {
    const seen = [...README.matchAll(/<sub><b>Figure (\d)\.<\/b>/g)].map((match) => Number(match[1]));
    expect(seen).toEqual(FIGURES.map((figure) => figure.n).sort((left, right) => left - right));
  });
});

describe("the figures stay legible in both modes", () => {
  test("text and node borders clear their contrast floors on the card and the node", () => {
    for (const mode of ["dark", "light"] as const) {
      const vars = DIAGRAM_VARS[mode];
      for (const surface of ["--surface", "--surface-2"]) {
        for (const text of ["--text", "--dim", "--comment", "--accent", "--accent-dim", "--warn", "--bad", "--ok"]) {
          expect(contrast(vars[text] as string, vars[surface] as string), `${mode} ${text} on ${surface}`).toBeGreaterThanOrEqual(4.5);
        }
      }
      expect(contrast(vars["--line-strong"] as string, vars["--surface-2"] as string), `${mode} border`).toBeGreaterThanOrEqual(3);
    }
  });

  test("every edge leaves and lands at the middle of a node's side, so a fan shares one anchor", () => {
    const middles = (svg: string): string[] =>
      [...svg.matchAll(/<g class="dg-node[^"]*"><rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"/g)].flatMap((match) => {
        const [x, y, width, height] = match.slice(1, 5).map(Number) as [number, number, number, number];
        return [`${x} ${y + height / 2}`, `${x + width} ${y + height / 2}`, `${x + width / 2} ${y}`, `${x + width / 2} ${y + height}`];
      });
    for (const figure of FIGURES) {
      const svg = figureSvg(figure);
      const anchors = new Set(middles(svg));
      const curves = [...svg.matchAll(/class="dg-edge[^"]*" d="M([\d.]+) ([\d.]+) C([\d.]+) ([\d.]+) [\d.]+ [\d.]+ ([\d.]+) ([\d.]+)"/g)];
      for (const [, x1, y1, , controlY, stopX, stopY] of curves) {
        expect(anchors.has(`${x1} ${y1}`), `figure ${figure.n}: edge leaves ${x1},${y1}`).toBe(true);
        // A horizontal edge leaves flat, so its first control point keeps the start's y.
        const isHorizontal = controlY === y1;
        const tip = isHorizontal ? `${Number(stopX) + 8} ${stopY}` : `${stopX} ${Number(stopY) + (Number(stopY) > Number(y1) ? 8 : -8)}`;
        expect(anchors.has(tip), `figure ${figure.n}: edge lands at ${tip}`).toBe(true);
      }
    }
  });

  test("hero, heading, button and card text clear their contrast floors", () => {
    for (const mode of ["dark", "light"] as const) {
      const theme = THEMES[mode];
      for (const text of [theme.ink, theme.muted, theme.accent]) expect(contrast(text, theme.field), `${mode} ${text} on field`).toBeGreaterThanOrEqual(4.5);
      for (const text of [theme.ink, theme.muted, theme.badText, theme.goodText]) expect(contrast(text, theme.raised), `${mode} ${text} on card`).toBeGreaterThanOrEqual(4.5);
      expect(contrast(theme.buttonInk, theme.fill), `${mode} button text on fill`).toBeGreaterThanOrEqual(4.5);
      expect(contrast(theme.border, theme.field), `${mode} outline button border on field`).toBeGreaterThanOrEqual(3);
    }
  });
});
