# Handler: Language -- Python

## Purpose

Language-specific review for Python code. Supplements the 8-concern review agents with Python-idiomatic checks, framework-aware patterns, and diagnostic tool integration.

## Integration

Dispatched as **Step 2b** (between Step 2 dispatch and Step 3 aggregate). Findings use the same YAML format. Language findings receive a **+10% confidence bonus** when corroborated by a concern agent.

## Procedure

### Step 1 -- Detect Python Scope

1. Identify `.py` files in the diff
2. If no Python files, skip this handler entirely
3. Detect frameworks from imports:
   - `django` imports -> enable Django checks
   - `fastapi` imports -> enable FastAPI checks
   - `flask` imports -> enable Flask checks
   - `sqlalchemy` imports -> enable SQLAlchemy checks
4. Read `.ai-engineering/contexts/languages/python.md` if not already loaded

### Step 2 -- Critical Findings (severity: critical)

Scan every changed line for:

**SQL Injection via f-strings or format()**
```python
# BAD: injectable
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)
cursor.execute("SELECT * FROM users WHERE id = {}".format(user_id))

# GOOD: parameterized
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

**Command Injection via subprocess**
```python
# BAD: shell=True with user input
subprocess.run(f"ls {user_input}", shell=True)
os.system(f"echo {user_input}")

# GOOD: argument list, no shell
subprocess.run(["ls", user_input], shell=False)
```

**eval/exec with untrusted input**
- Flag any `eval()` or `exec()` call
- Confidence 90% if argument includes variables, 60% if string literal

**Unsafe deserialization**
- `pickle.loads()`, `pickle.load()` on untrusted data
- `yaml.load()` without `Loader=SafeLoader` or `yaml.safe_load()`
- `marshal.loads()`, `shelve.open()` on user-controlled paths

**Bare except swallowing errors**
```python
# BAD: swallows everything including KeyboardInterrupt
except:
    pass

# GOOD: specific exceptions
except ValueError:
    logger.warning("Invalid value")
```

### Step 3 -- High Findings (severity: major)

**Missing type hints on public functions**
- Public functions (no leading underscore) missing parameter or return type annotations
- Confidence 70% for library code, 50% for scripts

**Mutable default arguments**
```python
# BAD: shared mutable default
def append_to(item, target=[]):
    target.append(item)
    return target

# GOOD: None sentinel
def append_to(item, target=None):
    if target is None:
        target = []
    target.append(item)
    return target
```

**Imperative loops replaceable with comprehensions**
- `for` loops that build a list via `.append()` -> list comprehension
- Only flag when the comprehension would be a single readable expression

**Raw string concatenation for paths**
- `path + "/" + filename` -> `pathlib.Path` or `os.path.join()`

### Step 4 -- Medium Findings (severity: minor)

**PEP 8 violations not caught by formatter**
- Semantic naming violations (single-letter variables outside comprehensions/lambdas)
- Module-level code organization (imports, constants, classes, functions)

**print() instead of logging**
- `print()` in library/application code -> `logging.getLogger(__name__)`
- Acceptable in CLI entry points and scripts

**Identity checks for singletons**
```python
# BAD
if value == None:
if value == True:

# GOOD
if value is None:
if value is True:
```

**Unnecessary else after return**
```python
# BAD
if condition:
    return x
else:
    return y

# GOOD
if condition:
    return x
return y
```

### Step 5 -- Framework-Specific Checks

**Django**
- Missing `select_related()` / `prefetch_related()` in querysets accessed in loops (N+1)
- Database writes outside `transaction.atomic()` in multi-step operations
- Raw SQL in views without parameterization
- Missing `@login_required` or permission checks on views
- `Model.objects.all()` without pagination in API views

**FastAPI**
- Overly permissive CORS (`allow_origins=["*"]` in production)
- Missing Pydantic model validation on request bodies
- Synchronous blocking calls in async endpoints
- Missing `status_code` on response models
- `@app.on_event("startup")` instead of lifespan context manager

**Flask**
- `app.secret_key` hardcoded in source
- Missing CSRF protection on forms
- `render_template_string()` with user input (SSTI)
- Debug mode enabled in production config

### Step 6 -- Diagnostic Tool Cross-Reference

When feasible, validate findings against tool output:

| Tool | Command | Validates |
|------|---------|-----------|
| mypy | `mypy --strict {files}` | Type safety findings |
| ruff | `ruff check {files}` | Style, import, complexity findings |
| bandit | `bandit -r {files}` | Security findings |
| pytest | `pytest --cov --cov-report=term-missing` | Test coverage gaps |

If a diagnostic tool contradicts a finding, note the discrepancy and adjust confidence accordingly.

## Output Format

```yaml
findings:
  - id: lang-python-N
    severity: critical|major|minor
    confidence: 0-100
    file: path
    line: N
    finding: "description"
    evidence: "code snippet"
    remediation: "how to fix"
    self_challenge:
      counter: "why this might be wrong"
      resolution: "why it stands or adjustment"
      adjusted_confidence: N
```
