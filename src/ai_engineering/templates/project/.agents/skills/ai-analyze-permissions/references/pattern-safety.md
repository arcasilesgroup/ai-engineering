# Pattern Safety Guidelines

## Safe to auto-approve (commonly needed)

- `Bash(npx:*)`, `Bash(node:*)`, `Bash(npm:*)`, `Bash(pnpm:*)` - JS/Node tooling
- `Bash(python:*)`, `Bash(python3:*)`, `Bash(pip:*)` - Python tooling
- `Bash(cargo :*)`, `Bash(cd :* && cargo:*)` - Rust tooling
- `Bash(docker compose:*)`, `Bash(docker ps:*)` - Docker
- `Bash(kubectl get:*)`, `Bash(kubectl describe:*)` - K8s read operations
- `Bash(git:*)` subcommands (add, commit, log, diff, etc.)
- `Bash(gh:*)` read operations (pr view, issue list, api, etc.)
- `Bash(chmod:*)`, `Bash(ln:*)`, `Bash(wc:*)`, `Bash(which:*)` - basic utilities
- `Bash(ssh:*)`, `Bash(tmux:*)`, `Bash(bash:*)`, `Bash(zsh:*)` - shell/system
- `WebFetch(domain:*)`, `WebSearch` - web access

## Require review (side effects)

- `Bash(kubectl delete:*)`, `Bash(kubectl apply:*)`
- `Bash(docker rm:*)`, `Bash(docker exec:*)`
- `Bash(aws s3 rm:*)`
- `Bash(rm:*)`, `Bash(mv:*)`
- `Bash(git push:*)` - consider keeping per-project in local settings

## Never auto-approve

- `Bash(sudo:*)`
- `Bash(chmod 777:*)`
- Patterns that could leak secrets
