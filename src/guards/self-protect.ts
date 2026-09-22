// Writes against the four things that govern the agent, and nothing else: the files the
// chain itself reads (config.toml, overrides.toml, ai-eng.lock, arch.rules.json), the git
// floor, spec.html once its sha256 is pinned in the lock (reopening an approved contract
// costs a human), and the machine-side canon and carriers.
//
// Everything else under .ai-engineering/ is the session's to write — the fence protects
// the machinery, not the session's own evidence. The slots (brainstorm/spec/plan/recap
// die at `spec close` and the session is their only writer) and the artifacts the
// canon's own nodes promise (ai-research writes research/NNN-{name}.html, ai-security
// writes security/run-N/, ai-design writes design/direction.html) all have to pass, and
// a guard that stops a session writing what its skill told it to write protects nothing
// and breaks the loop it governs. What stays protected is the machinery a session could
// use to unpin, unhook or re-date itself.

import { basename, isAbsolute, join, resolve } from "node:path";
import { existsSync, readFileSync, realpathSync } from "node:fs";
import type { Payload } from "../chain/payload.ts";
import { home, machineBase } from "../env.ts";

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
/** A path-shaped token with at least one `/` and no leading `/` — the form the
 *  absolute-path rewrite cannot see, and therefore the form that evaded it. */
const RELATIVE_PATH = /(^|[\s"'=<>|;&(])((?:\.\.?\/)?[\w.@+-]+(?:\/[\w.@+-]+)+)/g;

type GuardResult = { deny: true; reason: string } | { deny: false } | undefined;

export type ProtectedPaths = {
  literals: string[]; // substring-matched against commands and resolved paths
  specPinned: boolean; // spec.html approved (sha256 in lock) → protected
  /** Matched as the LAST segment only: the protected directory itself, never a child of
   *  it. `rm -rf .ai-engineering` names it and nothing else; `.ai-engineering/research/…`
   *  inside it is the session's own material. */
  terminal: string[];
};

function surfacesSettings(repoRoot: string): string[] {
  // The settings files this install wires, per surface (derived from what install
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
  // The machine side is protected whether or not this call happens inside a governed
  // repo: the canon and its mirrors govern every session on this machine, and a repo-less
  // call is exactly the one an injected instruction would use to unprotect them (R4).
  const globalHome = join(home(), "");
  literals.push(join(home(), "skills"));
  literals.push(join(machineBase(), ".claude", "skills"));
  literals.push(join(machineBase(), ".agents", "skills"));
  literals.push(join(machineBase(), ".config", "opencode", "skill"));
  literals.push(globalHome);
  for (const carrier of [".claude/settings.json", ".config/opencode/plugins", ".codex/hooks.json", ".omp/agent/hooks", ".pi/agent/extensions", ".copilot/hooks", "machine.json"]) {
    literals.push(join(machineBase(), carrier));
  }
  if (!repoRoot) return { literals: literals.filter((p) => p.length > 0), specPinned: false, terminal: [] };

  // Prose contracts the user owns: editable by the governed agent (blueprint §9.2
  // "AGENTS.md no es sagrado" / §13.3 "tú lo editas"), so they are NOT literals.
  // Only the machinery below stays protected.
  //
  // The directory is protected as a TERMINAL match — the last segment, never a prefix: a
  // command that names `.ai-engineering` is deleting everything the chain owns in one
  // word, while a file inside it is the session's own material (the four slots, the
  // research and security artifacts its own nodes write, the receipts). One substring
  // literal for the directory denied both, which is how a guard ends up stopping the loop
  // it governs.
  const aiEng = join(repoRoot, ".ai-engineering");
  const terminal = [".ai-engineering", aiEng];
  // The four files the chain itself reads: the ceiling, the guard switches, the pins, the
  // layer rules.
  for (const name of ["config.toml", "overrides.toml", "ai-eng.lock", "arch.rules.json"]) {
    literals.push(join(aiEng, name));
  }
  // The git floor itself. The shims live in .git/hooks/ (marker-managed, §13.2),
  // NOT under .ai-engineering/git/ — protecting a ghost there while the real shims
  // stay writable lets a session overwrite the hook with `exit 0`
  // (Write/Edit/redirect all allowed).
  literals.push(join(repoRoot, ".git", "hooks"));
  // spec.html is protected ONLY once approved: its sha256 sits in the lock (§9.3).
  // The fence is that file, not the word. Matching the substring "spec.html" also denied
  // `templates/spec.html.tpl` — the payload `init` generates every project's contract
  // from — and any future `docs/spec.html.md`, while the rule's own criterion is the
  // pinned file. Pushing the path through the literal list keeps the same protection on
  // the same file, through the same matching the other governed paths already use.
  let specPinned = false;
  try {
    const lock = Bun.TOML.parse(readFileSync(join(aiEng, "ai-eng.lock"), "utf8")) as Record<string, unknown>;
    const pinned = lock["spec_sha256"];
    specPinned = typeof pinned === "string" && pinned.length >= 64;
  } catch {
    specPinned = false;
  }
  if (specPinned) literals.push(join(aiEng, "spec.html"));
  // Surface wiring we ourselves wrote.
  literals.push(...surfacesSettings(repoRoot));
  // Global canon and machine state: ~/.ai-engineering/** and the home mirrors. Both are
  // protected above, for the repo-less call as well.
  // Drop empties: the test is substring, and "" is a substring of every command.
  return { literals: literals.filter((p) => p.length > 0), specPinned, terminal };
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
  if (path === "~") return machineBase();
  if (path.startsWith("~/")) return join(machineBase(), path.slice(2));
  return path;
}

/** The governed file or path this text offends, or null.
 *
 *  The prose contracts the user owns (AGENTS.md, DECISIONS.md) are
 *  EDITABLE by the governed agent (blueprint §9.2: "AGENTS.md no es sagrado";
 *  §13.3: "tú lo editas") — they are instructions, not wiring, and are simply not
 *  in the protected literal list. What must never change from inside a session is
 *  the machinery: the four files the chain reads, surface settings, git hooks, the
 *  global canon, and spec.html once approved. Bare names match as whole path
 *  SEGMENTS (never substrings): "src/AGENTS.md.notes/x.md" is not a contract file.
 *  Absolute literals stay substring. */
function offendingPath(paths: ProtectedPaths, text: string): string | null {
  // The directory, as the last segment only. A child of it is the session's material, so
  // this cannot be a substring test: `.ai-engineering/research/x.html` contains the
  // directory and is not it.
  for (const path of paths.terminal) {
    const segment = new RegExp(`(^|/)${path.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`);
    if (segment.test(text)) return path;
  }
  for (const path of paths.literals) {
    const bare = path === basename(path);
    if (bare) {
      // Match as a whole path segment: the text ends with the name after / or start.
      const segment = new RegExp(`(^|/)${path.replace(/\./g, "\\.")}$`);
      if (segment.test(text)) return path;
      continue;
    }
    if (!text.includes(path)) continue;
    return path;
  }
  return null;
}

export function runSelfProtect(payload: Payload, repoRoot: string | null): GuardResult {
  const paths = protectedPaths(repoRoot);
  const args = payload.tool_input;
  const target = args["file_path"] ?? args["path"] ?? "";
  if (typeof target === "string" && target.length > 0) {
    const expanded = expandTilde(target);
    const resolved = isAbsolute(expanded) ? resolve(expanded) : resolve(repoRoot ?? process.cwd(), expanded);
    // macOS: /var is a symlink of /private/var — canonicalize BEFORE the match, or
    // the tmpdir alias of a governed path evades (same canon the command branch uses).
    let canonical = resolved;
    try {
      canonical = realpathSync(resolved);
    } catch {
      // Not-yet-existing file: canonicalize the longest existing prefix.
      const parts = resolved.split("/");
      let prefix = resolved.startsWith("/") ? "/" : process.cwd();
      for (const part of parts) {
        const next = join(prefix, part);
        try {
          prefix = realpathSync(next);
        } catch {
          prefix = next;
        }
      }
      canonical = prefix;
    }
    const candidates = [canonical, resolved, expanded, target];
    const found = candidates.map((form) => offendingPath(paths, form)).find((hit) => hit != null) ?? null;
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
    // The command branch shares the canonicalization above.
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
      const expanded = text.replace(/(^|[\s"'=])~\//g, `$1${machineBase()}/`);
      const absolute = expanded.replace(/(\/[\w.@+-]+)+/g, (m) => canonPath(m));
      // A relative path escapes a substring test on absolute literals:
      // `> .git/hooks/pre-commit` never matches the absolute literal, so a session
      // can disarm the floor with a redirect or a chmod. Resolve every relative
      // path token against the repo root before judging.
      const base = repoRoot ?? process.cwd();
      return absolute.replace(RELATIVE_PATH, (match, lead: string, token: string) => `${lead}${canonPath(join(base, token))}`);
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
      // The same canon as the literals: an absolute entry left in its raw form never
      // matches a command whose path tokens were rewritten above. The relative form is
      // left alone on purpose — realpathSync would resolve it against the process cwd,
      // not against the repo being judged.
      terminal: paths.terminal.map((p) => {
        if (!isAbsolute(p)) return p;
        try {
          return realpathSync(p);
        } catch {
          return p;
        }
      }),
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
