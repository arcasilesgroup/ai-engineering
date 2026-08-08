# Compatibility

- Anything already shipped in the default branch that this changes: signature, output shape,
  status code, file format, config key, environment variable.
- Data written by the old version and read by the new one, and the other way around.
- Migrations: forward-only, ordered, and rerunnable without damage.
- Removals: hard delete with the breakage written in the changelog, never a silent shim.
- Config: a key that changes meaning is a breaking change even when it keeps its name.
