# Puppeteer patterns for verification specs

Read this while writing specs in Step 5, or when triaging a failure in Step 6. It exists because
the same handful of mistakes produce the same two bad outcomes every time: a test that passes when
the app is broken, or a test that fails when the app is fine. Both destroy the value of the verdict.

Specs run on `node --test` with `puppeteer-core` driving `chrome-headless-shell`. Everything you
need is exported from `.feature-verify/harness.mjs`.

## Contents

- [Harness API](#harness-api)
- [Selectors](#selectors)
- [Waiting](#waiting)
- [Spec shape](#spec-shape)
- [Diagnostics: console and page errors](#diagnostics-console-and-page-errors)
- [Forms](#forms)
- [Navigation and reload](#navigation-and-reload)
- [Dialogs, menus, and overlays](#dialogs-menus-and-overlays)
- [Network: stubbing and asserting](#network-stubbing-and-asserting)
- [Auth](#auth)
- [Regression smoke tests](#regression-smoke-tests)
- [Screenshots](#screenshots)
- [Diagnosing a failure](#diagnosing-a-failure)

## Harness API

```js
import { check, visible, hidden, count, text, value, url, poll, shot, browser, BASE_URL }
  from '../harness.mjs';
```

| Export | What it does |
|---|---|
| `check(name, fn)` | One acceptance criterion. Gives `fn` a fresh page, captures evidence on failure. |
| `visible(page, sel)` | Waits for the element to exist with a non-zero box. |
| `hidden(page, sel)` | Waits for it to be absent or zero-sized. |
| `count(page, sel, n)` | Waits for exactly `n` matches. |
| `text(page, sel, m)` | Waits for `innerText` to contain a string / match a RegExp. |
| `value(page, sel, v)` | Waits for an input's value. |
| `url(page, m)` | Waits for the page URL to match. |
| `poll(fn, {timeout})` | Escape hatch for a condition the above don't cover. |
| `shot(page, name, o)` | Screenshot into `artifacts/`. `{fullPage, deviceScaleFactor}`. |
| `browser()` | The shared browser instance — you rarely need it directly. |

Every assertion takes an options object as its last argument: `await visible(page, sel, { timeout: 15_000 })`.
Default timeout is 10s. `page.goto('/products')` resolves against `BASE_URL`, so pass paths, not URLs.

One browser is launched per spec file and reused for every page and screenshot in it. Don't launch
your own — a relaunch costs ~1.13s against ~0.19s reused.

## Selectors

Preference order, and the reason for it: a selector should break when the *user-visible behavior*
breaks and not before. Role and text selectors track what the user perceives; CSS class and DOM
path selectors track how the code happens to be written, which changes for reasons that have
nothing to do with correctness.

Puppeteer's `::-p-*` pseudo-selectors work anywhere a selector string is accepted (`page.$`,
`page.$$`, `page.locator`, and every harness assertion):

```js
page.locator('button::-p-aria(Save changes)')    // best: role + accessible name, what the user sees
page.locator('input::-p-aria(Email address)')    // form fields, via their label
page.locator('::-p-text(No results found)')      // static copy
page.locator('[data-testid="cart-total"]')       // when nothing else identifies it
page.locator('.btn-primary > span:nth-child(2)') // last resort; brittle by construction
```

**Anchor `::-p-aria(...)` to a tag.** An accessible name is computed from descendant text, so a
container inherits its child's name and matches too — bare `::-p-aria(Delete)` over a two-row table
returns **four** elements: two buttons and the two `<td>`s wrapping them. `page.$` then hands you the
cell instead of the button, and `count()` reports double. `button::-p-aria(Delete)` returns two.
`::-p-text(...)` does not have this problem.

Scope before you disambiguate. If two elements match, prefer narrowing the container over indexing —
index-based selection silently follows whatever happens to render first. Note that `:has()` does
**not** accept `::-p-*` selectors inside it (`tr:has(::-p-text(Acme))` throws a `SyntaxError`); use a
descendant combinator, or XPath plus a scoped query:

```js
// good: descendant combinator, p-selector on the right
await visible(page, '[role="dialog"] button::-p-aria(Confirm)');

// good: XPath finds the row, then query inside that handle
const row = await page.$('::-p-xpath(//tr[td[contains(.,"Acme Corp")]])');
await row.$('button::-p-aria(Delete)');

// avoid: (await page.$$('button::-p-aria(Delete)'))[1]
```

If an element has no accessible name and no test id, that is itself a finding — an element users
can't identify by role or label is usually also inaccessible to screen readers. Note it in the
report. Don't add a `data-testid` to the app; this skill doesn't edit app code.

## Waiting

Fixed sleeps are banned in these specs for a concrete reason: they encode a guess about machine
speed. They pass on your machine, fail on a slower one, and when they do fail they report "element
not visible" rather than "the request took 600ms". Every harness assertion polls until the condition
holds, and `page.locator(...)` waits for the element to be visible and actionable before acting — so
waiting and asserting are the same operation.

```js
// wrong
await page.click('#submit');
await new Promise(r => setTimeout(r, 1000));
assert.ok(await page.$('.toast'));

// right
await page.locator('button::-p-aria(Submit)').click();
await text(page, '[role="status"]', 'Saved');
```

For content that appears after a fetch, assert on the content — the assertion does the waiting.
When you need to wait on the request itself (rare), wait on the response, not on the clock:

```js
const res = page.waitForResponse(r => r.url().includes('/api/items') && r.ok());
await page.locator('button::-p-aria(Load more)').click();
await res;
```

Raise a single assertion's budget rather than the global timeout when one operation is genuinely
slow: `await visible(page, sel, { timeout: 15_000 })`.

## Spec shape

One acceptance criterion per `check()`, named in the language of the criterion. The name is what
lands in the report, so it should read as a claim about the product.

```js
// .feature-verify/specs/feature.test.mjs
import { check, visible, hidden, count, value } from '../harness.mjs';

check('typing in the search box narrows the visible rows to matches', async (page) => {
  await page.goto('/products');
  await page.locator('input::-p-aria(Search products)').fill('widget');
  await count(page, 'tbody tr:not([hidden])', 2);
  await hidden(page, '::-p-text(gadget)');
});

check('the filter survives a page reload', async (page) => {
  await page.goto('/products');
  await page.locator('input::-p-aria(Search products)').fill('widget');
  await count(page, 'tbody tr:not([hidden])', 2);
  await page.reload();
  await value(page, 'input::-p-aria(Search products)', 'widget');
  await count(page, 'tbody tr:not([hidden])', 2);
});
```

Assert the negative too. "Matches are shown" is half the criterion; "non-matches are gone" is the
half that catches a filter that renders everything.

Checks inside one file run in order, sharing a browser but not a page — each `check()` gets a fresh
page with a clean session. If a criterion genuinely depends on state left by a previous step, do
both steps in one `check()`.

## Diagnostics: console and page errors

`check()` already attaches `pageerror`, console-error, and HTTP-5xx listeners for you. On failure it
writes three files into `artifacts/`, named after the check:

- `<slug>.png` — full-page screenshot at the moment of failure
- `<slug>.html` — the DOM as it stood
- `<slug>.errors.txt` — collected browser errors, when there were any

and appends the evidence path plus the error list to the thrown error. An uncaught exception usually
names the real cause, turning "expected 3 rows, got 0" into "TypeError: cannot read property 'map'
of undefined at ProductTable.tsx:42". Read these before writing the "Likely cause" line of any
finding.

## Forms

```js
await page.locator('input::-p-aria(Email)').fill('user@example.com');
await page.select('select[name="country"]', 'CA');
await page.locator('input::-p-aria(Subscribe)').click();          // checkbox
await page.locator('button::-p-aria(Create account)').click();
await text(page, '[role="alert"]', 'Account created');
```

Validation is worth one check on its own — submit invalid input and assert the error appears *and*
that submission did not proceed. A form that shows an error and submits anyway passes a naive test.

```js
check('submitting an invalid email shows an error and does not create the account', async (page) => {
  await page.goto('/signup');
  await page.locator('input::-p-aria(Email)').fill('nope');
  await page.locator('button::-p-aria(Create account)').click();
  await visible(page, '::-p-text(Enter a valid email)');
  await url(page, /\/signup/);                                // still here, didn't navigate
});
```

## Navigation and reload

```js
await page.goto('/dashboard');                                // relative to BASE_URL
await page.locator('a::-p-aria(Settings)').click();
await url(page, /\/settings/);
await text(page, 'h1', 'Settings');                   // the heading, not the link
```

Client-side routing needs no explicit wait — assert on the destination's content and URL together.
Asserting URL alone passes even when the page renders an error boundary.

For a full document navigation you can await both at once:

```js
await Promise.all([
  page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
  page.locator('button::-p-aria(Sign out)').click(),
]);
```

## Dialogs, menus, and overlays

```js
await page.locator('button::-p-aria(Delete)').click();
await visible(page, '[role="dialog"]');
await page.locator('[role="dialog"] button::-p-aria(Confirm)').click();
await hidden(page, '[role="dialog"]');
```

Native `alert`/`confirm` need a handler registered *before* the action, or the page hangs:

```js
page.once('dialog', d => d.accept());
await page.locator('button::-p-aria(Reset)').click();
```

## Network: stubbing and asserting

Stub when the criterion is about how the UI *handles* a response — error and empty states are hard
to reach otherwise, and they're where regressions hide. Puppeteer needs interception enabled first,
and every request must then be either fulfilled or continued:

```js
await page.setRequestInterception(true);
page.on('request', (req) => {
  if (req.url().includes('/api/products')) req.respond({ status: 500, body: 'server error' });
  else req.continue();
});
await page.goto('/products');
await visible(page, "::-p-text(Couldn't load products)");
```

Don't stub the happy path when verifying a feature that owns the request — you'd be testing the
stub. Do stub third-party calls (payments, analytics, maps) so the verdict doesn't depend on
someone else's uptime; note any stubbing in the report's "Not covered" section.

## Auth

If the app requires login, sign in once and reuse the cookies rather than logging in per check. The
harness shares one browser per file, so a `beforeAll`-style helper works:

```js
import { check, browser, BASE_URL, visible } from '../harness.mjs';

let authed = false;
async function login() {
  if (authed) return;
  const page = await (await browser()).newPage();
  await page.goto(new URL('/login', BASE_URL).href);
  await page.locator('input::-p-aria(Email)').fill(process.env.E2E_EMAIL);
  await page.locator('input::-p-aria(Password)').fill(process.env.E2E_PASSWORD);
  await page.locator('button::-p-aria(Sign in)').click();
  await page.waitForNavigation();
  await page.close();                       // cookies persist on the shared browser context
  authed = true;
}

check('the dashboard shows the signed-in user', async (page) => {
  await login();
  await page.goto('/dashboard');
  await visible(page, 'button::-p-aria(Account menu)');
});
```

Never hardcode credentials in a spec — read them from env, and if there are none, say in the report
that authenticated flows went unverified rather than inventing a login.

## Regression smoke tests

Shallow and broad. The job is to prove a route still functions, not to re-test it.

```js
// .feature-verify/specs/regression.test.mjs
import { check, visible, hidden, text } from '../harness.mjs';

const ROUTES = [
  { url: '/',          heading: 'Dashboard' },
  { url: '/products',  heading: 'Products' },
  { url: '/settings',  heading: 'Settings' },   // control: untouched by the change
];

for (const { url: path, heading } of ROUTES) {
  check(`${path} still renders and its primary action works`, async (page) => {
    const res = await page.goto(path);
    if (res.status() >= 400) throw new Error(`${path} returned HTTP ${res.status()}`);
    await text(page, 'h1', heading);
    await hidden(page, '::-p-text(Something went wrong)');
    await hidden(page, '::-p-text(Application error)');
  });
}
```

The error-boundary assertion matters: a crashed React tree often still returns HTTP 200 with a
heading intact, so status and heading alone can both pass on a broken page.

## Screenshots

The harness's `shot()` is for the multi-shot case and reuses the browser. For a single one-off shot
with no waiting or interaction, skip Node entirely and call the binary — the path is in
`.feature-verify/config.json`:

```bash
chrome-headless-shell --headless --disable-gpu --hide-scrollbars \
  --screenshot=out.png --window-size=1280,720 --force-device-scale-factor=1 http://localhost:3000/products
```

It already waits for the load event; no extra wait flag is needed. Two or more shots, or anything
needing a wait, a full page, or interaction, goes through the harness:

```js
await shot(page, 'products-empty-state');                       // agent verification: dSF 1
await shot(page, 'products-full', { fullPage: true });
await shot(page, 'hero-for-review', { deviceScaleFactor: 3 });  // human deliverable only
```

`deviceScaleFactor: 3` is for deliverables a human will look at. On a tall full-page capture it is
wasted entirely: output is capped at 2000px on the long edge either way, so legibility scale =
`2000 / page_height_css`. 11px text needs the page under ~3100px tall; past ~3000px, shoot
viewport-sized sections instead of one full-page capture. That cap comes from how images are resized
before a model sees them, not from the machine — it carries over to any repo.

## Diagnosing a failure

1. **Read the error and the `artifacts/<slug>.errors.txt` first.** An exception in the console
   usually answers the question before you open anything else.
2. **Look at `artifacts/<slug>.png` and `<slug>.html`** — the screenshot and DOM at the moment the
   assertion gave up show you what was actually on the page when the selector missed.
3. **Reproduce manually** against the running dev server. If it works by hand, the test is wrong;
   fix the spec and re-run. That's not a defect and doesn't belong in the report as one.
4. **Check the control route.** If a route untouched by the change also fails, suspect the
   environment — server not up, missing env var, no seed data.
5. **Re-run the one check:** `node --test --test-name-pattern '<check name>' .feature-verify/specs/*.test.mjs`.
   Passing on a re-run means flaky: report it as unproven with what you observed, never as a pass.
