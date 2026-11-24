// scripts/readme-badges.ts — the README's badge row, drawn here instead of fetched from shields.io.
//
// GitHub proxies every remote README image through camo, which answers 504 now and then, and a page
// that argues "nothing leaves your machine" cannot show broken boxes. Each badge is a small SVG
// committed beside the other README images. Its value is read from the repository at render time,
// and the render throws when the repository disagrees with what the badge would say.
//
// Badges for facts the repository cannot prove were dropped: the CI status and the SonarCloud
// coverage are live third-party numbers, and a frozen picture of them would go stale and lie.

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { colour, type Mode } from "./readme-figures.ts";

const ROOT = join(import.meta.dir, "..");
const readRoot = (file: string): string => readFileSync(join(ROOT, file), "utf8");

type Package = { name: string; version: string; license: string };
const readPackage = (): Package => JSON.parse(readRoot("package.json")) as Package;

/** The licence named by LICENSE, as an SPDX id; unknown text is an error rather than a guess. */
function licenceFromFile(): string {
  const text = readRoot("LICENSE");
  if (/Apache License\s+Version 2\.0/.test(text)) return "Apache-2.0";
  throw new Error("LICENSE is not a licence the badge script can name; teach scripts/readme-badges.ts about it");
}

export type Badge = { slug: string; label: string; value: string; href: string; alt: string };

/** The badges in README order. Each value comes from package.json or LICENSE, never typed here. */
export function badges(): Badge[] {
  const { name, version, license } = readPackage();
  const licenceFile = licenceFromFile();
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
const radius = (): number => {
  const { radius: steps } = JSON.parse(readRoot("brand/tokens.json")) as { radius: Record<string, unknown> & { map: Record<string, string> } };
  return Number.parseInt(steps[steps.map.control as string] as string, 10);
};

const escapeXml = (text: string): string => text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

export function badgeSvg(badge: Badge, mode: Mode): string {
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
<clipPath id="r"><rect width="${width}" height="${HEIGHT}" rx="${radius()}"/></clipPath>
<g clip-path="url(#r)"><rect width="${labelWidth}" height="${HEIGHT}" fill="${palette.label}"/><rect x="${labelWidth}" width="${width - labelWidth}" height="${HEIGHT}" fill="${palette.value}"/></g>
${text(PAD, labelText, palette.labelInk, badge.label)}
${text(labelWidth + PAD, valueText, palette.valueInk, badge.value)}
</svg>
`;
}
