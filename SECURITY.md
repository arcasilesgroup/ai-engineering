# Security

This package runs hooks on every tool call, on your machine. That deserves a way to tell
us when something is wrong with it.

## Reporting

Report privately through GitHub's security advisories on this repository:
**Security → Report a vulnerability**. We acknowledge within 3 working days and aim to
have a fix or a stated position within 14. Please do not open a public issue first.

## Supported versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | yes       |
| 0.13.x  | frozen at its tag; security fixes only until 2027-02-01 |
| < 0.13  | no        |

## What we do on our side

- Releases are published from a tagged workflow using PyPI trusted publishing. No
  long-lived token on anybody's laptop.
- Build attestations are produced with the wheel, so `ai-eng doctor` can verify that the
  running wheel is the one that tag produced.
- Auto-update is off by design. A version change is a committed diff in `.ai/config.toml`,
  reviewed in a pull request, which is the real control against a compromised release.

## What this does not protect against

The framework is a policy layer. It cannot protect you from credentials that already have
every permission on every system reachable from the session. Per-repository tokens and a
database user without superuser rights beat every line of code in this repository. That is
stated in the design, not hidden in it.
