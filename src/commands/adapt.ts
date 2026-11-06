// Proposals can be prepared in the governed session, but cannot be applied there.
// The self-hash is integrity metadata, not proof of human approval.

import { sha256 } from "../install.ts";

export const PROPOSAL_RELATIVE = ".ai-engineering/config-proposal.html";

export function proposalPayload(files: Record<string, string>): string {
  const ordered: Record<string, string> = {};
  for (const key of Object.keys(files).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0))) ordered[key] = files[key]!;
  return JSON.stringify(ordered).replace(/</g, "\\u003c");
}

export function proposalHtml(files: Record<string, string>): string {
  const payload = proposalPayload(files);
  const hash = sha256(payload);
  return `<!doctype html>\n<meta name="ai-eng-proposal-sha256" content="${hash}">\n<script type="application/json" id="payload">${payload}</script>\n`;
}

function fail(message: string): number {
  process.stderr.write(`${message}\n`);
  return 2;
}

/** A same-user agent can forge a proposal hash, so no in-process writer is safe. */
export function adaptApply(_root: string): number {
  return fail("adapt apply is disabled: a proposal hash cannot prove human approval. Apply the reviewed changes manually outside the governed agent session.");
}

export function adaptMain(args: string[]): number {
  const sub = args[0];
  if (sub !== "apply") {
    process.stderr.write("usage: ai-eng adapt apply\n");
    return 2;
  }
  return adaptApply(process.cwd());
}
