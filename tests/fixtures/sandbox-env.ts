// The variables a sandboxed suite points at a machine of its own. A suite hands them
// back exactly as it found them — deleting instead of restoring leaves every later suite
// in the same serial process on a different machine home (tests/test-hygiene.spec.ts).

export const SANDBOX_VARS = ["AI_ENG_HOME", "PI_CODING_AGENT_DIR", "GIT_CONFIG_GLOBAL"] as const;

export type SandboxEnv = Record<(typeof SANDBOX_VARS)[number], string | undefined>;

export function snapshotSandboxEnv(): SandboxEnv {
  return { AI_ENG_HOME: process.env["AI_ENG_HOME"], PI_CODING_AGENT_DIR: process.env["PI_CODING_AGENT_DIR"], GIT_CONFIG_GLOBAL: process.env["GIT_CONFIG_GLOBAL"] };
}

/** Put each variable back as the snapshot saw it: unset stays unset, never "undefined". */
export function restoreSandboxEnv(snapshot: SandboxEnv): void {
  for (const name of SANDBOX_VARS) {
    const prior = snapshot[name];
    if (prior === undefined) delete process.env[name];
    else process.env[name] = prior;
  }
}
