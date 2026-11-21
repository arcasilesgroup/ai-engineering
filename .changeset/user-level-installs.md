---
"ai-engineering": patch
---

The gitleaks install hint the commit floor prints now leads with what works without administrator rights. On Windows it suggested `choco install`, which needs an administrator; it now suggests `winget install --id Gitleaks.Gitleaks -e`, or putting `gitleaks.exe` from the releases page in a folder on your user PATH. On Linux it suggested `apt install`, which needs sudo; it now suggests the release binary in `~/.local/bin` first. The README gains a short section on installing Bun, ai-eng and gitleaks on a managed PC with no administrator rights.
