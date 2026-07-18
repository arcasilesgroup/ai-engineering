"""spec-187 W1 (T-1) — canonical token-baseline counter.

A thin, re-runnable tiktoken (cl100k_base) counter over the CANONICAL
surface only, producing a labelled JSON snapshot that later waves diff
against to prove the >=25% reduction target (D-187-02).
"""

from __future__ import annotations
