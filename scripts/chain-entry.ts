// ai-eng chain — the entry point gen-assets bundles for in-process plugin hosts
// (OMP/OpenCode). Exposes chain(event, payload, opts): the guard chain,
// fail-closed, never process.exit inside the host — a deny returns the verdict
// to the caller (inProcess: true).
import { runChain } from "../src/chain/mod.ts";

export { runChain };

export function chain(event: string, payload: Record<string, unknown>, opts: { surface?: string } = {}) {
  return runChain(payload, event, { ...opts, inProcess: true });
}
