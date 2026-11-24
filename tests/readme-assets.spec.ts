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
  loadQuickstartFacts,
  OUT_DIR,
  QUICKSTART_STORYBOARD,
  quickstartPosterAlt,
  quickstartPosterFile,
  quickstartStoryboardAlt,
  quickstartStoryboardFile,
  receiptFilename,
  receiptsLedgerAlt,
  receiptsLedgerFile,
  renderedFiles,
  SAMPLE_RECEIPTS,
  SKILL_GROUPS,
  skillsGridAlt,
  skillsGridFile,
  STORYBOARD_WIDTH,
  THEMES,
  verifyGuardLane,
  verifyQuickstartDeny,
} from "../scripts/readme-assets.ts";
import { TABLE } from "../src/chain/mod.ts";
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

/** Decode canvas pixel dimensions directly from a WebP VP8L or VP8X header. */
function webpDimensions(bytes: Buffer): { width: number; height: number } {
  expect(bytes.toString("ascii", 0, 4), "RIFF header").toBe("RIFF");
  expect(bytes.toString("ascii", 8, 12), "WEBP signature").toBe("WEBP");
  const chunk = bytes.toString("ascii", 12, 16);
  if (chunk === "VP8L") {
    expect(bytes[20], "VP8L signature byte").toBe(0x2f);
    const bits = bytes.readUInt32LE(21);
    return { width: (bits & 0x3fff) + 1, height: ((bits >> 14) & 0x3fff) + 1 };
  }
  if (chunk === "VP8X") {
    const width = (bytes[24]! | (bytes[25]! << 8) | (bytes[26]! << 16)) + 1;
    const height = (bytes[27]! | (bytes[28]! << 8) | (bytes[29]! << 16)) + 1;
    return { width, height };
  }
  throw new Error(`unexpected WebP chunk "${chunk}"`);
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

/** Minimal ISO BMFF (MP4) box reader so tests verify real video metadata without shelling out. */
type Mp4Box = { type: string; offset: number; payloadStart: number; end: number };

function mp4Children(buf: Buffer, start: number, end: number): Mp4Box[] {
  const boxes: Mp4Box[] = [];
  let cursor = start;
  while (cursor + 8 <= end) {
    let size = buf.readUInt32BE(cursor);
    const type = buf.toString("ascii", cursor + 4, cursor + 8);
    let header = 8;
    if (size === 1) {
      if (cursor + 16 > end) break;
      size = Number(buf.readBigUInt64BE(cursor + 8));
      header = 16;
    } else if (size === 0) {
      size = end - cursor;
    }
    if (size < header || cursor + size > end) break;
    boxes.push({ type, offset: cursor, payloadStart: cursor + header, end: cursor + size });
    cursor += size;
  }
  return boxes;
}

function inspectMp4(buf: Buffer): {
  topBoxes: string[];
  durationSeconds: number;
  width: number;
  height: number;
  handlers: string[];
  codecs: string[];
} {
  const top = mp4Children(buf, 0, buf.length);
  const moov = top.find((box) => box.type === "moov");
  expect(moov, "MP4 moov atom").toBeDefined();
  const moovChildren = mp4Children(buf, (moov as Mp4Box).payloadStart, (moov as Mp4Box).end);

  const mvhd = moovChildren.find((box) => box.type === "mvhd");
  expect(mvhd, "MP4 mvhd atom").toBeDefined();
  const mvhdStart = (mvhd as Mp4Box).payloadStart;
  const mvhdVer = buf[mvhdStart] ?? 0;
  const timescale = mvhdVer === 1 ? buf.readUInt32BE(mvhdStart + 20) : buf.readUInt32BE(mvhdStart + 12);
  const rawDuration = mvhdVer === 1 ? Number(buf.readBigUInt64BE(mvhdStart + 24)) : buf.readUInt32BE(mvhdStart + 16);

  let width = 0;
  let height = 0;
  const handlers: string[] = [];
  const codecs: string[] = [];

  for (const trak of moovChildren.filter((box) => box.type === "trak")) {
    const trakChildren = mp4Children(buf, trak.payloadStart, trak.end);
    const tkhd = trakChildren.find((box) => box.type === "tkhd");
    if (tkhd) {
      const tkhdVer = buf[tkhd.payloadStart] ?? 0;
      const wOff = tkhdVer === 1 ? 88 : 76;
      const trackW = buf.readUInt32BE(tkhd.payloadStart + wOff) / 65536;
      const trackH = buf.readUInt32BE(tkhd.payloadStart + wOff + 4) / 65536;
      if (trackW > 0 && trackH > 0) {
        width = trackW;
        height = trackH;
      }
    }
    const mdia = trakChildren.find((box) => box.type === "mdia");
    if (!mdia) continue;
    const mdiaChildren = mp4Children(buf, mdia.payloadStart, mdia.end);
    const hdlr = mdiaChildren.find((box) => box.type === "hdlr");
    if (hdlr) handlers.push(buf.toString("ascii", hdlr.payloadStart + 8, hdlr.payloadStart + 12));
    const minf = mdiaChildren.find((box) => box.type === "minf");
    const stbl = minf ? mp4Children(buf, minf.payloadStart, minf.end).find((box) => box.type === "stbl") : undefined;
    const stsd = stbl ? mp4Children(buf, stbl.payloadStart, stbl.end).find((box) => box.type === "stsd") : undefined;
    if (stsd && stsd.payloadStart + 16 <= stsd.end) {
      codecs.push(buf.toString("ascii", stsd.payloadStart + 12, stsd.payloadStart + 16));
    }
  }

  return {
    topBoxes: top.map((box) => box.type),
    durationSeconds: rawDuration / timescale,
    width,
    height,
    handlers,
    codecs,
  };
}

  test("the quickstart still and the walkthrough under it share one section: the still leads, the video follows, and no autoplaying loop remains", () => {
    // The still: both themes, matching 2x dimensions, and the live denial verified rather than typed.
    expect(verifyQuickstartDeny().length).toBeGreaterThan(0);
    const stillDark = quickstartStoryboardFile("dark");
    const stillLight = quickstartStoryboardFile("light");
    expect(README).toContain(`srcset=".github/assets/readme/${stillDark}"`);
    expect(README).toContain(`src=".github/assets/readme/${stillLight}"`);
    expect(altFor(stillLight)).toBe(quickstartStoryboardAlt());
    for (const spoken of [
      QUICKSTART_STORYBOARD.version,
      QUICKSTART_STORYBOARD.init.command,
      QUICKSTART_STORYBOARD.doctor.command,
      QUICKSTART_STORYBOARD.work.command,
      QUICKSTART_STORYBOARD.config.command,
      QUICKSTART_STORYBOARD.doctor.denyCommand,
      QUICKSTART_STORYBOARD.doctor.denyPill,
      QUICKSTART_STORYBOARD.doctor.verdict,
    ]) {
      expect(altFor(stillLight), `alt text names ${spoken}`).toContain(spoken);
    }

    const stillDarkDims = webpDimensions(readFileSync(join(OUT_DIR, stillDark)));
    const stillLightDims = webpDimensions(readFileSync(join(OUT_DIR, stillLight)));
    expect(stillDarkDims.width, "dark storyboard width (2x CSS canvas)").toBe(STORYBOARD_WIDTH * 2);
    expect(stillLightDims, "light storyboard matches dark dimensions").toEqual(stillDarkDims);
    expect(stillDarkDims.height, "compact landscape-ish proportions").toBeGreaterThan(800);
    expect(stillDarkDims.height, "fits cleanly without vertical bloat").toBeLessThan(1600);

    // No autoplaying GIF loop remains anywhere in the assets or the README (WCAG 2.2.2).
    const facts = loadQuickstartFacts();
    const assetsDir = join(ROOT, ".github", "assets");
    const tapesDir = join(assetsDir, "tapes");
    expect(readdirSync(assetsDir).filter((name) => name.endsWith(".gif"))).toEqual([]);
    expect(README).not.toContain("quickstart-loop.gif");
    expect(README).not.toContain("quickstart-loop.tape");
    expect(README).not.toContain("quickstart-preview-");
    expect(existsSync(join(tapesDir, "quickstart-loop.tape"))).toBe(false);

    // Deterministic VHS tape, ffmpeg script, and captured facts live beside each other.
    for (const file of ["quickstart.tape", "quickstart-video.sh", "quickstart-facts.json"]) {
      expect(existsSync(join(tapesDir, file)), `tapes/${file}`).toBe(true);
    }

    // The video follows the still: its dark/light poster sits under the storyboard, inside a link
    // to the MP4, so it never autoplays and the still is what a reader sees first.
    expect(README).toMatch(/<a href="\.github\/assets\/quickstart\.mp4">\s*<picture>[\s\S]*?quickstart-poster-dark\.webp[\s\S]*?quickstart-poster-light\.webp[\s\S]*?<\/picture>\s*<\/a>/);
    expect(altFor(quickstartPosterFile("light"))).toBe(quickstartPosterAlt());
    expect(README).toContain(quickstartPosterFile("dark"));
    const stillTagAt = README.indexOf(`src=".github/assets/readme/${stillLight}"`);
    const posterLinkAt = README.indexOf('<a href=".github/assets/quickstart.mp4">');
    expect(stillTagAt, "the still's img tag comes before the video link").toBeLessThan(posterLinkAt);

    // Real MP4 metadata: 16:9 H.264, faststart (moov before mdat), silent (no audio track), sensible size, human-paced duration.
    const mp4Bytes = readFileSync(join(assetsDir, "quickstart.mp4"));
    expect(mp4Bytes.length, "MP4 size stays sensible for a repository (<= 4 MiB)").toBeLessThanOrEqual(4 * 1024 * 1024);
    const meta = inspectMp4(mp4Bytes);
    expect(meta.topBoxes[0]).toBe("ftyp");
    expect(meta.topBoxes.indexOf("moov"), "faststart puts moov before mdat").toBeLessThan(meta.topBoxes.indexOf("mdat"));
    expect(meta.width).toBe(1920);
    expect(meta.height).toBe(1080);
    expect(meta.handlers).toEqual(["vide"]);
    expect(meta.codecs).toContain("avc1");
    expect(Math.abs(meta.durationSeconds - facts.durationSeconds), "facts duration matches MP4").toBeLessThan(0.25);
    expect(meta.durationSeconds, "paced for human reading, not a rushed < 5 s loop").toBeGreaterThanOrEqual(30);

    // One transcript serves both assets: it quotes the still's four panels and the recording's own run.
    expect(README).toContain("<summary>Text transcript of ai-eng init, doctor, work and config</summary>");
    expect(README).toContain(QUICKSTART_STORYBOARD.doctor.denyPill);
    expect(README).toContain(QUICKSTART_STORYBOARD.work.header);
    expect(README).toContain(QUICKSTART_STORYBOARD.config.command);
    for (const expected of [
      `ai-eng ${facts.version}`,
      `${facts.durationSeconds.toFixed(1)} s MP4`,
      "ai-eng init --surface claude-code --yes",
      "ai-eng doctor",
      `DENY in ${facts.denyMs}ms`,
      `p50 ${facts.receiptP50Ms}ms · p95 ${facts.receiptP95Ms}ms`,
      `${facts.checksTotal} checks: ${facts.checksOk} OK · ${facts.checksWarn} WARN · ${facts.checksFail} FAIL`,
      "Chain verified.",
      "ai-eng work",
      `active lanes: ${facts.activeLanes}/${facts.maxLanes}`,
      "ai-eng config --add cursor",
      `2 enabled: ${facts.surfacesAfterAdd.join(", ")}`,
      `${facts.mirrorTargets} targets`,
    ]) {
      expect(README, `README quotes recorded fact "${expected}"`).toContain(expected);
    }
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
        expect(contrast(text, theme.termWell), `${mode} ${text} on termWell`).toBeGreaterThanOrEqual(4.5);
        expect(contrast(text, theme.denyWell), `${mode} ${text} on denyWell`).toBeGreaterThanOrEqual(4.5);
      }
      for (const text of [theme.ink, theme.panelMuted, theme.goodText, theme.badText]) {
        expect(contrast(text, theme.chrome), `${mode} ${text} on chrome`).toBeGreaterThanOrEqual(4.5);
      }
      expect(contrast(theme.buttonInk, theme.fill), `${mode} button text on fill`).toBeGreaterThanOrEqual(4.5);
      expect(contrast(theme.border, theme.field), `${mode} outline button border on field`).toBeGreaterThanOrEqual(3);
      expect(contrast(theme.warn, theme.field), `${mode} caveat dashed border on field`).toBeGreaterThanOrEqual(3);
    }
  });
});
