/**
 * The browser half of the accessibility gate.
 *
 * `bun test` proves what markup can prove on its own. It cannot see what a
 * browser computes: the contrast of a colour over a gradient, two boxes that
 * overlap, a page that scrolls sideways at 320px. So this command opens every
 * shipped page in the system Chrome — not a downloaded browser, so it works on
 * an air-gapped machine and on a CI runner that already has Chrome — and asks
 * axe-core for the WCAG 2.0, 2.1 and 2.2 A and AA rules at four widths and in
 * Windows high contrast.
 *
 * It then does the three things axe-core does not: it walks every tab set with
 * the arrow keys, it checks that 320px (the WCAG 1.4.10 reflow width) never
 * scrolls sideways — with and without the 1.4.12 text-spacing overrides — and it
 * opens every page with JavaScript off to prove the reading survives.
 *
 * Nothing is waived. A violation names the page, the width and the rule, and
 * the command exits 1.
 */
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { join, relative } from "node:path";
import { pathToFileURL } from "node:url";
import { chromium, type Browser, type Page } from "playwright-core";
import { carrierPaths } from "./brand.ts";

const ROOT = join(import.meta.dir, "..");
/** 320 is the reflow width; 390 a phone; 768 a tablet; 1440 a laptop. */
const WIDTHS = [320, 390, 768, 1440] as const;
const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"] as const;
const REFLOW_WIDTH = 320;
/** WCAG 1.4.12 asks a page to survive a reader's own text spacing. */
const TEXT_SPACING = `* { line-height: 1.5 !important; letter-spacing: 0.12em !important; word-spacing: 0.16em !important; } p { margin-bottom: 2em !important; }`;
const axeSource = readFileSync(createRequire(import.meta.url).resolve("axe-core/axe.min.js"), "utf8");

interface AxeViolation {
  id: string;
  help: string;
  nodes: { target: string[] }[];
}

interface TabSetReport {
  sets: number;
  problems: string[];
}

const problems: string[] = [];

function fail(message: string): void {
  problems.push(message);
}

interface StagedPage {
  /** The repository path, which is what a failure names. */
  readonly label: string;
  /** A real `.html` file in a scratch folder: Chrome renders by extension, and `.tpl` is not one. */
  readonly url: string;
}

/**
 * Copy every carrier to a scratch folder as `.html` and hand back its `file://`
 * URL. The pages are byte-identical to the committed ones and open from a
 * folder, which is how a reader opens them; the scratch copy exists only
 * because Chrome picks how to render a file by its extension.
 */
function stagePages(directory: string): StagedPage[] {
  // Derived, so a ninth carrier is covered the day it lands.
  return carrierPaths(ROOT).map((label) => {
    const target = join(directory, `${label.split("/").join("-")}.html`);
    writeFileSync(target, readFileSync(join(ROOT, label)));
    return { label, url: pathToFileURL(target).href };
  });
}

async function openPage(browser: Browser, url: string): Promise<Page> {
  const page = await browser.newPage();
  // The page is one file opened from a folder: no server, no sibling request.
  await page.goto(url, { waitUntil: "load" });
  return page;
}

async function axeViolations(page: Page, isForcedColors: boolean): Promise<AxeViolation[]> {
  await page.addScriptTag({ content: axeSource });
  const result = await page.evaluate(
    async ([tags, isForced]) =>
      (window as unknown as { axe: { run: (context: Document, options: unknown) => Promise<{ violations: AxeViolation[] }> } }).axe.run(
        document,
        {
          runOnly: { type: "tag", values: tags },
          // In forced colours the operating system owns every colour, so the
          // page cannot be measured for contrast there — axe would compare the
          // reader's palette against itself. The pass exists to catch what the
          // layer can break: a box that loses its border, a stroke that
          // disappears, a control that becomes invisible.
          rules: isForced ? { "color-contrast": { enabled: false } } : {},
        },
      ),
    [[...TAGS], isForcedColors] as const,
  );
  return result.violations;
}

/** The five WCAG tags at every width, then the same five under forced colours. */
async function auditWidths(browser: Browser, page_: StagedPage): Promise<number> {
  const page = await openPage(browser, page_.url);
  let runs = 0;
  try {
    for (const width of WIDTHS) {
      await page.setViewportSize({ width, height: 900 });
      for (const mode of ["screen", "forced-colours"] as const) {
        await page.emulateMedia(mode === "forced-colours" ? { forcedColors: "active" } : { forcedColors: "none" });
        await page.goto(page_.url, { waitUntil: "load" });
        for (const violation of await axeViolations(page, mode === "forced-colours")) {
          for (const node of violation.nodes) {
            fail(`${page_.label} · ${width}px · ${mode} · ${violation.id} · ${node.target.join(" ")} — ${violation.help}`);
          }
        }
        runs += 1;
      }
    }
  } finally {
    await page.close();
  }
  return runs;
}

/**
 * The WAI-ARIA tabs pattern, driven the way a keyboard user drives it: one tab
 * stop, then the arrows, Home and End move selection and focus together, and
 * exactly one panel is visible at each stop.
 */
async function tabsByKeyboard(browser: Browser, page_: StagedPage): Promise<TabSetReport> {
  const page = await openPage(browser, page_.url);
  const report: TabSetReport = { sets: 0, problems: [] };
  try {
    await page.setViewportSize({ width: 1440, height: 900 });
    const sets = await page.locator(".tabs").count();
    report.sets = sets;
    for (let index = 0; index < sets; index += 1) {
      const tabs = page.locator(".tabs").nth(index).locator('[role="tab"]');
      const count = await tabs.count();
      if (count < 2) continue;
      await tabs.first().focus();
      for (const key of ["ArrowRight", "ArrowRight", "ArrowLeft", "End", "Home"] as const) {
        await page.keyboard.press(key);
        const state = await page.evaluate((setIndex) => {
          const set = document.querySelectorAll(".tabs")[setIndex];
          if (!set) return null;
          const buttons = [...set.querySelectorAll('[role="tab"]')];
          const selected = buttons.filter((button) => button.getAttribute("aria-selected") === "true");
          const panels = [...set.querySelectorAll('[role="tabpanel"]')];
          const visible = panels.filter((panel) => !(panel as HTMLElement).hidden);
          const focused = document.activeElement;
          return {
            selected: selected.length,
            visible: visible.length,
            focusIsSelected: selected.length === 1 && focused === selected[0],
            laidOut: buttons.every((button) => button.getBoundingClientRect().width > 0),
          };
        }, index);
        const where = `${page_.label} · ${key} · tab set ${index + 1}`;
        if (state === null) fail(`${where} — the tab set disappeared after the key`);
        else {
          if (state.selected !== 1) fail(`${where} — ${state.selected} tabs selected, expected one`);
          if (state.visible !== 1) fail(`${where} — ${state.visible} panels visible, expected one`);
          if (!state.focusIsSelected) fail(`${where} — focus did not follow the selection`);
          if (!state.laidOut) fail(`${where} — a tab has no width`);
        }
      }
    }
  } finally {
    await page.close();
  }
  return report;
}

async function scrollsSideways(page: Page): Promise<boolean> {
  return page.evaluate(() => {
    const root = document.documentElement;
    return root.scrollWidth > root.clientWidth + 1;
  });
}

/** WCAG 1.4.10 (reflow) and 1.4.12 (text spacing), measured, not assumed. */
async function reflow(browser: Browser, page_: StagedPage): Promise<string[]> {
  const page = await openPage(browser, page_.url);
  const found: string[] = [];
  try {
    await page.setViewportSize({ width: REFLOW_WIDTH, height: 900 });
    if (await scrollsSideways(page)) found.push(`${page_.label} · ${REFLOW_WIDTH}px · the page scrolls sideways`);
    await page.addStyleTag({ content: TEXT_SPACING });
    if (await scrollsSideways(page)) {
      found.push(`${page_.label} · ${REFLOW_WIDTH}px + text spacing · the page scrolls sideways`);
    }
  } finally {
    await page.close();
  }
  return found;
}

/** With the script off every panel is readable and no control asks for a click. */
async function withoutScript(browser: Browser, page_: StagedPage): Promise<string[]> {
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 900 } });
  const found: string[] = [];
  try {
    const page = await context.newPage();
    await page.goto(page_.url, { waitUntil: "load" });
    const state = await page.evaluate(() => {
      const panels = [...document.querySelectorAll(".tabpanel")];
      const controls = [...document.querySelectorAll(".copy, .chip, .tool")];
      return {
        panels: panels.length,
        hiddenPanels: panels.filter((panel) => (panel as HTMLElement).hidden).length,
        visibleControls: controls.filter((control) => (control as HTMLElement).offsetParent !== null).length,
      };
    });
    if (state.hiddenPanels > 0) found.push(`${page_.label} · no script · ${state.hiddenPanels} tab panel(s) hidden`);
    if (state.visibleControls > 0) found.push(`${page_.label} · no script · ${state.visibleControls} control(s) still ask for a click`);
  } finally {
    await context.close();
  }
  return found;
}

async function main(): Promise<number> {
  let browser: Browser;
  try {
    browser = await chromium.launch({ channel: "chrome" });
  } catch {
    console.error(
      'a11y: Google Chrome was not found. This gate drives the system Chrome through channel "chrome" and downloads no browser; install Chrome, or leave this command to the machine that has it.',
    );
    return 1;
  }

  const scratch = mkdtempSync(join(tmpdir(), "artifact-a11y-"));
  try {
    const staged = stagePages(scratch);
    for (const page_ of staged) {
      const before = problems.length;
      const runs = await auditWidths(browser, page_);
      const keys = await tabsByKeyboard(browser, page_);
      for (const problem of keys.problems) fail(problem);
      const reflowProblems = await reflow(browser, page_);
      for (const problem of reflowProblems) fail(problem);
      const scriptProblems = await withoutScript(browser, page_);
      for (const problem of scriptProblems) fail(problem);
      const pageProblems = problems.length - before;
      console.log(
        `${pageProblems === 0 ? "ok  " : "FAIL"} ${page_.label} — ${runs} axe runs (${WIDTHS.join(", ")}px, screen and forced colours), ${pageProblems} problem(s)`,
      );
      console.log(
        `     keys ${keys.sets} tab set(s) · reflow ${REFLOW_WIDTH}px and text spacing ${reflowProblems.length === 0 ? "ok" : "FAILED"} · no script ${scriptProblems.length === 0 ? "ok" : "FAILED"}`,
      );
    }
  } finally {
    await browser.close();
    rmSync(scratch, { recursive: true, force: true });
  }

  if (problems.length > 0) {
    console.error(`\n${problems.length} accessibility problem(s):\n${problems.map((problem) => `  ${problem}`).join("\n")}`);
    console.error("\nEach line names the page, the width, the rule and the element. Fix the page; there is no waiver.");
    return 1;
  }
  console.log(`\n${carrierPaths(ROOT).length} pages pass axe-core (${TAGS.join(", ")}) at ${WIDTHS.join(", ")}px and in forced colours, the tab keyboard pattern, reflow and the no-script reading.`);
  return 0;
}

process.exit(await main());
