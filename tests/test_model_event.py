"""Executable contracts for spec 042 / B-042-1 and B-042-2: the model event field.

`_emit` records `model` from `AI_ENG_MODEL` (honestly `undetermined` when a surface does
not set it), and the command event carries `tier_model` — the model string the pin's
[models] tiers say the verb routes to (B-042-1). The two fields are different facts: what
the surface reported, and what the pin says the verb should run on.
"""

from __future__ import annotations

import contextlib
import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

from ai_engineering import paths

ROOT = Path(__file__).resolve().parents[1]


def _last_buffered(repodir: Path) -> dict:
    lines = (repodir / ".ai" / "events.jsonl").read_text(encoding="utf-8").strip().splitlines()
    return json.loads(lines[-1])


def _emit_model(tmp_path, monkeypatch, env_model: str | None):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "--quiet", "-b", "main"], cwd=root, check=True)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "r",
        "GIT_AUTHOR_EMAIL": "r@x",
        "GIT_COMMITTER_NAME": "r",
        "GIT_COMMITTER_EMAIL": "r@x",
    }
    subprocess.run(
        ["git", "commit", "--quiet", "--allow-empty", "-m", "base"], cwd=root, check=True, env=env
    )
    # The buffer exists only where a pin exists (buffer_path checks .ai/config.toml);
    # put the real pin's [models] here so the emit path and the tier reading agree.
    (root / ".ai").mkdir(exist_ok=True)
    (root / ".ai" / "config.toml").write_text(
        "[models]\n"
        'top = "deepseek-v4-flash"\n'
        'medium = "qwen3.8-flash"\n'
        'low = "qwen3.6"\n'
        'default_tier = "deepseek-v4-flash"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_ENGINEERING_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("AI_ENG_SESSION", "test-session")
    if env_model is None:
        monkeypatch.delenv("AI_ENG_MODEL", raising=False)
    else:
        monkeypatch.setenv("AI_ENG_MODEL", env_model)
    # The _emit hook resolves the repo by walking up from cwd, not via paths.repo_root;
    # run inside the repo so the hook finds the same buffer we then read.
    monkeypatch.chdir(root)
    paths.load("_emit").emit("audit", "command", verb="audit", exit=0)
    return _last_buffered(root)


def test_emit_records_model_from_ai_eng_model(tmp_path, monkeypatch):
    event = _emit_model(tmp_path, monkeypatch, env_model="nan/deepseek-v4-flash")
    assert event.get("model") == "nan/deepseek-v4-flash"


def test_emit_records_undetermined_when_surface_did_not_say(tmp_path, monkeypatch):
    event = _emit_model(tmp_path, monkeypatch, env_model=None)
    assert event.get("model") == "undetermined"


# ---- B-042-1 : the pin tier, on the command event ----


def test_route_returns_model_strings_not_tier_labels():
    from ai_engineering import model_router as mr

    cfg = {
        "models": {
            "top": "deepseek-v4-flash",
            "medium": "qwen3.8-flash",
            "low": "qwen3.6",
            "default_tier": "deepseek-v4-flash",
        }
    }
    assert mr.route("audit", cfg) == "deepseek-v4-flash"  # top step -> top model
    assert mr.route("report", cfg) == "qwen3.8-flash"  # unmapped verb -> medium
    assert mr.route("spec", cfg) == "qwen3.6"  # low step -> low model


def test_no_pin_and_no_env_reports_nothing_invented():
    from ai_engineering import model_router as mr

    # No models configured: route falls back to the empty string (the session's own model).
    assert mr.route("audit", {}) == ""
    assert mr.route("report", {}) == ""


# ---- B-042-2 : the chain hook passes through a payload model ----


def _run_chain(monkeypatch, tmp_path, body: str):
    monkeypatch.setattr(sys, "argv", ["chain.py", "PostToolUse"])
    monkeypatch.setattr(sys, "stdin", type("S", (), {"read": lambda self: body})())
    monkeypatch.setenv("AI_ENGINEERING_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("AI_ENG_MODEL", raising=False)
    with contextlib.suppress(SystemExit):
        runpy.run_path(str(ROOT / "hooks" / "chain.py"), run_name="__main__")


def test_chain_hook_sets_ai_eng_model_from_a_real_payload_model(tmp_path, monkeypatch):
    """The chain hook exports AI_ENG_MODEL only when the payload actually carries a model
    string — never from sessionId, and never an empty value. Driven by path like every
    hook."""
    body = json.dumps(
        {
            "session_id": "s-1",
            "model": "nan/deepseek-v4-flash",
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
        }
    )
    _run_chain(monkeypatch, tmp_path, body)
    assert os.environ.get("AI_ENG_MODEL") == "nan/deepseek-v4-flash"


# ---- B-042-1 : both cli emit paths record tier_model ----


def test_the_real_cli_records_tier_model_from_the_pin(tmp_path):
    """Running the actual `ai-eng` binary in a repo with a pin puts tier_model on the
    command event — the model string the pin's tiers say the verb routes to, on both the
    plain path and the --json path. The event's `model` stays undetermined (no surface
    env), keeping the two facts separate."""
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "--quiet", "-b", "main"], cwd=root, check=True)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "r",
        "GIT_AUTHOR_EMAIL": "r@x",
        "GIT_COMMITTER_NAME": "r",
        "GIT_COMMITTER_EMAIL": "r@x",
    }
    subprocess.run(
        ["git", "commit", "--quiet", "--allow-empty", "-m", "base"], cwd=root, check=True, env=env
    )
    (root / ".ai").mkdir(exist_ok=True)
    (root / ".ai" / "config.toml").write_text(
        "[models]\n"
        'top = "deepseek-v4-flash"\n'
        'medium = "qwen3.8-flash"\n'
        'low = "qwen3.6"\n'
        'default_tier = "deepseek-v4-flash"\n',
        encoding="utf-8",
    )
    env.pop("AI_ENG_MODEL", None)

    def run(*args) -> dict:
        subprocess.run(
            ["uv", "run", "ai-eng", *args],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        lines = (root / ".ai" / "events.jsonl").read_text(encoding="utf-8").strip().splitlines()
        return json.loads(lines[-1])

    plain = run("--non-interactive", "report", "surfaces")
    assert plain["cls"] == "command"
    assert plain["data"]["verb"] == "report"
    assert plain["data"]["tier_model"] == "qwen3.8-flash"  # report -> medium
    assert plain["model"] == "undetermined"  # no surface env

    json_event = run("--json", "report", "surfaces")
    assert json_event["cls"] == "command"
    assert json_event["data"]["tier_model"] == "qwen3.8-flash"
