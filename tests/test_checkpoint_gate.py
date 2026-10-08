"""Run: python3 tests/test_checkpoint_gate.py"""
import copy
import errno
import json
import os
import subprocess
import sys
import tempfile

HOOK = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "checkpoint-gate.py")
)


def cp(i, status="pending", b="pending", u="n/a", r="pending"):
    g = lambda s: {"status": s, "attempts": 0, "findings": []}
    return {"id": i, "status": status, "gates": {"behavior": g(b), "ui": g(u), "review": g(r)}}


PLAN = {"slug": "demo", "checkpoints": [cp(1, "passed", "passed", "n/a", "passed"), cp(2, u="pending"), cp(3)]}


def run(root, payload):
    env = {**os.environ, "CLAUDE_PROJECT_DIR": root}
    return subprocess.run([sys.executable, HOOK], input=json.dumps(payload), capture_output=True, text=True, env=env).returncode


def agent(marker):
    return {"tool_name": "Agent", "tool_input": {"prompt": f"{marker}\nDo the work."}}


def write(path, plan):
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": json.dumps(plan)}}


def with_gate(plan, cid, **gates):
    p = copy.deepcopy(plan)
    c = next(c for c in p["checkpoints"] if c["id"] == cid)
    for k, v in gates.items():
        if k == "status":
            c["status"] = v
        else:
            c["gates"][k]["status"] = v
    return p


def is_symlink_creation_unavailable(error):
    unavailable_errors = {errno.EACCES, errno.EPERM}
    for name in ("ENOSYS", "ENOTSUP", "EOPNOTSUPP"):
        if hasattr(errno, name):
            unavailable_errors.add(getattr(errno, name))
    return getattr(error, "winerror", None) == 1314 or error.errno in unavailable_errors


with tempfile.TemporaryDirectory(
    prefix=".checkpoint-gate-",
    dir=os.path.dirname(os.path.abspath(__file__)),
) as temporary_root:
    root = os.path.realpath(temporary_root)
    os.makedirs(f"{root}/.ai-engineering/workflow/checkpoints")
    path = f"{root}/.ai-engineering/workflow/checkpoints/demo.json"
    json.dump(PLAN, open(path, "w"))

    cases = [
        ("no marker → allowed", agent("plain prompt"), 0),
        ("#2 implement (prev passed) → allowed", agent("[checkpoint demo#2 implement]"), 0),
        ("#3 implement while #2 open → blocked", agent("[checkpoint demo#3 implement]"), 2),
        ("#2 ui before behavior → blocked", agent("[checkpoint demo#2 ui]"), 2),
        ("#2 review before behavior → blocked", agent("[checkpoint demo#2 review]"), 2),
        ("#1 already passed → blocked", agent("[checkpoint demo#1 fix]"), 2),
        ("unknown checkpoint → blocked", agent("[checkpoint demo#9 tests]"), 2),
        ("mark #2 behavior failed → allowed", write(path, with_gate(PLAN, 2, behavior="failed")), 0),
        ("mark #2 behavior passed → allowed", write(path, with_gate(PLAN, 2, behavior="passed")), 0),
        ("mark #3 behavior passed while #2 open → blocked", write(path, with_gate(PLAN, 3, behavior="passed")), 2),
        ("mark #2 ui passed before behavior → blocked", write(path, with_gate(PLAN, 2, ui="passed")), 2),
        ("mark #2 status passed with gates pending → blocked", write(path, with_gate(PLAN, 2, status="passed")), 2),
        ("mark #2 fully passed → allowed", write(path, with_gate(PLAN, 2, behavior="passed", ui="passed", review="passed", status="passed")), 0),
        ("unrelated file → allowed", {"tool_name": "Write", "tool_input": {"file_path": f"{root}/x.json", "content": "{}"}}, 0),
    ]
    fails = 0
    for name, payload, want in cases:
        got = run(root, payload)
        ok = got == want
        fails += not ok
        print(("ok  " if ok else "FAIL"), name, f"(exit {got})")

    other_plan = copy.deepcopy(PLAN)
    other_plan["slug"] = "other"
    other_plan["lifecycle"] = {
        "phase": "implementation",
        "plan_approval": "approved",
        "app_review": "not-started",
        "reviewed_main": None,
    }
    json.dump(other_plan, open(path, "w"))
    got = run(root, agent("[checkpoint demo#2 implement]"))
    fails += got != 2
    print(("ok  " if got == 2 else "FAIL"), "marker slug mismatch → blocked", f"(exit {got})")

    contradictory = copy.deepcopy(PLAN)
    contradictory["checkpoints"][0]["gates"]["review"]["status"] = "pending"
    contradictory["lifecycle"] = {
        "phase": "implementation",
        "plan_approval": "approved",
        "app_review": "not-started",
        "reviewed_main": None,
    }
    json.dump(contradictory, open(path, "w"))
    got = run(root, agent("[checkpoint demo#2 implement]"))
    fails += got != 2
    print(("ok  " if got == 2 else "FAIL"), "passed predecessor with incomplete gate → blocked", f"(exit {got})")

    contradictory.pop("lifecycle")
    json.dump(contradictory, open(path, "w"))
    got = run(root, agent("[checkpoint demo#2 implement]"))
    fails += got != 2
    print(("ok  " if got == 2 else "FAIL"), "legacy passed predecessor with incomplete gate → blocked", f"(exit {got})")

    overflow = json.dumps(with_gate(PLAN, 1, status="pending", behavior="pending")).replace('"id": 1,', '"id": 1e999,', 1)
    with open(path, "w") as fixture:
        fixture.write(overflow)
    got = run(root, agent("[checkpoint demo#2 implement]"))
    fails += got != 2
    print(("ok  " if got == 2 else "FAIL"), "non-finite predecessor id cannot bypass incomplete gate → blocked", f"(exit {got})")

    # Edit path: simulate replacing one gate status in the file on disk.
    json.dump(PLAN, open(path, "w"), indent=2)
    text = open(path).read()
    edit = {"tool_name": "Edit", "tool_input": {"file_path": path, "old_string": '"id": 3,\n      "status": "pending"', "new_string": '"id": 3,\n      "status": "passed"'}}
    got = run(root, edit)
    print(("ok  " if got == 2 else "FAIL"), "Edit #3 status passed while #2 open → blocked", f"(exit {got})")
    fails += got != 2

    # --- Bash guard ---
    bash = lambda c: {"tool_name": "Bash", "tool_input": {"command": c}}
    # --- Stop hook ---
    orch_tx = f"{root}/orch.jsonl"
    open(orch_tx, "w").write('{"name":"Skill","input":{"skill":"ai-orchestrator"}} read .ai-engineering/workflow/checkpoints/demo.json\n')
    other_tx = f"{root}/other.jsonl"
    open(other_tx, "w").write("unrelated session\n")
    mid = with_gate(PLAN, 2, behavior="failed")  # #2 started, not passed
    done = with_gate(PLAN, 2, behavior="passed", ui="passed", review="passed", status="passed")
    done = with_gate(done, 3, behavior="passed", review="passed", status="passed")
    halted = {**mid, "halted": {"reason": "circuit breaker", "checkpoint": 2}}
    bad = with_gate(PLAN, 3, behavior="passed")  # written behind the hooks' back: #3 moved while #2 open

    def stop(plan, tx=orch_tx, session="s1", reason="end_turn"):
        def payload():  # lazy: write this case's plan to disk right before the hook runs
            json.dump(plan, open(path, "w"))
            return {"hook_event_name": "Stop", "session_id": session, "transcript_path": tx, "stop_reason": reason}
        return payload

    later = [
        ("bash heredoc into plan → blocked", bash("cat > .ai-engineering/workflow/checkpoints/demo.json <<EOF\n{}\nEOF"), 2),
        ("bash python rewrite of plan → blocked", bash("python3 -c \"open('.ai-engineering/workflow/checkpoints/demo.json','w')\""), 2),
        ("bash git add plan → allowed", bash("git add .ai-engineering/workflow/checkpoints/demo.json"), 0),
        ("bash cat plan → allowed", bash("cat .ai-engineering/workflow/checkpoints/demo.json"), 0),
        ("stop mid-checkpoint (orchestrator session) → blocked", stop(mid), 2),
        ("stop mid-checkpoint (other session) → allowed", stop(mid, tx=other_tx), 0),
        ("stop mid-checkpoint on user interrupt → allowed", stop(mid, reason="user_interrupt"), 0),
        ("stop to ask the human → allowed", stop(mid, reason="ask_user_question"), 0),
        ("stop with halted reason → allowed", stop(halted), 0),
        ("stop with all passed → allowed", stop(done), 0),
        ("stop with invalid state written via bash → blocked", stop(bad), 2),
        ("stop before any gate started → allowed", stop(PLAN), 0),
    ]
    for name, payload, want in later:
        got = run(root, payload() if callable(payload) else payload)
        fails += got != want
        print(("ok  " if got == want else "FAIL"), name, f"(exit {got})")

    # loop guard: blocks MAX_STOP_BLOCKS times in a row, then lets the stop through
    codes = [run(root, stop(mid, session="loop")()) for _ in range(4)]
    ok = codes == [2, 2, 2, 0]
    fails += not ok
    print(("ok  " if ok else "FAIL"), "stop loop guard: 3 blocks then allow", codes)

    def surfaced(payload, surface):
        env = {**os.environ, "CLAUDE_PROJECT_DIR": root}
        return subprocess.run(
            [sys.executable, HOOK, "--surface", surface],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
        )

    dialects = [
        ("cursor allow prints permission", agent("plain prompt"), "cursor", 0, '"permission": "allow"'),
        ("cursor deny stays exit 0", agent("[checkpoint demo#3 implement]"), "cursor", 0, '"permission": "deny"'),
        ("cursor Shell is Bash", {"tool_name": "Shell", "tool_input": {"command": "cat > .ai-engineering/workflow/checkpoints/demo.json <<EOF\n{}\nEOF"}}, "cursor", 0, '"permission": "deny"'),
        ("codex deny is JSON exit 0", agent("[checkpoint demo#3 implement]"), "codex", 0, '"permissionDecision": "deny"'),
        ("copilot deny is JSON exit 0", agent("[checkpoint demo#3 implement]"), "copilot-cli", 0, '"permissionDecision": "deny"'),
        ("pi deny stays exit 2", agent("[checkpoint demo#3 implement]"), "pi", 2, ""),
        ("opencode deny stays exit 2", agent("[checkpoint demo#3 implement]"), "opencode", 2, ""),
        ("oh-my-pi deny stays exit 2", agent("[checkpoint demo#3 implement]"), "oh-my-pi", 2, ""),
    ]
    for name, payload, surface, want, needle in dialects:
        result = surfaced(payload, surface)
        ok = result.returncode == want and (needle in result.stdout if needle else result.stdout == "")
        fails += not ok
        print(("ok  " if ok else "FAIL"), name, f"(exit {result.returncode})")

    # --- Local lifecycle state ---
    legacy = copy.deepcopy(PLAN)

    def life(phase, plan_approval="pending", app_review="not-started", reviewed_main=None):
        return {
            "phase": phase,
            "plan_approval": plan_approval,
            "app_review": app_review,
            "reviewed_main": reviewed_main,
        }

    def with_lifecycle(plan, lifecycle):
        result = copy.deepcopy(plan)
        result["lifecycle"] = lifecycle
        return result

    def all_gates_passed(plan):
        result = copy.deepcopy(plan)
        for checkpoint in result["checkpoints"]:
            checkpoint["status"] = "passed"
            for gate_state in checkpoint["gates"].values():
                gate_state["status"] = "passed"
        return result

    def lifecycle_result(name, old_plan, new_plan, want):
        json.dump(old_plan, open(path, "w"))
        got = run(root, write(path, new_plan))
        ok = got == want
        nonlocal_fails[0] += not ok
        print(("ok  " if ok else "FAIL"), f"{name} (exit {got})")

    def legacy_result(name, payload, want):
        json.dump(legacy, open(path, "w"))
        got = run(root, payload)
        ok = got == want
        nonlocal_fails[0] += not ok
        print(("ok  " if ok else "FAIL"), f"{name} (exit {got})")

    nonlocal_fails = [0]
    git_env = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
    }

    def git(args, cwd=root):
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            env=git_env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")
        return result.stdout.strip()

    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, env=git_env, check=True)
    git(["config", "user.name", "Ada Lovelace"])
    git(["config", "user.email", "ada@example.com"])
    git(["config", "commit.gpgsign", "false"])
    os.makedirs(f"{root}/.ai-engineering", exist_ok=True)
    with open(f"{root}/.ai-engineering/config.toml", "w") as fixture:
        fixture.write('[git]\nworktrees_dir = "selected-worktrees"\n')
    with open(f"{root}/README.md", "w") as fixture:
        fixture.write("# lifecycle fixture\n")
    git(["add", "README.md", ".ai-engineering/config.toml"])
    git(["commit", "-q", "-m", "lifecycle base"])
    reviewed_main = git(["rev-parse", "refs/heads/main"])

    initial = life("awaiting-plan-approval")
    initial_plan = with_lifecycle(legacy, initial)
    legacy_result("U8: legacy checkpoint keeps existing gate behavior", agent("[checkpoint demo#2 implement]"), 0)
    legacy_result("U8: legacy checkpoint still blocks a skipped checkpoint", agent("[checkpoint demo#3 implement]"), 2)
    lifecycle_result(
        "U8: legacy checkpoint cannot gain direct merge authority",
        legacy,
        with_lifecycle(legacy, life("ready-to-merge", "approved", "approved", reviewed_main)),
        2,
    )
    lifecycle_result("U17: legacy checkpoint cannot initialize lifecycle in primary checkout", legacy, initial_plan, 2)
    legacy_result(
        "U17: legacy primary checkpoint keeps existing gate writes",
        write(path, with_gate(legacy, 2, behavior="failed")),
        0,
    )

    # A fresh lifecycle plan belongs to the Git-listed feature worktree, not the primary checkout.
    os.makedirs(f"{root}/selected-worktrees")
    selected_root = os.path.realpath(f"{root}/selected-worktrees/selected-feature")
    subprocess.run(
        ["git", "worktree", "add", "-q", "-b", "feat/demo", selected_root],
        cwd=root,
        env=git_env,
        check=True,
    )
    selected_path = f"{selected_root}/.ai-engineering/workflow/checkpoints/demo.json"
    os.makedirs(os.path.dirname(selected_path), exist_ok=True)
    selected_result = run(selected_root, write(selected_path, initial_plan))
    fails += selected_result != 0
    print(("ok  " if selected_result == 0 else "FAIL"), "U17: initial lifecycle plan is accepted in selected feature worktree", f"(exit {selected_result})")
    checkpoint_dir = os.path.dirname(selected_path)
    alias_path = f"{checkpoint_dir}/demo-alias.json"
    with open(selected_path, "w") as fixture:
        json.dump(legacy, fixture)
    canonical_result = run(selected_root, write(selected_path, initial_plan))
    fails += canonical_result != 0
    print(("ok  " if canonical_result == 0 else "FAIL"), "U20: canonical lifecycle path remains accepted", f"(exit {canonical_result})")
    try:
        os.symlink(selected_path, alias_path)
    except OSError as error:
        if not is_symlink_creation_unavailable(error):
            raise
        print(f"SKIP U20: distinct checkpoint alias symlink regression; this platform denies symlink creation ({error})")
    else:
        try:
            alias_result = run(selected_root, write(alias_path, initial_plan))
        finally:
            os.unlink(alias_path)
        fails += alias_result != 2
        print(("ok  " if alias_result == 2 else "FAIL"), f"U20: distinct symlink alias cannot initialize lifecycle (exit {alias_result})")
    os.unlink(selected_path)

    target_path = f"{selected_path}.target"
    with open(target_path, "w") as fixture:
        json.dump(legacy, fixture)
    try:
        os.symlink(target_path, selected_path)
    except OSError as error:
        if not is_symlink_creation_unavailable(error):
            raise
        print(f"SKIP U20: target-file symlink regression; this platform denies symlink creation ({error})")
    else:
        try:
            symlink_result = run(selected_root, write(selected_path, initial_plan))
        finally:
            os.unlink(selected_path)
        fails += symlink_result != 2
        print(("ok  " if symlink_result == 2 else "FAIL"), f"U20: target-file symlink cannot initialize lifecycle (exit {symlink_result})")
    os.unlink(target_path)

    with open(selected_path, "w") as fixture:
        json.dump(legacy, fixture)
    component_target = f"{checkpoint_dir}-target"
    os.rename(checkpoint_dir, component_target)
    try:
        os.symlink(component_target, checkpoint_dir, target_is_directory=True)
    except OSError as error:
        os.rename(component_target, checkpoint_dir)
        if not is_symlink_creation_unavailable(error):
            raise
        print(f"SKIP U20: path-component symlink regression; this platform denies symlink creation ({error})")
    else:
        try:
            symlink_result = run(selected_root, write(selected_path, initial_plan))
        finally:
            if os.name == "nt":
                os.rmdir(checkpoint_dir)
            else:
                os.unlink(checkpoint_dir)
            os.rename(component_target, checkpoint_dir)
        fails += symlink_result != 2
        print(("ok  " if symlink_result == 2 else "FAIL"), f"U20: path-component symlink cannot initialize lifecycle (exit {symlink_result})")
    if os.path.exists(selected_path):
        os.unlink(selected_path)
    primary_result = run(selected_root, write(path, initial_plan))
    fails += primary_result != 2
    print(("ok  " if primary_result == 2 else "FAIL"), "U17: selected feature worktree rejects writing its plan in the primary checkout", f"(exit {primary_result})")
    other_root = f"{root}/selected-worktrees/other-feature"
    subprocess.run(
        ["git", "worktree", "add", "-q", "-b", "feat/other", other_root],
        cwd=root,
        env=git_env,
        check=True,
    )
    other_path = f"{other_root}/.ai-engineering/workflow/checkpoints/demo.json"
    os.makedirs(os.path.dirname(other_path), exist_ok=True)
    other_result = run(other_root, write(other_path, initial_plan))
    fails += other_result != 2
    print(("ok  " if other_result == 2 else "FAIL"), "U17: lifecycle initialization in the wrong feature worktree is blocked", f"(exit {other_result})")
    git(["worktree", "remove", other_root])
    missing_lifecycle_result = run(selected_root, write(selected_path, legacy))
    fails += missing_lifecycle_result != 2
    print(("ok  " if missing_lifecycle_result == 2 else "FAIL"), "U17: a new feature plan cannot omit its initial lifecycle", f"(exit {missing_lifecycle_result})")
    git(["worktree", "remove", selected_root])
    outside_root = f"{root}/outside-feature"
    subprocess.run(
        ["git", "worktree", "add", "-q", outside_root, "feat/demo"],
        cwd=root,
        env=git_env,
        check=True,
    )
    outside_path = f"{outside_root}/.ai-engineering/workflow/checkpoints/demo.json"
    os.makedirs(os.path.dirname(outside_path), exist_ok=True)
    outside_result = run(outside_root, write(outside_path, initial_plan))
    fails += outside_result != 2
    print(("ok  " if outside_result == 2 else "FAIL"), "U17: lifecycle initialization outside the configured worktree root is blocked", f"(exit {outside_result})")
    git(["worktree", "remove", outside_root])

    implementation = with_lifecycle(
        legacy,
        life("implementation", "approved"),
    )
    lifecycle_result("U10: approved lifecycle permits implementation", initial_plan, implementation, 0)
    lifecycle_result(
        "U19: pending plan approval rejects implementation",
        initial_plan,
        with_lifecycle(legacy, life("implementation")),
        2,
    )
    json.dump(initial_plan, open(path, "w"))
    got = run(root, agent("[checkpoint demo#2 implement]"))
    fails += got != 2
    print(("ok  " if got == 2 else "FAIL"), "U19: implementation dispatch waits while plan approval is pending", f"(exit {got})")
    legacy_result("U19: legacy checkpoint keeps its existing gate behavior", agent("[checkpoint demo#2 implement]"), 0)

    overflow_lifecycle = json.dumps(implementation).replace('"id": 1,', '"id": 1e999,', 1)
    json.dump(initial_plan, open(path, "w"))
    got = run(root, {"tool_name": "Write", "tool_input": {"file_path": path, "content": overflow_lifecycle}})
    fails += got != 2
    print(("ok  " if got == 2 else "FAIL"), "non-finite id cannot pass lifecycle transition → blocked", f"(exit {got})")

    blocked = with_lifecycle(
        legacy,
        life("blocked", "approved"),
    )
    lifecycle_result("U10: entering blocked is accepted as a fail-safe", implementation, blocked, 0)
    lifecycle_result(
        "U11: resuming blocked work requires its plan approval",
        with_lifecycle(legacy, life("blocked")),
        implementation,
        2,
    )
    lifecycle_result("U10: valid blocked work can resume implementation", blocked, implementation, 0)

    completed_gates = all_gates_passed(legacy)
    awaiting_review = with_lifecycle(
        completed_gates,
        life("awaiting-app-review", "approved", "pending", reviewed_main),
    )
    lifecycle_result("U10: completed gates and current reviewed_main permit app review", implementation, awaiting_review, 0)

    ready_to_merge = with_lifecycle(
        completed_gates,
        life("ready-to-merge", "approved", "approved", reviewed_main),
    )
    lifecycle_result("U10: approved app review permits ready-to-merge", awaiting_review, ready_to_merge, 0)

    blocked_review = with_lifecycle(
        completed_gates,
        life("blocked", "approved", "approved", reviewed_main),
    )
    lifecycle_result("U10: blocked work retains current app approval", ready_to_merge, blocked_review, 0)
    lifecycle_result("U10: current blocked approval can resume merge", blocked_review, ready_to_merge, 0)

    invalid_lifecycles = [
        ("missing phase", {"plan_approval": "pending", "app_review": "not-started", "reviewed_main": None}),
        ("unknown phase", life("unrecognized")),
        ("invalid plan approval", life("awaiting-plan-approval", "yes")),
        ("invalid app review", life("awaiting-plan-approval", app_review="approved")),
        ("contradictory pending plan in implementation", life("implementation")),
    ]
    for name, invalid in invalid_lifecycles:
        lifecycle_result(f"U11: rejects {name}", legacy, with_lifecycle(legacy, invalid), 2)

    lifecycle_result(
        "U11: rejects implementation before plan approval",
        initial_plan,
        with_lifecycle(legacy, life("implementation")),
        2,
    )
    lifecycle_result(
        "U11: rejects skipped plan-approval and app-review phases",
        initial_plan,
        with_lifecycle(legacy, life("ready-to-merge", "approved", "approved", reviewed_main)),
        2,
    )
    lifecycle_result(
        "U19: rejects skipping directly to app review",
        initial_plan,
        awaiting_review,
        2,
    )
    lifecycle_result(
        "U11: rejects plan approval without entering implementation",
        initial_plan,
        with_lifecycle(legacy, life("awaiting-plan-approval", "approved")),
        2,
    )
    lifecycle_result(
        "U11: rejects app review before all checkpoint gates pass",
        implementation,
        with_lifecycle(legacy, life("awaiting-app-review", "approved", "pending", reviewed_main)),
        2,
    )
    lifecycle_result(
        "U11: rejects missing reviewed_main before app review",
        implementation,
        with_lifecycle(completed_gates, life("awaiting-app-review", "approved", "pending", None)),
        2,
    )
    lifecycle_result(
        "U11: rejects malformed reviewed_main",
        awaiting_review,
        with_lifecycle(completed_gates, life("ready-to-merge", "approved", "approved", "1234")),
        2,
    )
    lifecycle_result(
        "U11: rejects app-review approval without ready-to-merge transition",
        awaiting_review,
        with_lifecycle(completed_gates, life("awaiting-app-review", "approved", "approved", reviewed_main)),
        2,
    )
    lifecycle_result(
        "U11: rejects complete before verified merge",
        ready_to_merge,
        with_lifecycle(completed_gates, life("complete", "approved", "approved", reviewed_main)),
        2,
    )

    git(["commit", "--allow-empty", "-q", "-m", "advance local main"])
    current_main = git(["rev-parse", "refs/heads/main"])
    lifecycle_result(
        "U11: rejects ready-to-merge when reviewed_main is stale",
        awaiting_review,
        with_lifecycle(completed_gates, life("ready-to-merge", "approved", "approved", reviewed_main)),
        2,
    )
    lifecycle_result(
        "U11: rejects a non-current reviewed_main while awaiting app review",
        implementation,
        with_lifecycle(completed_gates, life("awaiting-app-review", "approved", "pending", reviewed_main)),
        2,
    )
    refreshed_review = with_lifecycle(
        completed_gates,
        life("awaiting-app-review", "approved", "pending", current_main),
    )
    lifecycle_result("U10: advancing local main resets approval for a fresh review", ready_to_merge, refreshed_review, 0)
    blocked_stale_review = with_lifecycle(
        completed_gates,
        life("blocked", "approved", "approved", reviewed_main),
    )
    lifecycle_result("U11: blocked stale review cannot skip a fresh review", blocked_stale_review, with_lifecycle(
        completed_gates,
        life("ready-to-merge", "approved", "approved", current_main),
    ), 2)
    lifecycle_result("U11: blocked stale review resumes at pending review on current main", blocked_stale_review, refreshed_review, 0)

    # U28: ready-to-merge stays bound to fresh approval, and complete needs a verified main merge.
    merge_slug = "verified-merge"
    merge_root = os.path.realpath(f"{root}/selected-worktrees/{merge_slug}")
    os.makedirs(os.path.dirname(merge_root), exist_ok=True)
    subprocess.run(
        ["git", "worktree", "add", "-q", "-b", f"feat/{merge_slug}", merge_root, "refs/heads/main"],
        cwd=root,
        env=git_env,
        check=True,
    )
    merge_checkpoint = f"{merge_root}/.ai-engineering/workflow/checkpoints/{merge_slug}.json"
    os.makedirs(os.path.dirname(merge_checkpoint), exist_ok=True)
    main_at_review = git(["rev-parse", "refs/heads/main"])
    ready_plan = {
        "slug": merge_slug,
        "checkpoints": [cp(1, "passed", "passed", "n/a", "passed")],
        "lifecycle": life("ready-to-merge", "approved", "approved", main_at_review),
    }
    with open(merge_checkpoint, "w") as fixture:
        json.dump(ready_plan, fixture)
    with open(f"{merge_root}/merge-feature.txt", "w") as fixture:
        fixture.write("approved feature\n")
    git(["add", merge_checkpoint, "merge-feature.txt"], cwd=merge_root)
    git(["commit", "-q", "-m", "approve feature for merge"], cwd=merge_root)
    merge_branch = git(["rev-parse", f"refs/heads/feat/{merge_slug}"])
    assert git(["symbolic-ref", "--short", "HEAD"], cwd=merge_root) == f"feat/{merge_slug}"
    assert git(["rev-parse", "refs/heads/main"]) == main_at_review
    assert git(["remote"]) == ""

    git(["commit", "--allow-empty", "-q", "-m", "advance main after approval"])
    stale_main = git(["rev-parse", "refs/heads/main"])
    stale_ready_result = run(merge_root, write(merge_checkpoint, ready_plan))
    fails += stale_ready_result != 2
    print(("ok  " if stale_ready_result == 2 else "FAIL"), "U28: stale app approval cannot enter ready-to-merge", f"(exit {stale_ready_result})")
    git(["rebase", "refs/heads/main"], cwd=merge_root)
    git(["merge-base", "--is-ancestor", stale_main, "HEAD"], cwd=merge_root)

    fresh_review_plan = with_lifecycle(
        ready_plan,
        life("awaiting-app-review", "approved", "pending", stale_main),
    )
    fresh_review_result = run(merge_root, write(merge_checkpoint, fresh_review_plan))
    fails += fresh_review_result != 0
    print(("ok  " if fresh_review_result == 0 else "FAIL"), "U28: renewed app review binds to the advanced local main", f"(exit {fresh_review_result})")
    with open(merge_checkpoint, "w") as fixture:
        json.dump(fresh_review_plan, fixture)
    fresh_ready_plan = with_lifecycle(
        fresh_review_plan,
        life("ready-to-merge", "approved", "approved", stale_main),
    )
    fresh_ready_result = run(merge_root, write(merge_checkpoint, fresh_ready_plan))
    fails += fresh_ready_result != 0
    print(("ok  " if fresh_ready_result == 0 else "FAIL"), "U28: fresh app approval authorizes ready-to-merge", f"(exit {fresh_ready_result})")
    with open(merge_checkpoint, "w") as fixture:
        json.dump(fresh_ready_plan, fixture)

    complete_plan = with_lifecycle(
        fresh_ready_plan,
        life("complete", "approved", "approved", stale_main),
    )
    unverified_complete_result = run(merge_root, write(merge_checkpoint, complete_plan))
    fails += unverified_complete_result != 2
    print(("ok  " if unverified_complete_result == 2 else "FAIL"), "U28: complete is refused before a verified merge", f"(exit {unverified_complete_result})")

    fresh_ready_bytes = open(merge_checkpoint).read()
    with open(merge_checkpoint, "w") as fixture:
        json.dump(fresh_ready_plan, fixture)
    git(["add", merge_checkpoint], cwd=merge_root)
    git(["commit", "-q", "-m", "record fresh merge approval"], cwd=merge_root)
    merge_branch = git(["rev-parse", f"refs/heads/feat/{merge_slug}"])
    assert git(["rev-parse", "refs/heads/main"]) == stale_main
    git(["merge-base", "--is-ancestor", stale_main, merge_branch])
    subprocess.run(
        ["git", "merge", "--no-commit", "--no-ff", f"refs/heads/feat/{merge_slug}"],
        cwd=root,
        env=git_env,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "-q", "-m", "chore(verified-merge): merge feature"],
        cwd=root,
        env=git_env,
        check=True,
    )
    merge_commit = git(["rev-parse", "refs/heads/main"])
    parents = git(["rev-list", "--parents", "-n", "1", merge_commit]).split()
    assert parents == [merge_commit, stale_main, merge_branch]
    git(["merge-base", "--is-ancestor", merge_branch, merge_commit])
    assert git(["symbolic-ref", "--short", "HEAD"], cwd=merge_root) == f"feat/{merge_slug}"
    assert git(["rev-parse", "HEAD"], cwd=merge_root) == merge_branch
    assert git(["rev-parse", "refs/heads/main"], cwd=merge_root) == merge_commit
    git(["merge-base", "--is-ancestor", "HEAD", merge_commit], cwd=merge_root)

    verified_process = subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps(write(merge_checkpoint, complete_plan)),
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": merge_root},
    )
    verified_complete_result = verified_process.returncode
    fails += verified_complete_result != 0
    if verified_complete_result != 0:
        print("U28 complete refusal detail:", verified_process.stderr.strip())
    print(("ok  " if verified_complete_result == 0 else "FAIL"), "U28: verified merge authorizes complete", f"(exit {verified_complete_result})")
    with open(merge_checkpoint, "w") as fixture:
        fixture.write(fresh_ready_bytes)
    git(["worktree", "remove", merge_root])

    fails += nonlocal_fails[0]

sys.exit(1 if fails else 0)
