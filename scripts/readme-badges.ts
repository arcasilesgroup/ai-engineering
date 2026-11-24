// scripts/readme-badges.ts — the README's badge row, drawn here instead of fetched from shields.io.
//
// GitHub proxies every remote README image through camo, which answers 504 now and then, and a page
// that argues "nothing leaves your machine" cannot show broken boxes. Each badge is a small SVG
// committed beside the other README images. Its value is read from the repository at render time,
// and the render throws when the repository disagrees with what the badge would say.
//
// Badges for facts the repository cannot prove were dropped: the CI status and the SonarCloud
// coverage are live third-party numbers, and a frozen picture of them would go stale and lie.

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";

const ROOT = join(import.meta.dir, "..");
const MODES = ["dark", "light"] as const;
export type Mode = (typeof MODES)[number];

const readRoot = (root: string, file: string): string => readFileSync(join(root, file), "utf8");

type Families = Record<string, string | Record<string, string>>;
type Tokens = { families: Families; radius: Record<string, unknown> & { map: Record<string, string> } };

const readTokens = (root: string): Tokens => JSON.parse(readRoot(root, "brand/tokens.json")) as Tokens;

function tokenColour(families: Families, path: string): string {
  const value = path.split(".").reduce<unknown>((node, key) => (node as Record<string, unknown> | undefined)?.[key], families);
  if (typeof value !== "string") throw new Error(`brand/tokens.json has no colour "${path}"`);
  return value;
}

function controlRadius(tokens: Tokens): number {
  const step = tokens.radius.map.control;
  const raw = step ? tokens.radius[step] : undefined;
  const parsed = typeof raw === "string" ? Number.parseInt(raw, 10) : Number.NaN;
  if (Number.isNaN(parsed)) throw new Error("brand/tokens.json has no radius.map.control step");
  return parsed;
}

type Package = { name: string; version: string; license: string };
const readPackage = (root: string): Package => JSON.parse(readRoot(root, "package.json")) as Package;

/** The licence named by LICENSE, as an SPDX id; unknown text is an error rather than a guess. */
function licenceFromFile(root: string): string {
  const text = readRoot(root, "LICENSE");
  if (/Apache License\s+Version 2\.0/.test(text)) return "Apache-2.0";
  throw new Error("LICENSE is not a licence the badge script can name; teach scripts/readme-badges.ts about it");
}

export type Badge = { slug: string; label: string; value: string; href: string; alt: string };

/** The badges in README order. Each value comes from package.json or LICENSE, never typed here. */
export function badges(root: string = ROOT): Badge[] {
  const { name, version, license } = readPackage(root);
  const licenceFile = licenceFromFile(root);
  if (license !== licenceFile) throw new Error(`package.json says ${license} but LICENSE is ${licenceFile}`);
  return [
    { slug: "version", label: "version", value: version, href: "https://github.com/arcasilesgroup/ai-engineering/releases/latest", alt: `version ${version}` },
    { slug: "npm", label: "npm", value: name, href: `https://www.npmjs.com/package/${name}`, alt: `npm package ${name}` },
    { slug: "license", label: "license", value: licenceFile, href: "LICENSE", alt: `license ${licenceFile}` },
  ];
}

export const badgeFile = (slug: string, mode: Mode): string => `badge-${slug}-${mode}.svg`;

// Same height as shields.io flat-square, so the row does not jump. Radius is the brand's `control` step.
const HEIGHT = 20;
const FONT_PX = 11;
const PAD = 8;
// An SVG used as <img> cannot load web fonts, so the width is fixed with textLength instead of measured.
const CHAR_PX = 6.6;
const FONT = "Verdana, 'DejaVu Sans', sans-serif";

const escapeXml = (text: string): string => text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

export function badgeSvg(badge: Badge, mode: Mode, root: string = ROOT): string {
  const tokens = readTokens(root);
  const colour = (path: string): string => tokenColour(tokens.families, path);
  const palette =
    mode === "dark"
      ? { label: colour("gray.dark4"), labelInk: colour("white"), value: colour("green.base"), valueInk: colour("black") }
      : { label: colour("black"), labelInk: colour("white"), value: colour("green.dark2"), valueInk: colour("white") };
  const labelText = Math.ceil(badge.label.length * CHAR_PX);
  const valueText = Math.ceil(badge.value.length * CHAR_PX);
  const labelWidth = labelText + PAD * 2;
  const width = labelWidth + valueText + PAD * 2;
  const text = (x: number, length: number, ink: string, content: string): string =>
    `<text x="${x}" y="14" fill="${ink}" font-family="${FONT}" font-size="${FONT_PX}" textLength="${length}" lengthAdjust="spacingAndGlyphs">${escapeXml(content)}</text>`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${HEIGHT}" viewBox="0 0 ${width} ${HEIGHT}" role="img" aria-label="${escapeXml(badge.alt)}">
<title>${escapeXml(badge.alt)}</title>
<clipPath id="r"><rect width="${width}" height="${HEIGHT}" rx="${controlRadius(tokens)}"/></clipPath>
<g clip-path="url(#r)"><rect width="${labelWidth}" height="${HEIGHT}" fill="${palette.label}"/><rect x="${labelWidth}" width="${width - labelWidth}" height="${HEIGHT}" fill="${palette.value}"/></g>
${text(PAD, labelText, palette.labelInk, badge.label)}
${text(labelWidth + PAD, valueText, palette.valueInk, badge.value)}
</svg>
`;
}

export function syncReadmeBadgeAlts(readme: string, row: readonly Badge[]): string {
  let updated = readme;
  for (const badge of row) {
    const src = `src=".github/assets/readme/${badgeFile(badge.slug, "light")}"`;
    let isMatched = false;
    updated = updated.replace(/<img\b[^>]*>/g, (tag) => {
      if (!tag.includes(src)) return tag;
      if (!/\balt="[^"]*"/.test(tag)) {
        throw new Error(`README.md badge <img> for ${badge.slug} has no alt attribute to rewrite`);
      }
      isMatched = true;
      return tag.replace(/\balt="[^"]*"/, () => `alt="${escapeXml(badge.alt)}"`);
    });
    if (!isMatched) {
      throw new Error(`README.md has no badge <img> referencing ${src}`);
    }
  }
  return updated;
}

export function syncReadmeBadges(root: string = ROOT): string[] {
  const row = badges(root);
  const outDir = join(root, ".github", "assets", "readme");
  mkdirSync(outDir, { recursive: true });
  const changed: string[] = [];
  for (const badge of row) {
    for (const mode of MODES) {
      const file = badgeFile(badge.slug, mode);
      const target = join(outDir, file);
      const next = badgeSvg(badge, mode, root);
      const previous = existsSync(target) ? readFileSync(target, "utf8") : undefined;
      if (previous === next) continue;
      writeFileSync(target, next);
      changed.push(`.github/assets/readme/${file}`);
    }
  }
  const readmePath = join(root, "README.md");
  const before = readFileSync(readmePath, "utf8");
  const after = syncReadmeBadgeAlts(before, row);
  if (after !== before) {
    writeFileSync(readmePath, after);
    changed.push("README.md");
  }
  return changed;
}

if (import.meta.main) {
  try {
    const changed = syncReadmeBadges(resolve(process.argv[2] ?? ROOT));
    for (const file of changed) process.stdout.write(`readme-badges: updated ${file}\n`);
    if (changed.length === 0) process.stdout.write("readme-badges: badges and README alt text already match package.json\n");
  } catch (error) {
    process.stderr.write(`readme-badges: ${error instanceof Error ? error.message : String(error)}\n`);
    process.exit(2);
  }
}
