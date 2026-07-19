"""spec-190 D-190-01: FrameworkEvent carries an aliased frameworkVersion field.

The model_config is ``populate_by_name`` only, so pydantic's default
``extra="ignore"`` would silently drop an unknown ``frameworkVersion``
envelope key on the pip read path. This test pins the field so the
version stamp round-trips through validate -> dump(by_alias=True).
"""

from __future__ import annotations

from ai_engineering.state.models import FrameworkEvent


def test_framework_version_alias_round_trip() -> None:
    event = FrameworkEvent.model_validate(
        {
            "frameworkVersion": "9.9.9",
            "project": "demo-project",
            "engine": "claude_code",
            "kind": "skill_invoked",
            "outcome": "success",
            "component": "hook.skill",
            "correlationId": "corr-1",
            "detail": {"skill": "ai-brainstorm"},
        }
    )
    dumped = event.model_dump(by_alias=True)
    assert dumped["frameworkVersion"] == "9.9.9"
    assert event.framework_version == "9.9.9"


def test_framework_version_defaults_to_none() -> None:
    event = FrameworkEvent(
        project="demo-project",
        engine="claude_code",
        kind="skill_invoked",
        outcome="success",
        component="hook.skill",
        correlationId="corr-1",
        detail={"skill": "ai-brainstorm"},
    )
    assert event.framework_version is None
