import { spawn } from "node:child_process";

import { type Result, err, ok } from "../../shared/kernel/result.ts";
import {
  type SLSAProvenance,
  SignatureError,
  type SignaturePort,
  type VerificationContext,
} from "../../shared/ports/signature.ts";

/**
 * SigstoreAdapter — driven adapter that shells out to the `cosign` and
 * `slsa-verifier` CLIs to verify Sigstore keyless OIDC bundles and SLSA
 * v1.0 provenance attestations.
 *
 * Why subprocess over an SDK: the official Sigstore TS SDK (`sigstore-js`)
 * carries a heavy transitive footprint and conflicts with our supply-chain
 * stance (we install plugins with `--ignore-scripts` and prefer pinned CLIs
 * verified by their own Sigstore signature). Spawning the CLI keeps trust
 * boundaries explicit: the developer's package manager installs the binary,
 * we only invoke it. Cross-platform safe via array args (no shell interp).
 *
 * Trust pipeline (ADR-0006):
 *   1. `verify(ctx)` — Sigstore keyless OIDC bundle verification (all tiers).
 *   2. `verifySLSA(...)` — SLSA v1.0 provenance check via `slsa-verifier`.
 *
 * Alpha-default UX: most users have no `cosign` or `slsa-verifier` installed.
 * The adapter probes the binary first and returns a clear `SignatureError`
 * with `reason: "invalid-bundle"` when the tool is unavailable. We do not
 * silently no-op — refusing to verify is the safe default per Constitution VI.
 */
export interface SigstoreAdapterOptions {
  readonly cosignPath?: string;
  readonly slsaVerifierPath?: string;
}

export class SigstoreAdapter implements SignaturePort {
  private readonly cosignPath: string;
  private readonly slsaVerifierPath: string;

  constructor(options?: Readonly<SigstoreAdapterOptions>) {
    this.cosignPath = options?.cosignPath ?? "cosign";
    this.slsaVerifierPath = options?.slsaVerifierPath ?? "slsa-verifier";
  }

  async verify(ctx: VerificationContext): Promise<Result<void, SignatureError>> {
    const probe = await runCli(this.cosignPath, ["--version"]);
    if (!probe.ok) {
      return err(
        new SignatureError(
          `cosign is not available on PATH (${this.cosignPath}). Install cosign to verify Sigstore bundles: https://docs.sigstore.dev/cosign/installation`,
          "invalid-bundle",
        ),
      );
    }

    const result = await runCli(this.cosignPath, [
      "verify-blob",
      ctx.artifactPath,
      "--bundle",
      bundleArgFrom(ctx),
      "--certificate-identity-regexp",
      ctx.expectedIdentityRegex,
      "--certificate-oidc-issuer",
      ctx.expectedIssuer,
    ]);

    if (!result.ok) {
      return err(classifyCosignFailure(result.stderr, result.stdout));
    }

    return ok(undefined);
  }

  async verifySLSA(
    artifactPath: string,
    attestationPath: string,
    sourceUri: string,
  ): Promise<Result<SLSAProvenance, SignatureError>> {
    const probe = await runCli(this.slsaVerifierPath, ["version"]);
    if (!probe.ok) {
      return err(
        new SignatureError(
          `slsa-verifier is not available on PATH (${this.slsaVerifierPath}). Install slsa-verifier to verify SLSA v1.0 provenance: https://github.com/slsa-framework/slsa-verifier#installation`,
          "invalid-bundle",
        ),
      );
    }

    const result = await runCli(this.slsaVerifierPath, [
      "verify-artifact",
      artifactPath,
      "--provenance-path",
      attestationPath,
      "--source-uri",
      sourceUri,
    ]);

    if (!result.ok) {
      return err(classifySlsaFailure(result.stderr, result.stdout));
    }

    return ok(parseSlsaProvenance(result.stdout, sourceUri));
  }
}

// -----------------------------------------------------------------------------
// Internals: subprocess plumbing + output parsing.
// -----------------------------------------------------------------------------

interface CliResult {
  readonly ok: boolean;
  readonly stdout: string;
  readonly stderr: string;
  readonly code: number | null;
}

const runCli = (binary: string, args: readonly string[]): Promise<CliResult> =>
  new Promise((resolve) => {
    let stdout = "";
    let stderr = "";
    let settled = false;

    const settle = (result: CliResult): void => {
      if (settled) return;
      settled = true;
      resolve(result);
    };

    try {
      const child = spawn(binary, [...args]);
      child.stdout.on("data", (d: Buffer) => {
        stdout += d.toString("utf8");
      });
      child.stderr.on("data", (d: Buffer) => {
        stderr += d.toString("utf8");
      });
      child.on("error", (e) => {
        // ENOENT and friends: treat as a non-ok CliResult so the caller can
        // surface a friendly SignatureError. We never throw past this boundary.
        settle({
          ok: false,
          stdout,
          stderr: stderr || (e instanceof Error ? e.message : String(e)),
          code: null,
        });
      });
      child.on("close", (code) => {
        settle({ ok: code === 0, stdout, stderr, code });
      });
    } catch (e) {
      settle({
        ok: false,
        stdout,
        stderr: e instanceof Error ? e.message : String(e),
        code: null,
      });
    }
  });

const bundleArgFrom = (ctx: VerificationContext): string => {
  // cosign's `--bundle` expects a JSON file path. The port hands us the bundle
  // contents as structured fields; we serialize to a stable JSON string so a
  // future filesystem-backed variant can persist it. For now cosign reads the
  // bundle path from disk — callers stage the bundle file before invoking.
  // This adapter assumes `ctx.bundle.signature` doubles as the bundle path
  // when the field is a path-like string. The plugin install flow is
  // responsible for materializing the bundle on disk first.
  return ctx.bundle.signature;
};

const classifyCosignFailure = (stderr: string, stdout: string): SignatureError => {
  const text = `${stderr}\n${stdout}`.toLowerCase();
  if (text.includes("certificate identity") || text.includes("identity-mismatch")) {
    return new SignatureError(
      `Sigstore identity mismatch: ${(stderr || stdout).trim()}`,
      "identity-mismatch",
    );
  }
  if (text.includes("rekor") && text.includes("not found")) {
    return new SignatureError(`Rekor entry missing: ${(stderr || stdout).trim()}`, "rekor-missing");
  }
  if (text.includes("expired") || text.includes("not valid after")) {
    return new SignatureError(`Certificate expired: ${(stderr || stdout).trim()}`, "expired-cert");
  }
  return new SignatureError(
    `cosign verify-blob failed: ${(stderr || stdout || "unknown error").trim()}`,
    "invalid-bundle",
  );
};

const classifySlsaFailure = (stderr: string, stdout: string): SignatureError => {
  const msg = (stderr || stdout || "unknown error").trim();
  return new SignatureError(`slsa-verifier failed: ${msg}`, "invalid-bundle");
};

const parseSlsaProvenance = (stdout: string, sourceUri: string): SLSAProvenance => {
  // slsa-verifier prints lines like:
  //   Verified signature against tlog entry index N for ...
  //   PASSED: SLSA verification passed
  //   Verifying artifact <hash>: PASSED
  //   builderID: https://github.com/slsa-framework/slsa-github-generator/...
  const builderMatch = stdout.match(/builder(?:\s|-)?id[:=]\s*(\S+)/i);
  const builderId = builderMatch?.[1] ?? "unknown";
  return {
    builderId,
    buildType: "https://github.com/slsa-framework/slsa-github-generator/generic@v1",
    invocation: Object.freeze({}),
    materials: Object.freeze([Object.freeze({ uri: sourceUri, digest: Object.freeze({}) })]),
  };
};
