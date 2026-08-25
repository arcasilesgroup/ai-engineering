"""Tests for spec 033 / B-033-2: the skillify extractor.

A costly one-off session becomes a SKILL.md skeleton that passes the contract: name,
description with a Not-for clause, the craft sections (spec 032) and a Procedure derived
from the generalisable steps, with the user's corrections as Rules. It names steps, never
the chat; a transcript with no generalisable steps emits nothing (cc-creators' skillify).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_engineering import contract, skillify  # noqa: E402

PROCEDURE_TRANSCRIPT = """User: we keep losing time migrating this config. Can you work out the
process so we can repeat it?
Assistant: Let's see. The steps are: read the old config keys, map them to the new names,
write a migration script, verify the diff.
User: yes, and never overwrite the original file. Keep a .bak.
"""

CHAT_ONLY = """User: hi
Assistant: hello, how can I help?
User: thanks
Assistant: bye
"""


def test_extract_emits_a_contract_clean_skeleton(tmp_path):
    skeleton = skillify.extract(PROCEDURE_TRANSCRIPT)
    assert skeleton is not None
    path = tmp_path / "ai-migrator" / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    (path.parent / "corpus.md").write_text(
        "# Corpus\n\n## Routes here\n\n- migrate config — taken\n\n"
        "## Refuses\n\n- other work — use /ai-other\n",
        encoding="utf-8",
    )
    path.write_text(skeleton, encoding="utf-8")
    problems = contract.audit_one(path)
    assert not problems, "\n".join(problems)


def test_extract_names_steps_not_chat():
    skeleton = skillify.extract(PROCEDURE_TRANSCRIPT) or ""
    assert "read the old config keys" in skeleton  # a step from the procedure
    assert "hello, how can I help" not in skeleton  # never the chat
    assert ".bak" in skeleton  # the user's correction became a rule


def test_extract_with_no_process_emits_nothing():
    assert skillify.extract(CHAT_ONLY) is None