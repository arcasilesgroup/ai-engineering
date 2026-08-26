"""The constellation rule over verdicts, spec 034 / B-034-3.

A cluster of same-class signals in one context reads as systemic failure; a single isolated
signal (or signals of different classes) reads as noise. The module classifies a cluster —
it never erases or downgrades an individual guard's fail (astryx).
"""

from __future__ import annotations


def classify(signals: list[dict]) -> str:
    """Return "systemic" when >=2 same-class signals share a context, else "isolated".

    The input is a list of observed signals, each {"class", "context", ...}. This only
    classifies the cluster; it never modifies a signal — a fail reported stays reported.
    """
    counts: dict[tuple[str, str], int] = {}
    for signal in signals:
        key = (str(signal.get("class", "")), str(signal.get("context", "")))
        counts[key] = counts.get(key, 0) + 1
    if any(count >= 2 for count in counts.values()):
        return "systemic"
    return "isolated"
