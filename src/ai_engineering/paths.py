"""Where everything is, resolved once.

The guards, the policy, the skills and the git hooks ship inside the wheel and stay
there: nothing is ever copied into a user's repository. In a checkout of this repository
they sit at the top level instead, so both layouts resolve here and nowhere else.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

PACKAGE = Path(__file__).resolve().parent
REPO = PACKAGE.parent.parent


def shipped(name: str) -> Path:
    inside = PACKAGE / name
    return inside if inside.exists() else REPO / name


def hooks() -> Path:
    return shipped("hooks")


def git_hooks() -> Path:
    return shipped("git-hooks")


def policy(name: str) -> Path:
    return shipped("policy") / name


def surfaces() -> Path:
    return shipped("surfaces")


def skills() -> Path:
    """The eight, as published. In a checkout they live in the one tree the repository
    itself uses — there is no second copy to keep in sync."""
    inside = PACKAGE / "skills"
    return inside if inside.exists() else REPO / ".agents" / "skills"


def home() -> Path:
    return load("_emit").home()


def load(name: str) -> ModuleType:
    """Import a hook module by path. They are standard-library Python executed by path,
    never `import ai_engineering`, because on the hot path that import is ~110 ms."""
    if str(hooks()) not in sys.path:
        sys.path.insert(0, str(hooks()))
    if name in sys.modules:
        return sys.modules[name]
    source = hooks() / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        # Said out loud rather than raised three lines later as an AttributeError on None.
        # A hook that cannot be loaded is the one case where the reason has to survive.
        raise ImportError(f"no hook module at {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def repo_root(start: Path | None = None) -> Path | None:
    return load("_emit").repo_root(start)
