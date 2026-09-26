import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = join(import.meta.dir, "..");
const templatePath = join(root, "templates/viewer.html.tpl");
const plantedPath = join(root, ".ai-engineering/workflow/checkpoints/viewer.html");

type DomNode = {
  id: string;
  hidden: boolean;
  className: string;
  textContent: string;
  innerHTML: string;
  classList: { add(): void; remove(): void };
  onchange: ((e: { target: { files: unknown[]; value: string } }) => void) | null;
  parentElement: {
    children: DomNode[];
    appendChild(child: DomNode): void;
    insertBefore(child: DomNode, ref: DomNode | null): void;
  } | null;
  setAttribute(name: string, value: string): void;
  getAttribute(name: string): string | null;
  remove(): void;
};

function el(init: Partial<DomNode> = {}): DomNode {
  const attrs: Record<string, string> = {};
  const node: DomNode = {
    id: "",
    hidden: true,
    className: "",
    textContent: "",
    innerHTML: "",
    classList: { add() {}, remove() {} },
    onchange: null,
    parentElement: null,
    setAttribute(name: string, value: string) {
      attrs[name] = value;
    },
    getAttribute(name: string) {
      return attrs[name] ?? null;
    },
    remove() {},
    ...init,
  };
  return node;
}

type ViewerApi = {
  load: (text: string) => boolean;
  servedInit: () => Promise<void>;
};

type NodeId =
  | "live"
  | "empty"
  | "app"
  | "file"
  | "title"
  | "summary"
  | "banner"
  | "bannerText"
  | "journey"
  | "steps"
  | "extra";

type ViewerNodes = Record<NodeId, DomNode>;
type ViewerHarness = {
  api: ViewerApi;
  nodes: ViewerNodes;
  byId: Record<string, DomNode>;
  tickAgain: () => Promise<void>;
};

function templateHtml(): string {
  return readFileSync(templatePath, "utf8");
}

/** Pull #empty's attributes and children from the shipped template — not literals. */
function emptySectionFromTemplate(html: string): {
  attrs: Record<string, string>;
  innerHTML: string;
  isHidden: boolean;
} {
  const match = html.match(/<section\b([^>]*\sid="empty"(?=[\s>])[^>]*)>([\s\S]*?)<\/section>/);
  if (!match?.[1] || match[2] === undefined) throw new Error("#empty section missing");
  const openAttrs = match[1];
  const attrs: Record<string, string> = {};
  for (const attr of openAttrs.matchAll(/([^\s=]+)(?:=(?:"([^"]*)"|'([^']*)'))?/g)) {
    const key = attr[1];
    if (!key) continue;
    attrs[key] = attr[2] ?? attr[3] ?? "";
  }
  return { attrs, innerHTML: match[2], isHidden: Object.hasOwn(attrs, "hidden") };
}

async function withViewer(
  opts: { search?: string; fetchText?: (url: string) => Promise<string> },
  run: (harness: ViewerHarness) => void | Promise<void>,
): Promise<void> {
  const source = templateHtml();
  const match = source.match(/<script>\n([\s\S]*)\n<\/script>/);
  if (!match?.[1]) throw new Error("viewer template has no script block");
  const body = match[1]
    .replace(/\nbindLocalFile\(\);\nif \(served\) servedInit\(\);\nelse \$\("empty"\)\.hidden = false;\s*$/, "")
    .trimEnd();

  const emptyParsed = emptySectionFromTemplate(source);
  const emptyAttrs = emptyParsed.attrs;
  const nodes: ViewerNodes = {
    live: el({ className: "live off", textContent: "offline", hidden: false }),
    empty: el({
      hidden: emptyParsed.isHidden,
      className: emptyAttrs.class ?? "",
      innerHTML: emptyParsed.innerHTML,
      getAttribute(name: string): string | null {
        return Object.hasOwn(emptyAttrs, name) ? (emptyAttrs[name] ?? "") : null;
      },
    }),
    app: el({ hidden: true }),
    file: el(),
    title: el({ hidden: false }),
    summary: el({ hidden: false }),
    banner: el({ hidden: false }),
    bannerText: el({ hidden: false }),
    journey: el({ hidden: false }),
    steps: el({ hidden: false }),
    extra: el({ hidden: false }),
  };
  const byId: Record<string, DomNode> = { ...nodes };

  const liveParent = {
    children: [] as DomNode[],
    appendChild(child: DomNode) {
      if (child.id) byId[child.id] = child;
      child.parentElement = liveParent;
      liveParent.children.push(child);
    },
    insertBefore(child: DomNode, ref: DomNode | null) {
      if (child.id) byId[child.id] = child;
      child.parentElement = liveParent;
      const at = ref ? liveParent.children.indexOf(ref) : -1;
      if (at >= 0) liveParent.children.splice(at, 0, child);
      else liveParent.children.push(child);
    },
  };
  nodes.live.parentElement = liveParent;
  liveParent.children.push(nodes.live);

  const previous = {
    document: globalThis.document,
    location: globalThis.location,
    fetch: globalThis.fetch,
    addEventListener: globalThis.addEventListener,
    setInterval: globalThis.setInterval,
    URLSearchParams: globalThis.URLSearchParams,
  };

  let pendingTick: (() => void | Promise<void>) | null = null;
  const fetchMap = opts.fetchText;
  Object.assign(globalThis, {
    document: {
      getElementById(id: string) {
        return byId[id] ?? null;
      },
      createElement(_tag: string) {
        const node = el();
        node.remove = () => {
          if (node.id && byId[node.id] === node) delete byId[node.id];
        };
        return node;
      },
      querySelectorAll() {
        return [];
      },
      title: "",
    },
    location: {
      protocol: "http:",
      search: opts.search ?? "",
    },
    fetch: async (url: string) => {
      if (!fetchMap) throw new Error(`unexpected fetch: ${url}`);
      try {
        const text = await fetchMap(url);
        return { ok: true, status: 200, text: async () => text };
      } catch (err) {
        const status = err instanceof Error && /^\d+$/.test(err.message) ? Number(err.message) : 500;
        return { ok: false, status, text: async () => "" };
      }
    },
    addEventListener() {},
    setInterval(fn: () => void | Promise<void>) {
      pendingTick = fn;
      return 0;
    },
    URLSearchParams,
  });

  try {
    const api = new Function(`${body}\nreturn { load, servedInit };`)() as ViewerApi;
    await run({
      api,
      nodes,
      byId,
      tickAgain: async () => {
        if (!pendingTick) throw new Error("no tick registered");
        await pendingTick();
      },
    });
  } finally {
    Object.assign(globalThis, previous);
  }
}

const samplePlan = JSON.stringify({
  feature: "Demo",
  slug: "demo",
  checkpoints: [{ id: 1, title: "One", size: "xs", status: "pending", gates: {} }],
});

const twoPlanIndex = '<a href="demo.json">demo</a><a href="other.json">other</a>';

describe("viewer-audit — checkpoint 1 offline on failed plan load", () => {
  test("U1: invalid JSON → load false, #empty shown, #app hidden", async () => {
    await withViewer({}, ({ api, nodes }) => {
      expect(api.load("{not-json")).toBe(false);
      expect(nodes.empty.hidden).toBe(false);
      expect(nodes.app.hidden).toBe(true);
    });
  });

  test("U2: fetch 404 → #empty shown, #live offline", async () => {
    await withViewer(
      {
        search: "?plan=missing",
        fetchText: async (url) => {
          if (url === "./") return "";
          throw new Error("404");
        },
      },
      async ({ api, nodes }) => {
        await api.servedInit();
        expect(nodes.empty.hidden).toBe(false);
        expect(nodes.app.hidden).toBe(true);
        expect(nodes.live.textContent).toBe("offline");
        expect(nodes.live.className).toBe("live off");
      },
    );
  });

  test("U2b: served invalid JSON → #empty shown, #live offline", async () => {
    await withViewer(
      {
        search: "?plan=broken",
        fetchText: async (url) => {
          if (url === "./") return "";
          if (url === "./broken.json") return "{not-json";
          throw new Error("404");
        },
      },
      async ({ api, nodes }) => {
        await api.servedInit();
        expect(nodes.empty.hidden).toBe(false);
        expect(nodes.app.hidden).toBe(true);
        expect(nodes.live.textContent).toBe("offline");
        expect(nodes.live.className).toBe("live off");
      },
    );
  });

  test("U3: valid JSON → #app shown, #live live", async () => {
    await withViewer(
      {
        search: "?plan=demo",
        fetchText: async (url) => {
          if (url === "./") return "";
          if (url === "./demo.json") return samplePlan;
          throw new Error("404");
        },
      },
      async ({ api, nodes }) => {
        await api.servedInit();
        expect(nodes.empty.hidden).toBe(true);
        expect(nodes.app.hidden).toBe(false);
        expect(nodes.live.textContent).toBe("live");
        expect(nodes.live.className).toBe("live");
        expect(api.load(samplePlan)).toBe(true);
      },
    );
  });

  test("U4: no plan slug → #empty shown, #live offline", async () => {
    await withViewer(
      {
        search: "",
        fetchText: async (url) => {
          if (url === "./") return "<html></html>";
          throw new Error("404");
        },
      },
      async ({ api, nodes }) => {
        await api.servedInit();
        expect(nodes.empty.hidden).toBe(false);
        expect(nodes.live.textContent).toBe("offline");
        expect(nodes.live.className).toBe("live off");
      },
    );
  });

  test("U5: non-object JSON → load false, #empty shown", async () => {
    await withViewer({}, ({ api, nodes }) => {
      expect(api.load("null")).toBe(false);
      expect(nodes.empty.hidden).toBe(false);
      expect(nodes.app.hidden).toBe(true);
      expect(api.load("42")).toBe(false);
      expect(nodes.empty.hidden).toBe(false);
    });
  });

  test("U6: templates/viewer.html.tpl and planted viewer.html are byte-identical", () => {
    const template = readFileSync(templatePath);
    const planted = readFileSync(plantedPath);
    expect(Buffer.compare(template, planted)).toBe(0);
  });
});

function styleBlock(html: string): string {
  const match = html.match(/<style>([\s\S]*?)<\/style>/);
  if (!match?.[1]) throw new Error("style block missing");
  return match[1];
}

const richPlan = JSON.stringify({
  feature: "Demo",
  slug: "demo",
  checkpoints: [
    {
      id: 1,
      title: "One",
      simple: "Ship one",
      size: "xs",
      status: "pending",
      gates: {},
      plain: {
        what: "A working empty drop",
        why: "People need a clear title",
        check: "Open a missing plan",
      },
      acceptance: ["empty title is h1"],
      tasks: ["raise heading levels"],
      files: [".ai-engineering/workflow/checkpoints/very/long/path/to/viewer.html"],
      verify: ["bun test"],
    },
  ],
});

describe("viewer-audit — checkpoint 2 empty drop and headings", () => {
  test('U13: failed load unhides #empty with h1 "Open a feature plan"', async () => {
    await withViewer({}, ({ api, nodes }) => {
      expect(api.load("{not-json")).toBe(false);
      expect(nodes.empty.hidden).toBe(false);
      expect(nodes.empty.innerHTML).toContain("<h1>Open a feature plan</h1>");
    });
  });

  test("U5: CSS source only — .drop input has min-height 44px (no browser layout)", () => {
    const css = styleBlock(templateHtml());
    expect(css).toMatch(/\.drop\s+input\s*\{[^}]*min-height:\s*44px/);
  });

  test("U6: CSS source only — .drop uses overflow-wrap anywhere (no browser layout)", () => {
    const css = styleBlock(templateHtml());
    expect(css).toMatch(/\.drop\s*\{[^}]*overflow-wrap:\s*anywhere/);
  });

  test("U7: in-card section labels are h2; page title stays h1", async () => {
    const html = templateHtml();
    expect(html).toMatch(/<h1 id="title"><\/h1>/);
    expect(styleBlock(html)).toMatch(/\.body\s+h2\s*\{/);
    expect(styleBlock(html)).not.toMatch(/\.body\s+h3\s*\{/);

    await withViewer({}, ({ api, nodes }) => {
      expect(api.load(richPlan)).toBe(true);
      const card = nodes.steps.innerHTML;
      expect(card).toContain("<h2>What you get</h2>");
      expect(card).toContain("<h2>Why it matters</h2>");
      expect(card).toContain("<h2>How you can check it</h2>");
      expect(card).toContain("<h2>Done when</h2>");
      expect(card).toContain("<h2>Tasks</h2>");
      expect(card).toContain("<h2>Files</h2>");
      expect(card).toContain("<h2>Check commands</h2>");
      expect(card).not.toMatch(/<h3>/);
      expect(nodes.title.textContent).toBe("Demo");
    });
  });

  test('U8: served with no slug keeps #empty data-region="empty-drop"', async () => {
    await withViewer(
      {
        search: "",
        fetchText: async (url) => {
          if (url === "./") return "<html></html>";
          throw new Error("404");
        },
      },
      async ({ api, nodes }) => {
        await api.servedInit();
        expect(nodes.empty.hidden).toBe(false);
        expect(nodes.empty.getAttribute("data-region")).toBe("empty-drop");
      },
    );
  });

  test("U9: template and planted viewer stay byte-identical", () => {
    const template = readFileSync(templatePath);
    const planted = readFileSync(plantedPath);
    expect(Buffer.compare(template, planted)).toBe(0);
  });

  test("U10: two plans + good load → #picker before #live with slug selected", async () => {
    await withViewer(
      {
        search: "?plan=demo",
        fetchText: async (url) => {
          if (url === "./") return twoPlanIndex;
          if (url === "./demo.json") return samplePlan;
          throw new Error("404");
        },
      },
      async ({ api, byId, nodes }) => {
        await api.servedInit();
        const picker = byId.picker;
        if (!picker) throw new Error("#picker missing after good load");
        expect(picker.innerHTML).toContain('<option selected>demo</option>');
        expect(picker.innerHTML).toContain("<option >other</option>");
        const parent = nodes.live.parentElement;
        if (!parent) throw new Error("#live has no parent");
        expect(parent.children.indexOf(picker)).toBeGreaterThanOrEqual(0);
        expect(parent.children.indexOf(picker)).toBeLessThan(parent.children.indexOf(nodes.live));
      },
    );
  });

  test("U11: good then broken tick removes #picker", async () => {
    let planFetches = 0;
    await withViewer(
      {
        search: "?plan=demo",
        fetchText: async (url) => {
          if (url === "./") return twoPlanIndex;
          if (url === "./demo.json") {
            planFetches += 1;
            return planFetches === 1 ? samplePlan : "{not-json";
          }
          throw new Error("404");
        },
      },
      async ({ api, byId, tickAgain }) => {
        await api.servedInit();
        expect(byId.picker).toBeDefined();
        await tickAgain();
        expect(byId.picker).toBeUndefined();
      },
    );
  });

  test("U12: second good tick leaves existing #picker untouched", async () => {
    await withViewer(
      {
        search: "?plan=demo",
        fetchText: async (url) => {
          if (url === "./") return twoPlanIndex;
          if (url === "./demo.json") return samplePlan;
          throw new Error("404");
        },
      },
      async ({ api, byId, tickAgain }) => {
        await api.servedInit();
        const picker = byId.picker;
        if (!picker) throw new Error("#picker missing after good load");
        const htmlBefore = picker.innerHTML;
        picker.innerHTML = "MARKER_SHOULD_STAY";
        await tickAgain();
        expect(byId.picker).toBe(picker);
        expect(picker.innerHTML).toBe("MARKER_SHOULD_STAY");
        expect(htmlBefore).toContain("selected");
      },
    );
  });
});

const sizeLadderPlan = JSON.stringify({
  feature: "Demo",
  slug: "demo",
  checkpoints: [
    { id: 1, title: "Xs", size: "xs", status: "pending", gates: {} },
    { id: 2, title: "S", size: "s", status: "pending", gates: {} },
    { id: 3, title: "M", size: "m", status: "pending", gates: {} },
    { id: 4, title: "M2", size: "m", status: "pending", gates: {} },
    { id: 5, title: "L", size: "l", status: "pending", gates: {} },
    { id: 6, title: "L2", size: "l", status: "pending", gates: {} },
    { id: 7, title: "Xl", size: "xl", status: "pending", gates: {} },
  ],
});

describe("viewer-audit — checkpoint 3 journey fit and tech tap", () => {
  test("U10: CSS source only — .journey .line min-width 4px", () => {
    const css = styleBlock(templateHtml());
    expect(css).toMatch(/\.journey\s+\.line\s*\{[^}]*min-width:\s*4px/);
  });

  test("U10b: CSS source only — .journey has min-width 0, overflow-x auto, and 4px padding", () => {
    const css = styleBlock(templateHtml());
    expect(css).toMatch(/\.journey\s*\{[^}]*min-width:\s*0/);
    expect(css).toMatch(/\.journey\s*\{[^}]*overflow-x:\s*auto/);
    expect(css).toMatch(/\.journey\s*\{[^}]*padding:\s*4px/);
  });

  test("U11: CSS source only — .tech>summary has padding-block 13px", () => {
    const css = styleBlock(templateHtml());
    expect(css).toMatch(/\.tech\s*>\s*summary\s*\{[^}]*padding-block:\s*13px/);
  });

  test("U12: load() keeps seven-step diameters 27/32/37/37/42/42/47 (not 44)", async () => {
    await withViewer({}, ({ api, nodes }) => {
      expect(api.load(sizeLadderPlan)).toBe(true);
      const journey = nodes.journey.innerHTML;
      for (const diameter of [27, 32, 37, 42, 47]) {
        expect(journey).toContain(`width:${diameter}px;height:${diameter}px`);
      }
      expect([...journey.matchAll(/width:(\d+)px;height:\1px/g)].map((m) => m[1])).toEqual([
        "27",
        "32",
        "37",
        "37",
        "42",
        "42",
        "47",
      ]);
      expect(journey).not.toContain("width:44px");
    });
  });

  test('U13: load() puts data-region="tech-details" on Technical details', async () => {
    await withViewer({}, ({ api, nodes }) => {
      expect(api.load(richPlan)).toBe(true);
      expect(nodes.steps.innerHTML).toMatch(
        /<details\s+class="tech"[^>]*\bdata-region="tech-details"/,
      );
    });
  });

  test("U14: template and planted viewer stay byte-identical", () => {
    const template = readFileSync(templatePath);
    const planted = readFileSync(plantedPath);
    expect(Buffer.compare(template, planted)).toBe(0);
  });
});
