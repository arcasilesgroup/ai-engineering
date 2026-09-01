// Minimal TOML for exactly two files: .ai-engineering/config.toml and overrides.toml.
// Supports what they use — [table], [[array-of-tables]], strings, ints, bools — and
// nothing else. A parser pretending to be general is the drift the lockfile exists for.

export interface TomlTable {
  [key: string]: string | number | boolean | string[] | TomlTable | TomlTable[];
}

export function parseToml(text: string): TomlTable {
  const out: TomlTable = {};
  let current: TomlTable = out;
  for (const raw of text.split("\n")) {
    const line = stripComment(raw).trim();
    if (!line || line.startsWith("#")) continue;
    const arrayTable = /^\[\[\s*([A-Za-z0-9_.-]+)\s*\]\]$/.exec(line);
    if (arrayTable) {
      const path = arrayTable[1]!.split(".");
      current = enterArrayTable(out, path);
      continue;
    }
    const table = /^\[\s*([A-Za-z0-9_.-]+)\s*\]$/.exec(line);
    if (table) {
      const path = table[1]!.split(".");
      current = enterTable(out, path);
      continue;
    }
    const kv = /^(?:"([^"]+)"|([A-Za-z0-9_-]+))\s*=\s*(.+)$/.exec(line);
    if (!kv) throw new Error(`unparseable TOML line: ${raw.trim()}`);
    current[kv[1] ?? kv[2]!] = parseValue(kv[3]!.trim());
  }
  return out;
}

function stripComment(line: string): string {
  let quote: string | null = null;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i]!;
    if (quote) {
      if (ch === quote) quote = null;
    } else if (ch === '"' || ch === "'") {
      quote = ch;
    } else if (ch === "#") {
      return line.slice(0, i);
    }
  }
  return line;
}

function parseValue(text: string): string | number | boolean | string[] {
  if (text.startsWith("[") && text.endsWith("]")) {
    const inner = text.slice(1, -1).trim();
    if (!inner) return [];
    return inner
      .split(",")
      .map((item) => item.trim())
      .filter((item) => item.length > 0)
      .map((item) => (item.startsWith('"') && item.endsWith('"')) || (item.startsWith("'") && item.endsWith("'")) ? item.slice(1, -1) : item);
  }
  if ((text.startsWith('"') && text.endsWith('"')) || (text.startsWith("'") && text.endsWith("'")))
    return text.slice(1, -1);
  if (text === "true") return true;
  if (text === "false") return false;
  if (/^-?\d+$/.test(text)) return Number.parseInt(text, 10);
  return text; // dates and bare words pass through as strings — consumers narrow
}

function enterTable(root: TomlTable, path: string[]): TomlTable {
  let node = root;
  for (const key of path) {
    const existing = node[key];
    if (!existing || typeof existing !== "object" || Array.isArray(existing)) {
      const fresh: TomlTable = {};
      node[key] = fresh;
      node = fresh;
    } else {
      node = existing as TomlTable;
    }
  }
  return node;
}

function enterArrayTable(root: TomlTable, path: string[]): TomlTable {
  const parentPath = path.slice(0, -1);
  const key = path[path.length - 1]!;
  const parent = parentPath.length ? enterTable(root, parentPath) : root;
  const existing = parent[key];
  const list: TomlTable[] = Array.isArray(existing) && existing.every((item) => typeof item === "object" && !Array.isArray(item)) ? (existing as TomlTable[]) : [];
  const fresh: TomlTable = {};
  list.push(fresh);
  parent[key] = list;
  return fresh;
}

/** Serialize back the subset we write: flat tables of scalars, or [[array]] blocks. */
export function serializeToml(data: TomlTable): string {
  const lines: string[] = [];
  for (const [key, value] of Object.entries(data)) {
    if (Array.isArray(value) && value.every((v) => typeof v === "object")) {
      for (const entry of value as TomlTable[]) {
        lines.push(`[[${key}]]`);
        for (const [k, v] of Object.entries(entry)) {
          if (typeof v === "string" || typeof v === "number" || typeof v === "boolean") lines.push(`${k} = ${scalar(v)}`);
        }
        lines.push("");
      }
    } else if (typeof value === "object") {
      lines.push(`[${key}]`);
      for (const [k, v] of Object.entries(value as TomlTable)) {
        if (typeof v === "string" || typeof v === "number" || typeof v === "boolean") lines.push(`${k} = ${scalar(v)}`);
      }
      lines.push("");
    } else {
      lines.push(`${key} = ${scalar(value)}`);
    }
  }
  return `${lines.join("\n")}\n`;
}

function scalar(value: string | number | boolean): string {
  if (typeof value === "string") return `"${value.replace(/"/g, '\\"')}"`;
  return String(value);
}
