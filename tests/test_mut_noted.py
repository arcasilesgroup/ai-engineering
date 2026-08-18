"""A pass that can say what it observed, and the three ways it must not lie.

`EP-290` asks that the framework write only into the homes it declares *and that the count be
published*. The refusal half has always executed. The count half could not exist: a check
returned `None` for a pass and a string for the problem, so a check that inventoried 257
files and found every one correctly homed said exactly what a check that inventoried nothing
said. Two very different facts, one silence.

`Noted` is the channel. What these cases hold is that it stays a *pass* — the danger of a
truthy string in a contract where truthy means failure is that the fix publishes a number by
turning a green check red, and that would be discovered by whoever runs `doctor` next rather
than here.
"""

from __future__ import annotations

from ai_engineering import doctor


def test_a_noted_is_a_string_so_every_existing_reader_keeps_working():
    """The reason it is a subclass and not a new type. Twenty-odd checks return `str | None`
    and the renderer, the envelope and the tests all read it as text; a wrapper class would
    have meant touching every one of them to publish one number."""

    noted = doctor.Noted("nineteen files")

    assert isinstance(noted, str)
    assert str(noted) == "nineteen files"
    assert noted == "nineteen files"


def test_a_noted_is_distinguishable_from_the_problem_it_is_the_opposite_of():
    """The whole contract in one line. Both are non-empty strings and they mean opposite
    things, so the only thing separating a published observation from a reported failure is
    this test being true."""

    assert isinstance(doctor.Noted("all homed"), doctor.Noted)
    assert not isinstance("a stray in .ai-engineering/", doctor.Noted)


def test_the_homes_assertion_publishes_its_count_on_a_pass(tmp_path, monkeypatch):
    """`EP-290`'s own sentence, executed. The number has to come from the inventory rather
    than from a constant, because a published count that is written down somewhere is the
    two-homes-for-one-number defect this repository keeps finding in itself."""

    monkeypatch.setattr(doctor, "tracked_files", lambda root: [".ai/intent.md", "src/one.py"])
    monkeypatch.setattr(
        doctor, "intent_homes", lambda files: [f for f in files if f.endswith("intent.md")]
    )
    home = tmp_path / ".ai"
    home.mkdir()
    (home / "intent.md").write_text("x", encoding="utf-8")

    class _Valid:
        outcome = "PASS"

    monkeypatch.setattr(
        "ai_engineering.intent.validate", lambda source, root: _Valid(), raising=False
    )

    answer = doctor.data_is_yours(tmp_path)

    assert isinstance(answer, doctor.Noted), "a pass with a count must not read as a failure"
    assert "2 tracked files inventoried" in answer
    assert "1 Intent home," in answer, "singular, because one home is one home"


def test_a_stray_still_fails_and_is_not_wrapped(tmp_path, monkeypatch):
    """The control. Publishing a number on the pass is worthless if it also softened the
    refusal, and a `Noted` returned on a real problem would be a failure rendered as a pass —
    a false green produced by the mechanism built to prevent one."""

    monkeypatch.setattr(doctor, "tracked_files", lambda root: [".ai-engineering/scripts/thing.py"])

    answer = doctor.data_is_yours(tmp_path)

    assert answer is not None
    assert not isinstance(answer, doctor.Noted)
    assert "outside" in answer
