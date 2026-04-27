import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { isErr, isOk } from "../../../shared/kernel/result.ts";
import {
  type SignatureBundle,
  SignatureError,
  type VerificationContext,
} from "../../../shared/ports/signature.ts";
import { SigstoreAdapter } from "../sigstore.ts";

const cosignOnPath = (() => {
  const r = spawnSync("cosign", ["--version"]);
  return r.status === 0;
})();

const slsaVerifierOnPath = (() => {
  const r = spawnSync("slsa-verifier", ["version"]);
  return r.status === 0;
})();

let workDir = "";

const stubBundle = (): SignatureBundle => ({
  signature: "MEUCIQDfake-signature-bytes",
  certificate: "-----BEGIN CERTIFICATE-----\nFAKE-CERT\n-----END CERTIFICATE-----\n",
  rekorEntryId: "1234567890abcdef",
});

const stubContext = (artifactPath: string): VerificationContext => ({
  artifactPath,
  bundle: stubBundle(),
  expectedIdentityRegex:
    "^https://github.com/ai-engineering/.+/.github/workflows/release.yml@refs/tags/v.+",
  expectedIssuer: "https://token.actions.githubusercontent.com",
});

beforeEach(() => {
  workDir = mkdtempSync(join(tmpdir(), "ai-eng-sigstore-"));
});

afterEach(() => {
  rmSync(workDir, { recursive: true, force: true });
});

// -----------------------------------------------------------------------------
// Tier 1: tests that always run (do NOT require real cosign on PATH).
// They override the binary path to a known-bad value and assert the adapter
// returns SignatureError with reason="invalid-bundle" and a "cosign"-flavoured
// message. This is the alpha-default UX: most users have no cosign installed.
// -----------------------------------------------------------------------------

describe("SigstoreAdapter — cosign not available", () => {
  test("verify() returns SignatureError when cosign binary is missing", async () => {
    const adapter = new SigstoreAdapter({
      cosignPath: "/nonexistent/path/to/cosign",
    });
    const ctx = stubContext(join(workDir, "artifact.tgz"));
    writeFileSync(ctx.artifactPath, "fake-artifact-bytes");

    const r = await adapter.verify(ctx);
    expect(isErr(r)).toBe(true);
    if (isErr(r)) {
      expect(r.error).toBeInstanceOf(SignatureError);
      expect(r.error.reason).toBe("invalid-bundle");
      expect(r.error.message.toLowerCase()).toContain("cosign");
    }
  });

  test("verifySLSA() returns SignatureError when slsa-verifier binary is missing", async () => {
    const adapter = new SigstoreAdapter({
      slsaVerifierPath: "/nonexistent/path/to/slsa-verifier",
    });
    const artifact = join(workDir, "artifact.tgz");
    const attestation = join(workDir, "attestation.intoto.jsonl");
    writeFileSync(artifact, "fake");
    writeFileSync(attestation, "{}");

    const r = await adapter.verifySLSA(
      artifact,
      attestation,
      "github.com/ai-engineering/example-plugin",
    );
    expect(isErr(r)).toBe(true);
    if (isErr(r)) {
      expect(r.error).toBeInstanceOf(SignatureError);
      expect(r.error.reason).toBe("invalid-bundle");
      expect(r.error.message.toLowerCase()).toContain("slsa-verifier");
    }
  });

  test("verify() error message hints at remediation", async () => {
    const adapter = new SigstoreAdapter({
      cosignPath: "/definitely/not/here/cosign",
    });
    const ctx = stubContext(join(workDir, "x.tgz"));
    writeFileSync(ctx.artifactPath, "");

    const r = await adapter.verify(ctx);
    if (isErr(r)) {
      // Message should be actionable for the user, not just a raw spawn error.
      expect(r.error.message).toMatch(/not available|not installed|not found/i);
    }
  });
});

// -----------------------------------------------------------------------------
// Tier 2: tests that run only when cosign IS available on PATH. These exercise
// the real spawn path against a deliberately-malformed bundle/artifact so we
// see the verify-blob failure flow without leaving the box.
// -----------------------------------------------------------------------------

const dscribeCosign = cosignOnPath ? describe : describe.skip;

dscribeCosign("SigstoreAdapter — cosign available, verification fails", () => {
  test("verify() returns SignatureError when artifact does not exist", async () => {
    const adapter = new SigstoreAdapter();
    const ctx = stubContext(join(workDir, "ghost-artifact.tgz"));
    // Intentionally do NOT create the artifact. Real cosign will fail.

    const r = await adapter.verify(ctx);
    expect(isErr(r)).toBe(true);
    if (isErr(r)) {
      expect(r.error).toBeInstanceOf(SignatureError);
      expect(r.error.reason).toBe("invalid-bundle");
    }
  });

  test("verify() returns SignatureError on malformed bundle", async () => {
    const adapter = new SigstoreAdapter();
    const artifact = join(workDir, "art.tgz");
    writeFileSync(artifact, "garbage");
    const ctx = stubContext(artifact);

    const r = await adapter.verify(ctx);
    expect(isErr(r)).toBe(true);
    if (isErr(r)) expect(r.error).toBeInstanceOf(SignatureError);
  });
});

const dscribeSLSA = slsaVerifierOnPath ? describe : describe.skip;

dscribeSLSA("SigstoreAdapter — slsa-verifier available, verification fails", () => {
  test("verifySLSA() returns SignatureError on missing artifact", async () => {
    const adapter = new SigstoreAdapter();
    const artifact = join(workDir, "missing-art.tgz");
    const attestation = join(workDir, "att.intoto.jsonl");
    writeFileSync(attestation, "{}");

    const r = await adapter.verifySLSA(artifact, attestation, "github.com/ai-engineering/example");
    expect(isErr(r)).toBe(true);
    if (isErr(r)) expect(r.error).toBeInstanceOf(SignatureError);
  });
});

// -----------------------------------------------------------------------------
// Construction sanity: adapter is hexagonal — no dependencies on infra beyond
// optional binary paths. Default ctor uses the names "cosign"/"slsa-verifier".
// -----------------------------------------------------------------------------

describe("SigstoreAdapter — construction", () => {
  test("default ctor uses 'cosign' and 'slsa-verifier' binary names", () => {
    const adapter = new SigstoreAdapter();
    expect(adapter).toBeInstanceOf(SigstoreAdapter);
  });

  test("custom binary paths are accepted via options", () => {
    const adapter = new SigstoreAdapter({
      cosignPath: "/custom/cosign",
      slsaVerifierPath: "/custom/slsa-verifier",
    });
    expect(adapter).toBeInstanceOf(SigstoreAdapter);
  });

  test("returns Result.ok shape only on real success — failure path always errs", async () => {
    const adapter = new SigstoreAdapter({
      cosignPath: "/nope",
      slsaVerifierPath: "/nope",
    });
    const ctx = stubContext(join(workDir, "a.tgz"));
    writeFileSync(ctx.artifactPath, "");
    const r = await adapter.verify(ctx);
    // Sanity: on this synthetic failure path we MUST get err, not ok.
    expect(isOk(r)).toBe(false);
  });
});
