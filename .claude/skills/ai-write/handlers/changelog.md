# Handler: changelog

Generate changelogs and release notes from conventional commits.

## Process

1. **Identify scope** -- determine range:
   - Between tags: `git log v1.0.0..v2.0.0 --oneline`.
   - Since last release: `git log $(git describe --tags --abbrev=0)..HEAD --oneline`.
   - Time-based: `git log --since="2 weeks ago" --oneline`.

2. **Collect material** -- for each commit/PR: message, changed files, linked issues.

3. **Classify impact**:
   - User-visible: behavior change, new capability, bug fix.
   - Internal: refactoring, tests, CI (exclude from changelog).
   - Breaking: API change, feature removal (requires migration guide).
   - Security: vulnerability fix (include CVE, impact, affected versions).

4. **Map to categories** (Keep a Changelog):
   - **Added**: new capability users could not do before.
   - **Changed**: existing capability improved or different.
   - **Deprecated**: still works, include removal timeline.
   - **Removed**: previously available, now gone.
   - **Fixed**: was broken, now works.
   - **Security**: vulnerability fix with CVE reference.

5. **Transform language** -- user-facing, not technical:
   ```
   Bad:  "Refactored ReportExporter to support pagination"
   Good: "Reports now load 3x faster when filtering large datasets"
   ```
   Rules: start with "You can now..." / "Fixed an issue where...", present tense, no internal references.

6. **Format CHANGELOG.md** -- entries in `[Unreleased]` section. For releases: rename to `[X.Y.Z] - YYYY-MM-DD`, add comparison links.

7. **Quality check** -- reject: "various bug fixes", "updated dependencies" without impact, internal jargon, missing dates, buried breaking changes.

## Output

- CHANGELOG.md entries in Keep a Changelog format.
- Optional: GitHub Release Notes with highlights, upgrade guide, contributors.
