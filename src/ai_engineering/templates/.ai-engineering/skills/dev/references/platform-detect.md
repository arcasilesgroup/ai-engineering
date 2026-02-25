# Platform Detect

- Resolve host OS (`darwin`, `linux`, `win32`) before choosing installation commands.
- Detect provider context (GitHub vs Azure DevOps) before auth and policy flows.
- Validate tool availability with deterministic binary checks (`gh`, `az`, `uv`, `ruff`, `ty`).
- Prefer API-direct fallback when provider CLI installation/auth is unavailable.
