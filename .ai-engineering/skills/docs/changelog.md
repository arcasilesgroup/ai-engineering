# Changelog Documentation

## Purpose

Transform technical git history into polished, user-friendly documentation that customers and developers actually understand. Produces two outputs: a structured CHANGELOG.md following Keep a Changelog format, and GitHub Release Notes with highlights, upgrade guides, and contributor acknowledgments. Emphasizes user-facing language — write what users can DO, not what you BUILT.

## Trigger

- Command: agent invokes changelog skill or user requests changelog/release notes generation.
- Context: preparing a release, documenting recent changes, writing app store update descriptions, creating customer-facing product updates, transitioning `[Unreleased]` to a versioned release.

## Procedure

### Phase 1: Gather Changes

1. **Identify scope** — determine the range of changes to document.
   - Between two tags: `git log v1.0.0..v2.0.0 --oneline`.
   - Since last release: `git log $(git describe --tags --abbrev=0)..HEAD --oneline`.
   - Time-based: `git log --since="2 weeks ago" --oneline`.
   - If active spec exists, cross-reference `specs/<active>/tasks.md` for completed work.

2. **Collect raw material** — for each commit/PR, gather:
   - Commit message (may follow `spec-NNN: Task X.Y — <description>` format).
   - PR title and description (richer context than commit messages).
   - Changed files and diff summary (`git diff --stat`).
   - Linked issues or specs.

3. **Assess impact** — classify each change by user impact:
   - **User-visible**: changes behavior, adds capability, fixes a bug users experience.
   - **Internal**: refactoring, test improvements, CI changes, dependency bumps.
   - **Breaking**: changes API, removes features, requires migration.
   - **Security**: fixes vulnerabilities, updates vulnerable dependencies.

### Phase 2: Categorize

4. **Map to Keep a Changelog categories** — assign each user-visible change to exactly one category:

   | Category       | Rule                                                    | Example                                           |
   |---------------|---------------------------------------------------------|---------------------------------------------------|
   | **Added**      | Users couldn't do this before at all                    | "You can now export reports in bulk"              |
   | **Changed**    | Existing capability is now better, faster, or different | "Dashboard loads 3× faster on large datasets"     |
   | **Deprecated** | Still works, but will be removed — include timeline     | "REST API v1 will be removed in v3.0.0"           |
   | **Removed**    | Previously available, now gone                          | "Removed support for Python 3.9"                  |
   | **Fixed**      | Was broken, now works correctly                         | "Fixed an issue where CSV exports had missing columns" |
   | **Security**   | Vulnerability fix — include CVE, impact, affected versions | "Fixed SQL injection in search (CVE-2025-12346)" |

5. **Filter noise** — exclude from the changelog:
   - Internal refactoring with no behavior change.
   - Test additions/modifications (unless fixing a user-reported bug).
   - CI/CD pipeline changes.
   - Code style/formatting changes.
   - Dependency bumps with no user-visible impact (unless security-related).
   - Merge commits and branch housekeeping.

### Phase 3: Transform to User-Facing Language

6. **Rewrite entries** — convert technical commit messages to user-facing language:

   ```
   ❌ Technical (don't):
   "Implemented batch processing queue for the export service"
   "Refactored ReportExporter class to support pagination"
   "Fixed bug in CSV serialization (PR #4521)"
   "Various bug fixes and improvements"
   "Updated dependencies"

   ✅ User-facing (do):
   "You can now export up to 10,000 rows at once from any report"
   "Reports now load 3× faster when filtering large datasets"
   "Fixed an issue where exported CSV files had missing columns"
   ```

7. **Apply language rules**:
   - Start with "You can now..." / "X now..." / "Fixed an issue where..." / "Added support for...".
   - Include the benefit, not just the mechanism.
   - Use present tense.
   - Strip internal references (PR numbers, file paths, branch names) — unless linking to issues.
   - One changelog entry may represent many commits — group related work.
   - Don't say "Updated X" without saying how — was it improved or fixed?

### Phase 4: Format CHANGELOG.md

8. **Write entries in `[Unreleased]`** — add entries to the appropriate category section:

   ```markdown
   ## [Unreleased]

   ### Added
   - Changelog documentation skill for generating user-friendly changelogs and release notes.

   ### Fixed
   - Fixed an issue where exported CSV files had missing column headers.
   ```

9. **Handle version transitions** — when cutting a release:
   - Rename `[Unreleased]` to `[X.Y.Z] - YYYY-MM-DD`.
   - Create a new empty `[Unreleased]` section above it.
   - Add comparison links in the footer:
     ```markdown
     [Unreleased]: https://github.com/owner/repo/compare/vX.Y.Z...HEAD
     [X.Y.Z]: https://github.com/owner/repo/compare/vPREVIOUS...vX.Y.Z
     ```
   - Version number follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html):
     - MAJOR: breaking changes.
     - MINOR: new features (backwards-compatible).
     - PATCH: bug fixes.

### Phase 5: Format Release Notes (Optional)

10. **Produce GitHub Release Notes** — a standalone document for the GitHub release page:

    ```markdown
    # Release vX.Y.Z

    **Release Date:** YYYY-MM-DD

    ## Highlights

    - **Feature Name** — 1-2 sentence user-facing summary.

    ## What's New

    ### Feature Name
    Description of what users can now do and how.

    ## Improvements

    - Concise improvement entries.

    ## Bug Fixes

    - Fixed an issue where...

    ## Breaking Changes

    ### ⚠️ Change Title
    **What changed:** Description.
    **What you need to do:** Migration steps.
    **Timeline:** Deprecation → removal dates.

    ## Security Updates

    - **SEVERITY**: Description (CVE-YYYY-NNNNN)
      - Impact: ...
      - Affected versions: ...
      - Action: Upgrade immediately.

    ## Upgrade Guide

    Steps to upgrade from the previous version.

    ## Contributors

    Thanks to @contributor1, @contributor2.

    **Full Changelog**: https://github.com/owner/repo/compare/vPREVIOUS...vX.Y.Z
    ```

### Phase 6: Quality Check

11. **Validate against anti-patterns** — reject entries that match:
    - "Various bug fixes and improvements" — list specific fixes or omit.
    - "Updated dependencies" without stating user impact.
    - "Updated X" without explaining how (improved? fixed? changed?).
    - Internal jargon (class names, module paths, PR numbers in prose).
    - Missing dates on releases.
    - Breaking changes buried in the middle — must be prominent with `⚠️`.
    - Security entries without CVE references, impact level, or affected versions.
    - Vague language ("improved performance" without metrics or context).

12. **Cross-check completeness**:
    - Every user-visible change from the git range is represented.
    - Breaking changes have migration guidance.
    - Deprecated features include removal timeline.
    - Security entries include severity, affected versions, and required action.
    - Categories are mutually exclusive — each entry appears in exactly one.

## Output Contract

- **CHANGELOG.md entries**: new entries in `[Unreleased]` (or versioned section) following Keep a Changelog format.
- **Release Notes** (when requested): standalone GitHub Release Notes document with highlights, upgrade guide, breaking changes, and contributors.
- **Quality check results**: list of anti-patterns checked with pass/fail status.

## Governance Notes

- CHANGELOG.md follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format — no exceptions.
- Version numbers follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
- Breaking changes must be documented prominently — never buried in a list.
- Security entries must reference CVEs where applicable and include impact assessment.
- Changelog updates go through PR — never direct commit to protected branches.
- Internal-only changes (refactoring, tests, CI) are excluded from the changelog unless they affect user behavior.
- Don't manually edit auto-generated tool output without review — generated changelogs are a starting point, not final output.
- Each entry must be user-facing: benefit-first, present tense, no internal references.

## References

- `standards/framework/core.md` — governance structure and non-negotiables.
- `context/product/framework-contract.md` — release model and versioning.
- `skills/workflows/pr.md` — PR workflow (changelog updates go through PRs).
- `skills/review/security.md` — security entry format and CVE handling.
- `skills/dev/migration.md` — breaking changes documentation requirements.
