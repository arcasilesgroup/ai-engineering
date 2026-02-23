# Diagnostic Patterns Reference

On-demand reference for the debug skill. Load selectively by section heading.

## Reproduction Strategies

### Minimal Reproduction Case (MRC)
1. Strip all code unrelated to the bug.
2. Replace external dependencies with stubs/mocks.
3. Create a self-contained test that triggers the failure.
4. If the MRC passes, add back code until it fails — the last addition is the trigger.

### Time-Based Reproduction
- For intermittent bugs: increase iteration count (run 100x).
- For race conditions: add artificial delays at suspected contention points.
- For timezone bugs: test with UTC, UTC+14, UTC-12.

## Isolation Techniques

### Binary Search (git bisect)
```bash
git bisect start
git bisect bad HEAD
git bisect good <last-known-good-commit>
# Run test at each step
git bisect run pytest tests/test_specific.py::test_case
```

### Layer Isolation
1. **I/O layer**: mock file system, network, stdin/stdout.
2. **State layer**: initialize with known state, verify mutations.
3. **Logic layer**: test pure functions with edge cases.
4. **Integration layer**: test component interactions.

### Dependency Isolation
- Pin all dependencies to exact versions.
- Test with `--no-deps` to rule out transitive issues.
- Compare `pip freeze` between working and broken environments.

## Root Cause Analysis

### 5 Whys Template
```
Symptom: [observable failure]
Why 1: [immediate cause]
Why 2: [cause of Why 1]
Why 3: [cause of Why 2]
Why 4: [cause of Why 3]
Why 5: [root cause] → this is what we fix
```

### Common Root Cause Categories
| Category | Symptoms | Investigation |
|----------|----------|---------------|
| State corruption | Intermittent failures, works-then-breaks | Check shared mutable state, singletons |
| Race condition | Fails under load, passes in isolation | Check async/threading, add locks/barriers |
| Environment drift | Works locally, fails in CI | Compare env vars, paths, versions |
| Type mismatch | Silent wrong results | Check `None` vs empty, int vs str, encoding |
| Resource leak | Degrades over time | Check file handles, connections, memory |

## Evidence Collection

### What to Capture
- Full stack trace with local variables.
- Input values that trigger the failure.
- Environment: OS, Python version, dependency versions.
- Timeline: when it started, what changed.
- Frequency: always, intermittent, only-under-load.

### How to Capture (Python)
```python
import traceback
import sys

try:
    result = suspect_function(args)
except Exception:
    traceback.print_exc()
    # Capture locals at failure point
    tb = sys.exc_info()[2]
    frame = tb.tb_frame
    print(f"Locals: {frame.f_locals}")
```
