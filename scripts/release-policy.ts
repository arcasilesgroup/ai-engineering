// Release policy: nothing is published unless the release tag already exists, names the
// dispatched commit, is an annotated tag SSH-signed by a key the owner allowlisted
// (RELEASE_ALLOWED_SIGNERS) whose fingerprint is listed (RELEASE_SIGNER_FINGERPRINTS), and
// every bundled-content row in NOTICE.md records verified redistribution rights. Every
// refusal is reported together. The policy only reads: it never creates, moves or deletes
// a tag.
//
// Usage: bun scripts/release-policy.ts --tag <tag> [--sha <commit>]
//        (--sha defaults to GITHUB_SHA; reads NOTICE.md from the cwd)
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { devNull, tmpdir } from "node:os";
import { join } from "node:path";
import { parseArgs } from "node:util";

export type PolicyInput = {
  repoRoot: string;
  tag: string;
  /** The commit the release was dispatched for; the tag must name exactly this commit. */
  dispatchedCommit: string | undefined;
  allowedSigners: string | undefined;
  signerFingerprints: string | undefined;
  noticePath: string;
};
export type PolicyResult = { allowed: boolean; refusals: string[] };

const FINGERPRINT = /^SHA256:[A-Za-z0-9+/]{43}$/;
const SIGNATURE_BLOCK = /^-----BEGIN (SSH SIGNATURE|PGP SIGNATURE|PGP MESSAGE|SIGNED MESSAGE)-----$/m;
const FULL_COMMIT = /^(?:[0-9a-f]{40}|[0-9a-f]{64})$/;
const USAGE = "usage: bun scripts/release-policy.ts --tag <tag> [--sha <commit>]   (--sha defaults to GITHUB_SHA)";

/** Fingerprints the owner listed, or the refusals explaining why the list cannot be trusted.
 *  `undefined` fingerprints means the configuration refused and the signer cannot be matched. */
function parseFingerprints(raw: string | undefined): { fingerprints?: string[]; refusals: string[] } {
  const entries = (raw ?? "").split(/[,\n]/).map((entry) => entry.trim()).filter((entry) => entry !== "");
  if (entries.length === 0) {
    return {
      refusals: [
        "RELEASE_SIGNER_FINGERPRINTS is not set: an owner must list the release key's SHA256 fingerprint as a repository variable before publishing.",
      ],
    };
  }
  const malformed = entries.filter((entry) => !FINGERPRINT.test(entry));
  if (malformed.length > 0) {
    return {
      refusals: malformed.map(
        (entry) =>
          `RELEASE_SIGNER_FINGERPRINTS entry "${entry}" is not a SHA256:<43 base64 characters> fingerprint: replace it with the fingerprint printed by ssh-keygen -lf <key>.pub.`,
      ),
    };
  }
  return { fingerprints: entries, refusals: [] };
}

/** Git with no user, global or system configuration and no inherited repository location:
 *  only the repository at `repoRoot` and the `-c` values given here decide the answer. */
function git(repoRoot: string, args: string[]) {
  const env: NodeJS.ProcessEnv = { ...process.env, GIT_CONFIG_GLOBAL: devNull, GIT_CONFIG_NOSYSTEM: "1" };
  for (const name of ["GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_CONFIG", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT"]) {
    delete env[name];
  }
  return spawnSync("git", ["-C", repoRoot, ...args], { env, encoding: "utf8" });
}

/** The signer's fingerprint when the tag's signature verifies against the allowed signers,
 *  otherwise undefined. The allowed signers live in a private temporary file for this call. */
function verifiedSigner(repoRoot: string, tag: string, allowedSigners: string): string | undefined {
  const scratch = mkdtempSync(join(tmpdir(), "release-policy-"));
  try {
    const signersFile = join(scratch, "allowed_signers");
    writeFileSync(signersFile, allowedSigners.endsWith("\n") ? allowedSigners : `${allowedSigners}\n`, { mode: 0o600 });
    const result = git(repoRoot, [
      "-c", `gpg.ssh.allowedSignersFile=${signersFile}`,
      "-c", "gpg.ssh.program=ssh-keygen",
      "verify-tag", "--raw", `refs/tags/${tag}`,
    ]);
    if (result.status !== 0) return undefined;
    return /^Good "git" signature for .+ with \S+ key (SHA256:[A-Za-z0-9+/]{43})$/m.exec(result.stderr)?.[1];
  } finally {
    rmSync(scratch, { recursive: true, force: true });
  }
}

/** The commit the run releases, or the refusal explaining why it cannot be compared. */
function dispatchedCommitRefusals(dispatchedCommit: string | undefined): string[] {
  const dispatched = (dispatchedCommit ?? "").trim();
  if (dispatched === "") {
    return ['The dispatched commit is unknown: pass --sha <commit> (the workflow passes "$GITHUB_SHA") so the policy can prove the tag names it.'];
  }
  if (FULL_COMMIT.test(dispatched)) return [];
  return [`--sha ${dispatched} is not a full lowercase commit SHA: pass the dispatched commit as git rev-parse prints it.`];
}

/** A signed tag on any other commit vouches for a revision this run does not ship. An
 *  unknown or malformed dispatched commit is refused once, by dispatchedCommitRefusals. */
function commitMismatchRefusals(input: PolicyInput): string[] {
  const { repoRoot, tag } = input;
  const dispatched = (input.dispatchedCommit ?? "").trim();
  if (dispatchedCommitRefusals(dispatched).length > 0) return [];
  const tagged = git(repoRoot, ["rev-parse", "--verify", "--quiet", `refs/tags/${tag}^{commit}`]);
  const taggedCommit = tagged.stdout.trim();
  if (tagged.status !== 0 || taggedCommit === "") {
    return [`Tag ${tag} does not name a commit: sign the tag on the commit you dispatch.`];
  }
  if (taggedCommit === dispatched) return [];
  return [`Tag ${tag} points at ${taggedCommit}, not the dispatched commit ${dispatched}: sign the tag on the commit you dispatch.`];
}

function tagRefusals(input: PolicyInput, fingerprints: string[] | undefined): string[] {
  const { repoRoot, tag } = input;
  const objectType = git(repoRoot, ["cat-file", "-t", `refs/tags/${tag}`]);
  if (objectType.status !== 0) {
    return [`Tag ${tag} does not exist: the release owner must push a signed annotated tag (git tag -s) before publishing.`];
  }
  return [...signatureRefusals(input, fingerprints, objectType.stdout.trim()), ...commitMismatchRefusals(input)];
}

function signatureRefusals(input: PolicyInput, fingerprints: string[] | undefined, objectType: string): string[] {
  const { repoRoot, tag } = input;
  if (objectType !== "tag") {
    return [`Tag ${tag} is lightweight: release from a new version whose tag is signed and annotated (git tag -s); never move an existing tag.`];
  }
  const tagObject = git(repoRoot, ["cat-file", "tag", `refs/tags/${tag}`]);
  if (tagObject.status !== 0 || !SIGNATURE_BLOCK.test(tagObject.stdout)) {
    return [
      `Tag ${tag} is annotated but unsigned: release from a new version whose tag is signed with an allowlisted SSH key (git tag -s); never move an existing tag.`,
    ];
  }
  const allowedSigners = input.allowedSigners ?? "";
  if (allowedSigners.trim() === "") return [];
  const signer = verifiedSigner(repoRoot, tag, allowedSigners);
  if (signer === undefined) {
    return [`Tag ${tag} has a signature that does not verify against RELEASE_ALLOWED_SIGNERS: sign with an allowlisted key, or have an owner update the variable.`];
  }
  if (fingerprints === undefined || fingerprints.includes(signer)) return [];
  return [
    `Tag ${tag} is signed by ${signer}, which is not in RELEASE_SIGNER_FINGERPRINTS: an owner must allowlist that fingerprint, or the tag must be signed by an allowlisted key.`,
  ];
}

function tableCells(line: string): string[] | undefined {
  const trimmed = line.trim();
  if (!trimmed.startsWith("|")) return undefined;
  return trimmed.replace(/^\|/, "").replace(/\|$/, "").split("|").map((cell) => cell.trim());
}

/** One refusal per bundled-content row of NOTICE.md's attribution table (the table whose
 *  first header cell is `Skill`) that lacks verified redistribution rights. */
function noticeRefusals(noticePath: string): string[] {
  let lines: string[];
  try {
    lines = readFileSync(noticePath, "utf8").split("\n");
  } catch {
    return [`NOTICE.md could not be read at ${noticePath}: restore it before publishing.`];
  }
  const headerIndex = lines.findIndex((line) => tableCells(line)?.[0] === "Skill");
  const header = tableCells(lines[headerIndex] ?? "") ?? [];
  const column = header.indexOf("Redistribution");
  if (column < 0) {
    return ["NOTICE.md has no Redistribution column in its attribution table: add one and record verified or unresolved (<reason>) for every row."];
  }
  const refusals: string[] = [];
  let rowCount = 0;
  // headerIndex + 1 is the |---| separator; rows run until the first non-table line.
  for (let index = headerIndex + 2; index < lines.length; index += 1) {
    const cells = tableCells(lines[index] ?? "");
    if (cells === undefined) break;
    rowCount += 1;
    const content = cells[0] ?? "";
    const rights = cells[column] ?? "";
    const reason = /^unresolved \((.*\S.*)\)$/.exec(rights)?.[1];
    if (cells.length !== header.length || content === "" || (rights !== "verified" && reason === undefined)) {
      refusals.push(
        `NOTICE.md line ${index + 1} is not a parseable attribution row: give it every column and a Redistribution value of verified or unresolved (<reason>).`,
      );
    } else if (reason !== undefined) {
      refusals.push(`${content} redistribution rights are unresolved (${reason}): an owner must verify them and mark the row verified in NOTICE.md.`);
    }
  }
  if (rowCount === 0) return ["NOTICE.md lists no bundled content in its attribution table: restore the attribution rows before publishing."];
  return refusals;
}

export function evaluateReleasePolicy(input: PolicyInput): PolicyResult {
  const refusals: string[] = [];
  if ((input.allowedSigners ?? "").trim() === "") {
    refusals.push(
      "RELEASE_ALLOWED_SIGNERS is not set: an owner must add the release key's allowed_signers line as a repository variable before publishing.",
    );
  }
  const { fingerprints, refusals: fingerprintRefusals } = parseFingerprints(input.signerFingerprints);
  refusals.push(
    ...fingerprintRefusals,
    ...dispatchedCommitRefusals(input.dispatchedCommit),
    ...tagRefusals(input, fingerprints),
    ...noticeRefusals(input.noticePath),
  );
  return { allowed: refusals.length === 0, refusals };
}

function parseCli(argv: string[]): { tag: string; sha: string | undefined } | undefined {
  try {
    const { values, positionals } = parseArgs({
      args: argv,
      options: { tag: { type: "string" }, sha: { type: "string" } },
      allowPositionals: true,
      strict: true,
    });
    if (positionals.length > 0 || values.tag === undefined || values.tag.trim() === "") return undefined;
    return { tag: values.tag, sha: values.sha };
  } catch {
    return undefined;
  }
}

if (import.meta.main) {
  const cli = parseCli(process.argv.slice(2));
  if (cli === undefined) {
    process.stderr.write(`${USAGE}\n`);
    process.exit(1);
  }
  const { refusals } = evaluateReleasePolicy({
    repoRoot: process.cwd(),
    tag: cli.tag,
    dispatchedCommit: cli.sha ?? process.env["GITHUB_SHA"],
    allowedSigners: process.env["RELEASE_ALLOWED_SIGNERS"],
    signerFingerprints: process.env["RELEASE_SIGNER_FINGERPRINTS"],
    noticePath: join(process.cwd(), "NOTICE.md"),
  });
  if (refusals.length > 0) {
    process.stderr.write(`${refusals.join("\n")}\n`);
    process.exit(1);
  }
}
