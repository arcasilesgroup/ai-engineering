#!/usr/bin/env python3
"""PreToolUse hook: enforce checkpoint gating for /ai-orchestrator.

The exit depends on the surface (`--surface`, else `cursor_version` in the payload,
else Claude). Claude, Pi, Oh My Pi and OpenCode: exit 2 and the reason on stderr.
Cursor, Codex and Copilot: exit 0 and a JSON decision, because a non-zero exit is
not a denial there. Cursor also needs `{"permission":"allow"}` on a pass: its
template is fail-closed, and empty stdout is a hook error.

Two guards:

1. Agent/Task calls whose prompt starts with `[checkpoint <slug>#<id> <stage>]`:
   - every earlier checkpoint must have status "passed";
   - the checkpoint itself must not already be passed;
   - stage "ui" needs behavior passed, and stage "review" needs behavior passed
     and ui passed or n/a.
2. Write/Edit of .ai-engineering/workflow/checkpoints/*.json: the resulting state must be consistent.
   - Gates or status can only change on a checkpoint whose predecessors all passed.
   - A gate can only be "passed" if the gates before it passed.
   - A checkpoint is "passed" only when every gate is passed or n/a.
3. Bash commands that would write a plan file are blocked (use Edit/Write so guard 2 runs).

Stop hook (same script, hook_event_name == "Stop"): guards 1-3 gate the path; this gates the
outcome. For a session that ran /ai-orchestrator on a plan, it blocks finishing while a started
checkpoint has unproven gates or the plan is structurally invalid, whatever route the state
took to get there. It lets through user interrupts, AskUserQuestion stops, plans with a
top-level "halted" reason (circuit breaker), and gives up after MAX_STOP_BLOCKS blocks in a row.
"""
import copy
import json
import os
import re
import subprocess
import sys
import tomllib

GATES = ["behavior", "ui", "review"]
STAGES = {"tests", "implement", "behavior", "ui", "review", "fix"}
MARKER = re.compile(r"^\s*\[checkpoint\s+([\w.-]+)#(\d+)\s+(\w+)\]")
LIFECYCLE_PHASES = {
    "awaiting-plan-approval", "implementation", "blocked",
    "awaiting-app-review", "ready-to-merge",
}
LOWER_TOOLS = {"bash": "Bash", "shell": "Bash", "write": "Write", "edit": "Edit", "read": "Read"}
SURFACE = "claude-code"


def canonical_surface(name):
    return {"copilot": "copilot-cli", "claude": "claude-code"}.get(name, name)


def surface_from_argv(argv):
    name = os.environ.get("AI_ENG_SURFACE", "")
    if "--surface" in argv:
        index = argv.index("--surface")
        if index + 1 < len(argv):
            name = argv[index + 1]
    return canonical_surface(name) if name else ""


def detect_surface(data):
    if isinstance(data, dict) and data.get("cursor_version"):
        return "cursor"
    return "claude-code"


def allow():
    # Cursor's carrier is fail-closed: empty stdout is a hook error, not a pass.
    if SURFACE == "cursor":
        print(json.dumps({"permission": "allow"}))
    sys.exit(0)


def block(msg):
    text = f"checkpoint-gate: {msg}"
    print(text, file=sys.stderr)
    if SURFACE == "cursor":
        print(json.dumps({"permission": "deny", "user_message": text, "agent_message": text}))
        sys.exit(0)
    if SURFACE == "codex":
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": text,
            }
        }))
        sys.exit(0)
    if SURFACE == "copilot-cli":
        print(json.dumps({"permissionDecision": "deny", "permissionDecisionReason": text}))
        sys.exit(0)
    sys.exit(2)


def normalise(data, surface):
    tool = data.get("tool_name") or data.get("tool") or data.get("toolName") or ""
    if surface == "cursor" and tool == "Shell":
        tool = "Bash"
    elif surface in ("pi", "oh-my-pi", "opencode"):
        tool = LOWER_TOOLS.get(tool, tool)
    raw_input = data.get("tool_input") or data.get("toolInput") or data.get("input") or {}
    tool_input = raw_input if isinstance(raw_input, dict) else {}
    if not tool_input.get("file_path"):
        for key in ("filePath", "path"):
            if isinstance(tool_input.get(key), str):
                tool_input["file_path"] = tool_input[key]
                break
    data["tool_name"] = tool
    data["tool_input"] = tool_input
    event = data.get("hook_event_name") or data.get("hookEventName") or ""
    if isinstance(event, str) and event.lower() == "stop":
        data["hook_event_name"] = "Stop"
    return data


def gate(cp, name):
    gates = cp.get("gates")
    state = gates.get(name) if isinstance(gates, dict) else None
    return state.get("status", "pending") if isinstance(state, dict) else "pending"


def gate_ok(cp, name):
    return gate(cp, name) in ("passed", "n/a")


def checkpoint_id_error(cps):
    if not isinstance(cps, list):
        return "checkpoint plan must contain a checkpoint list"
    for expected, checkpoint in enumerate(cps, 1):
        if (
            not isinstance(checkpoint, dict)
            or type(checkpoint.get("id")) is not int
            or checkpoint["id"] != expected
        ):
            return "checkpoint IDs must be finite positive integers in sequential order starting at 1"
    return None


def unpassed_before(cps, cid):
    if error := checkpoint_id_error(cps):
        block(error + ".")
    return [
        c["id"] for c in cps
        if c["id"] < cid and not (c.get("status") == "passed" and all(gate_ok(c, name) for name in GATES))
    ]


def check_agent(prompt, root):
    m = MARKER.match(prompt or "")
    if not m:
        return  # not an orchestrated checkpoint call
    slug, cid, stage = m.group(1), int(m.group(2)), m.group(3)
    if stage not in STAGES:
        block(f"unknown stage '{stage}'. Use one of: {', '.join(sorted(STAGES))}.")
    path = os.path.join(root, ".ai-engineering", "workflow", "checkpoints", f"{slug}.json")
    try:
        plan = json.load(open(path))
        if not isinstance(plan, dict) or plan.get("slug") != slug:
            block(f"checkpoint plan slug doesn't match marker '{slug}'.")
        cps = plan["checkpoints"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        block(f"can't read {path}: {e}")
    if error := checkpoint_id_error(cps):
        block(error + ".")
    if isinstance(plan, dict) and "lifecycle" in plan:
        if not isinstance(cps, list) or any(not isinstance(checkpoint, dict) for checkpoint in cps):
            block("lifecycle checkpoint plan must contain a checkpoint list.")
        error = lifecycle_shape_error(plan.get("lifecycle"), plan, root)
        if error:
            block(error + ".")
        state = plan["lifecycle"]
        if state["phase"] != "implementation" or state["plan_approval"] != "approved":
            block(f"{slug}: implementation is not authorized by the lifecycle approval.")
    cp = next((c for c in cps if c.get("id") == cid), None)
    if cp is None:
        block(f"checkpoint #{cid} doesn't exist in {slug}.json.")
    if (todo := unpassed_before(cps, cid)):
        block(f"can't start #{cid} ({stage}): checkpoint(s) {todo} haven't passed. Finish them first.")
    if cp.get("status") == "passed":
        block(f"#{cid} has already passed. Reopen it in the JSON (set the failing gate to \"failed\" and status to \"pending\") before working on it again.")
    if stage == "ui" and gate(cp, "behavior") != "passed":
        block(f"#{cid}: the UI gate needs the behavior gate passed first (behavior is '{gate(cp, 'behavior')}').")
    if stage == "review" and not (gate(cp, "behavior") == "passed" and gate_ok(cp, "ui")):
        block(f"#{cid}: the review gate needs behavior passed and ui passed or n/a (behavior='{gate(cp, 'behavior')}', ui='{gate(cp, 'ui')}').")


def snapshot(cp):
    return (cp.get("status"), tuple(gate(cp, g) for g in GATES))


def reviewed_plan_payload(plan):
    if not isinstance(plan, dict) or not isinstance(plan.get("checkpoints"), list):
        return None
    payload = copy.deepcopy(plan)
    payload.pop("lifecycle", None)
    for checkpoint in payload["checkpoints"]:
        if not isinstance(checkpoint, dict):
            return None
        checkpoint.pop("status", None)
        if isinstance(checkpoint.get("gates"), dict):
            for state in checkpoint["gates"].values():
                if isinstance(state, dict):
                    for field in ("status", "attempts", "findings"):
                        state.pop(field, None)
    return payload


def has_app_review_claim(plan):
    if not isinstance(plan, dict) or not isinstance(plan.get("lifecycle"), dict):
        return False
    lifecycle = plan["lifecycle"]
    return lifecycle.get("phase") in ("awaiting-app-review", "ready-to-merge") or (
        lifecycle.get("phase") == "blocked"
        and lifecycle.get("app_review") in ("pending", "approved")
    )


def git(root, *args):
    try:
        env = os.environ.copy()
        for name in (
            "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
            "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
            "GIT_NAMESPACE", "GIT_CEILING_DIRECTORIES",
        ):
            env.pop(name, None)
        result = subprocess.run(
            ["git", *args], cwd=root, env=env, capture_output=True, text=True, check=False,
        )
    except OSError:
        return None
    return result if result.returncode == 0 else None


def full_commit(root, value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value):
        return False
    return git(root, "cat-file", "-e", f"{value}^{{commit}}") is not None


def local_main(root):
    result = git(root, "rev-parse", "--verify", "refs/heads/main^{commit}")
    return result.stdout.strip() if result is not None else None


def local_feature(root, slug):
    if not isinstance(slug, str) or not re.fullmatch(r"[\w.-]+", slug):
        return None
    result = git(root, "rev-parse", "--verify", f"refs/heads/feat/{slug}^{{commit}}")
    return result.stdout.strip() if result is not None else None


def reviewed_feature_chain_error(root, slug, reviewed_main, reviewed_feature, phase):
    feature_tip = local_feature(root, slug)
    if feature_tip is None:
        return "the local feature tip is unreadable"
    if git(root, "merge-base", "--is-ancestor", reviewed_feature, feature_tip) is None:
        return "reviewed_feature is not an ancestor of the local feature tip"
    commits = git(root, "rev-list", "--reverse", f"{reviewed_feature}..{feature_tip}")
    if commits is None:
        return "the commits after reviewed_feature are unreadable"
    checkpoint_path = f".ai-engineering/workflow/checkpoints/{slug}.json"
    previous = reviewed_feature
    for index, commit in enumerate(commits.stdout.split()):
        parents = git(root, "rev-list", "--parents", "-n", "1", commit)
        paths = git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", "--no-renames", "-z", commit)
        if parents is None or parents.stdout.split() != [commit, previous]:
            return "reviewed_feature has a non-linear descendant history"
        if paths is None or [path for path in paths.stdout.split("\0") if path] != [checkpoint_path]:
            return "only checkpoint metadata commits may follow reviewed_feature"
        checkpoint = git(root, "show", f"{commit}:{checkpoint_path}")
        if checkpoint is None:
            return "a reviewed-feature descendant has no readable lifecycle checkpoint"
        try:
            plan = json.loads(checkpoint.stdout)
        except ValueError:
            return "a reviewed-feature descendant has malformed lifecycle metadata"
        lifecycle = plan.get("lifecycle") if isinstance(plan, dict) else None
        expected_phase = "awaiting-app-review" if index == 0 else "ready-to-merge"
        expected_review = "pending" if index == 0 else "approved"
        lifecycle_fields = {"phase", "plan_approval", "app_review", "reviewed_main", "reviewed_feature"}
        if (
            not isinstance(plan, dict)
            or plan.get("slug") != slug
            or checkpoint_shape_error(plan) is not None
            or not completed_gates(plan)
            or not isinstance(lifecycle, dict)
            or not lifecycle_fields.issubset(lifecycle)
            or set(lifecycle) - lifecycle_fields
            or lifecycle.get("phase") != expected_phase
            or lifecycle.get("plan_approval") != "approved"
            or lifecycle.get("app_review") != expected_review
            or lifecycle.get("reviewed_main") != reviewed_main
            or lifecycle.get("reviewed_feature") != reviewed_feature
            or (phase == "awaiting-app-review" and index > 0)
        ):
            return "a reviewed-feature descendant has invalid app-review lifecycle metadata"
        previous = commit
    return None


def completed_gates(plan):
    checkpoints = plan.get("checkpoints")
    if not isinstance(checkpoints, list) or not checkpoints:
        return False
    for checkpoint in checkpoints:
        if not isinstance(checkpoint, dict) or checkpoint.get("status") != "passed":
            return False
        gates = checkpoint.get("gates")
        if not isinstance(gates, dict):
            return False
        for name in GATES:
            state = gates.get(name)
            if not isinstance(state, dict) or state.get("status") not in ("passed", "n/a"):
                return False
    return True


def checkpoint_shape_error(plan):
    checkpoints = plan.get("checkpoints") if isinstance(plan, dict) else None
    if not isinstance(checkpoints, list) or not checkpoints:
        return "lifecycle requires a non-empty checkpoint list"
    if error := checkpoint_id_error(checkpoints):
        return error
    for checkpoint in checkpoints:
        if not isinstance(checkpoint, dict) or checkpoint.get("status") not in ("pending", "passed"):
            return "lifecycle checkpoint has an invalid status"
        gates = checkpoint.get("gates")
        if not isinstance(gates, dict):
            return "lifecycle checkpoint has invalid gates"
        for name in GATES:
            state = gates.get(name)
            if not isinstance(state, dict) or state.get("status") not in ("pending", "failed", "passed", "n/a"):
                return "lifecycle checkpoint has an invalid gate status"
        if checkpoint["status"] == "passed" and not all(gate_ok(checkpoint, name) for name in GATES):
            return "lifecycle checkpoint marked passed has incomplete gates"
    return None


def lifecycle_shape_error(state, plan, root, require_fresh=True):
    error = checkpoint_shape_error(plan)
    if error:
        return error
    fields = {"phase", "plan_approval", "app_review", "reviewed_main"}
    if (
        not isinstance(state, dict)
        or not fields.issubset(state)
        or set(state) - fields not in (set(), {"reviewed_feature"})
    ):
        return "lifecycle must contain phase, plan_approval, app_review and reviewed_main"
    phase, approval, review, reviewed = (state[field] for field in ("phase", "plan_approval", "app_review", "reviewed_main"))
    if not isinstance(phase, str) or phase not in LIFECYCLE_PHASES:
        return "lifecycle has an unknown phase"
    if approval not in ("pending", "approved") or review not in ("not-started", "pending", "approved"):
        return "lifecycle has an invalid approval value"
    if reviewed is not None and not full_commit(root, reviewed):
        return "reviewed_main must be a full commit id"
    reviewed_feature = state.get("reviewed_feature")
    if reviewed_feature is not None and not full_commit(root, reviewed_feature):
        return "reviewed_feature must be a full commit id"
    if phase == "awaiting-plan-approval" and (
        (approval, review, reviewed) != ("pending", "not-started", None)
        or reviewed_feature is not None
    ):
        return "awaiting-plan-approval requires pending plan approval, no app review and no reviewed_main"
    if phase == "implementation" and (
        (approval, review, reviewed) != ("approved", "not-started", None)
        or reviewed_feature is not None
    ):
        return "implementation requires approved plan, no app review and no reviewed_main"
    if phase == "awaiting-app-review":
        if (
            (approval, review) != ("approved", "pending")
            or not isinstance(reviewed, str)
            or not isinstance(reviewed_feature, str)
        ):
            return "awaiting-app-review requires approved plan, pending app review and both reviewed commits"
        if not completed_gates(plan):
            return "awaiting-app-review requires completed checkpoint gates"
        if require_fresh:
            if reviewed != local_main(root):
                return "reviewed_main is stale or is not the current local main commit"
            if error := reviewed_feature_chain_error(
                root, plan.get("slug"), reviewed, reviewed_feature, phase,
            ):
                return error
    if phase == "ready-to-merge":
        if (
            (approval, review) != ("approved", "approved")
            or not isinstance(reviewed, str)
            or not isinstance(reviewed_feature, str)
        ):
            return "ready-to-merge requires approved plan and app review with reviewed_main and reviewed_feature"
        if not completed_gates(plan):
            return "ready-to-merge requires completed checkpoint gates"
        if require_fresh and reviewed != local_main(root):
            return "reviewed_main is stale or is not the current local main commit"
        if require_fresh:
            if error := reviewed_feature_chain_error(
                root, plan.get("slug"), reviewed, reviewed_feature, phase,
            ):
                return error
    if phase == "blocked":
        if approval == "pending":
            if (review, reviewed, reviewed_feature) != ("not-started", None, None):
                return "blocked work with pending plan approval cannot have app review state"
        elif review == "not-started":
            if reviewed is not None or reviewed_feature is not None:
                return "blocked work without app review cannot have reviewed commits"
        else:
            if not isinstance(reviewed, str) or not isinstance(reviewed_feature, str) or not completed_gates(plan):
                return "blocked app-review work requires completed gates and both reviewed commits"
    return None


def lifecycle_transition_error(old_state, new_state, root, slug):
    old_phase = old_state["phase"]
    new_phase = new_state["phase"]
    if old_state == new_state:
        return None
    if new_phase == "blocked":
        if any(
            old_state.get(field) != new_state.get(field)
            for field in ("plan_approval", "app_review", "reviewed_main", "reviewed_feature")
        ):
            if (
                old_phase in ("awaiting-app-review", "ready-to-merge")
                and old_state["plan_approval"] == "approved"
                and new_state["plan_approval"] == "approved"
                and new_state["app_review"] == "not-started"
                and new_state["reviewed_main"] is None
                and new_state.get("reviewed_feature") is None
            ):
                return None
            return "blocked is fail-safe and cannot change approval state"
        return None
    if new_phase == "implementation" and old_phase in ("awaiting-app-review", "ready-to-merge"):
        if (
            old_state["plan_approval"] == "approved"
            and new_state["plan_approval"] == "approved"
            and new_state["app_review"] == "not-started"
            and new_state["reviewed_main"] is None
            and new_state.get("reviewed_feature") is None
            and old_state["reviewed_main"] != local_main(root)
        ):
            return None
        return "app-review invalidation requires stale reviewed_main and cleared reviewed commits"
    if old_phase == "awaiting-plan-approval":
        if new_phase == "implementation" and new_state["plan_approval"] == "approved":
            return None
        return "plan approval must transition directly from awaiting-plan-approval to implementation"
    if old_phase == "implementation":
        if (
            new_phase == "awaiting-app-review"
            and new_state["reviewed_main"] == local_main(root)
            and new_state.get("reviewed_feature") == local_feature(root, slug)
        ):
            return None
        return "implementation may only advance to awaiting-app-review or blocked"
    if old_phase == "blocked":
        if new_phase == "awaiting-plan-approval" and new_state["plan_approval"] == "pending":
            return None
        if new_phase == "implementation" and (
            old_state["plan_approval"] == "approved" and old_state["app_review"] == "not-started"
        ):
            return None
        if new_phase == "awaiting-app-review" and old_state["app_review"] in ("pending", "approved"):
            if (
                new_state["app_review"] == "pending"
                and new_state["reviewed_main"] == local_main(root)
                and new_state.get("reviewed_feature") == local_feature(root, slug)
            ):
                return None
        if (
            new_phase == "ready-to-merge"
            and old_state["app_review"] == "approved"
            and new_state["reviewed_main"] == old_state["reviewed_main"]
            and new_state.get("reviewed_feature") == old_state.get("reviewed_feature")
        ):
            return None
        return "blocked work may resume only into a phase allowed by its existing approvals"
    if old_phase == "awaiting-app-review" and new_phase == "ready-to-merge":
        if (
            new_state["reviewed_main"] == old_state["reviewed_main"]
            and new_state.get("reviewed_feature") == old_state.get("reviewed_feature")
        ):
            return None
        return "app-review approval must retain both reviewed commits"
    if new_phase == "awaiting-app-review" and old_phase in ("awaiting-app-review", "ready-to-merge"):
        current = local_main(root)
        feature_tip = local_feature(root, slug)
        if (
            new_state["app_review"] == "pending"
            and new_state["reviewed_main"] == current
            and new_state.get("reviewed_feature") == feature_tip
            and (
                new_state["reviewed_main"] != old_state["reviewed_main"]
                or new_state.get("reviewed_feature") != old_state.get("reviewed_feature")
            )
        ):
            return None
        return "app-review reset requires a fresh review against current local refs"
    if old_phase == "ready-to-merge" and new_phase == "ready-to-merge":
        return "ready-to-merge approval cannot change without repeating app review"
    return f"unauthorized lifecycle transition from {old_phase} to {new_phase}"


def check_lifecycle(new_plan, old_plan, root, check_transition=True):
    if not isinstance(new_plan, dict):
        return
    new_has_state = "lifecycle" in new_plan
    old_has_state = isinstance(old_plan, dict) and "lifecycle" in old_plan
    if not new_has_state and not old_has_state:
        return  # legacy checkpoint-gate behavior is unchanged
    if not new_has_state:
        block("lifecycle state cannot be removed from a checkpoint.")
    new_state = new_plan["lifecycle"]
    error = lifecycle_shape_error(new_state, new_plan, root)
    if error:
        block(error + ".")
    if not check_transition:
        return
    if not old_has_state:
        initial_state = {
            "phase": "awaiting-plan-approval",
            "plan_approval": "pending",
            "app_review": "not-started",
            "reviewed_main": None,
        }
        brainstorm_approved_state = {
            "phase": "implementation",
            "plan_approval": "approved",
            "app_review": "not-started",
            "reviewed_main": None,
            "reviewed_feature": None,
        }
        if new_state not in (
            initial_state,
            {**initial_state, "reviewed_feature": None},
            brainstorm_approved_state,
        ):
            block("a new lifecycle must start pending plan approval or approved for implementation with no review.")
        return
    old_state = old_plan["lifecycle"]
    if lifecycle_shape_error(old_state, old_plan, root, require_fresh=False):
        block("existing lifecycle state is malformed; refusing a lifecycle transition.")
    error = lifecycle_transition_error(old_state, new_state, root, new_plan.get("slug"))
    if error:
        block(error + ".")


def has_symlink_component(path):
    drive, remainder = os.path.splitdrive(path)
    current = drive + os.sep if os.path.isabs(path) else drive
    if os.altsep:
        remainder = remainder.replace(os.altsep, os.sep)
    for component in remainder.split(os.sep):
        if component in ("", "."):
            continue
        if component == "..":
            current = os.path.dirname(current) or current
            continue
        current = os.path.join(current, component)
        if os.path.islink(current):
            return True
    return False


def lifecycle_plan_path_error(plan, path, root, require_feature_worktree):
    slug = plan.get("slug")
    if not isinstance(slug, str) or not re.fullmatch(r"[\w.-]+", slug):
        return "lifecycle checkpoint plan must have a valid slug"
    if not isinstance(path, str) or not path:
        return "lifecycle checkpoint plan must be written at its matching path inside the current worktree"
    worktree_root = os.path.realpath(root)
    candidate = path if os.path.isabs(path) else os.path.join(worktree_root, path)
    target = os.path.abspath(candidate)
    expected = os.path.join(
        worktree_root, ".ai-engineering", "workflow", "checkpoints", f"{slug}.json"
    )
    try:
        is_inside_worktree = (
            os.path.normcase(os.path.commonpath((worktree_root, target)))
            == os.path.normcase(worktree_root)
        )
    except ValueError:
        is_inside_worktree = False
    if (
        os.path.normcase(target) != os.path.normcase(expected)
        or not is_inside_worktree
        or has_symlink_component(candidate)
    ):
        return "lifecycle checkpoint plan must be written at its matching path inside the current worktree"
    if not require_feature_worktree:
        return None
    top = git(root, "rev-parse", "--show-toplevel")
    common_dir = git(root, "rev-parse", "--git-common-dir")
    listed = git(root, "worktree", "list", "--porcelain", "-z")
    if top is None or common_dir is None or listed is None:
        return "a new lifecycle plan must be created in its selected feature worktree"
    if os.path.realpath(top.stdout.strip()) != worktree_root:
        return "a new lifecycle plan must be created in its selected feature worktree"
    absolute_common_dir = os.path.realpath(os.path.join(worktree_root, common_dir.stdout.strip()))
    if os.path.basename(absolute_common_dir) != ".git":
        return "a new lifecycle plan must be created in its selected feature worktree"
    primary_root = os.path.realpath(os.path.dirname(absolute_common_dir))
    if worktree_root == primary_root:
        return "a new lifecycle plan cannot be created in the primary checkout"
    config_path = os.path.join(primary_root, ".ai-engineering", "config.toml")
    try:
        with open(config_path, "rb") as config_file:
            config = tomllib.load(config_file)
    except FileNotFoundError:
        config = {}
    except (OSError, tomllib.TOMLDecodeError):
        return "the configured worktree root cannot be read"
    git_config = config.get("git", {})
    if not isinstance(git_config, dict):
        return "the configured worktree root cannot be read"
    configured_root = git_config.get("worktrees_dir")
    if isinstance(configured_root, str) and configured_root.strip():
        configured_root = os.path.realpath(os.path.join(primary_root, configured_root.strip()))
    else:
        configured_root = os.path.realpath(f"{primary_root}.worktrees")
    try:
        is_managed_worktree = (
            worktree_root != configured_root
            and os.path.commonpath((configured_root, worktree_root)) == configured_root
        )
    except ValueError:
        is_managed_worktree = False
    if not is_managed_worktree:
        return "a new lifecycle plan must be created in its configured feature worktree"
    entries = []
    entry = {}
    for field in listed.stdout.split("\0"):
        if not field:
            if entry:
                entries.append(entry)
                entry = {}
            continue
        key, separator, value = field.partition(" ")
        if separator and key in ("worktree", "branch"):
            if key in entry:
                return "the Git worktree list is unreadable"
            entry[key] = value
    if entry:
        entries.append(entry)
    matches = [
        item for item in entries
        if isinstance(item.get("worktree"), str)
        and os.path.realpath(item["worktree"]) == worktree_root
    ]
    if len(matches) != 1 or matches[0].get("branch") != f"refs/heads/feat/{slug}":
        return "a new lifecycle plan must be created in its Git-listed feat/<slug> worktree"
    return None


def check_plan(new_text, old_text, root, check_transition=True, path=None):
    try:
        new_plan = json.loads(new_text)
    except ValueError:
        return  # not a valid plan yet; the planner validates JSON itself
    if not isinstance(new_plan, dict):
        return  # not a checkpoint plan; retain the existing legacy behavior
    if "checkpoints" not in new_plan:
        if "lifecycle" in new_plan:
            block("lifecycle checkpoint plan must contain a checkpoint list.")
        return
    new = new_plan["checkpoints"]
    if isinstance(new_plan, dict) and "lifecycle" in new_plan:
        if not isinstance(new, list) or any(not isinstance(cp, dict) for cp in new):
            block("lifecycle checkpoint plan must contain a checkpoint list.")
    if error := checkpoint_id_error(new):
        block(error + ".")
    old = {}
    old_plan = {}
    try:
        old_plan = json.loads(old_text)
        old = {c["id"]: snapshot(c) for c in old_plan["checkpoints"]}
    except (ValueError, KeyError, TypeError):
        pass
    had_plan = isinstance(old_plan, dict) and isinstance(old_plan.get("checkpoints"), list)
    had_lifecycle = isinstance(old_plan, dict) and "lifecycle" in old_plan
    if has_app_review_claim(new_plan) or (
        has_app_review_claim(old_plan)
        and not (
            isinstance(new_plan.get("lifecycle"), dict)
            and new_plan["lifecycle"].get("phase") == "implementation"
        )
    ):
        old_payload = reviewed_plan_payload(old_plan)
        new_payload = reviewed_plan_payload(new_plan)
        if old_payload is None or new_payload is None:
            block("can't verify the checkpoint plan across app review.")
        if old_payload != new_payload:
            block("checkpoint plan changed after app review began.")
    for cp in new:
        cid = cp.get("id")
        g = [gate(cp, x) for x in GATES]
        if g[1] == "passed" and g[0] != "passed":
            block(f"#{cid}: can't mark ui passed before behavior has passed.")
        if g[2] == "passed" and not (g[0] == "passed" and g[1] in ("passed", "n/a")):
            block(f"#{cid}: can't mark review passed before behavior and ui have passed.")
        if cp.get("status") == "passed" and not all(x in ("passed", "n/a") for x in g):
            block(f"#{cid}: status 'passed' needs every gate passed or n/a (gates: {dict(zip(GATES, g))}).")
        changed = cid in old and old[cid] != snapshot(cp)
        started = cid not in old and (cp.get("status") == "passed" or any(x in ("passed", "failed") for x in g))
        if (changed or started) and (todo := unpassed_before(new, cid)):
            block(f"#{cid}: can't change gates or status while checkpoint(s) {todo} haven't passed.")
    if check_transition:
        if "lifecycle" in new_plan:
            if error := lifecycle_plan_path_error(new_plan, path, root, not had_lifecycle):
                block(error + ".")
        elif not had_plan:
            block("a new checkpoint plan must include its initial lifecycle.")
    check_lifecycle(new_plan, old_plan, root, check_transition)


BASH_WRITE = re.compile(r">|\btee\b|\bsed\s+-i|\bpython3?\b|\bnode\b|\bperl\b|\bjq\b.*>|\bmv\b|\bcp\b|\btruncate\b")
MAX_STOP_BLOCKS = 3


def check_bash(cmd):
    """Plan files change only through Edit/Write, so check_plan always sees the change."""
    if re.search(r"\.ai-engineering/workflow/checkpoints/[^\s/]+\.json", cmd or "") and BASH_WRITE.search(cmd) and not re.match(r"\s*git\s", cmd):
        block("don't modify .ai-engineering/workflow/checkpoints/*.json from Bash. Use Edit or Write so the gate rules are checked.")


def orchestrating(transcript, slug):
    """Only the session that ran /ai-orchestrator on this plan is held to it; other sessions sharing the repo aren't."""
    try:
        t = open(transcript, errors="ignore").read()
    except (OSError, TypeError):
        return False
    ran = re.search(r'"skill"\s*:\s*"ai-orchestrator"|<command-name>/ai-orchestrator</command-name>', t)
    return bool(ran) and f".ai-engineering/workflow/checkpoints/{slug}.json" in t


def check_stop(data, root):
    """Stop hook: judge the outcome on disk, however it got there."""
    if data.get("stop_reason") in ("user_interrupt", "ask_user_question"):
        return  # the human is taking over or being asked (checkpoint/app review)
    counter = os.path.join(os.environ.get("TMPDIR", "/tmp"), f"checkpoint-gate-stop-{data.get('session_id', 'x')}")
    problems = []
    folder = os.path.join(root, ".ai-engineering", "workflow", "checkpoints")
    for f in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if not f.endswith(".json"):
            continue
        slug, text = f[:-5], open(os.path.join(folder, f)).read()
        try:
            plan = json.loads(text)
        except ValueError:
            continue
        if not orchestrating(data.get("transcript_path"), slug):
            continue
        check_plan(text, "", root, check_transition=False)  # structural rules against an empty baseline
        if (plan.get("halted") or {}).get("reason"):
            continue  # circuit breaker: stopping for a human is allowed, with the reason on record
        for cp in plan.get("checkpoints", []):
            gates = {g: gate(cp, g) for g in GATES}
            started = any(s in ("passed", "failed") for s in gates.values()) or any((cp.get("gates") or {}).get(g, {}).get("attempts") for g in GATES)
            if cp.get("status") != "passed" and started:
                open_gates = ", ".join(f"{g}={s}" for g, s in gates.items() if s not in ("passed", "n/a"))
                problems.append(f"{slug} #{cp.get('id')} {cp.get('title', '')}: gates not yet proven ({open_gates})")
    if not problems:
        _reset(counter)
        return
    n = _bump(counter)
    if n > MAX_STOP_BLOCKS:
        _reset(counter)
        print(f"checkpoint-gate: letting the stop through after {MAX_STOP_BLOCKS} blocks; still open: {'; '.join(problems)}", file=sys.stderr)
        return
    block("a checkpoint is mid-run. " + "; ".join(problems)
          + ". Keep going with the loop. If you really have to stop for a human (circuit breaker only), first set the top-level "
          + '"halted": {"reason": "...", "checkpoint": <id>} in the plan JSON.')


def _bump(path):
    try:
        n = int(open(path).read()) + 1
    except (OSError, ValueError):
        n = 1
    open(path, "w").write(str(n))
    return n


def _reset(path):
    try:
        os.remove(path)
    except OSError:
        pass


def main():
    global SURFACE
    chosen = surface_from_argv(sys.argv)
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except ValueError:
        SURFACE = chosen or "claude-code"
        allow()
    if not isinstance(data, dict):
        SURFACE = chosen or "claude-code"
        allow()
    SURFACE = chosen or detect_surface(data)
    data = normalise(data, SURFACE)
    tool, inp = data.get("tool_name", ""), data.get("tool_input") or {}
    root = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()

    if data.get("hook_event_name") == "Stop":
        check_stop(data, root)
        allow()
    if tool == "Bash":
        check_bash(inp.get("command"))
        allow()
    if tool in ("Agent", "Task"):
        check_agent(inp.get("prompt"), root)
        allow()

    path = inp.get("file_path", "")
    if tool not in ("Write", "Edit") or not re.search(r"\.ai-engineering/workflow/checkpoints/[^/]+\.json$", path):
        allow()
    try:
        old_text = open(path).read()
    except OSError:
        old_text = ""
    if tool == "Write":
        new_text = inp.get("content", "")
    else:
        old_s, new_s = inp.get("old_string", ""), inp.get("new_string", "")
        if not old_s or old_s not in old_text:
            allow()  # Edit will fail on its own
        new_text = old_text.replace(old_s, new_s) if inp.get("replace_all") else old_text.replace(old_s, new_s, 1)
    check_plan(new_text, old_text, root, path=path)
    allow()


if __name__ == "__main__":
    main()
