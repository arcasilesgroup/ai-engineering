"""Run: python3 tests/test_checkpoint_gate.py"""
import copy
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


with tempfile.TemporaryDirectory() as root:
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

sys.exit(1 if fails else 0)
