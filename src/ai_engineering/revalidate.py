"""Finding-granular revalidation, spec 030 / B-030-3.

After a correction, re-reads the specific file's diff and marks a finding `fixed` only when
the change actually removed the trigger, without re-running the whole lane (deepsec's
`revalidate`). A touched file whose diff keeps the trigger is INCOMPLETE, never silently
fixed; a finding whose trigger was never in the before-bytes is INCOMPLETE too — a `fixed`
that nothing was there to fix is the same false green.
"""

from __future__ import annotations

from typing import Any


def apply(finding: dict[str, Any], before: str, after: str) -> bool:
    """True when the diff removed the finding's trigger; False (INCOMPLETE) otherwise.

    `finding["trigger"]` is the exact substring the original scan flagged. `before` and
    `after` are the file's bytes at the two ends of the correction's diff.
    """
    trigger = finding.get("trigger", "")
    if not trigger:
        return False
    if trigger not in before:
        # The trigger was never there: nothing was fixed, and claiming so is a false green.
        return False
    return trigger not in after
