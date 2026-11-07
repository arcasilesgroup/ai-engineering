// scripts/first-install-probe.ts — the first-install judge.
//
// Does what a person at a workshop does with the `ai-eng` on PATH: init a fresh repo
// per surface, then runs every hook line init wrote in the shells that host uses on
// this OS, with a real payload on stdin. A cell is green only when the hook exits 0,
// in time, without a deny for a harmless call. The checkout's CI never ran a written
// hook line through a host shell, which is how 3.0.0 shipped hooks that broke Windows.
//
// Run: bun scripts/first-install-probe.ts   (exit 1 when any cell is red)
import { spawnSync } from "node:child_process";
import { appendFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import { join } from "node:path";
import surfacesJson from "../src/surfaces/surfaces.json";

const IS_WINDOWS = process.platform === "win32";
const SURFACES = (process.env.PROBE_SURFACES ?? "claude-code,copilot-cli,codex,cursor,pi").split(",");
// A slow hook is a broken hook: the hosts kill it at their timeout (claude 5 s).
const MAX_HOOK_MS = Number(process.env.PROBE_MAX_HOOK_MS ?? 5000);

type Shell = { name: string; argv: (command: string) => [string, string[]] };

function gitBash(): string | null {
  const candidates = ["C:\\Program Files\\Git\\bin\\bash.exe", "C:\\Program Files\\Git\\usr\\bin\\bash.exe"];
  return candidates.find((path) => existsSync(path)) ?? null;
}

/** The shells a host may hand a hook line to on this OS. Windows PowerShell 5.1 under
 *  the Restricted policy is the default on a fresh laptop, so it gets its own row. */
function shells(): Shell[] {
  if (!IS_WINDOWS) return [{ name: "sh", argv: (c) => ["/bin/sh", ["-c", c]] }];
  const rows: Shell[] = [
    { name: "powershell", argv: (c) => ["powershell.exe", ["-NoProfile", "-NonInteractive", "-Command", c]] },
    { name: "powershell-restricted", argv: (c) => ["powershell.exe", ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Restricted", "-Command", c]] },
    { name: "pwsh", argv: (c) => ["pwsh.exe", ["-NoProfile", "-NonInteractive", "-Command", c]] },
    { name: "cmd", argv: (c) => ["cmd.exe", ["/d", "/s", "/c", c]] },
  ];
  const bash = gitBash();
  if (bash) rows.push({ name: "git-bash", argv: (c) => [bash, ["-c", c]] });
  return rows;
}

const POWERSHELLS = new Set(["powershell", "powershell-restricted", "pwsh"]);

/** Which of those shells this host hands this line to on Windows, per its own docs. A
 *  line is only judged where its host runs it. Codex documents no shell: every one. */
function hostRuns(surface: string, key: string, shell: string): boolean {
  if (key === "powershell" || key === "windows") return POWERSHELLS.has(shell);
  if (!IS_WINDOWS) return true;
  if (key === "bash") return shell === "git-bash";
  // code.claude.com/docs/en/hooks: Git Bash, or PowerShell when Git Bash is absent.
  if (surface === "claude-code") return shell === "git-bash" || POWERSHELLS.has(shell);
  // cursor.com/docs/hooks: "On Windows, the desktop app runs hook commands through PowerShell".
  if (surface === "cursor") return POWERSHELLS.has(shell);
  return true;
}

/** A red cell this branch knows about and cannot fix in the line itself: shown in amber,
 *  named, never counted green. Cursor's line lives in the repo, shared by every OS, and
 *  Cursor has no per-OS key; PowerShell resolves the bare name to npm's ai-eng.ps1, which
 *  Restricted refuses and which loses the hook's stdin. bun's install has no .ps1. */
function knownGap(surface: string, shell: string): string | null {
  if (IS_WINDOWS && surface === "cursor" && POWERSHELLS.has(shell)) return "known: npm's ai-eng.ps1 under PowerShell — install with `bun add -g ai-engineering`";
  return null;
}

function run(file: string, argv: string[], options: { cwd: string; input?: string }) {
  const started = performance.now();
  const result = spawnSync(file, argv, { cwd: options.cwd, input: options.input ?? "", encoding: "utf8", timeout: 60_000, shell: false });
  return {
    status: result.status,
    stdout: (result.stdout ?? "").trim(),
    stderr: ((result.stderr ?? "") + (result.error ? ` ${result.error.message}` : "")).trim(),
    ms: Math.round(performance.now() - started),
  };
}

/** `ai-eng` itself, resolved the way a terminal does (the .cmd shim on Windows). */
function aiEng(args: string, cwd: string) {
  return IS_WINDOWS ? run("cmd.exe", ["/d", "/s", "/c", `ai-eng ${args}`], { cwd }) : run("/bin/sh", ["-c", `ai-eng ${args}`], { cwd });
}

/** Every hook line in a JSON carrier, with the key it sits under (command, bash, powershell…). */
function hookLines(file: string): Array<{ key: string; line: string }> {
  const found: Array<{ key: string; line: string }> = [];
  const walk = (node: unknown): void => {
    if (Array.isArray(node)) return node.forEach(walk);
    if (node === null || typeof node !== "object") return;
    // Beside a `powershell` line the Copilot harness hands `command` to bash only.
    const hasPowerShell = typeof (node as Record<string, unknown>)["powershell"] === "string";
    for (const [key, value] of Object.entries(node)) {
      if (typeof value === "string" && ["command", "bash", "powershell", "windows", "linux", "osx"].includes(key) && value.includes("ai-eng")) {
        found.push({ key: key === "command" && hasPowerShell ? "bash" : key, line: value });
      } else walk(value);
    }
  };
  walk(JSON.parse(readFileSync(file, "utf8")));
  return found;
}

let calls = 0;
function payloadFor(surface: string, cwd: string, event: string, command = "git status"): string {
  // One session per call: the loop guard rightly denies the same call repeated in one session.
  const base = { session_id: `probe-${++calls}`, cwd, hook_event_name: event };
  if (event === "UserPromptSubmit") return JSON.stringify({ ...base, prompt: "/ai-brainstorm hello" });
  if (event === "Stop") return JSON.stringify({ ...base, stop_hook_active: false });
  const tool = surface === "copilot-cli" ? { toolName: "bash", toolArgs: JSON.stringify({ command }) } : { tool_name: "Bash", tool_input: { command } };
  return JSON.stringify({ ...base, ...tool });
}

/** A hook that exits 0 on everything also exits 0 when it never ran: stdin lost between
 *  shells, a crash an `|| exit 0` swallowed, `exit $null` after a shim that did not start.
 *  So every PreToolUse line must also refuse a call that is always refused, in the shape
 *  its host reads: exit 2 with a silent stdout for Claude, deny JSON with exit 0 elsewhere. */
const ALWAYS_REFUSED = "git commit --no-verify -m probe";
function refusesInHostShape(surface: string, result: { status: number | null; stdout: string }): boolean {
  if (surface === "claude-code") return result.status === 2 && result.stdout === "";
  return result.status === 0 && isDeny(result.stdout);
}

function eventOf(line: string): string {
  return /chain\s+(\w+)/.exec(line)?.[1] ?? "PreToolUse";
}

function isDeny(stdout: string): boolean {
  return /"(?:permissionDecision|decision|permission)"\s*:\s*"(?:deny|block)"|"continue"\s*:\s*false/.test(stdout);
}

function carriersOf(surface: string, repo: string): string[] {
  const row = surfacesJson.surfaces.find((s) => s.id === surface);
  return (row?.carriers ?? []).map((c) => join(c.scope === "repo" ? repo : homedir(), c.path));
}

function countFiles(dir: string): number {
  if (!existsSync(dir)) return 0;
  return readdirSync(dir, { recursive: true, withFileTypes: true }).filter((e) => e.isFile()).length;
}

type Cell = { surface: string; check: string; shell: string; ok: boolean; detail: string; known?: string | null };
const cells: Cell[] = [];
const work = mkdtempSync(join(tmpdir(), "first install "));
const bare = join(work, "not governed");
mkdirSync(bare);

// Everyone who already uses Claude Code has this file: 3.0.0 refused to merge into it and
// installed no hooks at all. Seeded the way Claude Code writes it, unless one is there.
const userSettings = join(homedir(), ".claude", "settings.json");
if (!existsSync(userSettings)) {
  mkdirSync(join(homedir(), ".claude"), { recursive: true });
  writeFileSync(userSettings, `${JSON.stringify({ model: "opus" }, null, 2)}\n`);
}
// Codex too: a hooks file of the person's own, so the probe walks the merge, not the create.
const codexHooks = join(homedir(), ".codex", "hooks.json");
if (!existsSync(codexHooks)) {
  mkdirSync(join(homedir(), ".codex"), { recursive: true });
  writeFileSync(codexHooks, `${JSON.stringify({ hooks: {} }, null, 2)}\n`);
}

const version = aiEng("--version", work);
cells.push({ surface: "-", check: "ai-eng --version", shell: IS_WINDOWS ? "cmd" : "sh", ok: version.status === 0, detail: (version.stdout || version.stderr).slice(0, 160) });

for (const surface of SURFACES) {
  const repo = join(work, `repo ${surface}`);
  mkdirSync(repo);
  run("git", ["init", "-q"], { cwd: repo });
  const init = aiEng(`init --yes --surface ${surface}`, repo);
  cells.push({ surface, check: "init", shell: "-", ok: init.status === 0, detail: `exit ${init.status} ${init.ms}ms ${init.stderr.split("\n").slice(-2).join(" ").slice(0, 200)}` });

  for (const carrier of carriersOf(surface, repo)) {
    if (!existsSync(carrier)) {
      cells.push({ surface, check: `carrier ${carrier.replace(homedir(), "~").replace(repo, "<repo>")}`, shell: "-", ok: false, detail: "missing" });
      continue;
    }
    if (!carrier.endsWith(".json")) {
      const chain = carrier.replace(/ai-eng(\.ts)$/, (_m, ext) => (surface === "opencode" ? `ai-eng-chain${ext}` : `.ai-eng-chain${ext}`));
      cells.push({ surface, check: "module carrier + chain bundle", shell: "-", ok: existsSync(chain), detail: existsSync(chain) ? "present" : `no ${chain}` });
      continue;
    }
    const lines = hookLines(carrier);
    cells.push({ surface, check: `hook lines in ${carrier.replace(homedir(), "~").replace(repo, "<repo>")}`, shell: "-", ok: lines.length > 0, detail: `${lines.length} line(s)` });
    for (const { key, line } of lines) {
      const event = eventOf(line);
      for (const shell of shells()) {
        if (!hostRuns(surface, key, shell.name)) continue;
        const known = knownGap(surface, shell.name);
        for (const [where, cwd] of [["governed", repo], ["ungoverned", bare]] as const) {
          const [file, argv] = shell.argv(line);
          const r = run(file, argv, { cwd, input: payloadFor(surface, cwd, event) });
          const ok = r.status === 0 && r.ms <= MAX_HOOK_MS && !isDeny(r.stdout);
          cells.push({ surface, check: `${key}:${event} ${where}`, shell: shell.name, ok, known, detail: `exit ${r.status} ${r.ms}ms ${(r.stderr || r.stdout).replace(/\s+/g, " ").slice(0, 160)}` });
        }
        if (event !== "PreToolUse") continue;
        const [file, argv] = shell.argv(line);
        const refused = run(file, argv, { cwd: repo, input: payloadFor(surface, repo, event, ALWAYS_REFUSED) });
        cells.push({ surface, check: `${key}:${event} refuses --no-verify`, shell: shell.name, ok: refusesInHostShape(surface, refused), known, detail: `exit ${refused.status} stdout ${refused.stdout.slice(0, 80) || "(empty)"}` });
      }
    }
  }
}

const skills = countFiles(join(homedir(), ".ai-engineering", "skills"));
cells.push({ surface: "-", check: "skills canon", shell: "-", ok: skills > 0, detail: `${skills} files in ~/.ai-engineering/skills` });

const red = cells.filter((c) => !c.ok && !c.known);
const amber = cells.filter((c) => !c.ok && c.known);
const mark = (c: Cell) => (c.ok ? "🟢" : c.known ? "🟡" : "🔴");
const table = ["| ok | surface | check | shell | detail |", "|---|---|---|---|---|", ...cells.map((c) => `| ${mark(c)} | ${c.surface} | ${c.check} | ${c.shell} | ${(c.known && !c.ok ? `${c.known} · ` : "") + c.detail.replace(/\|/g, "\\|")} |`)].join("\n");
const summary = `## first-install probe · ${process.platform}-${process.arch}\n\n${cells.length - red.length - amber.length}/${cells.length} green · ${amber.length} known gap(s) · ${red.length} red\n\n${table}\n`;
console.log(summary);
writeFileSync(join(process.env.PROBE_OUT ?? work, `probe-${process.platform}.json`), JSON.stringify(cells, null, 2));
if (process.env.GITHUB_STEP_SUMMARY) appendFileSync(process.env.GITHUB_STEP_SUMMARY, summary);
process.exit(red.length === 0 ? 0 : 1);
