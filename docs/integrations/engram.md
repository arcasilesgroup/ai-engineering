# Engram (third-party memory)

`ai-engineering` does not bundle a memory layer. Engram is a peer
product maintained by `Gentleman-Programming/engram`; install it
separately if you want cross-session memory in your IDE assistant.

This integration is optional. The framework works without it.

## Install

### macOS

```bash
brew install engram
```

### Linux

```bash
curl -fsSL https://github.com/Gentleman-Programming/engram/releases/latest/download/engram-linux-x86_64 \
  -o "$HOME/.local/bin/engram"
chmod +x "$HOME/.local/bin/engram"
```

`$HOME/.local/bin` is on the standard Linux user `$PATH`. Adjust the
destination if your shell uses a different bin directory.

### Windows

```powershell
winget install Engram
```

## Configure your IDE

After the binary is on `$PATH`, run the IDE-specific setup once per
project:

```bash
engram setup claude_code   # Claude Code
engram setup codex          # OpenAI Codex
engram setup gemini_cli     # Gemini CLI
```

GitHub Copilot is not currently supported by Engram.

## Verify

```bash
ai-eng doctor
```

`doctor` reports Engram status without installing or modifying it.

## Removal

`brew uninstall engram` on macOS, `winget uninstall Engram` on
Windows, or `rm "$HOME/.local/bin/engram"` on Linux. `ai-eng` does not
manage Engram state on disk, so removal is a one-step operation.
