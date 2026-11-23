/**
 * The static accessibility gate, proven on both sides.
 *
 * One side: every page that ships — the eight templates and the gallery, found
 * by glob so a ninth is covered the day it lands — carries no problem, and the
 * one script the pages share is a classic script that writes text.
 *
 * Other side: each rule is shown to fire. A gate nobody has seen fail is a gate
 * nobody knows works, so every check gets a fixture that breaks exactly it, and
 * the test asserts the exact message and that nothing else fired.
 */
import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { staticA11yProblems, scriptProblems } from "../scripts/artifact-a11y.ts";
import { carrierPaths } from "../scripts/brand.ts";

const ROOT = join(import.meta.dir, "..");

const MEDIA = `@media (forced-colors:active){a{color:CanvasText}}
@media (prefers-reduced-motion:reduce){*{transition:none}}
@media print{nav{display:none}}`;

/** A page that breaks nothing: every fixture below changes exactly one byte of it. */
function soundPage(): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fixture</title>
<style>
${MEDIA}
</style>
</head>
<body>
<h1>Title</h1>
<table><caption>What it lists</caption><thead><tr><th scope="col">A</th></tr></thead></table>
<svg role="img" viewBox="0 0 10 10"><title>A picture</title></svg>
</body>
</html>
`;
}

/** One broken page and the one message it must produce. */
function broken(edit: (page: string) => string): string[] {
  const page = edit(soundPage());
  return [...staticA11yProblems(page, "page.html")];
}

describe("every shipped page passes the static gate", () => {
  test("the eight templates and the gallery carry no problem", () => {
    const carriers = carrierPaths(ROOT);
    // The glob is the list: a page added tomorrow is covered without an edit here.
    expect(carriers.filter((path) => path.startsWith("templates/")).length).toBe(8);
    expect(carriers).toContain("brand/gallery.html.tpl");
    const problems: string[] = [];
    for (const relativePath of carriers) {
      problems.push(...staticA11yProblems(readFileSync(join(ROOT, relativePath), "utf8"), relativePath));
    }
    expect(problems).toEqual([]);
  });

  test("the one page script is a classic script that writes text", () => {
    expect(scriptProblems(readFileSync(join(ROOT, "brand", "components.js"), "utf8"))).toEqual([]);
  });
});

describe("each rule fires on the page that breaks it", () => {
  test("no lang", () => {
    expect(broken((page) => page.replace(' lang="en"', ""))).toEqual([
      'page.html: no <html lang="...">, so a screen reader guesses the language',
    ]);
  });

  test("no title", () => {
    expect(broken((page) => page.replace("<title>Fixture</title>", "<title> </title>"))).toEqual([
      "page.html: no non-empty <title>, so the tab and the window name nothing",
    ]);
  });

  test("no h1", () => {
    expect(broken((page) => page.replace("<h1>Title</h1>", "<h2>Title</h2>"))).toEqual([
      "page.html: no h1 heading, so the page names no subject",
    ]);
  });

  test("two h1", () => {
    expect(broken((page) => page.replace("<h1>Title</h1>", "<h1>Title</h1><h1>Again</h1>"))).toEqual([
      "page.html: 2 h1 headings side by side; a rendered page carries exactly one",
    ]);
  });

  test("an h2 then an h4", () => {
    expect(broken((page) => page.replace("<h1>Title</h1>", "<h1>Title</h1><h2>Two</h2><h4>Four</h4>"))).toEqual([
      "page.html: heading order skips from h2 to h4",
    ]);
  });

  test("a th without scope", () => {
    expect(broken((page) => page.replace('<th scope="col">', "<th>"))).toEqual([
      "page.html: a <th> has no scope, so its column has no name",
    ]);
  });

  test("a table without a caption", () => {
    expect(broken((page) => page.replace("<caption>What it lists</caption>", ""))).toEqual([
      "page.html: a <table> has no <caption>, so its subject is unnamed",
    ]);
  });

  test("an svg without role", () => {
    expect(broken((page) => page.replace('<svg role="img"', "<svg"))).toEqual([
      'page.html: an <svg> has no role="img", so assistive tech skips it',
    ]);
  });

  test("an svg without a title", () => {
    expect(broken((page) => page.replace("<title>A picture</title>", ""))).toEqual([
      "page.html: an <svg> has no <title>, so its picture has no name",
    ]);
  });

  test("a dangling aria id", () => {
    expect(broken((page) => page.replace("<h1>", '<p aria-describedby="gone">Lead.</p><h1>'))).toEqual([
      'page.html: aria-describedby="gone" points at an id the page does not have',
    ]);
  });

  test("a duplicate id", () => {
    expect(broken((page) => page.replace("<h1>", '<div id="twice"></div><div id="twice"></div><h1>'))).toEqual([
      'page.html: duplicate id "twice", so a link lands on the wrong place',
    ]);
  });

  test("an external script", () => {
    expect(broken((page) => page.replace("</body>", '<script src="https://cdn.example/x.js"></script></body>'))).toEqual([
      "page.html: external script https://cdn.example/x.js — an artifact opens offline",
    ]);
  });

  test("an external stylesheet", () => {
    expect(broken((page) => page.replace("</head>", '<link rel="stylesheet" href="https://cdn.example/x.css"></head>'))).toEqual([
      "page.html: external stylesheet https://cdn.example/x.css — an artifact opens offline",
    ]);
  });

  test("an inline handler", () => {
    expect(broken((page) => page.replace("<h1>", '<button type="button" onclick="go()">Go</button><h1>'))).toEqual([
      "page.html: inline onclick handler — the page carries one script, not many",
    ]);
  });

  test("a viewport that blocks zoom", () => {
    expect(broken((page) => page.replace("width=device-width, initial-scale=1", "width=device-width, maximum-scale=1"))).toEqual([
      "page.html: the viewport blocks zoom, so a reader cannot enlarge the text",
    ]);
  });

  test("no forced-colors rule", () => {
    expect(broken((page) => page.replace("@media (forced-colors:active){a{color:CanvasText}}\n", ""))).toEqual([
      "page.html: no forced-colors layer, so Windows high contrast keeps every box visible",
    ]);
  });

  test("no reduced-motion rule", () => {
    expect(broken((page) => page.replace("@media (prefers-reduced-motion:reduce){*{transition:none}}\n", ""))).toEqual([
      "page.html: no prefers-reduced-motion rule, so the reader's own setting wins",
    ]);
  });

  test("no print rule", () => {
    expect(broken((page) => page.replace("@media print{nav{display:none}}", ""))).toEqual([
      "page.html: no print rule, so the page survives paper",
    ]);
  });

  test("commented-out markup and code samples are text, not structure", () => {
    const page = soundPage()
      .replace("<h1>", "<!-- <h1>Example</h1> <table></table> -->\n<pre><code>&lt;h1 id=\"x\"&gt;</code></pre><h1>");
    expect(staticA11yProblems(page, "page.html")).toEqual([]);
  });
});

describe("each script rule fires on the copy that breaks it", () => {
  const sound = readFileSync(join(ROOT, "brand", "components.js"), "utf8");

  test("markup written as a string", () => {
    expect(scriptProblems(`${sound}\nel.innerHTML = "<b>x</b>";\n`)).toEqual(["brand/components.js: uses innerHTML"]);
  });

  test("a network read", () => {
    expect(scriptProblems(`${sound}\nfetch("/x");\n`)).toEqual(["brand/components.js: uses fetch"]);
  });

  test("a module statement", () => {
    expect(scriptProblems(`export const x = 1;\n${sound}`)).toEqual([
      "brand/components.js: is an ES module; a page script is classic",
    ]);
  });

  test("a script that does not parse", () => {
    const problems = scriptProblems(`${sound}\n(function () {`);
    expect(problems).toHaveLength(1);
    expect(problems[0]).toStartWith("brand/components.js: does not parse as a classic script (");
  });
});
