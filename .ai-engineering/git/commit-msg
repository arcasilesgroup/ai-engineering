# .ai-engineering/git/commit-msg — shim. Convention + Receipt-Id trailer + override
# reason when one is active. Logic in the binary (blueprint 13.2).
#!/bin/sh
command -v ai-eng >/dev/null 2>&1 && exec ai-eng git commit-msg "$1"
exec "$HOME/repos/ai-engineering/dist/ai-eng" git commit-msg "$1"
