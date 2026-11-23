/**
 * The nav highlight is a behaviour, not a colour. `nav a.active` is painted in
 * the artifact shell, and docs/history/blueprint.html is the one page that actually
 * toggles it while scrolling. recap, brainstorm and research copy the shell
 * and used to ship the paint without the listener, so the titles never selected.
 *
 * brand/components.js owns the script. gen splices it into every template, and
 * the templates must carry the same bytes, because an agent fills a template and
 * writes no script of its own.
 */
import { describe, expect, test } from "bun:test";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

const ROOT = join(import.meta.dir, "..");

function read(path: string): string {
  return readFileSync(join(ROOT, path), "utf8");
}

/** Every template whose navigation links to its own sections, found by glob. */
const SHELLS = readdirSync(join(ROOT, "templates"))
  .filter((name) => name.endsWith(".html.tpl"))
  .map((name) => `templates/${name}`)
  .filter((path) => hasSectionNavigation(read(path)))
  .sort();

/** The scroll-spy function in brand/components.js: its comment through the IIFE's close. */
function scrollSpyScript(): string {
  const source = read("brand/components.js");
  const script = /\/\* scroll-spy:[\s\S]*?\n\}\)\(\);\n/.exec(source)?.[0];
  if (script === undefined) {
    throw new Error("brand/components.js has no scroll-spy function");
  }
  return script;
}

type SpyLink = {
  className: string;
  getAttribute(name: string): string | null;
  setAttribute(name: string, value: string): void;
  removeAttribute(name: string): void;
  classList: { toggle(name: string, force: boolean): void };
};

function install(script: string, tops: Map<string, number>, check: (links: SpyLink[], onScroll: () => void) => void): void {
  const attrs = new Map<SpyLink, Map<string, string>>();
  const links: SpyLink[] = [];
  for (const id of tops.keys()) {
    const link: SpyLink = {
      className: "",
      getAttribute(name) {
        return attrs.get(link)?.get(name) ?? null;
      },
      setAttribute(name, value) {
        attrs.get(link)?.set(name, value);
      },
      removeAttribute(name) {
        attrs.get(link)?.delete(name);
      },
      classList: {
        toggle(name, force) {
          const classes = new Set(link.className.split(" ").filter((token) => token.length > 0));
          if (force) classes.add(name);
          else classes.delete(name);
          link.className = [...classes].join(" ");
        },
      },
    };
    attrs.set(link, new Map([["href", `#${id}`]]));
    links.push(link);
  }

  let onScroll = (): void => {};
  const previousDocument = globalThis.document;
  const previousWindow = globalThis.window;
  Object.assign(globalThis, {
    document: {
      querySelectorAll(selector: string) {
        return selector === 'nav a[href^="#"]' ? links : [];
      },
      getElementById(id: string) {
        if (!tops.has(id)) return null;
        return { getBoundingClientRect: () => ({ top: tops.get(id) }) };
      },
    },
    window: {
      addEventListener(type: string, listener: () => void) {
        if (type === "scroll") onScroll = listener;
      },
    },
  });
  try {
    // The listener reads `document` when scroll fires, so the fake stays up
    // for the whole check. Restoring it first is what made the spy a no-op.
    new Function(script)();
    check(links, onScroll);
  } finally {
    Object.assign(globalThis, { document: previousDocument, window: previousWindow });
  }
}

function activeHref(links: SpyLink[]): string | null {
  const selected = links.filter((link) => link.className.split(" ").includes("active"));
  return selected.length === 1 ? selected[0]?.getAttribute("href") ?? null : null;
}

function hasSectionNavigation(page: string): boolean {
  return [...page.matchAll(/<nav\b[^>]*>[\s\S]*?<\/nav>/gi)]
    .some(([nav]) => /<a\b[^>]*\bhref=["']#[^"']+["']/i.test(nav));
}

/** Pages whose navigation links to same-page sections, not application views. */
function htmlWithSectionNav(): string[] {
  const found: string[] = [];
  const walk = (dir: string): void => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      if (entry.name === "node_modules" || entry.name === ".git") continue;
      const full = join(dir, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (entry.name.endsWith(".html")) {
        const page = readFileSync(full, "utf8");
        if (hasSectionNavigation(page)) found.push(full.slice(ROOT.length + 1));
      }
    }
  };
  walk(ROOT);
  return found;
}

describe("artifact scroll-spy", () => {
  test("brand/components.js owns the script, and every shell embeds those exact bytes", () => {
    const script = scrollSpyScript();
    expect(SHELLS.length).toBeGreaterThan(0);
    const drifted = SHELLS.filter((path) => !read(path).includes(script));
    expect(drifted).toEqual([]);
  });

  test("distinguishes application navigation from section links in any navigation region", () => {
    expect(hasSectionNavigation('<nav><button>All projects</button></nav>')).toBe(false);
    expect(hasSectionNavigation('<nav><a href="/projects">Projects</a></nav><nav><a href="#details">Details</a></nav>')).toBe(true);
    expect(hasSectionNavigation('<nav><a href="/projects">Projects</a><a href="/settings">Settings</a></nav>')).toBe(false);
  });

  test("every page with section navigation carries that script and the .active paint", () => {
    const script = scrollSpyScript();
    const bare = htmlWithSectionNav().filter((path) => {
      const page = read(path);
      return !page.includes(script) || !page.includes("nav a.active");
    });
    expect(bare).toEqual([]);
  });

  test("scrolling marks the section whose heading has cleared the sticky nav", () => {
    const tops = new Map([
      ["s01", 400],
      ["s02", 900],
      ["s03", 1400],
    ]);
    install(scrollSpyScript(), tops, (links, onScroll) => {
      // Still in the hero: every heading is below the lead, so nothing is selected.
      expect(activeHref(links)).toBeNull();

      tops.set("s01", 40);
      onScroll();
      expect(activeHref(links)).toBe("#s01");
      expect(links[0]?.getAttribute("aria-current")).toBe("location");

      // The later heading that has crossed the lead wins; the one above loses the mark.
      tops.set("s01", -240);
      tops.set("s02", 20);
      onScroll();
      expect(activeHref(links)).toBe("#s02");
      expect(links[0]?.className.includes("active")).toBe(false);
      expect(links[0]?.getAttribute("aria-current")).toBeNull();
      expect(links[1]?.getAttribute("aria-current")).toBe("location");
    });
  });
});
