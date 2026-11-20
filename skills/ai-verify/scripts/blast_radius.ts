#!/usr/bin/env bun
// TypeScript port of the former blast_radius.py. Same flags, same stdout
// shape, same exit codes: SKILL.md documents the invocation and the eval
// harness parses the report, so this file is a port and not a redesign.
//
// Trace which route entrypoints transitively depend on a set of changed files.
//
// Builds a reverse import graph for a JS/TS web project and reports, for each
// changed file, the routes that consume it -- directly or through any chain of
// intermediate modules. That set is the regression surface for a change.
//
//     bun blast_radius.ts --repo /path/to/repo --changed app/lib/format.ts components/Row.tsx
//     bun blast_radius.ts --repo . --changed $(git diff --name-only HEAD) --json
//
// Import resolution covers relative specifiers, tsconfig/jsconfig `paths`
// aliases, and directory/index imports. Bare package specifiers are ignored --
// a change inside node_modules is not what this is for.
//
// Limitations worth stating out loud in the verification report: this sees
// import edges only. Coupling through shared API routes, database rows,
// localStorage keys, cookies, global CSS, or env vars is invisible here and
// must be reasoned about separately.

import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, isAbsolute, join, normalize, relative, resolve, sep } from "node:path";

const SOURCE_EXTS = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts", ".svelte", ".vue"];
const RESOLVE_EXTS = [...SOURCE_EXTS, ".json", ".css"];
const SKIP_DIRS: Record<string, true> = {
  node_modules: true, ".git": true, ".next": true, ".nuxt": true, ".svelte-kit": true,
  dist: true, build: true, out: true, coverage: true, ".turbo": true, ".vercel": true,
  ".cache": true, __pycache__: true, ".feature-verify": true, "playwright-report": true,
  "test-results": true,
};

// Groups 1-4 are the Python named groups a/b/c/d, in the same alternation
// order -- the first group that matched wins, and `import` (group 1) must be
// tried before `import(` (group 3) for the same reason it is in the original.
const IMPORT_RE = /(?:(?:^|[\s;}])import\s+(?:[^'"()]*?\s+from\s+)?['"]([^'"]+)['"]|(?:^|[\s;}=(])require\s*\(\s*['"]([^'"]+)['"]\s*\)|(?:^|[\s;}=(,])import\s*\(\s*['"]([^'"]+)['"]\s*\)|(?:^|[\s;}])export\s+(?:[^'"()]*?\s+from\s+)?['"]([^'"]+)['"])/gm;

// (regex on repo-relative posix path, human label). Order matters: first match wins.
const ROUTE_PATTERNS: Array<[RegExp, string]> = [
  [/^(?:src\/)?app\/(.*\/)?page\.(tsx|jsx|ts|js)$/, "next-app-page"],
  [/^(?:src\/)?app\/(.*\/)?layout\.(tsx|jsx|ts|js)$/, "next-app-layout"],
  [/^(?:src\/)?app\/(.*\/)?route\.(ts|js)$/, "next-app-api"],
  [/^(?:src\/)?app\/(.*\/)?(loading|error|not-found|template)\.(tsx|jsx)$/, "next-app-special"],
  [/^(?:src\/)?middleware\.(ts|js)$/, "next-middleware"],
  [/^(?:src\/)?pages\/(?!_document|_app).*\.(tsx|jsx|ts|js)$/, "next-pages"],
  [/^(?:src\/)?routes\/.*\+page\.svelte$/, "sveltekit-page"],
  [/^app\/routes\/.*\.(tsx|jsx|ts|js)$/, "remix-route"],
  [/^(?:src\/)?(main|index|App)\.(tsx|jsx|ts|js)$/, "spa-entry"],
];

type Alias = { prefix: string; targets: string[] };
type RouteHit = { kind: string; url: string | null; hops: number };
type ChangedReport = { routes: Record<string, RouteHit>; direct_importers: string[] };
type Args = { repo: string; changed: string[]; json: boolean; maxDepth: number };

/** Repo-relative posix path -- the form every route pattern and every report
 *  line is written against. */
function relFrom(repo: string, path: string): string {
  const rel = relative(repo, path);
  return sep === "/" ? rel : rel.split(sep).join("/");
}

/** Every source file under `repo`. Unreadable directories are skipped rather
 *  than fatal: os.walk swallowed scandir errors the same way, and a bad
 *  --repo has to print an empty report instead of dying with a stack trace. */
function findSourceFiles(repo: string): string[] {
  const files: string[] = [];
  const walk = (dir: string): void => {
    let entries;
    try {
      entries = readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      if (entry.isDirectory()) {
        if (SKIP_DIRS[entry.name] === true || entry.name.startsWith(".git")) continue;
        walk(join(dir, entry.name));
      } else if (SOURCE_EXTS.some((ext) => entry.name.endsWith(ext))) {
        // Symlinks to directories are left out here, matching os.walk, which
        // lists them under dirnames and never under filenames.
        files.push(join(dir, entry.name));
      }
    }
  };
  walk(repo);
  return files;
}

/** Read `compilerOptions.paths` from tsconfig/jsconfig -> [{prefix, targets}]. */
function loadAliases(repo: string): Alias[] {
  const aliases: Alias[] = [];
  for (const name of ["tsconfig.json", "jsconfig.json"]) {
    const path = join(repo, name);
    if (!existsSync(path)) continue;
    let cfg: { compilerOptions?: { baseUrl?: string; paths?: Record<string, string[]> } };
    try {
      const raw = readFileSync(path, "utf8")
        // tsconfig is JSON with comments; json.loads needed the same cleanup.
        .replace(/\/\*[\s\S]*?\*\//g, "")
        .replace(/(^|\s)\/\/.*$/gm, "")
        .replace(/,(\s*[}\]])/g, "$1");
      cfg = JSON.parse(raw);
    } catch {
      continue;
    }
    const opts = cfg.compilerOptions ?? {};
    const base = join(repo, opts.baseUrl ?? ".");
    for (const [pattern, targets] of Object.entries(opts.paths ?? {})) {
      const prefix = pattern.endsWith("*") ? pattern.slice(0, -1) : pattern;
      aliases.push({
        prefix,
        targets: (targets ?? []).map((t) => normalize(join(base, t.endsWith("*") ? t.slice(0, -1) : t))),
      });
    }
  }
  // Longest prefix first, so "@/foo/bar" beats "@/foo" for the same specifier.
  aliases.sort((a, b) => b.prefix.length - a.prefix.length);
  return aliases;
}

/** Resolve an import specifier to a repo file, or null if external/unresolvable. */
function resolveSpec(
  spec: string,
  importer: string,
  repo: string,
  aliases: Alias[],
  known: Set<string>,
): string | null {
  const candidates: string[] = [];
  if (spec.startsWith(".")) {
    candidates.push(normalize(join(dirname(importer), spec)));
  } else {
    let aliased = false;
    for (const { prefix, targets } of aliases) {
      if (spec.startsWith(prefix)) {
        const rest = spec.slice(prefix.length);
        for (const target of targets) candidates.push(normalize(join(target, rest)));
        aliased = true;
        break;
      }
    }
    if (!aliased) {
      // Some projects import from the repo root without an alias declaration.
      if (["~/", "@/", "src/", "app/", "components/", "lib/"].some((p) => spec.startsWith(p))) {
        // lstrip("~@/") strips every leading character from that set, not just one.
        candidates.push(normalize(join(repo, spec.replace(/^[~@/]+/, ""))));
      }
    }
  }

  for (const base of candidates) {
    if (known.has(base) && statSync(base, { throwIfNoEntry: false })?.isFile()) return base;
    for (const ext of RESOLVE_EXTS) {
      // Membership in `known` is the only check here, as in the original: the
      // file was found by the same walk, so an extra isfile() costs a stat.
      if (known.has(base + ext)) return base + ext;
    }
    for (const ext of RESOLVE_EXTS) {
      const idx = join(base, "index" + ext);
      if (known.has(idx)) return idx;
    }
  }
  return null;
}

function routeKind(rel: string): string | null {
  for (const [pattern, label] of ROUTE_PATTERNS) {
    if (pattern.test(rel)) return label;
  }
  return null;
}

/** Best-effort URL for a route file. Returns null when it can't be inferred. */
function routeUrl(rel: string, kind: string): string | null {
  let segs: string[];
  if (kind.startsWith("next-app")) {
    const m = /^(?:src\/)?app\/(.*\/)?[^/]+$/.exec(rel);
    const group = m?.[1] ?? "";
    segs = group.replace(/^\/+/, "").replace(/\/+$/, "").split("/").filter((s) => s !== "");
  } else if (kind === "next-pages") {
    const body = rel
      .replace(/^(?:src\/)?pages\//, "")
      .replace(/\.(tsx|jsx|ts|js)$/, "")
      .replace(/\/?index$/, "");
    segs = body.split("/").filter((s) => s !== "");
  } else if (kind === "sveltekit-page") {
    const stripped = rel.replace(/^(?:src\/)?routes\//, "");
    const parts = stripped.split("/");
    // rsplit("/", 1)[0] returns the whole string when there is no "/", so the
    // top-level `routes/+page.svelte` turns into a URL of "/+page.svelte".
    // Odd, but that is what the original printed.
    const body = parts.length > 1 ? parts.slice(0, -1).join("/") : parts[0]!;
    segs = body.split("/").filter((s) => s !== "");
  } else {
    return null;
  }

  const out: string[] = [];
  for (const seg of segs) {
    if (seg.startsWith("(") && seg.endsWith(")")) continue; // Next.js route group -- organizational, not part of the URL
    if (seg.startsWith("@")) continue; // parallel route slot
    const m = /^\[+\.{0,3}([^\]]+)\]+$/.exec(seg);
    out.push(m ? ":" + m[1] : seg);
  }
  return "/" + out.join("/");
}

const PROG = "blast_radius.ts";
const USAGE = `usage: ${PROG} [-h] [--repo REPO] --changed CHANGED [CHANGED ...] [--json]\n` +
  `                    [--max-depth MAX_DEPTH]`;

// argparse only refuses a following token as an option when it is not a
// negative number (this parser declares no options that look like one), and it
// treats a lone "-" as a value. Take the same tokens so `--max-depth -2` lands
// on the int validation rather than on "expected one argument".
const NEGATIVE_NUMBER_RE = /^-\d+$|^-\d*\.\d+$/;

/** int() accepts whitespace, a sign, and single underscores between digits. */
const PY_INT_RE = /^[+-]?\d+(?:_\d+)*$/;

/** A token argparse would take as a value rather than as an option. */
function isValueToken(token: string | undefined): token is string {
  return token !== undefined && (!token.startsWith("-") || token === "-" || NEGATIVE_NUMBER_RE.test(token));
}

function fail(message: string): never {
  process.stderr.write(USAGE + "\n" + `${PROG}: error: ${message}\n`);
  process.exit(2);
}

function parseArgs(argv: string[]): Args {
  const args: Args = { repo: ".", changed: [], json: false, maxDepth: 12 };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i]!;
    const eq = arg.startsWith("--") ? arg.indexOf("=") : -1;
    const flag = eq === -1 ? arg : arg.slice(0, eq);
    const inlineValue = eq === -1 ? null : arg.slice(eq + 1);
    const take = (): string | null => {
      if (inlineValue !== null) return inlineValue;
      const next = argv[++i];
      return isValueToken(next) ? next : null;
    };
    switch (flag) {
      case "--repo": {
        const value = take();
        if (value === null) fail("argument --repo: expected one argument");
        args.repo = value;
        break;
      }
      case "--changed": {
        // nargs="+": a bare flag consumes following values until the next
        // option, but "--changed=x" consumes only x -- argparse then rejects any
        // trailing bare argument, so this must not sweep it up either.
        const inline = inlineValue !== null;
        const first = take();
        if (first === null) fail("argument --changed: expected at least one argument");
        const values = [first];
        if (!inline) {
          while (isValueToken(argv[i + 1])) values.push(argv[++i]!);
        }
        args.changed.push(...values);
        break;
      }
      case "--json":
        args.json = true;
        break;
      case "--max-depth": {
        // argparse type=int: whitespace, sign, single underscores. Number("")
        // is 0 and Number("1.0") is 1, so neither may be used here.
        const value = take();
        const text = value === null ? null : value.trim();
        if (text === null) fail("argument --max-depth: expected one argument");
        const hops = PY_INT_RE.test(text) ? Number(text.replace(/_/g, "")) : NaN;
        if (!Number.isInteger(hops)) fail(`argument --max-depth: invalid int value: '${value}'`);
        args.maxDepth = hops;
        break;
      }
      case "-h":
      case "--help":
        process.stdout.write(USAGE + `\n\nTrace which route entrypoints transitively depend on a set of changed files.\n`);
        process.exit(0);
        break;
      default:
        fail(`unrecognized arguments: ${arg}`);
    }
  }
  if (args.changed.length === 0) fail("the following arguments are required: --changed");
  return args;
}

/** Python's json.dumps(..., indent=2) escapes non-ASCII; JSON.stringify does
 *  not. Paths are usually ASCII, but the harness must parse the same bytes. */
function pythonJson(value: unknown): string {
  return JSON.stringify(value, null, 2).replace(
    /[\u007f-\uffff]/g,
    (ch) => "\\u" + ch.charCodeAt(0).toString(16).padStart(4, "0"),
  );
}

function main(): number {
  const args = parseArgs(process.argv.slice(2));

  const repo = resolve(args.repo); // abspath: resolves against cwd when relative
  const files = findSourceFiles(repo);
  const known = new Set(files);
  const aliases = loadAliases(repo);

  const importers = new Map<string, Set<string>>(); // file -> files that import it
  for (const src of files) {
    let text: string;
    try {
      text = readFileSync(src, "utf8");
    } catch {
      continue;
    }
    for (const m of text.matchAll(IMPORT_RE)) {
      const spec = m[1] ?? m[2] ?? m[3] ?? m[4];
      if (!spec) continue;
      const target = resolveSpec(spec, src, repo, aliases, known);
      if (target && target !== src) {
        let into = importers.get(target);
        if (!into) importers.set(target, (into = new Set()));
        into.add(src);
      }
    }
  }

  const changed: string[] = [];
  for (const c of args.changed) {
    const p = isAbsolute(c) ? c : join(repo, c);
    changed.push(normalize(p));
  }

  const report: Record<string, ChangedReport> = {};
  const allRoutes: Record<string, RouteHit> = {};
  const unknown: string[] = [];
  for (const target of changed) {
    if (!existsSync(target)) continue;
    if (!SOURCE_EXTS.some((ext) => target.endsWith(ext))) {
      unknown.push(relFrom(repo, target));
      continue;
    }

    const seen = new Set([target]);
    const queue: Array<[string, number]> = [[target, 0]];
    const hit: Record<string, RouteHit> = {};
    for (let head = 0; head < queue.length; head++) {
      const [node, depth] = queue[head]!;
      const rel = relFrom(repo, node);
      const kind = routeKind(rel);
      if (kind) hit[rel] = { kind, url: routeUrl(rel, kind), hops: depth };
      if (depth >= args.maxDepth) continue;
      for (const parent of importers.get(node) ?? []) {
        if (!seen.has(parent)) {
          seen.add(parent);
          queue.push([parent, depth + 1]);
        }
      }
    }

    const relChanged = relFrom(repo, target);
    report[relChanged] = {
      routes: hit,
      direct_importers: [...(importers.get(target) ?? [])].map((p) => relFrom(repo, p)).sort(),
    };
    Object.assign(allRoutes, hit);
  }

  if (args.json) {
    process.stdout.write(pythonJson({ changed: report, all_routes: allRoutes, non_source: unknown }) + "\n");
    return 0;
  }

  const out: string[] = ["BLAST RADIUS", "=".repeat(60)];
  for (const [changedFile, data] of Object.entries(report)) {
    out.push("", changedFile);
    const routes = Object.entries(data.routes).sort((a, b) => a[1].hops - b[1].hops);
    if (routes.length === 0) {
      out.push("  (no route depends on this via imports -- check for runtime coupling)");
    }
    for (const [rel, meta] of routes) {
      const url = meta.url ? `  url=${meta.url}` : "";
      const direct = meta.hops === 0 ? " [the changed file itself]" : `  hops=${meta.hops}`;
      out.push(`  - ${rel}  (${meta.kind})${url}${direct}`);
    }
    if (data.direct_importers.length > 0) {
      const shown = data.direct_importers.slice(0, 8);
      const more = data.direct_importers.length > 8 ? ` (+${data.direct_importers.length - 8} more)` : "";
      out.push(`  imported directly by: ${shown.join(", ")}${more}`);
    }
  }

  if (unknown.length > 0) {
    out.push("", "Non-source changed files (styles, config, assets -- reason about these manually):");
    for (const u of unknown) out.push(`  - ${u}`);
  }

  const urls = [...new Set(Object.values(allRoutes).map((m) => m.url).filter((u): u is string => u !== null))].sort();
  out.push("", "=".repeat(60), `UNIQUE ROUTES AFFECTED: ${Object.keys(allRoutes).length}`);
  if (urls.length > 0) out.push("Candidate URLs to smoke-test: " + urls.join(", "));
  out.push(
    "",
    "Import edges only. Shared API responses, storage keys, global CSS, and",
    "env vars create coupling this cannot see -- add those targets yourself.",
  );
  process.stdout.write(out.join("\n") + "\n");
  return 0;
}

process.exit(main());
