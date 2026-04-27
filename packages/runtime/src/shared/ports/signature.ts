import type { Result } from "../kernel/result.ts";

/**
 * SignaturePort — driven port for Sigstore keyless OIDC signing/verifying.
 *
 * Used by the plugin install flow to verify Sigstore bundles, SLSA v1.0
 * provenance, SBOM CycloneDX, and OpenSSF Scorecard ≥7 (verified tier).
 */
export interface SignatureBundle {
  readonly signature: string;
  readonly certificate: string;
  readonly rekorEntryId: string;
}

export interface SLSAProvenance {
  readonly builderId: string;
  readonly buildType: string;
  readonly invocation: Readonly<Record<string, unknown>>;
  readonly materials: ReadonlyArray<{
    uri: string;
    digest: Record<string, string>;
  }>;
}

export interface VerificationContext {
  readonly artifactPath: string;
  readonly bundle: SignatureBundle;
  readonly expectedIdentityRegex: string;
  readonly expectedIssuer: string;
}

export class SignatureError extends Error {
  constructor(
    message: string,
    public readonly reason:
      | "invalid-bundle"
      | "identity-mismatch"
      | "rekor-missing"
      | "expired-cert",
  ) {
    super(message);
    this.name = "SignatureError";
  }
}

export interface SignaturePort {
  verify(ctx: VerificationContext): Promise<Result<void, SignatureError>>;
  verifySLSA(
    artifactPath: string,
    attestationPath: string,
    sourceUri: string,
  ): Promise<Result<SLSAProvenance, SignatureError>>;
}
