import { describe, expect, test } from "bun:test";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, relative, resolve, sep } from "node:path";
import { ALL_VERBS } from "../src/shared-verbs.ts";

const ROOT = resolve(import.meta.dir, "..");
const DOCUMENT_PATHS = [
  "README.md",
  "CONTRIBUTING.md",
  "SECURITY.md",
  "PERMISSIONS.md",
  "NOTICE.md",
  "docs",
  "skills",
  "templates",
];
const DOCUMENT_EXTENSION = /\.(?:md|markdown|html|htm)$/i;

type Document = { path: string; content: string };
type Link = { value: string; source: string };

function documentFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) return documentFiles(path);
    return entry.isFile() && DOCUMENT_EXTENSION.test(entry.name) ? [path] : [];
  });
}

function documentsInScope(): Document[] {
  return DOCUMENT_PATHS.flatMap((documentPath) => {
    const path = resolve(ROOT, documentPath);
    if (!existsSync(path)) throw new Error(`Missing documentation scope path: ${documentPath}`);
    const files = statSync(path).isDirectory() ? documentFiles(path) : [path];
    return files
      .filter((file) => DOCUMENT_EXTENSION.test(file))
      .map((file) => ({ path: file, content: readFileSync(file, "utf8") }));
  }).sort((left, right) => left.path.localeCompare(right.path));
}

function unknownVerbCitations(documents: Document[]): string[] {
  const allowedVerbs = new Set(ALL_VERBS);
  const problems: string[] = [];
  for (const document of documents) {
    for (const snippet of codeSnippets(document.content)) {
      for (const match of snippet.matchAll(/\bai-eng\s+([a-z][\w-]*)\b/g)) {
        const verb = match[1] ?? "";
        if (!allowedVerbs.has(verb)) problems.push(`${relative(ROOT, document.path)}: ai-eng ${verb}`);
      }
    }
  }
  return [...new Set(problems)];
}

function codeSnippets(content: string): string[] {
  const snippets: string[] = [];
  let prose = content.replace(/<script\b[^>]*>[\s\S]*?<\/script>|<style\b[^>]*>[\s\S]*?<\/style>/gi, "");
  prose = prose.replace(/^ {0,3}(`{3,}|~{3,})[^\n]*\n([\s\S]*?)^ {0,3}\1[ \t]*$/gm, (_block, _fence: string, snippet: string) => {
    snippets.push(snippet);
    return "";
  });
  prose = prose.replace(/<(?:code|pre)\b[^>]*>([\s\S]*?)<\/(?:code|pre)>/gi, (_block, snippet: string) => {
    snippets.push(snippet);
    return "";
  });
  for (const match of prose.matchAll(/(?<!`)(`+)(?!`)([\s\S]*?)\1(?!`)/g)) snippets.push(match[2] ?? "");
  return snippets;
}

function decodeEntities(value: string): string {
  return value.replace(/&(#x[\da-f]+|#\d+|amp|quot|apos|lt|gt);/gi, (entity, name: string) => {
    if (name.toLowerCase() === "amp") return "&";
    if (name.toLowerCase() === "quot") return '"';
    if (name.toLowerCase() === "apos") return "'";
    if (name.toLowerCase() === "lt") return "<";
    if (name.toLowerCase() === "gt") return ">";
    const codePoint = name[1]?.toLowerCase() === "x"
      ? Number.parseInt(name.slice(2), 16)
      : Number.parseInt(name.slice(1), 10);
    return Number.isInteger(codePoint) && codePoint >= 0 && codePoint <= 0x10ffff
      ? String.fromCodePoint(codePoint)
      : entity;
  });
}

function linksIn(content: string, source: string): Link[] {
  const links: Link[] = [];
  const markdownPatterns = [
    /!?\[[^\]]*\]\(\s*(<[^>\n]*>|(?:\\.|[^)\s])+)/g,
    /^[ \t]{0,3}\[[^\]]+\]:[ \t]*(<[^>\n]*>|(?:\\.|[^\s])+)/gm,
  ];
  const withoutCode = content
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>|<style\b[^>]*>[\s\S]*?<\/style>/gi, "")
    .replace(/<(?:code|pre)\b[^>]*>[\s\S]*?<\/(?:code|pre)>/gi, "")
    .replace(/^ {0,3}(`{3,}|~{3,})[^\n]*\n[\s\S]*?^ {0,3}\1[ \t]*$/gm, "")
    .replace(/(?<!`)(`+)(?!`)[\s\S]*?\1(?!`)/g, "");
  for (const pattern of markdownPatterns) {
    for (const match of withoutCode.matchAll(pattern)) {
      const value = (match[1] ?? "").replace(/^<|>$/g, "");
      links.push({ value, source });
    }
  }
  const markup = content
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>|<style\b[^>]*>[\s\S]*?<\/style>/gi, "")
    .replace(/<(?:code|pre)\b[^>]*>[\s\S]*?<\/(?:code|pre)>/gi, "")
    .replace(/^ {0,3}(`{3,}|~{3,})[^\n]*\n[\s\S]*?^ {0,3}\1[ \t]*$/gm, "")
    .replace(/(?<!`)(`+)(?!`)[\s\S]*?\1(?!`)/g, "");
  for (const tag of markup.matchAll(/<[a-z][^>]*>/gi)) {
    for (const attribute of (tag[0] ?? "").matchAll(/\b(?:href|src)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/gi)) {
      links.push({ value: attribute[1] ?? attribute[2] ?? attribute[3] ?? "", source });
    }
  }
  return links;
}

function markdownAnchors(content: string): Set<string> {
  const anchors = new Set<string>();
  const headingCounts = new Map<string, number>();
  for (const match of content.matchAll(/^\s{0,3}#{1,6}[ \t]+(.+?)\s*#*\s*$/gm)) {
    let heading = match[1] ?? "";
    const explicitAnchor = /\s+\{#([^}]+)\}\s*$/.exec(heading);
    if (explicitAnchor) {
      anchors.add(explicitAnchor[1] ?? "");
      heading = heading.slice(0, explicitAnchor.index);
    }
    const slug = heading
      .replace(/`([^`]*)`/g, "$1")
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
      .replace(/<[^>]*>/g, "")
      .normalize("NFKC")
      .toLowerCase()
      .replace(/[^\p{L}\p{N}\s_-]/gu, "")
      .trim()
      .replace(/\s/g, "-");
    if (!slug) continue;
    const duplicate = headingCounts.get(slug) ?? 0;
    anchors.add(duplicate === 0 ? slug : `${slug}-${duplicate}`);
    headingCounts.set(slug, duplicate + 1);
  }
  for (const match of content.matchAll(/\b(?:id|name)\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s"'=<>`]+))/gi)) {
    anchors.add(decodeEntities(match[1] ?? match[2] ?? match[3] ?? ""));
  }
  return anchors;
}

function withinRepository(path: string): boolean {
  const pathFromRoot = relative(ROOT, path);
  return pathFromRoot !== ".." && !pathFromRoot.startsWith(`..${sep}`);
}

function anchorDocumentPath(path: string): string | null {
  if (!existsSync(path)) return null;
  if (!statSync(path).isDirectory()) return path;
  return ["README.md", "index.md", "index.html"]
    .map((name) => resolve(path, name))
    .find(existsSync) ?? null;
}

function brokenLinks(document: Document): string[] {
  const problems: string[] = [];
  for (const link of linksIn(document.content, document.path)) {
    const value = decodeEntities(link.value).trim();
    if (/^(?:[a-z][a-z\d+.-]*:|\/\/)/i.test(value)) continue;

    const hashIndex = value.indexOf("#");
    const pathAndQuery = hashIndex < 0 ? value : value.slice(0, hashIndex);
    const fragment = hashIndex < 0 ? "" : value.slice(hashIndex + 1);
    const pathValue = pathAndQuery.split("?")[0] ?? "";
    let targetPath: string;
    let targetFragment: string;
    try {
      const decodedPath = decodeURIComponent(pathValue);
      targetPath = decodedPath.startsWith("/")
        ? resolve(ROOT, decodedPath.slice(1))
        : resolve(dirname(link.source), decodedPath || relative(dirname(link.source), link.source));
      targetFragment = decodeURIComponent(fragment);
    } catch {
      problems.push(`${relative(ROOT, link.source)}: malformed link ${value}`);
      continue;
    }

    if (!withinRepository(targetPath)) {
      problems.push(`${relative(ROOT, link.source)}: link escapes repository ${value}`);
      continue;
    }
    if (!existsSync(targetPath)) {
      problems.push(`${relative(ROOT, link.source)}: missing target ${value}`);
      continue;
    }
    if (!targetFragment) continue;

    const anchorPath = anchorDocumentPath(targetPath);
    if (anchorPath && DOCUMENT_EXTENSION.test(anchorPath)) {
      const content = readFileSync(anchorPath, "utf8");
      if (!markdownAnchors(content).has(targetFragment)) {
        problems.push(`${relative(ROOT, link.source)}: missing anchor ${value}`);
      }
    } else if (statSync(targetPath).isDirectory()) {
      problems.push(`${relative(ROOT, link.source)}: missing anchor ${value}`);
    } else if (/^L\d+(?:-L\d+)?$/i.test(targetFragment)) {
      const lines = readFileSync(targetPath, "utf8").split(/\r?\n/).length;
      const lineNumbers = [...targetFragment.matchAll(/\d+/g)].map((match) => Number(match[0]));
      if (lineNumbers.some((lineNumber) => lineNumber < 1 || lineNumber > lines)) {
        problems.push(`${relative(ROOT, link.source)}: missing line anchor ${value}`);
      }
    }
  }
  return problems;
}

describe("CP17 docs lint", () => {
  test("every documented ai-eng verb is registered by the CLI", () => {
    expect(unknownVerbCitations(documentsInScope())).toEqual([]);
  });

  test("relative Markdown and HTML links and anchors resolve within the repository", () => {
    expect(documentsInScope().flatMap(brokenLinks)).toEqual([]);
  });

  test("the linter catches an unknown verb, a missing file, and a missing anchor", () => {
    const fixture: Document = {
      path: resolve(ROOT, "README.md"),
      content: "Run `ai-eng recap` and see [missing](docs-lint-missing-target.md) or [#lost](README.md#docs-lint-missing-anchor).",
    };
    expect(unknownVerbCitations([fixture])).toEqual(["README.md: ai-eng recap"]);
    expect(brokenLinks(fixture)).toEqual([
      "README.md: missing target docs-lint-missing-target.md",
      "README.md: missing anchor README.md#docs-lint-missing-anchor",
    ]);
  });
});
