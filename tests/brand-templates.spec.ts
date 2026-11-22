/**
 * Page templates must keep one copy of the brand, or every artifact drifts on its own.
 *
 * The markers are the only bytes gen may replace. A splice that refuses has to leave
 * the file on disk alone — a half-written template would be a second, quieter drift.
 *
 * `spliceBrandRegions(html, css, js, file)` is pure. The file argument is only there
 * so the refusal can name the template: the bytes do not know which file they came from.
 * `templateDrift(root)` globs `templates/*.html.tpl` under that root (the repo when
 * omitted) and returns the relative paths whose regions differ.
 * `rewriteBrandTemplate` is the write gen uses: splice first, and do not touch the
 * file when the splice throws.
 */
import { describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import * as brandModule from "../scripts/brand.ts";

type SpliceBrandRegions = (html: string, css: string, js: string, file: string) => string | Promise<string>;
type TemplateDrift = (root?: string) => readonly string[] | Promise<readonly string[]>;
type RewriteBrandTemplate = (templatePath: string, css: string, js: string) => void | Promise<void>;

function exportedBrandFunction(name: "spliceBrandRegions" | "templateDrift" | "rewriteBrandTemplate"): unknown {
  const brandExport = (brandModule as Record<string, unknown>)[name];
  if (typeof brandExport !== "function") {
    throw new Error(`scripts/brand.ts does not export ${name}`);
  }
  return brandExport;
}

function spliceBrandRegions(html: string, css: string, js: string, file: string): Promise<string> {
  const splice = exportedBrandFunction("spliceBrandRegions") as SpliceBrandRegions;
  return Promise.resolve(splice(html, css, js, file));
}

function templateDrift(root?: string): Promise<readonly string[]> {
  const drift = exportedBrandFunction("templateDrift") as TemplateDrift;
  return Promise.resolve(drift(root));
}

function rewriteBrandTemplate(templatePath: string, css: string, js: string): Promise<void> {
  const rewrite = exportedBrandFunction("rewriteBrandTemplate") as RewriteBrandTemplate;
  return Promise.resolve(rewrite(templatePath, css, js));
}

const ROOT = join(import.meta.dir, "..");

const CSS_BEGIN = "/* brand:begin */";
const CSS_END = "/* brand:end */";
const JS_BEGIN = "<!-- brand:js:begin -->";
const JS_END = "<!-- brand:js:end -->";

/** `cmdParity` pads `ok` to the same width as `DRIFT`, then a space, then the path. */
const BRAINSTORM_PARITY_LINE = "ok    templates/brainstorm.html.tpl";

const BEFORE_REGIONS = `<!DOCTYPE html>\n<html lang="en">\n<head>\n<title>{{title}}</title>\n<style>\n${CSS_BEGIN}`;
const BETWEEN_REGIONS = `${CSS_END}\n</style>\n</head>\n<body>\n<p>{{subtitle}}</p>\n${JS_BEGIN}`;
const AFTER_REGIONS = `${JS_END}\n<footer>{{footer}}</footer>\n</body>\n</html>\n`;
const STALE_CSS = "\n.stale{color:red}\n";
const STALE_SCRIPT = "\n<script>\nconsole.log(\"stale\");\n</script>\n";

function classicScript(source: string): string {
  return `<script>\n${source}</script>`;
}

function staleCarrier(): string {
  return BEFORE_REGIONS + STALE_CSS + BETWEEN_REGIONS + STALE_SCRIPT + AFTER_REGIONS;
}

function regionBetween(html: string, beginMarker: string, endMarker: string): string {
  const start = html.indexOf(beginMarker);
  const finish = html.indexOf(endMarker, start + beginMarker.length);
  if (start < 0 || finish < 0) {
    throw new Error(`spliced page lost ${beginMarker}`);
  }
  return html.slice(start + beginMarker.length, finish);
}

function readBrandComponent(filename: "components.css" | "components.js"): string {
  return readFileSync(join(ROOT, "brand", filename), "utf8");
}

function pageAround(styleBody: string, scriptBody: string): string {
  return `<!DOCTYPE html>\n<html lang="en">\n<head>\n<title>{{title}}</title>\n<style>\n${styleBody}\n</style>\n</head>\n<body>\n<p>{{subtitle}}</p>\n${scriptBody}\n<footer>{{footer}}</footer>\n</body>\n</html>\n`;
}

function expectMarkerRefusal(caught: unknown, message: string): void {
  if (!(caught instanceof Error)) {
    throw new Error(`expected BrandMarkerError, got ${String(caught)}`);
  }
  expect(caught.name).toBe("BrandMarkerError");
  expect(caught.message).toBe(message);
}

function assertScratchOutsideRepo(scratchPath: string): void {
  const resolved = resolve(scratchPath);
  const repo = resolve(ROOT);
  if (resolved === repo || resolved.startsWith(`${repo}/`)) {
    throw new Error(`scratch path ${resolved} is inside the repository`);
  }
}

function markedTemplatePaths(root: string): string[] {
  const templatesDir = join(root, "templates");
  return readdirSync(templatesDir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith(".html.tpl"))
    .filter((entry) => {
      const text = readFileSync(join(templatesDir, entry.name), "utf8");
      return text.includes(CSS_BEGIN) && text.includes(CSS_END) && text.includes(JS_BEGIN) && text.includes(JS_END);
    })
    .map((entry) => `templates/${entry.name}`)
    .sort();
}

function copyBrandTree(destination: string): void {
  assertScratchOutsideRepo(destination);
  const templatesDir = join(destination, "templates");
  mkdirSync(templatesDir, { recursive: true });
  mkdirSync(join(destination, "brand"), { recursive: true });
  for (const entry of readdirSync(join(ROOT, "templates"), { withFileTypes: true })) {
    if (!entry.isFile() || !entry.name.endsWith(".html.tpl")) continue;
    copyFileSync(join(ROOT, "templates", entry.name), join(templatesDir, entry.name));
  }
  copyFileSync(join(ROOT, "brand", "components.css"), join(destination, "brand", "components.css"));
  copyFileSync(join(ROOT, "brand", "components.js"), join(destination, "brand", "components.js"));
}

function flipByteInsideCssRegion(html: string, relativePath: string): string {
  const beginAt = html.indexOf(CSS_BEGIN);
  const endAt = beginAt < 0 ? -1 : html.indexOf(CSS_END, beginAt + CSS_BEGIN.length);
  if (beginAt < 0 || endAt < 0) {
    throw new Error(`${relativePath} has no css brand region`);
  }
  const regionStart = beginAt + CSS_BEGIN.length;
  if (endAt === regionStart) {
    throw new Error(`${relativePath} css brand region is empty`);
  }
  const index = regionStart + Math.floor((endAt - regionStart) / 2);
  const previous = html[index] ?? "";
  const byte = previous === "Q" ? "Z" : "Q";
  return html.slice(0, index) + byte + html.slice(index + 1);
}

function flipByteOutsideMarkers(html: string): { html: string; index: number; byte: string; previous: string } {
  const titleAt = html.indexOf("<title>");
  if (titleAt < 0) {
    throw new Error("templates/brainstorm.html.tpl has no title");
  }
  const index = titleAt + "<title>".length;
  const cssBeginAt = html.indexOf(CSS_BEGIN);
  const cssEndAt = html.indexOf(CSS_END);
  const jsBeginAt = html.indexOf(JS_BEGIN);
  const jsEndAt = html.indexOf(JS_END);
  if (cssBeginAt < 0 || cssEndAt < 0 || jsBeginAt < 0 || jsEndAt < 0) {
    throw new Error("templates/brainstorm.html.tpl is missing a brand marker pair");
  }
  const insideCss = index >= cssBeginAt && index < cssEndAt + CSS_END.length;
  const insideJs = index >= jsBeginAt && index < jsEndAt + JS_END.length;
  if (insideCss || insideJs) {
    throw new Error("the outside-marker edit landed inside a brand region");
  }
  const previous = html[index] ?? "";
  const byte = previous === "Q" ? "Z" : "Q";
  return { html: html.slice(0, index) + byte + html.slice(index + 1), index, byte, previous };
}

/** Marker-free bulk plus a css end with no begin, and a well-formed js pair. */
function carrierMissingCssBegin(bulk: string): string {
  const unmarked = bulk.replaceAll(CSS_BEGIN, "").replaceAll(CSS_END, "").replaceAll(JS_BEGIN, "").replaceAll(JS_END, "");
  return `${CSS_END}\n${unmarked}\n${JS_BEGIN}\n<script>\nkeep();\n</script>\n${JS_END}\n`;
}

async function withScratchWebDir(webDir: string, body: () => Promise<void>): Promise<void> {
  const previous = process.env["AI_ENGINEERING_WEB_DIR"];
  process.env["AI_ENGINEERING_WEB_DIR"] = webDir;
  try {
    await body();
  } finally {
    if (previous === undefined) delete process.env["AI_ENGINEERING_WEB_DIR"];
    else process.env["AI_ENGINEERING_WEB_DIR"] = previous;
  }
}

describe("spliceBrandRegions", () => {
  test("replaces the style region with brand/components.css byte for byte", async () => {
    const brandCss = readBrandComponent("components.css");
    const brandJs = readBrandComponent("components.js");
    const expected = BEFORE_REGIONS + brandCss + BETWEEN_REGIONS + classicScript(brandJs) + AFTER_REGIONS;
    expect(await spliceBrandRegions(staleCarrier(), brandCss, brandJs, "templates/fixture.html.tpl")).toBe(expected);
  });

  test("writes one classic script between the brand:js markers", async () => {
    const brandCss = readBrandComponent("components.css");
    const brandJs = readBrandComponent("components.js");
    const spliced = await spliceBrandRegions(staleCarrier(), brandCss, brandJs, "templates/fixture.html.tpl");
    expect(regionBetween(spliced, JS_BEGIN, JS_END)).toBe(classicScript(brandJs));
  });

  test("keeps bytes outside the markers, placeholders included", async () => {
    const brandCss = readBrandComponent("components.css");
    const brandJs = readBrandComponent("components.js");
    const script = classicScript(brandJs);
    const spliced = await spliceBrandRegions(staleCarrier(), brandCss, brandJs, "templates/fixture.html.tpl");
    expect(spliced.slice(0, BEFORE_REGIONS.length)).toBe(BEFORE_REGIONS);
    const betweenAt = BEFORE_REGIONS.length + brandCss.length;
    expect(spliced.slice(betweenAt, betweenAt + BETWEEN_REGIONS.length)).toBe(BETWEEN_REGIONS);
    expect(spliced.slice(betweenAt + BETWEEN_REGIONS.length + script.length)).toBe(AFTER_REGIONS);
    expect(spliced.length).toBe(BEFORE_REGIONS.length + brandCss.length + BETWEEN_REGIONS.length + script.length + AFTER_REGIONS.length);
  });

  test("splicing the committed brainstorm template is idempotent", async () => {
    const committed = readFileSync(join(ROOT, "templates", "brainstorm.html.tpl"), "utf8");
    const brandCss = readBrandComponent("components.css");
    const brandJs = readBrandComponent("components.js");
    const file = "templates/brainstorm.html.tpl";
    const once = await spliceBrandRegions(committed, brandCss, brandJs, file);
    expect(once).toBe(committed);
    expect(await spliceBrandRegions(once, brandCss, brandJs, file)).toBe(once);
  });

  test("refuses a missing, doubled or reversed marker for each pair", async () => {
    const validCss = `${CSS_BEGIN}\n.keep{}\n${CSS_END}`;
    const validJs = `${JS_BEGIN}\n<script>\nkeep();\n</script>\n${JS_END}`;
    const markerFaults = [
      {
        file: "templates/missing-css.html.tpl",
        html: pageAround(`.keep{}\n${CSS_END}`, validJs),
        message: "templates/missing-css.html.tpl: missing marker /* brand:begin */",
      },
      {
        file: "templates/doubled-css.html.tpl",
        html: pageAround(`${CSS_BEGIN}\n${CSS_BEGIN}\n.keep{}\n${CSS_END}`, validJs),
        message: "templates/doubled-css.html.tpl: doubled marker /* brand:begin */",
      },
      {
        file: "templates/reversed-css.html.tpl",
        html: pageAround(`${CSS_END}\n.keep{}\n${CSS_BEGIN}`, validJs),
        message: "templates/reversed-css.html.tpl: reversed marker /* brand:begin */",
      },
      {
        file: "templates/missing-js.html.tpl",
        html: pageAround(validCss, `<script>\nkeep();\n</script>\n${JS_END}`),
        message: "templates/missing-js.html.tpl: missing marker <!-- brand:js:begin -->",
      },
      {
        file: "templates/doubled-js.html.tpl",
        html: pageAround(validCss, `${JS_BEGIN}\n${JS_BEGIN}\n<script>\nkeep();\n</script>\n${JS_END}`),
        message: "templates/doubled-js.html.tpl: doubled marker <!-- brand:js:begin -->",
      },
      {
        file: "templates/reversed-js.html.tpl",
        html: pageAround(validCss, `${JS_END}\n<script>\nkeep();\n</script>\n${JS_BEGIN}`),
        message: "templates/reversed-js.html.tpl: reversed marker <!-- brand:js:begin -->",
      },
    ] as const;
    expect(markerFaults).toHaveLength(6);
    for (const fault of markerFaults) {
      let refused: unknown;
      try {
        await spliceBrandRegions(fault.html, "a{}\n", "var ready = true;\n", fault.file);
      } catch (error) {
        refused = error;
      }
      expectMarkerRefusal(refused, fault.message);
    }
  });
});

describe("gen refuses a broken template without writing it", () => {
  test("a refused splice leaves the scratch template byte-identical", async () => {
    const scratchRoot = mkdtempSync(join(tmpdir(), "brand-template-refuse-"));
    assertScratchOutsideRepo(scratchRoot);
    const scratchTemplate = join(scratchRoot, "brainstorm.html.tpl");
    const webDir = join(scratchRoot, "web");
    try {
      mkdirSync(webDir);
      const broken = carrierMissingCssBegin(readFileSync(join(ROOT, "templates", "brainstorm.html.tpl"), "utf8"));
      writeFileSync(scratchTemplate, broken);
      const before = readFileSync(scratchTemplate, "utf8");
      let refused: unknown;
      await withScratchWebDir(webDir, async () => {
        try {
          await rewriteBrandTemplate(scratchTemplate, "a{}\n", "var ready = true;\n");
        } catch (error) {
          refused = error;
        }
      });
      expectMarkerRefusal(refused, `${scratchTemplate}: missing marker /* brand:begin */`);
      expect(readFileSync(scratchTemplate, "utf8")).toBe(before);
      expect(readdirSync(scratchRoot).sort()).toEqual(["brainstorm.html.tpl", "web"]);
    } finally {
      rmSync(scratchRoot, { recursive: true, force: true });
    }
  });
});

describe("templateDrift", () => {
  test("is empty on the committed tree and covers every marked template", async () => {
    expect(await templateDrift()).toEqual([]);
    const covered = markedTemplatePaths(ROOT);
    const scratchRoot = mkdtempSync(join(tmpdir(), "brand-template-cover-"));
    try {
      copyBrandTree(scratchRoot);
      for (const relativePath of covered) {
        const templatePath = join(scratchRoot, relativePath);
        writeFileSync(templatePath, flipByteInsideCssRegion(readFileSync(templatePath, "utf8"), relativePath));
      }
      expect([...(await templateDrift(scratchRoot))].sort()).toEqual(covered);
    } finally {
      rmSync(scratchRoot, { recursive: true, force: true });
    }
  });

  test("names a one-byte edit inside the brainstorm region and keeps an edit outside", async () => {
    const scratchRoot = mkdtempSync(join(tmpdir(), "brand-template-drift-"));
    const relativePath = "templates/brainstorm.html.tpl";
    const webDir = join(scratchRoot, "web");
    try {
      copyBrandTree(scratchRoot);
      mkdirSync(webDir);
      const templatePath = join(scratchRoot, relativePath);
      const committed = readFileSync(templatePath, "utf8");
      expect(await templateDrift(scratchRoot)).toEqual([]);
      writeFileSync(templatePath, flipByteInsideCssRegion(committed, relativePath));
      expect(await templateDrift(scratchRoot)).toEqual([relativePath]);

      const outside = flipByteOutsideMarkers(committed);
      const titleEnd = outside.html.indexOf("</title>") + "</title>".length;
      expect(titleEnd).toBeGreaterThan(outside.index);
      expect(titleEnd).toBeLessThan(outside.html.indexOf(CSS_BEGIN));
      expect(committed[outside.index]).toBe(outside.previous);
      expect(outside.html[outside.index]).toBe(outside.byte);
      writeFileSync(templatePath, outside.html);
      const brandCss = readFileSync(join(scratchRoot, "brand", "components.css"), "utf8");
      const brandJs = readFileSync(join(scratchRoot, "brand", "components.js"), "utf8");
      await withScratchWebDir(webDir, async () => {
        await rewriteBrandTemplate(templatePath, brandCss, brandJs);
      });
      const written = readFileSync(templatePath, "utf8");
      expect(written.slice(0, titleEnd)).toBe(outside.html.slice(0, titleEnd));
      expect(written).toBe(await spliceBrandRegions(outside.html, brandCss, brandJs, templatePath));
    } finally {
      rmSync(scratchRoot, { recursive: true, force: true });
    }
  });
});

describe("parity", () => {
  test("prints the brainstorm template when the website checkout is missing", () => {
    const parityRoot = mkdtempSync(join(tmpdir(), "brand-parity-"));
    const missingWebDir = join(parityRoot, "missing-web");
    assertScratchOutsideRepo(parityRoot);
    try {
      expect(existsSync(missingWebDir)).toBe(false);
      const run = spawnSync(process.execPath, [join(ROOT, "scripts", "brand.ts"), "parity"], {
        cwd: ROOT,
        encoding: "utf8",
        env: { ...process.env, AI_ENGINEERING_WEB_DIR: missingWebDir, NO_COLOR: "1" },
      });
      expect(existsSync(missingWebDir)).toBe(false);
      const templateLines = (run.stdout ?? "").split("\n").filter((line) => line === BRAINSTORM_PARITY_LINE);
      expect(templateLines).toEqual([BRAINSTORM_PARITY_LINE]);
    } finally {
      rmSync(parityRoot, { recursive: true, force: true });
    }
  });
});
