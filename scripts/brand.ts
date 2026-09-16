#!/usr/bin/env bun
/**
 * brand.ts — the {ai} engineering brand system, compiled.
 *
 * One file declares the brand (brand/tokens.json). This script is the only thing
 * allowed to turn that file into code. It answers four questions, each with an
 * exit code a machine can read:
 *
 *   bun scripts/brand.ts check     — is the token file itself valid?
 *   bun scripts/brand.ts gen       — write every artifact it produces
 *   bun scripts/brand.ts parity    — does what is committed still match the tokens?
 *   bun scripts/brand.ts contrast  — is every declared text/surface pair legible?
 *   bun scripts/brand.ts artifact  — do the inline artifact blocks agree with the brand?
 *   bun scripts/brand.ts legacy    — has the previous palette really gone?
 *
 * Why this exists: a palette that lives in five places is five palettes. The
 * landing site, the CLI banner and the design record are all downstream of
 * brand/tokens.json, and the parity gate makes drift a failing build rather
 * than a design review nobody ran.
 *
 * Regenerate with `bun scripts/brand.ts gen`. Never hand-edit a generated file.
 */

import { existsSync } from 'node:fs';
import { mkdir, readdir, readFile } from 'node:fs/promises';
import { dirname, join, relative, resolve } from 'node:path';

// ---------------------------------------------------------------------------
// Types — the shape of brand/tokens.json
// ---------------------------------------------------------------------------

interface TokenColor {
  readonly ref: string;
  readonly alpha?: number;
  readonly displayName: string;
  readonly purpose: string;
}

interface TypeStep {
  readonly family: 'sans' | 'mono';
  readonly size: string;
  readonly weight: number;
  readonly lineHeight: number;
  readonly letterSpacing: string;
  readonly width?: number;
}

export interface Tokens {
  readonly version: number;
  readonly name: string;
  readonly provenance: {
    readonly source: string;
    readonly url: string;
    readonly license: string;
    readonly retrieved: string;
    readonly families_copied_verbatim: readonly string[];
    readonly excluded: string;
    readonly trademark: string;
  };
  readonly families: Record<string, string | Record<string, string>>;
  readonly semantic: Record<string, Record<string, TokenColor>>;
  readonly pairs: readonly { readonly text: string; readonly surface: string; readonly min: number }[];
  readonly artifact: {
    readonly files: readonly string[];
    readonly tokens: Record<string, { readonly ref: string }>;
    readonly ungated: string;
  };
  readonly typography: {
    readonly families: Record<string, string>;
    readonly substitution_note: string;
    readonly scale: Record<string, TypeStep>;
  };
  readonly radius: { readonly [key: string]: string | Record<string, string> };
  readonly space: Record<string, string>;
  readonly shadow: Record<string, { readonly value: string; readonly purpose: string }>;
  readonly motion: Record<string, string>;
  readonly cli: {
    readonly marks: Record<string, string>;
    readonly [key: string]: string | Record<string, string> | undefined;
  };
}

// ---------------------------------------------------------------------------
// Loading and validation — `check`
// ---------------------------------------------------------------------------

const ROOT = resolve(import.meta.dir, '..');
const TOKENS_PATH = join(ROOT, 'brand', 'tokens.json');

/** The landing site is a sibling checkout. Override for another layout. */
const WEB_DIR = process.env.AI_ENGINEERING_WEB_DIR ?? resolve(ROOT, '..', 'ai-engineering-web');

const OUT = {
  css: join(WEB_DIR, 'src', 'styles', 'tokens.css'),
  cliTheme: join(ROOT, 'src', 'theme.ts'),
  designJson: join(WEB_DIR, '.impeccable', 'design.json'),
  /** The brand declaration itself, copied verbatim into the landing site — the site
   *  consumes the derived `tokens.css`, and this copy is what lets somebody working
   *  only in that repository read the whole system: the semantic layer, the reasons
   *  beside each value, the contrast pairs, the artifact vocabulary. It is generated
   *  and parity-checked like every other artifact, so "verbatim" is enforced rather
   *  than promised. */
  tokensJson: join(WEB_DIR, 'src', 'styles', 'tokens.json'),
} as const;

const HEX = /^#[0-9A-Fa-f]{6}$/;

/** Everything that must be true of the token file, said once.
 *
 *  Exported so a test can feed it broken declarations. Every other gate here has been
 *  observed failing; this one had only ever passed, which means a validator that had
 *  quietly stopped validating would have looked exactly the same. */
export function validate(t: Tokens): string[] {
  const problems: string[] = [];
  const fail = (msg: string) => problems.push(msg);

  if (t.version !== 1) fail(`version: expected 1, got ${String(t.version)}`);

  // 1. Every colour family is a hex string or a steps object of hex strings.
  for (const [family, value] of Object.entries(t.families)) {
    if (typeof value === 'string') {
      if (!HEX.test(value)) fail(`families.${family}: "${value}" is not a #RRGGBB hex`);
      continue;
    }
    const steps = Object.entries(value);
    if (steps.length < 2) fail(`families.${family}: a family needs at least two steps`);
    for (const [step, hex] of steps) {
      if (!HEX.test(hex)) fail(`families.${family}.${step}: "${hex}" is not a #RRGGBB hex`);
    }
    // Steps must run dark → light, or the "tonal ramp" in the design record lies.
    const lums = steps.map(([, hex]) => luminance(hex));
    for (let i = 1; i < lums.length; i++) {
      if (lums[i]! <= lums[i - 1]!) {
        fail(`families.${family}: step "${steps[i]![0]}" is not lighter than "${steps[i - 1]![0]}"`);
      }
    }
  }

  // 2. Every semantic token points at something that exists.
  const colourNames: Record<string, true> = {};
  for (const [group, entries] of Object.entries(t.semantic)) {
    for (const [name, token] of Object.entries(entries)) {
      colourNames[name] = true;
      if (resolveRef(t, token.ref) === null) fail(`semantic.${group}.${name}: unknown ref "${token.ref}"`);
      if (token.alpha !== undefined && (token.alpha <= 0 || token.alpha > 1)) {
        fail(`semantic.${group}.${name}: alpha must be within (0, 1], got ${String(token.alpha)}`);
      }
      if (
        typeof token.displayName !== 'string' ||
        typeof token.purpose !== 'string' ||
        token.displayName.trim() === '' ||
        token.purpose.trim() === ''
      ) {
        fail(`semantic.${group}.${name}: needs both a displayName and a purpose`);
      }
    }
  }

  // 3. The contrast gate must have something to check, and only knows two levels.
  if (t.pairs.length === 0) fail('pairs: the contrast gate would check nothing');
  for (const pair of t.pairs) {
    if (!colourNames[pair.text]) fail(`pairs: "${pair.text}" is not a declared text token`);
    const surface = resolveRef(t, pair.surface);
    if (surface === null && !colourNames[pair.surface]) fail(`pairs: "${pair.surface}" resolves to nothing`);
    if (pair.min !== 4.5 && pair.min !== 3) fail(`pairs: ${pair.text}/${pair.surface} min must be 4.5 or 3`);
  }

  // 4. Type, spacing, radius, motion — the sections the generators read.
  for (const required of ['families', 'substitution_note', 'scale'] as const) {
    if (!(required in t.typography)) fail(`typography.${required}: missing`);
  }
  for (const [step, spec] of Object.entries(t.typography.scale)) {
    if (!(spec.family in t.typography.families)) fail(`typography.scale.${step}: unknown family "${spec.family}"`);
    if (spec.weight < 100 || spec.weight > 900 || spec.weight % 100 !== 0) {
      fail(`typography.scale.${step}: weight ${String(spec.weight)} is not a valid step`);
    }
  }
  for (const key of ['display', 'headline', 'title', 'body', 'label', 'code', 'stat']) {
    if (!(key in t.typography.scale)) fail(`typography.scale: "${key}" is required by the stylesheet`);
  }
  for (const key of ['xs', 'sm', 'md', 'lg', 'pill'] as const) {
    if (typeof t.radius[key] !== 'string') fail(`radius.${key}: missing`);
  }
  const radiusMap = t.radius['map'];
  if (typeof radiusMap !== 'object') fail('radius.map: missing');
  else {
    for (const [use, step] of Object.entries(radiusMap)) {
      if (!(step in t.radius)) fail(`radius.map.${use}: points at unknown radius "${step}"`);
    }
  }
  for (const key of ['maxw', 'maxw-prose', 'gutter', 'section-y'] as const) {
    if (!t.space[key]) fail(`space.${key}: missing`);
  }
  for (const key of ['lit-edge', 'window', 'card', 'glow'] as const) {
    if (!t.shadow[key]) fail(`shadow.${key}: missing`);
  }
  for (const key of ['ease-out', 'dur-fast', 'rise-dur', 'stagger-step'] as const) {
    if (!t.motion[key]) fail(`motion.${key}: missing`);
  }
  if (!t.cli.marks['ok']) fail('cli.marks.ok: missing');
  if (!t.cli.marks['head']) fail('cli.marks.head: missing');
  for (const key of ['banner-green', 'banner-meta'] as const) {
    if (!t.cli[key]) fail(`cli.${key}: missing`);
  }

  // 5. Values that reach the generated files must be the right KIND of value. A number
  // where a string belongs produces a declaration the browser drops in silence —
  // `--fs-code: 13;` is not a font-size — and a silently dropped type step is a defect no
  // other check here can see, because every other check reads what was generated, not
  // what should have been.
  for (const [name, value] of Object.entries(t.space)) {
    if (typeof value !== 'string') fail(`space.${name}: must be a string, got ${typeof value}`);
  }
  for (const [name, entry] of Object.entries(t.shadow)) {
    if (typeof entry.value !== 'string') fail(`shadow.${name}.value: must be a string`);
  }
  for (const [name, value] of Object.entries(t.motion)) {
    if (typeof value !== 'string') fail(`motion.${name}: must be a string`);
  }
  for (const [step, value] of Object.entries(t.radius)) {
    if (step !== 'map' && typeof value !== 'string') fail(`radius.${step}: must be a string`);
  }
  for (const [step, spec] of Object.entries(t.typography.scale)) {
    // `size` and `letterSpacing` are lengths and go to CSS verbatim; `lineHeight` is a
    // unitless ratio and is legitimately a number. Demanding the wrong kind here is how a
    // validator becomes the thing that breaks the build — this file's own oracle caught
    // exactly that on its first run.
    for (const key of ['size', 'letterSpacing'] as const) {
      if (typeof spec[key] !== 'string') fail(`typography.scale.${step}.${key}: must be a string`);
    }
    if (typeof spec.lineHeight !== 'number') fail(`typography.scale.${step}.lineHeight: must be a number`);
  }
  for (const [name, value] of Object.entries(t.cli)) {
    if (typeof value !== 'string' && typeof value !== 'object') fail(`cli.${name}: must be a string or a map`);
  }

  return problems;
}

export async function loadTokens(): Promise<Tokens> {
  const raw = await readFile(TOKENS_PATH, 'utf8');
  return JSON.parse(raw) as Tokens;
}

/** "green.base" → the hex in families.green.base. Unknown refs return null. */
function resolveRef(t: Tokens, ref: string): string | null {
  const [family, step] = ref.split('.');
  if (family === undefined) return null;
  const entry = t.families[family];
  if (entry === undefined) return null;
  if (typeof entry === 'string') return step === undefined ? entry : null;
  if (step === undefined) return null;
  return entry[step] ?? null;
}

/** A semantic token, resolved to the CSS colour it stands for. */
function colourOf(t: Tokens, name: string): string {
  for (const entries of Object.values(t.semantic)) {
    const token = entries[name];
    if (!token) continue;
    const hex = resolveRef(t, token.ref);
    if (hex === null) throw new Error(`unresolvable token: ${name} → ${token.ref}`);
    return token.alpha === undefined ? hex : rgba(hex, token.alpha);
  }
  throw new Error(`unknown token: ${name}`);
}

function rgba(hex: string, alpha: number): string {
  const n = parseInt(hex.slice(1), 16);
  const r = (n >> 16) & 255;
  const g = (n >> 8) & 255;
  const b = n & 255;
  return `rgba(${r}, ${g}, ${b}, ${Number(alpha.toFixed(3))})`;
}

// ---------------------------------------------------------------------------
// Colour maths — WCAG 2.1 relative luminance and contrast ratio
// ---------------------------------------------------------------------------

function channel(v: number): number {
  const s = v / 255;
  return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
}

export function luminance(hex: string): number {
  const n = parseInt(hex.slice(1), 16);
  return (
    0.2126 * channel((n >> 16) & 255) + 0.7152 * channel((n >> 8) & 255) + 0.0722 * channel(n & 255)
  );
}

/** The over-4.5-or-not number, computed rather than trusted. */
export function contrast(a: string, b: string): number {
  const la = luminance(a);
  const lb = luminance(b);
  const [hi, lo] = la > lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

/** Composite a translucent colour over an opaque one, so contrast is real. */
function over(fg: string, bg: string): string {
  const m = /^rgba\((\d+), (\d+), (\d+), ([0-9.]+)\)$/.exec(fg);
  if (m === null) return fg;
  const [r, g, b, a] = [Number(m[1]), Number(m[2]), Number(m[3]), Number(m[4])];
  const n = parseInt(bg.slice(1), 16);
  const mix = (f: number, s: number): number => Math.round(f * a + s * (1 - a));
  const hex = (v: number): string => v.toString(16).padStart(2, '0');
  return `#${hex(mix(r, (n >> 16) & 255))}${hex(mix(g, (n >> 8) & 255))}${hex(mix(b, n & 255))}`;
}

// ---------------------------------------------------------------------------
// Generators — the three artifacts
// ---------------------------------------------------------------------------

const BANNER = 'GENERATED FILE — do not edit. Source: brand/tokens.json. Regenerate: bun scripts/brand.ts gen';

function genCss(t: Tokens): string {
  const r = t.radius;
  const scale = t.typography.scale;
  const line = (name: string, value: string, note?: string): string =>
    `  --${name}: ${value};${note ? ` /* ${note} */` : ''}`;

  const groups: string[] = [
    [
      '/* Surfaces — the dark field and what sits on it. */',
      line('bg-deep', colourOf(t, 'bg')),
      line('bg-mid', colourOf(t, 'bg-mid')),
      line('surface-1', colourOf(t, 'surface-1')),
      line('surface-2', colourOf(t, 'surface-2')),
      line('surface-glass', colourOf(t, 'surface-glass')),
      line('surface-ivory', colourOf(t, 'surface-ivory'), 'the one light surface'),
      line('border', colourOf(t, 'border')),
      line('border-strong', colourOf(t, 'border-strong')),
      line('hairline', colourOf(t, 'hairline')),
      line('hairline-soft', colourOf(t, 'hairline-soft')),
    ].join('\n'),
    [
      '/* Text. `muted` is the AA floor for anything a reader must read; `muted-dim` is decoration only. */',
      line('text', colourOf(t, 'text')),
      line('text-body', colourOf(t, 'text-body')),
      line('muted', colourOf(t, 'muted')),
      line('muted-dim', colourOf(t, 'muted-dim')),
      line('on-accent', colourOf(t, 'on-accent')),
      line('on-ivory', colourOf(t, 'on-ivory')),
      line('on-ivory-muted', colourOf(t, 'on-ivory-muted')),
    ].join('\n'),
    [
      '/* One signal colour. Base is for fills and large UI; the light step is for small green. */',
      line('accent', colourOf(t, 'accent')),
      line('accent-text', colourOf(t, 'accent-text')),
      line('accent-hi', colourOf(t, 'accent-hi')),
      line('accent-deep', colourOf(t, 'accent-deep')),
      line('link', colourOf(t, 'link')),
      line('focus', colourOf(t, 'focus')),
      line('success', colourOf(t, 'success')),
      line('warn', colourOf(t, 'warn')),
      line('danger', colourOf(t, 'danger')),
    ].join('\n'),
    [
      '/* Decoration. Never carries meaning on its own. */',
      line('grid', colourOf(t, 'grid')),
      line('bracket', colourOf(t, 'bracket')),
      line('spot', colourOf(t, 'spot')),
    ].join('\n'),
    [
      '/* Depth: a neutral lit edge and three shadows. No grey-on-grey Material elevation. */',
      line('lit-edge', t.shadow['lit-edge']!.value),
      line('shadow-window', t.shadow['window']!.value),
      line('shadow-card', t.shadow['card']!.value),
      line('glow-brand', t.shadow['glow']!.value),
    ].join('\n'),
    [
      '/* Type. Two voices: Archivo for language, JetBrains Mono for instruments. */',
      line('font-sans', t.typography.families['sans']!),
      line('font-mono', t.typography.families['mono']!),
      line('fs-display', scale['display']!.size),
      line('fs-h2', scale['headline']!.size),
      line('fs-h3', scale['title']!.size),
      line('fs-body', scale['body']!.size),
      line('fs-small', '0.82rem'),
      line('fs-eyebrow', scale['label']!.size),
      line('fs-code', scale['code']!.size),
      line('fs-stat', scale['stat']!.size),
      line('fw-display', String(scale['display']!.weight)),
      line('lh-body', String(scale['body']!.lineHeight)),
      line('tracking-display', scale['display']!.letterSpacing),
    ].join('\n'),
    [
      '/* Layout */',
      line('maxw', t.space['maxw']!),
      line('maxw-prose', t.space['maxw-prose']!),
      line('gutter', t.space['gutter']!),
      line('section-y', t.space['section-y']!),
      ...Object.entries(r)
        .filter(([step]) => step !== 'map')
        .map(([step, value]) => line(`radius-${step}`, String(value))),
    ].join('\n'),
    [
      '/* Motion — one easing vocabulary, one reveal. */',
      ...Object.entries(t.motion).map(([name, value]) => line(name, value)),
    ].join('\n'),
  ];

  return `/*\n * ${BANNER}\n *\n * ${t.provenance.source} (${t.provenance.license}).\n * ${t.provenance.trademark}\n */\n:root {\n${groups.join('\n\n')}\n}\n`;
}

function genCliTheme(t: Tokens): string {
  const marks = t.cli.marks as Record<string, string>;
  const markLines = Object.entries(marks)
    .map(([name, value]) => `  ${name}: '${value}',`)
    .join('\n');

  return `// ${BANNER}
//
// The terminal owns its own background, so the CLI never paints prose in the brand
// green: the banner frame and braces carry the brand, the wordmark is left at the
// terminal's default foreground (legible on a light terminal and a dark one alike),
// and the status marks use the terminal's own named ANSI colours, which every theme
// already tunes for legibility. Under NO_COLOR or a piped stdout, styleText returns
// the text untouched and the CLI emits no escape bytes at all.

/** The one brand colour in the terminal: the banner frame and its braces. */
export const BANNER_GREEN = '${colourOf(t, t.cli['banner-green'] as string)}';

/** The dim version line under the logo. */
export const BANNER_META = '${t.cli['banner-meta'] as string}';

/** Status marks, by terminal-native colour name. */
export const MARKS = {
${markLines}
} as const;
`;
}

/**
 * Measure every declared pair. A translucent surface is composited over the field
 * (and translucent text over that) before it is measured: contrast against an
 * imaginary colour is not a measurement. Both the CLI gate and the design record
 * read these numbers, so they can never disagree.
 */
function measurePairs(t: Tokens): { text: string; surface: string; min: number; ratio: number }[] {
  return t.pairs.map((pair) => {
    const bgRaw = surfaceColour(t, pair.surface);
    const bg = bgRaw.startsWith('rgba') ? over(bgRaw, colourOf(t, 'bg')) : bgRaw;
    const fgRaw = colourOf(t, pair.text);
    return {
      text: pair.text,
      surface: pair.surface,
      min: pair.min,
      ratio: Number(contrast(fgRaw.startsWith('rgba') ? over(fgRaw, bg) : fgRaw, bg).toFixed(3)),
    };
  });
}

/**
 * The min-widths the stylesheet actually uses.
 *
 * Derived, never hand-listed: the previous design record claimed "560 / 640 / 900",
 * and the CSS uses 560, 620, 640, 720, 780, 880 and 920 — 900 does not exist anywhere
 * in it. A field that describes the responsive system is only worth carrying if it
 * cannot disagree with the CSS, so it is measured from the CSS.
 */
async function responsiveThresholds(): Promise<string[]> {
  const widths: Record<number, true> = {};
  for await (const file of walk(join(WEB_DIR, 'src'))) {
    if (!/\.(css|astro)$/.test(file)) continue;
    let text: string;
    try {
      text = await readFile(file, 'utf8');
    } catch {
      continue;
    }
    for (const match of text.matchAll(/min-width:\s*(\d+)px/g)) widths[Number(match[1])] = true;
  }
  return Object.keys(widths)
    .map(Number)
    .sort((a, b) => a - b)
    .map((px) => `${px}px`);
}

function genDesignJson(t: Tokens, breakpoints: readonly string[]): string {
  const colorMeta: Record<string, unknown> = {};
  for (const [group, entries] of Object.entries(t.semantic)) {
    const role =
      group === 'accent' ? 'primary' : group === 'state' ? 'state' : 'neutral';
    for (const [name, token] of Object.entries(entries)) {
      const hex = resolveRef(t, token.ref)!;
      const family = t.families[token.ref.split('.')[0]!];
      const ramp =
        typeof family === 'string' ? [family] : Object.values(family as Record<string, string>);
      colorMeta[name] = {
        role,
        displayName: token.displayName,
        canonical: token.alpha === undefined ? hex : rgba(hex, token.alpha),
        tonalRamp: ramp,
        purpose: token.purpose,
      };
    }
  }

  const typographyMeta: Record<string, unknown> = {};
  for (const [name, spec] of Object.entries(t.typography.scale)) {
    typographyMeta[name] = {
      displayName: name[0]!.toUpperCase() + name.slice(1),
      purpose: `${spec.family === 'mono' ? 'JetBrains Mono' : 'Archivo'} · ${spec.size} · weight ${spec.weight} · lh ${spec.lineHeight}${spec.width === undefined ? '' : ` · width ${spec.width}%`}.`,
    };
  }

  const doc = {
    schemaVersion: 2,
    // Deterministic on purpose: the record describes a dated palette, so it carries
    // the palette's date, not the machine's clock. That keeps `gen` idempotent.
    generatedAt: `${t.provenance.retrieved}T00:00:00Z`,
    title: `Design System: ${t.name}`,
    extensions: {
      provenance: t.provenance,
      substitution: t.typography.substitution_note,
      colorMeta,
      typographyMeta,
      shadows: Object.entries(t.shadow).map(([name, s]) => ({
        name,
        value: s.value,
        purpose: s.purpose,
      })),
      motion: Object.entries(t.motion).map(([name, value]) => ({ name, value })),
      radius: Object.fromEntries(
        Object.entries(t.radius).filter(([k]) => k !== 'map').map(([k, v]) => [k, String(v)]),
      ),
      typography: t.typography,
      breakpoints: {
        note: 'The min-widths this site actually uses, measured from src/**. They are not a normalised scale, and this list says so rather than inventing one.',
        values: breakpoints,
      },
      accessibility: { pairs: measurePairs(t) },
    },
    components: COMPONENT_SPECIMENS.map((c) => ({ ...c })),
  };

  return `${JSON.stringify(doc, null, 2)}\n`;
}

/** The surface side of a pair may be another token or a raw family ref. */
function surfaceColour(t: Tokens, name: string): string {
  const direct = resolveRef(t, name);
  if (direct !== null) return direct;
  return colourOf(t, name);
}

const COMPONENT_SPECIMENS = [
  {
    name: 'Primary Button',
    kind: 'button',
    refersTo: 'button',
    description: 'Solid brand green, small radius, dark ink. Lifts with the brand halo.',
    html: '<button class="ds-btn-primary">Install in under a minute</button>',
    css: '.ds-btn-primary { display:inline-flex; align-items:center; gap:0.5rem; min-height:44px; font-family:var(--font-sans); font-weight:600; font-size:0.95rem; padding:0.7rem 1.35rem; border-radius:var(--radius-sm); border:1px solid transparent; background:var(--accent); color:var(--on-accent); cursor:pointer; transition:transform var(--dur-fast) var(--ease-out), box-shadow var(--dur-fast) var(--ease-out); }',
  },
  {
    name: 'Ghost Button',
    kind: 'button',
    refersTo: 'button',
    description: 'Transparent secondary action with a neutral hairline.',
    html: '<button class="ds-btn-ghost">Read the source on GitHub</button>',
    css: '.ds-btn-ghost { display:inline-flex; align-items:center; gap:0.5rem; min-height:44px; font-family:var(--font-sans); font-weight:600; font-size:0.95rem; padding:0.7rem 1.35rem; border-radius:var(--radius-sm); border:1px solid var(--border); background:transparent; color:var(--text); cursor:pointer; }',
  },
  {
    name: 'Terminal Window',
    kind: 'custom',
    refersTo: 'window',
    description: 'The signature container: window chrome over command output.',
    html: '<div class="ds-window"><div class="ds-window__bar"><span class="ds-dots"><i></i><i></i><i></i></span><span class="ds-window__title">ai-eng — zsh</span></div><div class="ds-window__body"><pre class="ds-code"><span class="ds-prompt">$</span> <span class="ds-cmd">ai-eng doctor</span>\n<span class="ds-tag">✓</span> guards · contract · carriers</pre></div></div>',
    css: '.ds-window { border:1px solid var(--border); border-radius:var(--radius-lg); background:var(--surface-2); box-shadow:var(--shadow-window), var(--lit-edge); overflow:hidden; } .ds-window__bar { display:flex; align-items:center; gap:0.75rem; padding:0.6rem 1rem; border-bottom:1px solid var(--hairline); } .ds-window__title { font-family:var(--font-mono); font-size:0.82rem; color:var(--muted); }',
  },
  {
    name: 'Card',
    kind: 'card',
    refersTo: 'card',
    description: 'Surface card in the large radius the brand uses, with a cursor spotlight.',
    html: '<div class="ds-card"><h3 class="ds-card__title">Denied before it runs</h3><p class="ds-card__body">A guard screens the tool call and stops the destructive one before it executes.</p></div>',
    css: '.ds-card { position:relative; border:1px solid var(--hairline); border-radius:var(--radius-lg); background:var(--surface-1); box-shadow:var(--lit-edge); padding:1.5rem 1.6rem; } .ds-card:hover { border-color:var(--border-strong); box-shadow:var(--shadow-card), var(--lit-edge); }',
  },
  {
    name: 'Eyebrow',
    kind: 'label',
    refersTo: 'eyebrow',
    description: 'Monospace kicker above a section heading.',
    html: '<p class="ds-eyebrow">QUICK START</p>',
    css: '.ds-eyebrow { font-family:var(--font-mono); font-size:var(--fs-eyebrow); font-weight:600; letter-spacing:0.18em; text-transform:uppercase; color:var(--accent-text); margin:0 0 0.75rem; }',
  },
  {
    name: 'Stat Tile',
    kind: 'custom',
    refersTo: 'stat',
    description: 'The count-up readout: a large tabular number over a muted label.',
    html: '<div class="ds-stat"><span class="ds-stat__num">20</span><span class="ds-stat__label">skills</span></div>',
    css: '.ds-stat { display:flex; flex-direction:column; gap:0.25rem; } .ds-stat__num { font-family:var(--font-sans); font-weight:800; font-size:var(--fs-stat); line-height:1; letter-spacing:var(--tracking-display); color:var(--accent); font-variant-numeric:tabular-nums; } .ds-stat__label { font-family:var(--font-mono); font-size:var(--fs-small); color:var(--muted); }',
  },
] as const;

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

async function sameAsOnDisk(path: string, contents: string): Promise<boolean> {
  try {
    return (await readFile(path, 'utf8')) === contents;
  } catch {
    return false;
  }
}

/**
 * Every generated artifact, rendered. One function because `gen` and `parity` must
 * compute the same bytes: a parity check that renders its own way is a check that lies.
 */
async function renderArtifacts(t: Tokens): Promise<[string, string][]> {
  return [
    [OUT.css, genCss(t)],
    [OUT.cliTheme, genCliTheme(t)],
    [OUT.designJson, genDesignJson(t, await responsiveThresholds())],
    // Verbatim: the bytes of the declaration, not a rendering of it.
    [OUT.tokensJson, await readFile(TOKENS_PATH, 'utf8')],
  ];
}

async function cmdGen(t: Tokens): Promise<number> {
  for (const [path, contents] of await renderArtifacts(t)) {
    await mkdir(dirname(path), { recursive: true });
    await Bun.write(path, contents);
    console.log(`wrote ${relative(process.cwd(), path) || path}`);
  }
  return 0;
}

/**
 * The one palette value committed to a hand-written file. Returns the problem, or
 * null when it agrees — including when the sibling checkout is absent, because a
 * missing repository is not a drift.
 */
async function themeColorDrift(t: Tokens): Promise<string | null> {
  const file = join(WEB_DIR, 'src', 'layouts', 'Base.astro');
  let text: string;
  try {
    text = await readFile(file, 'utf8');
  } catch {
    return null;
  }
  const found = /<meta\s+name="theme-color"\s+content="([^"]+)"/.exec(text)?.[1];
  if (found === undefined) return `${file}: no theme-color meta tag — the browser chrome has no field colour.`;
  const expected = colourOf(t, 'bg');
  return found.toLowerCase() === expected.toLowerCase()
    ? null
    : `${file}: theme-color is ${found}, but the field is ${expected}. The mobile browser paints its chrome with the stale one.`;
}

async function cmdParity(t: Tokens): Promise<number> {
  const artifacts = await renderArtifacts(t);
  let drifted = 0;
  for (const [path, contents] of artifacts) {
    const ok = await sameAsOnDisk(path, contents);
    console.log(`${ok ? 'ok  ' : 'DRIFT'} ${relative(process.cwd(), path) || path}`);
    if (!ok) drifted++;
  }

  // `theme-color` is the one palette value that lives in a hand-written file: the
  // browser paints the mobile chrome with it, so a stale value is visible on every
  // phone while every other check stays green. It is compared, not generated —
  // writing it would mean a generator editing markup it does not own.
  const theme = await themeColorDrift(t);
  console.log(`${theme === null ? 'ok  ' : 'DRIFT'} src/layouts/Base.astro theme-color`);
  if (theme !== null) {
    console.error(`\n${theme}`);
    console.error('  Fix: edit the meta tag. `gen` owns the generated files, not markup.');
    return 1;
  }
  if (drifted > 0) {
    console.error(`\n${drifted} generated file(s) do not match brand/tokens.json. Run: bun scripts/brand.ts gen`);
    return 1;
  }
  console.log(`\n${artifacts.length} generated files and the theme-color meta match brand/tokens.json.`);
  return 0;
}

/**
 * The values the artifact block must declare, resolved from the brand source.
 * Refs may name any semantic colour, any family step, or a typography family path.
 */
function artifactExpected(t: Tokens): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [name, token] of Object.entries(t.artifact.tokens)) {
    if (token.ref.startsWith('typography.families.')) continue;
    const hex = resolveRef(t, token.ref);
    out[name] = hex === null ? colourOf(t, token.ref) : hex;
  }
  return out;
}

/** The `--name: value;` declarations of a file's FIRST `:root` block.
 *
 *  First, not all: the artifact canon also carries deliberate overrides for
 *  `@media (prefers-contrast: more)`, and those set different values for the same
 *  names on purpose. The base block is the one under test here. */
function rootTokens(text: string): Record<string, string> {
  const block = /:root\s*\{([^}]*)\}/.exec(text);
  if (block === null) return {};
  const out: Record<string, string> = {};
  for (const decl of (block[1] ?? '').matchAll(/--([a-z0-9-]+)\s*:\s*([^;]+);/g)) {
    out[decl[1]!] = decl[2]!.trim();
  }
  return out;
}

/** `rgba(61,79,88,.3)` and `rgba(61, 79, 88, 0.3)` are the same colour. */
function normalise(value: string): string {
  return value
    .toLowerCase()
    .replace(/\s+/g, '')
    .replace(/([(,])\.(\d)/g, '$10.$2');
}

/**
 * Where the remedy for the one blocked file is written, printed beside the failure so that
 * whoever runs the gate — a person, or CI — gets the route as well as the diagnosis. Only
 * named when it is actually there: a fresh clone has no handover, and pointing at a missing
 * document is the kind of help that wastes the reader's time.
 */
function remedyLine(): string {
  const path = join(ROOT, '.ai-engineering', 'brand', 'HANDOVER.md');
  return existsSync(path) ? `\nWhere the remaining fix is written: ${relative(process.cwd(), path)}` : '';
}

/**
 * The artifact gate. Each generated artifact inlines its own token block — it has to,
 * to render standalone — and that is exactly how one palette becomes three. So the
 * block is checked against brand/tokens.json instead of trusted: the canon's reference
 * block must declare every colour the brand defines, and every generated template must
 * agree with the reference name for name, value for value.
 */
async function cmdArtifact(t: Tokens): Promise<number> {
  const { problems, rows } = await artifactDrift(t);
  console.log(rows.join('\n'));
  if (problems.length > 0) {
    console.error(`\n${problems.join('\n')}`);
    console.error(`\nThe artifacts and the brand source disagree. Fix the file each message names — an artifact that renders in the retired palette is a second product.${remedyLine()}`);
    return 1;
  }
  console.log(`\n${t.artifact.files.length} artifact files agree with brand/tokens.json.`);
  return 0;
}

/**
 * Every disagreement between the artifact token blocks and the brand source.
 * Exported so tests/artifact-brand.spec.ts can assert it directly, rather than
 * pinning a second copy of the palette in a test file — which is exactly the
 * duplication this gate exists to end.
 */
export async function artifactDrift(
  t: Tokens,
): Promise<{ problems: string[]; rows: string[] }> {
  const expected = artifactExpected(t);
  const problems: string[] = [];
  const rows: string[] = [];
  let reference: Record<string, string> | null = null;

  for (const rel of t.artifact.files) {
    const declared = rootTokens(await readFile(join(ROOT, rel), 'utf8'));
    if (Object.keys(declared).length === 0) {
      problems.push(`${rel}: no :root token block found`);
      continue;
    }
    const drift: string[] = [];
    if (reference === null) {
      reference = declared;
      for (const [name, value] of Object.entries(expected)) {
        const actual = declared[name];
        if (actual === undefined) drift.push(`--${name} is missing (brand says ${value})`);
        else if (normalise(actual) !== normalise(value)) drift.push(`--${name} is ${actual}, brand says ${value}`);
      }
    } else {
      for (const [name, value] of Object.entries(declared)) {
        const canonical = reference[name];
        if (canonical === undefined) drift.push(`--${name} is not in the reference block`);
        else if (normalise(canonical) !== normalise(value)) drift.push(`--${name}: ${value} vs ${canonical}`);
      }
    }
    if (drift.length > 0) {
      problems.push(`${rel}:\n    ${drift.join('\n    ')}`);
      rows.push(`FAIL ${rel}`);
    } else {
      rows.push(`ok   ${rel} — ${Object.keys(declared).length} tokens`);
    }
  }
  return { problems, rows };
}

function cmdContrast(t: Tokens): number {
  const measured = measurePairs(t);
  const failures = measured.filter((m) => m.ratio < m.min);
  for (const m of measured) {
    console.log(
      `${m.ratio >= m.min ? 'PASS' : 'FAIL'}  ${m.text.padEnd(16)} on ${m.surface.padEnd(15)} ${m.ratio.toFixed(2).padStart(6)}:1  (needs ${m.min.toFixed(1)})`,
    );
  }
  console.log(`\n${measured.length - failures.length}/${measured.length} pairs meet their WCAG 2.1 level.`);
  return failures.length === 0 ? 0 : 1;
}

/** The previous palette, in both of the forms it actually shipped in.
 *
 *  Two vocabularies were retired, not one: the original teal-on-navy brand, and a
 *  second, never-declared variant that had grown inside the product blueprint and the
 *  recap skill (Tailwind-flavoured state colours and a lighter teal for light
 *  backgrounds). A palette that exists in two undocumented variants is exactly what
 *  this gate is for, so both lists are checked. */
const LEGACY = [
  // the retired {ai} brand
  '0B1120',
  '162844',
  '111C32',
  '00D4AA',
  '5FE6C6',
  '7EF7DE',
  '2EB39A',
  'F8FAFB',
  'A9BBD0',
  '0B8A6F', // the light-banner accent, a teal that only ever existed in that SVG
  '121E36', // artifact surface
  '0E1830', // artifact surface-2
  'B0C2D6', // artifact dim
  // the retired blueprint/recap variant
  '22c55e',
  'ef4444',
  'eab308',
  'f97316',
  'a855f7',
  '7dd3fc',
  '6b87a6',
  '94A3B8',
  'F1F5F9',
  '3d5273', // blueprint diagram edge, a blue-grey that was never a token
  '5b7089', // blueprint footer text, same
  'CBD8E6', // the old more-contrast override for --dim
  'B4C4D6', // the old more-contrast override for --comment
  '22d3ee', // blueprint pill border, Tailwind cyan, never a token
  // The artifact system's own state and syntax colours. The migration moved them, and
  // the gate was never told about them: a value nobody lists is a value the gate cannot
  // see come back. Found by testing this list against the retired files themselves.
  '9DB3CA', // artifact comment colour
  '4ade80', // artifact ok
  'fbb1b1', // artifact bad
  'facc15', // artifact warn
  'c084fc', // artifact purple
  'fb923c', // artifact "orange"
  '9DB2C9', // the generation before last: named in the old tokens.css comment
] as const;

/** Values the retired files contain that are deliberately NOT retired.
 *
 *  `#000000` is shadow black and is still in use (`rgba(0, 0, 0, 0.75)`); listing it would
 *  fire on every shadow. The old design record's ~53 tonal-ramp stops are derived tints of
 *  the retired colours — unreachable now, because the generator emits only the current
 *  palette, and listing them would bury a real finding under near-matches. */


/** Files allowed to remember the old palette: history, machine reports, and this gate itself. */
const LEGACY_ALLOW = [
  /CHANGELOG/i,
  /history/i,
  /_legacy/i,
  /DECISIONS\.md$/, // the log of what was decided; a decision about a retired value has to be able to name it
  /specs\//, // specs are the record of what was decided, including decisions since replaced
  /brand\/tokens\.json$/,
  /scripts\/brand\.ts$/,
  /reports\//, // mutation-testing output, regenerated by the tool that owns it
  /\.ai-engineering\//, // local runtime state, rebuilt from templates
  /graft\//, // the context graph's local index, declared "regenerable, not committed" in .gitignore; its extract cache mirrors the text of files this list already exempts, so it carries every retired value by construction
  /node_modules/,
  /\.git\//,
  /dist\//,
];

/** Text formats a colour could plausibly hide in. Deliberately broader than the
 *  formats that carry the palette today: a `.txt` or a `.toml` that quotes a retired
 *  value is exactly the surface a narrower list would miss, and widening it costs one
 *  line. Extensionless config (a `_headers` file) is not scanned — it carries CSP and
 *  cache directives, never a colour. */
const TEXT_EXT = /\.(ts|tsx|js|mjs|cjs|astro|css|html|json|md|svg|tpl|yml|yaml|sh|py|toml|txt|xml|webmanifest|gitignore|gitleaksignore)$/;

/**
 * A retired colour can hide in two forms: as a hex literal, or spelled out as an
 * `rgba()` triplet. Matching only the first one is how the second one survives a
 * migration that everyone believes is finished, so both are checked.
 */
function legacyHits(text: string): string[] {
  const upper = text.toUpperCase();
  const found: string[] = [];
  for (const hex of LEGACY) {
    if (upper.includes(hex.toUpperCase())) {
      found.push(`#${hex}`);
      continue;
    }
    const value = parseInt(hex, 16);
    const [r, g, b] = [(value >> 16) & 255, (value >> 8) & 255, value & 255];
    if (new RegExp(`\\b${r}\\s*,\\s*${g}\\s*,\\s*${b}\\b`).test(text)) found.push(`rgb(${r} ${g} ${b})`);
  }
  return found;
}

async function cmdLegacy(): Promise<number> {
  const roots = [ROOT, WEB_DIR];
  const hits: string[] = [];
  for (const root of roots) {
    for await (const file of walk(root)) {
      const rel = relative(root, file);
      if (!TEXT_EXT.test(file)) continue;
      if (LEGACY_ALLOW.some((re) => re.test(rel))) continue;
      let text: string;
      try {
        text = await readFile(file, 'utf8');
      } catch {
        continue;
      }
      for (const hit of legacyHits(text)) hits.push(`${relative(process.cwd(), file)} — ${hit}`);
    }
  }
  if (hits.length > 0) {
    console.error(hits.join('\n'));
    console.error(`\n${hits.length} retired palette reference(s) remain. The rebrand is not finished.${remedyLine()}`);
    return 1;
  }
  console.log(`clean: none of the ${LEGACY.length} retired palette values survive in shipped files, in hex or in rgba() form.`);
  console.log('allowlisted (history only): CHANGELOG, *history*, *_legacy*, specs/, reports/, .ai-engineering/, graft/, brand/tokens.json, scripts/brand.ts');
  return 0;
}

async function* walk(dir: string): AsyncGenerator<string> {
  let entries;
  try {
    entries = await readdir(dir, { withFileTypes: true });
  } catch {
    return;
  }
  for (const entry of entries) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === 'node_modules' || entry.name === '.git' || entry.name === 'dist') continue;
      yield* walk(path);
    } else {
      yield path;
    }
  }
}

// ---------------------------------------------------------------------------
// Entry point — guarded so the module can be imported by the test suite without
// running a command. A check that lives in one place is only useful if the test
// can call it instead of re-implementing it.
// ---------------------------------------------------------------------------

if (import.meta.main) {
  const command = process.argv[2] ?? 'check';
  const tokens = await loadTokens();

  switch (command) {
    case 'check': {
      const problems = validate(tokens);
      if (problems.length > 0) {
        console.error(problems.join('\n'));
        console.error(`\n${problems.length} problem(s) in brand/tokens.json`);
        process.exit(1);
      }
      const colours = Object.values(tokens.semantic).reduce((n, g) => n + Object.keys(g).length, 0);
      console.log(`brand/tokens.json is valid: ${Object.keys(tokens.families).length} colour families, ${colours} semantic colours, ${tokens.pairs.length} contrast pairs, ${Object.keys(tokens.typography.scale).length} type steps.`);
      break;
    }
    case 'gen':
      process.exit(await cmdGen(tokens));
    case 'parity':
      process.exit(await cmdParity(tokens));
    case 'contrast':
      process.exit(cmdContrast(tokens));
    case 'artifact':
      process.exit(await cmdArtifact(tokens));
    case 'legacy':
      process.exit(await cmdLegacy());
    default:
      console.error(`unknown command: ${command}\nusage: bun scripts/brand.ts <check|gen|parity|contrast|artifact|legacy>`);
      process.exit(2);
  }
}
