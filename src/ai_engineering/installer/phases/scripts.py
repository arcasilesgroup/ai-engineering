"""Scripts phase — deploy framework scripts to consumer ``.ai-engineering/scripts/``.

spec-133 D-133-21: every skill referencing
``python .ai-engineering/scripts/<x>.py`` must succeed immediately
post-install. Without this phase the bootstrap session, spec lifecycle,
commit composer, plan-task sync, etc. break on first invocation —
that is B1 highest-ROI fix per the spec brief.

This phase copies the 9 root framework scripts from the template tree
(``templates/.ai-engineering/scripts/``) into the consumer repo's
``.ai-engineering/scripts/`` directory. Idempotent: existing files are
overwritten in ``FRESH`` mode, preserved in ``INSTALL`` mode unless
content drifted.

Hooks subdirectory is OWNED by ``HooksPhase``; this phase does NOT
touch ``.ai-engineering/scripts/hooks/``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from ai_engineering.installer.templates import get_ai_engineering_template_root

from . import InstallContext, InstallMode, PhasePlan, PhaseResult, PhaseVerdict, PlannedAction

# Canonical list of 9 root framework scripts (spec-133 D-133-21).
# Order is alphabetical for stable diffs.
ROOT_SCRIPT_FILES: tuple[str, ...] = (
    "branch_slug.py",
    "commit_compose.py",
    "doc_gate.py",
    "plan_tasks.py",
    "pr_body_compose.py",
    "regenerate-hooks-manifest.py",
    "runtime_rotate.py",
    "session_bootstrap.py",
    "spec_lifecycle.py",
)

_SCRIPTS_REL = ".ai-engineering/scripts"


class ScriptsPhase:
    """Deploy 9 root framework scripts to the consumer's tree.

    Runs before ``HooksPhase`` and after ``DetectPhase`` so the scripts
    that hooks may invoke (e.g. ``runtime_rotate``) are on disk by the
    time hooks are wired.
    """

    @property
    def name(self) -> str:
        return "scripts"

    @property
    def critical(self) -> bool:
        return True

    def plan(self, context: InstallContext) -> PhasePlan:
        actions: list[PlannedAction] = []
        fresh = context.mode is InstallMode.FRESH
        for script in ROOT_SCRIPT_FILES:
            action_type = "overwrite" if fresh else "create"
            actions.append(
                PlannedAction(
                    action_type=action_type,
                    source=f"templates/.ai-engineering/scripts/{script}",
                    destination=f"{_SCRIPTS_REL}/{script}",
                    rationale=(
                        f"Deploy {script} so skills referencing "
                        f"python .ai-engineering/scripts/{script} succeed."
                    ),
                )
            )
        return PhasePlan(phase_name=self.name, actions=actions)

    def execute(self, plan: PhasePlan, context: InstallContext) -> PhaseResult:
        result = PhaseResult(phase_name=self.name)
        template_root = get_ai_engineering_template_root() / "scripts"
        target_root = context.target / _SCRIPTS_REL
        target_root.mkdir(parents=True, exist_ok=True)

        for action in plan.actions:
            script_name = Path(action.destination).name
            src = template_root / script_name
            dst = target_root / script_name

            if not src.exists():
                result.failed.append(f"{script_name}: source missing at {src}")
                continue

            try:
                if (
                    dst.exists()
                    and action.action_type == "create"
                    and dst.read_bytes() == src.read_bytes()
                ):
                    # Idempotent: only re-copy if content drifted.
                    result.skipped.append(script_name)
                    continue
                shutil.copy2(src, dst)
                # Preserve executable bit (the scripts have shebangs).
                dst.chmod(0o755)
                result.created.append(script_name)
            except OSError as exc:
                result.failed.append(f"{script_name}: {exc}")

        return result

    def verify(self, result: PhaseResult, context: InstallContext) -> PhaseVerdict:
        verdict = PhaseVerdict(phase_name=self.name, passed=True)
        target_root = context.target / _SCRIPTS_REL
        missing: list[str] = []
        for script in ROOT_SCRIPT_FILES:
            if not (target_root / script).exists():
                missing.append(script)
        if missing:
            verdict.passed = False
            verdict.errors.append(f"ScriptsPhase verification failed; missing: {missing}")
        if result.failed:
            verdict.passed = False
            verdict.errors.extend(result.failed)
        return verdict
