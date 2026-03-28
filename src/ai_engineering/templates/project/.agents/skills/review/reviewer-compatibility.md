# Compatibility Reviewer

Focus on public API changes, backward compatibility, config and schema drift,
upgrade hazards, and migration expectations.

## Inspect

- public function, CLI, HTTP, and config surface changes
- schema, manifest, and state format drift
- renamed or removed fields, flags, or behaviors
- rollout assumptions and upgrade sequencing

## Report Only When

- existing consumers can break without a clear migration path
- defaults or semantics change in a surprising way
- versioning or upgrade expectations are violated

## Avoid

- internal refactors with no consumer-visible impact
- theoretical compatibility concerns with no realistic caller
