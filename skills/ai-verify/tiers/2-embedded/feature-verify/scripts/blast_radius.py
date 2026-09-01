#!/usr/bin/env python3
"""Trace which route entrypoints transitively depend on a set of changed files.

Builds a reverse import graph for a JS/TS web project and reports, for each
changed file, the routes that consume it -- directly or through any chain of
intermediate modules. That set is the regression surface for a change.

Usage:
    python3 blast_radius.py --repo /path/to/repo --changed app/lib/format.ts components/Row.tsx
    python3 blast_radius.py --repo . --changed $(git diff --name-only HEAD) --json

Import resolution covers relative specifiers, tsconfig/jsconfig `paths` aliases,
and directory/index imports. Bare package specifiers are ignored -- a change
inside node_modules is not what this is for.

Limitations worth stating out loud in the verification report: this sees import
edges only. Coupling through shared API routes, database rows, localStorage
keys, cookies, global CSS, or env vars is invisible here and must be reasoned
about separately.
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict, deque

SOURCE_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts", ".svelte", ".vue")
RESOLVE_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts", ".svelte", ".vue", ".json", ".css")
SKIP_DIRS = {
    "node_modules", ".git", ".next", ".nuxt", ".svelte-kit", "dist", "build",
    "out", "coverage", ".turbo", ".vercel", ".cache", "__pycache__",
    ".feature-verify", "playwright-report", "test-results",
}

IMPORT_RE = re.compile(
    r"""(?:
          (?:^|[\s;}])import\s+(?:[^'"()]*?\s+from\s+)?['"](?P<a>[^'"]+)['"]
        | (?:^|[\s;}=(])require\s*\(\s*['"](?P<b>[^'"]+)['"]\s*\)
        | (?:^|[\s;}=(,])import\s*\(\s*['"](?P<c>[^'"]+)['"]\s*\)
        | (?:^|[\s;}])export\s+(?:[^'"()]*?\s+from\s+)?['"](?P<d>[^'"]+)['"]
    )""",
    re.VERBOSE | re.MULTILINE,
)

# (regex on repo-relative posix path, human label). Order matters: first match wins.
ROUTE_PATTERNS = [
    (re.compile(r"^(?:src/)?app/(.*/)?page\.(tsx|jsx|ts|js)$"), "next-app-page"),
    (re.compile(r"^(?:src/)?app/(.*/)?layout\.(tsx|jsx|ts|js)$"), "next-app-layout"),
    (re.compile(r"^(?:src/)?app/(.*/)?route\.(ts|js)$"), "next-app-api"),
    (re.compile(r"^(?:src/)?app/(.*/)?(loading|error|not-found|template)\.(tsx|jsx)$"), "next-app-special"),
    (re.compile(r"^(?:src/)?middleware\.(ts|js)$"), "next-middleware"),
    (re.compile(r"^(?:src/)?pages/(?!_document|_app).*\.(tsx|jsx|ts|js)$"), "next-pages"),
    (re.compile(r"^(?:src/)?routes/.*\+page\.svelte$"), "sveltekit-page"),
    (re.compile(r"^app/routes/.*\.(tsx|jsx|ts|js)$"), "remix-route"),
    (re.compile(r"^(?:src/)?(main|index|App)\.(tsx|jsx|ts|js)$"), "spa-entry"),
]


def find_source_files(repo):
    files = []
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".git")]
        for fn in filenames:
            if fn.endswith(SOURCE_EXTS):
                files.append(os.path.join(dirpath, fn))
    return files


def load_aliases(repo):
    """Read `compilerOptions.paths` from tsconfig/jsconfig -> [(prefix, [abs targets])]."""
    aliases = []
    for name in ("tsconfig.json", "jsconfig.json"):
        path = os.path.join(repo, name)
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                raw = fh.read()
            raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)
            raw = re.sub(r"(^|\s)//.*$", "", raw, flags=re.M)
            raw = re.sub(r",(\s*[}\]])", r"\1", raw)
            cfg = json.loads(raw)
        except Exception:
            continue
        opts = cfg.get("compilerOptions", {}) or {}
        base = os.path.join(repo, opts.get("baseUrl", "."))
        for pattern, targets in (opts.get("paths", {}) or {}).items():
            prefix = pattern[:-1] if pattern.endswith("*") else pattern
            resolved = [os.path.normpath(os.path.join(base, t[:-1] if t.endswith("*") else t))
                        for t in targets]
            aliases.append((prefix, resolved))
    aliases.sort(key=lambda a: -len(a[0]))
    return aliases


def resolve(spec, importer, repo, aliases, known):
    """Resolve an import specifier to a repo file, or None if external/unresolvable."""
    candidates = []
    if spec.startswith("."):
        candidates.append(os.path.normpath(os.path.join(os.path.dirname(importer), spec)))
    else:
        for prefix, targets in aliases:
            if spec.startswith(prefix):
                rest = spec[len(prefix):]
                candidates.extend(os.path.normpath(os.path.join(t, rest)) for t in targets)
                break
        else:
            # Some projects import from the repo root without an alias declaration.
            if spec.startswith(("~/", "@/", "src/", "app/", "components/", "lib/")):
                candidates.append(os.path.normpath(os.path.join(repo, spec.lstrip("~@/"))))

    for base in candidates:
        if base in known and os.path.isfile(base):
            return base
        for ext in RESOLVE_EXTS:
            if (base + ext) in known:
                return base + ext
        for ext in RESOLVE_EXTS:
            idx = os.path.join(base, "index" + ext)
            if idx in known:
                return idx
    return None


def route_kind(rel):
    for pattern, label in ROUTE_PATTERNS:
        if pattern.match(rel):
            return label
    return None


def route_url(rel, kind):
    """Best-effort URL for a route file. Returns None when it can't be inferred."""
    if kind.startswith("next-app"):
        m = re.match(r"^(?:src/)?app/(.*/)?[^/]+$", rel)
        segs = [s for s in (m.group(1) or "").strip("/").split("/") if s] if m else []
    elif kind == "next-pages":
        body = re.sub(r"^(?:src/)?pages/", "", rel)
        body = re.sub(r"\.(tsx|jsx|ts|js)$", "", body)
        body = re.sub(r"/?index$", "", body)
        segs = [s for s in body.split("/") if s]
    elif kind == "sveltekit-page":
        body = re.sub(r"^(?:src/)?routes/", "", rel).rsplit("/", 1)[0]
        segs = [s for s in body.split("/") if s]
    else:
        return None

    out = []
    for seg in segs:
        if seg.startswith("(") and seg.endswith(")"):
            continue  # Next.js route group -- organizational, not part of the URL
        if seg.startswith("@"):
            continue  # parallel route slot
        m = re.match(r"^\[+\.{0,3}([^\]]+)\]+$", seg)
        out.append(":" + m.group(1) if m else seg)
    return "/" + "/".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".", help="repository root")
    ap.add_argument("--changed", nargs="+", required=True, help="changed files (repo-relative or absolute)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a text report")
    ap.add_argument("--max-depth", type=int, default=12, help="max reverse-dependency hops")
    args = ap.parse_args()

    repo = os.path.abspath(args.repo)
    files = find_source_files(repo)
    known = set(files)
    aliases = load_aliases(repo)

    importers = defaultdict(set)  # file -> files that import it
    for src in files:
        try:
            with open(src, encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
        except OSError:
            continue
        for m in IMPORT_RE.finditer(text):
            spec = m.group("a") or m.group("b") or m.group("c") or m.group("d")
            if not spec:
                continue
            target = resolve(spec, src, repo, aliases, known)
            if target and target != src:
                importers[target].add(src)

    changed = []
    for c in args.changed:
        p = c if os.path.isabs(c) else os.path.join(repo, c)
        changed.append(os.path.normpath(p))

    report, all_routes, unknown = {}, {}, []
    for target in changed:
        if not os.path.exists(target):
            continue
        if not target.endswith(SOURCE_EXTS):
            unknown.append(os.path.relpath(target, repo))
            continue

        seen, queue, hit = {target}, deque([(target, 0)]), {}
        while queue:
            node, depth = queue.popleft()
            rel = os.path.relpath(node, repo)
            kind = route_kind(rel)
            if kind:
                hit[rel] = {"kind": kind, "url": route_url(rel, kind), "hops": depth}
            if depth >= args.max_depth:
                continue
            for parent in importers.get(node, ()):
                if parent not in seen:
                    seen.add(parent)
                    queue.append((parent, depth + 1))

        rel_changed = os.path.relpath(target, repo)
        report[rel_changed] = {
            "routes": hit,
            "direct_importers": sorted(os.path.relpath(p, repo) for p in importers.get(target, ())),
        }
        all_routes.update(hit)

    if args.json:
        print(json.dumps({"changed": report, "all_routes": all_routes, "non_source": unknown}, indent=2))
        return 0

    print("BLAST RADIUS\n" + "=" * 60)
    for changed_file, data in report.items():
        print(f"\n{changed_file}")
        if not data["routes"]:
            print("  (no route depends on this via imports -- check for runtime coupling)")
        for rel, meta in sorted(data["routes"].items(), key=lambda kv: kv[1]["hops"]):
            url = f"  url={meta['url']}" if meta["url"] else ""
            direct = " [the changed file itself]" if meta["hops"] == 0 else f"  hops={meta['hops']}"
            print(f"  - {rel}  ({meta['kind']}){url}{direct}")
        if data["direct_importers"]:
            shown = data["direct_importers"][:8]
            more = f" (+{len(data['direct_importers']) - 8} more)" if len(data["direct_importers"]) > 8 else ""
            print(f"  imported directly by: {', '.join(shown)}{more}")

    if unknown:
        print(f"\nNon-source changed files (styles, config, assets -- reason about these manually):")
        for u in unknown:
            print(f"  - {u}")

    urls = sorted({m["url"] for m in all_routes.values() if m["url"]})
    print("\n" + "=" * 60)
    print(f"UNIQUE ROUTES AFFECTED: {len(all_routes)}")
    if urls:
        print("Candidate URLs to smoke-test: " + ", ".join(urls))
    print("\nImport edges only. Shared API responses, storage keys, global CSS, and")
    print("env vars create coupling this cannot see -- add those targets yourself.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
