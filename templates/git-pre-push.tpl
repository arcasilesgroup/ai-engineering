# .ai-engineering/git/pre-push — shim. gitleaks over unpushed + override expiry.
# Logic in the binary (blueprint 13.2).
#!/bin/sh
command -v ai-eng >/dev/null 2>&1 && exec ai-eng git pre-push
exec "$HOME/repos/ai-engineering/dist/ai-eng" git pre-push
