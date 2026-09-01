// Writes against anything that governs the agent. The first thing an agent obeying
// injected text does is unhook its guards. Ported from v1's self_protect.py (145 LOC)
// with the v2 additions: .ai-engineering/ governed files, spec.html once its sha256
// is pinned in the lock (reopening an approved contract costs a human), canon skills.

import { basename, dirname, isAbsolute, join, resolve } from "node:path";
import { homedir } from "node:os";
import { existsSync, readFileSync } from "node:fs";
import type { Payload } from "../chain/payload.ts";
import { parseToml } from "../toml.ts";

/** A command whose first word is one of these writes wherever its arguments point.
 *  `sed` joins them only with -i. The list may over-deny: that is a person told to
 *  use the edit tool, never a write nobody saw. */
const WRITERS: Record<string, true> = {
  rm: true, mv: true, cp: true, install: true, truncate: true, dd: true, tee: true,
  chmod: true, chown: true, ln: true, python: true, python3: true, perl: true,
  ruby: true, node: true, sh: true, bash: true, zsh: true, bun: true,
};

const REDIRECT = /\d*>>?\s*("[^"]*"|'[^']*'|[^\s;|&]+)/g;
const SEPARATORS = /[\n;|&]+/;

type GuardResult = { deny: true; reason: string } | { deny: false } | undefined;

export type ProtectedPaths = {
  literals: string[]; // substring-matched against commands and resolved paths
  specPinned: boolean; // spec.html approved (sha256 in lock) → protected
};

function surfacesSettings(repoRoot: string): string[] {
  // The settings files this install wires, per surface (v2: derived from what plant
  // wrote; the on-disk check keeps an uninstall from leaving ghosts).
  const out: string[] = [];
  const candidates = [
    join(repoRoot, ".claude", "settings.json"),
    join(repoRoot, ".opencode", "plugins", "ai-eng.ts"),
    join(repoRoot, ".agents", "hooks", "ai-eng.ts"),
  ];
  for (const path of candidates) if (existsSync(path)) out.push(path);
  return out;
}

/** Every path this session may not write to. Derived, never copied: a list that can
 *  fall behind the wiring lets one edit to the IOC catalogue disarm the injection guard. */
export function protectedPaths(repoRoot: string | null): ProtectedPaths {
  const literals: string[] = [];
  if (!repoRoot) return { literals, specPinned: false };

  // Contract files in the repo root.
  literals.push("AGENTS.md", "CLAUDE.md", "DECISIONS.md");
  // The governed directory and its fixed governing children.
  const aiEng = join(repoRoot, ".ai-engineering");
  literals.push(aiEng);
  for (const name of ["config.toml", "overrides.toml", "ai-eng.lock", "arch.rules.json", "git"]) {
    literals.push(join(aiEng, name));
  }
  // spec.html is protected ONLY once approved: its sha256 sits in the lock (§9.3).
  let specPinned = false;
  try {
    const lock = parseToml(readFileSync(join(aiEng, "ai-eng.lock"), "utf8"));
    specPinned = typeof lock["spec_sha256"] === "string" && (lock["spec_sha256"] as string).length >= 64;
  } catch {
    specPinned = false;
  }
  // Surface wiring we ourselves wrote.
  literals.push(...surfacesSettings(repoRoot));
  // Global canon and machine state: ~/.ai-engineering/** and the home mirrors.
  const globalHome = join(homedir(), ".ai-engineering");
  literals.push(globalHome);
  for (const mirror of [".claude/skills", ".agents/skills", ".config/opencode/skill"]) {
    literals.push(join(homedir(), mirror));
  }
  // Drop empties: the test is substring, and "" is a substring of every command.
  return { literals: literals.filter((p) => p.length > 0), specPinned };
}


/** The protected path this ONE shell command writes to, or null. A redirect is
 *  judged by where it points; a pipe target (tee, xargs rm) is judged as a write
 *  when its receiver is a writer verb and the payload names a protected path. */
export function writesTo(paths: ProtectedPaths, command: string): string | null {
  const words = command.trim().split(/\s+/).filter((w) => w.length > 0);
  if (words.length === 0) return null;
  const verb = basename(words[0]!.replace(/["']/g, ""));
  if (WRITERS[verb] === true || (verb === "sed" && words.includes("-i"))) {
    return offendingPath(paths, command);
  }
  // A writer downstream of a pipe (echo x | tee <path>): its arguments carry the
  // destination. Judge the writer verb's own words, not the whole pipeline.
  for (let i = 1; i < words.length; i++) {
    if (words[i] === "|" && i + 1 < words.length) {
      const rest = words.slice(i + 1).join(" ");
      const downstream = writesTo(paths, rest);
      if (downstream) return downstream;
      break;
    }
  }
  for (const match of command.matchAll(REDIRECT)) {
    const found = offendingPath(paths, match[1]!.replace(/^["']|["']$/g, ""));
    if (found) return found;
  }
  return null;
}

function expandTilde(path: string): string {
  if (path === "~") return homedir();
  if (path.startsWith("~/")) return join(homedir(), path.slice(2));
  return path;
}
/** The governed file or path this text offends, or null. Bare contract names
 *  (AGENTS.md, CLAUDE.md, DECISIONS.md) match path SEGMENTS, never substrings —
 *  "src/AGENTS.md.notes/x.md" is not the contract. Absolute literals stay substring. */
function offendingPath(paths: ProtectedPaths, text: string): string | null {
  const bareNames = ["AGENTS.md", "CLAUDE.md", "DECISIONS.md"];
  for (const path of paths.literals) {
    const bare = path === basename(path) && bareNames.includes(path);
    if (bare) {
      // Match as a whole path segment: the text ends with the name after / or start.
      const segment = new RegExp(`(^|/)${path.replace(/\./g, "\\.")}$`);
      if (segment.test(text)) return path;
      continue;
    }
    if (text.includes(path)) return path;
  }
  if (paths.specPinned && text.includes("spec.html")) return "spec.html (approved contract — sha256 pinned)";
  return null;
}

export function runSelfProtect(payload: Payload, repoRoot: string | null): GuardResult {
  const paths = protectedPaths(repoRoot);
  const args = payload.tool_input;
  const target = args["file_path"] ?? args["path"] ?? "";
  if (typeof target === "string" && target.length > 0) {
    const expanded = expandTilde(target);
    const resolved = isAbsolute(expanded) ? resolve(expanded) : resolve(repoRoot ?? process.cwd(), expanded);
    const found = offendingPath(paths, resolved) ?? offendingPath(paths, expanded) ?? offendingPath(paths, target);
    if (found) {
      return {
        deny: true,
        reason: `${target} is part of what governs this session — it is how the rules reach you and how what happens here is recorded. Changing it from inside the session it governs is not a change a session gets to make. A person edits it, in a diff, in a pull request.`,
      };
    }
  }
  const command = args["command"];
  if (typeof command === "string" && command.length > 0) {
    // macOS: /var is a symlink of /private/var — paths must be canonicalized
    // BEFORE the substring test, or the agent evades by writing the tmpdir alias.
    const { realpathSync } = require("node:fs") as typeof import("node:fs");
    const canonPath = (target: string): string => {
      // Canonicalize the longest existing prefix; a not-yet-created file inherits the
      // real prefix of its directory (rm -rf into a symlinked tmpdir must not evade).
      const parts = target.split("/");
      let current = target.startsWith("/") ? "/" : process.cwd();
      for (const part of parts) {
        if (part === "" || part === ".") continue;
        if (part === "..") {
          current = join(current, "..");
          try {
            current = realpathSync(current);
          } catch {
            /* keep */
          }
          continue;
        }
        const next = join(current, part);
        try {
          current = realpathSync(next);
        } catch {
          current = next;
        }
      }
      return current;
    };
    const canon = (text: string): string => {
      const expanded = text.replace(/(^|[\s"'=])~\//g, `$1${homedir()}/`);
      return expanded.replace(/(\/[\w.@+-]+)+/g, (m) => canonPath(m));
    };
    const canonicalPaths: ProtectedPaths = {
      literals: paths.literals.map((p) => {
        try {
          return realpathSync(p);
        } catch {
          return p;
        }
      }),
      specPinned: paths.specPinned,
    };
    const expandedCommand = canon(command);
    const pieces = expandedCommand.split(SEPARATORS).filter((p) => p.trim().length > 0);
    for (let index = 0; index < pieces.length; index++) {
      const one = pieces[index]!;
      // A heredoc is one command spanning lines; what it writes is in the body below.
      const judged = one.includes("<<") ? pieces.slice(index).join(" ") : one;
      const found = writesTo(canonicalPaths, judged);
      if (found) {
        return {
          deny: true,
          reason: `this command writes to ${found}, which is part of what governs this session. A person changes that, in a reviewed diff — not the session it governs.`,
        };
      }
    }
  }
  return undefined;
}


/** Where the repo's own hooks would live if this install wired them (for tests). */
export function floorDir(repoRoot: string): string {
  return join(dirname(join(repoRoot, ".ai-engineering")), ".ai-engineering", "git");
}
