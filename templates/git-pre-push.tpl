#!/bin/sh
# .git/hooks/pre-push — ai-eng git floor shim, marker-managed (blueprint 13.2).
# Logic lives in the binary, not in this file. Regenerate: ai-eng init / update.
# Remove: ai-eng uninstall (it deletes only hooks carrying this marker).
# The same gate the chain asks (src/env.ts): a repo that never declared itself in
# .ai-engineering/config.toml is not governed, and its commits are not ours to judge.
# This shim is born with every clone now (init.templateDir), so it must pass in silence
# where nobody asked for policy.
[ -f .ai-engineering/config.toml ] || exit 0
command -v ai-eng >/dev/null 2>&1 && exec ai-eng git pre-push
echo "ai-eng: this repo is governed but 'ai-eng' is not on PATH — install it, or remove .ai-engineering/config.toml to stop being governed (hook: pre-push)" >&2
exit 1
