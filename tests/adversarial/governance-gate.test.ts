// Adversarial: the gate that decides whether a repo participates at all. Everything
// under it — guards, receipts, the git floor — is policy a repo asks for by declaring
// itself in .ai-engineering/config.toml. A repo that never asked gets allow, exit 0
// and not one byte written: no receipts, no .ai-engineering/ invented behind the
// user's back. The control in each block is the same payload in a governed repo, so
// an allow can never be a fixture that forgot to be adversarial (§A, G2-G5).

import { describe, test, expect } from "bun:test";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { runChain } from "../../src/chain/mod.ts";
import { receiptsDir } from "../../src/env.ts";
import { protectedPaths, runSelfProtect } from "../../src/guards/self-protect.ts";

const cli = join(import.meta.dir, "..", "..", "src", "cli.ts");
const PAYLOAD = { tool_name: "Bash", tool_input: { command: "git commit -n -m x" }, tool_use_id: "g1", session_id: "gate" };

const ENV = { ...process.env, NO_COLOR: "1", CI: "1", AI_ENG_NO_UPDATE_NOTICES: "1", AI_ENG_HOME: join(tmpdir(), "ai-eng-gate-home") };

function run(args: string[], cwd: string, input = ""): { status: number; stdout: string; stderr: string } {
  const r = spawnSync(process.execPath, [cli, ...args], { cwd, encoding: "utf8", env: ENV, input });
  return { status: r.status ?? 0, stdout: r.stdout ?? "", stderr: r.stderr ?? "" };
}

/** A directory that is a repo and nothing else: .git, no declaration. */
function foreignRepo(): string {
  const dir = mkdtempSync(join(tmpdir(), "ai-eng-foreign-"));
  mkdirSync(join(dir, ".git"));
  return dir;
}

/** The same shape, declared: [surfaces] enabled is what makes it governed. */
function governedRepo(config = '[surfaces]\nenabled = ["claude-code"]\n'): string {
  const dir = foreignRepo();
  mkdirSync(join(dir, ".ai-engineering"), { recursive: true });
  writeFileSync(join(dir, ".ai-engineering", "config.toml"), config);
  return dir;
}

describe("adversarial · the gate (config.toml decides, not .git)", () => {
  test("ungoverned repo allows: exit 0, zero stdout, and a governed repo denies the same payload", () => {
    const foreign = foreignRepo();
    const governed = governedRepo();
    try {
      const allowed = run(["chain", "PreToolUse"], foreign, JSON.stringify(PAYLOAD));
      expect(allowed.status).toBe(0);
      expect(allowed.stdout).toBe("");
      expect(allowed.stderr).toBe("");

      // The control: identical payload, identical binary, a repo that asked for
      // policy. If this did not deny, the allow above would prove nothing.
      const denied = run(["chain", "PreToolUse", "--surface", "claude-code"], governed, JSON.stringify(PAYLOAD));
      expect(denied.status).toBe(2);
      expect(denied.stderr).toInclude("no-verify");
    } finally {
      rmSync(foreign, { recursive: true, force: true });
      rmSync(governed, { recursive: true, force: true });
    }
  });

  test("ungoverned repo allows in-process too (the plugin hosts' path)", () => {
    const foreign = foreignRepo();
    const cwdBefore = process.cwd();
    try {
      process.chdir(foreign);
      expect(receiptsDir()).toBeNull(); // no receipt has anywhere to land
      const outcome = runChain(PAYLOAD, "PreToolUse", { inProcess: true });
      expect(outcome.action).toBe("allow");
      expect(outcome.receiptId).toBeNull();
    } finally {
      process.chdir(cwdBefore);
      rmSync(foreign, { recursive: true, force: true });
    }
  });

  test("no writes in a foreign repo: no receipts, no .ai-engineering invented", () => {
    const foreign = foreignRepo();
    try {
      const before = readdirSync(foreign).sort();
      run(["chain", "PreToolUse"], foreign, JSON.stringify(PAYLOAD));
      run(["chain", "PostToolUse"], foreign, JSON.stringify(PAYLOAD));
      run(["git", "pre-commit"], foreign); // the floor: silent, exit 0, nothing recorded
      run(["spec", "open", "not-mine"], foreign); // used to mkdir .ai-engineering/ here
      run(["git", "commit-msg", "msg.txt"], foreign);
      expect(existsSync(join(foreign, ".ai-engineering"))).toBe(false);
      expect(readdirSync(foreign).sort()).toEqual(before); // .git and nothing else
    } finally {
      rmSync(foreign, { recursive: true, force: true });
    }
  });

  test("unparseable config is not a governed repo, and doctor tells absent from corrupt", () => {
    const corrupt = governedRepo("this is not = toml = at all\n"); // real syntax error
    const empty = governedRepo(""); // parses, declares nothing — F2's trap
    const absent = foreignRepo();
    const surfacesless = governedRepo('[gc]\nmax_files = 25\n'); // parses, declares nothing
    try {
      for (const dir of [corrupt, empty, surfacesless]) {
        const allowed = run(["chain", "PreToolUse"], dir, JSON.stringify(PAYLOAD));
        expect(allowed.status).toBe(0);
        expect(allowed.stdout).toBe("");
      }
      const corruptDoctor = run(["doctor"], corrupt);
      expect(corruptDoctor.stdout + corruptDoctor.stderr).toInclude("unparseable");
      const emptyDoctor = run(["doctor"], empty);
      expect(emptyDoctor.stdout + emptyDoctor.stderr).toInclude("[surfaces]");
      expect(emptyDoctor.stdout + emptyDoctor.stderr).not.toInclude("unparseable");
      const absentDoctor = run(["doctor"], absent);
      expect(absentDoctor.stdout + absentDoctor.stderr).toInclude("absent");
      const surfaceslessDoctor = run(["doctor"], surfacesless);
      expect(surfaceslessDoctor.stdout + surfaceslessDoctor.stderr).toInclude("[surfaces]");
    } finally {
      for (const dir of [corrupt, empty, absent, surfacesless]) rmSync(dir, { recursive: true, force: true });
    }
  });

  test("git floor uses the same gate: foreign repo exits 0, governed repo applies the policy", () => {
    const foreign = foreignRepo();
    const governed = governedRepo();
    try {
      const silent = run(["git", "pre-commit"], foreign);
      expect(silent.status).toBe(0);
      expect(silent.stdout + silent.stderr).toBe("");

      // Same hook, same binary, a repo that declared itself: the floor runs and
      // refuses a staged trailing space. A floor that is off everywhere would pass
      // the assertion above and fail this one.
      writeFileSync(join(governed, "dirty.txt"), "trailing space \n");
      spawnSync("git", ["init", "-q"], { cwd: governed });
      spawnSync("git", ["add", "dirty.txt"], { cwd: governed });
      const blocked = run(["git", "pre-commit"], governed);
      expect(blocked.status).toBe(1);
      expect(blocked.stderr).toInclude("diff --check");
    } finally {
      rmSync(foreign, { recursive: true, force: true });
      rmSync(governed, { recursive: true, force: true });
    }
  });

  test("the session id cannot walk out of the state directory the guard writes to", () => {
    // The loop guard keys its state file on the session id, which the HOST supplies. A
    // traversal there overwrites whatever it names — a user's editor settings, or the
    // machine carrier that enforces policy everywhere — so the filename is derived.
    const governed = governedRepo();
    const sessionHome = mkdtempSync(join(tmpdir(), "ai-eng-loop-home-"));
    try {
      mkdirSync(join(sessionHome, ".claude"), { recursive: true });
      const victim = join(sessionHome, ".claude", "settings.json");
      const sentinel = '{\n  "env": {\n    "MINE": "yes"\n  }\n}\n';
      writeFileSync(victim, sentinel);
      const payload = {
        tool_name: "Bash",
        tool_input: { command: "echo one" },
        tool_use_id: "l1",
        session_id: "../../../.claude/settings",
      };
      const env = { ...ENV, AI_ENG_HOME: sessionHome };
      const r = spawnSync(process.execPath, [cli, "chain", "PreToolUse"], { cwd: governed, encoding: "utf8", env, input: JSON.stringify(payload) });
      expect(r.status).toBe(0);
      expect(readFileSync(victim, "utf8")).toBe(sentinel); // not one byte of the user's file
      const loopDir = join(sessionHome, "cache", "loop");
      expect(existsSync(loopDir)).toBe(true);
      for (const name of readdirSync(loopDir)) expect(/^[0-9a-f]{32}\.json$/.test(name)).toBe(true);
    } finally {
      rmSync(governed, { recursive: true, force: true });
      rmSync(sessionHome, { recursive: true, force: true });
    }
  });

  test("debt closed: the verdict cache writes inside the repo, HOME is protected, spec open invents nothing", () => {
    // Three findings the milestone's own inventory turned up, each with its own check
    // because each one was invisible: a cache that never worked, a guard list that
    // un-protected HOME outside a repo, and a verb that created .ai-engineering/ in a
    // stranger's checkout.
    const governed = governedRepo();
    const foreign = foreignRepo();
    const sessionHome = mkdtempSync(join(tmpdir(), "ai-eng-debt-home-"));
    try {
      // 1. The cache: the second delivery of a call is answered from the file, which means
      //    the directory got created. It never did — the write hit ENOENT into a silent
      //    catch, so the cache was dead code with a plausible name.
      const payload = { tool_name: "Bash", tool_input: { command: "git commit -m 'feat: x'" }, tool_use_id: "d1", session_id: "../../escaped" };
      run(["chain", "PreToolUse"], governed, JSON.stringify(payload));
      const cacheDir = join(governed, ".ai-engineering", "cache", "verdicts");
      expect(existsSync(cacheDir)).toBe(true);
      const files = readdirSync(cacheDir);
      expect(files.length).toBeGreaterThan(0);
      // 2. The session id reaches the cache FILENAME, and a host-supplied string with `..`
      //    in it must not walk out of that directory.
      for (const name of files) expect(/^[0-9a-f]{32}\.json$/.test(name)).toBe(true);
      expect(existsSync(join(governed, "escaped.json"))).toBe(false);
      expect(existsSync(join(governed, ".ai-engineering", "cache", "escaped.json"))).toBe(false);
      // And it lives INSIDE the state directory the lock owns: a cache at the repo root
      // is an unowned directory, and our own `git add -A` would commit the guard's
      // messages into the user's repository.
      expect(existsSync(join(governed, "cache"))).toBe(false);

      // 3. HOME's canon and mirrors are protected even when no governed repo is above the
      //    call: that is exactly the call an injected instruction would use.
      const previous = process.env["AI_ENG_HOME"];
      process.env["AI_ENG_HOME"] = sessionHome;
      try {
        const paths = protectedPaths(null);
        expect(paths.literals.some((literal) => literal.includes(join(sessionHome, "skills")))).toBe(true);
        expect(paths.literals.some((literal) => literal.includes(join(sessionHome, ".claude", "settings.json")))).toBe(true);
        const denied = runSelfProtect({ tool_name: "Write", tool_input: { file_path: join(sessionHome, "skills", "ai-verify", "SKILL.md"), content: "x" } } as never, null);
        expect(denied?.deny).toBe(true);
      } finally {
        if (previous === undefined) delete process.env["AI_ENG_HOME"];
        else process.env["AI_ENG_HOME"] = previous;
      }

      // 4. `spec open` in a repo that never declared itself writes nothing at all — it used
      //    to create the whole .ai-engineering/ carrier behind the user's back.
      run(["spec", "open", "not-mine"], foreign);
      expect(existsSync(join(foreign, ".ai-engineering"))).toBe(false);
    } finally {
      rmSync(governed, { recursive: true, force: true });
      rmSync(foreign, { recursive: true, force: true });
      rmSync(sessionHome, { recursive: true, force: true });
    }
  });
});

// The fence is four file names, not the directory. Everything else under .ai-engineering/
// is the session's own material: the four milestone slots (spec.html and plan.html
// scaffolded by `spec open` and filled in by the session; brainstorm.md and recap.html with
// no template at all — `spec close` sweeps all four, and doctor warns about an orphan
// brainstorm.md precisely because the session that should have written one did not, §21.2),
// and the artifacts the canon's own nodes promise: ai-research writes
// research/NNN-{name}.html, ai-security writes security/run-N/, ai-design writes
// design/direction.html. A directory literal denied every one of them — a guard that stops
// a session writing what its skill told it to write protects nothing and breaks the loop it
// governs. What stays protected is what a session could use to unpin, unhook or re-date
// itself: the four files the chain reads, the directory itself, and the git floor.
describe("adversarial · self-protect: the session writes its own artifacts, not the machinery", () => {
  const SLOTS = ["spec.html", "plan.html", "brainstorm.md", "recap.html"];

  /** A governed repo, plus a lock that pins a contract when asked. The pin is the only
   *  thing that freezes a slot: spec.html stops being a draft the moment its sha256 is
   *  in the lock (§9.3). */
  function slotRepo(pinned: boolean): string {
    const dir = governedRepo();
    if (pinned) writeFileSync(join(dir, ".ai-engineering", "ai-eng.lock"), `version = "2.2.0"\nspec_sha256 = "${"a".repeat(64)}"\n`);
    return dir;
  }

  const write = (root: string, ...parts: string[]) =>
    runSelfProtect({ tool_name: "Write", tool_input: { file_path: join(root, ".ai-engineering", ...parts), content: "x" } } as never, root);

  test("every artifact a node promises is writable while the milestone is open", () => {
    const repo = slotRepo(false);
    try {
      for (const name of SLOTS) expect(write(repo, name)?.deny ?? false).toBe(false);
      expect(write(repo, "research", "002-mutation-tier-facts.html")?.deny ?? false).toBe(false);
      expect(write(repo, "security", "run-3", "findings.json")?.deny ?? false).toBe(false);
      expect(write(repo, "security", "run-3", "REPORT.md")?.deny ?? false).toBe(false);
      expect(write(repo, "design", "direction.html")?.deny ?? false).toBe(false);
      expect(write(repo, "receipts", "x.json")?.deny ?? false).toBe(false);
      expect(write(repo, "cache", "verdicts", "a.json")?.deny ?? false).toBe(false);
    } finally {
      rmSync(repo, { recursive: true, force: true });
    }
  });

  test("the four files the chain itself reads are denied", () => {
    const repo = slotRepo(false);
    try {
      for (const name of ["config.toml", "overrides.toml", "ai-eng.lock", "arch.rules.json"]) {
        expect(write(repo, name)?.deny).toBe(true);
      }
    } finally {
      rmSync(repo, { recursive: true, force: true });
    }
  });

  test("an approved contract is frozen, and the other three are not", () => {
    const repo = slotRepo(true);
    try {
      // The pin, not the name: `spec.html` is the one artifact of the four that stops
      // being a draft the moment a human approves it.
      expect(write(repo, "spec.html")?.deny).toBe(true);
      expect(write(repo, "plan.html")?.deny ?? false).toBe(false);
      expect(write(repo, "brainstorm.md")?.deny ?? false).toBe(false);
      expect(write(repo, "recap.html")?.deny ?? false).toBe(false);
    } finally {
      rmSync(repo, { recursive: true, force: true });
    }
  });

  test("a command that names the directory is judged as a whole; its files are not it", () => {
    const repo = slotRepo(false);
    try {
      const bash = (command: string) => runSelfProtect({ tool_name: "Bash", tool_input: { command } } as never, repo);
      // `rm -rf .ai-engineering` names the directory and nothing else: the layer rules, the
      // lock, the ledger and the receipts in one word. That stays denied, and so does
      // naming one of the four files the chain reads.
      expect(bash(`rm -rf ${join(repo, ".ai-engineering")}`)?.deny).toBe(true);
      expect(bash(`rm -rf ${join(repo, ".ai-engineering", "ai-eng.lock")}`)?.deny).toBe(true);
      // Its children are the session's own material, so deleting or moving one is a write
      // like any other.
      expect(bash(`rm -rf ${join(repo, ".ai-engineering", "brainstorm.md")}`)?.deny ?? false).toBe(false);
      expect(bash(`mv ${join(repo, ".ai-engineering", "brainstorm.md")} /tmp/x`)?.deny ?? false).toBe(false);
    } finally {
      rmSync(repo, { recursive: true, force: true });
    }
  });
});
