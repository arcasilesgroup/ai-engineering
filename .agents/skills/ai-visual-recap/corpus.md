# Corpus: ai-visual-recap

Turns a finished work unit into the record a reviewer reads before the raw diff: one page
whose file-tree and excerpts come from `git diff` itself, narrative grounded in files the
range touches, handed over as a `file://` link beside the spec digest it carries.

## Routes here

- "recap this PR before I review the diff" — the plain trigger: a finished range that needs its shape before its lines.
- "the build is done, what did it actually change" — the page's file list equals `git diff --name-status`, so the answer is the diff's structure plus why.
- "make a visual summary of everything we did on this branch" — scope is the whole work unit, not the last fix, and the base is where the unit starts.
- "the tests and the record changes too, not just the code" — yes: the recap covers implementation, tests and record in one range.
- "is this change correct" — use /ai-review, which attacks the diff; a recap shows what is there and never judges it.
- "recap the plan before we build it" — use /ai-visual-plan, which reads a plan forwards; this reads a diff backwards.
- "write the changelog entry" — use /ai-ship, which owns the changelog; the recap page is a review surface, not the release note.

## Refuses

- "summarize what the other agent said it did" — refused: the page is derived from `git diff`, and a narrative that cites no file the range touches is the fabrication this command exists to catch.
- "every change gets a recap page" — refused under the tab floor: a one-file fix reviews faster as a plain diff plus one sentence.
- "pad the excerpts so the page looks thorough" — the budgets in `policy/visual-pages.md` are a cost ceiling, and if that file is missing the recap refuses to author until it is restored; a recap that dumps is a recap the reviewer scrolls past.
- "the diff has a secret in it, redact it on the page" — the redactor runs, but the fix is the hunk: a secret in a committed range is a rotated credential, not a formatting problem.
