// Adversarial: the gate that decides whether a repo participates at all. Everything
// under it — guards, receipts, the git floor — is policy a repo asks for by declaring
// itself in .ai-engineering/config.toml. A repo that never asked gets allow, exit 0
// and not one byte written: no receipts, no .ai-engineering/ invented behind the
// user's back. The control in each block is the same payload in a governed repo, so
// an allow can never be a fixture that forgot to be adversarial (§A, G2-G5).

import { describe, test, expect } from "bun:test";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { runChain } from "../../src/chain/mod.ts";
import { receiptsDir } from "../../src/env.ts";

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
});
