#!/bin/sh
# .git/hooks/pre-push — ai-eng git floor shim, marker-managed (blueprint 13.2).
# Logic lives in the binary, not in this file. Regenerate: ai-eng init / update.
# Remove: ai-eng uninstall (it deletes only hooks carrying this marker).
#!/bin/sh
command -v ai-eng >/dev/null 2>&1 && exec ai-eng git pre-push
echo "ai-eng: git floor unavailable — 'ai-eng' not on PATH (hook: pre-push)" >&2
exit 1
