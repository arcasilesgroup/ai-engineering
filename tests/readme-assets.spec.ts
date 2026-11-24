// The README's images: every one it references exists, every file in the folder is
// referenced, and the words the README repeats from a figure match the figure.
import { describe, expect, test } from "bun:test";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import {
  BUTTONS,
  buttonFile,
  CARDS,
  cardFile,
  GUARD_LANES,
  guardCountFor,
  guardsRefusedAlt,
  guardsRefusedFile,
  HEADINGS,
  headingFile,
  HERO,
  heroFile,
  OUT_DIR,
  receiptFilename,
  receiptsLedgerAlt,
  receiptsLedgerFile,
  renderedFiles,
  SAMPLE_RECEIPTS,
  SKILL_GROUPS,
  skillsGridAlt,
  skillsGridFile,
  THEMES,
  verifyGuardLane,
} from "../scripts/readme-assets.ts";
import { TABLE } from "../src/chain/mod.ts";
import { badgeFile, badges, badgeSvg } from "../scripts/readme-badges.ts";
import { DIAGRAM_VARS, FIGURES, figureFile, figureSvg } from "../scripts/readme-figures.ts";

const ROOT = resolve(import.meta.dir, "..");
const README = readFileSync(join(ROOT, "README.md"), "utf8");

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
    expect(onDisk).toEqual(renderedFiles().sort());
    const used = new Set(referenced().map((path) => path.split("/").pop()));
    expect(onDisk.filter((file) => !used.has(file))).toEqual([]);
  });

  test("the README uses no absolute local path and loads no third-party image host", () => {
    expect(README).not.toMatch(/(?:src|href|srcset)="(?:\/Users|\/home|[A-Za-z]:\\)/);
    const htmlHosts = [...README.matchAll(/\b(?:src|srcset)="([^"]+)"/g)].flatMap((match) =>
      [...(match[1] as string).matchAll(/https?:\/\/([^/\s,]+)/g)].map((url) => url[1] as string),
    );
    const markdownHosts = [...README.matchAll(/!\[[^\]]*\]\(https?:\/\/([^/\s)]+)/g)].map((match) => match[1] as string);
    expect([...new Set([...htmlHosts, ...markdownHosts])]).toEqual([]);
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

  test("each badge is a committed SVG whose alt text and link match the repository, in both themes", () => {
    const { version, license, name } = JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8")) as { version: string; license: string; name: string };
    const row = badges();
    expect(row.map((badge) => badge.value)).toEqual([version, name, license]);
    for (const badge of row) {
      expect(altFor(badgeFile(badge.slug, "light")), badge.slug).toBe(badge.alt);
      expect(README, `link of ${badge.slug}`).toContain(`<a href="${badge.href}"><picture><source media="(prefers-color-scheme: dark)" srcset=".github/assets/readme/${badgeFile(badge.slug, "dark")}">`);
      for (const mode of ["dark", "light"] as const) {
        expect(readFileSync(join(OUT_DIR, badgeFile(badge.slug, mode)), "utf8"), `${badge.slug} ${mode} is stale; run bun scripts/readme-assets.ts badge-`).toBe(badgeSvg(badge, mode));
      }
    }
  });

  test("the hero's alt text is the wordmark and the claim, word for word", () => {
    expect(altFor(heroFile("light"))).toBe(`${HERO.wordmark}. ${HERO.claim}`);
  });

  test("the README has one top-level h1 wrapping the hero and h3 stat cells with no h1 inside table cells", () => {
    const h1Tags = README.match(/<h1\b[^>]*>/g) ?? [];
    expect(h1Tags.length).toBe(1);
    expect(README).toMatch(/<h1><picture>[\s\S]*?hero-light\.webp/);
    expect(README).not.toMatch(/<td\b[^>]*>(?:(?!<\/td>)[\s\S])*?<h1\b/i);
    for (const metric of ["2,600+", "12", "under 3 ms", "7 of 10"]) {
      expect(README, `stat cell ${metric}`).toContain(`<td align="center"><h3>${metric}</h3>`);
    }
  });

  test("the quickstart demo embeds the finite recording directly and carries a faithful transcript", () => {
    const gifTag = (README.match(/<img\b[^>]*>/g) ?? []).find((entry) => entry.includes('src=".github/assets/quickstart.gif"'));
    expect(gifTag, "inline quickstart.gif img tag").toBeDefined();
    const gifAlt = gifTag?.match(/\balt="([^"]*)"/)?.[1] ?? "";
    expect(gifAlt).toContain("ai-eng init");
    expect(gifAlt).toContain("ai-eng doctor");
    expect(gifAlt).toContain("3.3.1");
    expect(README).not.toContain("quickstart-preview-");
    expect(README).toContain("<summary>Text transcript of ai-eng init and ai-eng doctor</summary>");
    expect(README).toContain("DENY in 7ms");
    expect(README).not.toContain("~6 ms");
    const gifBytes = readFileSync(join(ROOT, ".github", "assets", "quickstart.gif"));
    expect(gifBytes.includes(Buffer.from("NETSCAPE2.0"))).toBe(false);
  });

  test("the guards panel matches live no-verify and wrap verdicts and carries its claim in alt text", () => {
    expect(GUARD_LANES.some((lane) => lane.kind === "bash-deny")).toBe(true);
    expect(GUARD_LANES.some((lane) => lane.kind === "edit-deny")).toBe(true);
    expect(GUARD_LANES.some((lane) => lane.kind === "bash-rewrite" && lane.verdict === "rewrite")).toBe(true);
    for (const lane of GUARD_LANES) {
      expect(verifyGuardLane(lane).length).toBeGreaterThan(0);
    }
    expect(altFor(guardsRefusedFile("light"))).toBe(guardsRefusedAlt());
    expect(README).toContain(guardsRefusedFile("dark"));
    expect(README).toContain('href="src/guards/no-verify.ts"');
    expect(README).toContain('href="src/guards/wrap.ts"');
    expect(README).not.toMatch(/<a\s+href="src\/guards\/(?:no-verify|wrap)\.ts"><picture>/);
    expect(README).not.toContain("payload-bash-");
    expect(README).not.toContain("payload-edit-");
  });

  test("the receipts ledger panel matches real receipt filenames and per-tool guard counts, keeps the log-not-proof caveat, and carries its claim in alt text", () => {
    expect(SAMPLE_RECEIPTS.length).toBeGreaterThanOrEqual(2);
    const receiptNamePattern = /^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z-[A-Za-z0-9_-]+-[0-9a-f]{8}\.json$/;
    for (const receipt of SAMPLE_RECEIPTS) {
      expect(receiptFilename(receipt), `filename of ${receipt.operation_id}`).toMatch(receiptNamePattern);
      const matching = (TABLE[receipt.event] ?? []).filter((row) => row.matcher.test(receipt.tool)).map((row) => row.name);
      expect(guardCountFor(receipt.event, receipt.tool), `guard count for ${receipt.tool}`).toBe(matching.length);
      expect(receipt.guards.ran).toEqual(matching.slice(0, receipt.guards.ran.length));
    }
    expect(guardCountFor("PreToolUse", "Edit")).toBe(5);
    expect(guardCountFor("PreToolUse", "Bash")).toBe(9);
    expect(altFor(receiptsLedgerFile("light"))).toBe(receiptsLedgerAlt());
    expect(README).toContain(receiptsLedgerFile("dark"));
    expect(README).not.toMatch(/<a\s+href="src\/receipts\.ts"><picture>/);
    expect(altFor(receiptsLedgerFile("light")).toLowerCase()).toContain("a receipt is a log, not proof");
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

  test("hero, heading, button, card and showcase panel text clear their contrast floors", () => {
    for (const mode of ["dark", "light"] as const) {
      const theme = THEMES[mode];
      for (const text of [theme.ink, theme.muted, theme.panelMuted, theme.accent, theme.badText, theme.goodText, theme.warnText]) {
        expect(contrast(text, theme.field), `${mode} ${text} on field`).toBeGreaterThanOrEqual(4.5);
        expect(contrast(text, theme.well), `${mode} ${text} on well`).toBeGreaterThanOrEqual(4.5);
      }
      for (const text of [theme.ink, theme.muted, theme.badText, theme.goodText, theme.warnText]) {
        expect(contrast(text, theme.raised), `${mode} ${text} on card`).toBeGreaterThanOrEqual(4.5);
      }
      expect(contrast(theme.buttonInk, theme.fill), `${mode} button text on fill`).toBeGreaterThanOrEqual(4.5);
      expect(contrast(theme.border, theme.field), `${mode} outline button border on field`).toBeGreaterThanOrEqual(3);
      expect(contrast(theme.warn, theme.field), `${mode} caveat dashed border on field`).toBeGreaterThanOrEqual(3);
    }
  });
});
