# .ai-engineering/git/pre-commit — shim. The logic lives in the binary (blueprint 13.2).
#!/bin/sh
command -v ai-eng >/dev/null 2>&1 && exec ai-eng git pre-commit
exec "$HOME/repos/ai-engineering/dist/ai-eng" git pre-commit
