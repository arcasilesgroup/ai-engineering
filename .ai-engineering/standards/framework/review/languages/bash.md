# Bash Review Guidelines

## Update Metadata
- Rationale: Bash-specific patterns for safety, portability, and error handling.

## Idiomatic Patterns
- Always use `set -euo pipefail` at script start.
- Quote all variable expansions: `"$var"` not `$var`.
- Use `[[ ]]` over `[ ]` for conditionals (bash-specific, but safer).
- Use `local` for function variables to avoid scope leakage.
- Prefer `$(command)` over backticks for command substitution.

## Performance Anti-Patterns
- **Subshell in loops**: Avoid `$(cat file)` inside loops — read once into variable.
- **External commands for string ops**: Use bash built-ins (`${var%%pattern}`, `${var#prefix}`).
- **Unnecessary forks**: `echo "$var"` instead of `printf` in tight loops.

## Security Patterns
- Never use `eval` on user input.
- Always quote file paths: `rm "$file"` not `rm $file`.
- Use `mktemp` for temporary files with `trap` for cleanup.
- Validate script arguments before use.

## Testing Patterns
- Use BATS (Bash Automated Testing System) for test suites.
- Mock external commands by prepending a `$MOCK_DIR` to `PATH`.
- Test exit codes and stderr output, not just stdout.

## Self-Challenge Questions
- Is this portable to bash 4.0+ or only works on newer versions?
- Is the security concern realistic or theoretical?

## References
- Enforcement: `standards/framework/stacks/bash-powershell.md`
