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
type StepDetails = { dataset: { id: string }; open: boolean; ontoggle: (() => void) | null };
type GoLink = { dataset: { go: string }; onclick: (() => void) | null };
type ViewerHarness = {
  api: ViewerApi;
  nodes: ViewerNodes;
  byId: Record<string, DomNode>;
  tickAgain: () => Promise<void>;
  /** Simulates the person opening or closing a rendered step card. */
  setStepOpen: (id: number, isOpen: boolean) => void;
  /** Simulates the person clicking the link rendered in the status banner. */
  clickBannerLink: () => void;
  /** Element ids the viewer scrolled into view, in order. */
  scrolledTo: string[];
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
  let stepDetails: StepDetails[] = [];
  let bannerLinks: GoLink[] = [];
  const scrolledTo: string[] = [];
  const goLinksIn = (html: string): GoLink[] =>
    [...html.matchAll(/data-go="([^"]*)"/g)].map((m) => ({ dataset: { go: m[1] ?? "" }, onclick: null }));
  const fetchMap = opts.fetchText;
  Object.assign(globalThis, {
    document: {
      getElementById(id: string) {
        if (id.startsWith("step-") && nodes.steps.innerHTML.includes(`id="${id}"`)) {
          return { scrollIntoView: () => scrolledTo.push(id) };
        }
        return byId[id] ?? null;
      },
      createElement(_tag: string) {
        const node = el();
        node.remove = () => {
          if (node.id && byId[node.id] === node) delete byId[node.id];
        };
        return node;
      },
      querySelectorAll(selector: string) {
        if (selector === "[data-go]") {
          bannerLinks = goLinksIn(nodes.bannerText.innerHTML);
          return [...bannerLinks, ...goLinksIn(nodes.journey.innerHTML)];
        }
        if (selector !== "details.step") return [];
        stepDetails = [
          ...nodes.steps.innerHTML.matchAll(/<details class="step[^"]*" id="step-[^"]*" data-id="([^"]*)"\s*(open)?\s*>/g),
        ].map((m) => ({ dataset: { id: m[1] ?? "" }, open: m[2] !== undefined, ontoggle: null }));
        return stepDetails;
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
      setStepOpen: (id, isOpen) => {
        const details = stepDetails.find((d) => d.dataset.id === String(id));
        if (!details?.ontoggle) throw new Error(`step ${id} has no toggle handler`);
        details.open = isOpen;
        nodes.steps.innerHTML = nodes.steps.innerHTML.replace(
          new RegExp(`(<details class="step[^"]*" id="step-${id}" data-id="${id}")\\s*(?:open)?\\s*>`),
          isOpen ? "$1 open>" : "$1 >",
        );
        details.ontoggle();
      },
      clickBannerLink: () => {
        const [link] = bannerLinks;
        if (!link?.onclick) throw new Error("banner has no clickable link");
        link.onclick();
      },
      scrolledTo,
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

describe("viewer-audit — current checkpoint findings", () => {
  test("a halted plan keeps the current checkpoint findings link in the status banner", async () => {
    const plan = JSON.stringify({
      feature: "Floating core",
      halted: { reason: "review <input> is needed" },
      checkpoints: [
        {
          id: 19,
          title: "Install every skill",
          size: "xl",
          status: "pending",
          gates: { behavior: { status: "failed", attempts: 2, findings: ["Gate failed"] } },
        },
      ],
    });

    await withViewer({}, ({ api, nodes }) => {
      expect(api.load(plan)).toBe(true);
      expect(nodes.bannerText.innerHTML).toContain("Stopped. Needs your input: review &lt;input&gt; is needed");
      expect(nodes.bannerText.innerHTML).toContain('href="#step-19"');
      expect(nodes.bannerText.innerHTML).toContain("View 1 finding");
    });
  });

  test("failed gate findings are visible and linked from the status banner", async () => {
    const finding = "9 init-command tests failed; focused rerun passed 33 tests";
    const plan = JSON.stringify({
      feature: "Floating core",
      slug: "floating-core",
      checkpoints: [
        {
          id: 19,
          title: "Install every skill",
          simple: "Get every tool during setup",
          size: "xl",
          status: "pending",
          gates: {
            behavior: { status: "failed", attempts: 2, findings: [finding] },
          },
        },
      ],
    });

    await withViewer({}, ({ api, nodes }) => {
      expect(api.load(plan)).toBe(true);

      const card = nodes.steps.innerHTML;
      expect(card.indexOf(finding)).toBeGreaterThan(-1);
      expect(card.indexOf(finding)).toBeLessThan(card.indexOf('<details class="tech"'));
      expect(nodes.bannerText.innerHTML).toContain('href="#step-19"');
      expect(nodes.bannerText.innerHTML).toContain("View 1 finding");
    });
  });

  test("opens the new current checkpoint when live progress advances", async () => {
    const initialPlan = JSON.stringify({
      feature: "Floating core",
      checkpoints: [
        { id: 18, title: "Move skill sources", size: "l", status: "pending", gates: {} },
        { id: 19, title: "Install every skill", size: "xl", status: "pending", gates: {} },
      ],
    });
    const advancedPlan = JSON.stringify({
      feature: "Floating core",
      checkpoints: [
        { id: 18, title: "Move skill sources", size: "l", status: "passed", gates: {} },
        {
          id: 19,
          title: "Install every skill",
          size: "xl",
          status: "pending",
          gates: {
            behavior: { status: "failed", attempts: 2, findings: ["Gate failed"] },
          },
        },
      ],
    });

    await withViewer({}, ({ api, nodes }) => {
      expect(api.load(initialPlan)).toBe(true);
      expect(api.load(advancedPlan)).toBe(true);
      expect(nodes.steps.innerHTML).toContain(
        '<details class="step failed current" id="step-19" data-id="19" open>',
      );
    });
  });
});

function stepCardHtml(stepsHtml: string, id: number): string {
  const at = stepsHtml.indexOf(`id="step-${id}"`);
  if (at < 0) throw new Error(`step ${id} card missing`);
  const start = stepsHtml.lastIndexOf('<details class="step', at);
  const next = stepsHtml.indexOf('<details class="step', at);
  return stepsHtml.slice(start, next < 0 ? undefined : next);
}

function isStepOpen(stepsHtml: string, id: number): boolean {
  return new RegExp(`<details class="step[^"]*" id="step-${id}" data-id="${id}"\\s*open\\s*>`).test(stepsHtml);
}

const hostileFinding = '<img src=x onerror=alert(1)> broke "init"';
const hostileFindingHtml =
  '<div class="finding"><b>Works:</b> &lt;img src=x onerror=alert(1)&gt; broke &quot;init&quot;</div>';
const objectFinding = { detail: "<script>steal()</script>" };
const objectFindingHtml =
  '<div class="finding"><b>Code review:</b> {&quot;detail&quot;:&quot;&lt;script&gt;steal()&lt;/script&gt;&quot;}</div>';

function findingsPlan(opts: { behaviorAttempts: number; haltedReason?: string }): string {
  return JSON.stringify({
    feature: "Floating core",
    ...(opts.haltedReason ? { halted: { reason: opts.haltedReason } } : {}),
    checkpoints: [
      { id: 22, title: "Earlier step", size: "m", status: "passed", gates: {} },
      {
        id: 23,
        title: "Keep findings visible",
        size: "l",
        status: "pending",
        gates: {
          behavior: { status: "failed", attempts: opts.behaviorAttempts, findings: [hostileFinding] },
          review: { status: "pending", attempts: 0, findings: [objectFinding] },
        },
      },
      { id: 24, title: "Later step", size: "l", status: "pending", gates: {} },
    ],
  });
}

function expectCurrentFindingsVisibleAndEscaped(stepsHtml: string): void {
  expect(isStepOpen(stepsHtml, 23)).toBe(true);
  const card = stepCardHtml(stepsHtml, 23);
  const techAt = card.indexOf('<details class="tech"');
  expect(techAt).toBeGreaterThan(-1);
  for (const findingHtml of [hostileFindingHtml, objectFindingHtml]) {
    const findingAt = card.indexOf(findingHtml);
    expect(findingAt).toBeGreaterThan(-1);
    expect(findingAt).toBeLessThan(techAt);
  }
  expect(stepsHtml).not.toContain("<img");
  expect(stepsHtml).not.toContain("<script");
}

describe("viewer-audit — checkpoint 23 live progress and visible findings", () => {
  const progressPlan = (opts: { isStep18Passed: boolean; step19Behavior?: object }): string =>
    JSON.stringify({
      feature: "Floating core",
      checkpoints: [
        { id: 18, title: "Move skill sources", size: "l", status: opts.isStep18Passed ? "passed" : "pending", gates: {} },
        {
          id: 19,
          title: "Install every skill",
          size: "xl",
          status: "pending",
          gates: opts.step19Behavior ? { behavior: opts.step19Behavior } : {},
        },
        { id: 20, title: "Ship the release", size: "m", status: "pending", gates: {} },
      ],
    });
  const before = progressPlan({ isStep18Passed: false });
  const advanced = progressPlan({ isStep18Passed: true });
  const retried = progressPlan({
    isStep18Passed: true,
    step19Behavior: { status: "failed", attempts: 1, findings: ["Gate failed"] },
  });

  async function withServedPlan(
    firstPlan: string,
    run: (harness: ViewerHarness, serve: (plan: string) => void) => Promise<void>,
  ): Promise<void> {
    let servedPlan = firstPlan;
    await withViewer(
      {
        search: "?plan=demo",
        fetchText: async (url) => {
          if (url === "./") return "";
          if (url === "./demo.json") return servedPlan;
          throw new Error("404");
        },
      },
      async (harness) => {
        await harness.api.servedInit();
        await run(harness, (plan) => {
          servedPlan = plan;
        });
      },
    );
  }

  test("a polled update that advances the current step opens the new step and keeps every other card as the person left it", async () => {
    await withServedPlan(before, async ({ nodes, tickAgain, setStepOpen }, serve) => {
      expect(isStepOpen(nodes.steps.innerHTML, 18)).toBe(true);
      expect(isStepOpen(nodes.steps.innerHTML, 19)).toBe(false);
      expect(isStepOpen(nodes.steps.innerHTML, 20)).toBe(false);

      setStepOpen(18, false);
      setStepOpen(20, true);
      serve(advanced);
      await tickAgain();
      expect(stepCardHtml(nodes.steps.innerHTML, 19)).toStartWith(
        '<details class="step running current" id="step-19" data-id="19" open>',
      );
      expect(isStepOpen(nodes.steps.innerHTML, 18)).toBe(false);
      expect(isStepOpen(nodes.steps.innerHTML, 20)).toBe(true);
    });
  });

  test("a polled update that keeps the current step leaves open and closed cards exactly as the person set them", async () => {
    await withServedPlan(advanced, async ({ nodes, tickAgain, setStepOpen }, serve) => {
      expect(isStepOpen(nodes.steps.innerHTML, 19)).toBe(true);

      setStepOpen(18, true);
      setStepOpen(19, false);
      serve(retried);
      await tickAgain();
      expect(nodes.steps.innerHTML).toContain("Gate failed");
      expect(isStepOpen(nodes.steps.innerHTML, 18)).toBe(true);
      expect(isStepOpen(nodes.steps.innerHTML, 19)).toBe(false);
      expect(isStepOpen(nodes.steps.innerHTML, 20)).toBe(false);
    });
  });

  test("clicking the banner link reopens the closed current card with its findings and scrolls to it", async () => {
    await withViewer({}, ({ api, nodes, setStepOpen, clickBannerLink, scrolledTo }) => {
      expect(api.load(findingsPlan({ behaviorAttempts: 1 }))).toBe(true);
      setStepOpen(23, false);
      expect(isStepOpen(nodes.steps.innerHTML, 23)).toBe(false);

      clickBannerLink();
      expectCurrentFindingsVisibleAndEscaped(nodes.steps.innerHTML);
      expect(scrolledTo).toEqual(["step-23"]);
    });
  });

  for (const { label, behaviorAttempts, bannerClass } of [
    { label: "fixing", behaviorAttempts: 1, bannerClass: "banner run" },
    { label: "stuck", behaviorAttempts: 3, bannerClass: "banner stop" },
  ]) {
    test(`active ${label} banner links to the current step findings shown escaped outside Technical details`, async () => {
      await withViewer({}, ({ api, nodes }) => {
        expect(api.load(findingsPlan({ behaviorAttempts }))).toBe(true);
        expect(nodes.banner.className).toBe(bannerClass);
        expect(nodes.bannerText.innerHTML).toEndWith(' · <a href="#step-23" data-go="23">View 2 findings</a>');
        expectCurrentFindingsVisibleAndEscaped(nodes.steps.innerHTML);
      });
    });
  }

  test("halted banner links to the current step findings shown escaped outside Technical details", async () => {
    await withViewer({}, ({ api, nodes }) => {
      expect(api.load(findingsPlan({ behaviorAttempts: 2, haltedReason: "approve <b>scope</b>" }))).toBe(true);
      expect(nodes.banner.className).toBe("banner stop");
      expect(nodes.bannerText.innerHTML).toBe(
        'Stopped. Needs your input: approve &lt;b&gt;scope&lt;/b&gt; · <a href="#step-23" data-go="23">View 2 findings</a>',
      );
      expectCurrentFindingsVisibleAndEscaped(nodes.steps.innerHTML);
    });
  });
});

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
