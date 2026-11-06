// Release policy: nothing is published unless the release tag already exists, names the
// dispatched commit, is an annotated tag cryptographically signed with SSH by a key the owner allowlisted — both
// in RELEASE_ALLOWED_SIGNERS and by fingerprint in RELEASE_SIGNER_FINGERPRINTS — and every
// bundled-content row in NOTICE.md records owner-verified redistribution rights. Every
// fixture is a throwaway repository under os.tmpdir() signed by a key generated here; no
// real signer is configured, and the policy only reads: it never creates, moves or
// deletes a tag.
import { afterAll, afterEach, beforeAll, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { evaluateReleasePolicy } from "../scripts/release-policy.ts";

const REPO = join(import.meta.dir, "..");
// The policy runs on the Linux release runner. The hosted Windows image cannot create the
// SSH-signed tag fixtures these cases build, so they would test the fixture, not the policy.
const IS_WINDOWS = process.platform === "win32";
const POLICY_SCRIPT = join(REPO, "scripts/release-policy.ts");
const TAG = "v9.9.9";
const FROZEN_TAG = "2.6.0";
const PRINCIPAL = "release-test@example.invalid";
const FINGERPRINT = /^SHA256:[A-Za-z0-9+/]{43}$/;
// Valid in shape, belongs to no key: the allowlist names someone else.
const STRANGER_FINGERPRINT = `SHA256:${"A".repeat(43)}`;
const hasSshKeygen = Bun.which("ssh-keygen") !== null;

// The contract's refusals, verbatim: each names what is wrong and the next step.
const MISSING_ALLOWED_SIGNERS =
  "RELEASE_ALLOWED_SIGNERS is not set: an owner must add the release key's allowed_signers line as a repository variable before publishing.";
const MISSING_FINGERPRINTS =
  "RELEASE_SIGNER_FINGERPRINTS is not set: an owner must list the release key's SHA256 fingerprint as a repository variable before publishing.";
const malformedFingerprint = (entry: string) =>
  `RELEASE_SIGNER_FINGERPRINTS entry "${entry}" is not a SHA256:<43 base64 characters> fingerprint: replace it with the fingerprint printed by ssh-keygen -lf <key>.pub.`;
const tagMissing = (tag: string) =>
  `Tag ${tag} does not exist: the release owner must push a signed annotated tag (git tag -s) before publishing.`;
const tagLightweight = (tag: string) =>
  `Tag ${tag} is lightweight: release from a new version whose tag is signed and annotated (git tag -s); never move an existing tag.`;
const tagUnsigned = (tag: string) =>
  `Tag ${tag} is annotated but unsigned: release from a new version whose tag is signed with an allowlisted SSH key (git tag -s); never move an existing tag.`;
const signatureUnverified = (tag: string) =>
  `Tag ${tag} has a signature that does not verify against RELEASE_ALLOWED_SIGNERS: sign with an allowlisted key, or have an owner update the variable.`;
const fingerprintNotAllowed = (tag: string, fingerprint: string) =>
  `Tag ${tag} is signed by ${fingerprint}, which is not in RELEASE_SIGNER_FINGERPRINTS: an owner must allowlist that fingerprint, or the tag must be signed by an allowlisted key.`;
const noticeUnreadable = (path: string) => `NOTICE.md could not be read at ${path}: restore it before publishing.`;
const NOTICE_NO_COLUMN =
  "NOTICE.md has no Redistribution column in its attribution table: add one and record verified or unresolved (<reason>) for every row.";
const NOTICE_NO_ROWS =
  "NOTICE.md lists no bundled content in its attribution table: restore the attribution rows before publishing.";
const noticeUnparseableRow = (line: number) =>
  `NOTICE.md line ${line} is not a parseable attribution row: give it every column and a Redistribution value of verified or unresolved (<reason>).`;
const DISPATCHED_UNKNOWN =
  'The dispatched commit is unknown: pass --sha <commit> (the workflow passes "$GITHUB_SHA") so the policy can prove the tag names it.';
const dispatchedMalformed = (sha: string) =>
  `--sha ${sha} is not a full lowercase commit SHA: pass the dispatched commit as git rev-parse prints it.`;
const tagOnOtherCommit = (tag: string, tagged: string, dispatched: string) =>
  `Tag ${tag} points at ${tagged}, not the dispatched commit ${dispatched}: sign the tag on the commit you dispatch.`;
const USAGE = "usage: bun scripts/release-policy.ts --tag <tag> [--sha <commit>]   (--sha defaults to GITHUB_SHA)\n";
const rightsUnresolved = (content: string, reason: string) =>
  `${content} redistribution rights are unresolved (${reason}): an owner must verify them and mark the row verified in NOTICE.md.`;

type SigningKey = { privatePath: string; allowedSignersLine: string; fingerprint: string };

const roots: string[] = [];
let keyRoot = "";
let releaseKey: SigningKey;
let otherKey: SigningKey;

function newRoot(prefix: string): string {
  const root = mkdtempSync(join(tmpdir(), prefix));
  roots.push(root);
  return root;
}

/** Git and ssh-keygen with no user/global/system configuration, no agent and no inherited
 *  repository location: the machine running the suite decides nothing. */
function isolatedEnv(globalConfig: string): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = { ...process.env };
  for (const name of ["GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_CEILING_DIRECTORIES", "SSH_AUTH_SOCK"]) {
    delete env[name];
  }
  delete env["RELEASE_ALLOWED_SIGNERS"];
  delete env["RELEASE_SIGNER_FINGERPRINTS"];
  // CI sets GITHUB_SHA for the suite itself; a fixture names its dispatched commit explicitly.
  delete env["GITHUB_SHA"];
  return {
    ...env,
    GIT_CONFIG_GLOBAL: globalConfig,
    GIT_CONFIG_NOSYSTEM: "1",
    GIT_AUTHOR_NAME: "release-test",
    GIT_AUTHOR_EMAIL: PRINCIPAL,
    GIT_COMMITTER_NAME: "release-test",
    GIT_COMMITTER_EMAIL: PRINCIPAL,
  };
}

function run(command: string, args: string[], cwd: string, env: NodeJS.ProcessEnv): string {
  const result = spawnSync(command, args, { cwd, env, encoding: "utf8" });
  if (result.status !== 0) throw new Error(`${command} ${args.join(" ")} failed (${result.status}): ${result.stderr}`);
  return result.stdout;
}

function generateKey(name: string): SigningKey {
  const env = isolatedEnv(join(keyRoot, "gitconfig"));
  const privatePath = join(keyRoot, name);
  run("ssh-keygen", ["-q", "-t", "ed25519", "-N", "", "-C", name, "-f", privatePath], keyRoot, env);
  const publicKey = readFileSync(`${privatePath}.pub`, "utf8").trim();
  const fingerprint = run("ssh-keygen", ["-lf", `${privatePath}.pub`], keyRoot, env).split(" ")[1] ?? "";
  if (!FINGERPRINT.test(fingerprint)) throw new Error(`unexpected fingerprint for ${name}: ${fingerprint}`);
  return { privatePath, allowedSignersLine: `${PRINCIPAL} ${publicKey}\n`, fingerprint };
}

beforeAll(() => {
  if (!hasSshKeygen) return;
  keyRoot = mkdtempSync(join(tmpdir(), "release-policy-keys-"));
  writeFileSync(join(keyRoot, "gitconfig"), "");
  releaseKey = generateKey("release-key");
  otherKey = generateKey("other-key");
});

afterAll(() => {
  if (keyRoot !== "") rmSync(keyRoot, { recursive: true, force: true });
});

afterEach(() => {
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

type Fixture = { root: string; repo: string; env: NodeJS.ProcessEnv; globalConfig: string };

/** A one-commit repository under os.tmpdir() with an empty global config of its own. */
function newFixture(): Fixture {
  const root = newRoot("release-policy-");
  const repo = join(root, "repo");
  const globalConfig = join(root, "gitconfig");
  writeFileSync(globalConfig, "");
  const env = isolatedEnv(globalConfig);
  run("git", ["init", "-q", repo], root, env);
  run("git", ["-c", "commit.gpgsign=false", "commit", "--allow-empty", "-q", "-m", "fixture"], repo, env);
  return { root, repo, env, globalConfig };
}

function git(fixture: Fixture, args: string[]): string {
  return run("git", args, fixture.repo, fixture.env);
}

function signedTag(fixture: Fixture, key: SigningKey, tag = TAG): void {
  git(fixture, ["-c", "gpg.format=ssh", "-c", `user.signingKey=${key.privatePath}`, "tag", "-s", "-m", `release ${tag}`, tag]);
}

function annotatedTag(fixture: Fixture, tag = TAG): void {
  git(fixture, ["-c", "tag.gpgSign=false", "tag", "-a", "-m", `release ${tag}`, tag]);
}

function lightweightTag(fixture: Fixture, tag = TAG): void {
  git(fixture, ["-c", "tag.gpgSign=false", "tag", tag]);
}

const NOTICE_HEAD = [
  "# NOTICE.md — fixture attribution ledger",
  "",
  "Format: skill — source — author — license — URL — redistribution.",
  "",
];
const NOTICE_TABLE_HEADER = [
  "| Skill | Source (integrated verbatim) | Author | License | URL | Redistribution |",
  "|---|---|---|---|---|---|",
];
const VERIFIED_ROWS = [
  "| ai-alpha | original | fixture | Apache-2.0 | https://example.invalid/alpha | verified |",
  "| ai-beta | upstream method | fixture upstream | MIT | https://example.invalid/beta | verified |",
];
const NOTICE_TAIL = ["", "## Open issues", "- none in this fixture", ""];

function writeNotice(fixture: Fixture, lines: string[]): string {
  const path = join(fixture.root, "NOTICE.md");
  writeFileSync(path, lines.join("\n"));
  return path;
}

function verifiedNotice(fixture: Fixture): string {
  return writeNotice(fixture, [...NOTICE_HEAD, ...NOTICE_TABLE_HEADER, ...VERIFIED_ROWS, ...NOTICE_TAIL]);
}

type PolicyArgs = {
  tag?: string;
  dispatchedCommit?: string | undefined;
  allowedSigners?: string | undefined;
  signerFingerprints?: string | undefined;
  noticePath: string;
};

function head(fixture: Fixture): string {
  return git(fixture, ["rev-parse", "HEAD"]).trim();
}

/** Evaluates in-process with the fixture's isolated git configuration in effect, then
 *  puts the suite's environment back exactly as it was. The dispatched commit is the
 *  fixture's HEAD unless the case names one (an explicit undefined stays undefined). */
function evaluate(fixture: Fixture, args: PolicyArgs) {
  const saved = { global: process.env["GIT_CONFIG_GLOBAL"], nosystem: process.env["GIT_CONFIG_NOSYSTEM"] };
  process.env["GIT_CONFIG_GLOBAL"] = fixture.globalConfig;
  process.env["GIT_CONFIG_NOSYSTEM"] = "1";
  try {
    return evaluateReleasePolicy({
      repoRoot: fixture.repo,
      tag: args.tag ?? TAG,
      dispatchedCommit: "dispatchedCommit" in args ? args.dispatchedCommit : head(fixture),
      allowedSigners: args.allowedSigners,
      signerFingerprints: args.signerFingerprints,
      noticePath: args.noticePath,
    });
  } finally {
    if (saved.global === undefined) delete process.env["GIT_CONFIG_GLOBAL"];
    else process.env["GIT_CONFIG_GLOBAL"] = saved.global;
    if (saved.nosystem === undefined) delete process.env["GIT_CONFIG_NOSYSTEM"];
    else process.env["GIT_CONFIG_NOSYSTEM"] = saved.nosystem;
  }
}

function trustedConfig(): Pick<PolicyArgs, "allowedSigners" | "signerFingerprints"> {
  return { allowedSigners: releaseKey.allowedSignersLine, signerFingerprints: releaseKey.fingerprint };
}

if (!hasSshKeygen) console.warn("release-policy.spec: skipping signed-tag cases — ssh-keygen is not on PATH, so no SSH-signed tag fixture can be generated");

describe.skipIf(IS_WINDOWS)("U5 — a controlled fixture with every piece of evidence is allowed", () => {
  test.skipIf(!hasSshKeygen)(`allowed: annotated SSH-signed tag, allowlisted key and fingerprint, every NOTICE row verified`, () => {
    const fixture = newFixture();
    signedTag(fixture, releaseKey);
    const result = evaluate(fixture, {
      allowedSigners: releaseKey.allowedSignersLine,
      // A comma/newline list with surrounding blanks: only an exact listed entry counts.
      signerFingerprints: `\n${STRANGER_FINGERPRINT},\n  ${releaseKey.fingerprint}  \n`,
      noticePath: verifiedNotice(fixture),
    });
    expect(result).toEqual({ allowed: true, refusals: [] });
  });

  test.skipIf(!hasSshKeygen)("the CLI exits 0 and prints no refusal for the same evidence, reading NOTICE.md from the checkout", () => {
    const fixture = newFixture();
    signedTag(fixture, releaseKey);
    writeFileSync(join(fixture.repo, "NOTICE.md"), [...NOTICE_HEAD, ...NOTICE_TABLE_HEADER, ...VERIFIED_ROWS, ...NOTICE_TAIL].join("\n"));
    const result = spawnSync(process.execPath, [POLICY_SCRIPT, "--tag", TAG, "--sha", head(fixture)], {
      cwd: fixture.repo,
      env: { ...fixture.env, RELEASE_ALLOWED_SIGNERS: releaseKey.allowedSignersLine, RELEASE_SIGNER_FINGERPRINTS: releaseKey.fingerprint },
      encoding: "utf8",
    });
    expect({ status: result.status, stderr: result.stderr }).toEqual({ status: 0, stderr: "" });
  });
});

describe.skipIf(IS_WINDOWS)("U4 — signer configuration fails closed", () => {
  test.skipIf(!hasSshKeygen)("absent or blank configuration refuses, naming each missing variable", () => {
    const fixture = newFixture();
    signedTag(fixture, releaseKey);
    const noticePath = verifiedNotice(fixture);
    expect(evaluate(fixture, { allowedSigners: undefined, signerFingerprints: undefined, noticePath })).toEqual({
      allowed: false,
      refusals: [MISSING_ALLOWED_SIGNERS, MISSING_FINGERPRINTS],
    });
    expect(evaluate(fixture, { allowedSigners: " \n", signerFingerprints: "", noticePath })).toEqual({
      allowed: false,
      refusals: [MISSING_ALLOWED_SIGNERS, MISSING_FINGERPRINTS],
    });
    expect(evaluate(fixture, { allowedSigners: releaseKey.allowedSignersLine, signerFingerprints: ",\n,", noticePath })).toEqual({
      allowed: false,
      refusals: [MISSING_FINGERPRINTS],
    });
  });

  test.skipIf(!hasSshKeygen)("a malformed fingerprint entry refuses even when another entry matches the signer", () => {
    const fixture = newFixture();
    signedTag(fixture, releaseKey);
    const noticePath = verifiedNotice(fixture);
    const truncated = releaseKey.fingerprint.slice(0, -1);
    expect(
      evaluate(fixture, {
        allowedSigners: releaseKey.allowedSignersLine,
        signerFingerprints: `${releaseKey.fingerprint},MD5:aa:bb:cc\n${truncated}`,
        noticePath,
      }),
    ).toEqual({ allowed: false, refusals: [malformedFingerprint("MD5:aa:bb:cc"), malformedFingerprint(truncated)] });
  });
});

describe.skipIf(IS_WINDOWS)("U4 — the tag must exist, be annotated, signed and verified by an allowlisted key", () => {
  test.skipIf(!hasSshKeygen)("a missing tag refuses", () => {
    const fixture = newFixture();
    expect(evaluate(fixture, { ...trustedConfig(), noticePath: verifiedNotice(fixture) })).toEqual({
      allowed: false,
      refusals: [tagMissing(TAG)],
    });
  });

  test.skipIf(!hasSshKeygen)("a lightweight tag refuses", () => {
    const fixture = newFixture();
    lightweightTag(fixture);
    expect(evaluate(fixture, { ...trustedConfig(), noticePath: verifiedNotice(fixture) })).toEqual({
      allowed: false,
      refusals: [tagLightweight(TAG)],
    });
  });

  test.skipIf(!hasSshKeygen)("an annotated but unsigned tag refuses", () => {
    const fixture = newFixture();
    annotatedTag(fixture);
    expect(evaluate(fixture, { ...trustedConfig(), noticePath: verifiedNotice(fixture) })).toEqual({
      allowed: false,
      refusals: [tagUnsigned(TAG)],
    });
  });

  test.skipIf(!hasSshKeygen)("a tag signed by a key outside RELEASE_ALLOWED_SIGNERS refuses", () => {
    const fixture = newFixture();
    signedTag(fixture, otherKey);
    expect(evaluate(fixture, { ...trustedConfig(), noticePath: verifiedNotice(fixture) })).toEqual({
      allowed: false,
      refusals: [signatureUnverified(TAG)],
    });
  });

  test.skipIf(!hasSshKeygen)("an ambient git allowedSignersFile cannot vouch for a key the owner did not allow", () => {
    const fixture = newFixture();
    signedTag(fixture, otherKey);
    const hostileSigners = join(fixture.root, "hostile_allowed_signers");
    writeFileSync(hostileSigners, otherKey.allowedSignersLine);
    writeFileSync(fixture.globalConfig, `[gpg "ssh"]\n\tallowedSignersFile = ${hostileSigners.replaceAll("\\", "/")}\n`);
    expect(
      evaluate(fixture, {
        allowedSigners: releaseKey.allowedSignersLine,
        signerFingerprints: `${releaseKey.fingerprint},${otherKey.fingerprint}`,
        noticePath: verifiedNotice(fixture),
      }),
    ).toEqual({ allowed: false, refusals: [signatureUnverified(TAG)] });
  });

  test.skipIf(!hasSshKeygen)("a tag whose signature was tampered with refuses", () => {
    const fixture = newFixture();
    signedTag(fixture, releaseKey);
    const original = git(fixture, ["cat-file", "tag", TAG]);
    const forged = original.replace(`release ${TAG}`, `release ${TAG} (edited)`);
    const forgedObject = spawnSync("git", ["hash-object", "-t", "tag", "-w", "--stdin"], {
      cwd: fixture.repo,
      env: fixture.env,
      input: forged,
      encoding: "utf8",
    }).stdout.trim();
    git(fixture, ["update-ref", "refs/tags/v9.9.8", forgedObject]);
    expect(evaluate(fixture, { ...trustedConfig(), tag: "v9.9.8", noticePath: verifiedNotice(fixture) })).toEqual({
      allowed: false,
      refusals: [signatureUnverified("v9.9.8")],
    });
  });

  test.skipIf(!hasSshKeygen)("a verified signer whose fingerprint is not listed refuses, naming the fingerprint", () => {
    const fixture = newFixture();
    signedTag(fixture, releaseKey);
    expect(
      evaluate(fixture, {
        allowedSigners: releaseKey.allowedSignersLine,
        signerFingerprints: `${STRANGER_FINGERPRINT}\n${otherKey.fingerprint}`,
        noticePath: verifiedNotice(fixture),
      }),
    ).toEqual({ allowed: false, refusals: [fingerprintNotAllowed(TAG, releaseKey.fingerprint)] });
  });
});

describe.skipIf(IS_WINDOWS)("U4 — the signed tag must name the dispatched commit", () => {
  test.skipIf(!hasSshKeygen)("a valid signed tag on commit A refuses a release dispatched for commit B, naming both", () => {
    const fixture = newFixture();
    const tagged = head(fixture);
    signedTag(fixture, releaseKey);
    git(fixture, ["-c", "commit.gpgsign=false", "commit", "--allow-empty", "-q", "-m", "dispatched"]);
    const dispatched = head(fixture);
    expect(dispatched).not.toBe(tagged);
    expect(git(fixture, ["rev-parse", `${TAG}^{commit}`]).trim()).toBe(tagged);
    const noticePath = verifiedNotice(fixture);

    expect(evaluate(fixture, { ...trustedConfig(), dispatchedCommit: dispatched, noticePath })).toEqual({
      allowed: false,
      refusals: [tagOnOtherCommit(TAG, tagged, dispatched)],
    });
    expect(evaluate(fixture, { ...trustedConfig(), dispatchedCommit: tagged, noticePath })).toEqual({ allowed: true, refusals: [] });
  });

  test.skipIf(!hasSshKeygen)("a lightweight tag on another commit reports both refusals", () => {
    const fixture = newFixture();
    const tagged = head(fixture);
    lightweightTag(fixture);
    git(fixture, ["-c", "commit.gpgsign=false", "commit", "--allow-empty", "-q", "-m", "dispatched"]);
    const dispatched = head(fixture);
    expect(evaluate(fixture, { ...trustedConfig(), dispatchedCommit: dispatched, noticePath: verifiedNotice(fixture) })).toEqual({
      allowed: false,
      refusals: [tagLightweight(TAG), tagOnOtherCommit(TAG, tagged, dispatched)],
    });
  });

  test.skipIf(!hasSshKeygen)("an unknown or abbreviated dispatched commit refuses instead of skipping the comparison", () => {
    const fixture = newFixture();
    signedTag(fixture, releaseKey);
    const noticePath = verifiedNotice(fixture);
    const abbreviated = head(fixture).slice(0, 12);
    expect(evaluate(fixture, { ...trustedConfig(), dispatchedCommit: undefined, noticePath })).toEqual({
      allowed: false,
      refusals: [DISPATCHED_UNKNOWN],
    });
    expect(evaluate(fixture, { ...trustedConfig(), dispatchedCommit: " ", noticePath })).toEqual({
      allowed: false,
      refusals: [DISPATCHED_UNKNOWN],
    });
    expect(evaluate(fixture, { ...trustedConfig(), dispatchedCommit: abbreviated, noticePath })).toEqual({
      allowed: false,
      refusals: [dispatchedMalformed(abbreviated)],
    });
  });

  test.skipIf(!hasSshKeygen)("the CLI takes the dispatched commit from --sha, else GITHUB_SHA, and refuses without either", () => {
    const fixture = newFixture();
    const tagged = head(fixture);
    signedTag(fixture, releaseKey);
    git(fixture, ["-c", "commit.gpgsign=false", "commit", "--allow-empty", "-q", "-m", "dispatched"]);
    const dispatched = head(fixture);
    writeFileSync(join(fixture.repo, "NOTICE.md"), [...NOTICE_HEAD, ...NOTICE_TABLE_HEADER, ...VERIFIED_ROWS, ...NOTICE_TAIL].join("\n"));
    const env = { ...fixture.env, RELEASE_ALLOWED_SIGNERS: releaseKey.allowedSignersLine, RELEASE_SIGNER_FINGERPRINTS: releaseKey.fingerprint };
    const cli = (args: string[], extraEnv: NodeJS.ProcessEnv = {}) => {
      const result = spawnSync(process.execPath, [POLICY_SCRIPT, "--tag", TAG, ...args], { cwd: fixture.repo, env: { ...env, ...extraEnv }, encoding: "utf8" });
      return { status: result.status, stderr: result.stderr };
    };

    expect(cli(["--sha", dispatched])).toEqual({ status: 1, stderr: `${tagOnOtherCommit(TAG, tagged, dispatched)}\n` });
    expect(cli([], { GITHUB_SHA: dispatched })).toEqual({ status: 1, stderr: `${tagOnOtherCommit(TAG, tagged, dispatched)}\n` });
    expect(cli(["--sha", tagged], { GITHUB_SHA: dispatched })).toEqual({ status: 0, stderr: "" });
    expect(cli([])).toEqual({ status: 1, stderr: `${DISPATCHED_UNKNOWN}\n` });
    expect(cli(["--sha", tagged, "extra"])).toEqual({ status: 1, stderr: USAGE });
  });
});

describe.skipIf(IS_WINDOWS)("U4 — every bundled content row needs owner-verified redistribution rights", () => {
  test.skipIf(!hasSshKeygen)("each unresolved row refuses by name, in table order, with its reason", () => {
    const fixture = newFixture();
    signedTag(fixture, releaseKey);
    const noticePath = writeNotice(fixture, [
      ...NOTICE_HEAD,
      ...NOTICE_TABLE_HEADER,
      VERIFIED_ROWS[0] ?? "",
      "| ai-gamma | upstream skill | community | no license — attribution (H4) | local source | unresolved (no license — H4) |",
      VERIFIED_ROWS[1] ?? "",
      "| ai-delta | installed skill | unknown | unknown | installed locally | unresolved (author unknown) |",
      ...NOTICE_TAIL,
    ]);
    expect(evaluate(fixture, { ...trustedConfig(), noticePath })).toEqual({
      allowed: false,
      refusals: [rightsUnresolved("ai-gamma", "no license — H4"), rightsUnresolved("ai-delta", "author unknown")],
    });
  });

  test.skipIf(!hasSshKeygen)("a NOTICE without the Redistribution column refuses", () => {
    const fixture = newFixture();
    signedTag(fixture, releaseKey);
    const noticePath = writeNotice(fixture, [
      ...NOTICE_HEAD,
      "| Skill | Source (integrated verbatim) | Author | License | URL |",
      "|---|---|---|---|---|",
      "| ai-alpha | original | fixture | Apache-2.0 | https://example.invalid/alpha |",
      ...NOTICE_TAIL,
    ]);
    expect(evaluate(fixture, { ...trustedConfig(), noticePath })).toEqual({ allowed: false, refusals: [NOTICE_NO_COLUMN] });
  });

  test.skipIf(!hasSshKeygen)("rows that cannot be parsed refuse by line instead of being skipped", () => {
    const fixture = newFixture();
    signedTag(fixture, releaseKey);
    const tableStart = NOTICE_HEAD.length + NOTICE_TABLE_HEADER.length;
    const noticePath = writeNotice(fixture, [
      ...NOTICE_HEAD,
      ...NOTICE_TABLE_HEADER,
      VERIFIED_ROWS[0] ?? "",
      "| ai-short | original | fixture | MIT | verified |",
      "| ai-pending | original | fixture | MIT | https://example.invalid/pending | pending |",
      "| ai-bare | original | fixture | MIT | https://example.invalid/bare | unresolved |",
      ...NOTICE_TAIL,
    ]);
    expect(evaluate(fixture, { ...trustedConfig(), noticePath })).toEqual({
      allowed: false,
      refusals: [noticeUnparseableRow(tableStart + 2), noticeUnparseableRow(tableStart + 3), noticeUnparseableRow(tableStart + 4)],
    });
  });

  test.skipIf(!hasSshKeygen)("a table with no rows, or no NOTICE at all, refuses", () => {
    const fixture = newFixture();
    signedTag(fixture, releaseKey);
    const emptyTable = writeNotice(fixture, [...NOTICE_HEAD, ...NOTICE_TABLE_HEADER, ...NOTICE_TAIL]);
    expect(evaluate(fixture, { ...trustedConfig(), noticePath: emptyTable })).toEqual({ allowed: false, refusals: [NOTICE_NO_ROWS] });
    const absent = join(fixture.root, "absent", "NOTICE.md");
    expect(evaluate(fixture, { ...trustedConfig(), noticePath: absent })).toEqual({ allowed: false, refusals: [noticeUnreadable(absent)] });
  });
});

describe.skipIf(IS_WINDOWS)("U4 — refusals are reported together, and the policy only reads", () => {
  test.skipIf(!hasSshKeygen)("configuration, tag and rights refusals arrive in one report, in that order", () => {
    const fixture = newFixture();
    lightweightTag(fixture);
    const noticePath = writeNotice(fixture, [
      ...NOTICE_HEAD,
      ...NOTICE_TABLE_HEADER,
      "| ai-gamma | upstream skill | community | none | local source | unresolved (no license — H4) |",
      ...NOTICE_TAIL,
    ]);
    expect(evaluate(fixture, { allowedSigners: undefined, signerFingerprints: "not-a-fingerprint", noticePath })).toEqual({
      allowed: false,
      refusals: [
        MISSING_ALLOWED_SIGNERS,
        malformedFingerprint("not-a-fingerprint"),
        tagLightweight(TAG),
        rightsUnresolved("ai-gamma", "no license — H4"),
      ],
    });
  });

  test.skipIf(!hasSshKeygen)("the CLI prints every refusal on its own line and exits 1", () => {
    const fixture = newFixture();
    annotatedTag(fixture);
    writeFileSync(
      join(fixture.repo, "NOTICE.md"),
      [...NOTICE_HEAD, ...NOTICE_TABLE_HEADER, "| ai-gamma | upstream | community | none | local | unresolved (no license — H4) |", ...NOTICE_TAIL].join("\n"),
    );
    const result = spawnSync(process.execPath, [POLICY_SCRIPT, "--tag", TAG, "--sha", head(fixture)], {
      cwd: fixture.repo,
      env: { ...fixture.env, RELEASE_SIGNER_FINGERPRINTS: releaseKey.fingerprint },
      encoding: "utf8",
    });
    expect({ status: result.status, stderr: result.stderr }).toEqual({
      status: 1,
      stderr: `${[MISSING_ALLOWED_SIGNERS, tagUnsigned(TAG), rightsUnresolved("ai-gamma", "no license — H4")].join("\n")}\n`,
    });
  });

  test.skipIf(!hasSshKeygen)("the CLI refuses without --tag", () => {
    const fixture = newFixture();
    const result = spawnSync(process.execPath, [POLICY_SCRIPT], {
      cwd: fixture.repo,
      env: { ...fixture.env, RELEASE_ALLOWED_SIGNERS: releaseKey.allowedSignersLine, RELEASE_SIGNER_FINGERPRINTS: releaseKey.fingerprint },
      encoding: "utf8",
    });
    expect({ status: result.status, stderr: result.stderr }).toEqual({ status: 1, stderr: USAGE });
  });

  test.skipIf(!hasSshKeygen)("no tag is created, moved or deleted, and a fixture 2.6.0 tag stays byte-identical", () => {
    const fixture = newFixture();
    annotatedTag(fixture, FROZEN_TAG);
    git(fixture, ["-c", "commit.gpgsign=false", "commit", "--allow-empty", "-q", "-m", "after 2.6.0"]);
    signedTag(fixture, releaseKey);
    lightweightTag(fixture, "v9.9.7");
    const refs = () => git(fixture, ["for-each-ref", "--format=%(refname) %(objectname) %(objecttype)"]);
    const frozenObject = () => git(fixture, ["cat-file", "tag", FROZEN_TAG]);
    const refsBefore = refs();
    const frozenBefore = frozenObject();
    const noticePath = verifiedNotice(fixture);

    const frozenCommit = git(fixture, ["rev-parse", `${FROZEN_TAG}^{commit}`]).trim();
    for (const tag of [FROZEN_TAG, TAG, "v9.9.7", "v0.0.0-absent"]) {
      evaluate(fixture, { ...trustedConfig(), tag, noticePath });
      evaluate(fixture, { ...trustedConfig(), tag, dispatchedCommit: frozenCommit, noticePath });
      evaluate(fixture, { allowedSigners: undefined, signerFingerprints: undefined, dispatchedCommit: undefined, tag, noticePath });
    }
    const cli = spawnSync(process.execPath, [POLICY_SCRIPT, "--tag", FROZEN_TAG, "--sha", head(fixture)], {
      cwd: fixture.repo,
      env: { ...fixture.env, RELEASE_ALLOWED_SIGNERS: releaseKey.allowedSignersLine, RELEASE_SIGNER_FINGERPRINTS: releaseKey.fingerprint },
      encoding: "utf8",
    });

    expect(cli.status).toBe(1);
    expect(refs()).toBe(refsBefore);
    expect(frozenObject()).toBe(frozenBefore);
    expect(refsBefore.split("\n").filter((line) => line.startsWith("refs/tags/")).length).toBe(3);
  });
});

describe.skipIf(IS_WINDOWS)("real repository — rights attested, so NOTICE.md no longer blocks publication", () => {
  test.skipIf(!hasSshKeygen)("every row of the repository NOTICE.md records verified redistribution rights", () => {
    const fixture = newFixture();
    signedTag(fixture, releaseKey);
    // The refusal path is covered by the fixtures above; this asserts the checkout we
    // ship from has no row left unresolved, which is what the owner attested.
    expect(evaluate(fixture, { ...trustedConfig(), noticePath: join(REPO, "NOTICE.md") })).toEqual({
      allowed: true,
      refusals: [],
    });
  });
});

type Step = { uses?: string; run?: string; with?: Record<string, unknown>; env?: Record<string, unknown> };
type Job = { needs?: string | string[]; env?: Record<string, unknown>; steps?: Step[] };

describe("release.yml — the policy job gates every publication channel", () => {
  const jobs = (Bun.YAML.parse(readFileSync(join(REPO, ".github/workflows/release.yml"), "utf8")) as { jobs?: Record<string, Job> }).jobs ?? {};
  const commandLines = (step: Step) =>
    (step.run ?? "").split("\n").map((line) => line.trim()).filter((line) => line !== "" && !line.startsWith("#"));
  const needsOf = (name: string): string[] => {
    const needs = jobs[name]?.needs;
    if (needs === undefined) return [];
    return Array.isArray(needs) ? needs : [needs];
  };
  const transitiveNeeds = (name: string): Set<string> => {
    const seen = new Set<string>();
    const pending = [...needsOf(name)];
    for (let next = pending.pop(); next !== undefined; next = pending.pop()) {
      if (seen.has(next)) continue;
      seen.add(next);
      pending.push(...needsOf(next));
    }
    return seen;
  };
  const POLICY_COMMAND = /^bun scripts\/release-policy\.ts --tag "\$TAG" --sha "\$GITHUB_SHA"$/;
  const PUBLICATION = /\bnpm publish\b|\bgh release (create|upload|edit|delete)\b|\bgh api\b.*\breleases\b/;

  test("a policy job runs scripts/release-policy.ts with the tag, the dispatched SHA and the owner's repository variables", () => {
    const steps = jobs["policy"]?.steps ?? [];
    const policyIndex = steps.findIndex((step) => commandLines(step).some((line) => POLICY_COMMAND.test(line)));
    expect(policyIndex).toBeGreaterThanOrEqual(0);
    const policyStep = steps[policyIndex] ?? {};
    const env = { ...jobs["policy"]?.env, ...policyStep.env };
    expect({ tag: env["TAG"], signers: env["RELEASE_ALLOWED_SIGNERS"], fingerprints: env["RELEASE_SIGNER_FINGERPRINTS"] }).toEqual({
      tag: "${{ steps.flags.outputs.tag }}",
      signers: "${{ vars.RELEASE_ALLOWED_SIGNERS }}",
      fingerprints: "${{ vars.RELEASE_SIGNER_FINGERPRINTS }}",
    });
  });

  test("the policy job checks out the dispatched SHA with its tags before the policy runs", () => {
    const steps = jobs["policy"]?.steps ?? [];
    const checkouts = steps.filter((step) => step.uses?.startsWith("actions/checkout@"));
    expect(checkouts.length).toBe(1);
    expect(checkouts[0]?.with?.["ref"]).toBe("${{ github.sha }}");
    const fetchesTags = (step: Step) =>
      (step.uses?.startsWith("actions/checkout@") === true && step.with?.["fetch-tags"] === true) ||
      commandLines(step).some((line) => /^git fetch\b.*(--tags\b|refs\/tags\/)/.test(line));
    const fetchIndex = steps.findIndex(fetchesTags);
    const policyIndex = steps.findIndex((step) => commandLines(step).some((line) => POLICY_COMMAND.test(line)));
    expect(fetchIndex).toBeGreaterThanOrEqual(0);
    expect(fetchIndex).toBeLessThan(policyIndex);
  });

  test("publish, and every job that mutates npm or GitHub releases, needs the policy job", () => {
    expect(transitiveNeeds("publish").has("policy")).toBe(true);
    const publishing = Object.entries(jobs)
      .filter(([, job]) => (job.steps ?? []).some((step) => commandLines(step).some((line) => PUBLICATION.test(line))))
      .map(([name]) => name);
    expect(publishing).toContain("publish");
    expect(publishing.filter((name) => !transitiveNeeds(name).has("policy"))).toEqual([]);
  });
});

describe("C5 — README.md states the guard boundary", () => {
  const paragraphs = readFileSync(join(REPO, "README.md"), "utf8")
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.replace(/\s+/g, " "));
  const paragraphWith = (...patterns: RegExp[]) => paragraphs.find((paragraph) => patterns.every((pattern) => pattern.test(paragraph)));

  test("the Copilot CLI adapter can fail open", () => {
    expect(paragraphWith(/copilot cli/i, /fail(s)? open/i)).toBeDefined();
  });

  test("command guards do not sandbox opaque programs or scripts prepared in earlier calls", () => {
    expect(paragraphWith(/does not sandbox|do not sandbox|not a sandbox/i, /opaque program/i, /earlier (call|command|tool call)s?/i)).toBeDefined();
  });

  test("OS-level isolation is recommended for untrusted code", () => {
    expect(paragraphWith(/OS-level isolation/i, /container|virtual machine|\bVM\b|sandbox/i, /untrusted/i)).toBeDefined();
  });
});
