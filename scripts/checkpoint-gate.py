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
import json
import os
import re
import sys

GATES = ["behavior", "ui", "review"]
STAGES = {"tests", "implement", "behavior", "ui", "review", "fix"}
MARKER = re.compile(r"^\s*\[checkpoint\s+([\w.-]+)#(\d+)\s+(\w+)\]")
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
    return (cp.get("gates") or {}).get(name, {}).get("status", "pending")


def gate_ok(cp, name):
    return gate(cp, name) in ("passed", "n/a")


def unpassed_before(cps, cid):
    return [c["id"] for c in cps if c["id"] < cid and c.get("status") != "passed"]


def check_agent(prompt, root):
    m = MARKER.match(prompt or "")
    if not m:
        return  # not an orchestrated checkpoint call
    slug, cid, stage = m.group(1), int(m.group(2)), m.group(3)
    if stage not in STAGES:
        block(f"unknown stage '{stage}'. Use one of: {', '.join(sorted(STAGES))}.")
    path = os.path.join(root, ".ai-engineering", "workflow", "checkpoints", f"{slug}.json")
    try:
        cps = json.load(open(path))["checkpoints"]
    except (OSError, ValueError, KeyError) as e:
        block(f"can't read {path}: {e}")
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


def check_plan(new_text, old_text):
    try:
        new = json.loads(new_text)["checkpoints"]
    except (ValueError, KeyError, TypeError):
        return  # not a valid plan yet; the planner validates JSON itself
    old = {}
    try:
        old = {c["id"]: snapshot(c) for c in json.loads(old_text)["checkpoints"]}
    except (ValueError, KeyError, TypeError):
        pass
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
        check_plan(text, "")  # structural rules against an empty baseline; exits 2 on a violation
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
    check_plan(new_text, old_text)
    allow()


if __name__ == "__main__":
    main()
